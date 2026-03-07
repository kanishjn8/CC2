"""Pydantic schemas for API request / response validation."""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


# ── GeoJSON helper ───────────────────────────────────────────────────────────

class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""
    type: str = "Point"
    coordinates: List[float]   # [longitude, latitude]


class GeoJSONLineString(BaseModel):
    """GeoJSON LineString geometry."""
    type: str = "LineString"
    coordinates: List[List[float]]   # [[lon, lat], ...]


class GeoJSONFeature(BaseModel):
    """A single GeoJSON Feature."""
    type: str = "Feature"
    geometry: Optional[dict] = None
    properties: dict = {}


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection for map consumption."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = []


# ── Shipments ────────────────────────────────────────────────────────────────

class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shipment_id: str
    origin: str
    destination: str
    carrier: str
    route_id: Optional[str] = None
    eta: datetime
    sla_deadline: datetime
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Warehouses ───────────────────────────────────────────────────────────────

class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warehouse_id: str
    location: str
    capacity: int
    current_load: int
    queue_length: int
    congestion_score: float
    updated_at: Optional[datetime] = None


# ── Carriers ─────────────────────────────────────────────────────────────────

class CarrierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    carrier_id: str
    name: str
    reliability_score: float
    delay_probability: float
    pickup_success_rate: float
    total_shipments: int
    total_delays: int
    updated_at: Optional[datetime] = None


# ── Routes ───────────────────────────────────────────────────────────────────

class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    route_id: str
    origin: str
    destination: str
    distance: float
    traffic_level: str
    weather_factor: float
    updated_at: Optional[datetime] = None


# ── Events ───────────────────────────────────────────────────────────────────

class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    entity_id: str
    payload: Optional[str] = None
    sim_time: Optional[float] = None
    created_at: Optional[datetime] = None


# ── Simulation control ───────────────────────────────────────────────────────

class SimulationResponse(BaseModel):
    status: str
    message: str
    events_generated: int = 0
    details: Optional[dict] = None


class SimStatusResponse(BaseModel):
    running: bool
    sim_time: float
    total_events: int
    shipment_count: int
    warehouse_count: int
    carrier_count: int
    route_count: int


# ── Decision Log / Agent ─────────────────────────────────────────────────────

class DecisionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    decision_id: str
    risk_type: str
    entity_id: str
    shipment_id: Optional[str] = None
    risk_score: float
    problem: str
    evidence: Optional[str] = None
    root_cause: str
    confidence: float
    recommended_action: str
    action_details: Optional[str] = None
    requires_approval: bool
    status: str
    outcome: str
    sla_impact: Optional[float] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AgentMetricsOut(BaseModel):
    total_decisions: int
    intervention_success_rate: float
    false_positive_rate: float
    average_confidence: float
    outcomes: dict
    actions_breakdown: dict
    risk_type_breakdown: dict


class AgentStatusOut(BaseModel):
    running: bool
    cycle_count: int
    model_trained: bool
    total_decisions: int
    pending_approvals: int


class AgentAnalyzeResponse(BaseModel):
    status: str
    message: str
    risks_detected: int = 0
    risks: list = []


class AgentSummaryOut(BaseModel):
    cycle_count: int
    summary: str


class ApprovalRequest(BaseModel):
    approved: bool


class ApprovalResponse(BaseModel):
    status: str
    message: str
    decision_id: str
    result: Optional[dict] = None
