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
    for loc in locations:
        cap = random.randint(300, 1500)
        load = random.randint(0, int(cap * 0.65))
        wh = WarehouseState(
            warehouse_id=_uid("WH"),
            location=loc,
            capacity=cap,
            current_load=load,
            queue_length=random.randint(0, 20),
            congestion_score=round(load / cap, 3),
            geom=_point(loc),
        )
        db.add(wh)
        warehouses.append(wh)
        log.debug("  Warehouse %s @ %s  cap=%d load=%d", wh.warehouse_id, loc, cap, load)
    db.flush()
    log.info("  ✓ %d warehouses created", len(warehouses))
    return warehouses


def seed_carriers(db: Session, count: int = 12) -> list[CarrierPerformance]:
    carriers = []
    names = CARRIER_NAMES[:count]
    log.info("Seeding %d carriers…", count)
    for name in names:
        rel = round(random.uniform(0.6, 1.0), 3)
        carrier = CarrierPerformance(
            carrier_id=_uid("CR"),
            name=name,
            reliability_score=rel,
            delay_probability=round(1.0 - rel + random.uniform(0, 0.1), 3),
            pickup_success_rate=round(random.uniform(0.80, 0.99), 3),
            total_shipments=0,
            total_delays=0,
        )
        db.add(carrier)
        carriers.append(carrier)
        log.debug("  Carrier %s (%s)  reliability=%.3f", carrier.carrier_id, name, rel)
    db.flush()
    log.info("  ✓ %d carriers created", len(carriers))
    return carriers


def seed_routes(db: Session, count: int = 30) -> list[Route]:
    routes = []
    log.info("Seeding %d global routes…", count)
    for _ in range(count):
        o, d = random.sample(CITIES, 2)
        o_lon, o_lat = CITY_COORDS[o]
        d_lon, d_lat = CITY_COORDS[d]
        # Haversine-approximate distance (km) for realistic values
        import math
        dlat = math.radians(d_lat - o_lat)
        dlon = math.radians(d_lon - o_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(o_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
        dist_km = round(6371 * 2 * math.asin(math.sqrt(a)), 1)
        route = Route(
            route_id=_uid("RT"),
            origin=o,
            destination=d,
            distance=dist_km,
            traffic_level=random.choice(list(TrafficLevel)),
            weather_factor=round(random.uniform(0.8, 1.5), 2),
            path=_linestring(o, d),
        )
        db.add(route)
        routes.append(route)
        log.debug("  Route %s: %s → %s  %.0f km", route.route_id, o, d, dist_km)
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
    log.info("Seeding %d shipments across global routes…", count)
    for _ in range(count):
        route = random.choice(routes)
        carrier = random.choice(carriers)
        eta_hours = random.uniform(6, 120)   # up to 5 days for long-haul
        sla_buffer = random.uniform(2, 24)
        status = random.choice(
            [ShipmentStatus.created, ShipmentStatus.dispatched, ShipmentStatus.in_transit]
        )
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
        log.debug(
            "  Shipment %s: %s → %s  carrier=%s  status=%s  eta=+%.1fh",
            ship.shipment_id, route.origin, route.destination,
            carrier.name, status.value, eta_hours,
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
