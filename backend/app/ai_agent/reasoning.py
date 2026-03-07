"""
Reasoning engine — converts raw risk model predictions into structured,
human-readable explanations for the dashboard and decision log.

Uses Gemini LLM for richer natural-language explanations when available.
Fallback chain:  Gemini 3.1 Flash → Gemini 3.1 Flash Lite → rule-based templates.
"""

import json

from app.ai_agent.llm_client import call_llm_json

TRAFFIC_NAMES = {0: "LOW", 1: "MODERATE", 2: "HIGH", 3: "SEVERE"}


# ── LLM-enhanced explanation ─────────────────────────────────────────────────

def _llm_explain_delay_risk(
    shipment_id: str,
    features: dict,
    risk_score: float,
    origin: str,
    destination: str,
    evidence: dict,
) -> dict | None:
    """Ask Gemini to generate a richer natural-language explanation."""
    prompt = (
        f"You are an AI logistics analyst. A shipment {shipment_id} from {origin} "
        f"to {destination} has been flagged with a delay risk score of {risk_score:.2f} "
        f"(0 = no risk, 1 = certain delay).\n\n"
        f"Here is the operational evidence:\n{json.dumps(evidence, indent=2)}\n\n"
        f"Raw features: {json.dumps(features, indent=2)}\n\n"
        "Respond in JSON with exactly these fields:\n"
        '{"problem": "<concise 1-2 sentence problem description>", '
        '"root_cause": "<1-2 sentence root cause hypothesis>", '
        '"confidence": <float 0-1>}\n\n'
        "Be specific, reference the actual numbers, and keep it professional."
    )
    system = (
        "You are an expert logistics risk analyst. Always respond with valid JSON only. "
        "No markdown, no code fences, just raw JSON."
    )
    result = call_llm_json(prompt, system_instruction=system)
    if result and "problem" in result and "root_cause" in result:
        return {
            "problem": str(result["problem"]),
            "evidence": evidence,
            "root_cause": str(result["root_cause"]),
            "confidence": round(float(result.get("confidence", min(0.5 + risk_score * 0.45, 0.99))), 3),
            "llm_generated": True,
        }
    return None


def _llm_explain_bottleneck(warehouse: dict) -> dict | None:
    """Ask Gemini to explain a warehouse bottleneck."""
    prompt = (
        f"You are an AI logistics analyst. Warehouse {warehouse['warehouse_id']} in "
        f"{warehouse['location']} is experiencing congestion.\n\n"
        f"Current load: {warehouse['current_load']} / {warehouse['capacity']} "
        f"(congestion: {warehouse['congestion_score'] * 100:.0f}%)\n"
        f"Queue length: {warehouse['queue_length']} shipments waiting\n\n"
        "Respond in JSON with exactly these fields:\n"
        '{"problem": "<1-2 sentence problem>", '
        '"root_cause": "<1-2 sentence root cause>", '
        '"confidence": <float 0-1>}\n\n'
        "Be specific and reference actual numbers."
    )
    system = (
        "You are an expert logistics risk analyst. Always respond with valid JSON only. "
        "No markdown, no code fences, just raw JSON."
    )
    result = call_llm_json(prompt, system_instruction=system)
    if result and "problem" in result and "root_cause" in result:
        evidence = {
            "current_load": warehouse["current_load"],
            "capacity": warehouse["capacity"],
            "congestion_score": f"{warehouse['congestion_score'] * 100:.0f}%",
            "queue_length": warehouse["queue_length"],
        }
        return {
            "problem": str(result["problem"]),
            "evidence": evidence,
            "root_cause": str(result["root_cause"]),
            "confidence": round(float(result.get("confidence", 0.9)), 3),
            "llm_generated": True,
        }
    return None


def _llm_explain_carrier_degradation(carrier: dict) -> dict | None:
    """Ask Gemini to explain carrier reliability degradation."""
    prompt = (
        f"You are an AI logistics analyst. Carrier {carrier['name']} ({carrier['carrier_id']}) "
        f"has degraded reliability.\n\n"
        f"Reliability score: {carrier['reliability_score']:.2f}\n"
        f"Delay probability: {carrier['delay_probability']:.2f}\n"
        f"Pickup success rate: {carrier['pickup_success_rate']:.2f}\n"
        f"Delays: {carrier['total_delays']} / {carrier['total_shipments']} shipments\n\n"
        "Respond in JSON with exactly these fields:\n"
        '{"problem": "<1-2 sentence problem>", '
        '"root_cause": "<1-2 sentence root cause>", '
        '"confidence": <float 0-1>}\n\n'
        "Be specific and reference actual numbers."
    )
    system = (
        "You are an expert logistics risk analyst. Always respond with valid JSON only. "
        "No markdown, no code fences, just raw JSON."
    )
    result = call_llm_json(prompt, system_instruction=system)
    if result and "problem" in result and "root_cause" in result:
        evidence = {
            "reliability_score": carrier["reliability_score"],
            "delay_probability": carrier["delay_probability"],
            "pickup_success_rate": carrier["pickup_success_rate"],
            "total_delays": carrier["total_delays"],
            "total_shipments": carrier["total_shipments"],
        }
        return {
            "problem": str(result["problem"]),
            "evidence": evidence,
            "root_cause": str(result["root_cause"]),
            "confidence": round(float(result.get("confidence", 0.85)), 3),
            "llm_generated": True,
        }
    return None


# ── Public API (LLM first → rule-based fallback) ────────────────────────────


def explain_delay_risk(
    shipment_id: str,
    features: dict,
    risk_score: float,
    origin: str = "",
    destination: str = "",
) -> dict:
    """Generate a structured explanation for a high delay-risk prediction.

    Tries Gemini LLM first for richer output; falls back to rule-based templates.
    """
    # Build evidence dict (factual — always rule-based)
    evidence: dict = {}
    problems: list[str] = []
    causes: list[str] = []

    # ── Traffic ───────────────────────────────────────────────────────────
    traffic = features.get("traffic_level", 0)
    traffic_name = TRAFFIC_NAMES.get(int(traffic), "UNKNOWN")
    evidence["traffic_level"] = traffic_name
    if traffic >= 2:
        problems.append(f"High traffic on route ({traffic_name})")
        causes.append("Route traffic congestion")

    # ── Weather ───────────────────────────────────────────────────────────
    weather = features.get("weather_factor", 1.0)
    evidence["weather_factor"] = round(weather, 2)
    if weather > 1.3:
        problems.append(f"Adverse weather conditions (factor: {weather:.2f})")
        causes.append("Weather degradation on route")

    # ── Warehouse congestion ──────────────────────────────────────────────
    congestion = features.get("congestion_score", 0)
    evidence["warehouse_congestion"] = f"{congestion * 100:.0f}%"
    if congestion > 0.8:
        problems.append(f"Warehouse congestion at origin ({congestion * 100:.0f}%)")
        causes.append("Warehouse overload at origin")

    # ── Carrier reliability ───────────────────────────────────────────────
    reliability = features.get("reliability_score", 1.0)
    evidence["carrier_reliability"] = round(reliability, 3)
    if reliability < 0.6:
        problems.append(f"Low carrier reliability ({reliability:.2f})")
        causes.append("Carrier performance degradation")

    # ── Carrier delay probability ─────────────────────────────────────────
    delay_prob = features.get("delay_probability", 0)
    evidence["carrier_delay_probability"] = round(delay_prob, 3)
    if delay_prob > 0.3:
        problems.append(f"High carrier delay probability ({delay_prob:.2f})")
        causes.append("Carrier delay history")

    # ── SLA buffer ────────────────────────────────────────────────────────
    buffer = features.get("eta_sla_buffer_hours", 12)
    evidence["eta_sla_buffer_hours"] = round(buffer, 1)
    if buffer < 4:
        problems.append(f"Tight SLA buffer ({buffer:.1f} hours)")
        causes.append("Insufficient time margin before SLA deadline")

    # ── Distance ──────────────────────────────────────────────────────────
    distance = features.get("distance", 0)
    evidence["distance_km"] = round(distance, 1)
    if distance > 1500:
        problems.append(f"Long-distance shipment ({distance:.0f} km)")
        causes.append("Extended transit distance")

    # ── Build final explanation ───────────────────────────────────────────
    location_detail = f" from {origin} to {destination}" if origin and destination else ""
    problem_text = f"High delay risk detected for shipment {shipment_id}{location_detail}."
    if problems:
        problem_text += " Issues: " + "; ".join(problems) + "."

    root_cause = " combined with ".join(causes) if causes else "Multiple contributing risk factors"
    confidence = min(0.5 + risk_score * 0.45, 0.99)

    # ── Try LLM-enhanced explanation first ────────────────────────────────
    llm_result = _llm_explain_delay_risk(
        shipment_id, features, risk_score, origin, destination, evidence,
    )
    if llm_result:
        return llm_result

    # ── Rule-based fallback ───────────────────────────────────────────────
    return {
        "problem": problem_text,
        "evidence": evidence,
        "root_cause": root_cause,
        "confidence": round(confidence, 3),
        "llm_generated": False,
    }


def explain_bottleneck(warehouse: dict) -> dict:
    """Generate explanation for a warehouse bottleneck."""
    # Try LLM first
    llm_result = _llm_explain_bottleneck(warehouse)
    if llm_result:
        return llm_result

    # Rule-based fallback
    congestion_pct = warehouse["congestion_score"] * 100
    return {
        "problem": (
            f"Warehouse {warehouse['warehouse_id']} in {warehouse['location']} "
            f"is congested at {congestion_pct:.0f}% capacity."
        ),
        "evidence": {
            "current_load": warehouse["current_load"],
            "capacity": warehouse["capacity"],
            "congestion_score": f"{congestion_pct:.0f}%",
            "queue_length": warehouse["queue_length"],
        },
        "root_cause": (
            f"Current load ({warehouse['current_load']}) exceeds safe operating "
            f"threshold of warehouse capacity ({warehouse['capacity']}). "
            f"Queue length: {warehouse['queue_length']} shipments waiting."
        ),
        "confidence": round(min(0.7 + warehouse["congestion_score"] * 0.25, 0.99), 3),
        "llm_generated": False,
    }


def explain_carrier_degradation(carrier: dict) -> dict:
    """Generate explanation for carrier reliability degradation."""
    # Try LLM first
    llm_result = _llm_explain_carrier_degradation(carrier)
    if llm_result:
        return llm_result

    # Rule-based fallback
    return {
        "problem": (
            f"Carrier {carrier['name']} ({carrier['carrier_id']}) reliability "
            f"has degraded to {carrier['reliability_score']:.2f}."
        ),
        "evidence": {
            "reliability_score": carrier["reliability_score"],
            "delay_probability": carrier["delay_probability"],
            "pickup_success_rate": carrier["pickup_success_rate"],
            "total_delays": carrier["total_delays"],
            "total_shipments": carrier["total_shipments"],
        },
        "root_cause": (
            f"Carrier has accumulated {carrier['total_delays']} delays out of "
            f"{carrier['total_shipments']} shipments "
            f"(delay probability: {carrier['delay_probability']:.2f}, "
            f"pickup success rate: {carrier['pickup_success_rate']:.2f})."
        ),
        "confidence": round(min(0.75 + (1 - carrier["reliability_score"]) * 0.2, 0.99), 3),
        "llm_generated": False,
    }
