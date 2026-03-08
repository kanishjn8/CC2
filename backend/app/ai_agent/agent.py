"""
Main agent loop — orchestrates the full
Observe → Detect → Reason → Decide → Act → Learn cycle
via a LangGraph StateGraph.

Runs in a background thread alongside the simulation engine.
"""

import logging
import threading
import time
import traceback
import uuid

from sqlalchemy.orm import Session

log = logging.getLogger("cc2.agent")

from app.ai_agent.risk_models import DelayRiskModel
from app.ai_agent.graph import build_agent_graph
from app.ai_agent.nodes import set_delay_model, register_db, unregister_db
from app.config import AGENT_TICK_INTERVAL
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
        self._graph = None  # compiled LangGraph

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
        """Train ML models and compile graph — call once at startup."""
        self.delay_model.train()
        set_delay_model(self.delay_model)
        self._graph = build_agent_graph()
        log.info("✅ LangGraph agent pipeline compiled")

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
                self._run_graph(db)
                db.commit()
                self._cycle_count += 1
            except Exception:
                db.rollback()
                log.error("Agent cycle error:\n%s", traceback.format_exc())
            finally:
                db.close()
            time.sleep(self.tick_interval)

    # ── Graph execution ──────────────────────────────────────────────────

    def _run_graph(self, db: Session):
        """Execute one full cycle via the LangGraph pipeline."""
        db_key = f"db-{uuid.uuid4().hex[:8]}"
        register_db(db_key, db)

        try:
            initial_state = {
                "db_session_id": db_key,
                "cycle_count": self._cycle_count,
            }

            # Invoke the compiled graph
            result = self._graph.invoke(initial_state)

            # Extract results
            self._last_risks = result.get("all_risks", [])
            self._last_summary = result.get("summary", "")

            log.info(
                "🔄 Cycle %d complete — %d risk(s) detected via LangGraph",
                self._cycle_count, len(self._last_risks),
            )
        finally:
            unregister_db(db_key)

    # ── Manual trigger ───────────────────────────────────────────────────

    def run_single_cycle(self, db: Session) -> list[dict]:
        """Run one analysis cycle on demand (used by the /agent/analyze endpoint)."""
        self._run_graph(db)
        self._cycle_count += 1
        return self._last_risks
