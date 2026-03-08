"""
Tests for ORM model enums and DecisionLog model.
"""

import pytest

from app.models import (
    ShipmentStatus,
    TrafficLevel,
    EventType,
    DecisionLog,
    Shipment,
    WarehouseState,
    CarrierPerformance,
    Route,
    SimulationEvent,
)


class TestShipmentStatusEnum:

    def test_all_statuses(self):
        expected = {"created", "dispatched", "in_transit", "at_warehouse",
                    "out_for_delivery", "delivered", "delayed", "failed"}
        assert {s.value for s in ShipmentStatus} == expected

    def test_string_value(self):
        assert ShipmentStatus.created.value == "created"
        assert ShipmentStatus.in_transit.value == "in_transit"

    def test_str_enum_comparison(self):
        """ShipmentStatus(str, enum.Enum) should be comparable with strings."""
        assert ShipmentStatus.delivered == "delivered"


class TestTrafficLevelEnum:

    def test_all_levels(self):
        expected = {"low", "moderate", "high", "severe"}
        assert {t.value for t in TrafficLevel} == expected

    def test_ordering_by_value(self):
        levels = sorted(TrafficLevel, key=lambda t: t.value)
        assert levels[0] == TrafficLevel.high  # alphabetical, not severity


class TestEventTypeEnum:

    def test_count(self):
        assert len(EventType) == 11

    def test_key_event_types_present(self):
        names = {e.name for e in EventType}
        assert "shipment_created" in names
        assert "shipment_delivered" in names
        assert "warehouse_congestion" in names
        assert "carrier_failure" in names
        assert "eta_drift" in names
        assert "pickup_failure" in names


class TestDecisionLogModel:

    def test_table_name(self):
        assert DecisionLog.__tablename__ == "decision_log"

    def test_has_required_columns(self):
        col_names = {c.name for c in DecisionLog.__table__.columns}
        required = {
            "id", "decision_id", "risk_type", "entity_id", "risk_score",
            "problem", "root_cause", "confidence", "recommended_action",
            "requires_approval", "status", "outcome", "created_at",
        }
        assert required.issubset(col_names)


class TestShipmentModel:

    def test_table_name(self):
        assert Shipment.__tablename__ == "shipments"

    def test_has_geo_columns(self):
        col_names = {c.name for c in Shipment.__table__.columns}
        assert "current_location" in col_names
        assert "origin_point" in col_names
        assert "destination_point" in col_names

    def test_has_is_active_column(self):
        col_names = {c.name for c in Shipment.__table__.columns}
        assert "is_active" in col_names


class TestWarehouseModel:

    def test_table_name(self):
        assert WarehouseState.__tablename__ == "warehouse_state"


class TestCarrierModel:

    def test_table_name(self):
        assert CarrierPerformance.__tablename__ == "carrier_performance"


class TestRouteModel:

    def test_table_name(self):
        assert Route.__tablename__ == "routes"

    def test_has_path_column(self):
        col_names = {c.name for c in Route.__table__.columns}
        assert "path" in col_names


class TestSimulationEventModel:

    def test_table_name(self):
        assert SimulationEvent.__tablename__ == "simulation_events"
