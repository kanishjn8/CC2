"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/cc2_db",
)

# SQLite fallback — used automatically when PostgreSQL is unreachable
SQLITE_FALLBACK_URL: str = os.getenv(
    "SQLITE_FALLBACK_URL",
    "sqlite:///./cc2_local.db",
)

# Set to "true" to always use SQLite regardless of DATABASE_URL
FORCE_SQLITE: bool = os.getenv("FORCE_SQLITE", "false").lower() in ("true", "1", "yes")

# Simulation defaults
SIM_TICK_INTERVAL: float = float(os.getenv("SIM_TICK_INTERVAL", "2.0"))   # seconds between ticks
SIM_SPEED: float = float(os.getenv("SIM_SPEED", "10.0"))                  # sim-minutes per real-second
EVENT_RETENTION_HOURS: int = int(os.getenv("EVENT_RETENTION_HOURS", "72"))

# Seed counts
SEED_WAREHOUSES: int = int(os.getenv("SEED_WAREHOUSES", "5"))
SEED_CARRIERS: int = int(os.getenv("SEED_CARRIERS", "8"))
SEED_ROUTES: int = int(os.getenv("SEED_ROUTES", "12"))
SEED_SHIPMENTS: int = int(os.getenv("SEED_SHIPMENTS", "20"))

# Agent configuration
AGENT_TICK_INTERVAL: float = float(os.getenv("AGENT_TICK_INTERVAL", "10.0"))
RISK_THRESHOLD: float = float(os.getenv("RISK_THRESHOLD", "0.6"))

# Gemini LLM configuration
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_PRIMARY_MODEL: str = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.1-flash")
GEMINI_FALLBACK_MODEL: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite")
BOTTLENECK_THRESHOLD: float = float(os.getenv("BOTTLENECK_THRESHOLD", "0.85"))
CARRIER_RELIABILITY_THRESHOLD: float = float(os.getenv("CARRIER_RELIABILITY_THRESHOLD", "0.5"))
