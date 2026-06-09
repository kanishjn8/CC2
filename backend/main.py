"""
Routesense — Logistics Simulation & Data Layer
FastAPI application entry point.
"""

import asyncio
import logging
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
from app.routers import data, simulate
from app.routers.geo import router as geo_router
from app.routers.agent import router as agent_router
from app.routers.actions import router as actions_router
from app.config import SEED_WAREHOUSES, SEED_CARRIERS, SEED_ROUTES, SEED_SHIPMENTS, ALLOWED_ORIGINS
from app.ai_agent import agent_loop
from app.lifecycle import lifecycle_manager

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy third-party loggers
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

log = logging.getLogger("cc2.main")

# ── App-wide readiness flag ───────────────────────────────────────────────────
_ready = False


def _wait_for_db(retries: int = 20, delay: float = 3.0):
    """Block until PostgreSQL accepts connections."""
    import app.config as cfg
    try:
        from urllib.parse import urlparse
        parsed = urlparse(cfg.DATABASE_URL)
        log.info("🔌 Connecting to DB host: %s:%s/%s", parsed.hostname, parsed.port, parsed.path.lstrip("/"))
    except Exception:
        pass

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("✅ Database is ready.")
            return
        except OperationalError as e:
            last_error = e
            log.warning("⏳ Waiting for database… (attempt %d/%d): %s", attempt, retries, str(e)[:200])
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to the database after {retries} retries. Last error: {last_error}")


async def _startup_task():
    """Run all heavy startup work in a background task so /health responds immediately."""
    global _ready
    try:
        log.info("=" * 60)
        log.info("CCRoutesense2 Logistics Platform — starting up")
        log.info("=" * 60)

        # Run blocking DB wait in a thread so we don't block the event loop
        await asyncio.get_event_loop().run_in_executor(None, _wait_for_db)

        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.commit()
        log.info("✅ PostGIS extension verified.")

        Base.metadata.create_all(bind=engine)
        log.info("✅ Database tables created / verified.")

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
        log.info("✅ Simulation engine started.")

        agent_loop.initialize()
        agent_loop.start()
        log.info("✅ AI Agent loop started.")

        lifecycle_manager.start()
        log.info("✅ Shipment lifecycle manager started.")

        _ready = True
        log.info("=" * 60)
        log.info("Routesense is ready 🚀")
        log.info("=" * 60)

    except Exception as exc:
        log.exception("❌ Startup failed: %s", exc)
        # Don't re-raise — keep server alive so Railway doesn't restart loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fire startup in background — /health is available immediately
    task = asyncio.create_task(_startup_task())

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    log.info("Shutting down…")
    task.cancel()
    lifecycle_manager.stop()
    simulation.stop()
    agent_loop.stop()
    log.info("✅ All background services stopped.")


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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(data.router, prefix="/api")
app.include_router(simulate.router, prefix="/api")
app.include_router(geo_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(actions_router, prefix="/api")


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "CC2 Logistics Simulation",
        "status": "ready" if _ready else "starting",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    # Always return 200 — Railway healthcheck just needs the process to be alive.
    # The _ready flag tells you if full init is done.
    return {"status": "ok", "ready": _ready}
