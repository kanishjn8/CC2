"""
Main agent loop — orchestrates the full
Observe → Reason → Decide → Act → Learn cycle.

Runs in a background thread alongside the simulation engine.
"""

import logging
import threading
import time
import traceback

from sqlalchemy.orm import Session

log = logging.getLogger("cc2.agent")

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
    AGENT_TICK_INTERVAL,
    RISK_THRESHOLD,
    BOTTLENECK_THRESHOLD,
    CARRIER_RELIABILITY_THRESHOLD,
)
from app.database import SessionLocal


class AgentLoop:
    """Background agent that continuously monitors and acts on logistics risks."""

    def __init__(self, tick_interval: float = AGENT_TICK_INTERVAL):
        self.tick_interval = tick_interval
        self.delay_model = DelayRiskModel()
        self._running = False
        self._thread: threading.Thread | None = None
        self._cycle_count = 0
        self._last_risks: list[dict] = []
        self._last_summary: str = ""

    # ── Public properties ────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def last_risks(self) -> list[dict]:
        return list(self._last_risks)

    @property
    def last_summary(self) -> str:
        return self._last_summary

    # ── Lifecycle ────────────────────────────────────────────────────────

    def initialize(self):
        """Train ML models — call once at startup."""
        self.delay_model.train()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ── Internal loop ────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            db = SessionLocal()
            try:
                self._cycle(db)
                db.commit()
                self._cycle_count += 1
            except Exception:
                db.rollback()
                log.error("Agent cycle error:\n%s", traceback.format_exc())
            finally:
                db.close()
            time.sleep(self.tick_interval)

    # ── Single cycle ─────────────────────────────────────────────────────

    def _cycle(self, db: Session):
        """Execute one full Observe → Reason → Decide → Act → Learn cycle."""
        risks: list[dict] = []

        # ── OBSERVE ──────────────────────────────────────────────────────
        shipments = get_active_shipments(db)
        warehouses_by_loc = get_warehouses_by_location(db)
        carriers_map = get_carriers_map(db)
        routes_map = get_routes_map(db)
        all_warehouses = get_all_warehouses(db)
        all_carriers = get_all_carriers(db)

        # ── REASON + DECIDE + ACT: Delay risk per shipment ───────────────
        for ship in shipments:
            carrier = carriers_map.get(ship.carrier)
            route = routes_map.get(ship.route_id) if ship.route_id else None
            warehouse = warehouses_by_loc.get(ship.origin)

            features = build_shipment_features(ship, carrier, route, warehouse)
            risk_score = self.delay_model.predict(features)

            if risk_score < RISK_THRESHOLD:
                continue

            # Deduplication — skip if already tracking this shipment
            if has_pending_decision(db, ship.shipment_id, "delay_risk"):
                continue

            explanation = explain_delay_risk(
                ship.shipment_id, features, risk_score,
                origin=ship.origin, destination=ship.destination,
            )

            scored_actions = evaluate_delay_risk_actions(risk_score, features)
            best = select_best_action(scored_actions, context={"risk_score": risk_score, **features})

            needs_approval = best["requires_approval"]
            status = "pending_approval" if needs_approval else "executed"
            action_result = None

            if not needs_approval:
                action_result = execute_action(
                    db, best["action"], ship.shipment_id,
                    message=explanation["problem"],
                )

            log_decision(
                db,
                risk_type="delay_risk",
                entity_id=ship.shipment_id,
                shipment_id=ship.shipment_id,
                risk_score=risk_score,
                problem=explanation["problem"],
                evidence=explanation["evidence"],
                root_cause=explanation["root_cause"],
                confidence=explanation["confidence"],
                recommended_action=best["action"],
                action_details={"action_scores": scored_actions, "result": action_result},
                requires_approval=needs_approval,
                status=status,
            )

            risks.append({
                "type": "delay_risk",
                "entity_id": ship.shipment_id,
                "risk_score": round(risk_score, 4),
                "explanation": explanation,
                "recommended_action": best["action"],
                "requires_approval": needs_approval,
            })

        # ── REASON + DECIDE + ACT: Bottlenecks ──────────────────────────
        bottlenecks = detect_bottlenecks(all_warehouses, BOTTLENECK_THRESHOLD)
        for bn in bottlenecks:
            if has_pending_decision(db, bn["warehouse_id"], "bottleneck"):
                continue

            explanation = explain_bottleneck(bn)
            scored_actions = evaluate_bottleneck_actions(bn)
            best = select_best_action(scored_actions, context={
                "risk_score": bn["congestion_score"],
                "congestion_score": bn["congestion_score"],
            })

            action_result = execute_action(
                db, best["action"], bn["warehouse_id"],
                message=explanation["problem"],
            )

            log_decision(
                db,
                risk_type="bottleneck",
                entity_id=bn["warehouse_id"],
                shipment_id=None,
                risk_score=bn["congestion_score"],
                problem=explanation["problem"],
                evidence=explanation["evidence"],
                root_cause=explanation["root_cause"],
                confidence=explanation["confidence"],
                recommended_action=best["action"],
                action_details={"action_scores": scored_actions, "result": action_result},
                requires_approval=False,
                status="executed",
            )

            risks.append({
                "type": "bottleneck",
                "entity_id": bn["warehouse_id"],
                "risk_score": round(bn["congestion_score"], 4),
                "explanation": explanation,
                "recommended_action": best["action"],
                "requires_approval": False,
            })

        # ── REASON + DECIDE + ACT: Carrier degradation ──────────────────
        degraded = detect_carrier_degradation(all_carriers, CARRIER_RELIABILITY_THRESHOLD)
        for d in degraded:
            if has_pending_decision(db, d["carrier_id"], "carrier_degradation"):
                continue

            explanation = explain_carrier_degradation(d)
            scored_actions = evaluate_carrier_degradation_actions(d)
            best = select_best_action(scored_actions, context={
                "risk_score": 1 - d["reliability_score"],
                "reliability_score": d["reliability_score"],
            })

            needs_approval = best["requires_approval"]
            status = "pending_approval" if needs_approval else "executed"
            action_result = None

            if not needs_approval:
                action_result = execute_action(
                    db, best["action"], d["carrier_id"],
                    message=explanation["problem"],
                )

            log_decision(
                db,
                risk_type="carrier_degradation",
                entity_id=d["carrier_id"],
                shipment_id=None,
                risk_score=1 - d["reliability_score"],
                problem=explanation["problem"],
                evidence=explanation["evidence"],
                root_cause=explanation["root_cause"],
                confidence=explanation["confidence"],
                recommended_action=best["action"],
                action_details={"action_scores": scored_actions, "result": action_result},
                requires_approval=needs_approval,
                status=status,
            )

            risks.append({
                "type": "carrier_degradation",
                "entity_id": d["carrier_id"],
                "risk_score": round(1 - d["reliability_score"], 4),
                "explanation": explanation,
                "recommended_action": best["action"],
                "requires_approval": needs_approval,
            })

        # ── LEARN ────────────────────────────────────────────────────────
        evaluate_outcomes(db)

        self._last_risks = risks

        # ── LLM CYCLE SUMMARY ────────────────────────────────────────────
        self._last_summary = self._summarize_cycle(
            len(shipments), len(all_warehouses), len(all_carriers), risks,
        )

    # ── Manual trigger ───────────────────────────────────────────────────

    def run_single_cycle(self, db: Session) -> list[dict]:
        """Run one analysis cycle on demand (used by the /agent/analyze endpoint)."""
        self._cycle(db)
        self._cycle_count += 1
        return self._last_risks

    # ── LLM cycle summary ────────────────────────────────────────────────

    def _summarize_cycle(
        self,
        n_shipments: int,
        n_warehouses: int,
        n_carriers: int,
        risks: list[dict],
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

        result = call_llm(prompt, system_instruction="You are a logistics operations AI narrator.", caller="cycle_summary")
        if result:
            return result

        # Rule-based fallback summary
        if not risks:
            return (
                f"Cycle {self._cycle_count}: Monitoring {n_shipments} active shipments "
                f"across {n_warehouses} warehouses and {n_carriers} carriers. "
                "No significant risks detected. Network operating normally."
            )
        return (
            f"Cycle {self._cycle_count}: Detected {len(risks)} risk(s) — "
            f"{len(delay_risks)} delay, {len(bottlenecks)} bottleneck, "
            f"{len(degraded)} carrier degradation. "
            f"Actions taken for the highest-priority issues."
        )
