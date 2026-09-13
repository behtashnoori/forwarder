"""Shared eligibility rules for expert shipment scopes."""
from __future__ import annotations

from typing import Any, Iterable, TypeVar

from sqlalchemy import select

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership

# The current PostgreSQL role contract and authority model have one ordinary
# operational role: expert.  Legacy business_expert references are not a
# valid role value for the governed database and must not receive this baseline.
EXPERT_ROLES = ("expert",)
# A normal active Expert is an operational user.  This baseline deliberately
# grants workflow capability, not tenant-wide visibility or administrative
# authority: endpoint guards and assigned-work policy remain authoritative.
EXPERT_BASELINE_OPERATIONAL_PERMISSIONS: tuple[str, ...] = (
    "execution_unit.create",
    "execution_unit.update",
    "operational_shipment.create",
    "operational_shipment.create_direct",
    "operational_shipment.create_from_quote",
    "operational_shipment.read",
    # These are bounded command permissions.  Tenant and assigned-work
    # authorization is still enforced by the shipment/execution services.
    "personal_dashboard.manage",
    "personal_dashboard.read",
)
T = TypeVar("T", bound=ExpertUser)


def is_expert_role(role: str | None) -> bool:
    return role in EXPERT_ROLES


def default_operational_permissions_for_role(role: str | None) -> list[str]:
    """Return the least-privilege operational permissions provisioned by role."""
    if is_expert_role(role):
        return list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS)
    return []


def merge_expert_baseline_permissions(permissions: Iterable[Any] | None) -> list[str]:
    """Return a deterministic, duplicate-free additive Expert permission set."""
    existing = {value for value in (permissions or []) if isinstance(value, str) and value}
    return sorted(existing | set(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS))


def reconcile_expert_baseline_permissions(*, apply: bool = False) -> dict[str, Any]:
    """Plan or apply additive baseline convergence for active Expert memberships.

    Inactive users/memberships and non-Expert roles are deliberately excluded.
    The caller owns transaction commit, making dry-run and apply explicit.
    """
    rows = db.session.execute(
        select(OperationalMembership, ExpertUser).join(
            ExpertUser, ExpertUser.id == OperationalMembership.user_id
        ).where(OperationalMembership.is_active.is_(True), ExpertUser.is_active.is_(True))
    ).all()
    changes: list[dict[str, Any]] = []
    skipped = 0
    for membership, user in rows:
        if not is_expert_role(user.role):
            skipped += 1
            continue
        merged = merge_expert_baseline_permissions(membership.permissions)
        current = sorted({value for value in (membership.permissions or []) if isinstance(value, str) and value})
        if merged == current:
            continue
        changes.append({
            "membership_id": membership.id,
            "organization_id": membership.organization_id,
            "user_id": user.id,
            "added_permissions": sorted(set(merged) - set(current)),
        })
        if apply:
            membership.permissions = merged
    return {
        "mode": "apply" if apply else "dry-run",
        "targeted_memberships": len(rows) - skipped,
        "skipped_non_expert_or_inactive": skipped,
        "changed_memberships": len(changes),
        "changes": changes,
    }


def can_handle_request(expert: ExpertUser, shipment_request: ShipmentRequest) -> bool:
    if not expert.is_active or not is_expert_role(expert.role):
        return False
    if shipment_request.shipping_type == "international":
        return bool(expert.can_handle_international)
    return bool(expert.can_handle_domestic)


def eligible_experts(experts: Iterable[T], shipment_request: ShipmentRequest) -> list[T]:
    return [expert for expert in experts if can_handle_request(expert, shipment_request)]
