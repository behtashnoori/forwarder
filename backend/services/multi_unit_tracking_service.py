"""Core write rules and customer-safe projection for manual unit tracking."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import (
    ShipmentRequest,
    ShipmentTracking,
    ShipmentTransportUnit,
    ShipmentTransportUnitUpdate,
    TrackingLocationReference,
)
from backend.services.legacy_datetime import serialize_legacy_utc_datetime


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
    if req.ownership_scope != "TENANT" or req.operational_organization_id is None:
        raise TrackingValidationError("tracking requires an explicit tenant-owned shipment")
    now = _utc_naive(now or datetime.utcnow())
    tracking = req.shipment_tracking
    if tracking is None:
        tracking = ShipmentTracking(
            shipment_request=req,
            operational_organization_id=req.operational_organization_id,
        )
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
    if tracking.operational_organization_id is None:
        raise TrackingValidationError("tracking has ambiguous tenant ownership")
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
        ownership_scope="TENANT",
        operational_organization_id=tracking.operational_organization_id,
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
    logistics_point_public_id: str | None = None,
    location_reference_id: int | None = None,
    location_text: str | None = None,
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
    if unit.ownership_scope != "TENANT" or unit.operational_organization_id is None:
        raise TrackingValidationError("transport unit has ambiguous tenant ownership")
    if unit.tracking.operational_organization_id != unit.operational_organization_id:
        raise TrackingValidationError("transport unit belongs to a different Organization")
    normalized_status = _clean_required(status, "status", 32).lower()
    if normalized_status not in UNIT_STATUSES:
        raise TrackingValidationError("unsupported status")
    if not isinstance(occurred_at, datetime):
        raise TrackingValidationError("occurred_at must be a datetime")
    occurred_at = _utc_naive(occurred_at)
    created_at = _utc_naive(now or datetime.utcnow())
    if occurred_at > created_at:
        raise TrackingValidationError("occurred_at cannot be in the future")
    clean_location = _clean_optional(location, "location", 255)
    clean_location_text = _clean_optional(location_text, "location_text", 255)
    point_public_id = _clean_optional(
        logistics_point_public_id, "logistics_point_public_id", 36
    )
    reference = None
    point = None
    if location_reference_id is not None:
        if not isinstance(location_reference_id, int) or isinstance(location_reference_id, bool):
            raise TrackingValidationError("location_reference_id must be an integer")
        reference = db.session.get(TrackingLocationReference, location_reference_id)
        if reference is None or not reference.is_active:
            raise TrackingValidationError("active tracking location reference not found")
    if point_public_id:
        point = db.session.scalar(
            db.select(LogisticsPoint)
            .join(LogisticsPointType)
            .where(
                LogisticsPoint.public_id == point_public_id,
                LogisticsPoint.organization_id == unit.operational_organization_id,
                LogisticsPoint.is_active.is_(True),
                LogisticsPointType.is_active.is_(True),
            )
            .with_for_update()
        )
        if point is None:
            raise TrackingValidationError("active logistics point not found")
    authorities = sum(bool(value) for value in (point, reference, clean_location_text))
    if authorities > 1:
        raise TrackingValidationError("supply exactly one location authority")
    if clean_location and authorities:
        raise TrackingValidationError("location cannot accompany another location authority")
    resolved_location = (
        point.fa_name if point else reference.name_fa if reference else (clean_location_text or clean_location)
    )
    clean_message = (customer_message or "").strip() or None
    clean_internal_note = (internal_note or "").strip() or None
    if not isinstance(is_customer_visible, bool):
        raise TrackingValidationError("is_customer_visible must be boolean")
    update = ShipmentTransportUnitUpdate(
        unit=unit,
        ownership_scope="TENANT",
        operational_organization_id=unit.operational_organization_id,
        status=normalized_status,
        location=resolved_location,
        logistics_point_id=point.id if point else None,
        location_reference=reference,
        location_name_snapshot=point.fa_name if point else reference.name_fa if reference else None,
        country_code_snapshot=point.country.code if point else reference.country_code if reference else None,
        location_name_en_snapshot=point.en_name if point else None,
        location_type_code_snapshot=point.point_type.immutable_code if point else None,
        location_city_name_snapshot=point.city.name_fa if point and point.city else None,
        location_text=clean_location_text or (clean_location if not reference else None),
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
    # Values reaching this serializer are written by this service using the
    # legacy schema's proven UTC-naive convention.
    return serialize_legacy_utc_datetime(value)


def _location_payload(row):
    name = row.location_name_snapshot or row.location_text or row.location
    source = (
        "logistics_point" if row.logistics_point_id else
        "legacy_reference" if row.location_reference_id else
        "manual" if (row.location_text or row.location) else
        "unavailable"
    )
    return {
        "location_name": name,
        "location_name_en": row.location_name_en_snapshot,
        "location_text": row.location_text,
        "country_code": row.country_code_snapshot,
        "location_type_code": row.location_type_code_snapshot,
        "location_city_name": row.location_city_name_snapshot,
        "location_source": source,
    }


def _public_location_payload(row):
    payload = _location_payload(row)
    payload.pop("location_type_code", None)
    return payload


def _latest_location_row(history):
    return next(
        (
            row
            for row in history
            if row.location_name_snapshot or row.location_text or row.location
        ),
        None,
    )


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
                "latest_location": (
                    _location_payload(_latest_location_row(_history))["location_name"]
                    if _latest_location_row(_history)
                    else None
                ),
                "latest_location_detail": (
                    _location_payload(_latest_location_row(_history))
                    if _latest_location_row(_history)
                    else None
                ),
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
        latest_location_row = _latest_location_row(history_rows)
        latest_status = latest.status if latest else "not_started"
        progress_values.append(STATUS_PROGRESS.get(latest_status, 0))
        public_units.append(
            {
                "unit_code": unit.unit_code,
                "unit_type": unit.unit_type,
                "display_name": unit.display_name,
                "vehicle_reference": unit.vehicle_reference,
                "latest_status": latest_status,
                "latest_location": (
                    _public_location_payload(latest_location_row)["location_name"]
                    if latest_location_row
                    else None
                ),
                "latest_location_detail": _public_location_payload(latest_location_row) if latest_location_row else None,
                "latest_event_at": _iso(latest.occurred_at) if latest else None,
                "timeline": [
                    {
                        "status": row.status,
                        "location": row.location,
                        **_public_location_payload(row),
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
