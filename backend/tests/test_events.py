"""
Tests for the event generation system — every EventType is verified
to be emitted with the correct payload structure and recorded in the DB.
"""

import json

import pytest

from app.models import EventType, ShipmentStatus, SimulationEvent, TrafficLevel
from app.simulation import LogisticsSimulation
from tests.conftest import (
    make_carrier,
    make_route,
    make_shipment,
    make_warehouse,
)
from unittest.mock import patch


@pytest.fixture()
def sim():
    return LogisticsSimulation(tick_interval=0.01, sim_speed=1.0)


# ── Helper: pull the latest event of a given type ──────────────────────────

def latest(db, event_type):
    db.flush()   # ensure pending adds are visible to the same session
    return (
        db.query(SimulationEvent)
        .filter_by(event_type=event_type)
        .order_by(SimulationEvent.id.desc())
        .first()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Direct _emit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmitHelper:

    def test_emit_persists_to_db(self, sim, db):
        sim._emit(db, EventType.eta_drift, "SH-abc123", {"drift_hours": 2.5})
        db.flush()
        assert db.query(SimulationEvent).count() == 1

    def test_emit_stores_correct_event_type(self, sim, db):
        sim._emit(db, EventType.warehouse_congestion, "WH-001", {"congestion_score": 0.9})
        db.flush()
        ev = db.query(SimulationEvent).first()
        assert ev.event_type == EventType.warehouse_congestion

    def test_emit_stores_entity_id(self, sim, db):
        sim._emit(db, EventType.pickup_failure, "SH-xyz", {})
        db.flush()
        ev = db.query(SimulationEvent).first()
        assert ev.entity_id == "SH-xyz"

    def test_emit_payload_is_valid_json(self, sim, db):
        payload = {"key": "value", "number": 42, "nested": {"a": 1}}
        sim._emit(db, EventType.shipment_created, "SH-001", payload)
        db.flush()
        ev = db.query(SimulationEvent).first()
        assert json.loads(ev.payload) == payload

    def test_emit_records_sim_time(self, sim, db):
        sim._emit(db, EventType.eta_drift, "SH-001", {})
        db.flush()
        ev = db.query(SimulationEvent).first()
        assert ev.sim_time == sim.sim_time

    def test_emit_increments_total_events_counter(self, sim, db):
        before = sim.total_events
        sim._emit(db, EventType.route_traffic_update, "RT-001", {})
        sim._emit(db, EventType.route_traffic_update, "RT-002", {})
        assert sim.total_events == before + 2

    def test_emit_empty_payload(self, sim, db):
        sim._emit(db, EventType.shipment_delivered, "SH-001", {})
        db.flush()
        ev = db.query(SimulationEvent).first()
        assert json.loads(ev.payload) == {}


# ═══════════════════════════════════════════════════════════════════════════════
# shipment_created
# ═══════════════════════════════════════════════════════════════════════════════

class TestShipmentCreatedEvent:

    def test_payload_fields_present(self, sim, db):
        payload = {
            "origin": "Mumbai",
            "destination": "Delhi",
            "carrier": "CR-abc",
            "eta": "2026-03-08T10:00:00",
            "sla_deadline": "2026-03-08T12:00:00",
        }
        sim._emit(db, EventType.shipment_created, "SH-new", payload)
        ev = latest(db, EventType.shipment_created)
        data = json.loads(ev.payload)
        for key in ("origin", "destination", "carrier", "eta", "sla_deadline"):
            assert key in data, f"Missing key: {key}"


# ═══════════════════════════════════════════════════════════════════════════════
# shipment_dispatched
# ═══════════════════════════════════════════════════════════════════════════════

class TestShipmentDispatchedEvent:

    def test_emitted_on_created_to_dispatched_transition(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            sim._advance_shipments(db)

        ev = latest(db, EventType.shipment_dispatched)
        assert ev is not None
        assert ev.entity_id == shipment.shipment_id
        data = json.loads(ev.payload)
        assert "origin" in data
        assert "destination" in data
        assert "carrier" in data

    def test_emitted_on_dispatched_to_in_transit(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.dispatched)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            sim._advance_shipments(db)

        ev = latest(db, EventType.shipment_dispatched)
        assert ev is not None
        data = json.loads(ev.payload)
        assert data["status"] == "in_transit"


# ═══════════════════════════════════════════════════════════════════════════════
# shipment_delivered
# ═══════════════════════════════════════════════════════════════════════════════

class TestShipmentDeliveredEvent:

    def test_emitted_with_destination(self, sim, db):
        carrier = make_carrier(db, delay_prob=0.0)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.2):
            sim._advance_shipments(db)

        ev = latest(db, EventType.shipment_delivered)
        assert ev is not None
        data = json.loads(ev.payload)
        assert data["destination"] == shipment.destination


# ═══════════════════════════════════════════════════════════════════════════════
# shipment_delayed
# ═══════════════════════════════════════════════════════════════════════════════

class TestShipmentDelayedEvent:

    def test_payload_contains_new_eta_and_carrier(self, sim, db):
        carrier = make_carrier(db, delay_prob=1.0)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.01):
            with patch("app.simulation.random.uniform", return_value=4.0):
                sim._advance_shipments(db)

        ev = latest(db, EventType.shipment_delayed)
        assert ev is not None
        data = json.loads(ev.payload)
        assert "new_eta" in data
        assert data["carrier"] == carrier.carrier_id


# ═══════════════════════════════════════════════════════════════════════════════
# warehouse_load_update
# ═══════════════════════════════════════════════════════════════════════════════

class TestWarehouseLoadUpdateEvent:

    def test_payload_contains_score_and_load(self, sim, db):
        wh = make_warehouse(db, capacity=1000, load=100)
        db.commit()

        with patch("app.simulation.random.randint", side_effect=[-10, 1]):
            sim._fluctuate_warehouses(db)

        ev = latest(db, EventType.warehouse_load_update)
        assert ev is not None
        data = json.loads(ev.payload)
        assert "congestion_score" in data
        assert "current_load" in data

    def test_entity_id_matches_warehouse(self, sim, db):
        wh = make_warehouse(db, capacity=1000, load=100)
        db.commit()

        with patch("app.simulation.random.randint", side_effect=[-10, 1]):
            sim._fluctuate_warehouses(db)

        ev = latest(db, EventType.warehouse_load_update)
        assert ev.entity_id == wh.warehouse_id


# ═══════════════════════════════════════════════════════════════════════════════
# warehouse_congestion
# ═══════════════════════════════════════════════════════════════════════════════

class TestWarehouseCongestionEvent:

    def test_congestion_score_in_payload_exceeds_threshold(self, sim, db):
        wh = make_warehouse(db, capacity=100, load=99)
        db.commit()

        with patch("app.simulation.random.randint", side_effect=[1, 1]):
            sim._fluctuate_warehouses(db)

        ev = latest(db, EventType.warehouse_congestion)
        assert ev is not None
        data = json.loads(ev.payload)
        assert data["congestion_score"] > 0.85
        assert "capacity" in data

    def test_current_load_consistent_with_score(self, sim, db):
        wh = make_warehouse(db, capacity=100, load=99)
        db.commit()

        with patch("app.simulation.random.randint", side_effect=[1, 1]):
            sim._fluctuate_warehouses(db)

        ev = latest(db, EventType.warehouse_congestion)
        data = json.loads(ev.payload)
        expected = round(data["current_load"] / data["capacity"], 3)
        assert data["congestion_score"] == pytest.approx(expected, abs=0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# route_traffic_update
# ═══════════════════════════════════════════════════════════════════════════════

class TestRouteTrafficUpdateEvent:

    def test_payload_contains_traffic_and_weather(self, sim, db):
        route = make_route(db)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            with patch("app.simulation.random.choice", return_value=TrafficLevel.high):
                with patch("app.simulation.random.uniform", return_value=0.0):
                    sim._fluctuate_routes(db)

        ev = latest(db, EventType.route_traffic_update)
        assert ev is not None
        data = json.loads(ev.payload)
        assert data["traffic_level"] == "high"
        assert "weather_factor" in data

    def test_entity_id_matches_route(self, sim, db):
        route = make_route(db)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            with patch("app.simulation.random.choice", return_value=TrafficLevel.low):
                with patch("app.simulation.random.uniform", return_value=0.0):
                    sim._fluctuate_routes(db)

        ev = latest(db, EventType.route_traffic_update)
        assert ev.entity_id == route.route_id


# ═══════════════════════════════════════════════════════════════════════════════
# eta_drift
# ═══════════════════════════════════════════════════════════════════════════════

class TestEtaDriftEvent:

    def test_payload_contains_drift_hours_and_new_eta(self, sim, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.05):
            with patch("app.simulation.random.uniform", return_value=3.0):
                sim._random_disruption(db)

        ev = latest(db, EventType.eta_drift)
        assert ev is not None
        data = json.loads(ev.payload)
        assert data["drift_hours"] == pytest.approx(3.0, abs=0.01)
        assert "new_eta" in data

    def test_no_eta_drift_when_no_in_transit_shipments(self, sim, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.05):
            sim._random_disruption(db)

        assert db.query(SimulationEvent).filter_by(event_type=EventType.eta_drift).count() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# pickup_failure
# ═══════════════════════════════════════════════════════════════════════════════

class TestPickupFailureEvent:

    def test_pickup_failure_event_emitted(self, sim, db):
        carrier = make_carrier(db, pickup_rate=0.95)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.15):
            sim._random_disruption(db)

        ev = latest(db, EventType.pickup_failure)
        assert ev is not None

    def test_pickup_success_rate_floor(self, sim, db):
        carrier = make_carrier(db, pickup_rate=0.51)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        for _ in range(30):
            with patch("app.simulation.random.random", return_value=0.15):
                sim._random_disruption(db)

        assert carrier.pickup_success_rate >= 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# carrier_delay_event
# ═══════════════════════════════════════════════════════════════════════════════

class TestCarrierDelayEvent:

    def test_carrier_delay_event_emitted(self, sim, db):
        make_carrier(db, reliability=0.9)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.22):
            sim._random_disruption(db)

        ev = latest(db, EventType.carrier_delay_event)
        assert ev is not None
        data = json.loads(ev.payload)
        assert "reliability_score" in data
        assert "delay_probability" in data

    def test_delay_probability_ceiling(self, sim, db):
        carrier = make_carrier(db, delay_prob=0.58)
        db.commit()

        for _ in range(30):
            with patch("app.simulation.random.random", return_value=0.22):
                sim._random_disruption(db)

        assert carrier.delay_probability <= 0.6
