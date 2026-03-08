"""
Action execution — applies agent decisions to the simulation state.

Each function mutates the database to reflect the intervention.
The caller is responsible for committing the transaction.
"""

import json
import logging
import random
import smtplib
import time
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from app.models import (
    CarrierPerformance,
    Route,
    Shipment,
    ShipmentStatus,
    TrafficLevel,
    WarehouseState,
)
from app import config as _cfg

log = logging.getLogger("cc2.actions")

# Global email cooldown tracker — timestamp of last email sent (monotonic)
_email_last_sent_at: float = 0.0


def _linestring_geojson(geom_col) -> dict | None:
    """Convert a WKB LINESTRING to a GeoJSON dict."""
    if geom_col is None:
        return None
    try:
        shape = to_shape(geom_col)
        return {"type": "LineString", "coordinates": [list(c) for c in shape.coords]}
    except Exception:
        return None


def reroute_shipment(db: Session, shipment_id: str) -> dict:
    """Find a lower-traffic route and reassign the shipment."""
    shipment = db.query(Shipment).filter_by(shipment_id=shipment_id).first()
    if not shipment:
        return {"success": False, "reason": "Shipment not found"}

    # Capture old route geometry before switching
    old_route = db.query(Route).filter_by(route_id=shipment.route_id).first() if shipment.route_id else None

    best_route = (
        db.query(Route)
        .filter(Route.route_id != shipment.route_id)
        .filter(Route.traffic_level.in_([TrafficLevel.low, TrafficLevel.moderate]))
        .order_by(Route.weather_factor.asc())
        .first()
    )
    if not best_route:
        return {"success": False, "reason": "No better route available"}

    old_route_id = shipment.route_id
    shipment.route_id = best_route.route_id
    improvement = timedelta(hours=random.uniform(1, 4))
    shipment.eta = shipment.eta - improvement

    result = {
        "success": True,
        "shipment_id": shipment_id,
        "old_route": old_route_id,
        "new_route": best_route.route_id,
        "new_route_origin": best_route.origin,
        "new_route_destination": best_route.destination,
        "eta_improvement_hours": round(improvement.total_seconds() / 3600, 2),
        "old_route_geometry": _linestring_geojson(old_route.path) if old_route else None,
        "new_route_geometry": _linestring_geojson(best_route.path),
        "origin": shipment.origin,
        "destination": shipment.destination,
    }

    log.info("🔀 Rerouted %s: %s → %s (ETA improved by %.1fh)",
             shipment_id, old_route_id, best_route.route_id,
             improvement.total_seconds() / 3600)
    return result


def prioritize_loading(db: Session, shipment_id: str) -> dict:
    """Prioritize a shipment at its origin warehouse, advancing its status."""
    shipment = db.query(Shipment).filter_by(shipment_id=shipment_id).first()
    if not shipment:
        return {"success": False, "reason": "Shipment not found"}

    warehouse = db.query(WarehouseState).filter_by(location=shipment.origin).first()
    if warehouse:
        warehouse.queue_length = max(0, warehouse.queue_length - 1)

    if shipment.status == ShipmentStatus.created:
        shipment.status = ShipmentStatus.dispatched

    improvement = timedelta(hours=random.uniform(0.5, 2))
    shipment.eta = shipment.eta - improvement

    return {
        "success": True,
        "shipment_id": shipment_id,
        "new_status": shipment.status.value,
        "eta_improvement_hours": round(improvement.total_seconds() / 3600, 2),
    }


def switch_carrier(db: Session, shipment_id: str) -> dict:
    """Reassign a shipment to the most reliable alternative carrier."""
    shipment = db.query(Shipment).filter_by(shipment_id=shipment_id).first()
    if not shipment:
        return {"success": False, "reason": "Shipment not found"}

    old_carrier_obj = (
        db.query(CarrierPerformance)
        .filter(CarrierPerformance.carrier_id == shipment.carrier)
        .first()
    )

    best_carrier = (
        db.query(CarrierPerformance)
        .filter(CarrierPerformance.carrier_id != shipment.carrier)
        .order_by(CarrierPerformance.reliability_score.desc())
        .first()
    )
    if not best_carrier:
        return {"success": False, "reason": "No alternative carrier available"}

    old_carrier_id = shipment.carrier
    old_carrier_name = old_carrier_obj.name if old_carrier_obj else old_carrier_id
    old_reliability = old_carrier_obj.reliability_score if old_carrier_obj else 0.0
    old_delay_prob = old_carrier_obj.delay_probability if old_carrier_obj else 1.0

    shipment.carrier = best_carrier.carrier_id
    best_carrier.total_shipments += 1

    # ETA improvement from better carrier reliability
    reliability_gain = best_carrier.reliability_score - old_reliability
    improvement = timedelta(hours=random.uniform(0.5, 2) * max(reliability_gain, 0.1))
    shipment.eta = shipment.eta - improvement

    # Get route geometry for map visualization
    route = db.query(Route).filter_by(route_id=shipment.route_id).first() if shipment.route_id else None

    result = {
        "success": True,
        "shipment_id": shipment_id,
        "old_carrier": old_carrier_id,
        "old_carrier_name": old_carrier_name,
        "old_carrier_reliability": round(old_reliability, 3),
        "old_carrier_delay_prob": round(old_delay_prob, 3),
        "new_carrier": best_carrier.carrier_id,
        "new_carrier_name": best_carrier.name,
        "new_carrier_reliability": round(best_carrier.reliability_score, 3),
        "new_carrier_delay_prob": round(best_carrier.delay_probability, 3),
        "eta_improvement_hours": round(improvement.total_seconds() / 3600, 2),
        "origin": shipment.origin,
        "destination": shipment.destination,
        "route_id": shipment.route_id,
        "route_geometry": _linestring_geojson(route.path) if route else None,
    }

    log.info("🔄 Carrier switched for %s: %s → %s (reliability %.2f → %.2f, ETA improved by %.1fh)",
             shipment_id, old_carrier_id, best_carrier.carrier_id,
             old_reliability, best_carrier.reliability_score,
             improvement.total_seconds() / 3600)
    return result


def _send_email(subject: str, body_html: str, body_text: str) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure."""
    if not _cfg.SMTP_HOST or not _cfg.ALERT_EMAIL_TO:
        log.debug("📧 SMTP not configured — skipping email send")
        return False

    recipients = [e.strip() for e in _cfg.ALERT_EMAIL_TO.split(",") if e.strip()]
    if not recipients:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = _cfg.ALERT_EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        if _cfg.SMTP_USE_TLS:
            server = smtplib.SMTP(_cfg.SMTP_HOST, _cfg.SMTP_PORT, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(_cfg.SMTP_HOST, _cfg.SMTP_PORT, timeout=10)

        if _cfg.SMTP_USER and _cfg.SMTP_PASSWORD:
            server.login(_cfg.SMTP_USER, _cfg.SMTP_PASSWORD)

        server.sendmail(_cfg.ALERT_EMAIL_FROM, recipients, msg.as_string())
        server.quit()
        log.info("📧 Email sent to %s — subject: %s", recipients, subject)
        return True
    except Exception as exc:
        log.error("📧 Failed to send email: %s", exc)
        return False


def send_alert(db: Session, entity_id: str, message: str) -> dict:
    """Record an operator alert and optionally send via SMTP email.

    Emails are rate-limited **globally**: at most one email per
    ALERT_EMAIL_COOLDOWN seconds (default 5 min), regardless of entity.
    The alert is always logged to the DB; only the email is throttled.
    """
    global _email_last_sent_at

    alert_message = message or f"Risk detected for entity {entity_id}"
    log.info("🚨 ALERT  %s", entity_id)

    # ── global email cooldown ──────────────────────────────────────────
    now = time.monotonic()
    cooldown = _cfg.ALERT_EMAIL_COOLDOWN
    elapsed = now - _email_last_sent_at

    if elapsed < cooldown:
        remaining = int(cooldown - elapsed)
        log.debug("📧 Email suppressed — cooldown %ds remaining", remaining)
        return {
            "success": True,
            "entity_id": entity_id,
            "alert_type": "risk_alert",
            "alert_message": alert_message,
            "email_sent": False,
            "email_suppressed": True,
            "cooldown_remaining_seconds": remaining,
        }

    # ── build email ────────────────────────────────────────────────────
    subject = f"⚠️ RouteSense Alert — {entity_id}"
    body_text = f"Entity: {entity_id}\n\n{alert_message}"
    body_html = _build_alert_email_html(entity_id, alert_message)
    email_sent = _send_email(subject, body_html, body_text)

    if email_sent:
        _email_last_sent_at = now

    return {
        "success": True,
        "entity_id": entity_id,
        "alert_type": "risk_alert",
        "alert_message": alert_message,
        "email_sent": email_sent,
        "email_suppressed": False,
    }


def _build_alert_email_html(entity_id: str, message: str) -> str:
    """Generate a polished HTML email for risk alerts."""
    from datetime import datetime

    timestamp = datetime.utcnow().strftime("%b %d, %Y  %H:%M UTC")

    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:32px 16px">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#dc2626 0%,#991b1b 100%);padding:24px 32px">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px">
                  ⚠️&nbsp; Risk Alert
                </td>
                <td align="right" style="color:#fca5a5;font-size:12px">
                  {timestamp}
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Entity Badge -->
        <tr>
          <td style="padding:24px 32px 12px">
            <table cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#0f172a;border:1px solid #475569;border-radius:6px;padding:6px 14px">
                  <span style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1px">Entity</span><br>
                  <span style="color:#f1f5f9;font-size:16px;font-weight:600;font-family:monospace">{entity_id}</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Message -->
        <tr>
          <td style="padding:12px 32px 24px">
            <p style="color:#e2e8f0;font-size:14px;line-height:1.7;margin:0">
              {message}
            </p>
          </td>
        </tr>
        <!-- Divider -->
        <tr>
          <td style="padding:0 32px">
            <div style="border-top:1px solid #334155"></div>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:16px 32px 24px">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:#64748b;font-size:11px">
                  Sent by <strong style="color:#94a3b8">RouteSense AI Control Tower</strong>
                </td>
                <td align="right">
                  <span style="background:#14532d;color:#4ade80;font-size:10px;font-weight:600;padding:3px 10px;border-radius:10px;letter-spacing:0.5px">AUTOMATED</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def reserve_capacity(db: Session, warehouse_id: str) -> dict:
    """Free up capacity at a warehouse (simulates reserving overflow space)."""
    warehouse = db.query(WarehouseState).filter_by(warehouse_id=warehouse_id).first()
    if not warehouse:
        return {"success": False, "reason": "Warehouse not found"}

    reduction = random.randint(10, 30)
    warehouse.current_load = max(0, warehouse.current_load - reduction)
    warehouse.congestion_score = round(
        warehouse.current_load / max(warehouse.capacity, 1), 3
    )

    return {
        "success": True,
        "warehouse_id": warehouse_id,
        "load_reduction": reduction,
        "new_congestion_score": warehouse.congestion_score,
    }


def execute_action(db: Session, action: str, entity_id: str, **kwargs) -> dict:
    """Dispatch an action by name to the appropriate handler."""
    if action == "reroute_shipment":
        return reroute_shipment(db, entity_id)
    elif action == "prioritize_loading":
        return prioritize_loading(db, entity_id)
    elif action == "switch_carrier":
        return switch_carrier(db, entity_id)
    elif action == "send_alert":
        return send_alert(db, entity_id, kwargs.get("message", ""))
    elif action == "reserve_capacity":
        return reserve_capacity(db, entity_id)
    return {"success": False, "reason": f"Unknown action: {action}"}
