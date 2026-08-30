"""
Learning loop — logs agent decisions, evaluates past outcomes,
and computes aggregate metrics for continuous improvement.
"""

import json
import uuid
from datetime import datetime

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.ai_agent.risk_models import DelayRiskModel, FEATURE_NAMES
from app.config import (
    RISK_MODEL_REAL_SAMPLE_WEIGHT,
    RISK_MODEL_RETRAIN_INTERVAL_CYCLES,
    RISK_MODEL_RETRAIN_MIN_SAMPLES,
    RISK_MODEL_RETRAIN_SYNTHETIC_SAMPLES,
)
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


# ── Delay model retraining data ──────────────────────────────────────────────

OUTCOME_TO_DELAY_LABEL = {
    "success": 0,
    "failed": 1,
}


def extract_delay_training_samples(
    db: Session,
    *,
    limit: int = 2000,
) -> list[tuple[dict, int]]:
    """Build training samples from resolved delay-risk decisions.

    Labels are derived from evaluated outcomes:
    - success -> 0, the shipment stayed within SLA
    - failed -> 1, the shipment missed SLA or failed
    """
    decisions = (
        db.query(DecisionLog)
        .filter(
            DecisionLog.risk_type == "delay_risk",
            DecisionLog.outcome.in_(list(OUTCOME_TO_DELAY_LABEL)),
            DecisionLog.evidence.isnot(None),
        )
        .order_by(DecisionLog.id.desc())
        .limit(limit)
        .all()
    )

    samples: list[tuple[dict, int]] = []
    seen: set[tuple] = set()
    for dec in decisions:
        features = _extract_model_features(dec.evidence)
        if features is None:
            continue

        label = OUTCOME_TO_DELAY_LABEL[dec.outcome]
        fingerprint = (
            dec.shipment_id,
            label,
            tuple(round(float(features[name]), 6) for name in FEATURE_NAMES),
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        samples.append((features, label))

    return samples


def should_retrain_delay_model(
    cycle_count: int,
    *,
    interval_cycles: int = RISK_MODEL_RETRAIN_INTERVAL_CYCLES,
) -> bool:
    """Return True when this agent cycle should attempt model retraining."""
    return interval_cycles > 0 and cycle_count > 0 and cycle_count % interval_cycles == 0


def retrain_delay_model_from_learning_data(
    db: Session,
    model: DelayRiskModel,
    *,
    min_samples: int = RISK_MODEL_RETRAIN_MIN_SAMPLES,
    synthetic_samples: int = RISK_MODEL_RETRAIN_SYNTHETIC_SAMPLES,
    real_sample_weight: float = RISK_MODEL_REAL_SAMPLE_WEIGHT,
) -> dict:
    """Retrain the delay model with resolved decision outcomes when available."""
    samples = extract_delay_training_samples(db)
    if len(samples) < min_samples:
        return {
            "retrained": False,
            "reason": "not_enough_real_samples",
            "real_samples": len(samples),
            "min_samples": min_samples,
            "training": model.get_training_summary(),
        }

    metadata = model.train(
        n_samples=synthetic_samples,
        training_samples=samples,
        real_sample_weight=real_sample_weight,
    )
    return {
        "retrained": True,
        "real_samples": len(samples),
        "min_samples": min_samples,
        "training": metadata,
    }


def _extract_model_features(evidence_raw: str | None) -> dict | None:
    """Read a feature snapshot from a decision evidence JSON blob."""
    if not evidence_raw:
        return None

    try:
        evidence = json.loads(evidence_raw)
    except (TypeError, ValueError):
        return None

    features = evidence.get("model_features") or evidence.get("features")
    if not isinstance(features, dict):
        return None

    try:
        return {name: float(features[name]) for name in FEATURE_NAMES}
    except (KeyError, TypeError, ValueError):
        return None


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
