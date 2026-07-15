"""Core write rules and customer-safe projection for manual unit tracking."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.extensions import db
from backend.models import (
    ShipmentRequest,
    ShipmentTracking,
    ShipmentTransportUnit,
    ShipmentTransportUnitUpdate,
)


TRACKING_ELIGIBLE_REQUEST_STATUSES = frozenset({"won"})
UNIT_TYPES = frozenset({"truck", "container", "wagon", "other"})
UNIT_STATUSES = frozenset(
    {
        "not_started",
        "loading",
        "departed",
        "in_transit",
        "at_checkpoint",
        "delayed",
        "arrived_destination",
        "delivered",
        "cancelled",
    }
)
AGGREGATE_STATUSES = frozenset(
    {
        "not_started",
        "in_progress",
        "partially_delivered",
        "attention_required",
        "completed",
        "cancelled",
    }
)
STATUS_PROGRESS = {
    "not_started": 0,
    "loading": 10,
    "departed": 25,
    "in_transit": 55,
    "at_checkpoint": 65,
    "delayed": 55,
    "arrived_destination": 90,
    "delivered": 100,
    "cancelled": 0,
}
SUMMARY_CATEGORIES = {
    "not_started": "not_started",
    "loading": "loading",
    "departed": "in_transit",
    "in_transit": "in_transit",
    "at_checkpoint": "in_transit",
    "delayed": "delayed",
    "arrived_destination": "arrived",
    "delivered": "delivered",
    "cancelled": "cancelled",
}


class TrackingValidationError(ValueError):
    """Raised when a tracking write violates the MVP domain rules."""


def _clean_required(value: str | None, field: str, maximum: int) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise TrackingValidationError(f"{field} is required")
    if len(cleaned) > maximum:
        raise TrackingValidationError(f"{field} must be at most {maximum} characters")
    return cleaned


def _clean_optional(value: str | None, field: str, maximum: int) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TrackingValidationError(f"{field} must be a string")
    cleaned = (value or "").strip() or None
    if cleaned and len(cleaned) > maximum:
        raise TrackingValidationError(f"{field} must be at most {maximum} characters")
    return cleaned


def _utc_naive(value: datetime) -> datetime:
    """Normalize aware API timestamps to the UTC-naive convention used by this schema."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def enable_tracking(req: ShipmentRequest, actor_id: int, *, now: datetime | None = None):
    """Enable customer tracking only after the request has been won/accepted."""
    if req.status not in TRACKING_ELIGIBLE_REQUEST_STATUSES:
        raise TrackingValidationError("shipment must be accepted before tracking is enabled")
    if not req.tracking_code:
        raise TrackingValidationError("shipment must have a tracking code")
    now = _utc_naive(now or datetime.utcnow())
    tracking = req.shipment_tracking
    if tracking is None:
        tracking = ShipmentTracking(shipment_request=req)
        db.session.add(tracking)
    if not tracking.is_enabled:
        tracking.is_enabled = True
        tracking.enabled_at = now
        tracking.enabled_by_user_id = actor_id
    tracking.disabled_at = None
    tracking.disabled_by_user_id = None
    return tracking


def disable_tracking(tracking: ShipmentTracking, actor_id: int, *, now: datetime | None = None):
    """Disable public unit detail without deleting its audit history."""
    if tracking.is_enabled:
        tracking.is_enabled = False
        tracking.disabled_at = _utc_naive(now or datetime.utcnow())
        tracking.disabled_by_user_id = actor_id
    return tracking


def add_unit(
    tracking: ShipmentTracking,
    actor_id: int,
    *,
    unit_code: str,
    unit_type: str,
    display_name: str | None = None,
    vehicle_reference: str | None = None,
    sort_order: int = 0,
):
    if not tracking.is_enabled:
        raise TrackingValidationError("tracking must be enabled before units are added")
    code = _clean_required(unit_code, "unit_code", 64)
    kind = _clean_required(unit_type, "unit_type", 32).lower()
    if kind not in UNIT_TYPES:
        raise TrackingValidationError("unsupported unit_type")
    if not isinstance(sort_order, int) or isinstance(sort_order, bool) or sort_order < 0:
        raise TrackingValidationError("sort_order must be a non-negative integer")
    name = _clean_optional(display_name, "display_name", 100)
    reference = _clean_optional(vehicle_reference, "vehicle_reference", 100)
    unit = ShipmentTransportUnit(
        tracking=tracking,
        unit_code=code,
        unit_type=kind,
        display_name=name,
        vehicle_reference=reference,
        sort_order=sort_order,
        is_active=True,
        created_by_user_id=actor_id,
    )
    db.session.add(unit)
    return unit


def update_unit_metadata(
    unit: ShipmentTransportUnit,
    *,
    display_name: str | None = None,
    vehicle_reference: str | None = None,
):
    """Update customer-safe optional metadata without changing the business key."""
    unit.display_name = _clean_optional(display_name, "display_name", 100)
    unit.vehicle_reference = _clean_optional(
        vehicle_reference, "vehicle_reference", 100
    )
    return unit


def add_update(
    unit: ShipmentTransportUnit,
    actor_id: int,
    *,
    status: str,
    occurred_at: datetime,
    location: str | None = None,
    customer_message: str | None = None,
    internal_note: str | None = None,
    is_customer_visible: bool = True,
    now: datetime | None = None,
):
    """Append a manual unit update; existing updates are intentionally immutable."""
    if not unit.tracking.is_enabled:
        raise TrackingValidationError("tracking is not enabled")
    if not unit.is_active:
        raise TrackingValidationError("unit is inactive")
    normalized_status = _clean_required(status, "status", 32).lower()
    if normalized_status not in UNIT_STATUSES:
        raise TrackingValidationError("unsupported status")
    if not isinstance(occurred_at, datetime):
        raise TrackingValidationError("occurred_at must be a datetime")
    occurred_at = _utc_naive(occurred_at)
    created_at = _utc_naive(now or datetime.utcnow())
    if occurred_at > created_at:
        raise TrackingValidationError("occurred_at cannot be in the future")
    clean_location = (location or "").strip() or None
    if clean_location and len(clean_location) > 255:
        raise TrackingValidationError("location must be at most 255 characters")
    clean_message = (customer_message or "").strip() or None
    clean_internal_note = (internal_note or "").strip() or None
    if not isinstance(is_customer_visible, bool):
        raise TrackingValidationError("is_customer_visible must be boolean")
    update = ShipmentTransportUnitUpdate(
        unit=unit,
        status=normalized_status,
        location=clean_location,
        customer_message=clean_message,
        internal_note=clean_internal_note,
        is_customer_visible=is_customer_visible,
        occurred_at=occurred_at,
        created_by_user_id=actor_id,
        created_at=created_at,
    )
    db.session.add(update)
    return update


def _iso(value):
    return value.isoformat() if value and hasattr(value, "isoformat") else None


def _latest_visible_updates(tracking: ShipmentTracking):
    rows = []
    for unit in tracking.units:
        if not unit.is_active:
            continue
        history = [row for row in unit.updates if row.is_customer_visible]
        history.sort(key=lambda row: (row.occurred_at, row.id or 0), reverse=True)
        rows.append((unit, history, history[0] if history else None))
    return rows


def _aggregate(latest_rows):
    summary = {key: 0 for key in (
        "without_updates", "not_started", "loading", "in_transit", "delayed",
        "arrived", "delivered", "cancelled",
    )}
    summary["total_units"] = len(latest_rows)
    latest_events = []
    for _unit, _history, latest in latest_rows:
        if latest is None:
            summary["without_updates"] += 1
            continue
        latest_events.append(latest)
        summary[SUMMARY_CATEGORIES[latest.status]] += 1

    total = summary["total_units"]
    with_updates = total - summary["without_updates"]
    if total == 0 or with_updates == 0:
        status = "not_started"
    elif with_updates == total and summary["delivered"] == total:
        status = "completed"
    elif with_updates == total and summary["cancelled"] == total:
        status = "cancelled"
    elif summary["delayed"] or summary["cancelled"]:
        status = "attention_required"
    elif summary["delivered"]:
        status = "partially_delivered"
    else:
        status = "in_progress"
    assert status in AGGREGATE_STATUSES
    last_updated = max((row.occurred_at for row in latest_events), default=None)
    return status, summary, last_updated


def build_internal_unit_tracking(req: ShipmentRequest):
    """Return authenticated management data, including IDs required by mutations."""
    tracking = req.shipment_tracking
    if tracking is None or not tracking.is_enabled:
        return None
    latest_rows = _latest_visible_updates(tracking)
    aggregate_status, summary, last_updated = _aggregate(latest_rows)
    return {
        "enabled": True,
        "enabled_at": _iso(tracking.enabled_at),
        "aggregate_status": aggregate_status,
        "summary": summary,
        "last_updated_at": _iso(last_updated),
        "units": [
            {
                "id": unit.id,
                "unit_code": unit.unit_code,
                "unit_type": unit.unit_type,
                "display_name": unit.display_name,
                "vehicle_reference": unit.vehicle_reference,
                "is_active": unit.is_active,
                "latest_status": latest.status if latest else "not_started",
                "latest_location": latest.location if latest else None,
                "latest_event_at": _iso(latest.occurred_at) if latest else None,
            }
            for unit, _history, latest in latest_rows
        ],
    }


def build_public_unit_tracking(req: ShipmentRequest):
    """Build a customer-safe response from an explicit field allowlist."""
    tracking = req.shipment_tracking
    if tracking is None or not tracking.is_enabled:
        return None

    public_units = []
    progress_values = []
    latest_rows = _latest_visible_updates(tracking)
    aggregate_status, summary, last_updated = _aggregate(latest_rows)
    for unit, history_rows, latest in latest_rows:
        latest_location_row = next((row for row in history_rows if row.location), None)
        latest_status = latest.status if latest else "not_started"
        progress_values.append(STATUS_PROGRESS.get(latest_status, 0))
        public_units.append(
            {
                "unit_code": unit.unit_code,
                "unit_type": unit.unit_type,
                "display_name": unit.display_name,
                "vehicle_reference": unit.vehicle_reference,
                "latest_status": latest_status,
                "latest_location": latest_location_row.location if latest_location_row else None,
                "latest_event_at": _iso(latest.occurred_at) if latest else None,
                "timeline": [
                    {
                        "status": row.status,
                        "location": row.location,
                        "customer_note": row.customer_message,
                        "event_at": _iso(row.occurred_at),
                    }
                    for row in history_rows
                ],
            }
        )

    total = len(public_units)
    return {
        "enabled": True,
        "enabled_at": _iso(tracking.enabled_at),
        "aggregate_status": aggregate_status,
        "progress_percent": round(sum(progress_values) / total) if total else 0,
        "summary": summary,
        "last_updated_at": _iso(last_updated),
        "units": public_units,
    }
