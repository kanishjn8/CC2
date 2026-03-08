"""
Shipment Lifecycle Manager — queue-based data flow.

Runs as a background thread alongside the SimPy simulation and AI agent.
Responsibilities:
  1. Mark delivered/failed shipments with a ``delivered_at`` timestamp.
  2. After a grace period (~20 s) set ``is_active = False`` so the shipment
     disappears from the map and shipment table (but stays in the DB forever
     for logs and audit).
  3. Spawn a replacement shipment for every pruned one — keeping the total
     active count roughly constant (the queue effect).
  4. Randomly inject new disruptions (delays, status regressions) to keep
     the agent busy.

The SimPy simulation still handles physics-level ticks (geo interpolation,
carrier fluctuations, etc.).  This manager handles the business-level
lifecycle.
"""

import logging
import random
import threading
import time
import uuid
from datetime import datetime, timedelta

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    CarrierPerformance,
    Route,
    Shipment,
    ShipmentStatus,
    TrafficLevel,
)
from app.seed import CITY_COORDS, CITIES
from app.config import (
    LIFECYCLE_TICK_INTERVAL,
    LIFECYCLE_GRACE_PERIOD,
    LIFECYCLE_TARGET_ACTIVE,
)

log = logging.getLogger("cc2.lifecycle")

# ── Tunables (from config / env) ────────────────────────────────────────────
TICK_INTERVAL = LIFECYCLE_TICK_INTERVAL
GRACE_PERIOD = LIFECYCLE_GRACE_PERIOD
TARGET_ACTIVE = LIFECYCLE_TARGET_ACTIVE
MAX_SPAWN_PER_TICK = 4       # never create more than this many per tick


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _point(city: str):
    lon, lat = CITY_COORDS[city]
    return from_shape(Point(lon, lat), srid=4326)


# ── Core lifecycle logic ─────────────────────────────────────────────────────

def _stamp_terminal_shipments(db: Session):
    """Set ``delivered_at`` on shipments that just reached a terminal state."""
    terminal = (
        db.query(Shipment)
        .filter(
            Shipment.status.in_([ShipmentStatus.delivered, ShipmentStatus.failed]),
            Shipment.delivered_at.is_(None),
            Shipment.is_active.is_(True),
        )
        .all()
    )
    now = datetime.utcnow()
    for s in terminal:
        s.delivered_at = now
    if terminal:
        log.debug("🏁 Stamped %d terminal shipments with delivered_at", len(terminal))


def _prune_expired(db: Session) -> int:
    """Hide shipments whose grace period has elapsed.  Returns count pruned."""
    cutoff = datetime.utcnow() - timedelta(seconds=GRACE_PERIOD)
    expired = (
        db.query(Shipment)
        .filter(
            Shipment.is_active.is_(True),
            Shipment.delivered_at.isnot(None),
            Shipment.delivered_at < cutoff,
        )
        .all()
    )
    for s in expired:
        s.is_active = False
    if expired:
        log.debug("🗑️  Pruned %d expired shipments from active view", len(expired))
    return len(expired)


def _count_active(db: Session) -> int:
    return (
        db.query(Shipment)
        .filter(Shipment.is_active.is_(True))
        .count()
    )


def _spawn_shipment(db: Session, carriers: list, routes: list) -> Shipment:
    """Create a single new shipment with randomised attributes."""
    now = datetime.utcnow()

    carrier = random.choice(carriers)
    route = random.choice(routes)

    # Randomise initial status — mostly created/dispatched
    roll = random.random()
    if roll < 0.50:
        status = ShipmentStatus.created
    elif roll < 0.80:
        status = ShipmentStatus.dispatched
    else:
        status = ShipmentStatus.in_transit

    # ETA and SLA
    eta_hours = random.uniform(6, 96)
    sla_buffer = random.uniform(1, 18)

    # Occasionally make things tight
    if random.random() < 0.25:
        sla_buffer = random.uniform(0.5, 2.0)

    ship = Shipment(
        shipment_id=_uid("SH"),
        origin=route.origin,
        destination=route.destination,
        carrier=carrier.carrier_id,
        route_id=route.route_id,
        eta=now + timedelta(hours=eta_hours),
        sla_deadline=now + timedelta(hours=eta_hours + sla_buffer),
        status=status,
        is_active=True,
        delivered_at=None,
        origin_point=_point(route.origin),
        destination_point=_point(route.destination),
        current_location=_point(route.origin),
    )
    db.add(ship)
    carrier.total_shipments += 1
    return ship


def _spawn_replacements(db: Session, deficit: int):
    """Create new shipments to fill the gap left by pruned ones."""
    if deficit <= 0:
        return

    to_spawn = min(deficit, MAX_SPAWN_PER_TICK)

    carriers = db.query(CarrierPerformance).all()
    routes = db.query(Route).all()
    if not carriers or not routes:
        return

    for _ in range(to_spawn):
        ship = _spawn_shipment(db, carriers, routes)
        log.debug("📦 Spawned replacement %s  %s → %s  carrier=%s  status=%s",
                 ship.shipment_id, ship.origin, ship.destination,
                 ship.carrier, ship.status.value)


def _inject_disruptions(db: Session):
    """Randomly delay or regress some active shipments to keep things interesting."""
    active = (
        db.query(Shipment)
        .filter(
            Shipment.is_active.is_(True),
            Shipment.status.in_([ShipmentStatus.in_transit, ShipmentStatus.dispatched]),
        )
        .all()
    )
    if not active:
        return

    for s in active:
        roll = random.random()
        if roll < 0.06:
            # Random delay
            s.status = ShipmentStatus.delayed
            drift = timedelta(hours=random.uniform(1, 8))
            s.eta = s.eta + drift
            carrier = db.query(CarrierPerformance).filter_by(carrier_id=s.carrier).first()
            if carrier:
                carrier.total_delays += 1
            log.debug("⚠️  LIFECYCLE DELAY  %s  %s → %s  drift=+%.1fh",
                        s.shipment_id, s.origin, s.destination,
                        drift.total_seconds() / 3600)


# ── Background thread ────────────────────────────────────────────────────────

class LifecycleManager:
    """Background thread that runs the shipment lifecycle queue."""

    def __init__(self, tick_interval: float = TICK_INTERVAL,
                 target_active: int = TARGET_ACTIVE):
        self.tick_interval = tick_interval
        self.target_active = target_active
        self._running = False
        self._thread: threading.Thread | None = None
        self._tick_count = 0

    @property
    def running(self) -> bool:
        return self._running

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("✅ Lifecycle manager started  tick=%.0fs  target_active=%d",
                 self.tick_interval, self.target_active)

    def stop(self):
        self._running = False
        log.info("Lifecycle manager stopped after %d ticks", self._tick_count)

    def _loop(self):
        # Small initial delay so seed data settles
        time.sleep(5.0)
        while self._running:
            db = SessionLocal()
            try:
                self._tick(db)
                db.commit()
                self._tick_count += 1
            except Exception as exc:
                db.rollback()
                log.error("Lifecycle tick error: %s", exc, exc_info=True)
            finally:
                db.close()
            time.sleep(self.tick_interval)

    def _tick(self, db: Session):
        # 1. Stamp terminal shipments
        _stamp_terminal_shipments(db)

        # 2. Prune expired ones
        pruned = _prune_expired(db)

        # 3. Count active and spawn replacements
        active = _count_active(db)
        deficit = self.target_active - active
        if deficit > 0:
            _spawn_replacements(db, deficit)

        # 4. Inject random disruptions
        _inject_disruptions(db)

        if self._tick_count % 12 == 0:  # log summary every ~2 min
            log.info("📊 Lifecycle #%d — active=%d  pruned=%d  deficit=%d",
                     self._tick_count, active, pruned, deficit)


# ── Module-level singleton ───────────────────────────────────────────────────
lifecycle_manager = LifecycleManager()
