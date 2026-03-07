// ============================================================
// Core TypeScript interfaces for RouteSense
// Maps directly to the database schema + API contract
// ============================================================

export type ShipmentStatus =
  | "created"
  | "dispatched"
  | "in_transit"
  | "delivered"
  | "delayed"
  | "at_risk";

export type TrafficLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ActionAuthorization = "autonomous" | "requires_approval";

// ---- Core Entities ----

export interface Shipment {
  shipment_id: string;
  origin: string;
  destination: string;
  carrier_id: string;
  eta: string;
  sla_deadline: string;
  status: ShipmentStatus;
  delay_risk: number;
  recommended_action: string | null;
}

export interface Warehouse {
  warehouse_id: string;
  name: string;
  location: string;
  capacity: number;
  current_load: number;
  queue_length: number;
  congestion_score: number;
}

export interface Carrier {
  carrier_id: string;
  name: string;
  reliability_score: number;
  delay_probability: number;
  pickup_success_rate: number;
}

export interface Route {
  route_id: string;
  origin: string;
  destination: string;
  distance: number;
  traffic_level: TrafficLevel;
  weather_factor: number;
}

// ---- Events & Decisions ----

export interface SimulationEvent {
  event_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface AgentDecision {
  log_id: string;
  shipment_id: string;
  risk_score: number;
  problem: string;
  root_cause: string;
  confidence: number;
  action_taken: string;
  outcome: string;
  sla_impact: string;
  requires_approval: boolean;
  approved: boolean | null;
  timestamp: string;
}

// ---- Dashboard Aggregations ----

export interface NetworkOverview {
  total_shipments: number;
  shipments_at_risk: number;
  predicted_sla_breaches: number;
  network_health_score: number;
  active_carriers: number;
  active_warehouses: number;
  shipment_trend: TrendPoint[];
  risk_distribution: RiskBucket[];
}

export interface TrendPoint {
  time: string;
  count: number;
  at_risk: number;
}

export interface RiskBucket {
  level: string;
  count: number;
  color: string;
}

export interface AgentMetrics {
  intervention_success_rate: number;
  false_positive_rate: number;
  prediction_accuracy: number;
  total_decisions: number;
}

// ---- API Response Wrappers ----

export interface SimulationResponse {
  success: boolean;
  message: string;
  events_generated: number;
}
