"""Canonical, read-only expert workload projection.

This service defines the user-facing operational workload only. Referral
capacity and least-workload deliberately retain their broader compatibility
semantics until an Accepted ADR authorizes a strategy change.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership


DISPLAYED_ACTIVE_STATUSES = frozenset({"assigned", "in_progress"})
REFERRAL_ACTIVE_STATUSES = frozenset(
    {"assigned", "in_progress", "quoted", "waiting_for_customer"}
)


def organization_workloads(
    organization_id: int, expert_user_ids: Iterable[int] | None = None
) -> dict[int, int]:
    """Return active operational request counts, tenant-fenced and batched."""
    membership_query = db.session.query(OperationalMembership.user_id).filter(
        OperationalMembership.organization_id == organization_id,
        OperationalMembership.is_active.is_(True),
    )
    requested_ids = {int(value) for value in expert_user_ids or []}
    if requested_ids:
        membership_query = membership_query.filter(
            OperationalMembership.user_id.in_(requested_ids)
        )
    member_ids = [row[0] for row in membership_query.all()]
    result = {user_id: 0 for user_id in member_ids}
    if not member_ids:
        return result
    rows = (
        db.session.query(ShipmentRequest.assigned_to, func.count(ShipmentRequest.id))
        .join(ExpertUser, ExpertUser.id == ShipmentRequest.assigned_to)
        .filter(
            ShipmentRequest.operational_organization_id == organization_id,
            ShipmentRequest.ownership_scope == "TENANT",
            ShipmentRequest.assigned_to.in_(member_ids),
            ShipmentRequest.status.in_(DISPLAYED_ACTIVE_STATUSES),
            ExpertUser.is_active.is_(True),
        )
        .group_by(ShipmentRequest.assigned_to)
        .all()
    )
    result.update({expert_id: count for expert_id, count in rows})
    return result


def workload_payload(organization_id: int, expert: ExpertUser, active_count: int) -> dict:
    """Build an explainable public projection without exposing tenant identity."""
    return {
        "active_count": active_count,
        "included_statuses": sorted(DISPLAYED_ACTIVE_STATUSES),
        "unit": "REQUEST",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
