"""Service helpers for expert console request list responses."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from sqlalchemy import desc, or_

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.services.legacy_datetime import serialize_legacy_utc_datetime
from backend.services.route_payload_service import build_route_payload
from backend.services.ownership_service import tenant_organization_for_user


def normalize_request_list_filters(args: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize request list query args while preserving the current defaults."""
    return {
        "page": args.get("page", 1, type=int),
        "per_page": min(args.get("per_page", 20, type=int), 100),
        "status": args.get("status"),
        "assigned_to": args.get("assigned_to"),
        "priority": args.get("priority"),
        "search": args.get("search"),
        "sort_by": args.get("sort_by", "created_at"),
        "sort_order": args.get("sort_order", "desc"),
    }


def apply_request_list_visibility(query, user: dict[str, Any], filters: dict[str, Any]):
    """Apply the current admin/expert visibility rules to the list query."""
    organization_id = tenant_organization_for_user(user)
    query = query.filter(
        ShipmentRequest.ownership_scope == "TENANT",
        ShipmentRequest.operational_organization_id == organization_id,
    )
    if user.get("role") != "admin":
        return query.filter(ShipmentRequest.assigned_to == user["id"])
    if filters.get("assigned_to"):
        return query.filter(ShipmentRequest.assigned_to == filters["assigned_to"])
    return query


def apply_request_list_filters(query, filters: dict[str, Any]):
    """Apply current status, priority, search, and sort behavior."""
    status = filters.get("status")
    if status:
        if "," in status:
            status_list = [s.strip() for s in status.split(",")]
            query = query.filter(ShipmentRequest.status.in_(status_list))
        else:
            query = query.filter(ShipmentRequest.status == status)

    priority = filters.get("priority")
    if priority:
        query = query.filter(ShipmentRequest.priority == priority)

    search = filters.get("search")
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                ShipmentRequest.contact_phone.like(search_term),
                ShipmentRequest.customer_first_name.like(search_term),
                ShipmentRequest.customer_last_name.like(search_term),
                ShipmentRequest.cargo_description.like(search_term),
            )
        )

    sort_by = filters.get("sort_by")
    if sort_by == "created_at":
        sort_column = ShipmentRequest.created_at
    elif sort_by == "sla_due_at":
        sort_column = ShipmentRequest.sla_due_at
    elif sort_by == "priority":
        sort_column = ShipmentRequest.priority
    else:
        sort_column = ShipmentRequest.created_at

    if filters.get("sort_order") == "desc":
        return query.order_by(desc(sort_column))
    return query.order_by(sort_column)


def build_request_list_item_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build the current request list item payload."""
    assigned_expert = db.session.query(ExpertUser).get(req.assigned_to) if req.assigned_to else None

    sla_status = "on_time"
    if req.sla_due_at:
        if datetime.utcnow() > req.sla_due_at:
            sla_status = "overdue"
        elif datetime.utcnow() + timedelta(hours=2) > req.sla_due_at:
            sla_status = "due_soon"

    return {
        "id": req.id,
        "public_id": req.public_id,
        "tracking_number": req.tracking_code if getattr(req, "tracking_code", None) else f"SR{req.id:06d}",
        "status": req.status,
        "priority": req.priority,
        "created_at": serialize_legacy_utc_datetime(req.created_at),
        "sla_due_at": req.sla_due_at.isoformat() if req.sla_due_at else None,
        "sla_status": sla_status,
        "assigned_to": {
            "id": assigned_expert.id,
            "name": assigned_expert.full_name,
        } if assigned_expert else None,
        "customer": {
            "name": f"{req.customer_first_name or ''} {req.customer_last_name or ''}".strip() or "نامشخص",
            "phone": req.contact_phone,
        },
        "route": build_route_payload(req),
        "transport_method": req.transport_method,
        "international_transport_method": req.international_transport_method,
        "domestic_transport_method": req.domestic_transport_method,
        "transport_method_preference": req.transport_method_preference,
        "cargo": {
            "description": req.cargo_description,
            "weight": req.cargo_weight,
            "volume": req.cargo_volume,
            "value": req.cargo_value,
        },
        "has_unread": req.has_unread_for_assignee,
    }


def build_request_list_response_payload(items, pagination, filters: dict[str, Any]) -> dict[str, Any]:
    """Build the current request list response payload."""
    return {
        "requests": [build_request_list_item_payload(req) for req in items],
        "pagination": {
            "page": filters["page"],
            "per_page": filters["per_page"],
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    }


def list_expert_requests(user: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
    """Return the current filtered and paginated expert request list payload."""
    query = db.session.query(ShipmentRequest)
    query = apply_request_list_visibility(query, user, filters)
    query = apply_request_list_filters(query, filters)
    pagination = query.paginate(
        page=filters["page"],
        per_page=filters["per_page"],
        error_out=False,
    )
    return build_request_list_response_payload(pagination.items, pagination, filters)
