"""Fail-closed assigned-work authorization for ADR-042/ADR-043.

This module is deliberately independent of HTTP input: tenant, parent, and
root are derived from persisted rows, never from client supplied identifiers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import false, or_, select

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment

PLATFORM_ADMIN = "PLATFORM_ADMIN"
ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
EXPERT = "EXPERT"

INTRINSIC_REQUEST_ACTIONS = frozenset({"request.read", "request.message", "request.quote", "request.status"})
INTRINSIC_SHIPMENT_ACTIONS = frozenset({"shipment.read", "route.read", "tracking.read", "document.read", "execution.read"})


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    organization_id: int | None = None
    root_type: str | None = None
    root_id: int | None = None


def _deny(reason: str) -> AuthorizationDecision:
    return AuthorizationDecision(False, reason)


def _authority(user: ExpertUser) -> str:
    value = (getattr(user, "authority", None) or EXPERT).upper()
    return value if value in {PLATFORM_ADMIN, ORGANIZATION_ADMIN, EXPERT} else EXPERT


def _membership(user_id: int) -> OperationalMembership | None:
    rows = db.session.scalars(select(OperationalMembership).join(
        OperationalOrganization, OperationalOrganization.id == OperationalMembership.organization_id
    ).where(OperationalMembership.user_id == user_id, OperationalMembership.is_active.is_(True), OperationalOrganization.is_active.is_(True))).all()
    return rows[0] if len(rows) == 1 else None


def _has_capability(membership: OperationalMembership, action: str) -> bool:
    # Action names are semantic; governed actions retain an explicit membership grant.
    aliases = {"shipment.read": "operational_shipment.read", "request.read": "request.read"}
    return aliases.get(action, action) in set(membership.permissions or [])


def _request_root(shipment: OperationalShipment) -> ShipmentRequest | None:
    if shipment.source_type != "accepted_quote" or shipment.shipment_request_id is None:
        return None
    request = db.session.get(ShipmentRequest, shipment.shipment_request_id)
    if request is None or request.operational_organization_id != shipment.organization_id:
        return None
    return request


def authorize_work_action(actor: dict[str, Any], resource: Any, action: str) -> AuthorizationDecision:
    """Evaluate one current operation; callers must not cache an allow decision."""
    user_id = actor.get("id")
    if not isinstance(user_id, int):
        return _deny("ACTIVE_IDENTITY_REQUIRED")
    user = db.session.get(ExpertUser, user_id)
    if user is None or not user.is_active:
        return _deny("ACTIVE_IDENTITY_REQUIRED")
    membership = _membership(user_id)
    if membership is None:
        return _deny("EXACTLY_ONE_ACTIVE_MEMBERSHIP_REQUIRED")
    authority = _authority(user)
    if authority == PLATFORM_ADMIN:
        return _deny("PLATFORM_ADMIN_HAS_NO_TENANT_WORK_AUTHORITY")

    if isinstance(resource, ShipmentRequest):
        if resource.operational_organization_id != membership.organization_id:
            return _deny("RESOURCE_TENANT_MISMATCH")
        if authority == ORGANIZATION_ADMIN:
            return AuthorizationDecision(_has_capability(membership, action), "ORG_ADMIN_CAPABILITY_REQUIRED", membership.organization_id, "ShipmentRequest", resource.id)
        if action not in INTRINSIC_REQUEST_ACTIONS:
            return _deny("EXPLICIT_GOVERNED_CAPABILITY_REQUIRED")
        if resource.assigned_to != user_id:
            return _deny("CURRENT_ROOT_ASSIGNMENT_REQUIRED")
        return AuthorizationDecision(True, "INTRINSIC_ASSIGNED_REQUEST", membership.organization_id, "ShipmentRequest", resource.id)

    if isinstance(resource, OperationalShipment):
        if resource.organization_id != membership.organization_id:
            return _deny("RESOURCE_TENANT_MISMATCH")
        if authority == ORGANIZATION_ADMIN:
            return AuthorizationDecision(_has_capability(membership, action), "ORG_ADMIN_CAPABILITY_REQUIRED", membership.organization_id, "OperationalShipment", resource.id)
        if action not in INTRINSIC_SHIPMENT_ACTIONS:
            return _deny("EXPLICIT_GOVERNED_CAPABILITY_REQUIRED")
        request = _request_root(resource)
        if request is not None:
            return AuthorizationDecision(request.assigned_to == user_id, "REQUEST_ROOT_ASSIGNMENT_REQUIRED", membership.organization_id, "ShipmentRequest", request.id)
        if resource.source_type == "direct" and resource.primary_responsible_expert_id == user_id:
            return AuthorizationDecision(True, "DIRECT_SHIPMENT_ROOT_ASSIGNMENT", membership.organization_id, "OperationalShipment", resource.id)
        return _deny("CERTIFIED_ROOT_ASSIGNMENT_REQUIRED")
    return _deny("RESOURCE_LINEAGE_NOT_CERTIFIED")


def assigned_request_scope(actor: dict[str, Any], action: str = "request.read"):
    """Return a SQL predicate before pagination/count; never post-filter rows."""
    user_id = actor.get("id")
    if not isinstance(user_id, int):
        return false()
    user = db.session.get(ExpertUser, user_id)
    membership = _membership(user_id)
    if user is None or not user.is_active or membership is None:
        return false()
    authority = _authority(user)
    base = ShipmentRequest.ownership_scope == "TENANT"
    tenant = ShipmentRequest.operational_organization_id == membership.organization_id
    if authority == EXPERT:
        return base & tenant & (ShipmentRequest.assigned_to == user_id)
    if authority == ORGANIZATION_ADMIN and _has_capability(membership, action):
        return base & tenant
    return false()


def assigned_shipment_scope(actor: dict[str, Any], action: str = "operational_shipment.read"):
    """Canonical OperationalShipment SQL scope, applied before pagination."""
    user_id = actor.get("id")
    if not isinstance(user_id, int):
        return false()
    user = db.session.get(ExpertUser, user_id)
    membership = _membership(user_id)
    if user is None or not user.is_active or membership is None:
        return false()
    tenant = OperationalShipment.organization_id == membership.organization_id
    authority = _authority(user)
    if authority == ORGANIZATION_ADMIN and _has_capability(membership, action):
        return tenant
    if authority != EXPERT:
        return false()
    request_assigned = OperationalShipment.source_type == "accepted_quote"
    request_assigned &= OperationalShipment.shipment_request_id.in_(select(ShipmentRequest.id).where(
        ShipmentRequest.operational_organization_id == membership.organization_id,
        ShipmentRequest.ownership_scope == "TENANT",
        ShipmentRequest.assigned_to == user_id,
    ))
    direct_assigned = (OperationalShipment.source_type == "direct") & (OperationalShipment.primary_responsible_expert_id == user_id)
    return tenant & or_(request_assigned, direct_assigned)
