"""Tenant-fenced ShipmentRequest opaque identity resolution."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from backend.extensions import db
from backend.models import ShipmentRequest


def canonical_uuid4(value: object) -> str | None:
    """Return canonical lowercase UUID v4 text, otherwise fail closed."""
    if not isinstance(value, str) or len(value) != 36:
        return None
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None
    canonical = str(parsed)
    if parsed.version != 4 or value != canonical:
        return None
    return canonical


def resolve_tenant_request_by_public_id(
    trusted_organization_id: int,
    public_id: object,
) -> ShipmentRequest | None:
    """Resolve a TENANT request inside trusted scope; grant no authorization."""
    if (
        isinstance(trusted_organization_id, bool)
        or not isinstance(trusted_organization_id, int)
        or trusted_organization_id <= 0
    ):
        return None
    canonical = canonical_uuid4(public_id)
    if canonical is None:
        return None
    return db.session.scalar(
        select(ShipmentRequest).where(
            ShipmentRequest.public_id == canonical,
            ShipmentRequest.ownership_scope == "TENANT",
            ShipmentRequest.operational_organization_id == trusted_organization_id,
        )
    )
