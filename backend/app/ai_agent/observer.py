"""
Observe step — reads the current logistics network state from the database
and builds feature vectors for the risk detection models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Shipment,
    WarehouseState,
    CarrierPerformance,
    Route,
    ShipmentStatus,
    TrafficLevel,
)

TRAFFIC_ENCODING = {
    TrafficLevel.low: 0,
    TrafficLevel.moderate: 1,
    TrafficLevel.high: 2,
    TrafficLevel.severe: 3,
    "low": 0,
    "moderate": 1,
    "high": 2,
    "severe": 3,
}


def get_active_shipments(db: Session) -> list[Shipment]:
    """Return all shipments that are not yet delivered or failed."""
    return (
        db.query(Shipment)
        .filter(Shipment.status.notin_([ShipmentStatus.delivered, ShipmentStatus.failed]))
        .all()
    )


def get_warehouses_by_location(db: Session) -> dict[str, WarehouseState]:
    """Return warehouses indexed by location (for origin-matching)."""
    warehouses = db.query(WarehouseState).all()
    return {wh.location: wh for wh in warehouses}


def get_carriers_map(db: Session) -> dict[str, CarrierPerformance]:
    """Return carriers indexed by carrier_id."""
    carriers = db.query(CarrierPerformance).all()
    return {c.carrier_id: c for c in carriers}


def get_routes_map(db: Session) -> dict[str, Route]:
    """Return routes indexed by route_id."""
    routes = db.query(Route).all()
    return {r.route_id: r for r in routes}


def get_all_warehouses(db: Session) -> list[WarehouseState]:
    return db.query(WarehouseState).all()


def get_all_carriers(db: Session) -> list[CarrierPerformance]:
    return db.query(CarrierPerformance).all()


def build_shipment_features(
    shipment: Shipment,
    carrier: Optional[CarrierPerformance],
    route: Optional[Route],
    warehouse: Optional[WarehouseState],
) -> dict:
    """Build a feature dictionary for the delay risk model."""
    now = datetime.utcnow()

    distance = route.distance if route else 500.0
    traffic = TRAFFIC_ENCODING.get(route.traffic_level, 1) if route else 1
    weather = route.weather_factor if route else 1.0
    congestion = warehouse.congestion_score if warehouse else 0.3
    reliability = carrier.reliability_score if carrier else 0.7
    delay_prob = carrier.delay_probability if carrier else 0.15
    pickup_rate = carrier.pickup_success_rate if carrier else 0.9

    eta_sla_buffer = 12.0
    if shipment.sla_deadline and shipment.eta:
        eta_sla_buffer = (shipment.sla_deadline - shipment.eta).total_seconds() / 3600

    return {
        "distance": distance,
        "traffic_level": traffic,
        "weather_factor": weather,
        "congestion_score": congestion,
        "reliability_score": reliability,
        "delay_probability": delay_prob,
        "pickup_success_rate": pickup_rate,
        "eta_sla_buffer_hours": eta_sla_buffer,
    }
