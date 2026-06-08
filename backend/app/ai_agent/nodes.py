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
    FEATURE_NAMES,
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
from app.ai_agent.actions import execute_action, _linestring_geojson
from app.ai_agent.learning import (
    log_decision,
    evaluate_outcomes,
    has_pending_decision,
    retrain_delay_model_from_learning_data,
    should_retrain_delay_model,
)
from app.ai_agent.llm_client import call_llm
from app.config import (
    RISK_THRESHOLD,
    BOTTLENECK_THRESHOLD,
    CARRIER_RELIABILITY_THRESHOLD,
)
from app.models import (
    CarrierPerformance,
    Route,
    Shipment,
    TrafficLevel,
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
    # For carrier degradation, we also identify an affected shipment so that
    # switch_carrier can be executed against a concrete shipment, not just
    # the carrier entity.
    carrier_risks: list[RiskItem] = []
    # Build a quick lookup of shipments by carrier
    shipments_by_carrier: dict[str, list[dict]] = {}
    for ship in state.get("shipments", []):
        cid = ship.get("carrier")
        if cid:
            shipments_by_carrier.setdefault(cid, []).append(ship)

    for c in state["all_carriers"]:
        if c["reliability_score"] < CARRIER_RELIABILITY_THRESHOLD:
            if has_pending_decision(db, c["carrier_id"], "carrier_degradation"):
                continue
            # Find the most at-risk shipment using this carrier
            affected = shipments_by_carrier.get(c["carrier_id"], [])
            # Pick a delayed or in-transit shipment if available
            target_ship = next(
                (s for s in affected if s.get("status") in ("delayed", "in_transit", "dispatched")),
                affected[0] if affected else None,
            )
            carrier_risks.append({
                "type": "carrier_degradation",
                "entity_id": target_ship["shipment_id"] if target_ship else c["carrier_id"],
                "shipment_id": target_ship["shipment_id"] if target_ship else None,
                "risk_score": round(1 - c["reliability_score"], 4),
                "raw_data": {
                    **c,
                    "affected_shipment": target_ship,
                },
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
    autonomous (auto-execute) vs approval-required.

    When the *best* action requires approval (reroute/switch_carrier),
    a companion ``send_alert`` is automatically queued as an autonomous
    action so the operator is notified immediately.
    """

    pending_approvals: list[RiskItem] = []
    autonomous_actions: list[RiskItem] = []
    companion_alerts: list[RiskItem] = []  # auto-fire send_alert alongside approval items

    # ── helper: if the best action requires approval, also queue send_alert ──
    def _classify(risk: RiskItem, scored: list[dict], best: dict):
        risk["scored_actions"] = scored
        risk["best_action"] = best
        risk["requires_approval"] = best["requires_approval"]

        if best["requires_approval"]:
            pending_approvals.append(risk)
            # Queue a companion send_alert so the operator gets an
            # immediate notification while the primary action awaits approval.
            alert_score = next(
                (s for s in scored if s["action"] == "send_alert"), None
            )
            if alert_score:
                companion = dict(risk)  # shallow copy
                companion["best_action"] = alert_score
                companion["requires_approval"] = False
                companion["is_companion_alert"] = True
                companion_alerts.append(companion)
        else:
            autonomous_actions.append(risk)

    # Delay risks
    for risk in state.get("delay_risks", []):
        features = risk["features"]
        scored = evaluate_delay_risk_actions(risk["risk_score"], features)
        best = select_best_action(scored, context={"risk_score": risk["risk_score"], **features})
        _classify(risk, scored, best)

    # Bottlenecks
    for risk in state.get("bottleneck_risks", []):
        scored = evaluate_bottleneck_actions(risk["raw_data"])
        best = select_best_action(scored, context={
            "risk_score": risk["risk_score"],
            "congestion_score": risk["risk_score"],
        })
        _classify(risk, scored, best)

    # Carrier degradation
    for risk in state.get("carrier_risks", []):
        scored = evaluate_carrier_degradation_actions(risk["raw_data"])
        best = select_best_action(scored, context={
            "risk_score": risk["risk_score"],
            "reliability_score": risk["raw_data"]["reliability_score"],
        })
        _classify(risk, scored, best)

    # Merge companion alerts into autonomous list
    autonomous_actions.extend(companion_alerts)

    log.info("⚖️  DECIDE — %d autonomous (%d companion alerts), %d need approval",
             len(autonomous_actions), len(companion_alerts), len(pending_approvals))

    return {
        "pending_approvals": pending_approvals,
        "autonomous_actions": autonomous_actions,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Helper: build action_details for decision log
# ═════════════════════════════════════════════════════════════════════════════

def _build_action_details(risk: RiskItem, best: dict, result: dict | None = None) -> dict:
    """Build action_details dict, special-casing companion alerts so their
    reasoning chain shows only *their own* score instead of the parent
    decision's full scored_actions (which confusingly shows reroute at top)."""

    details: dict = {}

    if risk.get("is_companion_alert"):
        # Only include the companion's own score + a pointer to the primary action
        companion_score = next(
            (s for s in risk["scored_actions"] if s["action"] == best["action"]),
            best,
        )
        primary_action = next(
            (s for s in risk["scored_actions"]
             if s.get("requires_approval") and s["action"] != best["action"]),
            None,
        )
        details["action_scores"] = [companion_score]
        details["is_companion_alert"] = True
        if primary_action:
            details["primary_action"] = primary_action["action"]
            details["primary_action_score"] = round(primary_action["total_score"], 4)
    else:
        details["action_scores"] = risk["scored_actions"]

    if result is not None:
        details["result"] = result

    return details


def _build_decision_evidence(risk: RiskItem) -> dict:
    """Include model inputs in delay-risk evidence so resolved outcomes can train."""
    evidence = dict(risk.get("explanation", {}).get("evidence") or {})
    if risk["type"] == "delay_risk":
        features = risk.get("features") or {}
        evidence["model_features"] = {
            name: float(features[name])
            for name in FEATURE_NAMES
            if name in features
        }
        evidence["model_feature_names"] = list(FEATURE_NAMES)
    return evidence


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
            evidence=_build_decision_evidence(risk),
            root_cause=risk["explanation"]["root_cause"],
            confidence=risk["explanation"]["confidence"],
            recommended_action=best["action"],
            action_details=_build_action_details(risk, best, result),
            requires_approval=False,
            status="executed",
        )
        executed.append(risk)

    # Log pending-approval decisions (NOT executed — waiting for human)
    for risk in state.get("pending_approvals", []):
        best = risk["best_action"]
        # Include pre-execution context so the dashboard can display
        # meaningful info (shipment route, carrier details) while pending.
        action_context: dict = {"action_scores": risk["scored_actions"]}
        raw = risk.get("raw_data", {})
        if best["action"] == "switch_carrier":
            action_context["current_carrier"] = raw.get("carrier_id")
            action_context["current_carrier_name"] = raw.get("name")
            action_context["current_reliability"] = raw.get("reliability_score")
            action_context["current_delay_prob"] = raw.get("delay_probability")
            action_context["shipment_id"] = risk.get("shipment_id") or risk.get("entity_id")
            affected = raw.get("affected_shipment")
            if affected:
                action_context["origin"] = affected.get("origin")
                action_context["destination"] = affected.get("destination")
                action_context["current_route"] = affected.get("route_id")

            # Pre-compute the proposed new carrier so the operator sees
            # the comparison *before* approving.
            try:
                sid = action_context.get("shipment_id")
                if sid:
                    shipment_obj = db.query(Shipment).filter_by(shipment_id=sid).first()
                    if shipment_obj:
                        best_carrier = (
                            db.query(CarrierPerformance)
                            .filter(CarrierPerformance.carrier_id != shipment_obj.carrier)
                            .order_by(CarrierPerformance.reliability_score.desc())
                            .first()
                        )
                        if best_carrier:
                            action_context["proposed_new_carrier"] = best_carrier.carrier_id
                            action_context["proposed_new_carrier_name"] = best_carrier.name
                            action_context["proposed_new_reliability"] = round(best_carrier.reliability_score, 3)
                            action_context["proposed_new_delay_prob"] = round(best_carrier.delay_probability, 3)
                        # Include route geometry for map preview
                        route_obj = db.query(Route).filter_by(route_id=shipment_obj.route_id).first() if shipment_obj.route_id else None
                        if route_obj:
                            action_context["route_geometry"] = _linestring_geojson(route_obj.path)
            except Exception:
                pass  # best-effort preview

        elif best["action"] == "reroute_shipment":
            action_context["shipment_id"] = risk.get("shipment_id") or risk.get("entity_id")
            action_context["origin"] = raw.get("origin")
            action_context["destination"] = raw.get("destination")
            action_context["current_route"] = raw.get("route_id")

            # Pre-compute the proposed new route so the operator sees the
            # old vs new comparison *before* approving.
            try:
                sid = action_context.get("shipment_id")
                if sid:
                    shipment_obj = db.query(Shipment).filter_by(shipment_id=sid).first()
                    if shipment_obj:
                        old_route = db.query(Route).filter_by(route_id=shipment_obj.route_id).first() if shipment_obj.route_id else None
                        best_route = (
                            db.query(Route)
                            .filter(Route.route_id != shipment_obj.route_id)
                            .filter(Route.traffic_level.in_([TrafficLevel.low, TrafficLevel.moderate]))
                            .order_by(Route.weather_factor.asc())
                            .first()
                        )
                        if old_route:
                            action_context["old_route_geometry"] = _linestring_geojson(old_route.path)
                        if best_route:
                            action_context["proposed_new_route"] = best_route.route_id
                            action_context["proposed_new_route_origin"] = best_route.origin
                            action_context["proposed_new_route_destination"] = best_route.destination
                            action_context["new_route_geometry"] = _linestring_geojson(best_route.path)
            except Exception:
                pass  # best-effort preview

        log_decision(
            db,
            risk_type=risk["type"],
            entity_id=risk["entity_id"],
            shipment_id=risk.get("shipment_id"),
            risk_score=risk["risk_score"],
            problem=risk["explanation"]["problem"],
            evidence=_build_decision_evidence(risk),
            root_cause=risk["explanation"]["root_cause"],
            confidence=risk["explanation"]["confidence"],
            recommended_action=best["action"],
            action_details=action_context,
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
    cycle_count = state.get("cycle_count", 0)
    if should_retrain_delay_model(cycle_count):
        retrain_result = retrain_delay_model_from_learning_data(db, get_delay_model())
        if retrain_result["retrained"]:
            training = retrain_result["training"]
            log.info(
                "📈 RETRAIN — delay model source=%s real=%d synthetic=%d accuracy=%.3f",
                training["source"],
                training["real_samples"],
                training["synthetic_samples"],
                training["accuracy"],
            )
        else:
            log.info(
                "📈 RETRAIN skipped — %d/%d real samples available",
                retrain_result["real_samples"],
                retrain_result["min_samples"],
            )

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
