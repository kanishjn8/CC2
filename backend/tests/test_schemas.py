"""
Tests for Pydantic schemas — validation, defaults, and serialisation.
"""

from datetime import datetime

import pytest

from app.schemas import (
    ShipmentOut,
    WarehouseOut,
    CarrierOut,
    RouteOut,
    EventOut,
    SimulationResponse,
    SimStatusResponse,
    DecisionLogOut,
    AgentMetricsOut,
    AgentStatusOut,
    GeoJSONPoint,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
)


class TestShipmentOut:

    def test_minimum_fields(self):
        s = ShipmentOut(
            shipment_id="SH-001",
            origin="Mumbai",
            destination="Delhi",
            carrier="CR-001",
            eta=datetime(2026, 3, 8, 10, 0),
            sla_deadline=datetime(2026, 3, 8, 18, 0),
            status="in_transit",
        )
        assert s.shipment_id == "SH-001"
        assert s.carrier_name is None
        assert s.is_active is True

    def test_carrier_name_optional(self):
        s = ShipmentOut(
            shipment_id="SH-002",
            origin="A",
            destination="B",
            carrier="CR-x",
            carrier_name="FastFreight",
            eta=datetime.now(),
            sla_deadline=datetime.now(),
            status="created",
        )
        assert s.carrier_name == "FastFreight"

    def test_from_attributes_mode(self):
        """ConfigDict(from_attributes=True) must be set."""
        assert ShipmentOut.model_config.get("from_attributes") is True


class TestWarehouseOut:

    def test_basic(self):
        w = WarehouseOut(
            warehouse_id="WH-001",
            location="Pune",
            capacity=500,
            current_load=100,
            queue_length=5,
            congestion_score=0.2,
        )
        assert w.warehouse_id == "WH-001"
        assert w.updated_at is None

    def test_from_attributes_mode(self):
        assert WarehouseOut.model_config.get("from_attributes") is True


class TestCarrierOut:

    def test_basic(self):
        c = CarrierOut(
            carrier_id="CR-001",
            name="TestCarrier",
            reliability_score=0.9,
            delay_probability=0.1,
            pickup_success_rate=0.95,
            total_shipments=100,
            total_delays=10,
        )
        assert c.name == "TestCarrier"

    def test_from_attributes_mode(self):
        assert CarrierOut.model_config.get("from_attributes") is True


class TestRouteOut:

    def test_basic(self):
        r = RouteOut(
            route_id="RT-001",
            origin="Mumbai",
            destination="Delhi",
            distance=1400.0,
            traffic_level="low",
            weather_factor=1.0,
        )
        assert r.distance == 1400.0

    def test_from_attributes_mode(self):
        assert RouteOut.model_config.get("from_attributes") is True


class TestEventOut:

    def test_basic(self):
        e = EventOut(
            id=1,
            event_type="eta_drift",
            entity_id="SH-001",
            payload='{"drift_hours": 2.0}',
            sim_time=10.0,
        )
        assert e.event_type == "eta_drift"

    def test_nullable_fields(self):
        e = EventOut(
            id=2,
            event_type="shipment_created",
            entity_id="SH-002",
        )
        assert e.payload is None
        assert e.sim_time is None


class TestSimulationResponse:

    def test_defaults(self):
        r = SimulationResponse(status="ok", message="done")
        assert r.events_generated == 0
        assert r.details is None

    def test_with_details(self):
        r = SimulationResponse(
            status="ok",
            message="done",
            events_generated=3,
            details={"carrier_id": "CR-001"},
        )
        assert r.details["carrier_id"] == "CR-001"


class TestSimStatusResponse:

    def test_all_fields(self):
        s = SimStatusResponse(
            running=True,
            sim_time=123.45,
            total_events=50,
            shipment_count=10,
            warehouse_count=5,
            carrier_count=3,
            route_count=8,
        )
        assert s.running is True
        assert s.total_events == 50


class TestDecisionLogOut:

    def test_required_fields(self):
        d = DecisionLogOut(
            id=1,
            decision_id="DEC-ABC123",
            risk_type="delay_risk",
            entity_id="SH-001",
            risk_score=0.8,
            problem="Shipment likely to miss SLA",
            root_cause="High traffic",
            confidence=0.9,
            recommended_action="reroute_shipment",
            requires_approval=False,
            status="executed",
            outcome="pending",
        )
        assert d.decision_id == "DEC-ABC123"
        assert d.shipment_id is None


class TestGeoJSONSchemas:

    def test_point(self):
        p = GeoJSONPoint(coordinates=[72.8777, 19.076])
        assert p.type == "Point"
        assert len(p.coordinates) == 2

    def test_feature(self):
        f = GeoJSONFeature(
            geometry={"type": "Point", "coordinates": [72.8777, 19.076]},
            properties={"name": "Mumbai"},
        )
        assert f.type == "Feature"

    def test_feature_collection_empty(self):
        fc = GeoJSONFeatureCollection()
        assert fc.type == "FeatureCollection"
        assert fc.features == []

    def test_feature_collection_with_features(self):
        fc = GeoJSONFeatureCollection(features=[
            GeoJSONFeature(properties={"id": 1}),
            GeoJSONFeature(properties={"id": 2}),
        ])
        assert len(fc.features) == 2


class TestAgentMetricsOut:

    def test_basic(self):
        m = AgentMetricsOut(
            total_decisions=10,
            intervention_success_rate=0.8,
            false_positive_rate=0.05,
            average_confidence=0.85,
            outcomes={"pending": 2, "success": 6, "failed": 2},
            actions_breakdown={"reroute_shipment": 5, "send_alert": 5},
            risk_type_breakdown={"delay_risk": 10},
        )
        assert m.total_decisions == 10


class TestAgentStatusOut:

    def test_basic(self):
        s = AgentStatusOut(
            running=True,
            cycle_count=5,
            model_trained=True,
            total_decisions=20,
            pending_approvals=2,
        )
        assert s.running is True
