"use client"

import { useCallback } from "react"
import { api } from "@/lib/api"
import { usePollingData } from "./use-polling-data"
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
} from "@/lib/types"

// ---- Stable fallback constants (avoid re-creation every render) ----
const EMPTY_ARRAY: never[] = []

const METRICS_FALLBACK: AgentMetrics = {
  total_decisions: 0,
  intervention_success_rate: 0,
  false_positive_rate: 0,
  average_confidence: 0,
  outcomes: {},
  actions_breakdown: {},
  risk_type_breakdown: {},
}

const AGENT_STATUS_FALLBACK: AgentStatus = {
  running: false,
  cycle_count: 0,
  model_trained: false,
  total_decisions: 0,
  pending_approvals: 0,
}

const SIM_STATUS_FALLBACK: SimulationStatus = {
  running: false,
  sim_time: 0,
  total_events: 0,
  shipment_count: 0,
  warehouse_count: 0,
  carrier_count: 0,
  route_count: 0,
}

export function useShipments(interval = 10000) {
  const fetcher = useCallback(() => api.getShipments(), [])
  return usePollingData<Shipment[]>({
    fetcher,
    fallback: EMPTY_ARRAY as Shipment[],
    interval,
  })
}

export function useWarehouses(interval = 10000) {
  const fetcher = useCallback(() => api.getWarehouses(), [])
  return usePollingData<Warehouse[]>({
    fetcher,
    fallback: EMPTY_ARRAY as Warehouse[],
    interval,
  })
}

export function useCarriers(interval = 10000) {
  const fetcher = useCallback(() => api.getCarriers(), [])
  return usePollingData<Carrier[]>({
    fetcher,
    fallback: EMPTY_ARRAY as Carrier[],
    interval,
  })
}

export function useRoutes(interval = 15000) {
  const fetcher = useCallback(() => api.getRoutes(), [])
  return usePollingData<Route[]>({
    fetcher,
    fallback: EMPTY_ARRAY as Route[],
    interval,
  })
}

export function useEvents(limit = 50, interval = 10000) {
  const fetcher = useCallback(() => api.getEvents(undefined, undefined, limit), [limit])
  return usePollingData<SimulationEvent[]>({
    fetcher,
    fallback: EMPTY_ARRAY as SimulationEvent[],
    interval,
  })
}

export function useDecisions(interval = 10000) {
  const fetcher = useCallback(() => api.getDecisions(), [])
  return usePollingData<AgentDecision[]>({
    fetcher,
    fallback: EMPTY_ARRAY as AgentDecision[],
    interval,
  })
}

export function useAgentMetrics(interval = 15000) {
  const fetcher = useCallback(() => api.getMetrics(), [])
  return usePollingData<AgentMetrics>({
    fetcher,
    fallback: METRICS_FALLBACK,
    interval,
  })
}

export function useAgentStatus(interval = 10000) {
  const fetcher = useCallback(() => api.getAgentStatus(), [])
  return usePollingData<AgentStatus>({
    fetcher,
    fallback: AGENT_STATUS_FALLBACK,
    interval,
  })
}

export function useSimulationStatus(interval = 10000) {
  const fetcher = useCallback(() => api.getSimulationStatus(), [])
  return usePollingData<SimulationStatus>({
    fetcher,
    fallback: SIM_STATUS_FALLBACK,
    interval,
  })
}
