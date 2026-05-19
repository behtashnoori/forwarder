"""Service helpers for user-management transport method endpoints."""
from __future__ import annotations

from typing import Any

from backend.extensions import db
from backend.models import TransportMethod


def normalize_transport_method_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep current route payload semantics while centralizing the handoff."""
    return payload


def build_transport_method_payload(method: TransportMethod) -> dict[str, Any]:
    """Build the current transport method response item shape."""
    return {
        "id": method.id,
        "name": method.name,
        "name_fa": method.name_fa,
        "description": method.description,
        "is_active": method.is_active,
        "created_at": method.created_at.isoformat(),
    }


def list_transport_methods() -> list[dict[str, Any]]:
    """List active transport methods in the current name_fa order."""
    transport_methods = db.session.query(TransportMethod).filter(
        TransportMethod.is_active == True
    ).order_by(TransportMethod.name_fa).all()
    return [build_transport_method_payload(method) for method in transport_methods]


def create_transport_method(payload: dict[str, Any] | None) -> TransportMethod:
    """Create and commit a transport method using the existing field defaults."""
    data = normalize_transport_method_payload(payload)
    transport_method = TransportMethod(
        name=data.get("name"),
        name_fa=data.get("name_fa"),
        description=data.get("description"),
        is_active=data.get("is_active", True),
    )

    db.session.add(transport_method)
    db.session.commit()
    return transport_method
