import type {
  Shipment,
  Warehouse,
  Carrier,
  Route,
  AgentDecision,
  NetworkOverview,
  AgentMetrics,
} from "./types";

// ============================================================
// Mock Data Layer
// Provides realistic demo data when the backend is unavailable.
// All data follows the exact schema the API will return.
// ============================================================

function hoursFromNow(h: number): string {
  return new Date(Date.now() + h * 3600000).toISOString();
}

function hoursAgo(h: number): string {
  return new Date(Date.now() - h * 3600000).toISOString();
}

// ---- Shipments ----

export const mockShipments: Shipment[] = [
  {
    shipment_id: "SHP-1001",
    origin: "Mumbai",
    destination: "Delhi",
    carrier_id: "CR-001",
    eta: hoursFromNow(6),
    sla_deadline: hoursFromNow(8),
    status: "in_transit",
    delay_risk: 0.82,
    recommended_action: "Reroute via alternate highway",
  },
  {
    shipment_id: "SHP-1002",
    origin: "Bangalore",
    destination: "Chennai",
    carrier_id: "CR-002",
    eta: hoursFromNow(3),
    sla_deadline: hoursFromNow(5),
    status: "in_transit",
    delay_risk: 0.35,
    recommended_action: null,
  },
  {
    shipment_id: "SHP-1003",
    origin: "Delhi",
    destination: "Jaipur",
    carrier_id: "CR-003",
    eta: hoursFromNow(2),
    sla_deadline: hoursFromNow(2.5),
    status: "at_risk",
    delay_risk: 0.91,
    recommended_action: "Switch to priority carrier",
  },
  {
    shipment_id: "SHP-1004",
    origin: "Kolkata",
    destination: "Hyderabad",
    carrier_id: "CR-004",
    eta: hoursFromNow(12),
    sla_deadline: hoursFromNow(14),
    status: "dispatched",
    delay_risk: 0.45,
    recommended_action: "Monitor traffic on NH-16",
  },
  {
    shipment_id: "SHP-1005",
    origin: "Pune",
    destination: "Ahmedabad",
    carrier_id: "CR-005",
    eta: hoursFromNow(5),
    sla_deadline: hoursFromNow(7),
    status: "in_transit",
    delay_risk: 0.22,
    recommended_action: null,
  },
  {
    shipment_id: "SHP-1006",
    origin: "Hyderabad",
    destination: "Mumbai",
    carrier_id: "CR-001",
    eta: hoursFromNow(8),
    sla_deadline: hoursFromNow(9),
    status: "at_risk",
    delay_risk: 0.76,
    recommended_action: "Reroute shipment via Pune corridor",
  },
  {
    shipment_id: "SHP-1007",
    origin: "Chennai",
    destination: "Bangalore",
    carrier_id: "CR-002",
    eta: hoursFromNow(1.5),
    sla_deadline: hoursFromNow(3),
    status: "in_transit",
    delay_risk: 0.18,
    recommended_action: null,
  },
  {
    shipment_id: "SHP-1008",
    origin: "Ahmedabad",
    destination: "Delhi",
    carrier_id: "CR-003",
    eta: hoursFromNow(10),
    sla_deadline: hoursFromNow(10.5),
    status: "delayed",
    delay_risk: 0.95,
    recommended_action: "Escalate to operations manager",
  },
  {
    shipment_id: "SHP-1009",
    origin: "Jaipur",
    destination: "Lucknow",
    carrier_id: "CR-004",
    eta: hoursFromNow(7),
    sla_deadline: hoursFromNow(9),
    status: "in_transit",
    delay_risk: 0.31,
    recommended_action: null,
  },
  {
    shipment_id: "SHP-1010",
    origin: "Lucknow",
    destination: "Kolkata",
    carrier_id: "CR-005",
    eta: hoursFromNow(9),
    sla_deadline: hoursFromNow(11),
    status: "dispatched",
    delay_risk: 0.55,
    recommended_action: "Prioritize loading at Lucknow hub",
  },
  {
    shipment_id: "SHP-1011",
    origin: "Mumbai",
    destination: "Pune",
    carrier_id: "CR-001",
    eta: hoursFromNow(1),
    sla_deadline: hoursFromNow(2),
    status: "in_transit",
    delay_risk: 0.12,
    recommended_action: null,
  },
  {
    shipment_id: "SHP-1012",
    origin: "Delhi",
    destination: "Kolkata",
    carrier_id: "CR-002",
    eta: hoursFromNow(14),
    sla_deadline: hoursFromNow(13),
    status: "delayed",
    delay_risk: 0.88,
    recommended_action: "Reroute via air cargo",
  },
];

// ---- Warehouses ----

export const mockWarehouses: Warehouse[] = [
  {
    warehouse_id: "WH-001",
    name: "Mumbai Central Hub",
    location: "Mumbai",
    capacity: 500,
    current_load: 460,
    queue_length: 34,
    congestion_score: 0.92,
  },
  {
    warehouse_id: "WH-002",
    name: "Delhi Distribution Center",
    location: "Delhi",
    capacity: 600,
    current_load: 390,
    queue_length: 12,
    congestion_score: 0.65,
  },
  {
    warehouse_id: "WH-003",
    name: "Bangalore Tech Park Hub",
    location: "Bangalore",
    capacity: 400,
    current_load: 180,
    queue_length: 5,
    congestion_score: 0.35,
  },
  {
    warehouse_id: "WH-004",
    name: "Chennai Port Warehouse",
    location: "Chennai",
    capacity: 450,
    current_load: 410,
    queue_length: 28,
    congestion_score: 0.85,
  },
  {
    warehouse_id: "WH-005",
    name: "Kolkata Eastern Hub",
    location: "Kolkata",
    capacity: 350,
    current_load: 200,
    queue_length: 8,
    congestion_score: 0.48,
  },
  {
    warehouse_id: "WH-006",
    name: "Hyderabad Logistics Park",
    location: "Hyderabad",
    capacity: 500,
    current_load: 280,
    queue_length: 10,
    congestion_score: 0.52,
  },
];

// ---- Carriers ----

export const mockCarriers: Carrier[] = [
  {
    carrier_id: "CR-001",
    name: "BlueDart Express",
    reliability_score: 0.92,
    delay_probability: 0.08,
    pickup_success_rate: 0.96,
  },
  {
    carrier_id: "CR-002",
    name: "Delhivery",
    reliability_score: 0.78,
    delay_probability: 0.22,
    pickup_success_rate: 0.88,
  },
  {
    carrier_id: "CR-003",
    name: "DTDC Logistics",
    reliability_score: 0.44,
    delay_probability: 0.56,
    pickup_success_rate: 0.72,
  },
  {
    carrier_id: "CR-004",
    name: "Ecom Express",
    reliability_score: 0.81,
    delay_probability: 0.19,
    pickup_success_rate: 0.91,
  },
  {
    carrier_id: "CR-005",
    name: "XpressBees",
    reliability_score: 0.67,
    delay_probability: 0.33,
    pickup_success_rate: 0.84,
  },
];

// ---- Routes ----

export const mockRoutes: Route[] = [
  { route_id: "RT-001", origin: "Mumbai", destination: "Delhi", distance: 1400, traffic_level: "HIGH", weather_factor: 0.85 },
  { route_id: "RT-002", origin: "Bangalore", destination: "Chennai", distance: 350, traffic_level: "MEDIUM", weather_factor: 0.95 },
  { route_id: "RT-003", origin: "Delhi", destination: "Jaipur", distance: 280, traffic_level: "CRITICAL", weather_factor: 0.70 },
  { route_id: "RT-004", origin: "Kolkata", destination: "Hyderabad", distance: 1500, traffic_level: "LOW", weather_factor: 0.92 },
  { route_id: "RT-005", origin: "Pune", destination: "Ahmedabad", distance: 660, traffic_level: "MEDIUM", weather_factor: 0.88 },
  { route_id: "RT-006", origin: "Hyderabad", destination: "Mumbai", distance: 710, traffic_level: "HIGH", weather_factor: 0.80 },
  { route_id: "RT-007", origin: "Chennai", destination: "Bangalore", distance: 350, traffic_level: "LOW", weather_factor: 0.98 },
  { route_id: "RT-008", origin: "Ahmedabad", destination: "Delhi", distance: 950, traffic_level: "HIGH", weather_factor: 0.75 },
];

// ---- Agent Decisions ----

export const mockDecisions: AgentDecision[] = [
  {
    log_id: "DEC-001",
    shipment_id: "SHP-1001",
    risk_score: 0.82,
    problem: "High delay risk detected for shipment SHP-1001 (Mumbai → Delhi)",
    root_cause: "Warehouse congestion at Mumbai Central Hub (92% load) combined with HIGH traffic on Mumbai-Delhi corridor",
    confidence: 0.89,
    action_taken: "Reroute via alternate highway",
    outcome: "pending",
    sla_impact: "Estimated 2hr improvement",
    requires_approval: true,
    approved: null,
    timestamp: hoursAgo(0.5),
  },
  {
    log_id: "DEC-002",
    shipment_id: "SHP-1003",
    risk_score: 0.91,
    problem: "Critical SLA breach imminent for SHP-1003 (Delhi → Jaipur)",
    root_cause: "DTDC Logistics carrier degradation (reliability: 0.44) + CRITICAL traffic on Delhi-Jaipur route",
    confidence: 0.94,
    action_taken: "Switch to priority carrier BlueDart Express",
    outcome: "pending",
    sla_impact: "Prevents SLA breach",
    requires_approval: true,
    approved: null,
    timestamp: hoursAgo(0.3),
  },
  {
    log_id: "DEC-003",
    shipment_id: "SHP-1008",
    risk_score: 0.95,
    problem: "Shipment SHP-1008 already delayed, SLA breach likely",
    root_cause: "Carrier DTDC experiencing systemic delays (56% delay probability) + poor weather on Ahmedabad-Delhi route",
    confidence: 0.91,
    action_taken: "Escalate to operations manager",
    outcome: "escalated",
    sla_impact: "SLA breach expected without intervention",
    requires_approval: false,
    approved: true,
    timestamp: hoursAgo(1),
  },
  {
    log_id: "DEC-004",
    shipment_id: "SHP-1006",
    risk_score: 0.76,
    problem: "Elevated delay risk for SHP-1006 (Hyderabad → Mumbai)",
    root_cause: "HIGH traffic on Hyderabad-Mumbai route combined with Mumbai warehouse nearing capacity",
    confidence: 0.78,
    action_taken: "Reroute shipment via Pune corridor",
    outcome: "pending",
    sla_impact: "Estimated 1.5hr improvement",
    requires_approval: true,
    approved: null,
    timestamp: hoursAgo(0.2),
  },
  {
    log_id: "DEC-005",
    shipment_id: "SHP-1010",
    risk_score: 0.55,
    problem: "Moderate delay risk for SHP-1010 (Lucknow → Kolkata)",
    root_cause: "Queue build-up at Lucknow warehouse, carrier XpressBees showing moderate reliability",
    confidence: 0.72,
    action_taken: "Prioritize loading at Lucknow hub",
    outcome: "completed",
    sla_impact: "Reduced wait time by 45 min",
    requires_approval: false,
    approved: true,
    timestamp: hoursAgo(2),
  },
  {
    log_id: "DEC-006",
    shipment_id: "SHP-1012",
    risk_score: 0.88,
    problem: "SHP-1012 (Delhi → Kolkata) ETA exceeds SLA deadline",
    root_cause: "Delhivery carrier delay + long route distance (1400km). ETA overshot by 1hr.",
    confidence: 0.86,
    action_taken: "Reroute via air cargo",
    outcome: "pending",
    sla_impact: "Could save 3hrs, prevent SLA breach",
    requires_approval: true,
    approved: null,
    timestamp: hoursAgo(0.1),
  },
  {
    log_id: "DEC-007",
    shipment_id: "SHP-1004",
    risk_score: 0.45,
    problem: "Moderate risk — SHP-1004 traffic conditions unstable",
    root_cause: "NH-16 traffic patterns historically spike during this time window",
    confidence: 0.65,
    action_taken: "Monitor traffic on NH-16",
    outcome: "monitoring",
    sla_impact: "No immediate action needed",
    requires_approval: false,
    approved: true,
    timestamp: hoursAgo(1.5),
  },
];

// ---- Network Overview ----

export const mockOverview: NetworkOverview = {
  total_shipments: 12,
  shipments_at_risk: 5,
  predicted_sla_breaches: 3,
  network_health_score: 72,
  active_carriers: 5,
  active_warehouses: 6,
  shipment_trend: [
    { time: "00:00", count: 8, at_risk: 1 },
    { time: "02:00", count: 9, at_risk: 1 },
    { time: "04:00", count: 10, at_risk: 2 },
    { time: "06:00", count: 11, at_risk: 2 },
    { time: "08:00", count: 14, at_risk: 3 },
    { time: "10:00", count: 16, at_risk: 4 },
    { time: "12:00", count: 15, at_risk: 5 },
    { time: "14:00", count: 13, at_risk: 4 },
    { time: "16:00", count: 12, at_risk: 5 },
    { time: "18:00", count: 12, at_risk: 5 },
  ],
  risk_distribution: [
    { level: "Critical", count: 3, color: "#ef4444" },
    { level: "Warning", count: 4, color: "#f59e0b" },
    { level: "Normal", count: 5, color: "#10b981" },
  ],
};

// ---- Agent Metrics ----

export const mockMetrics: AgentMetrics = {
  intervention_success_rate: 0.84,
  false_positive_rate: 0.12,
  prediction_accuracy: 0.87,
  total_decisions: 7,
};
