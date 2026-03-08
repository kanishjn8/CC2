"""
LangGraph graph definition — builds the Observe → Detect → Reason → Decide → Act → Learn
pipeline with conditional routing for human-in-the-loop approval.
"""

import logging

from langgraph.graph import StateGraph, END

from app.ai_agent.state import AgentState
from app.ai_agent.nodes import (
    observe_node,
    detect_risks_node,
    reason_node,
    decide_node,
    act_node,
    learn_node,
)

log = logging.getLogger("cc2.graph")


def _route_after_detect(state: AgentState) -> str:
    """Skip the rest of the pipeline if no risks were detected."""
    has_risks = (
        state.get("delay_risks")
        or state.get("bottleneck_risks")
        or state.get("carrier_risks")
    )
    if has_risks:
        return "reason"
    return "learn"     # straight to learn (evaluate past outcomes + summary)


def build_agent_graph() -> StateGraph:
    """Construct and compile the LangGraph agent pipeline.

    Graph layout:
        observe → detect_risks ─┬─ (has risks) → reason → decide → act → learn → END
                                 └─ (no risks)  ──────────────────────────→ learn → END
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("observe", observe_node)
    graph.add_node("detect_risks", detect_risks_node)
    graph.add_node("reason", reason_node)
    graph.add_node("decide", decide_node)
    graph.add_node("act", act_node)
    graph.add_node("learn", learn_node)

    # Edges
    graph.set_entry_point("observe")
    graph.add_edge("observe", "detect_risks")

    # Conditional: skip reasoning/deciding/acting when no risks found
    graph.add_conditional_edges(
        "detect_risks",
        _route_after_detect,
        {"reason": "reason", "learn": "learn"},
    )

    graph.add_edge("reason", "decide")
    graph.add_edge("decide", "act")
    graph.add_edge("act", "learn")
    graph.add_edge("learn", END)

    return graph.compile()
