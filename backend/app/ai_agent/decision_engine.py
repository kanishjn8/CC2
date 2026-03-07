"""
Decision engine — evaluates and scores possible interventions for detected risks.
Includes the guardrail system that defines autonomous vs. approval-required actions.

Uses Gemini LLM to reason about edge cases where the top-2 actions are
close in score.  Fallback: pure heuristic scoring (always available).
"""

import json

from app.ai_agent.llm_client import call_llm_json

# ── Guardrail definitions ────────────────────────────────────────────────────

AUTONOMOUS_ACTIONS = frozenset({
    "prioritize_loading",
    "send_alert",
    "reserve_capacity",
})

APPROVAL_REQUIRED_ACTIONS = frozenset({
    "reroute_shipment",
    "switch_carrier",
})


def requires_approval(action: str) -> bool:
    """Return True if the action must be approved by a human operator."""
    return action in APPROVAL_REQUIRED_ACTIONS


# ── Action scoring ───────────────────────────────────────────────────────────

def score_action(action: str, context: dict) -> dict:
    """Score a candidate action across four criteria (all 0–1, higher = better).

    Criteria:
      sla_improvement  — estimated improvement to SLA compliance
      cost_impact      — cost efficiency (1 = free, 0 = expensive)
      operational_risk — safety of the action (1 = very safe)
      reversibility    — ease of undoing the action (1 = trivially reversible)

    Weights: SLA 55%, safety 20%, cost 15%, reversibility 10%.
    SLA is the dominant driver — a high-risk shipment must be acted on decisively.
    send_alert has limited SLA improvement (it doesn't fix the route/carrier),
    so at high risk scores reroute/switch_carrier naturally beat it.
    """
    risk_score  = context.get("risk_score", 0.5)
    congestion  = context.get("congestion_score", 0.5)
    reliability = context.get("reliability_score", 0.7)
    sla_buffer  = context.get("eta_sla_buffer_hours", 12.0)
    # 0 = comfortable (24h+), 1 = critical (0h)
    sla_urgency = max(0.0, min(1.0, 1.0 - sla_buffer / 24.0))

    scores: dict[str, float] = {}

    if action == "reroute_shipment":
        # Directly reduces transit time and avoids bad traffic — highest SLA fix
        scores = {
            "sla_improvement": 0.55 + 0.45 * risk_score,   # 0.82 at 0.6, 1.0 at 1.0
            "cost_impact": 0.35,
            "operational_risk": 0.55,
            "reversibility": 0.40,
        }
    elif action == "prioritize_loading":
        # Helps at origin warehouse; moderate SLA gain, low cost
        scores = {
            "sla_improvement": 0.30 + 0.20 * congestion,   # 0.40 at cong=0.5
            "cost_impact": 0.85,
            "operational_risk": 0.90,
            "reversibility": 0.90,
        }
    elif action == "switch_carrier":
        # Fixes reliability issues at the source; costly and risky
        scores = {
            "sla_improvement": 0.50 + 0.45 * (1 - reliability),  # 0.72 at rel=0.5
            "cost_impact": 0.25,
            "operational_risk": 0.40,
            "reversibility": 0.25,
        }
    elif action == "send_alert":
        # Notifies humans — limited direct SLA fix; always safe and cheap
        scores = {
            "sla_improvement": 0.15 + 0.25 * risk_score,   # 0.30 at 0.6, 0.40 at 1.0
            "cost_impact": 1.0,
            "operational_risk": 1.0,
            "reversibility": 1.0,
        }
    elif action == "reserve_capacity":
        # Frees warehouse space; useful for bottlenecks
        scores = {
            "sla_improvement": 0.38 + 0.30 * congestion,
            "cost_impact": 0.60,
            "operational_risk": 0.70,
            "reversibility": 0.80,
        }
    else:
        scores = {
            "sla_improvement": 0.0,
            "cost_impact": 0.0,
            "operational_risk": 0.0,
            "reversibility": 0.0,
        }

    # SLA is king; safety matters more than cost for high-stakes ops
    total = (
        0.55 * scores["sla_improvement"]
        + 0.15 * scores["cost_impact"]
        + 0.20 * scores["operational_risk"]
        + 0.10 * scores["reversibility"]
    )

    return {
        "action": action,
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "total_score": round(total, 3),
        "requires_approval": requires_approval(action),
    }


# ── Per-risk evaluators ──────────────────────────────────────────────────────

def evaluate_delay_risk_actions(risk_score: float, features: dict) -> list[dict]:
    """Evaluate and rank candidate actions for a high delay-risk shipment."""
    context = {"risk_score": risk_score, **features}

    # send_alert is always a candidate — escalates to human operator
    candidates = ["send_alert", "prioritize_loading"]

    # Reroute kicks in at moderate risk (>0.62) — previously was 0.7, too high
    if risk_score > 0.62:
        candidates.append("reroute_shipment")

    # Switch carrier when reliability is degraded (>0.65 risk AND bad carrier)
    if risk_score > 0.65 and features.get("reliability_score", 1.0) < 0.65:
        candidates.append("switch_carrier")

    scored = [score_action(a, context) for a in candidates]
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


def evaluate_bottleneck_actions(warehouse_info: dict) -> list[dict]:
    """Evaluate candidate actions for a warehouse bottleneck."""
    congestion = warehouse_info["congestion_score"]
    context = {
        "risk_score": congestion,
        "congestion_score": congestion,
        "eta_sla_buffer_hours": 8,
        "reliability_score": 0.7,
    }

    # Prioritize loading + reserve capacity are primary bottleneck tools.
    # For high congestion (>0.80) also consider rerouting shipments away.
    candidates = ["send_alert", "reserve_capacity", "prioritize_loading"]
    if congestion > 0.80:
        candidates.append("reroute_shipment")

    scored = [score_action(a, context) for a in candidates]
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


def evaluate_carrier_degradation_actions(carrier_info: dict) -> list[dict]:
    """Evaluate candidate actions for a degraded carrier.

    switch_carrier has a boosted SLA score in this context because it directly
    resolves the root cause (unreliable carrier), unlike the generic scorer.
    """
    reliability = carrier_info["reliability_score"]
    risk = 1.0 - reliability  # high unreliability = high risk

    context = {
        "risk_score": risk,
        "congestion_score": 0.5,
        "eta_sla_buffer_hours": 12,
        "reliability_score": reliability,
    }

    # Score all candidates
    candidates_raw = ["send_alert", "switch_carrier"]
    scored = [score_action(a, context) for a in candidates_raw]

    # Boost switch_carrier: it's the definitive fix for carrier degradation.
    # Apply a +0.20 domain bonus to its total_score for this evaluator only.
    for s in scored:
        if s["action"] == "switch_carrier":
            boosted = min(1.0, s["total_score"] + 0.20)
            s["total_score"] = round(boosted, 3)
            s["domain_boost"] = True  # mark so UI can show it

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


def _llm_break_tie(scored_actions: list[dict], context: dict) -> dict | None:
    """Ask Gemini to break a tie when top-2 actions are within 0.05 score."""
    if len(scored_actions) < 2:
        return None
    gap = scored_actions[0]["total_score"] - scored_actions[1]["total_score"]
    if gap > 0.05:
        return None  # Clear winner — no LLM needed

    top_two = scored_actions[:2]
    prompt = (
        "You are an AI logistics operations advisor. Two candidate interventions "
        "are very close in score and you must decide which is better.\n\n"
        f"Context: {json.dumps(context, indent=2)}\n\n"
        f"Option A: {json.dumps(top_two[0], indent=2)}\n"
        f"Option B: {json.dumps(top_two[1], indent=2)}\n\n"
        "Consider: SLA impact, cost efficiency, safety, and reversibility. "
        "Which option is better? Respond in JSON:\n"
        '{"chosen": "A" or "B", "reasoning": "<1-2 sentence justification>"}'
    )
    system = (
        "You are an expert logistics decision advisor. "
        "Always respond with valid JSON only. No markdown or code fences."
    )
    result = call_llm_json(prompt, system_instruction=system, caller="tiebreaker")
    if result and result.get("chosen") in ("A", "B"):
        idx = 0 if result["chosen"] == "A" else 1
        chosen = dict(top_two[idx])
        chosen["llm_tiebreaker"] = True
        chosen["llm_reasoning"] = result.get("reasoning", "")
        return chosen
    return None


def select_best_action(scored_actions: list[dict], context: dict | None = None) -> dict:
    """Return the highest-scoring action. Uses LLM to break ties when scores are close."""
    if not scored_actions:
        return {
            "action": "send_alert",
            "scores": {},
            "total_score": 0.0,
            "requires_approval": False,
            "llm_tiebreaker": False,
        }

    # Try LLM tiebreaker when top-2 are close
    if context and len(scored_actions) >= 2:
        llm_pick = _llm_break_tie(scored_actions, context)
        if llm_pick:
            return llm_pick

    return scored_actions[0]
