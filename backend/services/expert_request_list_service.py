"""Service helpers for expert console request list responses."""
from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy import desc, or_

from backend.extensions import db
from backend.models import City, County, ExpertUser, Province, ShipmentRequest
from backend.services import sla_policy_service


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
            query = query.filter(
                or_(
                    ShipmentRequest.status.in_(status_list),
                    ShipmentRequest.status_request_status.in_(status_list),
                )
            )
        else:
            query = query.filter(
                or_(
                    ShipmentRequest.status == status,
                    ShipmentRequest.status_request_status == status,
                )
            )

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
    origin_province = db.session.query(Province).get(req.origin_province_id)
    origin_county = db.session.query(County).get(req.origin_county_id)
    origin_city = db.session.query(City).get(req.origin_city_id)
    dest_province = db.session.query(Province).get(req.dest_province_id)
    dest_county = db.session.query(County).get(req.dest_county_id)
    dest_city = db.session.query(City).get(req.dest_city_id)
    assigned_expert = db.session.query(ExpertUser).get(req.assigned_to) if req.assigned_to else None

    sla_status = sla_policy_service.calculate_request_sla_status(req)

    return {
        "id": req.id,
        "tracking_number": req.tracking_code if getattr(req, "tracking_code", None) else f"SR{req.id:06d}",
        "status": req.status,
        "priority": req.priority,
        "created_at": req.created_at.isoformat(),
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
        "route": {
            "origin": {
                "province": origin_province.name_fa if origin_province else "نامشخص",
                "county": origin_county.name_fa if origin_county else "نامشخص",
                "city": origin_city.name_fa if origin_city else "نامشخص",
            },
            "destination": {
                "province": dest_province.name_fa if dest_province else "نامشخص",
                "county": dest_county.name_fa if dest_county else "نامشخص",
                "city": dest_city.name_fa if dest_city else "نامشخص",
            },
        },
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
