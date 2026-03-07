"""
Shared pytest fixtures — in-memory SQLite DB + seeded data + FastAPI test client.

All tests run against an isolated SQLite database so Postgres is not required.
GeoAlchemy2 geometry columns are rendered as plain TEXT in SQLite (no spatial ops).

Strategy:
  1. Monkey-patch GeoAlchemy2 *before* any model import so its DDL hooks
     become no-ops on SQLite.
  2. Register a custom type compiler so Geometry(...) → TEXT on SQLite.
  3. Override the FastAPI lifespan to skip Postgres-specific startup
     (PostGIS extension, real seeding, simulation thread).
"""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

# ────────────────────────────────────────────────────────────────────────────
# 1. Neuter GeoAlchemy2 DDL management for SQLite
# ────────────────────────────────────────────────────────────────────────────
import geoalchemy2.admin as _ga2_admin  # noqa: E402

_original_select_dialect = _ga2_admin.select_dialect


class _NoOpSpatialDialect:
    """Stand-in that silently swallows every DDL hook GeoAlchemy2 fires."""

    @staticmethod
    def after_create(*a, **kw):   pass
    @staticmethod
    def before_create(*a, **kw):  pass
    @staticmethod
    def after_drop(*a, **kw):     pass
    @staticmethod
    def before_drop(*a, **kw):    pass
    @staticmethod
    def after_parent_attach(*a, **kw): pass


def _patched_select_dialect(dialect_name):
    if dialect_name == "sqlite":
        return _NoOpSpatialDialect
    return _original_select_dialect(dialect_name)


_ga2_admin.select_dialect = _patched_select_dialect

# ────────────────────────────────────────────────────────────────────────────
# 2. Compile Geometry(...) → TEXT on the SQLite dialect
#    AND disable the bind-value wrapper (GeomFromEWKT) for SQLite.
# ────────────────────────────────────────────────────────────────────────────
from geoalchemy2 import Geometry as _GA2Geometry  # noqa: E402
from geoalchemy2.types import _GISType as _GA2GISType  # noqa: E402


@compiles(_GA2Geometry, "sqlite")
def _compile_geometry_sqlite(type_, compiler, **kw):
    return "TEXT"


# Override bind_expression so SQLAlchemy doesn't wrap values in GeomFromEWKT()
_original_bind_expression = _GA2GISType.bind_expression


def _noop_bind_expression(self, bindvalue):
    """On SQLite, pass the value straight through — no spatial function wrapper."""
    from sqlalchemy.engine import default as _eng_default

    # Only short-circuit for SQLite; let Postgres use the real wrapper.
    return bindvalue


_GA2GISType.bind_expression = _noop_bind_expression

# Also neuter column_expression so SELECTs don't wrap columns in ST_AsEWKB()
_GA2GISType.column_expression = lambda self, col: col

# Disable result-value processing so SQLite text values aren't parsed as WKB hex
_GA2GISType.result_processor = lambda self, dialect, coltype: None


# ────────────────────────────────────────────────────────────────────────────
# 3. Import application modules (models load *after* the patches above)
# ────────────────────────────────────────────────────────────────────────────
from app.database import Base, get_db  # noqa: E402
from app.models import (               # noqa: E402
    CarrierPerformance,
    Route,
    Shipment,
    ShipmentStatus,
    SimulationEvent,
    TrafficLevel,
    WarehouseState,
    EventType,
)

# ────────────────────────────────────────────────────────────────────────────
# 4. In-memory SQLite engine
# ────────────────────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────────────────
# 5. Fixtures
# ────────────────────────────────────────────────────────────────────────────

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


@asynccontextmanager
async def _noop_lifespan(app):
    """Replacement lifespan that skips Postgres startup, PostGIS, seeding, sim."""
    yield


@pytest.fixture()
def client(db):
    """FastAPI TestClient wired to the per-test DB session.

    The real lifespan is replaced with a no-op so the test client never
    touches the production Postgres / PostGIS / simulation engine.
    """
    from main import app

    # Swap in no-op lifespan to avoid Postgres / PostGIS startup
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan


# ────────────────────────────────────────────────────────────────────────────
# 6. Seeding helpers
# ────────────────────────────────────────────────────────────────────────────

def make_carrier(db, *, name="TestCarrier", reliability=0.9, delay_prob=0.1,
                 pickup_rate=0.95):
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
