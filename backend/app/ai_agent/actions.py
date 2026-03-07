"""
Action execution — applies agent decisions to the simulation state.

Each function mutates the database to reflect the intervention.
The caller is responsible for committing the transaction.
"""

import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import (
    CarrierPerformance,
    Route,
    Shipment,
    ShipmentStatus,
    TrafficLevel,
    WarehouseState,
)


def reroute_shipment(db: Session, shipment_id: str) -> dict:
    """Find a lower-traffic route and reassign the shipment."""
    shipment = db.query(Shipment).filter_by(shipment_id=shipment_id).first()
    if not shipment:
        return {"success": False, "reason": "Shipment not found"}

    best_route = (
        db.query(Route)
        .filter(Route.route_id != shipment.route_id)
        .filter(Route.traffic_level.in_([TrafficLevel.low, TrafficLevel.moderate]))
        .order_by(Route.weather_factor.asc())
        .first()
    )
    if not best_route:
        return {"success": False, "reason": "No better route available"}

    old_route = shipment.route_id
    shipment.route_id = best_route.route_id
    improvement = timedelta(hours=random.uniform(1, 4))
    shipment.eta = shipment.eta - improvement

    return {
        "success": True,
        "old_route": old_route,
        "new_route": best_route.route_id,
        "eta_improvement_hours": round(improvement.total_seconds() / 3600, 2),
    }


def prioritize_loading(db: Session, shipment_id: str) -> dict:
    """Prioritize a shipment at its origin warehouse, advancing its status."""
    shipment = db.query(Shipment).filter_by(shipment_id=shipment_id).first()
    if not shipment:
        return {"success": False, "reason": "Shipment not found"}

    warehouse = db.query(WarehouseState).filter_by(location=shipment.origin).first()
    if warehouse:
        warehouse.queue_length = max(0, warehouse.queue_length - 1)

    if shipment.status == ShipmentStatus.created:
        shipment.status = ShipmentStatus.dispatched

    improvement = timedelta(hours=random.uniform(0.5, 2))
    shipment.eta = shipment.eta - improvement

    return {
        "success": True,
        "shipment_id": shipment_id,
        "new_status": shipment.status.value,
        "eta_improvement_hours": round(improvement.total_seconds() / 3600, 2),
    }


def switch_carrier(db: Session, shipment_id: str) -> dict:
    """Reassign a shipment to the most reliable alternative carrier."""
    shipment = db.query(Shipment).filter_by(shipment_id=shipment_id).first()
    if not shipment:
        return {"success": False, "reason": "Shipment not found"}

    best_carrier = (
        db.query(CarrierPerformance)
        .filter(CarrierPerformance.carrier_id != shipment.carrier)
        .order_by(CarrierPerformance.reliability_score.desc())
        .first()
    )
    if not best_carrier:
        return {"success": False, "reason": "No alternative carrier available"}

    old_carrier = shipment.carrier
    shipment.carrier = best_carrier.carrier_id
    best_carrier.total_shipments += 1

    return {
        "success": True,
        "old_carrier": old_carrier,
        "new_carrier": best_carrier.carrier_id,
        "new_carrier_reliability": best_carrier.reliability_score,
    }


def send_alert(db: Session, entity_id: str, message: str) -> dict:
    """Record an operator alert (no state mutation)."""
    return {
        "success": True,
        "entity_id": entity_id,
        "alert_message": message,
    }


def reserve_capacity(db: Session, warehouse_id: str) -> dict:
    """Free up capacity at a warehouse (simulates reserving overflow space)."""
    warehouse = db.query(WarehouseState).filter_by(warehouse_id=warehouse_id).first()
    if not warehouse:
        return {"success": False, "reason": "Warehouse not found"}

    reduction = random.randint(10, 30)
    warehouse.current_load = max(0, warehouse.current_load - reduction)
    warehouse.congestion_score = round(
        warehouse.current_load / max(warehouse.capacity, 1), 3
    )

    return {
        "success": True,
        "warehouse_id": warehouse_id,
        "load_reduction": reduction,
        "new_congestion_score": warehouse.congestion_score,
    }


def execute_action(db: Session, action: str, entity_id: str, **kwargs) -> dict:
    """Dispatch an action by name to the appropriate handler."""
    if action == "reroute_shipment":
        return reroute_shipment(db, entity_id)
    elif action == "prioritize_loading":
        return prioritize_loading(db, entity_id)
    elif action == "switch_carrier":
        return switch_carrier(db, entity_id)
    elif action == "send_alert":
        return send_alert(db, entity_id, kwargs.get("message", ""))
    elif action == "reserve_capacity":
        return reserve_capacity(db, entity_id)
    return {"success": False, "reason": f"Unknown action: {action}"}
