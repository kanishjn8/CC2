"""
Tests for the SimPy simulation engine (LogisticsSimulation).

All tests call internal methods directly on a fresh LogisticsSimulation instance
wired to an in-memory SQLite session, so no threads or real timers are needed.
"""

import json
import random

import pytest
from unittest.mock import patch

from app.models import (
    CarrierPerformance,
    EventType,
    Route,
    Shipment,
    ShipmentStatus,
    SimulationEvent,
    TrafficLevel,
    WarehouseState,
)
from app.simulation import LogisticsSimulation
from tests.conftest import (
    make_carrier,
    make_route,
    make_shipment,
    make_warehouse,
    seed_full,
)


@pytest.fixture()
def sim():
    """Return a fresh simulation instance (not started)."""
    return LogisticsSimulation(tick_interval=0.01, sim_speed=1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Engine lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineLifecycle:
    def test_initial_state(self, sim):
        assert sim.running is False
        assert sim.sim_time == 0.0
        assert sim.total_events == 0

    def test_start_sets_running(self, sim):
        sim.start()
        assert sim.running is True
        sim.stop()

    def test_double_start_is_idempotent(self, sim):
        sim.start()
        thread_id = id(sim._thread)
        sim.start()                          # second call should be a no-op
        assert id(sim._thread) == thread_id
        sim.stop()

    def test_stop_clears_running(self, sim):
        sim.start()
        sim.stop()
        assert sim.running is False

    def test_events_counter_increments(self, sim, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        before = sim.total_events
        sim._emit(db, EventType.eta_drift, "SH-test", {"drift_hours": 1})
        assert sim.total_events == before + 1


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Shipment lifecycle transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestShipmentLifecycle:

    def test_created_transitions_to_dispatched(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        # Force roll to always dispatch
        with patch("app.simulation.random.random", return_value=0.1):
            sim._advance_shipments(db)

        assert shipment.status == ShipmentStatus.dispatched
        db.flush()
        event = db.query(SimulationEvent).filter_by(
            event_type=EventType.shipment_dispatched,
            entity_id=shipment.shipment_id,
        ).first()
        assert event is not None

    def test_dispatched_transitions_to_in_transit(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.dispatched)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            sim._advance_shipments(db)

        assert shipment.status == ShipmentStatus.in_transit

    def test_in_transit_can_deliver(self, sim, db):
        carrier = make_carrier(db, delay_prob=0.0)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        # roll=0.2 → < 0.25 → delivered branch (delay_prob * 0.5 = 0 so no delay)
        with patch("app.simulation.random.random", return_value=0.2):
            sim._advance_shipments(db)

        assert shipment.status == ShipmentStatus.delivered
        db.flush()
        event = db.query(SimulationEvent).filter_by(
            event_type=EventType.shipment_delivered,
        ).first()
        assert event is not None
        payload = json.loads(event.payload)
        assert "destination" in payload

    def test_in_transit_can_delay(self, sim, db):
        carrier = make_carrier(db, delay_prob=1.0)   # always delays
        shipment = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        original_eta = shipment.eta
        db.commit()

        with patch("app.simulation.random.random", return_value=0.01):
            with patch("app.simulation.random.uniform", return_value=5.0):
                sim._advance_shipments(db)

        assert shipment.status == ShipmentStatus.delayed
        assert shipment.eta > original_eta
        db.flush()
        event = db.query(SimulationEvent).filter_by(
            event_type=EventType.shipment_delayed,
        ).first()
        assert event is not None
        payload = json.loads(event.payload)
        assert "new_eta" in payload
        assert payload["carrier"] == carrier.carrier_id

    def test_delay_increments_carrier_total_delays(self, sim, db):
        carrier = make_carrier(db, delay_prob=1.0)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        before_delays = carrier.total_delays
        with patch("app.simulation.random.random", return_value=0.01):
            with patch("app.simulation.random.uniform", return_value=3.0):
                sim._advance_shipments(db)

        assert carrier.total_delays == before_delays + 1

    def test_delayed_can_resume_transit(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.delayed)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            sim._advance_shipments(db)

        assert shipment.status == ShipmentStatus.in_transit

    def test_delivered_shipments_are_skipped(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.delivered)
        db.commit()

        sim._advance_shipments(db)

        # Status must remain delivered — no transition
        assert shipment.status == ShipmentStatus.delivered

    def test_failed_shipments_are_skipped(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.failed)
        db.commit()

        sim._advance_shipments(db)

        assert shipment.status == ShipmentStatus.failed

    def test_multiple_shipments_processed_independently(self, sim, db):
        carrier = make_carrier(db, delay_prob=0.0)
        s1 = make_shipment(db, carrier, status=ShipmentStatus.created)
        s2 = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        rolls = iter([0.1, 0.2])   # s1 → dispatch (0.1<0.4), s2 → deliver (0.2<0.25)
        with patch("app.simulation.random.random", side_effect=rolls):
            sim._advance_shipments(db)

        assert s1.status == ShipmentStatus.dispatched
        assert s2.status == ShipmentStatus.delivered


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Warehouse fluctuations
# ═══════════════════════════════════════════════════════════════════════════════

class TestWarehouseFluctuations:

    def test_load_stays_within_bounds(self, sim, db):
        wh = make_warehouse(db, capacity=500, load=490)
        db.commit()

        for _ in range(20):
            sim._fluctuate_warehouses(db)

        assert 0 <= wh.current_load <= wh.capacity

    def test_load_never_goes_negative(self, sim, db):
        wh = make_warehouse(db, capacity=500, load=0)
        db.commit()

        for _ in range(20):
            sim._fluctuate_warehouses(db)

        assert wh.current_load >= 0

    def test_congestion_score_calculated_correctly(self, sim, db):
        wh = make_warehouse(db, capacity=400, load=200)
        db.commit()

        sim._fluctuate_warehouses(db)

        assert wh.congestion_score == pytest.approx(
            wh.current_load / wh.capacity, abs=0.001
        )

    def test_congestion_event_emitted_when_score_above_threshold(self, sim, db):
        wh = make_warehouse(db, capacity=100, load=99)
        db.commit()

        # Force delta_load = +1 so score stays at 1.0 → congestion path
        with patch("app.simulation.random.randint", side_effect=[1, 1]):
            sim._fluctuate_warehouses(db)

        db.flush()
        ev = db.query(SimulationEvent).filter_by(
            event_type=EventType.warehouse_congestion,
            entity_id=wh.warehouse_id,
        ).first()
        assert ev is not None
        payload = json.loads(ev.payload)
        assert payload["congestion_score"] > 0.85

    def test_load_update_event_emitted_when_not_congested(self, sim, db):
        wh = make_warehouse(db, capacity=1000, load=100)
        db.commit()

        with patch("app.simulation.random.randint", side_effect=[-10, 1]):
            sim._fluctuate_warehouses(db)

        db.flush()
        ev = db.query(SimulationEvent).filter_by(
            event_type=EventType.warehouse_load_update,
            entity_id=wh.warehouse_id,
        ).first()
        assert ev is not None

    def test_queue_length_never_goes_negative(self, sim, db):
        wh = make_warehouse(db, capacity=500, load=100, queue=0)
        db.commit()

        for _ in range(10):
            sim._fluctuate_warehouses(db)

        assert wh.queue_length >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Route fluctuations
# ═══════════════════════════════════════════════════════════════════════════════

class TestRouteFluctuations:

    def test_route_traffic_level_updated(self, sim, db):
        route = make_route(db, traffic=TrafficLevel.low)
        db.commit()

        # Ensure the 0.25 threshold is always crossed
        with patch("app.simulation.random.random", return_value=0.1):
            with patch("app.simulation.random.choice", return_value=TrafficLevel.severe):
                with patch("app.simulation.random.uniform", return_value=0.1):
                    sim._fluctuate_routes(db)

        assert route.traffic_level == TrafficLevel.severe

    def test_route_traffic_event_emitted(self, sim, db):
        route = make_route(db)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            with patch("app.simulation.random.choice", return_value=TrafficLevel.high):
                with patch("app.simulation.random.uniform", return_value=0.0):
                    sim._fluctuate_routes(db)

        db.flush()
        ev = db.query(SimulationEvent).filter_by(
            event_type=EventType.route_traffic_update,
            entity_id=route.route_id,
        ).first()
        assert ev is not None

    def test_weather_factor_clamped_to_max(self, sim, db):
        route = make_route(db, weather=1.95)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            with patch("app.simulation.random.choice", return_value=TrafficLevel.low):
                with patch("app.simulation.random.uniform", return_value=0.2):
                    sim._fluctuate_routes(db)

        assert route.weather_factor <= 2.0

    def test_weather_factor_clamped_to_min(self, sim, db):
        route = make_route(db, weather=0.55)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            with patch("app.simulation.random.choice", return_value=TrafficLevel.low):
                with patch("app.simulation.random.uniform", return_value=-0.2):
                    sim._fluctuate_routes(db)

        assert route.weather_factor >= 0.5

    def test_no_update_below_threshold(self, sim, db):
        route = make_route(db, traffic=TrafficLevel.moderate)
        db.commit()

        # roll > 0.25 → no update
        with patch("app.simulation.random.random", return_value=0.9):
            sim._fluctuate_routes(db)

        assert route.traffic_level == TrafficLevel.moderate


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Random disruptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestRandomDisruptions:

    def test_eta_drift_applied_to_in_transit_shipment(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        original_eta = shipment.eta
        db.commit()

        with patch("app.simulation.random.random", return_value=0.05):
            with patch("app.simulation.random.uniform", return_value=3.0):
                sim._random_disruption(db)

        assert shipment.eta > original_eta
        db.flush()
        ev = db.query(SimulationEvent).filter_by(event_type=EventType.eta_drift).first()
        assert ev is not None
        payload = json.loads(ev.payload)
        assert payload["drift_hours"] == pytest.approx(3.0, abs=0.01)

    def test_pickup_failure_degrades_carrier(self, sim, db):
        carrier = make_carrier(db, pickup_rate=0.95)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        original_rate = carrier.pickup_success_rate

        with patch("app.simulation.random.random", return_value=0.11):
            sim._random_disruption(db)

        assert carrier.pickup_success_rate < original_rate

    def test_carrier_delay_event_reduces_reliability(self, sim, db):
        carrier = make_carrier(db, reliability=0.9)
        db.commit()
        original_reliability = carrier.reliability_score

        with patch("app.simulation.random.random", return_value=0.16):
            sim._random_disruption(db)

        assert carrier.reliability_score < original_reliability

    def test_carrier_delay_event_increases_delay_probability(self, sim, db):
        carrier = make_carrier(db, delay_prob=0.1)
        db.commit()
        original_prob = carrier.delay_probability

        with patch("app.simulation.random.random", return_value=0.16):
            sim._random_disruption(db)

        assert carrier.delay_probability > original_prob

    def test_reliability_score_never_goes_below_minimum(self, sim, db):
        carrier = make_carrier(db, reliability=0.31)
        db.commit()

        for _ in range(50):
            with patch("app.simulation.random.random", return_value=0.16):
                sim._random_disruption(db)

        assert carrier.reliability_score >= 0.3

    def test_no_disruption_above_threshold(self, sim, db):
        carrier = make_carrier(db)
        shipment = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()
        original_eta = shipment.eta

        # roll > 0.18 → none of the disruption branches fire
        with patch("app.simulation.random.random", return_value=0.99):
            sim._random_disruption(db)

        assert shipment.eta == original_eta
        assert db.query(SimulationEvent).count() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Full tick integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullTick:

    def test_tick_generates_events(self, sim, db):
        seed_full(db)

        sim._tick(db)
        db.commit()

        assert db.query(SimulationEvent).count() > 0

    def test_tick_does_not_raise_with_empty_db(self, sim, db):
        """Engine should be resilient when tables are empty."""
        sim._tick(db)   # must not raise

    def test_multiple_ticks_accumulate_events(self, sim, db):
        seed_full(db)

        for _ in range(5):
            sim._tick(db)
            db.commit()

        assert db.query(SimulationEvent).count() >= 5

    def test_event_payload_is_valid_json(self, sim, db):
        seed_full(db)
        sim._tick(db)
        db.commit()

        for ev in db.query(SimulationEvent).all():
            if ev.payload:
                parsed = json.loads(ev.payload)
                assert isinstance(parsed, dict)

    def test_event_sim_time_is_recorded(self, sim, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        with patch("app.simulation.random.random", return_value=0.1):
            sim._advance_shipments(db)

        db.flush()
        ev = db.query(SimulationEvent).first()
        assert ev is not None
        assert ev.sim_time == sim.sim_time
