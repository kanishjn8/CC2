"""
Tests for agent API endpoints:
  GET  /api/agent/decisions
  GET  /api/agent/decisions/{id}
  GET  /api/agent/metrics
  GET  /api/agent/status
  GET  /api/agent/risks
  GET  /api/agent/graph-info
  GET  /api/agent/summary
  GET  /api/agent/feature-importance
  GET  /api/agent/llm-stats
  POST /api/agent/approve/{id}
"""

import json

import pytest

from app.models import DecisionLog
from tests.conftest import make_carrier, make_shipment


def _add_decision(db, *, decision_id="DEC-TEST001", status="executed",
                  outcome="pending", risk_type="delay_risk", entity_id="SH-001",
                  requires_approval=False):
    dec = DecisionLog(
        decision_id=decision_id,
        risk_type=risk_type,
        entity_id=entity_id,
        shipment_id=entity_id,
        risk_score=0.75,
        problem="Test problem",
        evidence=json.dumps({"test": True}),
        root_cause="Test root cause",
        confidence=0.85,
        recommended_action="reroute_shipment",
        action_details=json.dumps({"route": "RT-001"}),
        requires_approval=requires_approval,
        status=status,
        outcome=outcome,
    )
    db.add(dec)
    db.flush()
    return dec


class TestListDecisions:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/decisions").status_code == 200

    def test_returns_empty_list(self, client, db):
        data = client.get("/api/agent/decisions").json()
        assert data == []

    def test_returns_decisions(self, client, db):
        _add_decision(db)
        db.commit()

        data = client.get("/api/agent/decisions").json()
        assert len(data) == 1
        assert data[0]["decision_id"] == "DEC-TEST001"

    def test_filter_by_risk_type(self, client, db):
        _add_decision(db, decision_id="DEC-1", risk_type="delay_risk")
        _add_decision(db, decision_id="DEC-2", risk_type="bottleneck")
        db.commit()

        data = client.get("/api/agent/decisions?risk_type=bottleneck").json()
        assert len(data) == 1
        assert data[0]["risk_type"] == "bottleneck"

    def test_filter_by_status(self, client, db):
        _add_decision(db, decision_id="DEC-X1", status="executed")
        _add_decision(db, decision_id="DEC-X2", status="pending_approval")
        db.commit()

        data = client.get("/api/agent/decisions?status=pending_approval").json()
        assert len(data) == 1

    def test_filter_by_outcome(self, client, db):
        d1 = _add_decision(db, decision_id="DEC-O1")
        d1.outcome = "success"
        d2 = _add_decision(db, decision_id="DEC-O2")
        d2.outcome = "failed"
        db.commit()

        data = client.get("/api/agent/decisions?outcome=success").json()
        assert len(data) == 1

    def test_limit(self, client, db):
        for i in range(10):
            _add_decision(db, decision_id=f"DEC-L{i:02d}")
        db.commit()

        data = client.get("/api/agent/decisions?limit=3").json()
        assert len(data) == 3


class TestGetDecision:

    def test_returns_correct_decision(self, client, db):
        _add_decision(db, decision_id="DEC-FIND")
        db.commit()

        data = client.get("/api/agent/decisions/DEC-FIND").json()
        assert data["decision_id"] == "DEC-FIND"

    def test_unknown_id_returns_404(self, client, db):
        resp = client.get("/api/agent/decisions/DEC-UNKNOWN")
        assert resp.status_code == 404


class TestAgentMetrics:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/metrics").status_code == 200

    def test_empty_metrics(self, client, db):
        data = client.get("/api/agent/metrics").json()
        assert data["total_decisions"] == 0

    def test_with_decisions(self, client, db):
        d1 = _add_decision(db, decision_id="DEC-M1")
        d1.outcome = "success"
        _add_decision(db, decision_id="DEC-M2")
        db.commit()

        data = client.get("/api/agent/metrics").json()
        assert data["total_decisions"] == 2


class TestAgentStatus:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/status").status_code == 200

    def test_shape(self, client, db):
        data = client.get("/api/agent/status").json()
        for field in ("running", "cycle_count", "model_trained",
                      "total_decisions", "pending_approvals"):
            assert field in data


class TestAgentRisks:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/risks").status_code == 200

    def test_returns_list(self, client, db):
        data = client.get("/api/agent/risks").json()
        assert isinstance(data, list)


class TestGraphInfo:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/graph-info").status_code == 200

    def test_shape(self, client, db):
        data = client.get("/api/agent/graph-info").json()
        assert "engine" in data
        assert data["engine"] == "langgraph"
        assert "nodes" in data
        assert "compiled" in data


class TestAgentSummary:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/summary").status_code == 200

    def test_shape(self, client, db):
        data = client.get("/api/agent/summary").json()
        assert "cycle_count" in data
        assert "summary" in data


class TestFeatureImportance:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/feature-importance").status_code == 200


class TestLlmStats:

    def test_returns_200(self, client, db):
        assert client.get("/api/agent/llm-stats").status_code == 200


class TestApproveDecision:

    def test_approve_pending_decision(self, client, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier)
        dec = _add_decision(
            db,
            decision_id="DEC-APPROVE",
            status="pending_approval",
            requires_approval=True,
            entity_id=ship.shipment_id,
        )
        db.commit()

        resp = client.post(
            "/api/agent/approve/DEC-APPROVE",
            json={"approved": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

    def test_reject_pending_decision(self, client, db):
        _add_decision(
            db,
            decision_id="DEC-REJECT",
            status="pending_approval",
            requires_approval=True,
        )
        db.commit()

        resp = client.post(
            "/api/agent/approve/DEC-REJECT",
            json={"approved": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    def test_approve_non_pending_returns_400(self, client, db):
        _add_decision(db, decision_id="DEC-DONE", status="executed")
        db.commit()

        resp = client.post(
            "/api/agent/approve/DEC-DONE",
            json={"approved": True},
        )
        assert resp.status_code == 400

    def test_approve_unknown_returns_404(self, client, db):
        resp = client.post(
            "/api/agent/approve/DEC-GHOST",
            json={"approved": True},
        )
        assert resp.status_code == 404
