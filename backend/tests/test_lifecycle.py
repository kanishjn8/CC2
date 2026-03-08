"""
Tests for the shipment lifecycle manager — stamp, prune, spawn logic.

Uses the same in-memory SQLite setup as other test modules.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.models import (
    CarrierPerformance,
    Route,
    Shipment,
    ShipmentStatus,
)
from app.lifecycle import (
    _stamp_terminal_shipments,
    _prune_expired,
    _count_active,
    _spawn_shipment,
    _spawn_replacements,
    _inject_disruptions,
)
from tests.conftest import make_carrier, make_route, make_shipment, make_warehouse


# ═══════════════════════════════════════════════════════════════════════════════
# _stamp_terminal_shipments
# ═══════════════════════════════════════════════════════════════════════════════

class TestStampTerminal:

    def test_stamps_delivered_shipment(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.delivered)
        ship.is_active = True
        ship.delivered_at = None
        db.flush()

        _stamp_terminal_shipments(db)

        assert ship.delivered_at is not None

    def test_stamps_failed_shipment(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.failed)
        ship.is_active = True
        ship.delivered_at = None
        db.flush()

        _stamp_terminal_shipments(db)

        assert ship.delivered_at is not None

    def test_does_not_stamp_in_transit(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        ship.is_active = True
        ship.delivered_at = None
        db.flush()

        _stamp_terminal_shipments(db)

        assert ship.delivered_at is None

    def test_does_not_re_stamp(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.delivered)
        ship.is_active = True
        ship.delivered_at = datetime(2026, 1, 1)
        db.flush()

        _stamp_terminal_shipments(db)

        assert ship.delivered_at == datetime(2026, 1, 1)  # unchanged


# ═══════════════════════════════════════════════════════════════════════════════
# _prune_expired
# ═══════════════════════════════════════════════════════════════════════════════

class TestPruneExpired:

    def test_prunes_past_grace_period(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.delivered)
        ship.is_active = True
        ship.delivered_at = datetime.utcnow() - timedelta(hours=1)
        db.flush()

        pruned = _prune_expired(db)

        assert pruned == 1
        assert ship.is_active is False

    def test_does_not_prune_recent(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.delivered)
        ship.is_active = True
        ship.delivered_at = datetime.utcnow()
        db.flush()

        pruned = _prune_expired(db)

        assert pruned == 0
        assert ship.is_active is True

    def test_does_not_prune_already_inactive(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.delivered)
        ship.is_active = False
        ship.delivered_at = datetime.utcnow() - timedelta(hours=1)
        db.flush()

        pruned = _prune_expired(db)
        assert pruned == 0


# ═══════════════════════════════════════════════════════════════════════════════
# _count_active
# ═══════════════════════════════════════════════════════════════════════════════

class TestCountActive:

    def test_counts_active_only(self, db):
        carrier = make_carrier(db)
        s1 = make_shipment(db, carrier)
        s1.is_active = True
        s2 = make_shipment(db, carrier)
        s2.is_active = False
        s3 = make_shipment(db, carrier)
        s3.is_active = True
        db.flush()

        assert _count_active(db) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# _spawn_shipment
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpawnShipment:

    def test_creates_one_shipment(self, db):
        carrier = make_carrier(db)
        route = make_route(db)
        db.flush()

        ship = _spawn_shipment(db, [carrier], [route])

        assert ship.shipment_id.startswith("SH-")
        assert ship.is_active is True
        assert ship.delivered_at is None

    def test_carrier_shipment_count_incremented(self, db):
        carrier = make_carrier(db)
        route = make_route(db)
        db.flush()
        before = carrier.total_shipments

        _spawn_shipment(db, [carrier], [route])

        assert carrier.total_shipments == before + 1

    def test_status_is_active(self, db):
        carrier = make_carrier(db)
        route = make_route(db)
        db.flush()

        ship = _spawn_shipment(db, [carrier], [route])

        assert ship.status in {ShipmentStatus.created, ShipmentStatus.dispatched, ShipmentStatus.in_transit}

    def test_sla_after_eta(self, db):
        carrier = make_carrier(db)
        route = make_route(db)
        db.flush()

        ship = _spawn_shipment(db, [carrier], [route])

        assert ship.sla_deadline > ship.eta


# ═══════════════════════════════════════════════════════════════════════════════
# _spawn_replacements
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpawnReplacements:

    def test_spawns_correct_count(self, db):
        carrier = make_carrier(db)
        route = make_route(db)
        db.flush()

        before = db.query(Shipment).count()
        _spawn_replacements(db, 3)
        db.flush()

        assert db.query(Shipment).count() == before + 3

    def test_zero_deficit_no_spawn(self, db):
        before = db.query(Shipment).count()
        _spawn_replacements(db, 0)
        db.flush()
        assert db.query(Shipment).count() == before

    def test_negative_deficit_no_spawn(self, db):
        before = db.query(Shipment).count()
        _spawn_replacements(db, -5)
        db.flush()
        assert db.query(Shipment).count() == before

    def test_no_carriers_no_spawn(self, db):
        make_route(db)
        db.flush()
        before = db.query(Shipment).count()
        _spawn_replacements(db, 3)
        db.flush()
        assert db.query(Shipment).count() == before

    def test_max_cap_per_tick(self, db):
        """Even with large deficit, should cap at MAX_SPAWN_PER_TICK (4)."""
        carrier = make_carrier(db)
        route = make_route(db)
        db.flush()

        before = db.query(Shipment).count()
        _spawn_replacements(db, 100)
        db.flush()

        spawned = db.query(Shipment).count() - before
        assert spawned <= 4  # MAX_SPAWN_PER_TICK


# ═══════════════════════════════════════════════════════════════════════════════
# _inject_disruptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestInjectDisruptions:

    def test_no_active_shipments_is_noop(self, db):
        """Must not raise when there are no active shipments."""
        _inject_disruptions(db)  # should not raise

    def test_disruption_can_delay(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        ship.is_active = True
        original_eta = ship.eta
        db.flush()

        # Force the delay branch
        with patch("app.lifecycle.random.random", return_value=0.01):
            with patch("app.lifecycle.random.uniform", return_value=4.0):
                _inject_disruptions(db)

        assert ship.status == ShipmentStatus.delayed
        assert ship.eta > original_eta

    def test_disruption_does_not_affect_delivered(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.delivered)
        ship.is_active = True
        db.flush()

        _inject_disruptions(db)

        assert ship.status == ShipmentStatus.delivered
