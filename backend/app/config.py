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
SEED_SHIPMENTS: int = int(os.getenv("SEED_SHIPMENTS", "60"))

# Agent defaults
AGENT_TICK_INTERVAL: float = float(os.getenv("AGENT_TICK_INTERVAL", "60.0"))  # 1 minute between cycles
RISK_THRESHOLD: float = float(os.getenv("RISK_THRESHOLD", "0.6"))
BOTTLENECK_THRESHOLD: float = float(os.getenv("BOTTLENECK_THRESHOLD", "0.85"))
CARRIER_RELIABILITY_THRESHOLD: float = float(os.getenv("CARRIER_RELIABILITY_THRESHOLD", "0.5"))

# LLM rate-limiting — minimum seconds between any two LLM API calls
LLM_CALL_COOLDOWN: float = float(os.getenv("LLM_CALL_COOLDOWN", "30.0"))  # 30 seconds default

# Gemini LLM
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_PRIMARY_MODEL: str = os.getenv("GEMINI_PRIMARY_MODEL", "models/gemini-2.0-flash")
GEMINI_FALLBACK_MODEL: str = os.getenv("GEMINI_FALLBACK_MODEL", "models/gemini-2.0-flash-lite")

# SMTP Email (for alert actions)
SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
ALERT_EMAIL_FROM: str = os.getenv("ALERT_EMAIL_FROM", "alerts@routesense.ai")
ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "")  # comma-separated list
# Minimum seconds between emails for the *same* entity (per-entity cooldown)
ALERT_EMAIL_COOLDOWN: float = float(os.getenv("ALERT_EMAIL_COOLDOWN", "300.0"))  # 5 minutes default

# Shipment lifecycle manager
LIFECYCLE_TICK_INTERVAL: float = float(os.getenv("LIFECYCLE_TICK_INTERVAL", "10.0"))
LIFECYCLE_GRACE_PERIOD: float = float(os.getenv("LIFECYCLE_GRACE_PERIOD", "20.0"))  # seconds before pruning delivered shipments from map
LIFECYCLE_TARGET_ACTIVE: int = int(os.getenv("LIFECYCLE_TARGET_ACTIVE", "60"))      # target active shipment count

# CORS — comma-separated list of allowed frontend origins.
# In production set e.g. ALLOWED_ORIGINS=https://routesense.vercel.app
# Defaults to wildcard so local dev works without any .env entry.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: list[str] = (
    ["*"] if _raw_origins.strip() == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)
