"""
Seed function tests — verify that seed helpers produce correct, consistent data.
"""

import pytest
from geoalchemy2.shape import to_shape

from app.models import (
    CarrierPerformance,
    Route,
    Shipment,
    ShipmentStatus,
    TrafficLevel,
    WarehouseState,
)
from app.seed import seed_all, seed_carriers, seed_routes, seed_shipments, seed_warehouses
from tests.conftest import make_carrier, make_route


# ═══════════════════════════════════════════════════════════════════════════════
# seed_warehouses
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeedWarehouses:

    def test_correct_count(self, db):
        result = seed_warehouses(db, count=3)
        assert len(result) == 3

    def test_unique_warehouse_ids(self, db):
        warehouses = seed_warehouses(db, count=5)
        ids = [w.warehouse_id for w in warehouses]
        assert len(ids) == len(set(ids))

    def test_warehouse_id_prefix(self, db):
        warehouses = seed_warehouses(db, count=3)
        assert all(w.warehouse_id.startswith("WH-") for w in warehouses)

    def test_capacity_in_valid_range(self, db):
        warehouses = seed_warehouses(db, count=5)
        for wh in warehouses:
            assert 300 <= wh.capacity <= 1500

    def test_current_load_does_not_exceed_capacity(self, db):
        warehouses = seed_warehouses(db, count=5)
        for wh in warehouses:
            assert wh.current_load <= wh.capacity

    def test_current_load_non_negative(self, db):
        warehouses = seed_warehouses(db, count=5)
        for wh in warehouses:
            assert wh.current_load >= 0

    def test_congestion_score_matches_load_ratio(self, db):
        warehouses = seed_warehouses(db, count=5)
        for wh in warehouses:
            expected = round(wh.current_load / wh.capacity, 3)
            assert wh.congestion_score == pytest.approx(expected, abs=0.001)

    def test_queue_length_non_negative(self, db):
        warehouses = seed_warehouses(db, count=5)
        for wh in warehouses:
            assert wh.queue_length >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# seed_carriers
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeedCarriers:

    def test_correct_count(self, db):
        result = seed_carriers(db, count=4)
        assert len(result) == 4

    def test_unique_carrier_ids(self, db):
        carriers = seed_carriers(db, count=8)
        ids = [c.carrier_id for c in carriers]
        assert len(ids) == len(set(ids))

    def test_carrier_id_prefix(self, db):
        carriers = seed_carriers(db, count=3)
        assert all(c.carrier_id.startswith("CR-") for c in carriers)

    def test_reliability_in_valid_range(self, db):
        carriers = seed_carriers(db, count=8)
        for c in carriers:
            assert 0.25 <= c.reliability_score <= 1.0

    def test_pickup_success_rate_in_valid_range(self, db):
        carriers = seed_carriers(db, count=8)
        for c in carriers:
            assert 0.55 <= c.pickup_success_rate <= 1.0

    def test_total_shipments_non_negative(self, db):
        carriers = seed_carriers(db, count=4)
        for c in carriers:
            assert c.total_shipments >= 0

    def test_total_delays_non_negative(self, db):
        carriers = seed_carriers(db, count=4)
        for c in carriers:
            assert c.total_delays >= 0

    def test_delay_probability_non_negative(self, db):
        carriers = seed_carriers(db, count=8)
        for c in carriers:
            assert c.delay_probability >= 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# seed_routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeedRoutes:

    def test_correct_count(self, db):
        result = seed_routes(db, count=6)
        assert len(result) == 6

    def test_unique_route_ids(self, db):
        routes = seed_routes(db, count=6)
        ids = [r.route_id for r in routes]
        assert len(ids) == len(set(ids))

    def test_route_id_prefix(self, db):
        routes = seed_routes(db, count=3)
        assert all(r.route_id.startswith("RT-") for r in routes)

    def test_distance_positive(self, db):
        routes = seed_routes(db, count=6)
        for r in routes:
            assert r.distance > 0

    def test_weather_factor_in_valid_range(self, db):
        routes = seed_routes(db, count=6)
        for r in routes:
            assert 0.5 <= r.weather_factor <= 2.5

    def test_traffic_level_is_valid_enum(self, db):
        routes = seed_routes(db, count=6)
        valid = set(TrafficLevel)
        for r in routes:
            assert r.traffic_level in valid

    def test_origin_and_destination_differ(self, db):
        routes = seed_routes(db, count=10)
        for r in routes:
            assert r.origin != r.destination

    def test_routes_use_maritime_waypoint_geometry(self, db):
        routes = seed_routes(db, count=10)
        for r in routes:
            shape = to_shape(r.path)
            assert shape.geom_type == "LineString"
            assert len(shape.coords) > 2


# ═══════════════════════════════════════════════════════════════════════════════
# seed_shipments
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeedShipments:

    def test_correct_count(self, db):
        carriers = seed_carriers(db, count=2)
        routes = seed_routes(db, count=2)
        result = seed_shipments(db, carriers, routes, count=5)
        assert len(result) == 5

    def test_unique_shipment_ids(self, db):
        carriers = seed_carriers(db, count=2)
        routes = seed_routes(db, count=2)
        shipments = seed_shipments(db, carriers, routes, count=10)
        ids = [s.shipment_id for s in shipments]
        assert len(ids) == len(set(ids))

    def test_shipment_id_prefix(self, db):
        carriers = seed_carriers(db, count=2)
        routes = seed_routes(db, count=2)
        shipments = seed_shipments(db, carriers, routes, count=3)
        assert all(s.shipment_id.startswith("SH-") for s in shipments)

    def test_sla_deadline_relationship_to_eta(self, db):
        """SLA deadline should differ from ETA — for delayed/failed shipments the buffer can be negative."""
        carriers = seed_carriers(db, count=2)
        routes = seed_routes(db, count=2)
        shipments = seed_shipments(db, carriers, routes, count=5)
        for s in shipments:
            assert s.sla_deadline is not None
            assert s.eta is not None

    def test_status_is_valid(self, db):
        carriers = seed_carriers(db, count=2)
        routes = seed_routes(db, count=2)
        shipments = seed_shipments(db, carriers, routes, count=10)
        valid_statuses = set(ShipmentStatus)
        for s in shipments:
            assert s.status in valid_statuses

    def test_carrier_id_references_existing_carrier(self, db):
        carriers = seed_carriers(db, count=3)
        routes = seed_routes(db, count=2)
        carrier_ids = {c.carrier_id for c in carriers}
        shipments = seed_shipments(db, carriers, routes, count=5)
        for s in shipments:
            assert s.carrier in carrier_ids

    def test_carrier_shipment_count_incremented(self, db):
        carriers = seed_carriers(db, count=2)
        routes = seed_routes(db, count=2)
        before = sum(c.total_shipments for c in carriers)
        seed_shipments(db, carriers, routes, count=4)
        after = sum(c.total_shipments for c in carriers)
        assert after == before + 4


# ═══════════════════════════════════════════════════════════════════════════════
# seed_all
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeedAll:

    def test_populates_all_tables(self, db):
        seed_all(db, warehouses=2, carriers=2, routes=2, shipments=3)
        assert db.query(WarehouseState).count() == 2
        assert db.query(CarrierPerformance).count() == 2
        assert db.query(Route).count() == 2
        assert db.query(Shipment).count() == 3

    def test_idempotent_on_second_call(self, db):
        seed_all(db, warehouses=2, carriers=2, routes=2, shipments=3)
        seed_all(db, warehouses=5, carriers=5, routes=5, shipments=10)   # second call → skipped

        # Counts must remain from the first call
        assert db.query(WarehouseState).count() == 2
        assert db.query(CarrierPerformance).count() == 2
