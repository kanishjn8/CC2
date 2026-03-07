"""Seed the database with initial warehouses, carriers, routes, and shipments."""

import logging
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, LineString

from app.models import (
    Shipment,
    WarehouseState,
    CarrierPerformance,
    Route,
    ShipmentStatus,
    TrafficLevel,
)

log = logging.getLogger("cc2.seed")

# ---------------------------------------------------------------------------
# Global city network — covers Asia, Europe, Americas, Middle East, Africa,
# Oceania so shipments are not limited to India.
# City name → (longitude, latitude) — WGS84
# ---------------------------------------------------------------------------
CITY_COORDS: dict[str, tuple[float, float]] = {
    # ── South Asia ──────────────────────────────────────────────────────
    "Mumbai":       (72.8777,  19.0760),
    "Delhi":        (77.1025,  28.7041),
    "Bangalore":    (77.5946,  12.9716),
    "Chennai":      (80.2707,  13.0827),
    "Hyderabad":    (78.4867,  17.3850),
    "Kolkata":      (88.3639,  22.5726),
    "Ahmedabad":    (72.5714,  23.0225),
    "Karachi":      (67.0099,  24.8607),
    "Dhaka":        (90.4125,  23.8103),
    "Colombo":      (79.8612,   6.9271),
    # ── East Asia ───────────────────────────────────────────────────────
    "Shanghai":    (121.4737,  31.2304),
    "Beijing":     (116.4074,  39.9042),
    "Shenzhen":    (114.0579,  22.5431),
    "Hong Kong":   (114.1694,  22.3193),
    "Tokyo":       (139.6917,  35.6895),
    "Osaka":       (135.5022,  34.6937),
    "Seoul":       (126.9780,  37.5665),
    "Taipei":      (121.5654,  25.0330),
    "Singapore":   (103.8198,   1.3521),
    "Kuala Lumpur":(101.6869,   3.1390),
    "Bangkok":     (100.5018,  13.7563),
    "Jakarta":     (106.8650,  -6.2088),
    # ── Middle East ─────────────────────────────────────────────────────
    "Dubai":        (55.2708,  25.2048),
    "Abu Dhabi":    (54.3773,  24.4539),
    "Riyadh":       (46.7219,  24.6877),
    "Doha":         (51.5310,  25.2854),
    "Kuwait City":  (47.9783,  29.3759),
    "Muscat":       (58.5922,  23.5880),
    # ── Europe ──────────────────────────────────────────────────────────
    "London":       (-0.1276,  51.5074),
    "Amsterdam":    ( 4.9041,  52.3676),
    "Frankfurt":    ( 8.6821,  50.1109),
    "Paris":        ( 2.3522,  48.8566),
    "Rotterdam":    ( 4.4777,  51.9244),
    "Hamburg":      ( 9.9937,  53.5511),
    "Antwerp":      ( 4.4025,  51.2194),
    "Barcelona":    ( 2.1734,  41.3851),
    "Milan":        ( 9.1900,  45.4654),
    "Warsaw":       (21.0122,  52.2297),
    "Istanbul":     (28.9784,  41.0082),
    # ── Africa ──────────────────────────────────────────────────────────
    "Nairobi":      (36.8219,  -1.2921),
    "Lagos":         (3.3792,   6.5244),
    "Cairo":        (31.2357,  30.0444),
    "Johannesburg": (28.0473, -26.2041),
    "Casablanca":   (-7.5898,  33.5731),
    "Addis Ababa":  (38.7578,   9.0249),
    # ── Americas ────────────────────────────────────────────────────────
    "New York":    (-74.0060,  40.7128),
    "Los Angeles": (-118.2437, 34.0522),
    "Chicago":     (-87.6298,  41.8781),
    "Miami":       (-80.1918,  25.7617),
    "Houston":     (-95.3698,  29.7604),
    "Toronto":     (-79.3832,  43.6532),
    "Mexico City": (-99.1332,  19.4326),
    "São Paulo":   (-46.6333, -23.5505),
    "Buenos Aires":(-58.3816, -34.6037),
    "Bogotá":      (-74.0721,   4.7110),
    # ── Oceania ─────────────────────────────────────────────────────────
    "Sydney":      (151.2093, -33.8688),
    "Melbourne":   (144.9631, -37.8136),
    "Auckland":    (174.7633, -36.8485),
}

# Warehouse hubs — spread across every region
WAREHOUSE_CITIES = [
    "Mumbai", "Dubai", "Singapore", "Shanghai", "Frankfurt",
    "London", "New York", "São Paulo", "Nairobi", "Sydney",
    "Tokyo", "Istanbul", "Los Angeles", "Johannesburg", "Bangkok",
]

CITIES = list(CITY_COORDS.keys())

CARRIER_NAMES = [
    "SwiftLogistics", "CargoExpress", "TransFast", "ReliFreight",
    "QuickShip", "PrimeHaul", "MetroCarriers", "AlphaTransport",
    "GlobalFreight", "OceanLink", "AirBridge", "SilkRoute",
]


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _point(city: str):
    """Return a WKB POINT geometry for a city name (SRID 4326)."""
    lon, lat = CITY_COORDS[city]
    return from_shape(Point(lon, lat), srid=4326)


def _linestring(origin_city: str, dest_city: str):
    """Return a WKB LINESTRING from origin to destination (SRID 4326)."""
    o_lon, o_lat = CITY_COORDS[origin_city]
    d_lon, d_lat = CITY_COORDS[dest_city]
    return from_shape(LineString([(o_lon, o_lat), (d_lon, d_lat)]), srid=4326)


def seed_warehouses(db: Session, count: int = 10) -> list[WarehouseState]:
    warehouses = []
    # Prefer the designated global hubs, then fill from remaining cities
    hub_pool = [c for c in WAREHOUSE_CITIES if c in CITY_COORDS]
    extra_pool = [c for c in CITIES if c not in hub_pool]
    locations = (hub_pool + extra_pool)[:count]
    random.shuffle(locations)
    locations = locations[:count]

    log.info("Seeding %d warehouses across global hubs…", count)
    for i, loc in enumerate(locations):
        cap = random.randint(300, 1500)

        # Diversity: some warehouses are critically congested, some near-empty
        if i < 2:
            # Near-full / critically congested
            load = random.randint(int(cap * 0.88), cap)
            queue = random.randint(15, 40)
        elif i < 4:
            # Moderately congested
            load = random.randint(int(cap * 0.65), int(cap * 0.85))
            queue = random.randint(8, 20)
        elif i < count - 2:
            # Normal
            load = random.randint(int(cap * 0.20), int(cap * 0.60))
            queue = random.randint(0, 10)
        else:
            # Nearly empty
            load = random.randint(0, int(cap * 0.15))
            queue = random.randint(0, 2)

        wh = WarehouseState(
            warehouse_id=_uid("WH"),
            location=loc,
            capacity=cap,
            current_load=load,
            queue_length=queue,
            congestion_score=round(load / cap, 3),
            geom=_point(loc),
        )
        db.add(wh)
        warehouses.append(wh)
        log.debug("  Warehouse %s @ %s  cap=%d load=%d cong=%.2f queue=%d",
                  wh.warehouse_id, loc, cap, load, wh.congestion_score, queue)
    db.flush()
    log.info("  ✓ %d warehouses created", len(warehouses))
    return warehouses


def seed_carriers(db: Session, count: int = 12) -> list[CarrierPerformance]:
    carriers = []
    names = CARRIER_NAMES[:count]
    log.info("Seeding %d carriers (with diverse reliability profiles)…", count)
    for i, name in enumerate(names):
        # Diversity: some carriers are very unreliable, some excellent
        if i < 2:
            # Very unreliable carriers
            rel = round(random.uniform(0.25, 0.45), 3)
            delay_prob = round(random.uniform(0.40, 0.65), 3)
            pickup = round(random.uniform(0.55, 0.75), 3)
            total_sh = random.randint(40, 100)
            total_dl = int(total_sh * random.uniform(0.30, 0.50))
        elif i < 4:
            # Below average
            rel = round(random.uniform(0.45, 0.60), 3)
            delay_prob = round(random.uniform(0.25, 0.40), 3)
            pickup = round(random.uniform(0.70, 0.85), 3)
            total_sh = random.randint(30, 80)
            total_dl = int(total_sh * random.uniform(0.20, 0.35))
        elif i < count - 2:
            # Average / good
            rel = round(random.uniform(0.70, 0.90), 3)
            delay_prob = round(random.uniform(0.05, 0.20), 3)
            pickup = round(random.uniform(0.85, 0.96), 3)
            total_sh = random.randint(20, 60)
            total_dl = int(total_sh * random.uniform(0.05, 0.15))
        else:
            # Excellent
            rel = round(random.uniform(0.92, 0.99), 3)
            delay_prob = round(random.uniform(0.01, 0.05), 3)
            pickup = round(random.uniform(0.96, 1.00), 3)
            total_sh = random.randint(50, 120)
            total_dl = int(total_sh * random.uniform(0.01, 0.05))

        carrier = CarrierPerformance(
            carrier_id=_uid("CR"),
            name=name,
            reliability_score=rel,
            delay_probability=delay_prob,
            pickup_success_rate=pickup,
            total_shipments=total_sh,
            total_delays=total_dl,
        )
        db.add(carrier)
        carriers.append(carrier)
        log.debug("  Carrier %s (%s)  rel=%.3f delay_p=%.3f pickup=%.3f ships=%d delays=%d",
                  carrier.carrier_id, name, rel, delay_prob, pickup, total_sh, total_dl)
    db.flush()
    log.info("  ✓ %d carriers created", len(carriers))
    return carriers


def seed_routes(db: Session, count: int = 30) -> list[Route]:
    routes = []
    log.info("Seeding %d global routes (with diverse traffic & weather)…", count)
    import math

    for i in range(count):
        o, d = random.sample(CITIES, 2)
        o_lon, o_lat = CITY_COORDS[o]
        d_lon, d_lat = CITY_COORDS[d]
        # Haversine-approximate distance (km)
        dlat = math.radians(d_lat - o_lat)
        dlon = math.radians(d_lon - o_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(o_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
        dist_km = round(6371 * 2 * math.asin(math.sqrt(a)), 1)

        # Diversity: some routes have severe traffic + bad weather
        if i < 3:
            # Nightmare routes — severe traffic, terrible weather
            traffic = TrafficLevel.severe
            weather = round(random.uniform(1.5, 2.0), 2)
        elif i < 6:
            # Bad routes — high traffic, moderate-bad weather
            traffic = TrafficLevel.high
            weather = round(random.uniform(1.3, 1.6), 2)
        elif i < count - 4:
            # Normal routes
            traffic = random.choice(list(TrafficLevel))
            weather = round(random.uniform(0.8, 1.3), 2)
        else:
            # Easy routes — low traffic, good weather
            traffic = TrafficLevel.low
            weather = round(random.uniform(0.8, 1.0), 2)

        route = Route(
            route_id=_uid("RT"),
            origin=o,
            destination=d,
            distance=dist_km,
            traffic_level=traffic,
            weather_factor=weather,
            path=_linestring(o, d),
        )
        db.add(route)
        routes.append(route)
        log.debug("  Route %s: %s → %s  %.0f km  traffic=%s weather=%.2f",
                  route.route_id, o, d, dist_km, traffic.value, weather)
    db.flush()
    log.info("  ✓ %d routes created", len(routes))
    return routes


def seed_shipments(
    db: Session,
    carriers: list[CarrierPerformance],
    routes: list[Route],
    count: int = 40,
) -> list[Shipment]:
    shipments = []
    now = datetime.utcnow()
    log.info("Seeding %d shipments (all statuses, diverse SLA scenarios)…", count)

    # Ensure unreliable carriers get assigned more shipments to trigger agent
    bad_carriers = [c for c in carriers if c.reliability_score < 0.5]
    ok_carriers = [c for c in carriers if c.reliability_score >= 0.5]

    # Ensure some routes are bad to trigger risk
    bad_routes = [r for r in routes if r.traffic_level in (TrafficLevel.high, TrafficLevel.severe)]
    all_routes = routes

    for i in range(count):
        # ── Status distribution ──────────────────────────────────────
        # 25% created, 20% dispatched, 25% in_transit, 8% delayed,
        # 5% failed, 7% at_warehouse, 5% out_for_delivery, 5% delivered
        r = random.random()
        if r < 0.25:
            status = ShipmentStatus.created
        elif r < 0.45:
            status = ShipmentStatus.dispatched
        elif r < 0.70:
            status = ShipmentStatus.in_transit
        elif r < 0.78:
            status = ShipmentStatus.delayed
        elif r < 0.83:
            status = ShipmentStatus.failed
        elif r < 0.90:
            status = ShipmentStatus.at_warehouse
        elif r < 0.95:
            status = ShipmentStatus.out_for_delivery
        else:
            status = ShipmentStatus.delivered

        # ── Carrier selection — bias some shipments to bad carriers ────
        if i < 6 and bad_carriers:
            carrier = random.choice(bad_carriers)
        else:
            carrier = random.choice(carriers)

        # ── Route selection — bias some shipments to bad routes ────
        if i < 8 and bad_routes:
            route = random.choice(bad_routes)
        else:
            route = random.choice(all_routes)

        # ── ETA / SLA diversity ──────────────────────────────────────
        if i < 5:
            # SLA already breached — ETA past SLA deadline
            eta_hours = random.uniform(24, 96)
            sla_buffer = random.uniform(-12, -2)  # negative = SLA in the past relative to ETA
        elif i < 10:
            # Very tight SLA — under 2 hours buffer
            eta_hours = random.uniform(6, 48)
            sla_buffer = random.uniform(0.5, 2.0)
        elif i < 15:
            # Moderate SLA pressure
            eta_hours = random.uniform(8, 72)
            sla_buffer = random.uniform(2, 6)
        else:
            # Normal / comfortable
            eta_hours = random.uniform(6, 120)
            sla_buffer = random.uniform(4, 24)

        # For delayed / failed shipments, set ETA in the past or very soon
        if status == ShipmentStatus.delayed:
            eta_hours = random.uniform(-6, 3)  # already late or almost late
            sla_buffer = random.uniform(-8, -1)
        elif status == ShipmentStatus.failed:
            eta_hours = random.uniform(-24, -6)  # definitely past
            sla_buffer = random.uniform(-24, -6)
        elif status == ShipmentStatus.delivered:
            eta_hours = random.uniform(-48, -2)  # completed in the past
            sla_buffer = random.uniform(1, 12)

        ship = Shipment(
            shipment_id=_uid("SH"),
            origin=route.origin,
            destination=route.destination,
            carrier=carrier.carrier_id,
            route_id=route.route_id,
            eta=now + timedelta(hours=eta_hours),
            sla_deadline=now + timedelta(hours=eta_hours + sla_buffer),
            status=status,
            origin_point=_point(route.origin),
            destination_point=_point(route.destination),
            current_location=_point(route.origin),
        )
        db.add(ship)
        shipments.append(ship)
        carrier.total_shipments += 1
        if status in (ShipmentStatus.delayed, ShipmentStatus.failed):
            carrier.total_delays += 1
        log.debug(
            "  Shipment %s: %s → %s  carrier=%s  status=%s  eta=+%.1fh  sla_buf=%.1fh",
            ship.shipment_id, route.origin, route.destination,
            carrier.name, status.value, eta_hours, sla_buffer,
        )
    db.flush()
    log.info("  ✓ %d shipments created", len(shipments))
    return shipments


def seed_all(db: Session, *, warehouses: int = 10, carriers: int = 12, routes: int = 30, shipments: int = 40):
    """Seed all tables. Skips if data already exists."""
    from app.models import WarehouseState as WS
    if db.query(WS).first() is not None:
        log.info("[seed] Data already exists — skipping seed.")
        return

    log.info("[seed] Starting global seed…")
    whs = seed_warehouses(db, warehouses)
    crs = seed_carriers(db, carriers)
    rts = seed_routes(db, routes)
    shs = seed_shipments(db, crs, rts, shipments)
    db.commit()
    log.info(
        "[seed] ✅ Complete — %d warehouses | %d carriers | %d routes | %d shipments",
        len(whs), len(crs), len(rts), len(shs),
    )
