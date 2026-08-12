"""Canonical MT-1 ownership transitions and fail-closed write guards."""
from __future__ import annotations

from backend.extensions import db
from backend.models import DocumentAuditEvent, ShipmentRequest
from backend.services.operational_service import organization_for_user


class OwnershipContractError(ValueError):
    """A write would create or mutate an ambiguous/cross-tenant resource."""


def tenant_organization_for_user(user: dict) -> int:
    if not user or user.get("id") is None:
        raise OwnershipContractError("A tenant-owned write requires an authenticated organization member")
    try:
        return organization_for_user(int(user["id"]))
    except Exception as exc:
        raise OwnershipContractError("Exactly one active Organization is required") from exc


def require_tenant_resource(resource, *, expected_organization_id: int | None = None) -> int:
    organization_id = getattr(resource, "operational_organization_id", None)
    if getattr(resource, "ownership_scope", None) != "TENANT" or organization_id is None:
        raise OwnershipContractError("Resource is not explicit tenant-owned business data")
    if expected_organization_id is not None and organization_id != expected_organization_id:
        raise OwnershipContractError("Cross-tenant relationship is forbidden")
    return int(organization_id)


def accept_intake_for_tenant(request_id: int, user: dict) -> ShipmentRequest:
    """Explicit INTAKE -> TENANT transition; assignment is intentionally irrelevant."""
    organization_id = tenant_organization_for_user(user)
    row = db.session.get(ShipmentRequest, request_id)
    if row is None:
        raise OwnershipContractError("Shipment request was not found")
    if row.ownership_scope == "TENANT" and row.operational_organization_id == organization_id:
        return row
    if row.ownership_scope != "INTAKE" or row.operational_organization_id is not None:
        raise OwnershipContractError("Only an unowned INTAKE request can be accepted")
    row.ownership_scope = "TENANT"
    row.operational_organization_id = organization_id
    for relationship in ("logs", "expert_logs", "expert_messages", "expert_notifications", "referral_assignment_logs"):
        for child in getattr(row, relationship, ()):
            child.operational_organization_id = organization_id
    if row.shipment_tracking is not None:
        row.shipment_tracking.operational_organization_id = organization_id
        for unit in row.shipment_tracking.units:
            unit.ownership_scope = "TENANT"
            unit.operational_organization_id = organization_id
            for update in unit.updates:
                update.ownership_scope = "TENANT"
                update.operational_organization_id = organization_id
    db.session.add(DocumentAuditEvent(
        scope_type="TENANT",
        operational_organization_id=organization_id,
        event_type="shipment_intake_accepted",
        actor_id=int(user["id"]),
        shipment_request_id=row.id,
        details="Explicit authenticated INTAKE to TENANT acceptance",
    ))
    db.session.flush()
    return row
