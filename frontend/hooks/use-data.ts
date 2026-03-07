"use client"

import { usePollingData } from "@/hooks/use-polling-data"
import { api } from "@/lib/api"
import type {
  Shipment,
  Warehouse,
  Carrier,
  Route,
  SimulationEvent,
  AgentDecision,
  AgentMetrics,
  AgentStatus,
  SimulationStatus,
  LlmStats,
} from "@/lib/types"

// ── Stable module-level fallback constants (never recreated) ─────────────────
const EMPTY_SHIPMENTS: Shipment[] = []
const EMPTY_WAREHOUSES: Warehouse[] = []
const EMPTY_CARRIERS: Carrier[] = []
const EMPTY_ROUTES: Route[] = []
const EMPTY_EVENTS: SimulationEvent[] = []
const EMPTY_DECISIONS: AgentDecision[] = []

const DEFAULT_METRICS: AgentMetrics = {
  total_decisions: 0,
  intervention_success_rate: 0,
  false_positive_rate: 0,
  average_confidence: 0,
  outcomes: {},
  actions_breakdown: {},
  risk_type_breakdown: {},
}

const DEFAULT_AGENT_STATUS: AgentStatus = {
  running: false,
  cycle_count: 0,
  model_trained: false,
  total_decisions: 0,
  pending_approvals: 0,
}

const DEFAULT_SIM_STATUS: SimulationStatus = {
  running: false,
  sim_time: 0,
  total_events: 0,
  shipment_count: 0,
  warehouse_count: 0,
  carrier_count: 0,
  route_count: 0,
}

// ── Polling hooks ─────────────────────────────────────────────────────────────

export function useShipments(interval = 10000) {
  return usePollingData<Shipment[]>({
    fetcher: () => api.getShipments(),
    fallback: EMPTY_SHIPMENTS,
    interval,
  })
}

export function useWarehouses(interval = 15000) {
  return usePollingData<Warehouse[]>({
    fetcher: () => api.getWarehouses(),
    fallback: EMPTY_WAREHOUSES,
    interval,
  })
}

export function useCarriers(interval = 20000) {
  return usePollingData<Carrier[]>({
    fetcher: () => api.getCarriers(),
    fallback: EMPTY_CARRIERS,
    interval,
  })
}

export function useRoutes(interval = 30000) {
  return usePollingData<Route[]>({
    fetcher: () => api.getRoutes(),
    fallback: EMPTY_ROUTES,
    interval,
  })
}

export function useEvents(limit = 50, interval = 8000) {
  return usePollingData<SimulationEvent[]>({
    fetcher: () => api.getEvents(undefined, undefined, limit),
    fallback: EMPTY_EVENTS,
    interval,
  })
}

export function useDecisions(interval = 10000) {
  return usePollingData<AgentDecision[]>({
    fetcher: () => api.getDecisions({ limit: 100 }),
    fallback: EMPTY_DECISIONS,
    interval,
  })
}

export function useAgentMetrics(interval = 15000) {
  return usePollingData<AgentMetrics>({
    fetcher: () => api.getMetrics(),
    fallback: DEFAULT_METRICS,
    interval,
  })
}

export function useAgentStatus(interval = 10000) {
  return usePollingData<AgentStatus>({
    fetcher: () => api.getAgentStatus(),
    fallback: DEFAULT_AGENT_STATUS,
    interval,
  })
}

export function useSimulationStatus(interval = 10000) {
  return usePollingData<SimulationStatus>({
    fetcher: () => api.getSimulationStatus(),
    fallback: DEFAULT_SIM_STATUS,
    interval,
  })
}

const DEFAULT_LLM_STATS: LlmStats = {
  total_calls: 0,
  total_skipped: 0,
  total_failures: 0,
  cooldown_seconds: 0,
  api_key_set: false,
  primary_model: "",
  fallback_model: "",
}

export function useLlmStats(interval = 15000) {
  return usePollingData<LlmStats>({
    fetcher: () => api.getLlmStats(),
    fallback: DEFAULT_LLM_STATS,
    interval,
  })
}
