"""Governed Operational Shipment Population v1.

This authority deliberately separates authenticated assignment visibility from
the route-envelope window.  It returns a composable SQL statement; consumers
apply bounded pagination only after the deterministic ordering defined here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from backend.operational_models import OperationalShipment, RouteLeg, RoutePlan
from backend.services.assigned_work_authorization import assigned_shipment_scope
from backend.services.operational_service import OperationalError, organization_for_user


VISIBILITY_POLICY = "SHIPMENT_OPERATIONAL_ASSIGNED"
SUPPORTED_STATUSES = frozenset({"planned", "in_progress", "completed", "cancelled", "closed"})


@dataclass(frozen=True)
class OperationalWindow:
    """Inclusive requested window, normalized to UTC before construction."""

    from_: datetime | None = None
    to: datetime | None = None

    def __post_init__(self):
        for field, value in (("from_", self.from_), ("to", self.to)):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise OperationalError(
                    "OFFSET_AWARE_DATETIME_REQUIRED",
                    "Operational window timestamps must include a UTC offset.",
                    422,
                )
            if value is not None:
                object.__setattr__(self, field, value.astimezone(timezone.utc))
        if self.from_ is not None and self.to is not None and self.from_ > self.to:
            raise OperationalError(
                "INVALID_OPERATIONAL_WINDOW",
                "Operational window start must not be after its end.",
                422,
            )


def parse_transport_datetime(value: str | None, field: str) -> datetime | None:
    """Compatibility adapter for legacy date/date-time query parameters.

    Date-only and naive values historically reached this endpoint.  They are
    interpreted explicitly as UTC at this transport boundary; the governed
    internal contract never receives a naive datetime.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise OperationalError(
            "INVALID_OPERATIONAL_WINDOW",
            f"{field} must be an ISO-8601 timestamp.",
            422,
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _route_envelope_subqueries():
    active_plan = (
        select(RoutePlan.id)
        .where(
            RoutePlan.operational_shipment_id == OperationalShipment.id,
            RoutePlan.is_active.is_(True),
        )
        .correlate(OperationalShipment)
        .scalar_subquery()
    )
    first_departure = (
        select(RouteLeg.planned_departure)
        .where(RouteLeg.route_plan_id == active_plan)
        .order_by(RouteLeg.sequence_number.asc())
        .limit(1)
        .correlate(OperationalShipment)
        .scalar_subquery()
    )
    final_arrival = (
        select(RouteLeg.planned_arrival)
        .where(RouteLeg.route_plan_id == active_plan)
        .order_by(RouteLeg.sequence_number.desc())
        .limit(1)
        .correlate(OperationalShipment)
        .scalar_subquery()
    )
    return first_departure, final_arrival


def route_envelope_columns():
    """Public composable route-envelope expressions for governed consumers."""
    return _route_envelope_subqueries()


def operational_shipment_population(user, *, status: str | None = None, window: OperationalWindow | None = None):
    """Build the authorized, route-based Operational Shipment population."""
    organization_id = organization_for_user(int(user["id"]))
    if status is not None and status not in SUPPORTED_STATUSES:
        raise OperationalError("INVALID_SHIPMENT_STATUS", "Shipment status is unsupported.", 422)
    window = window or OperationalWindow()
    first_departure, final_arrival = _route_envelope_subqueries()
    statement = select(OperationalShipment).where(
        OperationalShipment.organization_id == organization_id,
        assigned_shipment_scope(user),
        first_departure.is_not(None),
        final_arrival.is_not(None),
    )
    if status is not None:
        statement = statement.where(OperationalShipment.lifecycle_status == status)
    # Inclusive interval overlap: envelope end >= requested start and envelope
    # start <= requested end.  Sequence, never timestamp MIN/MAX, owns bounds.
    if window.from_ is not None:
        statement = statement.where(final_arrival >= window.from_)
    if window.to is not None:
        statement = statement.where(first_departure <= window.to)
    return statement.order_by(
        OperationalShipment.created_at.desc(), OperationalShipment.public_id.asc()
    )
