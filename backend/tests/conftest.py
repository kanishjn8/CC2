"""
Shared pytest fixtures — in-memory SQLite DB + seeded data + FastAPI test client.

All tests run against an isolated SQLite database so Postgres is not required.
"""

import json
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models import (
    CarrierPerformance,
    Route,
    Shipment,
    ShipmentStatus,
    SimulationEvent,
    TrafficLevel,
    WarehouseState,
    EventType,
)

# ── In-memory SQLite engine (isolated per test session) ──────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db():
    """Fresh DB session per test; rolls back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    """FastAPI TestClient wired to the per-test DB session."""
    from main import app

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Seeding helpers ───────────────────────────────────────────────────────────

def make_carrier(db, *, name="TestCarrier", reliability=0.9, delay_prob=0.1, pickup_rate=0.95):
    c = CarrierPerformance(
        carrier_id=f"CR-{uuid.uuid4().hex[:8]}",
        name=name,
        reliability_score=reliability,
        delay_probability=delay_prob,
        pickup_success_rate=pickup_rate,
        total_shipments=0,
        total_delays=0,
    )
    db.add(c)
    db.flush()
    return c


def make_warehouse(db, *, location="TestCity", capacity=500, load=100, queue=5):
    wh = WarehouseState(
        warehouse_id=f"WH-{uuid.uuid4().hex[:8]}",
        location=location,
        capacity=capacity,
        current_load=load,
        queue_length=queue,
        congestion_score=round(load / capacity, 3),
    )
    db.add(wh)
    db.flush()
    return wh


def make_route(db, *, origin="Mumbai", destination="Delhi", distance=1400.0,
               traffic=TrafficLevel.low, weather=1.0):
    r = Route(
        route_id=f"RT-{uuid.uuid4().hex[:8]}",
        origin=origin,
        destination=destination,
        distance=distance,
        traffic_level=traffic,
        weather_factor=weather,
    )
    db.add(r)
    db.flush()
    return r


def make_shipment(db, carrier, route=None, *, status=ShipmentStatus.created,
                  eta_offset_hours=24, sla_offset_hours=28):
    now = datetime.utcnow()
    s = Shipment(
        shipment_id=f"SH-{uuid.uuid4().hex[:8]}",
        origin="Mumbai",
        destination="Delhi",
        carrier=carrier.carrier_id,
        route_id=route.route_id if route else None,
        eta=now + timedelta(hours=eta_offset_hours),
        sla_deadline=now + timedelta(hours=sla_offset_hours),
        status=status,
    )
    db.add(s)
    db.flush()
    return s


def seed_full(db, *, n_carriers=3, n_warehouses=3, n_routes=3, n_shipments=6):
    """Seed a minimal but complete dataset and return all created objects."""
    carriers = [make_carrier(db, name=f"Carrier{i}") for i in range(n_carriers)]
    warehouses = [make_warehouse(db, location=f"City{i}") for i in range(n_warehouses)]
    routes = [make_route(db) for _ in range(n_routes)]
    shipments = []
    statuses = [
        ShipmentStatus.created,
        ShipmentStatus.dispatched,
        ShipmentStatus.in_transit,
        ShipmentStatus.delayed,
        ShipmentStatus.delivered,
        ShipmentStatus.failed,
    ]
    for i in range(n_shipments):
        s = make_shipment(
            db,
            carriers[i % n_carriers],
            routes[i % n_routes],
            status=statuses[i % len(statuses)],
        )
        shipments.append(s)
    db.commit()
    return carriers, warehouses, routes, shipments
