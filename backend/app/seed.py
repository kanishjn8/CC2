"""Seed the database with initial warehouses, carriers, routes, and shipments."""

import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Shipment,
    WarehouseState,
    CarrierPerformance,
    Route,
    ShipmentStatus,
    TrafficLevel,
)

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Surat", "Nagpur", "Indore", "Bhopal", "Kochi",
]

CARRIER_NAMES = [
    "SwiftLogistics", "CargoExpress", "TransFast", "ReliFreight",
    "QuickShip", "PrimeHaul", "MetroCarriers", "AlphaTransport",
]


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def seed_warehouses(db: Session, count: int = 5) -> list[WarehouseState]:
    warehouses = []
    locations = random.sample(CITIES, min(count, len(CITIES)))
    for i, loc in enumerate(locations):
        cap = random.randint(200, 1000)
        load = random.randint(0, int(cap * 0.6))
        wh = WarehouseState(
            warehouse_id=_uid("WH"),
            location=loc,
            capacity=cap,
            current_load=load,
            queue_length=random.randint(0, 15),
            congestion_score=round(load / cap, 3),
        )
        db.add(wh)
        warehouses.append(wh)
    db.flush()
    return warehouses


def seed_carriers(db: Session, count: int = 8) -> list[CarrierPerformance]:
    carriers = []
    names = CARRIER_NAMES[:count]
    for name in names:
        rel = round(random.uniform(0.6, 1.0), 3)
        carrier = CarrierPerformance(
            carrier_id=_uid("CR"),
            name=name,
            reliability_score=rel,
            delay_probability=round(1.0 - rel + random.uniform(0, 0.1), 3),
            pickup_success_rate=round(random.uniform(0.80, 0.99), 3),
            total_shipments=0,
            total_delays=0,
        )
        db.add(carrier)
        carriers.append(carrier)
    db.flush()
    return carriers


def seed_routes(db: Session, count: int = 12) -> list[Route]:
    routes = []
    for _ in range(count):
        o, d = random.sample(CITIES, 2)
        route = Route(
            route_id=_uid("RT"),
            origin=o,
            destination=d,
            distance=round(random.uniform(100, 2500), 1),
            traffic_level=random.choice(list(TrafficLevel)),
            weather_factor=round(random.uniform(0.8, 1.5), 2),
        )
        db.add(route)
        routes.append(route)
    db.flush()
    return routes


def seed_shipments(
    db: Session,
    carriers: list[CarrierPerformance],
    routes: list[Route],
    count: int = 20,
) -> list[Shipment]:
    shipments = []
    now = datetime.utcnow()
    for _ in range(count):
        route = random.choice(routes)
        carrier = random.choice(carriers)
        eta_hours = random.uniform(6, 72)
        sla_buffer = random.uniform(2, 12)
        ship = Shipment(
            shipment_id=_uid("SH"),
            origin=route.origin,
            destination=route.destination,
            carrier=carrier.carrier_id,
            route_id=route.route_id,
            eta=now + timedelta(hours=eta_hours),
            sla_deadline=now + timedelta(hours=eta_hours + sla_buffer),
            status=random.choice(
                [ShipmentStatus.created, ShipmentStatus.dispatched, ShipmentStatus.in_transit]
            ),
        )
        db.add(ship)
        shipments.append(ship)

        # bump carrier shipment count
        carrier.total_shipments += 1

    db.flush()
    return shipments


def seed_all(db: Session, *, warehouses: int = 5, carriers: int = 8, routes: int = 12, shipments: int = 20):
    """Seed all tables. Skips if data already exists."""
    from app.models import WarehouseState as WS
    if db.query(WS).first() is not None:
        return  # already seeded

    whs = seed_warehouses(db, warehouses)
    crs = seed_carriers(db, carriers)
    rts = seed_routes(db, routes)
    shs = seed_shipments(db, crs, rts, shipments)
    db.commit()
    print(
        f"[seed] Seeded {len(whs)} warehouses, {len(crs)} carriers, "
        f"{len(rts)} routes, {len(shs)} shipments."
    )
