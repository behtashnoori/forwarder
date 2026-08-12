"""Service helpers for user-management assignment statistics endpoint."""
from __future__ import annotations

from typing import Any


def normalize_assignment_statistics(raw_stats: dict[str, Any]) -> dict[str, Any]:
    """Keep the current assignment engine statistics payload unchanged."""
    return raw_stats


def build_assignment_statistics_response_payload(raw_stats: dict[str, Any]) -> dict[str, Any]:
    """Build the current assignment statistics response payload."""
    return normalize_assignment_statistics(raw_stats)


def get_assignment_statistics_payload(context=None) -> dict[str, Any]:
    """Fetch assignment statistics from the current assignment engine."""
    if context is not None:
        from sqlalchemy import func
        from backend.extensions import db
        from backend.models import ShipmentRequest
        query = db.session.query(ShipmentRequest.status, func.count(ShipmentRequest.id)).filter(ShipmentRequest.operational_organization_id == context.organization_id, ShipmentRequest.ownership_scope == "TENANT").group_by(ShipmentRequest.status)
        return {"total_requests": sum(row[1] for row in query.all()), "by_status": {row[0]: row[1] for row in query.all()}}
    from backend.assignment_engine import assignment_engine

    raw_stats = assignment_engine.get_assignment_statistics()
    return build_assignment_statistics_response_payload(raw_stats)
