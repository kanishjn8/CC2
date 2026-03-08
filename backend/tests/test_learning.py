"""
Tests for the learning module — decision logging, outcome evaluation, metrics.
"""

import json
from datetime import datetime, timedelta

import pytest

from app.models import DecisionLog, Shipment, ShipmentStatus
from app.ai_agent.learning import (
    has_pending_decision,
    log_decision,
    evaluate_outcomes,
    get_metrics,
)
from tests.conftest import make_carrier, make_shipment


def _make_decision(db, *, entity_id="SH-001", risk_type="delay_risk",
                   status="executed", outcome="pending", **kwargs):
    """Helper to create a DecisionLog entry."""
    return log_decision(
        db,
        risk_type=risk_type,
        entity_id=entity_id,
        shipment_id=kwargs.get("shipment_id", entity_id),
        risk_score=kwargs.get("risk_score", 0.75),
        problem=kwargs.get("problem", "Test problem"),
        evidence=kwargs.get("evidence", {"test": True}),
        root_cause=kwargs.get("root_cause", "Test root cause"),
        confidence=kwargs.get("confidence", 0.85),
        recommended_action=kwargs.get("recommended_action", "reroute_shipment"),
        action_details=kwargs.get("action_details"),
        requires_approval=kwargs.get("requires_approval", False),
        status=status,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# has_pending_decision
# ═══════════════════════════════════════════════════════════════════════════════

class TestHasPendingDecision:

    def test_returns_true_when_pending_exists(self, db):
        _make_decision(db, entity_id="SH-X", risk_type="delay_risk")
        db.flush()

        assert has_pending_decision(db, "SH-X", "delay_risk") is True

    def test_returns_false_when_no_pending(self, db):
        assert has_pending_decision(db, "SH-Y", "delay_risk") is False

    def test_different_risk_type_returns_false(self, db):
        _make_decision(db, entity_id="SH-X", risk_type="delay_risk")
        db.flush()

        assert has_pending_decision(db, "SH-X", "bottleneck") is False

    def test_resolved_decision_returns_false(self, db):
        dec = _make_decision(db, entity_id="SH-R")
        dec.outcome = "success"
        db.flush()

        assert has_pending_decision(db, "SH-R", "delay_risk") is False


# ═══════════════════════════════════════════════════════════════════════════════
# log_decision
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogDecision:

    def test_creates_record(self, db):
        dec = _make_decision(db)
        db.flush()

        assert dec.id is not None
        assert dec.decision_id.startswith("DEC-")

    def test_persists_to_db(self, db):
        _make_decision(db, entity_id="SH-persist")
        db.flush()

        count = db.query(DecisionLog).filter_by(entity_id="SH-persist").count()
        assert count == 1

    def test_stores_evidence_as_json(self, db):
        dec = _make_decision(db, evidence={"key": "value", "num": 42})
        db.flush()

        parsed = json.loads(dec.evidence)
        assert parsed["key"] == "value"
        assert parsed["num"] == 42

    def test_default_outcome_is_pending(self, db):
        dec = _make_decision(db)
        db.flush()
        assert dec.outcome == "pending"

    def test_requires_approval_flag(self, db):
        dec = _make_decision(db, requires_approval=True, status="pending_approval")
        db.flush()
        assert dec.requires_approval is True
        assert dec.status == "pending_approval"


# ═══════════════════════════════════════════════════════════════════════════════
# evaluate_outcomes
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluateOutcomes:

    def test_delivered_within_sla_is_success(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.delivered,
                             sla_offset_hours=48)
        dec = _make_decision(db, entity_id=ship.shipment_id, shipment_id=ship.shipment_id)
        db.flush()

        evaluate_outcomes(db)

        assert dec.outcome == "success"
        assert dec.resolved_at is not None

    def test_failed_shipment_is_failure(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.failed)
        dec = _make_decision(db, entity_id=ship.shipment_id, shipment_id=ship.shipment_id)
        db.flush()

        evaluate_outcomes(db)

        assert dec.outcome == "failed"
        assert dec.sla_impact == -1.0

    def test_in_transit_beyond_sla_is_failure(self, db):
        carrier = make_carrier(db)
        # ETA and SLA in the past → already missed
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit,
                             eta_offset_hours=-5, sla_offset_hours=-2)
        dec = _make_decision(db, entity_id=ship.shipment_id, shipment_id=ship.shipment_id)
        db.flush()

        evaluate_outcomes(db)

        assert dec.outcome == "failed"

    def test_in_transit_within_sla_stays_pending(self, db):
        carrier = make_carrier(db)
        ship = make_shipment(db, carrier, status=ShipmentStatus.in_transit,
                             eta_offset_hours=24, sla_offset_hours=48)
        dec = _make_decision(db, entity_id=ship.shipment_id, shipment_id=ship.shipment_id)
        db.flush()

        evaluate_outcomes(db)

        assert dec.outcome == "pending"  # still in-transit, SLA not breached

    def test_no_shipment_skipped(self, db):
        dec = _make_decision(db, entity_id="SH-ghost", shipment_id="SH-ghost")
        db.flush()

        evaluate_outcomes(db)

        assert dec.outcome == "pending"  # can't resolve without shipment


# ═══════════════════════════════════════════════════════════════════════════════
# get_metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetMetrics:

    def test_empty_db_returns_zeros(self, db):
        metrics = get_metrics(db)
        assert metrics["total_decisions"] == 0
        assert metrics["intervention_success_rate"] == 0.0
        assert metrics["false_positive_rate"] == 0.0

    def test_counts_decisions(self, db):
        _make_decision(db, entity_id="SH-1")
        _make_decision(db, entity_id="SH-2")
        _make_decision(db, entity_id="SH-3")
        db.flush()

        metrics = get_metrics(db)
        assert metrics["total_decisions"] == 3

    def test_success_rate(self, db):
        d1 = _make_decision(db, entity_id="SH-s1")
        d1.outcome = "success"
        d2 = _make_decision(db, entity_id="SH-s2")
        d2.outcome = "failed"
        db.flush()

        metrics = get_metrics(db)
        assert metrics["intervention_success_rate"] == 0.5

    def test_outcomes_dict(self, db):
        d1 = _make_decision(db, entity_id="SH-o1")
        d1.outcome = "success"
        d2 = _make_decision(db, entity_id="SH-o2")
        d2.outcome = "pending"
        db.flush()

        metrics = get_metrics(db)
        assert metrics["outcomes"]["success"] == 1
        assert metrics["outcomes"]["pending"] == 1

    def test_actions_breakdown(self, db):
        _make_decision(db, entity_id="SH-a1", recommended_action="reroute_shipment")
        _make_decision(db, entity_id="SH-a2", recommended_action="send_alert")
        db.flush()

        metrics = get_metrics(db)
        assert "reroute_shipment" in metrics["actions_breakdown"]
        assert "send_alert" in metrics["actions_breakdown"]

    def test_risk_type_breakdown(self, db):
        _make_decision(db, entity_id="SH-r1", risk_type="delay_risk")
        _make_decision(db, entity_id="SH-r2", risk_type="bottleneck")
        db.flush()

        metrics = get_metrics(db)
        assert "delay_risk" in metrics["risk_type_breakdown"]
        assert "bottleneck" in metrics["risk_type_breakdown"]
