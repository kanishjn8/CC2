"""
Agent API endpoints — expose AI agent decisions, metrics, risk snapshots,
and approval workflow to the dashboard.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DecisionLog
from app.schemas import (
    DecisionLogOut,
    AgentMetricsOut,
    AgentStatusOut,
    AgentAnalyzeResponse,
    AgentSummaryOut,
    ApprovalRequest,
    ApprovalResponse,
)
from app.ai_agent import agent_loop
from app.ai_agent.learning import get_metrics
from app.ai_agent.actions import execute_action
from app.ai_agent.llm_client import get_llm_stats

router = APIRouter(prefix="/agent", tags=["AI Agent"])
log = logging.getLogger("cc2.agent_api")


# ── Graph info ───────────────────────────────────────────────────────────────

@router.get("/graph-info")
def graph_info():
    """Return LangGraph pipeline metadata."""
    graph = agent_loop._graph
    nodes = list(graph.nodes.keys()) if graph else []
    return {
        "engine": "langgraph",
        "nodes": nodes,
        "compiled": graph is not None,
        "cycle_count": agent_loop.cycle_count,
    }


# ── Decision log ─────────────────────────────────────────────────────────────

@router.get("/decisions", response_model=list[DecisionLogOut])
def list_decisions(
    risk_type: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    shipment_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(DecisionLog)
    if risk_type:
        q = q.filter(DecisionLog.risk_type == risk_type)
    if status:
        q = q.filter(DecisionLog.status == status)
    if outcome:
        q = q.filter(DecisionLog.outcome == outcome)
    if shipment_id:
        q = q.filter(DecisionLog.shipment_id == shipment_id)
    return q.order_by(DecisionLog.id.desc()).limit(limit).all()


@router.get("/decisions/{decision_id}", response_model=DecisionLogOut)
def get_decision(decision_id: str, db: Session = Depends(get_db)):
    dec = db.query(DecisionLog).filter_by(decision_id=decision_id).first()
    if not dec:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found")
    return dec


# ── Metrics ──────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=AgentMetricsOut)
def agent_metrics(db: Session = Depends(get_db)):
    return get_metrics(db)


# ── Status ───────────────────────────────────────────────────────────────────

@router.get("/status", response_model=AgentStatusOut)
def agent_status(db: Session = Depends(get_db)):
    return AgentStatusOut(
        running=agent_loop.running,
        cycle_count=agent_loop.cycle_count,
        model_trained=agent_loop.delay_model.is_trained,
        total_decisions=db.query(DecisionLog).count(),
        pending_approvals=db.query(DecisionLog).filter_by(status="pending_approval").count(),
    )


# ── Current risks ────────────────────────────────────────────────────────────

@router.get("/risks")
def current_risks():
    """Return the risk snapshot from the most recent agent cycle."""
    return agent_loop.last_risks


# ── Manual analysis trigger ──────────────────────────────────────────────────

@router.post("/analyze", response_model=AgentAnalyzeResponse)
def trigger_analysis(db: Session = Depends(get_db)):
    """Run a single Observe → Reason → Decide → Act → Learn cycle on demand."""
    risks = agent_loop.run_single_cycle(db)
    db.commit()
    return AgentAnalyzeResponse(
        status="ok",
        message=f"Analysis complete. {len(risks)} risk(s) detected.",
        risks_detected=len(risks),
        risks=risks,
    )


# ── Approval workflow ────────────────────────────────────────────────────────

@router.post("/approve/{decision_id}", response_model=ApprovalResponse)
def approve_decision(
    decision_id: str,
    body: ApprovalRequest,
    db: Session = Depends(get_db),
):
    """Approve or reject a pending agent action."""
    dec = db.query(DecisionLog).filter_by(decision_id=decision_id).first()
    if not dec:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found")

    if dec.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Decision is not pending approval (current status: {dec.status})",
        )

    if body.approved:
        result = execute_action(db, dec.recommended_action, dec.entity_id)
        dec.status = "approved"
        # Merge execution result into action_details
        existing = json.loads(dec.action_details) if dec.action_details else {}
        existing["approval_result"] = result
        dec.action_details = json.dumps(existing)
        db.commit()

        log.info("✅ Approved decision %s — action '%s' executed for %s",
                 decision_id, dec.recommended_action, dec.entity_id)

        return ApprovalResponse(
            status="approved",
            message=f"Action '{dec.recommended_action}' approved and executed.",
            decision_id=decision_id,
            result=result,
        )
    else:
        dec.status = "rejected"
        dec.outcome = "rejected"
        db.commit()

        log.info("❌ Rejected decision %s — action '%s' for %s",
                 decision_id, dec.recommended_action, dec.entity_id)

        return ApprovalResponse(
            status="rejected",
            message=f"Action '{dec.recommended_action}' rejected by operator.",
            decision_id=decision_id,
        )


# ── Cycle summary (LLM-powered) ──────────────────────────────────────────────

@router.get("/summary", response_model=AgentSummaryOut)
def agent_summary():
    """Return the LLM-generated narrative summary from the latest cycle."""
    return AgentSummaryOut(
        cycle_count=agent_loop.cycle_count,
        summary=agent_loop.last_summary or "No cycles completed yet.",
    )


# ── Feature importance (model explainability) ────────────────────────────────

@router.get("/feature-importance")
def feature_importance():
    """Return the feature importance weights from the trained delay risk model."""
    return agent_loop.delay_model.get_feature_importance()


# ── LLM usage statistics ─────────────────────────────────────────────────────

@router.get("/llm-stats")
def llm_stats():
    """Return LLM call statistics for monitoring."""
    return get_llm_stats()
