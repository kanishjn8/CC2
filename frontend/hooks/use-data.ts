"use client"

import { useCallback } from "react"
import { api } from "@/lib/api"
import {
  mockShipments,
  mockWarehouses,
  mockCarriers,
  mockDecisions,
  mockOverview,
  mockMetrics,
} from "@/lib/mock-data"
import { usePollingData } from "./use-polling-data"
import type {
  Shipment,
  Warehouse,
  Carrier,
  AgentDecision,
  NetworkOverview,
  AgentMetrics,
} from "@/lib/types"

export function useShipments(interval = 10000) {
  const fetcher = useCallback(() => api.getShipments(), [])
  return usePollingData<Shipment[]>({
    fetcher,
    fallback: mockShipments,
    interval,
  })
}

export function useWarehouses(interval = 10000) {
  const fetcher = useCallback(() => api.getWarehouses(), [])
  return usePollingData<Warehouse[]>({
    fetcher,
    fallback: mockWarehouses,
    interval,
  })
}

export function useCarriers(interval = 10000) {
  const fetcher = useCallback(() => api.getCarriers(), [])
  return usePollingData<Carrier[]>({
    fetcher,
    fallback: mockCarriers,
    interval,
  })
}

export function useDecisions(interval = 5000) {
  const fetcher = useCallback(() => api.getDecisions(), [])
  return usePollingData<AgentDecision[]>({
    fetcher,
    fallback: mockDecisions,
    interval,
  })
}

export function useOverview(interval = 10000) {
  const fetcher = useCallback(() => api.getOverview(), [])
  return usePollingData<NetworkOverview>({
    fetcher,
    fallback: mockOverview,
    interval,
  })
}

export function useAgentMetrics(interval = 15000) {
  const fetcher = useCallback(() => api.getMetrics(), [])
  return usePollingData<AgentMetrics>({
    fetcher,
    fallback: mockMetrics,
    interval,
  })
}
