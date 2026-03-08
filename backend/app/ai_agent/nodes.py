"""
LangGraph node implementations — each function is a graph node that reads
and writes to the shared AgentState.

Nodes wrap existing logic from observer, risk_models, reasoning,
decision_engine, actions, and learning modules.  The business logic in
those modules is UNCHANGED — these nodes simply orchestrate them.
"""

import logging

from app.ai_agent.state import AgentState, RiskItem
from app.ai_agent.observer import (
    get_active_shipments,
    get_all_carriers,
    get_all_warehouses,
    get_carriers_map,
    get_routes_map,
    get_warehouses_by_location,
    build_shipment_features,
)
from app.ai_agent.risk_models import (
    DelayRiskModel,
    detect_bottlenecks,
    detect_carrier_degradation,
)
from app.ai_agent.reasoning import (
    explain_delay_risk,
    explain_bottleneck,
    explain_carrier_degradation,
)
from app.ai_agent.decision_engine import (
    evaluate_delay_risk_actions,
    evaluate_bottleneck_actions,
    evaluate_carrier_degradation_actions,
    select_best_action,
)
from app.ai_agent.actions import execute_action
from app.ai_agent.learning import (
    log_decision,
    evaluate_outcomes,
    has_pending_decision,
)
from app.ai_agent.llm_client import call_llm
from app.config import (
    RISK_THRESHOLD,
    BOTTLENECK_THRESHOLD,
    CARRIER_RELIABILITY_THRESHOLD,
)

log = logging.getLogger("cc2.graph")

# ── Shared delay model (initialised once by AgentLoop.initialize) ────────────
_delay_model: DelayRiskModel | None = None


def set_delay_model(model: DelayRiskModel):
    global _delay_model
    _delay_model = model


def get_delay_model() -> DelayRiskModel:
    if _delay_model is None:
        raise RuntimeError("Delay model not initialised — call set_delay_model() first")
    return _delay_model


# ── DB-session registry ──────────────────────────────────────────────────────
# LangGraph state must be serialisable (for checkpointing) so we cannot put
# a raw SQLAlchemy Session in the state dict.  Instead we store a string key
# and resolve it via this in-process registry.

_db_registry: dict[str, object] = {}


def register_db(key: str, db):
    _db_registry[key] = db


def get_db(key: str):
    return _db_registry[key]


def unregister_db(key: str):
    _db_registry.pop(key, None)


# ═════════════════════════════════════════════════════════════════════════════
# NODE: observe
# ═════════════════════════════════════════════════════════════════════════════

def observe_node(state: AgentState) -> dict:
    """Read current logistics network state from the database."""
    db = get_db(state["db_session_id"])

    shipments = get_active_shipments(db)
    warehouses_by_loc = get_warehouses_by_location(db)
    carriers_map = get_carriers_map(db)
    routes_map = get_routes_map(db)
    all_warehouses = get_all_warehouses(db)
    all_carriers = get_all_carriers(db)

    # Serialise ORM objects into plain dicts for state (checkpointable)
    shipment_dicts = []
    for s in shipments:
        shipment_dicts.append({
            "shipment_id": s.shipment_id,
            "origin": s.origin,
            "destination": s.destination,
            "carrier": s.carrier,
            "route_id": s.route_id,
            "eta": s.eta.isoformat() if s.eta else None,
            "sla_deadline": s.sla_deadline.isoformat() if s.sla_deadline else None,
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
        })

    wh_dicts = []
    for wh in all_warehouses:
        wh_dicts.append({
            "warehouse_id": wh.warehouse_id,
            "location": wh.location,
            "capacity": wh.capacity,
            "current_load": wh.current_load,
            "queue_length": wh.queue_length,
            "congestion_score": wh.congestion_score,
        })

    carrier_dicts = []
    for c in all_carriers:
        carrier_dicts.append({
            "carrier_id": c.carrier_id,
            "name": c.name,
            "reliability_score": c.reliability_score,
            "delay_probability": c.delay_probability,
            "pickup_success_rate": c.pickup_success_rate,
            "total_shipments": c.total_shipments,
            "total_delays": c.total_delays,
        })

    # Keep mappings as dicts-of-dicts for lookups by downstream nodes
    wh_loc_map = {loc: {"warehouse_id": wh.warehouse_id, "location": wh.location,
                         "capacity": wh.capacity, "current_load": wh.current_load,
                         "queue_length": wh.queue_length, "congestion_score": wh.congestion_score}
                  for loc, wh in warehouses_by_loc.items()}

    carrier_map_d = {cid: {"carrier_id": c.carrier_id, "name": c.name,
                            "reliability_score": c.reliability_score,
                            "delay_probability": c.delay_probability,
                            "pickup_success_rate": c.pickup_success_rate,
                            "total_shipments": c.total_shipments,
                            "total_delays": c.total_delays}
                     for cid, c in carriers_map.items()}

    route_map_d = {rid: {"route_id": r.route_id, "origin": r.origin,
                          "destination": r.destination, "distance": r.distance,
                          "traffic_level": r.traffic_level.value if hasattr(r.traffic_level, "value") else str(r.traffic_level),
                          "weather_factor": r.weather_factor}
                   for rid, r in routes_map.items()}

    log.info("📡 OBSERVE — %d shipments, %d warehouses, %d carriers",
             len(shipment_dicts), len(wh_dicts), len(carrier_dicts))

    return {
        "shipments": shipment_dicts,
        "warehouses_by_loc": wh_loc_map,
        "carriers_map": carrier_map_d,
        "routes_map": route_map_d,
        "all_warehouses": wh_dicts,
        "all_carriers": carrier_dicts,
    }


# ═════════════════════════════════════════════════════════════════════════════
# NODE: detect_risks
# ═════════════════════════════════════════════════════════════════════════════

def detect_risks_node(state: AgentState) -> dict:
    """Run ML delay prediction + rule-based bottleneck/carrier detection."""
    db = get_db(state["db_session_id"])
    model = get_delay_model()

    shipments = state["shipments"]
    carriers_map = state["carriers_map"]
    routes_map = state["routes_map"]
    wh_loc_map = state["warehouses_by_loc"]

    # ── Delay risks ──────────────────────────────────────────────────────
    delay_risks: list[RiskItem] = []
    for ship in shipments:
        carrier = carriers_map.get(ship["carrier"])
        route = routes_map.get(ship["route_id"]) if ship.get("route_id") else None
        warehouse = wh_loc_map.get(ship["origin"])

        features = _build_features_from_dicts(ship, carrier, route, warehouse)
        risk_score = model.predict(features)

        if risk_score < RISK_THRESHOLD:
            continue

        if has_pending_decision(db, ship["shipment_id"], "delay_risk"):
            continue

        delay_risks.append({
            "type": "delay_risk",
            "entity_id": ship["shipment_id"],
            "shipment_id": ship["shipment_id"],
            "risk_score": round(risk_score, 4),
            "features": features,
            "raw_data": ship,
        })

    # ── Bottlenecks ──────────────────────────────────────────────────────
    bottleneck_risks: list[RiskItem] = []
    for wh in state["all_warehouses"]:
        if wh["congestion_score"] > BOTTLENECK_THRESHOLD:
            if has_pending_decision(db, wh["warehouse_id"], "bottleneck"):
                continue
            bottleneck_risks.append({
                "type": "bottleneck",
                "entity_id": wh["warehouse_id"],
                "risk_score": round(wh["congestion_score"], 4),
                "raw_data": wh,
            })

    # ── Carrier degradation ──────────────────────────────────────────────
    carrier_risks: list[RiskItem] = []
    for c in state["all_carriers"]:
        if c["reliability_score"] < CARRIER_RELIABILITY_THRESHOLD:
            if has_pending_decision(db, c["carrier_id"], "carrier_degradation"):
                continue
            carrier_risks.append({
                "type": "carrier_degradation",
                "entity_id": c["carrier_id"],
                "risk_score": round(1 - c["reliability_score"], 4),
                "raw_data": c,
            })

    log.info("🔍 DETECT — %d delay, %d bottleneck, %d carrier risks",
             len(delay_risks), len(bottleneck_risks), len(carrier_risks))

    return {
        "delay_risks": delay_risks,
        "bottleneck_risks": bottleneck_risks,
        "carrier_risks": carrier_risks,
    }


def _build_features_from_dicts(ship: dict, carrier: dict | None,
                                route: dict | None, warehouse: dict | None) -> dict:
    """Build feature vector from plain dicts (same logic as observer.build_shipment_features)."""
    from app.ai_agent.observer import TRAFFIC_ENCODING
    from datetime import datetime

    distance = route["distance"] if route else 500.0

    # Handle traffic_level as string or enum
    traffic_raw = route["traffic_level"] if route else "moderate"
    traffic = TRAFFIC_ENCODING.get(traffic_raw, 1)

    weather = route["weather_factor"] if route else 1.0
    congestion = warehouse["congestion_score"] if warehouse else 0.3
    reliability = carrier["reliability_score"] if carrier else 0.7
    delay_prob = carrier["delay_probability"] if carrier else 0.15
    pickup_rate = carrier["pickup_success_rate"] if carrier else 0.9

    eta_sla_buffer = 12.0
    if ship.get("sla_deadline") and ship.get("eta"):
        try:
            sla = datetime.fromisoformat(ship["sla_deadline"])
            eta = datetime.fromisoformat(ship["eta"])
            eta_sla_buffer = (sla - eta).total_seconds() / 3600
        except (ValueError, TypeError):
            pass

    return {
        "distance": distance,
        "traffic_level": traffic,
        "weather_factor": weather,
        "congestion_score": congestion,
        "reliability_score": reliability,
        "delay_probability": delay_prob,
        "pickup_success_rate": pickup_rate,
        "eta_sla_buffer_hours": eta_sla_buffer,
    }


# ═════════════════════════════════════════════════════════════════════════════
# NODE: reason
# ═════════════════════════════════════════════════════════════════════════════

def reason_node(state: AgentState) -> dict:
    """Generate explanations for all detected risks."""

    for risk in state.get("delay_risks", []):
        ship = risk["raw_data"]
        risk["explanation"] = explain_delay_risk(
            risk["entity_id"], risk["features"], risk["risk_score"],
            origin=ship.get("origin", ""), destination=ship.get("destination", ""),
        )

    for risk in state.get("bottleneck_risks", []):
        risk["explanation"] = explain_bottleneck(risk["raw_data"])

    for risk in state.get("carrier_risks", []):
        risk["explanation"] = explain_carrier_degradation(risk["raw_data"])

    log.info("💡 REASON — explanations generated")

    return {
        "delay_risks": state.get("delay_risks", []),
        "bottleneck_risks": state.get("bottleneck_risks", []),
        "carrier_risks": state.get("carrier_risks", []),
    }


# ═════════════════════════════════════════════════════════════════════════════
# NODE: decide
# ═════════════════════════════════════════════════════════════════════════════

def decide_node(state: AgentState) -> dict:
    """Score and select best action for each risk.  Split into
    autonomous (auto-execute) vs approval-required."""

    pending_approvals: list[RiskItem] = []
    autonomous_actions: list[RiskItem] = []

    # Delay risks
    for risk in state.get("delay_risks", []):
        features = risk["features"]
        scored = evaluate_delay_risk_actions(risk["risk_score"], features)
        best = select_best_action(scored, context={"risk_score": risk["risk_score"], **features})
        risk["scored_actions"] = scored
        risk["best_action"] = best
        risk["requires_approval"] = best["requires_approval"]
        if best["requires_approval"]:
            pending_approvals.append(risk)
        else:
            autonomous_actions.append(risk)

    # Bottlenecks
    for risk in state.get("bottleneck_risks", []):
        scored = evaluate_bottleneck_actions(risk["raw_data"])
        best = select_best_action(scored, context={
            "risk_score": risk["risk_score"],
            "congestion_score": risk["risk_score"],
        })
        risk["scored_actions"] = scored
        risk["best_action"] = best
        risk["requires_approval"] = best["requires_approval"]
        if best["requires_approval"]:
            pending_approvals.append(risk)
        else:
            autonomous_actions.append(risk)

    # Carrier degradation
    for risk in state.get("carrier_risks", []):
        scored = evaluate_carrier_degradation_actions(risk["raw_data"])
        best = select_best_action(scored, context={
            "risk_score": risk["risk_score"],
            "reliability_score": risk["raw_data"]["reliability_score"],
        })
        risk["scored_actions"] = scored
        risk["best_action"] = best
        risk["requires_approval"] = best["requires_approval"]
        if best["requires_approval"]:
            pending_approvals.append(risk)
        else:
            autonomous_actions.append(risk)

    log.info("⚖️  DECIDE — %d autonomous, %d need approval",
             len(autonomous_actions), len(pending_approvals))

    return {
        "pending_approvals": pending_approvals,
        "autonomous_actions": autonomous_actions,
    }


# ═════════════════════════════════════════════════════════════════════════════
# NODE: act
# ═════════════════════════════════════════════════════════════════════════════

def act_node(state: AgentState) -> dict:
    """Execute autonomous actions and log all decisions (both auto and pending)."""
    db = get_db(state["db_session_id"])

    executed: list[RiskItem] = []

    # Execute autonomous actions
    for risk in state.get("autonomous_actions", []):
        best = risk["best_action"]
        result = execute_action(
            db, best["action"], risk["entity_id"],
            message=risk["explanation"]["problem"],
        )
        risk["action_result"] = result

        log_decision(
            db,
            risk_type=risk["type"],
            entity_id=risk["entity_id"],
            shipment_id=risk.get("shipment_id"),
            risk_score=risk["risk_score"],
            problem=risk["explanation"]["problem"],
            evidence=risk["explanation"]["evidence"],
            root_cause=risk["explanation"]["root_cause"],
            confidence=risk["explanation"]["confidence"],
            recommended_action=best["action"],
            action_details={"action_scores": risk["scored_actions"], "result": result},
            requires_approval=False,
            status="executed",
        )
        executed.append(risk)

    # Log pending-approval decisions (NOT executed — waiting for human)
    for risk in state.get("pending_approvals", []):
        best = risk["best_action"]
        log_decision(
            db,
            risk_type=risk["type"],
            entity_id=risk["entity_id"],
            shipment_id=risk.get("shipment_id"),
            risk_score=risk["risk_score"],
            problem=risk["explanation"]["problem"],
            evidence=risk["explanation"]["evidence"],
            root_cause=risk["explanation"]["root_cause"],
            confidence=risk["explanation"]["confidence"],
            recommended_action=best["action"],
            action_details={"action_scores": risk["scored_actions"]},
            requires_approval=True,
            status="pending_approval",
        )

    log.info("🎬 ACT — %d executed, %d awaiting approval",
             len(executed), len(state.get("pending_approvals", [])))

    return {"executed_risks": executed}


# ═════════════════════════════════════════════════════════════════════════════
# NODE: learn
# ═════════════════════════════════════════════════════════════════════════════

def learn_node(state: AgentState) -> dict:
    """Evaluate past outcomes and build the unified risk list + cycle summary."""
    db = get_db(state["db_session_id"])

    evaluate_outcomes(db)

    # Build combined risk list for the API
    all_risks: list[dict] = []

    for risk in state.get("autonomous_actions", []) + state.get("pending_approvals", []):
        all_risks.append({
            "type": risk["type"],
            "entity_id": risk["entity_id"],
            "risk_score": risk["risk_score"],
            "explanation": risk["explanation"],
            "recommended_action": risk["best_action"]["action"],
            "requires_approval": risk.get("requires_approval", False),
        })

    # Generate cycle summary
    n_ship = len(state.get("shipments", []))
    n_wh = len(state.get("all_warehouses", []))
    n_car = len(state.get("all_carriers", []))

    summary = _generate_cycle_summary(
        n_ship, n_wh, n_car, all_risks, state.get("cycle_count", 0),
    )

    log.info("📚 LEARN — %d total risks, summary generated", len(all_risks))

    return {"all_risks": all_risks, "summary": summary}


def _generate_cycle_summary(
    n_shipments: int, n_warehouses: int, n_carriers: int,
    risks: list[dict], cycle_count: int,
) -> str:
    """Generate a natural-language narrative of the agent cycle using Gemini."""
    delay_risks = [r for r in risks if r["type"] == "delay_risk"]
    bottlenecks = [r for r in risks if r["type"] == "bottleneck"]
    degraded = [r for r in risks if r["type"] == "carrier_degradation"]

    prompt = (
        "You are the AI Control Tower narrator for a logistics network. "
        "Summarize this monitoring cycle in 3-5 sentences for a human operator.\n\n"
        f"Network: {n_shipments} active shipments, {n_warehouses} warehouses, "
        f"{n_carriers} carriers.\n"
        f"Risks detected: {len(risks)} total — "
        f"{len(delay_risks)} shipment delay risks, "
        f"{len(bottlenecks)} warehouse bottlenecks, "
        f"{len(degraded)} carrier degradations.\n\n"
    )
    if delay_risks:
        top = delay_risks[0]
        prompt += (
            f"Highest delay risk: {top['entity_id']} "
            f"(score: {top['risk_score']}) — "
            f"action: {top['recommended_action']}.\n"
        )
    if bottlenecks:
        prompt += f"Bottleneck at: {bottlenecks[0]['entity_id']}.\n"
    if degraded:
        prompt += f"Degraded carrier: {degraded[0]['entity_id']}.\n"

    prompt += (
        "\nWrite a concise, professional operator briefing. "
        "Mention the most critical risk and action taken. "
        "Do NOT use JSON — respond in plain English."
    )

    result = call_llm(
        prompt,
        system_instruction="You are a logistics operations AI narrator.",
        caller="cycle_summary",
    )
    if result:
        return result

    # Rule-based fallback
    if not risks:
        return (
            f"Cycle {cycle_count}: Monitoring {n_shipments} active shipments "
            f"across {n_warehouses} warehouses and {n_carriers} carriers. "
            "No significant risks detected. Network operating normally."
        )
    return (
        f"Cycle {cycle_count}: Detected {len(risks)} risk(s) — "
        f"{len(delay_risks)} delay, {len(bottlenecks)} bottleneck, "
        f"{len(degraded)} carrier degradation. "
        f"Actions taken for the highest-priority issues."
    )
