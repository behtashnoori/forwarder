"""Core write rules and customer-safe projection for manual unit tracking."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import uuid
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import (
    ShipmentRequest,
    ShipmentTracking,
    ShipmentTransportUnit,
    ShipmentTransportUnitUpdate,
    TrackingLocationReference,
)
from backend.operational_models import ExecutionUnit, OperationalEvent, OperationalShipment, utcnow
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


class LegacyWriteMappingError(TrackingValidationError):
    """A compatibility write lacks a safe, existing canonical target."""

    status = 409
    code = "LEGACY_WRITE_MAPPING"
    state = "NEEDS_DECISION"

    def __init__(self):
        super().__init__("A canonical execution mapping is required.")


def legacy_write_mapping_payload() -> dict:
    """Stable public error contract; never disclose persistence details."""
    return {
        "code": LegacyWriteMappingError.code,
        "state": LegacyWriteMappingError.state,
        "error": "A canonical execution mapping is required.",
    }


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
    shipment = db.session.scalar(
        db.select(OperationalShipment).where(OperationalShipment.shipment_request_id == req.id)
    )
    if shipment is not None:
        if tracking.operational_shipment_id not in (None, shipment.id):
            raise TrackingValidationError("tracking belongs to another operational shipment")
        tracking.operational_shipment_id = shipment.id
    if not tracking.is_enabled:
        tracking.is_enabled = True
        tracking.enabled_at = now
        tracking.enabled_by_user_id = actor_id
    tracking.disabled_at = None
    tracking.disabled_by_user_id = None
    return tracking


def enable_tracking_for_shipment(shipment: OperationalShipment, actor_id: int, *, now: datetime | None = None):
    """Enable the one tracking root for an operational shipment of either origin."""
    if shipment.organization_id is None:
        raise TrackingValidationError("tracking requires an explicit tenant-owned shipment")
    now = _utc_naive(now or datetime.utcnow())
    tracking = db.session.scalar(
        db.select(ShipmentTracking).where(ShipmentTracking.operational_shipment_id == shipment.id)
    )
    if tracking is None and shipment.shipment_request_id:
        req = db.session.get(ShipmentRequest, shipment.shipment_request_id)
        if req and req.shipment_tracking:
            tracking = req.shipment_tracking
    if tracking is None:
        tracking = ShipmentTracking(
            operational_shipment_id=shipment.id,
            shipment_request_id=shipment.shipment_request_id,
            operational_organization_id=shipment.organization_id,
        )
        db.session.add(tracking)
    if tracking.operational_shipment_id not in (None, shipment.id):
        raise TrackingValidationError("tracking belongs to another operational shipment")
    tracking.operational_shipment_id = shipment.id
    if tracking.operational_organization_id != shipment.organization_id:
        raise TrackingValidationError("tracking belongs to a different Organization")
    if not tracking.is_enabled:
        tracking.is_enabled = True
        tracking.enabled_at = now
        tracking.enabled_by_user_id = actor_id
    tracking.disabled_at = None
    tracking.disabled_by_user_id = None
    # ShipmentTransportUnit is historical compatibility data.  In particular,
    # enabling a compatibility projection must never attach legacy rows and
    # thereby promote them to current operational truth.
    return tracking


def tracking_for_shipment(shipment: OperationalShipment):
    return db.session.scalar(db.select(ShipmentTracking).where(ShipmentTracking.operational_shipment_id == shipment.id))


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
    """Retired compatibility command: it cannot safely create an execution."""
    # This legacy contract has no ExecutionUnit identity or project lineage.
    # Validating its free-text fields cannot make identity deterministic.
    raise LegacyWriteMappingError()


def _canonical_unit_for_legacy_unit(unit: ShipmentTransportUnit) -> ExecutionUnit:
    """Resolve only the one explicit back-reference, in the same tenant/root."""
    if unit.ownership_scope != "TENANT" or unit.operational_organization_id is None:
        raise LegacyWriteMappingError()
    execution = db.session.scalar(
        db.select(ExecutionUnit).where(
            ExecutionUnit.legacy_unit_id == unit.id,
            ExecutionUnit.organization_id == unit.operational_organization_id,
        )
    )
    if execution is None:
        raise LegacyWriteMappingError()
    if (
        unit.operational_shipment_id is not None
        and execution.operational_shipment_id != unit.operational_shipment_id
    ):
        raise LegacyWriteMappingError()
    return execution


def update_unit_metadata(
    unit: ShipmentTransportUnit,
    *,
    display_name: str | None = None,
    vehicle_reference: str | None = None,
):
    """Delegate supported compatibility metadata to the mapped execution."""
    execution = _canonical_unit_for_legacy_unit(unit)
    execution.display_name = _clean_optional(display_name, "display_name", 160)
    execution.vehicle_reference = _clean_optional(vehicle_reference, "vehicle_reference", 160)
    execution.version += 1
    execution.updated_at = utcnow()
    return execution


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
    """Append a canonical event for an explicitly mapped legacy unit."""
    # Resolve identity before legacy-envelope validation so every ambiguous
    # compatibility write has the one stable fail-closed contract.
    execution = _canonical_unit_for_legacy_unit(unit)
    if unit.tracking is None or not unit.tracking.is_enabled:
        raise TrackingValidationError("tracking is not enabled")
    if not unit.is_active:
        raise TrackingValidationError("unit is inactive")
    if unit.ownership_scope != "TENANT" or unit.operational_organization_id is None:
        raise LegacyWriteMappingError()
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
    lifecycle_status, delayed = {
        "not_started": ("not_started", False),
        "loading": ("in_progress", False),
        "departed": ("in_progress", False),
        "in_transit": ("in_progress", False),
        "at_checkpoint": ("in_progress", False),
        "delayed": ("in_progress", True),
        "arrived_destination": ("arrived", False),
        "delivered": ("delivered", False),
        "cancelled": ("cancelled", False),
    }[normalized_status]
    payload = {
        "status": normalized_status,
        "occurred_at": occurred_at.isoformat(),
        "location": resolved_location,
        "customer_message": clean_message,
        "internal_note": clean_internal_note,
        "is_customer_visible": is_customer_visible,
    }
    event = OperationalEvent(
        organization_id=execution.organization_id,
        project_id=execution.project_id,
        execution_unit_id=execution.id,
        event_type="legacy_tracking_update",
        lifecycle_status=lifecycle_status,
        checkpoint_text=resolved_location,
        customer_message=clean_message,
        internal_note=clean_internal_note,
        # The canonical event contract requires a customer message for public
        # visibility.  A legacy update without one is retained internally.
        visibility="customer" if is_customer_visible and clean_message else "internal",
        attention_required=False,
        delayed=delayed,
        occurred_at=occurred_at.replace(tzinfo=timezone.utc),
        actor_user_id=actor_id,
        source="legacy_compatibility",
        idempotency_key=f"legacy-compat-{uuid.uuid4()}",
        request_hash=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        threshold_policy_version="legacy-compat-v1",
    )
    db.session.add(event)
    execution.lifecycle_status = lifecycle_status
    execution.latest_checkpoint = resolved_location or execution.latest_checkpoint
    execution.delayed = delayed
    prior_event_at = execution.last_event_at
    if prior_event_at is not None and prior_event_at.tzinfo is None:
        prior_event_at = prior_event_at.replace(tzinfo=timezone.utc)
    execution.last_event_at = max(
        (value for value in (prior_event_at, event.occurred_at) if value is not None),
        default=None,
    )
    execution.version += 1
    execution.updated_at = utcnow()
    return event


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


def build_internal_tracking_for_shipment(shipment: OperationalShipment):
    """Authenticated tracking projection rooted at the operational shipment."""
    tracking = tracking_for_shipment(shipment)
    if tracking is None or not tracking.is_enabled:
        return None
    latest_rows = _latest_visible_updates(tracking)
    # A direct-operation legacy unit may predate the compatibility tracking
    # root.  Keep it visible as history without attaching or mutating it.
    for historical_unit in db.session.scalars(
        db.select(ShipmentTransportUnit).where(
            ShipmentTransportUnit.operational_shipment_id == shipment.id,
            ShipmentTransportUnit.tracking_id.is_(None),
        )
    ):
        history = list(historical_unit.updates)
        history.sort(key=lambda row: (row.occurred_at, row.id or 0), reverse=True)
        latest_rows.append((historical_unit, history, history[0] if history else None))
    aggregate_status, summary, last_updated = _aggregate(latest_rows)
    # Allocation is an execution read-model, not a tracking event.  ADR-046
    # makes ExecutionUnitCargoAllocation authoritative for current cargo
    # participation.  The legacy allocation table remains readable only for
    # cargo that has no canonical allocation; it must never override a
    # canonical execution shown on the same tracking surface.
    from backend.cargo_models import (
        ExecutionUnitCargoAllocation,
        ShipmentCargoTransportAllocation,
    )
    from backend.models import Customer
    from backend.operational_models import ExecutionUnit

    canonical_rows = db.session.scalars(
        db.select(ExecutionUnitCargoAllocation)
        .join(ExecutionUnit, ExecutionUnit.id == ExecutionUnitCargoAllocation.execution_unit_id)
        .where(
            ExecutionUnitCargoAllocation.operational_shipment_id == shipment.id,
            ExecutionUnitCargoAllocation.is_current.is_(True),
            or_(ExecutionUnitCargoAllocation.dimension == "ACTUAL", ExecutionUnitCargoAllocation.dimension.is_(None)),
            ExecutionUnit.organization_id == shipment.organization_id,
        )
        .options(
            selectinload(ExecutionUnitCargoAllocation.cargo_item),
            selectinload(ExecutionUnitCargoAllocation.execution_unit),
        )
    ).all()
    canonical_rows.sort(key=lambda row: (
        row.route_stage_execution.route_plan_id if row.route_stage_execution else -1,
        row.route_stage_execution.route_leg.sequence_number if row.route_stage_execution else -1,
    ), reverse=True)
    canonical_cargo_ids = {
        row.shipment_cargo_item_id for row in canonical_rows
    }
    canonical_by_unit = {}
    seen_unit_cargo = set()
    for row in canonical_rows:
        pair = (row.execution_unit_id, row.shipment_cargo_item_id)
        if pair in seen_unit_cargo:
            continue
        seen_unit_cargo.add(pair)
        cargo = row.cargo_item
        canonical_by_unit.setdefault(row.execution_unit_id, []).append({
            "cargo_item_public_id": cargo.public_id,
            "cargo_name": cargo.display_name_snapshot,
            "cargo_owner": (
                (db.session.get(Customer, cargo.cargo_owner_customer_id).company_name
                 or f"{db.session.get(Customer, cargo.cargo_owner_customer_id).first_name} {db.session.get(Customer, cargo.cargo_owner_customer_id).last_name}".strip())
                if cargo.cargo_owner_customer_id else None
            ),
            "allocated_quantity": str(row.allocated_quantity),
            "uom_symbol": cargo.uom_symbol_snapshot,
        })

    by_unit = {}
    rows = db.session.scalars(
        db.select(ShipmentCargoTransportAllocation)
        .where(ShipmentCargoTransportAllocation.operational_shipment_id == shipment.id)
        .options(selectinload(ShipmentCargoTransportAllocation.cargo_item))
    ).all()
    for row in rows:
        if row.shipment_cargo_item_id in canonical_cargo_ids:
            continue
        owner = db.session.get(Customer, row.cargo_item.cargo_owner_customer_id) if row.cargo_item.cargo_owner_customer_id else None
        by_unit.setdefault(row.transport_unit_id, []).append({"cargo_item_public_id": row.cargo_item.public_id, "cargo_name": row.cargo_item.display_name_snapshot, "cargo_owner": (owner.company_name or f"{owner.first_name} {owner.last_name}".strip()) if owner else None, "allocated_quantity": str(row.allocated_quantity), "uom_symbol": row.cargo_item.uom_symbol_snapshot})
    canonical_units = []
    for execution_id, allocated_cargo in canonical_by_unit.items():
        unit = next(row.execution_unit for row in canonical_rows if row.execution_unit_id == execution_id)
        carrier = db.session.get(Customer, unit.carrier_customer_id) if unit.carrier_customer_id else None
        canonical_units.append({
            "id": unit.id,
            "public_id": unit.public_id,
            "source": "canonical_execution",
            "unit_code": unit.unit_code,
            "unit_type": unit.unit_type,
            "display_name": unit.display_name,
            "vehicle_reference": unit.vehicle_reference,
            "carrier": (carrier.company_name or f"{carrier.first_name} {carrier.last_name}".strip()) if carrier else None,
            "is_active": unit.is_active,
            "latest_status": unit.lifecycle_status,
            "latest_location": unit.latest_checkpoint,
            "latest_location_detail": None,
            "latest_event_at": _iso(unit.last_event_at),
            "allocated_cargo": allocated_cargo,
            # Event history belongs to OperationalEvent.  Do not manufacture
            # ShipmentTransportUnitUpdate history for an ExecutionUnit.
            "history": [],
        })
    return {
        "enabled": True,
        "enabled_at": _iso(tracking.enabled_at),
        "aggregate_status": aggregate_status,
        "summary": summary,
        "last_updated_at": _iso(last_updated),
        "units": canonical_units + [
            {
                "id": unit.id,
                "source": "historical_legacy",
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
                "allocated_cargo": by_unit.get(unit.id, []),
                "history": [{"id": event.id, "status": event.status, "location": _location_payload(event), "customer_message": event.customer_message, "internal_note": event.internal_note, "is_customer_visible": event.is_customer_visible, "occurred_at": _iso(event.occurred_at)} for event in sorted(unit.updates, key=lambda x: (x.occurred_at, x.id or 0), reverse=True)],
            }
            for unit, _history, latest in latest_rows
        ],
    }


def build_internal_unit_tracking(req: ShipmentRequest):
    """Legacy request-root projection, retained for compatible request URLs."""
    shipment = db.session.scalar(
        db.select(OperationalShipment).where(OperationalShipment.shipment_request_id == req.id)
    )
    tracking = req.shipment_tracking
    if shipment is not None and tracking is not None and tracking_for_shipment(shipment) is tracking:
        return build_internal_tracking_for_shipment(shipment)
    # Historical request tracking before the operational root was materialized
    # (and old fixtures) remains a fully functional compatible projection.
    if tracking is None or not tracking.is_enabled:
        return None
    latest_rows = _latest_visible_updates(tracking)
    aggregate_status, summary, last_updated = _aggregate(latest_rows)
    return {"enabled": True, "enabled_at": _iso(tracking.enabled_at), "aggregate_status": aggregate_status, "summary": summary, "last_updated_at": _iso(last_updated), "units": [{"id": unit.id, "unit_code": unit.unit_code, "unit_type": unit.unit_type, "display_name": unit.display_name, "vehicle_reference": unit.vehicle_reference, "is_active": unit.is_active, "latest_status": latest.status if latest else "not_started", "latest_location": _location_payload(_latest_location_row(history))["location_name"] if _latest_location_row(history) else None, "latest_location_detail": _location_payload(_latest_location_row(history)) if _latest_location_row(history) else None, "latest_event_at": _iso(latest.occurred_at) if latest else None, "allocated_cargo": [], "history": [{"id": event.id, "status": event.status, "location": _location_payload(event), "customer_message": event.customer_message, "internal_note": event.internal_note, "is_customer_visible": event.is_customer_visible, "occurred_at": _iso(event.occurred_at)} for event in sorted(unit.updates, key=lambda x: (x.occurred_at, x.id or 0), reverse=True)]} for unit, history, latest in latest_rows]}


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
