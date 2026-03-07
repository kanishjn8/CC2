import type {
  Shipment,
  Warehouse,
  Carrier,
  Route,
  AgentDecision,
  NetworkOverview,
  AgentMetrics,
  SimulationResponse,
} from "./types";

// ============================================================
// API Client for the RouteSense Backend
// Centralized fetch layer — swap base URL via env var
// Falls back to mock data when backend is unreachable
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
  getShipments(): Promise<Shipment[]> {
    return this.request<Shipment[]>("/shipments");
  }

  getShipment(id: string): Promise<Shipment> {
    return this.request<Shipment>(`/shipments/${encodeURIComponent(id)}`);
  }

  // ---- Warehouses ----
  getWarehouses(): Promise<Warehouse[]> {
    return this.request<Warehouse[]>("/warehouses");
  }

  // ---- Carriers ----
  getCarriers(): Promise<Carrier[]> {
    return this.request<Carrier[]>("/carriers");
  }

  // ---- Routes ----
  getRoutes(): Promise<Route[]> {
    return this.request<Route[]>("/routes");
  }

  // ---- AI Agent ----
  getDecisions(): Promise<AgentDecision[]> {
    return this.request<AgentDecision[]>("/agent/decisions");
  }

  getMetrics(): Promise<AgentMetrics> {
    return this.request<AgentMetrics>("/agent/metrics");
  }

  approveAction(logId: string): Promise<{ success: boolean }> {
    return this.request(`/agent/decisions/${encodeURIComponent(logId)}/approve`, {
      method: "POST",
    });
  }

  rejectAction(logId: string): Promise<{ success: boolean }> {
    return this.request(`/agent/decisions/${encodeURIComponent(logId)}/reject`, {
      method: "POST",
    });
  }

  // ---- Overview / Aggregations ----
  getOverview(): Promise<NetworkOverview> {
    return this.request<NetworkOverview>("/overview");
  }

  // ---- Simulation Controls ----
  simulateWarehouseCongestion(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/simulate/warehouse-congestion", {
      method: "POST",
    });
  }

  simulateCarrierFailure(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/simulate/carrier-failure", {
      method: "POST",
    });
  }

  simulateTrafficSpike(): Promise<SimulationResponse> {
    return this.request<SimulationResponse>("/simulate/traffic-spike", {
      method: "POST",
    });
  }
}

export const api = new ApiClient(API_BASE);
