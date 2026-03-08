"""
LangGraph state definition — typed dictionary that flows through the graph.

Each node reads from and writes to this shared state object.
"""

from typing import TypedDict, Optional


class RiskItem(TypedDict, total=False):
    type: str                    # delay_risk | bottleneck | carrier_degradation
    entity_id: str
    risk_score: float
    features: dict               # raw features (delay_risk only)
    raw_data: dict               # raw warehouse/carrier info (bottleneck/carrier only)
    explanation: dict             # from reasoning engine
    scored_actions: list[dict]   # from decision engine
    best_action: dict            # selected action
    requires_approval: bool
    action_result: dict | None   # from execution
    shipment_id: str | None


class AgentState(TypedDict, total=False):
    """Full state of one agent cycle flowing through the LangGraph."""

    # ── Observe outputs ──────────────────────────────────────────────────
    shipments: list              # active Shipment ORM objects (serialized ids)
    warehouses_by_loc: dict      # location → warehouse dict
    carriers_map: dict           # carrier_id → carrier dict
    routes_map: dict             # route_id → route dict
    all_warehouses: list[dict]   # all warehouse dicts
    all_carriers: list[dict]     # all carrier dicts

    # ── Risk detection outputs ───────────────────────────────────────────
    delay_risks: list[RiskItem]
    bottleneck_risks: list[RiskItem]
    carrier_risks: list[RiskItem]

    # ── Decide outputs ───────────────────────────────────────────────────
    pending_approvals: list[RiskItem]   # risks that need human approval
    autonomous_actions: list[RiskItem]  # risks that can be auto-executed

    # ── Act outputs ──────────────────────────────────────────────────────
    executed_risks: list[RiskItem]      # risks with action_result filled in

    # ── Learn & summary ──────────────────────────────────────────────────
    all_risks: list[dict]       # final combined risk list for the API
    summary: str                # cycle narrative

    # ── Control ──────────────────────────────────────────────────────────
    cycle_count: int
    db_session_id: str          # key to retrieve the db session from the registry
