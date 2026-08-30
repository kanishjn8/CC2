# CC2 — Logistics Simulation & Data Layer

AI-powered logistics monitoring platform — Simulation engine, event generation system, and RESTful API for real-time operational data.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │  Data API     │  │ Simulate API │  │  Health / Docs    │ │
│  │ /api/shipments│  │ /api/simulate│  │  / , /health      │ │
│  │ /api/warehouses│ │   /start     │  │  /docs (Swagger)  │ │
│  │ /api/carriers │  │   /stop      │  └───────────────────┘ │
│  │ /api/routes   │  │   /status    │                        │
│  │ /api/events   │  │   /scenarios │                        │
│  └──────┬───────┘  └──────┬───────┘                         │
│  ┌──────┴─────────────────┴──────────────┐                  │
│  │       SimPy Simulation Engine         │                  │
│  │  • Shipment lifecycle transitions     │                  │
│  │  • Warehouse load fluctuations        │                  │
│  │  • Route traffic / weather updates    │                  │
│  │  • Random disruptions                 │                  │
│  └──────────────────┬────────────────────┘                  │
│  ┌──────────────────┴────────────────────┐                  │
│  │   PostgreSQL 16  (SQLAlchemy ORM)     │                  │
│  │  shipments  •  warehouse_state        │                  │
│  │  carrier_performance  •  routes       │                  │
│  │  simulation_events                    │                  │
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

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [Docker](https://docs.docker.com/get-docker/) | 24 + | Run Postgres (+ optional full-stack) |
| [Docker Compose](https://docs.docker.com/compose/) | v2 + | Orchestrate services |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.5 + | Python package manager (local dev only) |
| Python | 3.11 + | Runtime (local dev only) |

> **Only Docker is required** to run the full stack.  
> `uv` and Python are only needed for local development without Docker.

---

## 🐳 Option A — Full stack with Docker (recommended)

Everything — Postgres **and** the API — starts with a single command.  
No Python, no `uv`, no manual setup needed on the host machine.

```bash
# 1. Clone the repo and enter the backend folder
git clone https://github.com/kanishjn/CC2.git
cd CC2/backend

# 2. Start both services (Postgres + FastAPI)
docker compose up --build

# 3. (Optional) Run in the background
docker compose up -d --build
```

On first boot Docker will:
- Pull `postgres:16` and create the `cc2_db` database
- Wait until Postgres passes its health check
- Install Python dependencies inside the `api` container via `uv`
- Run database migrations (create all tables)
- Seed warehouses, carriers, routes, and shipments
- Start the background simulation engine
- Expose the API on **http://localhost:8000**

### Useful Docker commands

```bash
# View live logs
docker compose logs -f

# View only API logs
docker compose logs -f api

# Stop all services
docker compose down

# Stop and wipe the database volume (full reset)
docker compose down -v

# Restart just the API (after a code change)
docker compose restart api
```

---

## 💻 Option B — Local development (Postgres in Docker, API on host)

Use this when you want hot-reload and direct debugger access.

```bash
# 1. Start only the Postgres container
docker compose up postgres -d

# 2. Copy the example env file
cp .env.example .env
# DATABASE_URL in .env already points to localhost:5432 — no change needed

# 3. Install Python dependencies
uv sync

# 4. Start the API with hot-reload
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at **http://localhost:8000**.  
Interactive docs (Swagger UI) at **http://localhost:8000/docs**.

On startup the server will:
1. Wait for Postgres to accept connections (retries automatically)
2. Create all database tables
3. Seed initial data (skipped if already present), including ship routes from `app/data/maritime_routes.json`
4. Start the background simulation engine

Seeded route geometries are local cached maritime polylines. No external routing API is called during ticks.

---

## Environment variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/cc2_db` | Postgres connection string |
| `SIM_TICK_INTERVAL` | `2.0` | Real-seconds between simulation ticks |
| `SIM_SPEED` | `10.0` | Sim-minutes advanced per real-second |
| `SEED_WAREHOUSES` | `5` | Number of warehouses to seed |
| `SEED_CARRIERS` | `8` | Number of carriers to seed |
| `SEED_ROUTES` | `12` | Number of routes to seed |
| `SEED_SHIPMENTS` | `20` | Number of shipments to seed |
| `RISK_MODEL_RETRAIN_INTERVAL_CYCLES` | `10` | Attempt delay-model retraining every N agent cycles (`0` disables it) |
| `RISK_MODEL_RETRAIN_MIN_SAMPLES` | `25` | Minimum resolved real samples before retraining |
| `RISK_MODEL_RETRAIN_SYNTHETIC_SAMPLES` | `2000` | Synthetic backfill samples used during hybrid retraining |
| `RISK_MODEL_REAL_SAMPLE_WEIGHT` | `4.0` | Weight multiplier for resolved real learning samples |

> When running the full Docker stack, environment variables are set directly in `docker-compose.yaml` and `.env` is **not** used by the container.

---

## Delay-risk learning feedback loop

The delay-risk model starts with synthetic training data so it can score shipments immediately. During agent cycles, delay-risk decisions store the exact model feature snapshot in `decision_log.evidence.model_features`. Once `learning.evaluate_outcomes()` resolves those decisions, `success` becomes a no-delay label and `failed` becomes a delay/missed-SLA label. The Learn node periodically retrains the in-memory model with a hybrid synthetic + real dataset when enough resolved samples exist.

Full details are in `../docs/risk-model-feedback-loop.md`.

---

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
| GET | `/api/shipments` | List shipments (filter by `?status=`) |
| GET | `/api/shipments/{id}` | Get single shipment |
| GET | `/api/warehouses` | List warehouses (sorted by congestion) |
| GET | `/api/warehouses/{id}` | Get single warehouse |
| GET | `/api/carriers` | List carriers (sorted by reliability) |
| GET | `/api/carriers/{id}` | Get single carrier |
| GET | `/api/routes` | List all routes |
| GET | `/api/routes/{id}` | Get single route |
| GET | `/api/events` | List events (filter by `?event_type=`, `?entity_id=`) |

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

---

## Database Schema

### `shipments`
| Column | Type | Description |
|--------|------|-------------|
| `shipment_id` | VARCHAR(64) | Unique identifier |
| `origin` | VARCHAR(128) | Source location |
| `destination` | VARCHAR(128) | Target location |
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
