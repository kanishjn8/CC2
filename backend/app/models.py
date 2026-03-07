"""SQLAlchemy ORM models for the logistics simulation."""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    Enum as SAEnum,
    func,
)
import enum

from app.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class ShipmentStatus(str, enum.Enum):
    created = "created"
    dispatched = "dispatched"
    in_transit = "in_transit"
    at_warehouse = "at_warehouse"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    delayed = "delayed"
    failed = "failed"


class TrafficLevel(str, enum.Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    severe = "severe"


class EventType(str, enum.Enum):
    shipment_created = "shipment_created"
    shipment_dispatched = "shipment_dispatched"
    shipment_delivered = "shipment_delivered"
    shipment_delayed = "shipment_delayed"
    warehouse_load_update = "warehouse_load_update"
    warehouse_congestion = "warehouse_congestion"
    carrier_delay_event = "carrier_delay_event"
    carrier_failure = "carrier_failure"
    route_traffic_update = "route_traffic_update"
    pickup_failure = "pickup_failure"
    eta_drift = "eta_drift"


# ── Core tables ──────────────────────────────────────────────────────────────

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String(64), unique=True, nullable=False, index=True)
    origin = Column(String(128), nullable=False)
    destination = Column(String(128), nullable=False)
    carrier = Column(String(64), nullable=False)
    route_id = Column(String(64), nullable=True)
    eta = Column(DateTime, nullable=False)
    sla_deadline = Column(DateTime, nullable=False)
    status = Column(SAEnum(ShipmentStatus), default=ShipmentStatus.created, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WarehouseState(Base):
    __tablename__ = "warehouse_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(String(64), unique=True, nullable=False, index=True)
    location = Column(String(128), nullable=False)
    capacity = Column(Integer, nullable=False)
    current_load = Column(Integer, default=0, nullable=False)
    queue_length = Column(Integer, default=0, nullable=False)
    congestion_score = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CarrierPerformance(Base):
    __tablename__ = "carrier_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    carrier_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    reliability_score = Column(Float, default=1.0, nullable=False)
    delay_probability = Column(Float, default=0.05, nullable=False)
    pickup_success_rate = Column(Float, default=0.95, nullable=False)
    total_shipments = Column(Integer, default=0, nullable=False)
    total_delays = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(64), unique=True, nullable=False, index=True)
    origin = Column(String(128), nullable=False)
    destination = Column(String(128), nullable=False)
    distance = Column(Float, nullable=False)          # in km
    traffic_level = Column(SAEnum(TrafficLevel), default=TrafficLevel.low, nullable=False)
    weather_factor = Column(Float, default=1.0, nullable=False)  # 1.0 = clear, >1 = degraded
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SimulationEvent(Base):
    __tablename__ = "simulation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(SAEnum(EventType), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    payload = Column(Text, nullable=True)  # JSON string with event details
    sim_time = Column(Float, nullable=True)           # simulation clock value
    created_at = Column(DateTime, server_default=func.now(), index=True)
