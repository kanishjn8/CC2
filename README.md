# RouteSense — AI-Powered Autonomous Logistics Agent

An autonomous AI agent that continuously monitors a global logistics network, detects risks before they cascade, and intervenes to prevent SLA breaches — built with LangGraph, FastAPI, SimPy, Gemini, scikit-learn, and Next.js.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [AI Agent Pipeline](#ai-agent-pipeline)
  - [Observe](#1-observe)
  - [Detect](#2-detect)
  - [Reason](#3-reason)
  - [Decide](#4-decide)
  - [Act](#5-act)
  - [Learn](#6-learn)
- [ML Risk Model](#ml-risk-model)
- [LLM Integration](#llm-integration)
- [Simulation Engine](#simulation-engine)
- [Lifecycle Manager](#lifecycle-manager)
- [Frontend Dashboard](#frontend-dashboard)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Option A — Full Stack with Docker](#option-a--full-stack-with-docker-recommended)
  - [Option B — Local Development](#option-b--local-development)
  - [Frontend](#frontend)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Seed Data](#seed-data)
- [Running Tests](#running-tests)

---

## Overview

RouteSense is an end-to-end logistics monitoring platform with an autonomous AI agent at its core. The system simulates a global logistics network of **60+ shipments, 10 warehouses, 12 carriers, and 30 routes** spanning 60+ cities worldwide — then deploys an AI agent that runs a continuous **observe → detect → reason → decide → act → learn** loop to prevent SLA breaches before they happen.

**What the agent catches:**

| Risk Type | Detection Method | Threshold |
|-----------|-----------------|-----------|
| Shipment Delay | Gradient Boosting ML model | Probability > 0.6 |
| Warehouse Bottleneck | Rule-based (load/capacity) | Congestion > 85% |
| Carrier Degradation | Rule-based (reliability) | Reliability < 0.5 |

**What the agent can do:**

| Action | Type | Description |
|--------|------|-------------|
| Reroute Shipment | Requires Approval | Find lower-traffic, better-weather route |
| Switch Carrier | Requires Approval | Assign more reliable carrier |
| Prioritize Loading | Autonomous | Fast-track shipment through warehouse queue |
| Reserve Capacity | Autonomous | Pre-allocate warehouse space |
| Send Alert | Autonomous | Email ops team with risk details |

---

It simulates a live logistics network (shipments, warehouses, carriers, routes), continuously emits events into Postgres, and runs an **Observe → Detect → Reason → Decide → Act → Learn** agent loop that turns those events into operator-facing decisions (reroutes, carrier switches, alerts).

```
┌──────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                             │
│  Overview · Shipments · Decisions · Carriers · Warehouses · Sim  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ REST API (polling 8–30s)
┌──────────────────────────┴───────────────────────────────────────┐
│                    FastAPI Backend                                │
│                                                                  │
│  ┌──────────┐ ┌───────────┐ ┌─────────┐ ┌────────┐ ┌────────┐  │
│  │ Data API │ │Simulate   │ │ Geo API │ │Agent   │ │Actions │  │
│  │ /api/data│ │/api/sim   │ │ /api/geo│ │/agent  │ │/actions│  │
│  └────┬─────┘ └─────┬─────┘ └────┬────┘ └────┬───┘ └───┬────┘  │
│       │              │            │           │         │        │
│  ┌────┴──────────────┴────────────┴───────────┴─────────┴────┐  │
│  │                  Background Threads                        │  │
│  │                                                            │  │
│  │  ┌─────────────────┐  ┌───────────────┐  ┌────────────┐  │  │
│  │  │ SimPy Simulation│  │ AI Agent Loop │  │ Lifecycle  │  │  │
│  │  │  (every 2s)     │  │ (every 60s)   │  │ Manager    │  │  │
│  │  │                 │  │               │  │ (every 10s)│  │  │
│  │  │ • Transitions   │  │ LangGraph:    │  │            │  │  │
│  │  │ • Fluctuations  │  │ observe →     │  │ • Prune    │  │  │
│  │  │ • Disruptions   │  │ detect →      │  │ • Spawn    │  │  │
│  │  │                 │  │ reason →      │  │ • Disrupt  │  │  │
│  │  │                 │  │ decide →      │  │            │  │  │
│  │  │                 │  │ act → learn   │  │            │  │  │
│  │  └────────┬────────┘  └───────┬───────┘  └─────┬─────┘  │  │
│  └───────────┼───────────────────┼─────────────────┼────────┘  │
│              │                   │                  │           │
│  ┌───────────┴───────────────────┴─────────────────┴────────┐  │
│  │          PostgreSQL 16 + PostGIS (SQLAlchemy ORM)         │  │
│  │  shipments · warehouse_state · carrier_performance        │  │
│  │  routes · simulation_events · decision_log                │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

Three background threads run concurrently and coordinate through the shared PostgreSQL database:
1. **SimPy Simulation** — generates logistics events every 2 seconds
2. **AI Agent** — full analysis cycle every 60 seconds via LangGraph
3. **Lifecycle Manager** — maintains active shipment count every 10 seconds

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React, Tailwind CSS, Radix UI, Recharts |
| API | FastAPI + Uvicorn |
| AI Agent | LangGraph (StateGraph) |
| LLM | Google Gemini 2.0 Flash |
| ML | scikit-learn (Gradient Boosting Classifier) |
| Simulation | SimPy (discrete-event) |
| Database | PostgreSQL 16 + PostGIS |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 |
| Geospatial | PostGIS, Shapely, GeoAlchemy2 |
| Infra | Docker Compose, uv |

---

## AI Agent Pipeline

The agent implements a **6-node LangGraph StateGraph** with conditional routing:

```
observe → detect_risks ─┬─ (risks found) → reason → decide → act → learn → END
                        └─ (no risks) ──────────────────────→ learn → END
```

### 1. Observe

**File:** `backend/app/ai_agent/nodes.py` — `observe_node()`

Queries the database for the current state of the entire logistics network:
- All active shipments (not delivered/failed)
- All warehouses with capacity, load, congestion scores
- All carriers with reliability, delay probability, pickup rates
- All routes with traffic levels, weather factors
- Serializes ORM objects into plain dicts for LangGraph state (checkpointable)

### 2. Detect

**File:** `backend/app/ai_agent/nodes.py` — `detect_risks_node()`

Runs three detection mechanisms:

| Detector | Method | Threshold |
|----------|--------|-----------|
| **Delay Risk** | Gradient Boosting ML model on 8 features | Score > 0.6 |
| **Bottleneck** | Rule-based: `congestion_score > threshold` | > 0.85 |
| **Carrier Degradation** | Rule-based: `reliability_score < threshold` | < 0.5 |

**Deduplication:** Before flagging any risk, checks `has_pending_decision(entity_id, risk_type)` — skips entities that already have an unresolved decision.

### 3. Reason

**File:** `backend/app/ai_agent/nodes.py` — `reason_node()`

Generates human-readable explanations for each detected risk:

- **LLM-first approach:** Sends risk context to Gemini, expects structured JSON with `problem`, `root_cause`, `confidence`
- **Rule-based fallback:** If LLM is unavailable or rate-limited, generates explanations from identified factors
- **Evidence collected:** traffic level, weather factor, warehouse congestion %, carrier reliability, SLA buffer hours, distance

### 4. Decide

**File:** `backend/app/ai_agent/nodes.py` — `decide_node()`

Scores every possible action on 4 weighted criteria:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| SLA Improvement | 55% | Direct SLA compliance gain |
| Operational Risk | 20% | Risk of making things worse |
| Cost Impact | 15% | Operational cost efficiency |
| Reversibility | 10% | Ease of undoing the action |

**Guardrail system:**
- **Autonomous** (auto-execute): `prioritize_loading`, `send_alert`, `reserve_capacity`
- **Requires approval** (human-in-the-loop): `reroute_shipment`, `switch_carrier`

**LLM tiebreaker:** If the top 2 actions score within ±0.05, Gemini is asked to pick the better one with full context.

### 5. Act

**File:** `backend/app/ai_agent/nodes.py` — `act_node()`

Executes autonomous actions immediately and logs approval-required ones for human review:

| Action | What It Does |
|--------|-------------|
| `reroute_shipment` | Find best alternative route (low traffic, low weather), update shipment, improve ETA |
| `switch_carrier` | Assign highest-reliability carrier, update shipment |
| `prioritize_loading` | Reduce warehouse queue, fast-track dispatch |
| `reserve_capacity` | Pre-allocate warehouse space |
| `send_alert` | Rate-limited SMTP email (5-min global cooldown) + DB log |

All decisions are written to the `decision_log` table with full audit trail.

### 6. Learn

**File:** `backend/app/ai_agent/nodes.py` — `learn_node()`

Closes the feedback loop:

1. **`evaluate_outcomes()`** — checks all pending decisions against current shipment states:
   - Delivered on time → `outcome = "success"`, compute hours saved
   - Missed SLA or failed → `outcome = "failed"`, compute hours lost
   - Still in transit → remains `"pending"`

2. **Aggregate metrics** — computes `intervention_success_rate`, `false_positive_rate`, per-risk-type and per-action breakdowns

3. **Cycle summary** — LLM-generated natural language summary of what happened

```
Cycle N:  observe → detect → reason → decide → act → learn
                                                       │
                                          evaluate_outcomes()
                                    (grades Cycle N-1 decisions)
                                                       │
Cycle N+1: detect ← has_pending_decision() ← skips already-handled risks
```

---

## ML Risk Model

**File:** `backend/app/ai_agent/risk_models.py`

| Aspect | Detail |
|--------|--------|
| Algorithm | `GradientBoostingClassifier` (100 trees, depth 4, LR 0.1) |
| Training | 5,000 synthetic logistics samples at startup |
| Normalization | `StandardScaler` on all features |
| Inference | ~1ms per prediction |
| Fallback | Heuristic weighted average if model is untrained |

**8 Input Features:**

| Feature | Source | Range |
|---------|--------|-------|
| `distance` | Route | 100–2500 km |
| `traffic_level` | Route | 0 (low) – 3 (severe) |
| `weather_factor` | Route | 0.5 – 2.0 |
| `congestion_score` | Warehouse | 0.0 – 1.0 |
| `reliability_score` | Carrier | 0.0 – 1.0 |
| `delay_probability` | Carrier | 0.0 – 1.0 |
| `pickup_success_rate` | Carrier | 0.0 – 1.0 |
| `eta_sla_buffer_hours` | Shipment | Hours until SLA deadline |

**Output:** Delay probability (0.0 – 1.0). Threshold: **0.6** triggers the risk pipeline.

Feature importance is exposed via `GET /agent/feature-importance`.

---

## LLM Integration

**File:** `backend/app/ai_agent/llm_client.py`

**Three-tier fallback chain:**
```
Gemini 2.0 Flash → Gemini 2.0 Flash Lite → Rule-based heuristics
```

The agent **never fails** — if both LLM models are down or rate-limited, rule-based reasoning kicks in immediately.

| Setting | Default | Purpose |
|---------|---------|---------|
| `GEMINI_PRIMARY_MODEL` | `gemini-2.0-flash` | Primary LLM |
| `GEMINI_FALLBACK_MODEL` | `gemini-2.0-flash-lite` | Fallback LLM |
| `LLM_CALL_COOLDOWN` | 30 seconds | Minimum time between LLM calls |

**Used in:**
- **Reasoning:** Generate human-readable root cause explanations
- **Decision tiebreaking:** Choose between equally-scored actions
- **Cycle summaries:** Natural language summary of agent activity

LLM stats exposed via `GET /agent/llm-stats`.

---

## Simulation Engine

**File:** `backend/app/simulation.py`

A **SimPy discrete-event simulation** running in a background thread:

| Setting | Default | Description |
|---------|---------|-------------|
| `SIM_TICK_INTERVAL` | 2.0s | Real-seconds between ticks |
| `SIM_SPEED` | 10.0 | Sim-minutes per real-second |

**Each tick:**

1. **Advance shipments** — Probabilistic state transitions:
   - `created → dispatched` (~40%), `dispatched → in_transit` (~35%), `in_transit → delivered/delayed` (~25%)
   - Carrier reliability modulates delay probability
   - ETA interpolation via geospatial linear interpolation

2. **Fluctuate warehouses** — Random load changes (±20–25 per tick), congestion alerts at > 85%

3. **Fluctuate routes** — 25% chance per tick to randomize traffic level & weather factor

4. **Random disruptions** (one per tick):
   - **ETA drift** (12%): +1–6 hour delay on random shipment
   - **Pickup failure** (8%): Reduces carrier pickup_success_rate by 2%
   - **Carrier degradation** (6%): Reduces reliability by 3%, increases delay_prob by 2%

All events are logged to the `simulation_events` table.

**Manual disruption triggers** available via API:
- `POST /api/simulate/warehouse-congestion`
- `POST /api/simulate/carrier-failure`
- `POST /api/simulate/traffic-spike`
- `POST /api/simulate/pickup-failure`
- `POST /api/simulate/eta-drift`
- `POST /api/simulate/create-shipment`

---

## Lifecycle Manager

**File:** `backend/app/lifecycle.py`

Background thread (every 10s) that maintains a healthy shipment ecosystem:

1. **Stamp terminal shipments** — Mark delivered/failed shipments with `delivered_at` timestamp
2. **Prune expired** — After grace period (20s), set `is_active = False`
3. **Spawn replacements** — Create new shipments to maintain target active count (60)
4. **Inject disruptions** — Randomly delay 6% of in-transit/dispatched shipments

---

## Frontend Dashboard

**Directory:** `frontend/`

Six pages built with Next.js, Tailwind CSS, and Radix UI:

| Page | Key Features |
|------|-------------|
| **Overview** | 6 KPI cards, network health score, status distribution chart, live shipment map, warehouse utilization |
| **Shipments** | Searchable/filterable table, SLA breach detection, shipment detail drawer |
| **Decisions** | Decision log with expandable reasoning chains, approve/reject buttons, LLM stats |
| **Carriers** | Carrier performance metrics, reliability trends |
| **Warehouses** | Capacity monitoring, congestion alerts |
| **Simulator** | Manual disruption triggers for testing |

**Network Health Score:**
```
(1 − avg_congestion) × 0.3 + avg_reliability × 0.4 + on_time_rate × 0.3
```

**Data hooks** poll the backend at staggered intervals:

| Hook | Interval |
|------|----------|
| `useEvents()` | 8s |
| `useShipments()`, `useDecisions()`, `useAgentStatus()`, `useSimulationStatus()` | 10s |
| `useWarehouses()`, `useAgentMetrics()`, `useLlmStats()` | 15s |
| `useCarriers()` | 20s |
| `useRoutes()` | 30s |

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

Six tables on PostgreSQL 16 + PostGIS:

### `shipments`
| Column | Type | Description |
|--------|------|-------------|
| `shipment_id` | VARCHAR(64) PK | Unique identifier |
| `origin` | VARCHAR(128) | Source city |
| `destination` | VARCHAR(128) | Target city |
| `carrier` | VARCHAR(64) | Assigned carrier ID |
| `route_id` | VARCHAR(64) | Route ID |
| `eta` | TIMESTAMP | Estimated time of arrival |
| `sla_deadline` | TIMESTAMP | SLA deadline |
| `status` | ENUM | `created` · `dispatched` · `in_transit` · `at_warehouse` · `out_for_delivery` · `delivered` · `delayed` · `failed` |
| `current_location` | GEOMETRY(POINT) | Current geospatial position |
| `origin_point` | GEOMETRY(POINT) | Origin coordinates |
| `destination_point` | GEOMETRY(POINT) | Destination coordinates |
| `is_active` | BOOLEAN | Whether shipment is visible |
| `delivered_at` | TIMESTAMP | When delivery completed |

### `warehouse_state`
| Column | Type | Description |
|--------|------|-------------|
| `warehouse_id` | VARCHAR(64) PK | Unique identifier |
| `location` | VARCHAR(128) | City |
| `capacity` | INT | Maximum load |
| `current_load` | INT | Current load |
| `queue_length` | INT | Queued shipments |
| `congestion_score` | FLOAT | Load/capacity ratio (0–1) |
| `geom` | GEOMETRY(POINT) | Geospatial position |

### `carrier_performance`
| Column | Type | Description |
|--------|------|-------------|
| `carrier_id` | VARCHAR(64) PK | Unique identifier |
| `name` | VARCHAR(128) | Carrier name |
| `reliability_score` | FLOAT | Historical reliability (0–1) |
| `delay_probability` | FLOAT | Delay likelihood (0–1) |
| `pickup_success_rate` | FLOAT | Pickup success rate (0–1) |
| `total_shipments` | INT | Lifetime shipments |
| `total_delays` | INT | Lifetime delays |

### `routes`
| Column | Type | Description |
|--------|------|-------------|
| `route_id` | VARCHAR(64) PK | Unique identifier |
| `origin` | VARCHAR(128) | Start city |
| `destination` | VARCHAR(128) | End city |
| `distance` | FLOAT | Distance in km |
| `traffic_level` | ENUM | `low` · `moderate` · `high` · `severe` |
| `weather_factor` | FLOAT | Weather multiplier (1.0 = clear) |
| `path` | GEOMETRY(LINESTRING) | Route geometry |

### `simulation_events`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment |
| `event_type` | ENUM | Event category |
| `entity_id` | VARCHAR(64) | Related entity ID |
| `payload` | TEXT (JSON) | Event detail payload |
| `sim_time` | FLOAT | Simulation clock value |
| `created_at` | TIMESTAMP | Wall-clock timestamp |

### `decision_log`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment |
| `decision_id` | VARCHAR(64) | Unique decision identifier |
| `risk_type` | VARCHAR(64) | `delay_risk` · `bottleneck` · `carrier_degradation` |
| `entity_id` | VARCHAR(64) | Affected entity |
| `shipment_id` | VARCHAR(64) | Related shipment (nullable) |
| `risk_score` | FLOAT | ML/rule score (0–1) |
| `problem` | TEXT | Human-readable problem statement |
| `evidence` | TEXT (JSON) | Supporting evidence |
| `root_cause` | TEXT | Identified root cause |
| `confidence` | FLOAT | Agent confidence (0–1) |
| `recommended_action` | VARCHAR(64) | Selected action |
| `action_details` | TEXT (JSON) | Scoring breakdown + execution result |
| `requires_approval` | BOOLEAN | Human-in-the-loop flag |
| `status` | VARCHAR(32) | `executed` · `pending_approval` · `approved` · `rejected` |
| `outcome` | VARCHAR(32) | `pending` · `success` · `failed` · `rejected` |
| `sla_impact` | FLOAT | Hours saved (positive) or lost (negative) |
| `resolved_at` | TIMESTAMP | When outcome was determined |
| `created_at` | TIMESTAMP | When decision was made |

### Event Types

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

---

## API Reference

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

### Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/shipments` | List shipments (`?status=`, `?include_inactive=`, `?limit=`) |
| GET | `/api/shipments/{id}` | Get single shipment |
| GET | `/api/warehouses` | List warehouses (sorted by congestion) |
| GET | `/api/warehouses/{id}` | Get single warehouse |
| GET | `/api/carriers` | List carriers (sorted by reliability) |
| GET | `/api/carriers/{id}` | Get single carrier |
| GET | `/api/routes` | List all routes |
| GET | `/api/routes/{id}` | Get single route |
| GET | `/api/events` | List events (`?event_type=`, `?entity_id=`, `?limit=`) |

### Simulation Control

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/simulate/start` | Start the simulation engine |
| POST | `/api/simulate/stop` | Stop the simulation engine |
| GET | `/api/simulate/status` | Engine status + entity counts |
| POST | `/api/simulate/warehouse-congestion` | Trigger warehouse congestion scenario |
| POST | `/api/simulate/carrier-failure` | Trigger carrier failure cascade |
| POST | `/api/simulate/traffic-spike` | Trigger traffic spike on routes |
| POST | `/api/simulate/pickup-failure` | Trigger a pickup failure |
| POST | `/api/simulate/eta-drift` | Trigger ETA drift on shipments |
| POST | `/api/simulate/create-shipment` | Create a new shipment on the fly |

### GeoJSON

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/geo/shipments` | All active shipments as FeatureCollection |
| GET | `/api/geo/warehouses` | All warehouses as FeatureCollection |
| GET | `/api/geo/routes` | All routes as FeatureCollection (LineString) |
| GET | `/api/geo/shipments/near-warehouse/{id}` | Spatial query: shipments within radius |
| GET | `/api/geo/shipments/on-route/{id}` | Buffer query: shipments along a route |

### AI Agent

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agent/graph-info` | LangGraph pipeline metadata (nodes, compiled, cycle count) |
| GET | `/agent/decisions` | Decision log (`?risk_type=`, `?status=`, `?outcome=`, `?limit=`) |
| GET | `/agent/decisions/{id}` | Single decision detail |
| GET | `/agent/metrics` | Learning metrics (success rate, FP rate, breakdowns) |
| GET | `/agent/status` | Agent status (running, cycle count, model trained) |
| GET | `/agent/risks` | Latest risk snapshot from last cycle |
| POST | `/agent/analyze` | Trigger a single agent cycle on demand |
| POST | `/agent/approve/{id}` | Approve or reject a pending decision |
| GET | `/agent/summary` | LLM-generated cycle summary |
| GET | `/agent/feature-importance` | ML model feature weights |
| GET | `/agent/llm-stats` | LLM call statistics |

### Actions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/actions/send-alert` | Send email alert for a shipment |
| POST | `/actions/reroute` | Reroute a shipment to a better route |
| POST | `/actions/switch-carrier` | Switch a shipment to a more reliable carrier |

---

## Getting Started

### Prerequisites

| Tool | Version | Required For |
|------|---------|-------------|
| [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/) | 24+ | Backend (Postgres + API) |
| [Node.js](https://nodejs.org/) | 18+ | Frontend |
| [uv](https://docs.astral.sh/uv/) | 0.5+ | Local dev only (Python package manager) |
| [Python](https://www.python.org/) | 3.11+ | Local dev only |

### Option A — Full Stack with Docker (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/kanishjn/CC2.git
cd CC2/backend

# 2. Start Postgres + FastAPI
docker compose up --build

# 3. (Optional) Run in background
docker compose up -d --build
```

On first boot Docker will:
- Start PostgreSQL 16 with PostGIS
- Install Python dependencies via `uv`
- Create all database tables
- Seed warehouses, carriers, routes, and shipments
- Start the simulation engine + AI agent + lifecycle manager
- Expose the API at **http://localhost:8000**

```bash
# View logs
docker compose logs -f

# View only API logs
docker compose logs -f api

# Stop all services
docker compose down

# Full reset (wipe database)
docker compose down -v
```

### Option B — Local Development

Run only Postgres via Docker, and the API locally with hot-reload:

```bash
# Terminal 1 — Start the database
cd backend
docker compose up postgres -d

# Terminal 2 — Run the API
cd backend
cp .env.example .env        # DATABASE_URL defaults to localhost:5432
uv sync                     # Install Python dependencies
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at **http://localhost:8000**. Swagger docs at **http://localhost:8000/docs**.

### Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at **http://localhost:3000**.

---

## Environment Variables

Create a `.env` file in the `backend/` directory:

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/cc2_db` | PostgreSQL connection string |

### Simulation

| Variable | Default | Description |
|----------|---------|-------------|
| `SIM_TICK_INTERVAL` | `2.0` | Real-seconds between simulation ticks |
| `SIM_SPEED` | `10.0` | Sim-minutes per real-second |
| `EVENT_RETENTION_HOURS` | `72` | How long to retain simulation events |

### Seed Data

| Variable | Default | Description |
|----------|---------|-------------|
| `SEED_WAREHOUSES` | `10` | Number of warehouses to seed |
| `SEED_CARRIERS` | `12` | Number of carriers to seed |
| `SEED_ROUTES` | `30` | Number of routes to seed |
| `SEED_SHIPMENTS` | `60` | Number of shipments to seed |

### AI Agent

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_TICK_INTERVAL` | `60.0` | Seconds between agent cycles |
| `RISK_THRESHOLD` | `0.6` | ML delay risk score cutoff |
| `BOTTLENECK_THRESHOLD` | `0.85` | Warehouse congestion cutoff |
| `CARRIER_RELIABILITY_THRESHOLD` | `0.5` | Carrier degradation cutoff |

### LLM (Gemini)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key |
| `GEMINI_PRIMARY_MODEL` | `models/gemini-2.0-flash` | Primary LLM model |
| `GEMINI_FALLBACK_MODEL` | `models/gemini-2.0-flash-lite` | Fallback LLM model |
| `LLM_CALL_COOLDOWN` | `30.0` | Minimum seconds between LLM calls |

### Email Alerts (SMTP)

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | *(empty)* | SMTP server host |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | *(empty)* | SMTP username |
| `SMTP_PASSWORD` | *(empty)* | SMTP password |
| `SMTP_USE_TLS` | `true` | Enable TLS |
| `ALERT_EMAIL_FROM` | `alerts@routesense.ai` | Sender address |
| `ALERT_EMAIL_TO` | *(empty)* | Comma-separated recipient list |
| `ALERT_EMAIL_COOLDOWN` | `300.0` | Global email rate-limit (seconds) |

### Lifecycle Manager

| Variable | Default | Description |
|----------|---------|-------------|
| `LIFECYCLE_TICK_INTERVAL` | `10.0` | Check frequency (seconds) |
| `LIFECYCLE_GRACE_PERIOD` | `20.0` | Seconds before pruning delivered shipments |
| `LIFECYCLE_TARGET_ACTIVE` | `60` | Target active shipment count |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `*` | Comma-separated frontend origins |

---

## Deployment

### Backend (Railway / Render)

Set these environment variables on your deployment platform:

```
DATABASE_URL=postgresql://user:pass@host:port/dbname?sslmode=require
GEMINI_API_KEY=your-api-key
ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
```

The app auto-creates all tables on startup (`Base.metadata.create_all()`). No manual schema migration needed.

**PostGIS requirement:** Your PostgreSQL instance must support PostGIS. Providers with built-in PostGIS:

| Provider | Free Tier | PostGIS |
|----------|-----------|---------|
| **Supabase** | 500 MB, 2 projects | Built-in |
| **Neon** | 512 MB, 1 project | Built-in |
| **Railway** | $5 trial credit | Run `CREATE EXTENSION IF NOT EXISTS postgis;` |
| **Render** | 256 MB, 90 days | Built-in |

### Frontend (Vercel)

```bash
cd frontend
# Deploy via Vercel CLI or connect GitHub repo
```

Set the environment variable:
```
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
```

### Deployment Architecture

```
Vercel                 Railway / Render         Railway / Supabase
┌──────────────┐      ┌──────────────┐         ┌──────────────┐
│   Next.js    │ ───► │   FastAPI    │ ──────► │  PostgreSQL  │
│   Frontend   │      │   Backend    │         │  + PostGIS   │
└──────────────┘      └──────────────┘         └──────────────┘
```

---

## Project Structure

```
CC2/
├── README.md                          # This file
├── backend/
│   ├── main.py                        # FastAPI entry point + lifespan
│   ├── docker-compose.yaml            # Postgres + API orchestration
│   ├── pyproject.toml                 # Python dependencies
│   ├── schema.sql                     # DDL (for manual use — app auto-creates)
│   ├── app/
│   │   ├── config.py                  # All environment variables + defaults
│   │   ├── database.py                # SQLAlchemy engine + session
│   │   ├── models.py                  # 6 ORM models + enums
│   │   ├── schemas.py                 # Pydantic response schemas
│   │   ├── seed.py                    # Data seeding (60+ cities, carriers, routes)
│   │   ├── simulation.py              # SimPy discrete-event simulation
│   │   ├── lifecycle.py               # Shipment lifecycle manager
│   │   ├── ai_agent/
│   │   │   ├── graph.py               # LangGraph StateGraph definition
│   │   │   ├── state.py               # AgentState TypedDict
│   │   │   ├── nodes.py               # 6 node implementations
│   │   │   ├── agent.py               # AgentLoop background thread
│   │   │   ├── observer.py            # DB queries + feature extraction
│   │   │   ├── risk_models.py         # ML model + rule-based detectors
│   │   │   ├── reasoning.py           # LLM + rule-based explanations
│   │   │   ├── decision_engine.py     # Multi-criteria action scoring
│   │   │   ├── actions.py             # Action executors (reroute, switch, alert)
│   │   │   ├── learning.py            # Outcome evaluation + metrics
│   │   │   └── llm_client.py          # Gemini API client with fallbacks
│   │   └── routers/
│   │       ├── data.py                # /api/ data endpoints
│   │       ├── simulate.py            # /api/simulate/ endpoints
│   │       ├── geo.py                 # /api/geo/ GeoJSON endpoints
│   │       ├── agent.py               # /agent/ AI agent endpoints
│   │       └── actions.py             # /actions/ direct action endpoints
│   └── tests/
│       ├── conftest.py                # Test fixtures
│       ├── test_data_api.py           # Data API tests
│       ├── test_events.py             # Event tests
│       ├── test_seed.py               # Seed tests
│       ├── test_simulate_api.py       # Simulation API tests
│       └── test_simulation.py         # Simulation engine tests
├── frontend/
│   ├── package.json
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx                 # Root layout with sidebar + header
│   │   ├── page.tsx                   # Overview page
│   │   ├── shipments/page.tsx
│   │   ├── decisions/page.tsx
│   │   ├── carriers/page.tsx
│   │   ├── warehouses/page.tsx
│   │   └── simulator/page.tsx
│   ├── components/
│   │   ├── overview-page.tsx          # KPIs, health score, charts, map
│   │   ├── shipments-page.tsx         # Shipment table + filters + drawer
│   │   ├── decisions-page.tsx         # Decision log + reasoning + approval
│   │   ├── carriers-page.tsx          # Carrier performance
│   │   ├── warehouses-page.tsx        # Warehouse monitoring
│   │   ├── simulator-page.tsx         # Manual disruption triggers
│   │   ├── shipment-map.tsx           # Live map component
│   │   ├── reasoning-chain.tsx        # Expandable reasoning visualization
│   │   ├── alert-notifications.tsx    # In-app alert toasts
│   │   └── ui/                        # Radix UI primitives
│   ├── hooks/
│   │   ├── use-data.ts                # Data fetching hooks
│   │   └── use-polling-data.ts        # Generic polling hook
│   └── lib/
│       ├── api.ts                     # API client (30+ endpoints)
│       ├── types.ts                   # TypeScript interfaces
│       └── utils.ts                   # Utility functions
```

---

## Seed Data

The system seeds a realistic global logistics network:

**60+ cities** across all continents:
- **South Asia:** Mumbai, Delhi, Bangalore, Chennai, Hyderabad, Kolkata, Ahmedabad, Karachi, Dhaka, Colombo
- **East Asia:** Shanghai, Beijing, Shenzhen, Hong Kong, Tokyo, Osaka, Seoul, Taipei, Singapore, Kuala Lumpur, Bangkok, Jakarta
- **Middle East:** Dubai, Abu Dhabi, Riyadh, Doha, Kuwait City, Muscat
- **Europe:** London, Amsterdam, Frankfurt, Paris, Rotterdam, Hamburg, Antwerp, Barcelona, Milan, Warsaw, Istanbul
- **Africa:** Nairobi, Lagos, Cairo, Johannesburg, Casablanca, Addis Ababa
- **Americas:** New York, Los Angeles, Chicago, Miami, Houston, Toronto, Mexico City, São Paulo, Buenos Aires, Bogotá
- **Oceania:** Sydney, Melbourne, Auckland

**15 warehouse hubs:** Mumbai, Dubai, Singapore, Shanghai, Frankfurt, London, New York, São Paulo, Nairobi, Sydney, Tokyo, Istanbul, Los Angeles, Johannesburg, Bangkok

**12 carriers:** SwiftLogistics, CargoExpress, TransFast, ReliFreight, QuickShip, PrimeHaul, MetroCarriers, AlphaTransport, GlobalFreight, OceanLink, AirBridge, SilkRoute — with diverse reliability profiles ranging from 0.25 to 0.99.

---

## Running Tests

```bash
cd backend
uv sync --all-extras
uv run pytest
```

---

**Made with 💙 by [Jal](https://github.com/Jal-Bafana), [Kanish](https://github.com/kanishjn), and [Kaivalya](https://github.com/KaivalyaJoglekar)**
