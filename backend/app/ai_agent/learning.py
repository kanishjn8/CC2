"""
Learning loop — logs agent decisions, evaluates past outcomes,
and computes aggregate metrics for continuous improvement.
"""

import json
import uuid
from datetime import datetime

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models import DecisionLog, Shipment, ShipmentStatus


# ── Deduplication ────────────────────────────────────────────────────────────

def has_pending_decision(db: Session, entity_id: str, risk_type: str) -> bool:
    """Return True if an unresolved decision already exists for this entity+risk."""
    return (
        db.query(DecisionLog)
        .filter(
            DecisionLog.entity_id == entity_id,
            DecisionLog.risk_type == risk_type,
            DecisionLog.outcome == "pending",
        )
        .first()
        is not None
    )


# ── Decision logging ─────────────────────────────────────────────────────────

def log_decision(
    db: Session,
    *,
    risk_type: str,
    entity_id: str,
    shipment_id: str | None,
    risk_score: float,
    problem: str,
    evidence: dict,
    root_cause: str,
    confidence: float,
    recommended_action: str,
    action_details: dict | None = None,
    requires_approval: bool = False,
    status: str = "executed",
) -> DecisionLog:
    """Create a decision log entry."""
    decision = DecisionLog(
        decision_id=f"DEC-{uuid.uuid4().hex[:8]}",
        risk_type=risk_type,
        entity_id=entity_id,
        shipment_id=shipment_id,
        risk_score=round(risk_score, 4),
        problem=problem,
        evidence=json.dumps(evidence),
        root_cause=root_cause,
        confidence=round(confidence, 4),
        recommended_action=recommended_action,
        action_details=json.dumps(action_details) if action_details else None,
        requires_approval=requires_approval,
        status=status,
        outcome="pending",
    )
    db.add(decision)
    return decision


# ── Outcome evaluation ───────────────────────────────────────────────────────

def evaluate_outcomes(db: Session):
    """Check past decisions and update outcomes based on current shipment states."""
    pending = (
        db.query(DecisionLog)
        .filter(
            DecisionLog.outcome == "pending",
            DecisionLog.status.in_(["executed", "approved"]),
            DecisionLog.shipment_id.isnot(None),
        )
        .all()
    )

    now = datetime.utcnow()
    for dec in pending:
        shipment = db.query(Shipment).filter_by(shipment_id=dec.shipment_id).first()
        if not shipment:
            continue

        if shipment.status == ShipmentStatus.delivered:
            if shipment.sla_deadline and now <= shipment.sla_deadline:
                dec.outcome = "success"
                dec.sla_impact = round(
                    (shipment.sla_deadline - now).total_seconds() / 3600, 2
                )
            else:
                dec.outcome = "failed"
                dec.sla_impact = round(
                    (now - shipment.sla_deadline).total_seconds() / 3600 * -1, 2
                )
            dec.resolved_at = now

        elif shipment.status == ShipmentStatus.failed:
            dec.outcome = "failed"
            dec.sla_impact = -1.0
            dec.resolved_at = now

        elif shipment.status in (ShipmentStatus.in_transit, ShipmentStatus.dispatched):
            # ETA already exceeds SLA — intervention likely failed
            if shipment.eta and shipment.sla_deadline and shipment.eta > shipment.sla_deadline:
                dec.outcome = "failed"
                dec.sla_impact = round(
                    (shipment.sla_deadline - shipment.eta).total_seconds() / 3600, 2
                )
                dec.resolved_at = now


# ── Aggregate metrics ────────────────────────────────────────────────────────

def get_metrics(db: Session) -> dict:
    """Compute aggregate learning metrics across all decisions."""
    total = db.query(DecisionLog).count()
    if total == 0:
        return {
            "total_decisions": 0,
            "intervention_success_rate": 0.0,
            "false_positive_rate": 0.0,
            "average_confidence": 0.0,
            "outcomes": {"pending": 0, "success": 0, "failed": 0},
            "actions_breakdown": {},
            "risk_type_breakdown": {},
        }

    success_count = db.query(DecisionLog).filter_by(outcome="success").count()
    failed_count = db.query(DecisionLog).filter_by(outcome="failed").count()
    pending_count = db.query(DecisionLog).filter_by(outcome="pending").count()
    resolved = success_count + failed_count

    success_rate = round(success_count / resolved, 3) if resolved > 0 else 0.0

    # False positives: risks flagged as high but shipment ended up fine
    false_positives = (
        db.query(DecisionLog)
        .filter(DecisionLog.outcome == "success", DecisionLog.risk_score < 0.5)
        .count()
    )
    fp_rate = round(false_positives / total, 3) if total > 0 else 0.0

    avg_conf = db.query(sa_func.avg(DecisionLog.confidence)).scalar() or 0.0

    actions = (
        db.query(DecisionLog.recommended_action, sa_func.count(DecisionLog.id))
        .group_by(DecisionLog.recommended_action)
        .all()
    )
    risk_types = (
        db.query(DecisionLog.risk_type, sa_func.count(DecisionLog.id))
        .group_by(DecisionLog.risk_type)
        .all()
    )

    return {
        "total_decisions": total,
        "intervention_success_rate": success_rate,
        "false_positive_rate": fp_rate,
        "average_confidence": round(float(avg_conf), 3),
        "outcomes": {
            "pending": pending_count,
            "success": success_count,
            "failed": failed_count,
        },
        "actions_breakdown": {a: c for a, c in actions},
        "risk_type_breakdown": {r: c for r, c in risk_types},
    }
