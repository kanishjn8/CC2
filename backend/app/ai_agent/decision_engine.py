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
    """
    risk_score = context.get("risk_score", 0.5)
    congestion = context.get("congestion_score", 0.5)
    reliability = context.get("reliability_score", 0.7)

    scores: dict[str, float] = {}

    if action == "reroute_shipment":
        scores = {
            "sla_improvement": 0.7 + 0.3 * risk_score,
            "cost_impact": 0.4,
            "operational_risk": 0.5,
            "reversibility": 0.5,
        }
    elif action == "prioritize_loading":
        scores = {
            "sla_improvement": 0.5 + 0.3 * congestion,
            "cost_impact": 0.8,
            "operational_risk": 0.9,
            "reversibility": 0.9,
        }
    elif action == "switch_carrier":
        scores = {
            "sla_improvement": 0.6 + 0.3 * (1 - reliability),
            "cost_impact": 0.3,
            "operational_risk": 0.4,
            "reversibility": 0.3,
        }
    elif action == "send_alert":
        scores = {
            "sla_improvement": 0.3,
            "cost_impact": 1.0,
            "operational_risk": 1.0,
            "reversibility": 1.0,
        }
    elif action == "reserve_capacity":
        scores = {
            "sla_improvement": 0.4 + 0.3 * congestion,
            "cost_impact": 0.6,
            "operational_risk": 0.7,
            "reversibility": 0.8,
        }
    else:
        scores = {
            "sla_improvement": 0.0,
            "cost_impact": 0.0,
            "operational_risk": 0.0,
            "reversibility": 0.0,
        }

    total = (
        0.40 * scores["sla_improvement"]
        + 0.20 * scores["cost_impact"]
        + 0.25 * scores["operational_risk"]
        + 0.15 * scores["reversibility"]
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

    candidates = ["send_alert", "prioritize_loading"]

    if risk_score > 0.7:
        candidates.append("reroute_shipment")
    if risk_score > 0.75 and features.get("reliability_score", 1.0) < 0.55:
        candidates.append("switch_carrier")

    scored = [score_action(a, context) for a in candidates]
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


def evaluate_bottleneck_actions(warehouse_info: dict) -> list[dict]:
    """Evaluate candidate actions for a warehouse bottleneck."""
    context = {
        "risk_score": warehouse_info["congestion_score"],
        "congestion_score": warehouse_info["congestion_score"],
        "eta_sla_buffer_hours": 8,
        "reliability_score": 0.7,
    }

    candidates = ["send_alert", "reserve_capacity", "prioritize_loading"]
    scored = [score_action(a, context) for a in candidates]
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


def evaluate_carrier_degradation_actions(carrier_info: dict) -> list[dict]:
    """Evaluate candidate actions for a degraded carrier."""
    context = {
        "risk_score": 1 - carrier_info["reliability_score"],
        "congestion_score": 0.5,
        "eta_sla_buffer_hours": 12,
        "reliability_score": carrier_info["reliability_score"],
    }

    candidates = ["send_alert", "switch_carrier"]
    scored = [score_action(a, context) for a in candidates]
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
    result = call_llm_json(prompt, system_instruction=system)
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
