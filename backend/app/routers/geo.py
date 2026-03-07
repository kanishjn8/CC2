"""GeoJSON endpoints for map visualization and spatial queries."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_AsGeoJSON, ST_DWithin, ST_Buffer, ST_Intersects

from app.database import get_db
from app.models import (
    Shipment,
    WarehouseState,
    Route,
    ShipmentStatus,
)
from app.schemas import GeoJSONFeature, GeoJSONFeatureCollection

import json

router = APIRouter(prefix="/geo", tags=["GeoJSON / Spatial"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _geojson_or_none(geom_col):
    """Convert a WKB geometry column value to a GeoJSON dict (or None)."""
    if geom_col is None:
        return None
    try:
        shape = to_shape(geom_col)
        return json.loads(json.dumps({
            "type": shape.geom_type,
            "coordinates": list(shape.coords) if shape.geom_type == "Point"
            else [list(c) for c in shape.coords],
        }))
    except Exception:
        return None


def _point_geojson(geom_col):
    """Convert a WKB POINT to a GeoJSON dict."""
    if geom_col is None:
        return None
    try:
        shape = to_shape(geom_col)
        return {"type": "Point", "coordinates": [shape.x, shape.y]}
    except Exception:
        return None


def _linestring_geojson(geom_col):
    """Convert a WKB LINESTRING to a GeoJSON dict."""
    if geom_col is None:
        return None
    try:
        shape = to_shape(geom_col)
        return {"type": "LineString", "coordinates": [list(c) for c in shape.coords]}
    except Exception:
        return None


# ── GeoJSON Feature Collections (map-ready) ─────────────────────────────────

@router.get("/shipments", response_model=GeoJSONFeatureCollection)
def shipments_geojson(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """All shipments as a GeoJSON FeatureCollection (current_location)."""
    q = db.query(Shipment)
    if status:
        q = q.filter(Shipment.status == status)
    shipments = q.all()

    features = []
    for s in shipments:
        features.append(GeoJSONFeature(
            geometry=_point_geojson(s.current_location),
            properties={
                "shipment_id": s.shipment_id,
                "origin": s.origin,
                "destination": s.destination,
                "carrier": s.carrier,
                "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                "eta": s.eta.isoformat() if s.eta else None,
            },
        ))
    return GeoJSONFeatureCollection(features=features)


@router.get("/warehouses", response_model=GeoJSONFeatureCollection)
def warehouses_geojson(db: Session = Depends(get_db)):
    """All warehouses as a GeoJSON FeatureCollection (hub markers)."""
    warehouses = db.query(WarehouseState).all()

    features = []
    for wh in warehouses:
        features.append(GeoJSONFeature(
            geometry=_point_geojson(wh.geom),
            properties={
                "warehouse_id": wh.warehouse_id,
                "location": wh.location,
                "capacity": wh.capacity,
                "current_load": wh.current_load,
                "congestion_score": wh.congestion_score,
                "queue_length": wh.queue_length,
            },
        ))
    return GeoJSONFeatureCollection(features=features)


@router.get("/routes", response_model=GeoJSONFeatureCollection)
def routes_geojson(db: Session = Depends(get_db)):
    """All routes as a GeoJSON FeatureCollection (network paths)."""
    routes = db.query(Route).all()

    features = []
    for rt in routes:
        features.append(GeoJSONFeature(
            geometry=_linestring_geojson(rt.path),
            properties={
                "route_id": rt.route_id,
                "origin": rt.origin,
                "destination": rt.destination,
                "distance": rt.distance,
                "traffic_level": rt.traffic_level.value if hasattr(rt.traffic_level, "value") else str(rt.traffic_level),
                "weather_factor": rt.weather_factor,
            },
        ))
    return GeoJSONFeatureCollection(features=features)


# ── Spatial Queries ──────────────────────────────────────────────────────────

@router.get("/shipments/near-warehouse/{warehouse_id}")
def shipments_near_warehouse(
    warehouse_id: str,
    radius_km: float = Query(50.0, ge=1, le=500, description="Search radius in km"),
    db: Session = Depends(get_db),
):
    """Find shipments within a radius of a warehouse (for congestion analysis).

    Uses ST_DWithin with geography cast for accurate distance in metres.
    """
    wh = db.query(WarehouseState).filter_by(warehouse_id=warehouse_id).first()
    if not wh or wh.geom is None:
        return {"warehouse_id": warehouse_id, "radius_km": radius_km, "shipments": []}

    radius_m = radius_km * 1000

    nearby = (
        db.query(Shipment)
        .filter(
            Shipment.current_location.isnot(None),
            sa_func.ST_DWithin(
                sa_func.cast(Shipment.current_location, sa_func.Geography),
                sa_func.cast(wh.geom, sa_func.Geography),
                radius_m,
            ),
        )
        .all()
    )

    return {
        "warehouse_id": warehouse_id,
        "warehouse_location": wh.location,
        "radius_km": radius_km,
        "count": len(nearby),
        "shipments": [
            {
                "shipment_id": s.shipment_id,
                "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                "carrier": s.carrier,
                "location": _point_geojson(s.current_location),
            }
            for s in nearby
        ],
    }


@router.get("/shipments/on-route/{route_id}")
def shipments_on_route(
    route_id: str,
    buffer_km: float = Query(25.0, ge=1, le=200, description="Buffer around route in km"),
    db: Session = Depends(get_db),
):
    """Find shipments traveling along (near) a route — useful for disruption detection.

    Buffers the route LINESTRING and checks which shipment locations intersect.
    """
    route = db.query(Route).filter_by(route_id=route_id).first()
    if not route or route.path is None:
        return {"route_id": route_id, "buffer_km": buffer_km, "shipments": []}

    # ST_Buffer on geography gives metres
    buffer_m = buffer_km * 1000

    on_route = (
        db.query(Shipment)
        .filter(
            Shipment.current_location.isnot(None),
            sa_func.ST_DWithin(
                sa_func.cast(Shipment.current_location, sa_func.Geography),
                sa_func.cast(route.path, sa_func.Geography),
                buffer_m,
            ),
        )
        .all()
    )

    return {
        "route_id": route_id,
        "origin": route.origin,
        "destination": route.destination,
        "buffer_km": buffer_km,
        "traffic_level": route.traffic_level.value if hasattr(route.traffic_level, "value") else str(route.traffic_level),
        "count": len(on_route),
        "shipments": [
            {
                "shipment_id": s.shipment_id,
                "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                "carrier": s.carrier,
                "location": _point_geojson(s.current_location),
            }
            for s in on_route
        ],
    }


@router.get("/shipments/within-radius")
def shipments_within_radius(
    lon: float = Query(..., ge=-180, le=180, description="Longitude (WGS84)"),
    lat: float = Query(..., ge=-90, le=90, description="Latitude (WGS84)"),
    radius_km: float = Query(50.0, ge=1, le=500, description="Search radius in km"),
    db: Session = Depends(get_db),
):
    """Find shipments within a geographic radius of a point (e.g. event location)."""
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    center = from_shape(Point(lon, lat), srid=4326)
    radius_m = radius_km * 1000

    nearby = (
        db.query(Shipment)
        .filter(
            Shipment.current_location.isnot(None),
            sa_func.ST_DWithin(
                sa_func.cast(Shipment.current_location, sa_func.Geography),
                sa_func.cast(center, sa_func.Geography),
                radius_m,
            ),
        )
        .all()
    )

    return {
        "center": {"lon": lon, "lat": lat},
        "radius_km": radius_km,
        "count": len(nearby),
        "shipments": [
            {
                "shipment_id": s.shipment_id,
                "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                "carrier": s.carrier,
                "origin": s.origin,
                "destination": s.destination,
                "location": _point_geojson(s.current_location),
            }
            for s in nearby
        ],
    }
