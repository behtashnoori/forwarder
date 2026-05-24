"""Service helpers for admin dashboard metrics."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func

from backend.extensions import db
from backend.models import Province, ShipmentRequest


def get_admin_dashboard_payload() -> dict[str, Any]:
    """Return the current admin dashboard metrics payload."""
    return build_admin_dashboard_metrics()


def build_admin_dashboard_metrics() -> dict[str, Any]:
    """Build the admin dashboard metrics using the existing query behavior."""
    total_requests = ShipmentRequest.query.count()

    requests_per_transport_method = build_transport_method_summary()
    requests_per_status = build_status_summary()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    last_7_days_count = ShipmentRequest.query.filter(
        ShipmentRequest.created_at >= seven_days_ago
    ).count()

    top_provinces = build_top_provinces_payload()

    one_day_ago = datetime.utcnow() - timedelta(days=1)
    last_24h_count = ShipmentRequest.query.filter(
        ShipmentRequest.created_at >= one_day_ago
    ).count()

    unassigned_count = ShipmentRequest.query.filter(
        and_(
            ShipmentRequest.assigned_to.is_(None),
            ShipmentRequest.status.in_(["new", "pending"]),
        )
    ).count()

    return {
        "total_requests": total_requests,
        "requests_per_transport_method": requests_per_transport_method,
        "requests_per_status": requests_per_status,
        "last_7_days_count": last_7_days_count,
        "last_24h_count": last_24h_count,
        "unassigned_count": unassigned_count,
        "top_provinces": top_provinces,
    }


def build_transport_method_summary() -> dict[str, int]:
    """Return request counts grouped by the current transport method expression."""
    transport_method_stats = db.session.query(
        func.coalesce(
            func.coalesce(
                ShipmentRequest.domestic_transport_method,
                ShipmentRequest.international_transport_method,
            ),
            ShipmentRequest.transport_method,
            "unknown",
        ).label("method"),
        func.count(ShipmentRequest.id).label("count"),
    ).group_by("method").all()

    return {stat.method: stat.count for stat in transport_method_stats}


def build_status_summary() -> dict[str, int]:
    """Return request counts grouped by status."""
    status_stats = db.session.query(
        ShipmentRequest.status,
        func.count(ShipmentRequest.id).label("count"),
    ).group_by(ShipmentRequest.status).all()

    return {stat.status: stat.count for stat in status_stats}


def build_top_provinces_payload() -> list[dict[str, Any]]:
    """Return the current top-origin-provinces payload."""
    top_provinces_query = (
        db.session.query(
            Province.name_fa,
            func.count(ShipmentRequest.id).label("count"),
        )
        .join(
            ShipmentRequest,
            ShipmentRequest.origin_province_id == Province.id,
        )
        .group_by(Province.id, Province.name_fa)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )

    return [
        {"province": prov.name_fa, "count": prov.count}
        for prov in top_provinces_query
    ]
