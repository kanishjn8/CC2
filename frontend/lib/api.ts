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
  SimulationResponse,
  ApprovalResponse,
  AgentSummary,
  AgentAnalyzeResponse,
} from "./types";

// ============================================================
// API Client for the CC2 Backend
// All routes prefixed with /api on the backend
// ============================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private base: string;

  constructor(base: string) {
    this.base = base;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.base}${endpoint}`;
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      throw new Error(`API ${res.status}: ${res.statusText}`);
    }
    return res.json();
  }

  // ---- Shipments ----
  getShipments(status?: string, limit?: number): Promise<Shipment[]> {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (limit) params.set("limit", String(limit));
    const qs = params.toString();
    return this.request<Shipment[]>(`/api/shipments${qs ? `?${qs}` : ""}`);
  }

  getShipment(id: string): Promise<Shipment> {
    return this.request<Shipment>(`/api/shipments/${encodeURIComponent(id)}`);
  }

  // ---- Warehouses ----
  getWarehouses(): Promise<Warehouse[]> {
    return this.request<Warehouse[]>("/api/warehouses");
  }

  getWarehouse(id: string): Promise<Warehouse> {
    return this.request<Warehouse>(`/api/warehouses/${encodeURIComponent(id)}`);
  }

  // ---- Carriers ----
  getCarriers(): Promise<Carrier[]> {
    return this.request<Carrier[]>("/api/carriers");
  }

  getCarrier(id: string): Promise<Carrier> {
    return this.request<Carrier>(`/api/carriers/${encodeURIComponent(id)}`);
  }

  // ---- Routes ----
  getRoutes(): Promise<Route[]> {
    return this.request<Route[]>("/api/routes");
  }

  getRoute(id: string): Promise<Route> {
    return this.request<Route>(`/api/routes/${encodeURIComponent(id)}`);
  }

  // ---- Events ----
  getEvents(eventType?: string, entityId?: string, limit?: number): Promise<SimulationEvent[]> {
    const params = new URLSearchParams();
    if (eventType) params.set("event_type", eventType);
    if (entityId) params.set("entity_id", entityId);
    if (limit) params.set("limit", String(limit));
    const qs = params.toString();
    return this.request<SimulationEvent[]>(`/api/events${qs ? `?${qs}` : ""}`);
  }

  // ---- AI Agent ----
  getDecisions(opts?: { risk_type?: string; status?: string; outcome?: string; shipment_id?: string; limit?: number }): Promise<AgentDecision[]> {
    const params = new URLSearchParams();
    if (opts?.risk_type) params.set("risk_type", opts.risk_type);
    if (opts?.status) params.set("status", opts.status);
    if (opts?.outcome) params.set("outcome", opts.outcome);
    if (opts?.shipment_id) params.set("shipment_id", opts.shipment_id);
    if (opts?.limit) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return this.request<AgentDecision[]>(`/api/agent/decisions${qs ? `?${qs}` : ""}`);
  }

  getDecision(decisionId: string): Promise<AgentDecision> {
    return this.request<AgentDecision>(`/api/agent/decisions/${encodeURIComponent(decisionId)}`);
  }

  getMetrics(): Promise<AgentMetrics> {
    return this.request<AgentMetrics>("/api/agent/metrics");
  }

  getAgentStatus(): Promise<AgentStatus> {
    return this.request<AgentStatus>("/api/agent/status");
  }

  getRisks(): Promise<unknown[]> {
    return this.request<unknown[]>("/api/agent/risks");
  }

  triggerAnalysis(): Promise<AgentAnalyzeResponse> {
    return this.request<AgentAnalyzeResponse>("/api/agent/analyze", { method: "POST" });
  }

  approveDecision(decisionId: string): Promise<ApprovalResponse> {
    return this.request<ApprovalResponse>(`/api/agent/approve/${encodeURIComponent(decisionId)}`, {
      method: "POST",
      body: JSON.stringify({ approved: true }),
    });
  }

  rejectDecision(decisionId: string): Promise<ApprovalResponse> {
    return this.request<ApprovalResponse>(`/api/agent/approve/${encodeURIComponent(decisionId)}`, {
      method: "POST",
      body: JSON.stringify({ approved: false }),
    });
  }

  getAgentSummary(): Promise<AgentSummary> {
    return this.request<AgentSummary>("/api/agent/summary");
  }

  // ---- Simulation Controls ----
  getSimulationStatus(): Promise<SimulationStatus> {
    return this.request<SimulationStatus>("/api/simulate/status");
  }

  startSimulation(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/start", { method: "POST" });
  }

  stopSimulation(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/stop", { method: "POST" });
  }

  simulateWarehouseCongestion(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/warehouse-congestion", { method: "POST" });
  }

  simulateCarrierFailure(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/carrier-failure", { method: "POST" });
  }

  simulateTrafficSpike(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/traffic-spike", { method: "POST" });
  }

  simulatePickupFailure(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/pickup-failure", { method: "POST" });
  }

  simulateEtaDrift(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/eta-drift", { method: "POST" });
  }

  createShipment(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/api/simulate/create-shipment", { method: "POST" });
  }
}

export const api = new ApiClient(API_BASE);
