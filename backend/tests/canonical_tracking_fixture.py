"""Small canonical execution/event builders shared by current-journey tests."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count

from backend.extensions import db
from backend.operational_models import ExecutionUnit, OperationalEvent, OperationalShipment, Project
from backend.services import execution_unit_service


_keys = count(1)


def execution_unit(
    project: Project,
    actor_id: int,
    *,
    shipment: OperationalShipment | None = None,
    unit_code: str,
    unit_type: str = "road",
    display_name: str | None = None,
    vehicle_reference: str | None = None,
    is_active: bool = True,
    sort_order: int = 0,
) -> ExecutionUnit:
    row = ExecutionUnit(
        project_id=project.id,
        operational_shipment_id=shipment.id if shipment else None,
        unit_code=unit_code,
        unit_type=unit_type,
        display_name=display_name,
        vehicle_reference=(vehicle_reference or "").strip() or None,
        is_active=is_active,
        created_by_user_id=actor_id,
    )
    db.session.add(row)
    db.session.flush()
    return row


def append_event(
    unit: ExecutionUnit,
    actor_id: int,
    *,
    status: str,
    occurred_at: datetime,
    logistics_point_public_id: str | None = None,
    tracking_location_reference_id: int | None = None,
    location_reference_id: int | None = None,
    location_text: str | None = None,
    customer_message: str | None = None,
    internal_note: str | None = None,
    customer_visible: bool = True,
):
    lifecycle, delayed = {
        "not_started": ("not_started", False),
        "loading": ("in_progress", False),
        "departed": ("in_progress", False),
        "in_transit": ("in_progress", False),
        "at_checkpoint": ("in_progress", False),
        "delayed": ("in_progress", True),
        "arrived_destination": ("arrived", False),
        "delivered": ("delivered", False),
        "cancelled": ("cancelled", False),
    }[status]
    tracking_location_reference_id = tracking_location_reference_id or location_reference_id
    identities = [
        ("logistics_point_public_id", logistics_point_public_id),
        ("tracking_location_reference_id", tracking_location_reference_id),
        ("location_text", location_text),
    ]
    supplied = [(key, value) for key, value in identities if value is not None]
    location = {supplied[0][0]: supplied[0][1]} if len(supplied) == 1 else (
        {key: value for key, value in supplied} if supplied else None
    )
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    payload = {
        "expected_version": unit.version,
        "event_type": status,
        "lifecycle_status": lifecycle,
        "occurred_at": occurred_at.isoformat(),
        "visibility": "customer" if customer_visible else "internal",
        "customer_message": (customer_message or status.replace("_", " ")) if customer_visible else None,
        "internal_note": internal_note,
        "delayed": delayed,
    }
    if location is not None:
        payload["location"] = location
    event, created = execution_unit_service.create_event(
        unit, payload, {"id": actor_id}, f"canonical-test-{next(_keys)}"
    )
    assert created is True
    return event


def latest_events(units: list[ExecutionUnit], *, customer: bool = False) -> dict[int, OperationalEvent | None]:
    result = {}
    for unit in units:
        query = db.select(OperationalEvent).where(OperationalEvent.execution_unit_id == unit.id)
        if customer:
            query = query.where(OperationalEvent.visibility == "customer")
        result[unit.id] = db.session.scalar(
            query
            .order_by(OperationalEvent.occurred_at.desc(), OperationalEvent.id.desc())
        )
    return result


def canonical_tracking_summary(project: Project) -> dict:
    """Legacy-shaped assertions backed exclusively by canonical rows."""
    units = db.session.scalars(
        db.select(ExecutionUnit)
        .where(ExecutionUnit.project_id == project.id, ExecutionUnit.is_active.is_(True))
        .order_by(ExecutionUnit.unit_code)
    ).all()
    latest = latest_events(units, customer=True)
    categories = {
        "without_updates": 0, "not_started": 0, "loading": 0, "in_transit": 0,
        "delayed": 0, "arrived": 0, "delivered": 0, "cancelled": 0,
    }
    for unit in units:
        event = latest[unit.id]
        if event is None:
            categories["without_updates"] += 1
        else:
            categories[{
                "not_started": "not_started", "loading": "loading", "departed": "in_transit",
                "in_transit": "in_transit", "at_checkpoint": "in_transit", "delayed": "delayed",
                "arrived_destination": "arrived", "delivered": "delivered", "cancelled": "cancelled",
            }[event.event_type]] += 1
    categories["total_units"] = len(units)
    updated = max((row.occurred_at for row in latest.values() if row), default=None)
    with_updates = len(units) - categories["without_updates"]
    if not units or not with_updates:
        aggregate = "not_started"
    elif categories["delivered"] == len(units):
        aggregate = "completed"
    elif categories["cancelled"] == len(units):
        aggregate = "cancelled"
    elif categories["delayed"] or categories["cancelled"]:
        aggregate = "attention_required"
    elif categories["delivered"]:
        aggregate = "partially_delivered"
    else:
        aggregate = "in_progress"
    return {"aggregate_status": aggregate, "summary": categories, "last_updated_at": updated}
