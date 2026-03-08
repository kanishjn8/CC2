"""CRUD / read endpoints for operational data."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Shipment,
    WarehouseState,
    CarrierPerformance,
    Route,
    SimulationEvent,
    ShipmentStatus,
)
from app.schemas import ShipmentOut, WarehouseOut, CarrierOut, RouteOut, EventOut

router = APIRouter(tags=["Data"])


def _attach_carrier_names(shipments: list[Shipment], db: Session) -> list[ShipmentOut]:
    """Join carrier names onto shipments in a single extra query."""
    carrier_ids = {s.carrier for s in shipments}
    carriers = (
        db.query(CarrierPerformance)
        .filter(CarrierPerformance.carrier_id.in_(carrier_ids))
        .all()
    ) if carrier_ids else []
    name_map = {c.carrier_id: c.name for c in carriers}

    results = []
    for ship in shipments:
        out = ShipmentOut.model_validate(ship)
        out.carrier_name = name_map.get(ship.carrier)
        results.append(out)
    return results


# ── Shipments ────────────────────────────────────────────────────────────────

@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(
    status: Optional[ShipmentStatus] = None,
    include_inactive: bool = Query(False, description="Include delivered/pruned shipments"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Shipment)
    if not include_inactive:
        q = q.filter(Shipment.is_active.is_(True))
    if status:
        q = q.filter(Shipment.status == status)
    shipments = q.order_by(Shipment.id.desc()).limit(limit).all()
    return _attach_carrier_names(shipments, db)


@router.get("/shipments/{shipment_id}", response_model=ShipmentOut)
def get_shipment(shipment_id: str, db: Session = Depends(get_db)):
    ship = db.query(Shipment).filter_by(shipment_id=shipment_id).first()
    if ship is None:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")
    return _attach_carrier_names([ship], db)[0]


# ── Warehouses ───────────────────────────────────────────────────────────────

@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(WarehouseState).order_by(WarehouseState.congestion_score.desc()).all()


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(warehouse_id: str, db: Session = Depends(get_db)):
    wh = db.query(WarehouseState).filter_by(warehouse_id=warehouse_id).first()
    if wh is None:
        raise HTTPException(status_code=404, detail=f"Warehouse '{warehouse_id}' not found")
    return wh


# ── Carriers ─────────────────────────────────────────────────────────────────

@router.get("/carriers", response_model=list[CarrierOut])
def list_carriers(db: Session = Depends(get_db)):
    return db.query(CarrierPerformance).order_by(CarrierPerformance.reliability_score.desc()).all()


@router.get("/carriers/{carrier_id}", response_model=CarrierOut)
def get_carrier(carrier_id: str, db: Session = Depends(get_db)):
    carrier = db.query(CarrierPerformance).filter_by(carrier_id=carrier_id).first()
    if carrier is None:
        raise HTTPException(status_code=404, detail=f"Carrier '{carrier_id}' not found")
    return carrier


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/routes", response_model=list[RouteOut])
def list_routes(db: Session = Depends(get_db)):
    return db.query(Route).all()


@router.get("/routes/{route_id}", response_model=RouteOut)
def get_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(Route).filter_by(route_id=route_id).first()
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found")
    return route


# ── Events ───────────────────────────────────────────────────────────────────

@router.get("/events", response_model=list[EventOut])
def list_events(
    event_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(SimulationEvent)
    if event_type:
        q = q.filter(SimulationEvent.event_type == event_type)
    if entity_id:
        q = q.filter(SimulationEvent.entity_id == entity_id)
    return q.order_by(SimulationEvent.id.desc()).limit(limit).all()
