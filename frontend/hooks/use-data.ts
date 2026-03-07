"use client"

import { useState, useCallback } from "react"
import {
  MOCK_SHIPMENTS,
  MOCK_WAREHOUSES,
  MOCK_CARRIERS,
  MOCK_ROUTES,
  MOCK_EVENTS,
  MOCK_DECISIONS,
  MOCK_METRICS,
  MOCK_AGENT_STATUS,
  MOCK_SIMULATION_STATUS,
} from "@/lib/mock-data"
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

// ---- Helper: return mock data instantly (no network, no polling) ----
function useMock<T>(initialData: T) {
  const [data, setData] = useState<T>(initialData)
  const refetch = useCallback(() => { /* no-op for mock */ }, [])
  return { data, setData, loading: false, error: null, refetch, lastUpdated: new Date() }
}

export function useShipments(_interval?: number) {
  return useMock<Shipment[]>(MOCK_SHIPMENTS)
}

export function useWarehouses(_interval?: number) {
  return useMock<Warehouse[]>(MOCK_WAREHOUSES)
}

export function useCarriers(_interval?: number) {
  return useMock<Carrier[]>(MOCK_CARRIERS)
}

export function useRoutes(_interval?: number) {
  return useMock<Route[]>(MOCK_ROUTES)
}

export function useEvents(_limit?: number, _interval?: number) {
  return useMock<SimulationEvent[]>(MOCK_EVENTS)
}

export function useDecisions(_interval?: number) {
  return useMock<AgentDecision[]>(MOCK_DECISIONS)
}

export function useAgentMetrics(_interval?: number) {
  return useMock<AgentMetrics>(MOCK_METRICS)
}

export function useAgentStatus(_interval?: number) {
  return useMock<AgentStatus>(MOCK_AGENT_STATUS)
}

export function useSimulationStatus(_interval?: number) {
  return useMock<SimulationStatus>(MOCK_SIMULATION_STATUS)
}
