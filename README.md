#+ CC2 — AI Logistics Control Center

CC2 is a full-stack, AI-assisted **logistics monitoring + control** demo.

It simulates a live logistics network (shipments, warehouses, carriers, routes), continuously emits events into Postgres, and runs an **Observe → Detect → Reason → Decide → Act → Learn** agent loop that turns those events into operator-facing decisions (reroutes, carrier switches, alerts).

This repo contains:

* **Backend** (`backend/`): FastAPI API + SimPy discrete-event simulator + LangGraph agent + Postgres/PostGIS persistence.
* **Frontend** (`frontend/`): Next.js dashboard UI that visualizes the system state and decisions.

---

## What the project does

### 1) Simulates operations

The simulation engine (`backend/app/simulation.py`) runs continuously and updates the database each tick:

* advances shipment status (`created → dispatched → in_transit → delivered`, plus `delayed` / `failed`)
* fluctuates warehouse load + congestion
* updates route traffic + weather
* occasionally injects disruptions (pickup failures, ETA drift, carrier degradation, congestion spikes)
* records every noteworthy change as a row in `simulation_events`

### 2) Exposes a real-time API

FastAPI routers (`backend/app/routers/`) expose read and control endpoints:

* list shipments/warehouses/carriers/routes
* retrieve the event stream
* create shipments and trigger scenario endpoints to force disruptions
* return GeoJSON for routes/points (PostGIS-backed) for map rendering

### 3) Runs an AI agent loop

The agent loop (`backend/app/ai_agent/agent.py`) runs in the background alongside the simulator:

* warm-starts an ML delay-risk model on synthetic data, then retrains it from resolved learning outcomes (`backend/app/ai_agent/risk_models.py`)
* compiles a LangGraph pipeline (`backend/app/ai_agent/graph.py`, `backend/app/ai_agent/nodes.py`)
* on each cycle, scans DB state/events and produces:
  * a structured set of detected risks
  * a decision recommendation with evidence + confidence
  * (optionally) an LLM-generated natural-language summary
* writes every decision to `decision_log` so the UI can show history and approvals
* snapshots delay-risk model features into decision evidence, resolves outcomes, and periodically retrains the delay model with real learning samples

### 4) Enables action + approval workflows

Two ways actions can happen:

* **Agent approval workflow**: `POST /api/agent/approve/{decision_id}` executes the recommended action when an operator approves.
* **Direct operator actions**: `POST /api/actions/*` endpoints let the UI trigger actions directly (for demo/MVP flows).

---

## Architecture (high-level)

```
┌───────────────────────────────────────────────────────────────────────┐
│                               Frontend                                │
│                        Next.js dashboard (React)                       │
│  - consumes REST API + renders maps, tables, decision timelines        │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ HTTP (JSON)
┌───────────────────────────────┴───────────────────────────────────────┐
│                                Backend                                 │
│                                FastAPI                                 │
│  Routers: /api/data, /api/simulate, /api/geo, /api/agent, /api/actions │
│                                                                       │
│  Background services (started on app startup):                          │
│   1) SimPy Simulation thread  → updates entities + writes events        │
│   2) LangGraph Agent thread    → detects risks + logs decisions         │
│   3) Lifecycle manager         → keeps population of active shipments   │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ SQLAlchemy
┌───────────────────────────────┴───────────────────────────────────────┐
│                         PostgreSQL 16 + PostGIS                         │
│  Tables: shipments, warehouse_state, carrier_performance, routes,       │
│         simulation_events, decision_log                                 │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Tech stack

### Backend

* **FastAPI** (API framework) + **Uvicorn** (ASGI server)
* **SQLAlchemy 2.x** (ORM)
* **PostgreSQL 16** + **PostGIS** (spatial types: points, linestrings)
* **GeoAlchemy2 + Shapely** (geometry conversions)
* **SimPy** (discrete-event simulation)
* **LangGraph** (agent graph orchestration)
* **google-genai** (Gemini client used by the LLM node; optional)
* **scikit-learn / pandas / numpy** (feature engineering + ML delay-risk model)
* **uv** (Python packaging + lockfile)

### Frontend

* **Next.js 15** (React 19)
* **TypeScript**
* **Tailwind CSS** + **shadcn/ui** (Radix primitives)
* Charts: **Recharts**
* Maps: **react-simple-maps**

---

## Repository tour (what each folder/file is for)

### Root

* `README.md` — this document
* `docs/risk-model-feedback-loop.md` — how resolved learning outcomes retrain the delay-risk model
* `pyproject.toml` — intentionally minimal (real configs live in `backend/` and `frontend/`)
* `uv.lock` — lockfile for the root (mostly unused; backend has its own)

### `backend/` (FastAPI + simulation + agent)

* `backend/main.py` — FastAPI entrypoint; starts background services; defines `/health`
* `backend/app/`
  * `config.py` — environment variables (DB URL, tick intervals, thresholds, origins)
  * `database.py` — SQLAlchemy engine/session
  * `models.py` — ORM schema (shipments, routes, events, decision log)
  * `schemas.py` — Pydantic response/request models
  * `seed.py` — seed initial warehouses/carriers/routes/shipments
  * `simulation.py` — SimPy simulation engine producing live events
  * `lifecycle.py` — keeps system “alive” (maintains active shipment set)
  * `routers/`
    * `data.py` — read APIs (shipments/warehouses/carriers/routes/events)
    * `simulate.py` — simulation control + scenario triggers
    * `geo.py` — geo endpoints returning GeoJSON (for map UI)
    * `agent.py` — agent endpoints (risks, decisions, approvals, summaries)
    * `actions.py` — direct operator action endpoints (alert/reroute/switch carrier)
  * `ai_agent/` — core decision engine
    * `agent.py` — background `AgentLoop`
    * `graph.py` / `nodes.py` — LangGraph pipeline definition
    * `risk_models.py` — ML delay risk model with synthetic warm-start + hybrid retraining
    * `actions.py` — action implementations used by agent + operator endpoints
    * `llm_client.py` — Gemini client + fallback behaviors
    * `learning.py` — metrics/learning loop fed by outcomes, including delay-model retraining samples
* `backend/docker-compose.yaml` — local dev stack (Postgres + API)
* `backend/Dockerfile` — container build used for Railway
* `backend/railway.toml` — Railway service config (healthcheck etc.)
* `backend/schema.sql` — DDL snapshot (useful for inspection/bootstrapping)
* `backend/tests/` — pytest suite

### `frontend/` (Next.js dashboard)

* `frontend/app/` — route tree (Next App Router pages)
* `frontend/components/` — UI building blocks (tables, charts, maps, reasoning)
* `frontend/lib/api.ts` — API client + `NEXT_PUBLIC_API_URL` wiring
* `frontend/package.json` — frontend deps + scripts

---

## How the backend starts (important)

`backend/main.py` uses FastAPI lifespan to start heavy work in a **background task**:

1. wait for Postgres (`SELECT 1` retry loop)
2. ensure PostGIS extension exists (`CREATE EXTENSION IF NOT EXISTS postgis`)
3. `Base.metadata.create_all(...)` to create/verify tables
4. seed initial data (idempotent)
5. start simulation thread
6. start agent loop thread
7. start lifecycle manager

`GET /health` always returns HTTP 200 with `{ ready: boolean }` so container health checks don’t fail during the longer initialization.

---

## Running locally

### Prerequisites

* Docker + Docker Compose
* For host-based backend dev: Python 3.11+ + `uv`
* For frontend dev: Node.js (npm)

### Option A — backend + database via Docker Compose

From the `backend/` folder:

```bash
docker compose up --build
```

API:

* http://localhost:8000
* Swagger docs: http://localhost:8000/docs

### Option B — Postgres in Docker, FastAPI on your machine (best for debugging)

```bash
cd backend
docker compose up postgres -d
cp .env.example .env
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Set the API base URL:

* Local dev: defaults to `http://localhost:8000`
* For deployments: set `NEXT_PUBLIC_API_URL=https://<your-backend-domain>`

---

## Environment variables (backend)

Backend env vars live in `backend/.env.example` and are read by `backend/app/config.py`.

Common ones:

* `DATABASE_URL` — Postgres connection string
* `SIM_TICK_INTERVAL` — real seconds between ticks (default `2.0`)
* `SIM_SPEED` — sim minutes advanced per real second (default `10.0`)
* `SEED_WAREHOUSES`, `SEED_CARRIERS`, `SEED_ROUTES`, `SEED_SHIPMENTS`
* `AGENT_TICK_INTERVAL` — seconds between agent cycles
* thresholds such as `RISK_THRESHOLD`, `BOTTLENECK_THRESHOLD`, `CARRIER_RELIABILITY_THRESHOLD`
* delay-model retraining knobs such as `RISK_MODEL_RETRAIN_INTERVAL_CYCLES`, `RISK_MODEL_RETRAIN_MIN_SAMPLES`, `RISK_MODEL_RETRAIN_SYNTHETIC_SAMPLES`, `RISK_MODEL_REAL_SAMPLE_WEIGHT`
* LLM settings such as `GEMINI_API_KEY`, `LLM_CALL_COOLDOWN`
* CORS allowlist: `ALLOWED_ORIGINS`

## Risk model feedback loop

The delay-risk model starts with synthetic data so the agent can score shipments immediately after startup. As the agent acts, delay-risk decisions store their exact model feature snapshot in `decision_log.evidence`. The Learn step later resolves those decisions into actual labels (`success` means within SLA, `failed` means missed/projected-missed SLA or failed) and periodically retrains the active model with a hybrid synthetic + real dataset.

See `docs/risk-model-feedback-loop.md` for the full flow, configuration, and current limitations.

---

## API overview

All backend endpoints are served under the FastAPI app in `backend/main.py`.

### Health

* `GET /` — service info (includes `status: starting|ready`)
* `GET /health` — liveness + readiness flag

### Core data (read)

* `GET /api/shipments`
* `GET /api/warehouses`
* `GET /api/carriers`
* `GET /api/routes`
* `GET /api/events`

### Simulation control

* `POST /api/simulate/start`
* `POST /api/simulate/stop`
* `GET /api/simulate/status`
* scenario triggers like `warehouse-congestion`, `traffic-spike`, `pickup-failure`, `eta-drift`, etc.

### Agent endpoints

* `GET /api/agent/status`
* `GET /api/agent/risks`
* `GET /api/agent/decisions`
* `POST /api/agent/analyze` (manual cycle)
* `POST /api/agent/approve/{decision_id}` (approval workflow)
* `GET /api/agent/summary`

### Operator actions

* `POST /api/actions/send-alert`
* `POST /api/actions/reroute`
* `POST /api/actions/switch-carrier` (if enabled in `actions.py`)

---

## Database schema (conceptual)

These are the main tables.

* `shipments` — shipments with status, ETA/SLA, and optional geometry points
* `warehouse_state` — capacity/load/queue/congestion and optional geometry
* `carrier_performance` — reliability, delay probability, pickup rate, totals
* `routes` — origin/destination, distance, traffic/weather, optional line geometry
* `simulation_events` — immutable event stream emitted by simulator
* `decision_log` — agent decision history + approval / outcome tracking

For full DDL, see `backend/schema.sql`.

---

## Deployment notes (Railway/Vercel)

This repo has been used with:

* **Railway** for backend + Postgres
  * `backend/Dockerfile` runs `uvicorn main:app` on port `8000`
  * `backend/railway.toml` sets healthcheck path `/health`
* **Vercel** for frontend
  * remember `NEXT_PUBLIC_API_URL` must include `https://`

---

## Tests

Backend tests live in `backend/tests/`.

```bash
cd backend
uv run pytest
```

| `carrier` | VARCHAR(64) | Assigned carrier ID |
| `route_id` | VARCHAR(64) | Route ID |
| `eta` | TIMESTAMP | Estimated time of arrival |
| `sla_deadline` | TIMESTAMP | SLA deadline |
| `status` | ENUM | `created` · `dispatched` · `in_transit` · `at_warehouse` · `out_for_delivery` · `delivered` · `delayed` · `failed` |

### `warehouse_state`
| Column | Type | Description |
|--------|------|-------------|
| `warehouse_id` | VARCHAR(64) | Unique identifier |
| `location` | VARCHAR(128) | City |
| `capacity` | INT | Maximum load |
| `current_load` | INT | Current load |
| `queue_length` | INT | Queued shipments |
| `congestion_score` | FLOAT | Computed metric (0 – 1) |

### `carrier_performance`
| Column | Type | Description |
|--------|------|-------------|
| `carrier_id` | VARCHAR(64) | Unique identifier |
| `name` | VARCHAR(128) | Carrier name |
| `reliability_score` | FLOAT | Historical reliability (0 – 1) |
| `delay_probability` | FLOAT | Delay likelihood |
| `pickup_success_rate` | FLOAT | Pickup success rate |
| `total_shipments` | INT | Lifetime shipments |
| `total_delays` | INT | Lifetime delays |

### `routes`
| Column | Type | Description |
|--------|------|-------------|
| `route_id` | VARCHAR(64) | Unique identifier |
| `origin` | VARCHAR(128) | Start city |
| `destination` | VARCHAR(128) | End city |
| `distance` | FLOAT | Distance in km |
| `traffic_level` | ENUM | `low` · `moderate` · `high` · `severe` |
| `weather_factor` | FLOAT | Weather multiplier (1.0 = clear) |

### `simulation_events`
| Column | Type | Description |
|--------|------|-------------|
| `event_type` | ENUM | Event category |
| `entity_id` | VARCHAR(64) | Related entity ID |
| `payload` | TEXT (JSON) | Event detail payload |
| `sim_time` | FLOAT | Simulation clock value |
| `created_at` | TIMESTAMP | Wall-clock timestamp |

### Event types

| Event | Trigger |
|-------|---------|
| `shipment_created` | New shipment added |
| `shipment_dispatched` | Shipment picked up by carrier |
| `shipment_delivered` | Shipment reaches destination |
| `shipment_delayed` | Shipment status moves to delayed |
| `warehouse_load_update` | Warehouse load changes |
| `warehouse_congestion` | Congestion score exceeds 0.85 |
| `carrier_delay_event` | Carrier reliability degrades |
| `carrier_failure` | Manual carrier failure scenario |
| `route_traffic_update` | Traffic or weather changes on a route |
| `pickup_failure` | Carrier fails to pick up a shipment |
| `eta_drift` | ETA pushed forward due to disruption |

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │  Data API     │  │ Simulate API │  │  Health / Docs    │ │
│  │ /api/shipments│  │ /api/simulate│  │  / , /health      │ │
│  │ /api/warehouses│ │   /start     │  │  /docs (Swagger)  │ │
│  │ /api/carriers │  │   /stop      │  └───────────────────┘ │
│  │ /api/routes   │  │   /status    │                        │
│  │ /api/events   │  │   /warehouse-│                        │
│  └──────┬───────┘  │    congestion │                        │
│         │          │   /carrier-   │                        │
│         │          │    failure    │                        │
│         │          │   /traffic-   │                        │
│         │          │    spike      │                        │
│         │          └──────┬───────┘                         │
│  ┌──────┴─────────────────┴──────────────┐                  │
│  │       SimPy Simulation Engine         │                  │
│  │  • Shipment lifecycle transitions     │                  │
│  │  • Warehouse load fluctuations        │                  │
│  │  • Route traffic / weather updates    │                  │
│  │  • Random disruptions                 │                  │
│  └──────────────────┬────────────────────┘                  │
│                     │                                       │
│  ┌──────────────────┴────────────────────┐                  │
│  │   PostgreSQL (SQLAlchemy ORM)         │                  │
│  │  • shipments       • warehouse_state  │                  │
│  │  • carrier_performance  • routes      │                  │
│  │  • simulation_events                  │                  │
│  └───────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Simulation | SimPy (discrete-event) |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Data | Pandas, NumPy |
| Package Manager | uv |

## Quick Start

### 1. Start PostgreSQL

```bash
docker compose up -d
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Run the server

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at **http://localhost:8000** and the interactive docs at **http://localhost:8000/docs**.

On startup, the server will:
- Create all database tables
- Seed initial warehouses, carriers, routes, and shipments
- Start the background simulation engine

## API Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

### Data (read)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/shipments` | List shipments (filter by status) |
| GET | `/api/shipments/{id}` | Get single shipment |
| GET | `/api/warehouses` | List warehouses (sorted by congestion) |
| GET | `/api/warehouses/{id}` | Get single warehouse |
| GET | `/api/carriers` | List carriers (sorted by reliability) |
| GET | `/api/carriers/{id}` | Get single carrier |
| GET | `/api/routes` | List all routes |
| GET | `/api/routes/{id}` | Get single route |
| GET | `/api/events` | List events (filter by type, entity) |

### Simulation Control
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/simulate/start` | Start the simulation engine |
| POST | `/api/simulate/stop` | Stop the simulation engine |
| GET | `/api/simulate/status` | Engine status + counts |
| POST | `/api/simulate/warehouse-congestion` | Trigger warehouse congestion |
| POST | `/api/simulate/carrier-failure` | Trigger carrier failure cascade |
| POST | `/api/simulate/traffic-spike` | Trigger traffic spike on routes |
| POST | `/api/simulate/pickup-failure` | Trigger a pickup failure |
| POST | `/api/simulate/eta-drift` | Trigger ETA drift on shipments |
| POST | `/api/simulate/create-shipment` | Create a new shipment on the fly |

## Database Schema

### `shipments`
| Column | Type | Description |
|--------|------|-------------|
| shipment_id | VARCHAR(64) | Unique identifier |
| origin | VARCHAR(128) | Source location |
| destination | VARCHAR(128) | Target location |
| carrier | VARCHAR(64) | Assigned carrier ID |
| route_id | VARCHAR(64) | Route ID |
| eta | TIMESTAMP | Estimated time of arrival |
| sla_deadline | TIMESTAMP | SLA deadline |
| status | ENUM | created, dispatched, in_transit, at_warehouse, out_for_delivery, delivered, delayed, failed |

### `warehouse_state`
| Column | Type | Description |
|--------|------|-------------|
| warehouse_id | VARCHAR(64) | Unique identifier |
| location | VARCHAR(128) | City |
| capacity | INT | Maximum load |
| current_load | INT | Current load |
| queue_length | INT | Queued shipments |
| congestion_score | FLOAT | Computed metric (0-1) |

### `carrier_performance`
| Column | Type | Description |
|--------|------|-------------|
| carrier_id | VARCHAR(64) | Unique identifier |
| name | VARCHAR(128) | Carrier name |
| reliability_score | FLOAT | Historical reliability (0-1) |
| delay_probability | FLOAT | Delay likelihood |
| pickup_success_rate | FLOAT | Pickup success rate |
| total_shipments | INT | Lifetime shipments |
| total_delays | INT | Lifetime delays |

### `routes`
| Column | Type | Description |
|--------|------|-------------|
| route_id | VARCHAR(64) | Unique identifier |
| origin | VARCHAR(128) | Start city |
| destination | VARCHAR(128) | End city |
| distance | FLOAT | Distance in km |
| traffic_level | ENUM | low, moderate, high, severe |
| weather_factor | FLOAT | Weather multiplier |

### `simulation_events`
| Column | Type | Description |
|--------|------|-------------|
| event_type | ENUM | Event category |
| entity_id | VARCHAR(64) | Related entity |
| payload | TEXT (JSON) | Event details |
| sim_time | FLOAT | Simulation clock |
| created_at | TIMESTAMP | Wall-clock time |

## Event Types

- `shipment_created` / `shipment_dispatched` / `shipment_delivered` / `shipment_delayed`
- `warehouse_load_update` / `warehouse_congestion`
- `carrier_delay_event` / `carrier_failure`
- `route_traffic_update`
- `pickup_failure`
- `eta_drift`
