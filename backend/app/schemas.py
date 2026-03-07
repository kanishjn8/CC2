"""Pydantic schemas for API request / response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


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
