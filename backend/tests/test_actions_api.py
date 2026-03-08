"""
Tests for operational action endpoints:
  POST /api/actions/send-alert
  POST /api/actions/reroute
  POST /api/actions/switch-carrier
"""

import json

import pytest

from app.models import (
    DecisionLog,
    Route,
    Shipment,
    ShipmentStatus,
    TrafficLevel,
)
from tests.conftest import make_carrier, make_route, make_shipment


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/actions/send-alert
# ═══════════════════════════════════════════════════════════════════════════════

class TestSendAlert:

    def test_returns_200(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier)
        db.commit()

        resp = client.post("/api/actions/send-alert", json={
            "shipment_id": ship.shipment_id,
            "risk_score": 0.8,
            "reason": "High delay risk",
        })
        assert resp.status_code == 200

    def test_response_shape(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier)
        db.commit()

        data = client.post("/api/actions/send-alert", json={
            "shipment_id": ship.shipment_id,
        }).json()
        assert data["status"] == "alert_sent"
        assert data["alert_type"] == "risk_alert"
        assert data["shipment_id"] == ship.shipment_id
        assert data["decision_id"] is not None

    def test_creates_decision_log(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier)
        db.commit()

        client.post("/api/actions/send-alert", json={
            "shipment_id": ship.shipment_id,
            "reason": "Test alert",
        })

        dec = db.query(DecisionLog).filter_by(
            recommended_action="send_alert",
        ).first()
        assert dec is not None
        assert dec.status == "executed"
        assert dec.outcome == "completed"

    def test_unknown_shipment_returns_404(self, client, db):
        resp = client.post("/api/actions/send-alert", json={
            "shipment_id": "SH-doesnotexist",
        })
        assert resp.status_code == 404

    def test_custom_message(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier)
        db.commit()

        data = client.post("/api/actions/send-alert", json={
            "shipment_id": ship.shipment_id,
            "message": "Custom alert message",
        }).json()
        assert data["message"] == "Custom alert message"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/actions/reroute
# ═══════════════════════════════════════════════════════════════════════════════

class TestReroute:

    def test_successful_reroute(self, client, db):
        carrier = make_carrier(db)
        route1 = make_route(db, traffic=TrafficLevel.severe, weather=1.8)
        route2 = make_route(db, traffic=TrafficLevel.low, weather=0.9)
        ship = make_shipment(db, carrier, route1, status=ShipmentStatus.in_transit)
        db.commit()

        resp = client.post("/api/actions/reroute", json={
            "shipment_id": ship.shipment_id,
            "reason": "Traffic too high",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rerouted"
        assert data["old_route"] == route1.route_id
        assert data["new_route"] == route2.route_id

    def test_creates_decision_log(self, client, db):
        carrier = make_carrier(db)
        route1 = make_route(db, traffic=TrafficLevel.severe)
        route2 = make_route(db, traffic=TrafficLevel.low)
        ship = make_shipment(db, carrier, route1)
        db.commit()

        client.post("/api/actions/reroute", json={
            "shipment_id": ship.shipment_id,
        })

        dec = db.query(DecisionLog).filter_by(
            recommended_action="reroute_shipment",
        ).first()
        assert dec is not None

    def test_unknown_shipment_returns_404(self, client, db):
        resp = client.post("/api/actions/reroute", json={
            "shipment_id": "SH-ghost",
        })
        assert resp.status_code == 404

    def test_no_better_route_returns_400(self, client, db):
        carrier = make_carrier(db)
        route = make_route(db, traffic=TrafficLevel.low)  # already the best
        ship = make_shipment(db, carrier, route, status=ShipmentStatus.in_transit)
        db.commit()

        resp = client.post("/api/actions/reroute", json={
            "shipment_id": ship.shipment_id,
        })
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/actions/switch-carrier
# ═══════════════════════════════════════════════════════════════════════════════

class TestSwitchCarrier:

    def test_successful_switch(self, client, db):
        bad_carrier = make_carrier(db, name="BadCarrier", reliability=0.3, delay_prob=0.7)
        good_carrier = make_carrier(db, name="GoodCarrier", reliability=0.95, delay_prob=0.05)
        ship = make_shipment(db, bad_carrier, status=ShipmentStatus.in_transit)
        db.commit()

        resp = client.post("/api/actions/switch-carrier", json={
            "shipment_id": ship.shipment_id,
            "reason": "Carrier unreliable",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "carrier_switched"
        assert data["old_carrier"] == bad_carrier.carrier_id
        assert data["new_carrier"] == good_carrier.carrier_id

    def test_creates_decision_log(self, client, db):
        bad_carrier = make_carrier(db, reliability=0.3)
        good_carrier = make_carrier(db, reliability=0.95)
        ship = make_shipment(db, bad_carrier, status=ShipmentStatus.in_transit)
        db.commit()

        client.post("/api/actions/switch-carrier", json={
            "shipment_id": ship.shipment_id,
        })

        dec = db.query(DecisionLog).filter_by(
            recommended_action="switch_carrier",
        ).first()
        assert dec is not None

    def test_unknown_shipment_returns_404(self, client, db):
        resp = client.post("/api/actions/switch-carrier", json={
            "shipment_id": "SH-ghost",
        })
        assert resp.status_code == 404

    def test_no_better_carrier_returns_400(self, client, db):
        # Only one carrier — can't switch
        carrier = make_carrier(db, reliability=0.9)
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit)
        db.commit()

        resp = client.post("/api/actions/switch-carrier", json={
            "shipment_id": ship.shipment_id,
        })
        assert resp.status_code == 400
