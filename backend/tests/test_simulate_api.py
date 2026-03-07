"""
Tests for all POST simulation control endpoints:
  POST /api/simulate/start
  POST /api/simulate/stop
  GET  /api/simulate/status
  POST /api/simulate/warehouse-congestion
  POST /api/simulate/carrier-failure
  POST /api/simulate/traffic-spike
  POST /api/simulate/pickup-failure
  POST /api/simulate/eta-drift
  POST /api/simulate/create-shipment
"""

import json

import pytest

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
from tests.conftest import (
    make_carrier,
    make_route,
    make_shipment,
    make_warehouse,
    seed_full,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Engine control endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineControl:

    def test_start_returns_ok(self, client, db):
        resp = client.post("/api/simulate/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_stop_returns_ok(self, client, db):
        client.post("/api/simulate/start")
        resp = client.post("/api/simulate/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_status_shape(self, client, db):
        seed_full(db)
        resp = client.get("/api/simulate/status")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("running", "sim_time", "total_events",
                      "shipment_count", "warehouse_count", "carrier_count", "route_count"):
            assert field in data, f"Missing: {field}"

    def test_status_counts_match_db(self, client, db):
        seed_full(db, n_carriers=2, n_warehouses=2, n_routes=2, n_shipments=4)
        data = client.get("/api/simulate/status").json()
        assert data["shipment_count"] == 4
        assert data["warehouse_count"] == 2
        assert data["carrier_count"] == 2
        assert data["route_count"] == 2

    def test_status_total_events_reflects_db(self, client, db):
        ev = SimulationEvent(event_type=EventType.eta_drift, entity_id="SH-x", payload="{}", sim_time=0)
        db.add(ev)
        db.commit()

        data = client.get("/api/simulate/status").json()
        assert data["total_events"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/simulate/warehouse-congestion
# ═══════════════════════════════════════════════════════════════════════════════

class TestWarehouseCongestionEndpoint:

    def test_returns_ok(self, client, db):
        make_warehouse(db)
        db.commit()
        resp = client.post("/api/simulate/warehouse-congestion")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_events_generated_count(self, client, db):
        make_warehouse(db)
        make_warehouse(db)
        db.commit()

        resp = client.post("/api/simulate/warehouse-congestion")
        data = resp.json()
        assert data["events_generated"] >= 1

    def test_warehouse_congestion_events_in_db(self, client, db):
        make_warehouse(db)
        db.commit()

        client.post("/api/simulate/warehouse-congestion")

        events = db.query(SimulationEvent).filter_by(event_type=EventType.warehouse_congestion).all()
        assert len(events) >= 1

    def test_congestion_score_exceeds_threshold_after_trigger(self, client, db):
        wh = make_warehouse(db, capacity=500)
        db.commit()

        client.post("/api/simulate/warehouse-congestion")
        db.refresh(wh)

        assert wh.congestion_score > 0.85

    def test_congestion_score_in_event_payload(self, client, db):
        make_warehouse(db, capacity=500)
        db.commit()

        client.post("/api/simulate/warehouse-congestion")

        ev = db.query(SimulationEvent).filter_by(
            event_type=EventType.warehouse_congestion
        ).first()
        data = json.loads(ev.payload)
        assert data["scenario"] == "manual_trigger"
        assert "congestion_score" in data

    def test_no_warehouses_returns_error(self, client, db):
        resp = client.post("/api/simulate/warehouse-congestion")
        assert resp.json()["status"] == "error"
        assert resp.json()["events_generated"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/simulate/carrier-failure
# ═══════════════════════════════════════════════════════════════════════════════

class TestCarrierFailureEndpoint:

    def test_returns_ok(self, client, db):
        make_carrier(db)
        db.commit()
        resp = client.post("/api/simulate/carrier-failure")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_carrier_reliability_decreases(self, client, db):
        carrier = make_carrier(db, reliability=0.9)
        db.commit()
        original = carrier.reliability_score

        client.post("/api/simulate/carrier-failure")
        db.refresh(carrier)

        assert carrier.reliability_score < original

    def test_carrier_delay_probability_increases(self, client, db):
        carrier = make_carrier(db, delay_prob=0.1)
        db.commit()
        original = carrier.delay_probability

        client.post("/api/simulate/carrier-failure")
        db.refresh(carrier)

        assert carrier.delay_probability > original

    def test_in_transit_shipments_get_delayed(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        client.post("/api/simulate/carrier-failure")
        db.refresh(ship)

        assert ship.status == ShipmentStatus.delayed

    def test_dispatched_shipments_get_delayed(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.dispatched)
        db.commit()

        client.post("/api/simulate/carrier-failure")
        db.refresh(ship)

        assert ship.status == ShipmentStatus.delayed

    def test_carrier_failure_event_in_db(self, client, db):
        make_carrier(db)
        db.commit()

        client.post("/api/simulate/carrier-failure")

        ev = db.query(SimulationEvent).filter_by(event_type=EventType.carrier_failure).first()
        assert ev is not None
        data = json.loads(ev.payload)
        assert data["scenario"] == "manual_trigger"
        assert "affected_shipments" in data

    def test_shipment_delayed_events_emitted(self, client, db):
        carrier = make_carrier(db)
        # Two in-transit shipments using the same carrier
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        resp = client.post("/api/simulate/carrier-failure")
        data = resp.json()
        # 1 carrier_failure event + 2 shipment_delayed events
        assert data["events_generated"] >= 3

    def test_no_carriers_returns_error(self, client, db):
        resp = client.post("/api/simulate/carrier-failure")
        assert resp.json()["status"] == "error"

    def test_response_contains_carrier_details(self, client, db):
        make_carrier(db, name="BrokenFreight")
        db.commit()

        data = client.post("/api/simulate/carrier-failure").json()
        assert "details" in data
        assert "carrier_id" in data["details"]
        assert "carrier_name" in data["details"]

    def test_eta_is_pushed_forward_for_delayed_shipments(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        original_eta = ship.eta
        db.commit()

        client.post("/api/simulate/carrier-failure")
        db.refresh(ship)

        assert ship.eta > original_eta


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/simulate/traffic-spike
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrafficSpikeEndpoint:

    def test_returns_ok(self, client, db):
        make_route(db)
        db.commit()
        resp = client.post("/api/simulate/traffic-spike")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_routes_set_to_severe(self, client, db):
        r1 = make_route(db, traffic=TrafficLevel.low)
        r2 = make_route(db, traffic=TrafficLevel.moderate)
        r3 = make_route(db, traffic=TrafficLevel.high)
        db.commit()

        client.post("/api/simulate/traffic-spike")
        for route in (r1, r2, r3):
            db.refresh(route)

        # All 3 routes exist and at least some should be severe
        severe_count = sum(
            1 for r in (r1, r2, r3) if r.traffic_level == TrafficLevel.severe
        )
        assert severe_count >= 1

    def test_weather_factor_increases(self, client, db):
        route = make_route(db, weather=1.0)
        db.commit()
        original_weather = route.weather_factor

        client.post("/api/simulate/traffic-spike")
        db.refresh(route)

        assert route.weather_factor >= original_weather  # can only increase

    def test_route_traffic_update_events_in_db(self, client, db):
        make_route(db)
        db.commit()

        client.post("/api/simulate/traffic-spike")

        events = db.query(SimulationEvent).filter_by(event_type=EventType.route_traffic_update).all()
        assert len(events) >= 1

    def test_in_transit_shipments_on_affected_routes_get_eta_drift(self, client, db):
        carrier = make_carrier(db)
        route = make_route(db)
        ship = make_shipment(db, carrier, route, status=ShipmentStatus.in_transit)
        original_eta = ship.eta
        db.commit()

        client.post("/api/simulate/traffic-spike")
        db.refresh(ship)

        # ship may or may not be on one of the target routes (random sample)
        # so just check eta did not go backwards
        assert ship.eta >= original_eta

    def test_no_routes_returns_error(self, client, db):
        resp = client.post("/api/simulate/traffic-spike")
        assert resp.json()["status"] == "error"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/simulate/pickup-failure
# ═══════════════════════════════════════════════════════════════════════════════

class TestPickupFailureEndpoint:

    def test_returns_ok(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        resp = client.post("/api/simulate/pickup-failure")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_shipment_status_becomes_failed(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        client.post("/api/simulate/pickup-failure")
        db.refresh(ship)

        assert ship.status == ShipmentStatus.failed

    def test_pickup_failure_event_in_db(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.dispatched)
        db.commit()

        client.post("/api/simulate/pickup-failure")

        ev = db.query(SimulationEvent).filter_by(event_type=EventType.pickup_failure).first()
        assert ev is not None
        data = json.loads(ev.payload)
        assert data["scenario"] == "manual_trigger"

    def test_carrier_pickup_rate_decreases(self, client, db):
        carrier = make_carrier(db, pickup_rate=0.95)
        make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()
        original_rate = carrier.pickup_success_rate

        client.post("/api/simulate/pickup-failure")
        db.refresh(carrier)

        assert carrier.pickup_success_rate < original_rate

    def test_events_generated_equals_1(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        data = client.post("/api/simulate/pickup-failure").json()
        assert data["events_generated"] == 1

    def test_response_details_contains_shipment_id(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.created)
        db.commit()

        data = client.post("/api/simulate/pickup-failure").json()
        assert "shipment_id" in data["details"]

    def test_no_eligible_shipments_returns_error(self, client, db):
        carrier = make_carrier(db)
        # Only delivered shipments — not eligible
        make_shipment(db, carrier, status=ShipmentStatus.delivered)
        db.commit()

        resp = client.post("/api/simulate/pickup-failure")
        assert resp.json()["status"] == "error"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/simulate/eta-drift
# ═══════════════════════════════════════════════════════════════════════════════

class TestEtaDriftEndpoint:

    def test_returns_ok(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        resp = client.post("/api/simulate/eta-drift")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_eta_pushed_forward(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        original_eta = ship.eta
        db.commit()

        client.post("/api/simulate/eta-drift")
        db.refresh(ship)

        assert ship.eta > original_eta

    def test_eta_drift_events_in_db(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        client.post("/api/simulate/eta-drift")

        events = db.query(SimulationEvent).filter_by(event_type=EventType.eta_drift).all()
        assert len(events) >= 1

    def test_events_generated_up_to_3(self, client, db):
        carrier = make_carrier(db)
        for _ in range(5):
            make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        data = client.post("/api/simulate/eta-drift").json()
        assert 1 <= data["events_generated"] <= 3

    def test_eta_drift_payload_has_drift_hours(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        client.post("/api/simulate/eta-drift")

        ev = db.query(SimulationEvent).filter_by(event_type=EventType.eta_drift).first()
        data = json.loads(ev.payload)
        assert "drift_hours" in data
        assert data["drift_hours"] > 0

    def test_no_in_transit_returns_error(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.delivered)
        db.commit()

        resp = client.post("/api/simulate/eta-drift")
        assert resp.json()["status"] == "error"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/simulate/create-shipment
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateShipmentEndpoint:

    def test_returns_ok(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        resp = client.post("/api/simulate/create-shipment")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_shipment_persisted_in_db(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        client.post("/api/simulate/create-shipment")

        assert db.query(Shipment).count() == 1

    def test_new_shipment_status_is_created(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        client.post("/api/simulate/create-shipment")
        ship = db.query(Shipment).first()

        assert ship.status == ShipmentStatus.created

    def test_shipment_created_event_in_db(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        client.post("/api/simulate/create-shipment")

        ev = db.query(SimulationEvent).filter_by(event_type=EventType.shipment_created).first()
        assert ev is not None
        data = json.loads(ev.payload)
        for key in ("origin", "destination", "carrier", "eta", "sla_deadline"):
            assert key in data

    def test_carrier_shipment_count_bumped(self, client, db):
        carrier = make_carrier(db)
        make_route(db)
        db.commit()
        original = carrier.total_shipments

        client.post("/api/simulate/create-shipment")
        db.refresh(carrier)

        assert carrier.total_shipments == original + 1

    def test_sla_deadline_after_eta(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        client.post("/api/simulate/create-shipment")
        ship = db.query(Shipment).first()

        assert ship.sla_deadline > ship.eta

    def test_response_details_contains_shipment_id(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        data = client.post("/api/simulate/create-shipment").json()
        assert "shipment_id" in data["details"]
        assert data["details"]["shipment_id"].startswith("SH-")

    def test_events_generated_equals_1(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        data = client.post("/api/simulate/create-shipment").json()
        assert data["events_generated"] == 1

    def test_no_seed_data_returns_error(self, client, db):
        resp = client.post("/api/simulate/create-shipment")
        assert resp.json()["status"] == "error"

    def test_multiple_shipments_created_independently(self, client, db):
        make_carrier(db)
        make_route(db)
        db.commit()

        client.post("/api/simulate/create-shipment")
        client.post("/api/simulate/create-shipment")

        ships = db.query(Shipment).all()
        assert len(ships) == 2
        ids = {s.shipment_id for s in ships}
        assert len(ids) == 2   # unique IDs
