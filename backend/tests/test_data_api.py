"""
Tests for GET data endpoints:
  GET /api/shipments
  GET /api/shipments/{id}
  GET /api/warehouses
  GET /api/warehouses/{id}
  GET /api/carriers
  GET /api/carriers/{id}
  GET /api/routes
  GET /api/routes/{id}
  GET /api/events
"""

import pytest

from app.models import EventType, ShipmentStatus, SimulationEvent, TrafficLevel
from tests.conftest import (
    make_carrier,
    make_route,
    make_shipment,
    make_warehouse,
    seed_full,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/shipments
# ═══════════════════════════════════════════════════════════════════════════════

class TestListShipments:

    def test_returns_200(self, client, db):
        seed_full(db)
        resp = client.get("/api/shipments")
        assert resp.status_code == 200

    def test_returns_list(self, client, db):
        seed_full(db)
        data = client.get("/api/shipments").json()
        assert isinstance(data, list)

    def test_count_matches_db(self, client, db):
        carriers, _, routes, _ = seed_full(db, n_shipments=4)
        data = client.get("/api/shipments").json()
        assert len(data) == 4

    def test_response_schema(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier)
        db.commit()

        item = client.get("/api/shipments").json()[0]
        for field in ("shipment_id", "origin", "destination", "carrier", "eta", "sla_deadline", "status"):
            assert field in item, f"Missing field: {field}"

    def test_filter_by_status(self, client, db):
        carrier = make_carrier(db)
        make_shipment(db, carrier, status=ShipmentStatus.created)
        make_shipment(db, carrier, status=ShipmentStatus.delivered)
        make_shipment(db, carrier, status=ShipmentStatus.delivered)
        db.commit()

        data = client.get("/api/shipments?status=delivered").json()
        assert len(data) == 2
        assert all(s["status"] == "delivered" for s in data)

    def test_invalid_status_returns_422(self, client, db):
        resp = client.get("/api/shipments?status=flying")
        assert resp.status_code == 422

    def test_limit_parameter(self, client, db):
        carrier = make_carrier(db)
        for _ in range(10):
            make_shipment(db, carrier)
        db.commit()

        data = client.get("/api/shipments?limit=3").json()
        assert len(data) == 3

    def test_limit_below_1_returns_422(self, client, db):
        resp = client.get("/api/shipments?limit=0")
        assert resp.status_code == 422

    def test_empty_db_returns_empty_list(self, client, db):
        data = client.get("/api/shipments").json()
        assert data == []


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/shipments/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetShipment:

    def test_returns_correct_shipment(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier)
        db.commit()

        data = client.get(f"/api/shipments/{ship.shipment_id}").json()
        assert data["shipment_id"] == ship.shipment_id
        assert data["origin"] == ship.origin

    def test_returns_none_for_unknown_id(self, client, db):
        resp = client.get("/api/shipments/SH-doesnotexist")
        assert resp.status_code == 404

    def test_shipment_id_preserved(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier)
        db.commit()

        data = client.get(f"/api/shipments/{ship.shipment_id}").json()
        assert data["shipment_id"] == ship.shipment_id


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/warehouses
# ═══════════════════════════════════════════════════════════════════════════════

class TestListWarehouses:

    def test_returns_200(self, client, db):
        make_warehouse(db)
        db.commit()
        assert client.get("/api/warehouses").status_code == 200

    def test_sorted_by_congestion_descending(self, client, db):
        make_warehouse(db, capacity=100, load=90)   # score 0.9
        make_warehouse(db, capacity=100, load=10)   # score 0.1
        make_warehouse(db, capacity=100, load=50)   # score 0.5
        db.commit()

        scores = [w["congestion_score"] for w in client.get("/api/warehouses").json()]
        assert scores == sorted(scores, reverse=True)

    def test_schema(self, client, db):
        make_warehouse(db)
        db.commit()

        item = client.get("/api/warehouses").json()[0]
        for field in ("warehouse_id", "location", "capacity", "current_load", "queue_length", "congestion_score"):
            assert field in item

    def test_congestion_score_range(self, client, db):
        make_warehouse(db, capacity=200, load=80)
        db.commit()

        data = client.get("/api/warehouses").json()
        for w in data:
            assert 0.0 <= w["congestion_score"] <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/warehouses/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetWarehouse:

    def test_returns_correct_warehouse(self, client, db):
        wh = make_warehouse(db, location="Kochi")
        db.commit()

        data = client.get(f"/api/warehouses/{wh.warehouse_id}").json()
        assert data["warehouse_id"] == wh.warehouse_id
        assert data["location"] == "Kochi"

    def test_unknown_id_returns_null(self, client, db):
        resp = client.get("/api/warehouses/WH-ghost")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/carriers
# ═══════════════════════════════════════════════════════════════════════════════

class TestListCarriers:

    def test_returns_200(self, client, db):
        make_carrier(db)
        db.commit()
        assert client.get("/api/carriers").status_code == 200

    def test_sorted_by_reliability_descending(self, client, db):
        make_carrier(db, reliability=0.6)
        make_carrier(db, reliability=0.95)
        make_carrier(db, reliability=0.8)
        db.commit()

        scores = [c["reliability_score"] for c in client.get("/api/carriers").json()]
        assert scores == sorted(scores, reverse=True)

    def test_schema(self, client, db):
        make_carrier(db)
        db.commit()

        item = client.get("/api/carriers").json()[0]
        for field in ("carrier_id", "name", "reliability_score", "delay_probability",
                      "pickup_success_rate", "total_shipments", "total_delays"):
            assert field in item

    def test_scores_in_valid_range(self, client, db):
        make_carrier(db, reliability=0.85, delay_prob=0.15, pickup_rate=0.92)
        db.commit()

        c = client.get("/api/carriers").json()[0]
        assert 0.0 <= c["reliability_score"] <= 1.0
        assert 0.0 <= c["delay_probability"] <= 1.0
        assert 0.0 <= c["pickup_success_rate"] <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/carriers/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCarrier:

    def test_returns_correct_carrier(self, client, db):
        carrier = make_carrier(db, name="AlphaFreight")
        db.commit()

        data = client.get(f"/api/carriers/{carrier.carrier_id}").json()
        assert data["carrier_id"] == carrier.carrier_id
        assert data["name"] == "AlphaFreight"

    def test_unknown_id_returns_null(self, client, db):
        assert client.get("/api/carriers/CR-ghost").status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestListRoutes:

    def test_returns_200(self, client, db):
        make_route(db)
        db.commit()
        assert client.get("/api/routes").status_code == 200

    def test_count_correct(self, client, db):
        for _ in range(4):
            make_route(db)
        db.commit()

        assert len(client.get("/api/routes").json()) == 4

    def test_schema(self, client, db):
        make_route(db)
        db.commit()

        item = client.get("/api/routes").json()[0]
        for field in ("route_id", "origin", "destination", "distance", "traffic_level", "weather_factor"):
            assert field in item

    def test_distance_is_positive(self, client, db):
        make_route(db, distance=1234.5)
        db.commit()

        data = client.get("/api/routes").json()
        assert all(r["distance"] > 0 for r in data)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/routes/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetRoute:

    def test_returns_correct_route(self, client, db):
        route = make_route(db, origin="Pune", destination="Surat", distance=250.0)
        db.commit()

        data = client.get(f"/api/routes/{route.route_id}").json()
        assert data["origin"] == "Pune"
        assert data["destination"] == "Surat"
        assert data["distance"] == pytest.approx(250.0, abs=0.01)

    def test_unknown_id_returns_null(self, client, db):
        assert client.get("/api/routes/RT-ghost").status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/events
# ═══════════════════════════════════════════════════════════════════════════════

class TestListEvents:

    def _add_event(self, db, event_type=EventType.eta_drift, entity_id="SH-001"):
        ev = SimulationEvent(event_type=event_type, entity_id=entity_id, payload="{}", sim_time=0.0)
        db.add(ev)
        db.flush()
        return ev

    def test_returns_200(self, client, db):
        assert client.get("/api/events").status_code == 200

    def test_returns_all_events(self, client, db):
        self._add_event(db, EventType.eta_drift, "SH-001")
        self._add_event(db, EventType.warehouse_congestion, "WH-001")
        db.commit()

        data = client.get("/api/events").json()
        assert len(data) == 2

    def test_filter_by_event_type(self, client, db):
        self._add_event(db, EventType.eta_drift, "SH-001")
        self._add_event(db, EventType.eta_drift, "SH-002")
        self._add_event(db, EventType.warehouse_congestion, "WH-001")
        db.commit()

        data = client.get("/api/events?event_type=eta_drift").json()
        assert len(data) == 2
        assert all(e["event_type"] == "eta_drift" for e in data)

    def test_filter_by_entity_id(self, client, db):
        self._add_event(db, EventType.eta_drift, "SH-AAA")
        self._add_event(db, EventType.pickup_failure, "SH-AAA")
        self._add_event(db, EventType.eta_drift, "SH-BBB")
        db.commit()

        data = client.get("/api/events?entity_id=SH-AAA").json()
        assert len(data) == 2
        assert all(e["entity_id"] == "SH-AAA" for e in data)

    def test_filter_by_type_and_entity_combined(self, client, db):
        self._add_event(db, EventType.eta_drift, "SH-AAA")
        self._add_event(db, EventType.pickup_failure, "SH-AAA")
        db.commit()

        data = client.get("/api/events?event_type=eta_drift&entity_id=SH-AAA").json()
        assert len(data) == 1
        assert data[0]["event_type"] == "eta_drift"

    def test_limit_parameter(self, client, db):
        for i in range(10):
            self._add_event(db, EventType.eta_drift, f"SH-{i:03d}")
        db.commit()

        data = client.get("/api/events?limit=4").json()
        assert len(data) == 4

    def test_schema(self, client, db):
        self._add_event(db)
        db.commit()

        item = client.get("/api/events").json()[0]
        for field in ("id", "event_type", "entity_id", "payload", "sim_time"):
            assert field in item

    def test_empty_returns_empty_list(self, client, db):
        assert client.get("/api/events").json() == []
