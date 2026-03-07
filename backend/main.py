"""
CC2 — Logistics Simulation & Data Layer
FastAPI application entry point.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import engine, Base
from app.models import *  # noqa: ensure all models are registered
from app.seed import seed_all
from app.database import SessionLocal
from app.simulation import simulation
from app.routers import data, simulate, agent
from app.ai_agent import agent_loop
from app.config import SEED_WAREHOUSES, SEED_CARRIERS, SEED_ROUTES, SEED_SHIPMENTS


def _wait_for_db(retries: int = 15, delay: float = 2.0):
    """Block until PostgreSQL accepts connections. Works in Docker and locally."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[startup] Database is ready.")
            return
        except OperationalError:
            print(f"[startup] Waiting for database… (attempt {attempt}/{retries})")
            time.sleep(delay)
    raise RuntimeError("Could not connect to the database after multiple retries.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    _wait_for_db()

    Base.metadata.create_all(bind=engine)
    print("[startup] Database tables created / verified.")

    db = SessionLocal()
    try:
        seed_all(
            db,
            warehouses=SEED_WAREHOUSES,
            carriers=SEED_CARRIERS,
            routes=SEED_ROUTES,
            shipments=SEED_SHIPMENTS,
        )
    finally:
        db.close()

    simulation.start()
    print("[startup] Simulation engine started.")

    agent_loop.initialize()
    agent_loop.start()
    print("[startup] AI Agent started.")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    agent_loop.stop()
    print("[shutdown] AI Agent stopped.")
    simulation.stop()
    print("[shutdown] Simulation engine stopped.")


app = FastAPI(
    title="CC2 — Logistics Simulation API",
    description=(
        "Simulation & Data Layer for the AI-powered logistics monitoring platform. "
        "Generates real-time shipment, warehouse, carrier, and route events."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(data.router, prefix="/api")
app.include_router(simulate.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "CC2 Logistics Simulation",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}