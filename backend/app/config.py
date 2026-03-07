"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/cc2_db",
)

# Simulation defaults
SIM_TICK_INTERVAL: float = float(os.getenv("SIM_TICK_INTERVAL", "2.0"))   # seconds between ticks
SIM_SPEED: float = float(os.getenv("SIM_SPEED", "10.0"))                  # sim-minutes per real-second
EVENT_RETENTION_HOURS: int = int(os.getenv("EVENT_RETENTION_HOURS", "72"))

# Seed counts (new global defaults — much larger dataset)
SEED_WAREHOUSES: int = int(os.getenv("SEED_WAREHOUSES", "10"))
SEED_CARRIERS: int = int(os.getenv("SEED_CARRIERS", "12"))
SEED_ROUTES: int = int(os.getenv("SEED_ROUTES", "30"))
SEED_SHIPMENTS: int = int(os.getenv("SEED_SHIPMENTS", "40"))

# Agent defaults
AGENT_TICK_INTERVAL: float = float(os.getenv("AGENT_TICK_INTERVAL", "60.0"))  # 1 minute between cycles
RISK_THRESHOLD: float = float(os.getenv("RISK_THRESHOLD", "0.6"))
BOTTLENECK_THRESHOLD: float = float(os.getenv("BOTTLENECK_THRESHOLD", "0.85"))
CARRIER_RELIABILITY_THRESHOLD: float = float(os.getenv("CARRIER_RELIABILITY_THRESHOLD", "0.5"))

# LLM rate-limiting — minimum seconds between any two LLM API calls
LLM_CALL_COOLDOWN: float = float(os.getenv("LLM_CALL_COOLDOWN", "300.0"))  # 5 minutes default

# Gemini LLM
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_PRIMARY_MODEL: str = os.getenv("GEMINI_PRIMARY_MODEL", "models/gemini-3-flash-preview")
GEMINI_FALLBACK_MODEL: str = os.getenv("GEMINI_FALLBACK_MODEL", "models/gemini-3-flash-lite-preview")
