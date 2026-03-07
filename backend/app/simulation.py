"""
SimPy-based logistics simulation engine.

Runs in a background thread and continuously generates operational events:
  • Shipment lifecycle transitions
  • Warehouse load fluctuations
  • Carrier reliability changes
  • Route traffic / weather updates
  • Random disruptions (delays, congestion, pickup failures, ETA drift)
"""

import json
import random
import threading
import time
from datetime import datetime, timedelta

import simpy
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Shipment,
    WarehouseState,
    CarrierPerformance,
    Route,
    SimulationEvent,
    ShipmentStatus,
    TrafficLevel,
    EventType,
)


class LogisticsSimulation:
    """Core simulation that ticks through logistics events using SimPy."""

    def __init__(self, tick_interval: float = 2.0, sim_speed: float = 10.0):
        self.env = simpy.Environment()
        self.tick_interval = tick_interval   # real-seconds between ticks
        self.sim_speed = sim_speed           # sim-minutes per real-second
        self._running = False
        self._thread: threading.Thread | None = None
        self._events_generated = 0

    # ── public control ───────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    @property
    def sim_time(self) -> float:
        return self.env.now

    @property
    def total_events(self) -> int:
        return self._events_generated

    def start(self):
        if self._running:
            return
        self._running = True
        self.env = simpy.Environment()
        self.env.process(self._main_loop())
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ── internal loop ────────────────────────────────────────────────────

    def _run_thread(self):
        while self._running:
            self.env.step()
            time.sleep(self.tick_interval)

    def _main_loop(self):
        while True:
            db = SessionLocal()
            try:
                self._tick(db)
                db.commit()
            except Exception as exc:
                db.rollback()
                print(f"[sim] tick error: {exc}")
            finally:
                db.close()
            yield self.env.timeout(self.sim_speed)

    # ── single tick ──────────────────────────────────────────────────────

    def _tick(self, db: Session):
        self._advance_shipments(db)
        self._fluctuate_warehouses(db)
        self._fluctuate_routes(db)
        self._random_disruption(db)

    # ── shipment lifecycle ───────────────────────────────────────────────

    def _advance_shipments(self, db: Session):
        shipments: list[Shipment] = db.query(Shipment).filter(
            Shipment.status.notin_([ShipmentStatus.delivered, ShipmentStatus.failed])
        ).all()

        for s in shipments:
            roll = random.random()
            carrier = db.query(CarrierPerformance).filter_by(carrier_id=s.carrier).first()

            if s.status == ShipmentStatus.created and roll < 0.4:
                s.status = ShipmentStatus.dispatched
                self._emit(db, EventType.shipment_dispatched, s.shipment_id, {
                    "origin": s.origin, "destination": s.destination, "carrier": s.carrier,
                })

            elif s.status == ShipmentStatus.dispatched and roll < 0.35:
                s.status = ShipmentStatus.in_transit
                self._emit(db, EventType.shipment_dispatched, s.shipment_id, {
                    "status": "in_transit",
                })

            elif s.status == ShipmentStatus.in_transit:
                if carrier and roll < carrier.delay_probability * 0.5:
                    s.status = ShipmentStatus.delayed
                    s.eta = s.eta + timedelta(hours=random.uniform(1, 8))
                    if carrier:
                        carrier.total_delays += 1
                    self._emit(db, EventType.shipment_delayed, s.shipment_id, {
                        "new_eta": s.eta.isoformat(),
                        "carrier": s.carrier,
                    })
                elif roll < 0.25:
                    s.status = ShipmentStatus.delivered
                    self._emit(db, EventType.shipment_delivered, s.shipment_id, {
                        "destination": s.destination,
                    })

            elif s.status == ShipmentStatus.delayed and roll < 0.3:
                s.status = ShipmentStatus.in_transit
                self._emit(db, EventType.shipment_dispatched, s.shipment_id, {
                    "status": "resumed_transit",
                })

    # ── warehouse fluctuations ───────────────────────────────────────────

    def _fluctuate_warehouses(self, db: Session):
        warehouses: list[WarehouseState] = db.query(WarehouseState).all()
        for wh in warehouses:
            delta_load = random.randint(-20, 25)
            wh.current_load = max(0, min(wh.capacity, wh.current_load + delta_load))
            wh.queue_length = max(0, wh.queue_length + random.randint(-3, 4))
            wh.congestion_score = round(wh.current_load / max(wh.capacity, 1), 3)

            if wh.congestion_score > 0.85:
                self._emit(db, EventType.warehouse_congestion, wh.warehouse_id, {
                    "congestion_score": wh.congestion_score,
                    "current_load": wh.current_load,
                    "capacity": wh.capacity,
                })
            else:
                self._emit(db, EventType.warehouse_load_update, wh.warehouse_id, {
                    "congestion_score": wh.congestion_score,
                    "current_load": wh.current_load,
                })

    # ── route fluctuations ───────────────────────────────────────────────

    def _fluctuate_routes(self, db: Session):
        routes: list[Route] = db.query(Route).all()
        for rt in routes:
            if random.random() < 0.25:
                rt.traffic_level = random.choice(list(TrafficLevel))
                rt.weather_factor = round(max(0.5, min(2.0, rt.weather_factor + random.uniform(-0.2, 0.2))), 2)
                self._emit(db, EventType.route_traffic_update, rt.route_id, {
                    "traffic_level": rt.traffic_level.value,
                    "weather_factor": rt.weather_factor,
                })

    # ── random disruptions ───────────────────────────────────────────────

    def _random_disruption(self, db: Session):
        """Roll for a random disruption each tick."""
        roll = random.random()

        if roll < 0.08:
            # ETA drift on a random in-transit shipment
            ship = (
                db.query(Shipment)
                .filter_by(status=ShipmentStatus.in_transit)
                .order_by(Shipment.id)
                .first()
            )
            if ship:
                drift = timedelta(hours=random.uniform(1, 6))
                ship.eta = ship.eta + drift
                self._emit(db, EventType.eta_drift, ship.shipment_id, {
                    "drift_hours": round(drift.total_seconds() / 3600, 2),
                    "new_eta": ship.eta.isoformat(),
                })

        elif roll < 0.14:
            # Pickup failure
            carrier = db.query(CarrierPerformance).order_by(CarrierPerformance.pickup_success_rate).first()
            if carrier:
                carrier.pickup_success_rate = round(max(0.5, carrier.pickup_success_rate - 0.02), 3)
                self._emit(db, EventType.pickup_failure, carrier.carrier_id, {
                    "pickup_success_rate": carrier.pickup_success_rate,
                })

        elif roll < 0.18:
            # Carrier delay event
            carrier = db.query(CarrierPerformance).order_by(CarrierPerformance.reliability_score).first()
            if carrier:
                carrier.reliability_score = round(max(0.3, carrier.reliability_score - 0.03), 3)
                carrier.delay_probability = round(min(0.6, carrier.delay_probability + 0.02), 3)
                self._emit(db, EventType.carrier_delay_event, carrier.carrier_id, {
                    "reliability_score": carrier.reliability_score,
                    "delay_probability": carrier.delay_probability,
                })

    # ── event helper ─────────────────────────────────────────────────────

    def _emit(self, db: Session, event_type: EventType, entity_id: str, payload: dict):
        ev = SimulationEvent(
            event_type=event_type,
            entity_id=entity_id,
            payload=json.dumps(payload),
            sim_time=self.env.now,
        )
        db.add(ev)
        self._events_generated += 1


# ── Module-level singleton ───────────────────────────────────────────────────
simulation = LogisticsSimulation()
