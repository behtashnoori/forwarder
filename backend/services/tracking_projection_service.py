"""Read-only canonical tracking projections authorized by ADR-040 phases 1-2."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select

from backend.extensions import db
from backend.operational_models import ExecutionUnit, OperationalEvent, OperationalShipment, Project


LOCATION_STATES = frozenset({"UNAVAILABLE", "SINGLE", "COMMON", "MULTIPLE"})
CACHE_STATES = frozenset(
    {"CONSISTENT", "CACHE_MISSING", "CACHE_STALE", "CACHE_CONFLICT", "NOT_APPLICABLE"}
)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    value = _utc(value)
    return value.isoformat().replace("+00:00", "Z") if value else None


def _event_key(event: OperationalEvent) -> tuple[datetime, datetime, str]:
    """ADR-040 business ordering; public_id is the immutable final tie-breaker."""
    return (_utc(event.occurred_at), _utc(event.recorded_at), event.public_id)


def _effective_events(events: Iterable[OperationalEvent]) -> list[OperationalEvent]:
    rows = list(events)
    superseded_ids = {row.supersedes_event_id for row in rows if row.supersedes_event_id}
    return sorted(
        (row for row in rows if row.id not in superseded_ids),
        key=_event_key,
        reverse=True,
    )


def _cache_health(
    unit: ExecutionUnit,
    events: list[OperationalEvent],
    latest_event: OperationalEvent | None,
    location_event: OperationalEvent | None,
) -> str:
    cached_at = _utc(unit.last_event_at)
    expected_at = _utc(latest_event.occurred_at) if latest_event else None
    expected_location = location_event.checkpoint_text if location_event else None
    if expected_at is None and expected_location is None:
        return "NOT_APPLICABLE" if cached_at is None and unit.latest_checkpoint is None else "CACHE_CONFLICT"
    if (expected_at is not None and cached_at is None) or (
        expected_location is not None and unit.latest_checkpoint is None
    ):
        return "CACHE_MISSING"
    if cached_at == expected_at and unit.latest_checkpoint == expected_location:
        return "CONSISTENT"

    effective_times = {_utc(row.occurred_at) for row in events}
    historical_locations = {
        row.checkpoint_text for row in events if row.checkpoint_text is not None
    }
    time_is_older = cached_at in effective_times and expected_at is not None and cached_at < expected_at
    location_is_older = (
        unit.latest_checkpoint in historical_locations
        and unit.latest_checkpoint != expected_location
    )
    return "CACHE_STALE" if time_is_older or location_is_older else "CACHE_CONFLICT"


def _unit_projection(unit: ExecutionUnit, events: Iterable[OperationalEvent]) -> dict:
    effective = _effective_events(events)
    latest = effective[0] if effective else None
    location = next((row for row in effective if row.checkpoint_text is not None), None)
    status = next((row for row in effective if row.lifecycle_status is not None), None)
    health = _cache_health(unit, effective, latest, location)
    source = "operational_event" if effective else "unavailable"
    projection_state = "conflict" if health in {"CACHE_STALE", "CACHE_CONFLICT"} else (
        "authoritative" if effective else "unavailable"
    )
    return {
        "unit_public_id": unit.public_id,
        "current_location": location.checkpoint_text if location else None,
        "location_state": "SINGLE" if location else "UNAVAILABLE",
        "latest_event_at": _iso(latest.occurred_at) if latest else None,
        "latest_event_recorded_at": _iso(latest.recorded_at) if latest else None,
        "latest_event_type": latest.event_type if latest else None,
        "latest_event_public_id": latest.public_id if latest else None,
        "lifecycle_status": status.lifecycle_status if status else "not_started",
        "source": source,
        "source_timestamp": _iso(latest.occurred_at) if latest else None,
        "is_fallback": False,
        "projection_state": projection_state,
        "subject_scope": "execution_unit",
        "reconciliation_health": health,
    }


def project_execution_units(
    organization_id: int, unit_ids: Iterable[int]
) -> dict[int, dict]:
    """Batch-project tenant-owned units without reading or changing legacy state."""
    ids = set(unit_ids)
    if not ids:
        return {}
    units = db.session.scalars(
        select(ExecutionUnit)
        .join(Project, Project.id == ExecutionUnit.project_id)
        .where(ExecutionUnit.id.in_(ids), Project.organization_id == organization_id)
    ).all()
    unit_projects = {unit.id: unit.project_id for unit in units}
    unit_id_set = set(unit_projects)
    events_by_unit: dict[int, list[OperationalEvent]] = defaultdict(list)
    if unit_id_set:
        events = db.session.scalars(
            select(OperationalEvent).where(
                OperationalEvent.execution_unit_id.in_(unit_id_set),
            )
        ).all()
        for event in events:
            if event.project_id == unit_projects[event.execution_unit_id]:
                events_by_unit[event.execution_unit_id].append(event)
    return {
        unit.id: _unit_projection(unit, events_by_unit[unit.id]) for unit in units
    }


def project_operational_shipments(
    organization_id: int, shipment_ids: Iterable[int]
) -> dict[int, dict]:
    """Batch-project active units for tenant-owned OperationalShipments."""
    ids = set(shipment_ids)
    if not ids:
        return {}
    shipments = db.session.scalars(
        select(OperationalShipment).where(
            OperationalShipment.id.in_(ids),
            OperationalShipment.organization_id == organization_id,
        )
    ).all()
    valid_ids = {shipment.id for shipment in shipments}
    units = db.session.scalars(
        select(ExecutionUnit)
        .join(Project, Project.id == ExecutionUnit.project_id)
        .where(
            ExecutionUnit.operational_shipment_id.in_(valid_ids),
            ExecutionUnit.is_active.is_(True),
            Project.organization_id == organization_id,
        )
    ).all()
    unit_projections = project_execution_units(organization_id, (unit.id for unit in units))
    units_by_shipment: dict[int, list[dict]] = defaultdict(list)
    for unit in units:
        units_by_shipment[unit.operational_shipment_id].append(unit_projections[unit.id])

    result = {}
    for shipment in shipments:
        projected_units = units_by_shipment[shipment.id]
        known = [row for row in projected_units if row["current_location"] is not None]
        distinct_locations = {row["current_location"] for row in known}
        if not known:
            location_state = "UNAVAILABLE"
        elif len(projected_units) == 1 and len(known) == 1:
            location_state = "SINGLE"
        elif len(distinct_locations) == 1:
            location_state = "COMMON"
        else:
            location_state = "MULTIPLE"
        current_location = known[0]["current_location"] if location_state in {"SINGLE", "COMMON"} else None
        latest = max(
            (row for row in projected_units if row["latest_event_at"]),
            key=lambda row: (
                row["latest_event_at"],
                row["latest_event_recorded_at"],
                row["latest_event_public_id"],
            ),
            default=None,
        )
        health_states = {row["reconciliation_health"] for row in projected_units}
        if "CACHE_CONFLICT" in health_states:
            health = "CACHE_CONFLICT"
        elif "CACHE_STALE" in health_states:
            health = "CACHE_STALE"
        elif "CACHE_MISSING" in health_states:
            health = "CACHE_MISSING"
        elif health_states == {"NOT_APPLICABLE"} or not health_states:
            health = "NOT_APPLICABLE"
        else:
            health = "CONSISTENT"
        source = "operational_event" if any(row["source"] == "operational_event" for row in projected_units) else "unavailable"
        result[shipment.id] = {
            "current_location": current_location,
            "location_state": location_state,
            "unit_count": len(projected_units),
            "known_location_unit_count": len(known),
            "latest_event_at": latest["latest_event_at"] if latest else None,
            "latest_event_type": latest["latest_event_type"] if latest else None,
            "lifecycle_status": shipment.lifecycle_status,
            "source": source,
            "source_timestamp": latest["latest_event_at"] if latest else None,
            "is_fallback": False,
            "projection_state": "conflict" if health in {"CACHE_STALE", "CACHE_CONFLICT"} else ("authoritative" if source == "operational_event" else "unavailable"),
            "subject_scope": "operational_shipment",
            "reconciliation_health": health,
            "units": projected_units,
        }
    return result
