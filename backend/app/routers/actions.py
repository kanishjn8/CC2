"""
Operational action endpoints — direct trigger for Send Alert and Reroute.

These provide explicit REST endpoints for the two MVP demo actions,
independent of the approval workflow in the agent router.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from app.database import get_db
from app.models import DecisionLog, Route, Shipment, TrafficLevel
from app.ai_agent.actions import reroute_shipment as _reroute_action

log = logging.getLogger("cc2.actions_api")

router = APIRouter(prefix="/actions", tags=["Operational Actions"])


# ── Request / Response Schemas ────────────────────────────────────────────────

class SendAlertRequest(BaseModel):
    shipment_id: str
    risk_score: float = 0.0
    reason: str = ""
    message: str = ""


class SendAlertResponse(BaseModel):
    status: str
    alert_type: str
    shipment_id: str
    message: str
    decision_id: str | None = None


class RerouteRequest(BaseModel):
    shipment_id: str
    reason: str = ""


class RouteGeometry(BaseModel):
    type: str = "LineString"
    coordinates: list[list[float]] = []


class RerouteResponse(BaseModel):
    status: str
    shipment_id: str
    old_route: str | None = None
    new_route: str | None = None
    new_route_origin: str | None = None
    new_route_destination: str | None = None
    eta_improvement_hours: float = 0.0
    old_route_geometry: RouteGeometry | None = None
    new_route_geometry: RouteGeometry | None = None
    message: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _linestring_geojson(geom_col) -> dict | None:
    """Convert a WKB LINESTRING to a GeoJSON dict."""
    if geom_col is None:
        return None
    try:
        shape = to_shape(geom_col)
        return {"type": "LineString", "coordinates": [list(c) for c in shape.coords]}
    except Exception:
        return None


# ── POST /api/actions/send-alert ──────────────────────────────────────────────

@router.post("/send-alert", response_model=SendAlertResponse)
def send_alert_action(body: SendAlertRequest, db: Session = Depends(get_db)):
    """
    Directly send a risk alert for a shipment.
    Creates a DecisionLog entry with status='executed' (autonomous).
    """
    shipment = db.query(Shipment).filter_by(shipment_id=body.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment '{body.shipment_id}' not found")

    # Create decision log entry for the alert
    from uuid import uuid4
    decision_id = f"DEC-{uuid4().hex[:8].upper()}"

    alert_msg = body.message or f"Risk alert: {body.reason or 'Anomaly detected'} for {body.shipment_id}"

    dec = DecisionLog(
        decision_id=decision_id,
        risk_type="operator_alert",
        entity_id=body.shipment_id,
        shipment_id=body.shipment_id,
        risk_score=body.risk_score,
        problem=body.reason or "Manual alert triggered",
        root_cause=body.reason or "Operator-initiated alert",
        confidence=1.0,
        recommended_action="send_alert",
        action_details=json.dumps({
            "alert_type": "risk_alert",
            "message": alert_msg,
            "triggered_by": "operator",
        }),
        requires_approval=False,
        status="executed",
        outcome="completed",
    )
    db.add(dec)
    db.commit()

    log.info("🚨 Alert sent for %s — %s", body.shipment_id, alert_msg)

    return SendAlertResponse(
        status="alert_sent",
        alert_type="risk_alert",
        shipment_id=body.shipment_id,
        message=alert_msg,
        decision_id=decision_id,
    )


# ── POST /api/actions/reroute ────────────────────────────────────────────────

@router.post("/reroute", response_model=RerouteResponse)
def reroute_action(body: RerouteRequest, db: Session = Depends(get_db)):
    """
    Directly reroute a shipment to a better route.
    Returns GeoJSON geometries for both old and new routes
    so the frontend can visualize the change on the map.
    """
    shipment = db.query(Shipment).filter_by(shipment_id=body.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment '{body.shipment_id}' not found")

    result = _reroute_action(db, body.shipment_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Reroute failed"))

    # Create decision log entry
    from uuid import uuid4
    decision_id = f"DEC-{uuid4().hex[:8].upper()}"

    dec = DecisionLog(
        decision_id=decision_id,
        risk_type="route_risk",
        entity_id=body.shipment_id,
        shipment_id=body.shipment_id,
        risk_score=0.7,
        problem=body.reason or "Route optimization requested",
        root_cause=body.reason or "Traffic/weather conditions",
        confidence=0.9,
        recommended_action="reroute_shipment",
        action_details=json.dumps({
            "old_route": result.get("old_route"),
            "new_route": result.get("new_route"),
            "eta_improvement_hours": result.get("eta_improvement_hours"),
            "triggered_by": "operator",
        }),
        requires_approval=False,
        status="executed",
        outcome="completed",
    )
    db.add(dec)
    db.commit()

    log.info("🔀 Reroute executed for %s: %s → %s",
             body.shipment_id, result.get("old_route"), result.get("new_route"))

    return RerouteResponse(
        status="rerouted",
        shipment_id=body.shipment_id,
        old_route=result.get("old_route"),
        new_route=result.get("new_route"),
        new_route_origin=result.get("new_route_origin"),
        new_route_destination=result.get("new_route_destination"),
        eta_improvement_hours=result.get("eta_improvement_hours", 0),
        old_route_geometry=result.get("old_route_geometry"),
        new_route_geometry=result.get("new_route_geometry"),
        message=f"Shipment rerouted. ETA improved by {result.get('eta_improvement_hours', 0):.1f}h",
    )
