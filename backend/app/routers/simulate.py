"""
Simulation control API — trigger demo scenarios and manage the engine.

POST /simulate/warehouse-congestion
POST /simulate/carrier-failure
POST /simulate/traffic-spike
POST /simulate/pickup-failure
POST /simulate/eta-drift
POST /simulate/create-shipment
POST /simulate/start
POST /simulate/stop
GET  /simulate/status
"""

import json
import random
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Shipment,
    WarehouseState,
    CarrierPerformance,
    Route,
    SimulationEvent,
    ShipmentStatus,
    TrafficLevel,
    EventType,
)
from app.schemas import SimulationResponse, SimStatusResponse
from app.simulation import simulation

router = APIRouter(prefix="/simulate", tags=["Simulation"])


def _emit(db: Session, event_type: EventType, entity_id: str, payload: dict):
    ev = SimulationEvent(
        event_type=event_type,
        entity_id=entity_id,
        payload=json.dumps(payload),
        sim_time=simulation.sim_time,
    )
    db.add(ev)
    return ev


# ── Engine control ───────────────────────────────────────────────────────────

@router.post("/start", response_model=SimulationResponse)
def start_simulation():
    simulation.start()
    return SimulationResponse(status="ok", message="Simulation engine started.")


@router.post("/stop", response_model=SimulationResponse)
def stop_simulation():
    simulation.stop()
    return SimulationResponse(status="ok", message="Simulation engine stopped.")


@router.get("/status", response_model=SimStatusResponse)
def simulation_status(db: Session = Depends(get_db)):
    return SimStatusResponse(
        running=simulation.running,
        sim_time=simulation.sim_time,
        total_events=db.query(SimulationEvent).count(),
        shipment_count=db.query(Shipment).count(),
        warehouse_count=db.query(WarehouseState).count(),
        carrier_count=db.query(CarrierPerformance).count(),
        route_count=db.query(Route).count(),
    )


# ── Scenario: Warehouse congestion ──────────────────────────────────────────

@router.post("/warehouse-congestion", response_model=SimulationResponse)
def trigger_warehouse_congestion(db: Session = Depends(get_db)):
    warehouses = db.query(WarehouseState).all()
    if not warehouses:
        return SimulationResponse(status="error", message="No warehouses found.", events_generated=0)

    events = 0
    for wh in random.sample(warehouses, k=min(2, len(warehouses))):
        wh.current_load = int(wh.capacity * random.uniform(0.88, 0.98))
        wh.queue_length = random.randint(15, 40)
        wh.congestion_score = round(wh.current_load / wh.capacity, 3)
        _emit(db, EventType.warehouse_congestion, wh.warehouse_id, {
            "scenario": "manual_trigger",
            "congestion_score": wh.congestion_score,
            "current_load": wh.current_load,
            "capacity": wh.capacity,
            "queue_length": wh.queue_length,
        })
        events += 1

    db.commit()
    return SimulationResponse(
        status="ok",
        message=f"Warehouse congestion triggered for {events} warehouse(s).",
        events_generated=events,
    )


# ── Scenario: Carrier failure ────────────────────────────────────────────────

@router.post("/carrier-failure", response_model=SimulationResponse)
def trigger_carrier_failure(db: Session = Depends(get_db)):
    carriers = db.query(CarrierPerformance).all()
    if not carriers:
        return SimulationResponse(status="error", message="No carriers found.", events_generated=0)

    carrier = random.choice(carriers)
    carrier.reliability_score = round(max(0.2, carrier.reliability_score - random.uniform(0.15, 0.3)), 3)
    carrier.delay_probability = round(min(0.8, carrier.delay_probability + random.uniform(0.1, 0.25)), 3)
    carrier.pickup_success_rate = round(max(0.4, carrier.pickup_success_rate - random.uniform(0.1, 0.2)), 3)

    # Delay all in-transit shipments using this carrier
    affected = db.query(Shipment).filter(
        Shipment.carrier == carrier.carrier_id,
        Shipment.status.in_([ShipmentStatus.in_transit, ShipmentStatus.dispatched]),
    ).all()

    events = 0
    _emit(db, EventType.carrier_failure, carrier.carrier_id, {
        "scenario": "manual_trigger",
        "reliability_score": carrier.reliability_score,
        "delay_probability": carrier.delay_probability,
        "pickup_success_rate": carrier.pickup_success_rate,
        "affected_shipments": len(affected),
    })
    events += 1

    for ship in affected:
        ship.status = ShipmentStatus.delayed
        drift = timedelta(hours=random.uniform(4, 16))
        ship.eta = ship.eta + drift
        carrier.total_delays += 1
        _emit(db, EventType.shipment_delayed, ship.shipment_id, {
            "cause": "carrier_failure",
            "carrier": carrier.carrier_id,
            "drift_hours": round(drift.total_seconds() / 3600, 2),
            "new_eta": ship.eta.isoformat(),
        })
        events += 1

    db.commit()
    return SimulationResponse(
        status="ok",
        message=f"Carrier {carrier.name} failed. {len(affected)} shipment(s) delayed.",
        events_generated=events,
        details={"carrier_id": carrier.carrier_id, "carrier_name": carrier.name},
    )


# ── Scenario: Traffic spike ─────────────────────────────────────────────────

@router.post("/traffic-spike", response_model=SimulationResponse)
def trigger_traffic_spike(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    if not routes:
        return SimulationResponse(status="error", message="No routes found.", events_generated=0)

    events = 0
    targets = random.sample(routes, k=min(3, len(routes)))
    for rt in targets:
        rt.traffic_level = TrafficLevel.severe
        rt.weather_factor = round(min(2.0, rt.weather_factor + random.uniform(0.3, 0.6)), 2)
        _emit(db, EventType.route_traffic_update, rt.route_id, {
            "scenario": "manual_trigger",
            "traffic_level": rt.traffic_level.value,
            "weather_factor": rt.weather_factor,
        })
        events += 1

    # Apply ETA drift to shipments on those routes
    route_ids = [rt.route_id for rt in targets]
    ships = db.query(Shipment).filter(
        Shipment.route_id.in_(route_ids),
        Shipment.status.in_([ShipmentStatus.in_transit, ShipmentStatus.dispatched]),
    ).all()
    for ship in ships:
        drift = timedelta(hours=random.uniform(2, 8))
        ship.eta = ship.eta + drift
        _emit(db, EventType.eta_drift, ship.shipment_id, {
            "cause": "traffic_spike",
            "drift_hours": round(drift.total_seconds() / 3600, 2),
            "new_eta": ship.eta.isoformat(),
        })
        events += 1

    db.commit()
    return SimulationResponse(
        status="ok",
        message=f"Traffic spike on {len(targets)} route(s), {len(ships)} shipment(s) affected.",
        events_generated=events,
    )


# ── Scenario: Pickup failure ────────────────────────────────────────────────

@router.post("/pickup-failure", response_model=SimulationResponse)
def trigger_pickup_failure(db: Session = Depends(get_db)):
    ships = db.query(Shipment).filter(
        Shipment.status.in_([ShipmentStatus.created, ShipmentStatus.dispatched])
    ).all()
    if not ships:
        return SimulationResponse(status="error", message="No eligible shipments found.", events_generated=0)

    ship = random.choice(ships)
    ship.status = ShipmentStatus.failed

    carrier = db.query(CarrierPerformance).filter_by(carrier_id=ship.carrier).first()
    if carrier:
        carrier.pickup_success_rate = round(max(0.4, carrier.pickup_success_rate - 0.05), 3)

    _emit(db, EventType.pickup_failure, ship.shipment_id, {
        "scenario": "manual_trigger",
        "carrier": ship.carrier,
        "origin": ship.origin,
    })
    db.commit()
    return SimulationResponse(
        status="ok",
        message=f"Pickup failure for shipment {ship.shipment_id}.",
        events_generated=1,
        details={"shipment_id": ship.shipment_id, "carrier": ship.carrier},
    )


# ── Scenario: ETA drift ─────────────────────────────────────────────────────

@router.post("/eta-drift", response_model=SimulationResponse)
def trigger_eta_drift(db: Session = Depends(get_db)):
    ships = db.query(Shipment).filter(
        Shipment.status == ShipmentStatus.in_transit
    ).all()
    if not ships:
        return SimulationResponse(status="error", message="No in-transit shipments.", events_generated=0)

    events = 0
    for ship in random.sample(ships, k=min(3, len(ships))):
        drift = timedelta(hours=random.uniform(2, 10))
        ship.eta = ship.eta + drift
        _emit(db, EventType.eta_drift, ship.shipment_id, {
            "scenario": "manual_trigger",
            "drift_hours": round(drift.total_seconds() / 3600, 2),
            "new_eta": ship.eta.isoformat(),
        })
        events += 1

    db.commit()
    return SimulationResponse(
        status="ok",
        message=f"ETA drift applied to {events} shipment(s).",
        events_generated=events,
    )


# ── Create new shipment on the fly ──────────────────────────────────────────

@router.post("/create-shipment", response_model=SimulationResponse)
def create_shipment(db: Session = Depends(get_db)):
    carriers = db.query(CarrierPerformance).all()
    routes = db.query(Route).all()
    if not carriers or not routes:
        return SimulationResponse(status="error", message="Seed data missing.", events_generated=0)

    route = random.choice(routes)
    carrier = random.choice(carriers)
    now = datetime.utcnow()
    eta_hours = random.uniform(6, 48)
    sla_buffer = random.uniform(2, 12)

    ship = Shipment(
        shipment_id=f"SH-{uuid.uuid4().hex[:8]}",
        origin=route.origin,
        destination=route.destination,
        carrier=carrier.carrier_id,
        route_id=route.route_id,
        eta=now + timedelta(hours=eta_hours),
        sla_deadline=now + timedelta(hours=eta_hours + sla_buffer),
        status=ShipmentStatus.created,
    )
    db.add(ship)
    carrier.total_shipments += 1

    _emit(db, EventType.shipment_created, ship.shipment_id, {
        "origin": ship.origin,
        "destination": ship.destination,
        "carrier": carrier.carrier_id,
        "eta": ship.eta.isoformat(),
        "sla_deadline": ship.sla_deadline.isoformat(),
    })

    db.commit()
    return SimulationResponse(
        status="ok",
        message=f"Shipment {ship.shipment_id} created.",
        events_generated=1,
        details={
            "shipment_id": ship.shipment_id,
            "origin": ship.origin,
            "destination": ship.destination,
        },
    )
