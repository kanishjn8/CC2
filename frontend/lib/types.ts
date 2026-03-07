// ============================================================
// Core TypeScript interfaces for RouteSense
// Maps directly to the backend API response schemas
// ============================================================

export type ShipmentStatus =
  | "created"
  | "dispatched"
  | "in_transit"
  | "at_warehouse"
  | "out_for_delivery"
  | "delivered"
  | "delayed"
  | "failed";

export type TrafficLevel = "low" | "moderate" | "high" | "severe";

// ---- Core Entities (match backend schemas exactly) ----

export interface Shipment {
  shipment_id: string;
  origin: string;
  destination: string;
  carrier: string;          // carrier name (backend field)
  route_id: string | null;
  eta: string;              // ISO datetime
  sla_deadline: string;     // ISO datetime
  status: ShipmentStatus;
  created_at: string | null;
  updated_at: string | null;
}

export interface Warehouse {
  warehouse_id: string;
  location: string;
  capacity: number;
  current_load: number;
  queue_length: number;
  congestion_score: number;
  updated_at: string | null;
}

export interface Carrier {
  carrier_id: string;
  name: string;
  reliability_score: number;
  delay_probability: number;
  pickup_success_rate: number;
  total_shipments: number;
  total_delays: number;
  updated_at: string | null;
}

export interface Route {
  route_id: string;
  origin: string;
  destination: string;
  distance: number;
  traffic_level: TrafficLevel;
  weather_factor: number;
  updated_at: string | null;
}

// ---- Events ----

export interface SimulationEvent {
  id: number;
  event_type: string;
  entity_id: string;
  payload: string | null;
  sim_time: number | null;
  created_at: string | null;
}

// ---- Agent Decision Log (matches backend DecisionLogOut) ----

export interface AgentDecision {
  id: number;
  decision_id: string;
  risk_type: string;
  entity_id: string;
  shipment_id: string | null;
  risk_score: number;
  problem: string;
  evidence: string | null;
  root_cause: string;
  confidence: number;
  recommended_action: string;
  action_details: string | null;
  requires_approval: boolean;
  status: string;         // executed | pending_approval | approved | rejected
  outcome: string;        // pending | success | failed | rejected
  sla_impact: number | null;
  created_at: string | null;
  resolved_at: string | null;
}

// ---- Agent Metrics (matches backend AgentMetricsOut) ----

export interface AgentMetrics {
  total_decisions: number;
  intervention_success_rate: number;
  false_positive_rate: number;
  average_confidence: number;
  outcomes: Record<string, number>;
  actions_breakdown: Record<string, number>;
  risk_type_breakdown: Record<string, number>;
}

// ---- Agent Status (matches backend AgentStatusOut) ----

export interface AgentStatus {
  running: boolean;
  cycle_count: number;
  model_trained: boolean;
  total_decisions: number;
  pending_approvals: number;
}

// ---- Simulation Status (matches backend SimStatusResponse) ----

export interface SimulationStatus {
  running: boolean;
  sim_time: number;
  total_events: number;
  shipment_count: number;
  warehouse_count: number;
  carrier_count: number;
  route_count: number;
}

// ---- API Response Wrappers ----

export interface SimulationResponse {
  status: string;
  message: string;
  events_generated: number;
  details?: Record<string, unknown> | null;
}

export interface ApprovalResponse {
  status: string;
  message: string;
  decision_id: string;
  result?: Record<string, unknown> | null;
}

export interface AgentSummary {
  cycle_count: number;
  summary: string;
}

export interface AgentAnalyzeResponse {
  status: string;
  message: string;
  risks_detected: number;
  risks: unknown[];
}
