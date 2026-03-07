-- =============================================================================
-- CC2 — Logistics Simulation Platform
-- PostgreSQL 16 Schema
--
-- Generated from: backend/app/models.py
-- Apply manually :  psql -U postgres -d cc2_db -f schema.sql
-- Docker auto-run:  schema.sql is mounted at /docker-entrypoint-initdb.d/
--                   and executed automatically on first container start.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------------

CREATE TYPE shipmentstatus AS ENUM (
    'created',
    'dispatched',
    'in_transit',
    'at_warehouse',
    'out_for_delivery',
    'delivered',
    'delayed',
    'failed'
);

CREATE TYPE trafficlevel AS ENUM (
    'low',
    'moderate',
    'high',
    'severe'
);

CREATE TYPE eventtype AS ENUM (
    'shipment_created',
    'shipment_dispatched',
    'shipment_delivered',
    'shipment_delayed',
    'warehouse_load_update',
    'warehouse_congestion',
    'carrier_delay_event',
    'carrier_failure',
    'route_traffic_update',
    'pickup_failure',
    'eta_drift'
);

-- ---------------------------------------------------------------------------
-- shipments
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS shipments (
    id              SERIAL          PRIMARY KEY,
    shipment_id     VARCHAR(64)     NOT NULL UNIQUE,
    origin          VARCHAR(128)    NOT NULL,
    destination     VARCHAR(128)    NOT NULL,
    carrier         VARCHAR(64)     NOT NULL,
    route_id        VARCHAR(64),
    eta             TIMESTAMP       NOT NULL,
    sla_deadline    TIMESTAMP       NOT NULL,
    status          shipmentstatus  NOT NULL DEFAULT 'created',
    created_at      TIMESTAMP       NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_shipments_shipment_id ON shipments (shipment_id);

-- ---------------------------------------------------------------------------
-- warehouse_state
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS warehouse_state (
    id               SERIAL       PRIMARY KEY,
    warehouse_id     VARCHAR(64)  NOT NULL UNIQUE,
    location         VARCHAR(128) NOT NULL,
    capacity         INTEGER      NOT NULL,
    current_load     INTEGER      NOT NULL DEFAULT 0,
    queue_length     INTEGER      NOT NULL DEFAULT 0,
    congestion_score FLOAT        NOT NULL DEFAULT 0.0,
    updated_at       TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_warehouse_state_warehouse_id ON warehouse_state (warehouse_id);

-- ---------------------------------------------------------------------------
-- carrier_performance
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS carrier_performance (
    id                  SERIAL       PRIMARY KEY,
    carrier_id          VARCHAR(64)  NOT NULL UNIQUE,
    name                VARCHAR(128) NOT NULL,
    reliability_score   FLOAT        NOT NULL DEFAULT 1.0,
    delay_probability   FLOAT        NOT NULL DEFAULT 0.05,
    pickup_success_rate FLOAT        NOT NULL DEFAULT 0.95,
    total_shipments     INTEGER      NOT NULL DEFAULT 0,
    total_delays        INTEGER      NOT NULL DEFAULT 0,
    updated_at          TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_carrier_performance_carrier_id ON carrier_performance (carrier_id);

-- ---------------------------------------------------------------------------
-- routes
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS routes (
    id             SERIAL        PRIMARY KEY,
    route_id       VARCHAR(64)   NOT NULL UNIQUE,
    origin         VARCHAR(128)  NOT NULL,
    destination    VARCHAR(128)  NOT NULL,
    distance       FLOAT         NOT NULL,        -- kilometres
    traffic_level  trafficlevel  NOT NULL DEFAULT 'low',
    weather_factor FLOAT         NOT NULL DEFAULT 1.0,  -- 1.0 = clear, >1 = degraded
    updated_at     TIMESTAMP     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_routes_route_id ON routes (route_id);

-- ---------------------------------------------------------------------------
-- simulation_events
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS simulation_events (
    id          SERIAL     PRIMARY KEY,
    event_type  eventtype  NOT NULL,
    entity_id   VARCHAR(64) NOT NULL,
    payload     TEXT,                     -- JSON string with event details
    sim_time    FLOAT,                    -- simulation clock value at emission
    created_at  TIMESTAMP  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_simulation_events_event_type ON simulation_events (event_type);
CREATE INDEX IF NOT EXISTS ix_simulation_events_entity_id  ON simulation_events (entity_id);
CREATE INDEX IF NOT EXISTS ix_simulation_events_created_at ON simulation_events (created_at);

-- ---------------------------------------------------------------------------
-- decision_log  (AI Agent)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS decision_log (
    id                  SERIAL       PRIMARY KEY,
    decision_id         VARCHAR(64)  NOT NULL UNIQUE,
    risk_type           VARCHAR(64)  NOT NULL,
    entity_id           VARCHAR(64)  NOT NULL,
    shipment_id         VARCHAR(64),
    risk_score          FLOAT        NOT NULL,
    problem             TEXT         NOT NULL,
    evidence            TEXT,
    root_cause          TEXT         NOT NULL,
    confidence          FLOAT        NOT NULL,
    recommended_action  VARCHAR(64)  NOT NULL,
    action_details      TEXT,
    requires_approval   BOOLEAN      NOT NULL DEFAULT FALSE,
    status              VARCHAR(32)  NOT NULL DEFAULT 'executed',
    outcome             VARCHAR(32)  NOT NULL DEFAULT 'pending',
    sla_impact          FLOAT,
    created_at          TIMESTAMP    NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_decision_log_decision_id ON decision_log (decision_id);
CREATE INDEX IF NOT EXISTS ix_decision_log_shipment_id ON decision_log (shipment_id);
CREATE INDEX IF NOT EXISTS ix_decision_log_created_at  ON decision_log (created_at);
