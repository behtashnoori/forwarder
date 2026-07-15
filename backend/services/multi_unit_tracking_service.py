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
        "pending",
        "ready_for_dispatch",
        "departed",
        "in_transit",
        "delayed",
        "arrived",
        "delivered",
        "exception",
    }
)
STATUS_PROGRESS = {
    "pending": 0,
    "ready_for_dispatch": 10,
    "departed": 25,
    "in_transit": 55,
    "delayed": 55,
    "exception": 55,
    "arrived": 90,
    "delivered": 100,
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
    name = (display_name or "").strip() or None
    if name and len(name) > 100:
        raise TrackingValidationError("display_name must be at most 100 characters")
    unit = ShipmentTransportUnit(
        tracking=tracking,
        unit_code=code,
        unit_type=kind,
        display_name=name,
        sort_order=sort_order,
        is_active=True,
        created_by_user_id=actor_id,
    )
    db.session.add(unit)
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


def build_public_unit_tracking(req: ShipmentRequest):
    """Return a privacy-allowlisted customer projection, or None when disabled."""
    tracking = req.shipment_tracking
    if tracking is None or not tracking.is_enabled:
        return None

    public_units = []
    progress_values = []
    delivered_count = 0
    arrived_count = 0
    shipment_last_updated = None
    for unit in tracking.units:
        if not unit.is_active:
            continue
        history_rows = [row for row in unit.updates if row.is_customer_visible]
        history_rows.sort(key=lambda row: (row.occurred_at, row.id or 0), reverse=True)
        latest = history_rows[0] if history_rows else None
        latest_location_row = next((row for row in history_rows if row.location), None)
        latest_status = latest.status if latest else "pending"
        progress_values.append(STATUS_PROGRESS.get(latest_status, 0))
        delivered_count += int(latest_status == "delivered")
        arrived_count += int(latest_status in {"arrived", "delivered"})
        if latest and (shipment_last_updated is None or latest.occurred_at > shipment_last_updated):
            shipment_last_updated = latest.occurred_at
        public_units.append(
            {
                "id": unit.id,
                "unit_code": unit.unit_code,
                "unit_type": unit.unit_type,
                "display_name": unit.display_name,
                "latest_status": latest_status,
                "latest_location": latest_location_row.location if latest_location_row else None,
                "latest_update_at": _iso(latest.occurred_at) if latest else None,
                "history": [
                    {
                        "status": row.status,
                        "location": row.location,
                        "message": row.customer_message,
                        "occurred_at": _iso(row.occurred_at),
                    }
                    for row in history_rows
                ],
            }
        )

    total = len(public_units)
    if total == 0:
        aggregate_status = "awaiting_units"
    elif delivered_count == total:
        aggregate_status = "delivered"
    elif delivered_count:
        aggregate_status = "partially_delivered"
    elif arrived_count == total:
        aggregate_status = "arrived"
    else:
        aggregate_status = "in_progress"
    return {
        "enabled": True,
        "enabled_at": _iso(tracking.enabled_at),
        "aggregate_status": aggregate_status,
        "progress_percent": round(sum(progress_values) / total) if total else 0,
        "unit_count": total,
        "delivered_unit_count": delivered_count,
        "arrived_unit_count": arrived_count,
        "is_partially_delivered": 0 < delivered_count < total,
        "is_complete": total > 0 and delivered_count == total,
        "latest_update_at": _iso(shipment_last_updated),
        "units": public_units,
    }
