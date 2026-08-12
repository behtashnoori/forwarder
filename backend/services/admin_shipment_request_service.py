"""Service helpers for admin shipment request read endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import desc, or_
from sqlalchemy.orm import joinedload

from backend.models import City, County, Province, ShipmentRequest
from backend.services.legacy_datetime import serialize_legacy_utc_datetime
from backend.services.route_payload_service import build_iran_destination_payload


INVALID_DATE_ERROR = "\u0641\u0631\u0645\u062a \u062a\u0627\u0631\u06cc\u062e \u0646\u0627\u0645\u0639\u062a\u0628\u0631 \u0627\u0633\u062a"


class AdminShipmentRequestFilterError(Exception):
    """Raised when admin shipment request filters cannot be parsed."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AdminRequestFilters:
    """Normalized query parameters for the admin request list endpoint."""

    limit: int
    offset: int
    status: str | None
    transport_method: str | None
    province_id: int | None
    date_from: str | None
    date_to: str | None


def get_admin_shipment_request_detail(request_id: int, context=None) -> dict[str, Any] | None:
    """Return the existing admin shipment request detail payload."""
    query = ShipmentRequest.query.options(
        joinedload(ShipmentRequest.assigned_expert)
    ).filter(ShipmentRequest.id == request_id)
    if context is not None: query = query.filter(ShipmentRequest.operational_organization_id == context.organization_id, ShipmentRequest.ownership_scope == "TENANT")
    shipment_request = query.one_or_none()

    if shipment_request is None:
        return None

    return build_admin_request_detail_payload(shipment_request)


def list_admin_shipment_requests(args, context=None) -> dict[str, Any]:
    """Return the existing admin shipment request list payload."""
    filters = normalize_admin_request_filters(args)
    query = ShipmentRequest.query
    if context is not None: query = query.filter(ShipmentRequest.operational_organization_id == context.organization_id, ShipmentRequest.ownership_scope == "TENANT")
    query = apply_admin_request_filters(query, filters)

    total_count = query.count()
    shipment_requests = (
        query.order_by(desc(ShipmentRequest.created_at))
        .offset(filters.offset)
        .limit(filters.limit)
        .all()
    )

    location_lookups = build_location_lookups(shipment_requests)
    items = [
        build_admin_request_list_item_payload(req, location_lookups)
        for req in shipment_requests
    ]

    return build_admin_request_list_response_payload(items, filters, total_count)


def normalize_admin_request_filters(args) -> AdminRequestFilters:
    """Normalize query parameters while preserving current parsing behavior."""
    return AdminRequestFilters(
        limit=min(int(args.get("limit", 50)), 200),
        offset=int(args.get("offset", 0)),
        status=args.get("status"),
        transport_method=args.get("transport_method"),
        province_id=args.get("province_id", type=int),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
    )


def apply_admin_request_filters(query, filters: AdminRequestFilters):
    """Apply the current admin shipment request filters to a query."""
    if filters.status:
        query = query.filter(ShipmentRequest.status == filters.status)

    if filters.transport_method:
        query = query.filter(
            or_(
                ShipmentRequest.transport_method == filters.transport_method,
                ShipmentRequest.domestic_transport_method == filters.transport_method,
                ShipmentRequest.international_transport_method == filters.transport_method,
            )
        )

    if filters.province_id:
        query = query.filter(
            or_(
                ShipmentRequest.origin_province_id == filters.province_id,
                ShipmentRequest.dest_province_id == filters.province_id,
            )
        )

    if filters.date_from:
        try:
            date_from_obj = datetime.fromisoformat(filters.date_from.replace("Z", "+00:00"))
            query = query.filter(ShipmentRequest.created_at >= date_from_obj)
        except ValueError as exc:
            raise AdminShipmentRequestFilterError(INVALID_DATE_ERROR) from exc

    if filters.date_to:
        try:
            date_to_obj = datetime.fromisoformat(filters.date_to.replace("Z", "+00:00"))
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(ShipmentRequest.created_at <= date_to_obj)
        except ValueError as exc:
            raise AdminShipmentRequestFilterError(INVALID_DATE_ERROR) from exc

    return query


def build_admin_request_detail_payload(shipment_request: ShipmentRequest) -> dict[str, Any]:
    """Build the existing admin shipment request detail response shape."""
    origin_province = (
        Province.query.get(shipment_request.origin_province_id)
        if shipment_request.origin_province_id
        else None
    )
    origin_county = (
        County.query.get(shipment_request.origin_county_id)
        if shipment_request.origin_county_id
        else None
    )
    origin_city = (
        City.query.get(shipment_request.origin_city_id)
        if shipment_request.origin_city_id
        else None
    )

    dest_province = (
        Province.query.get(shipment_request.dest_province_id)
        if shipment_request.dest_province_id
        else None
    )
    dest_county = (
        County.query.get(shipment_request.dest_county_id)
        if shipment_request.dest_county_id
        else None
    )
    dest_city = (
        City.query.get(shipment_request.dest_city_id)
        if shipment_request.dest_city_id
        else None
    )

    assigned_expert = None
    if shipment_request.assigned_expert:
        assigned_expert = {
            "id": shipment_request.assigned_expert.id,
            "full_name": shipment_request.assigned_expert.full_name,
            "username": shipment_request.assigned_expert.username,
        }

    return {
        "id": shipment_request.id,
        "contact_phone": shipment_request.contact_phone,
        "customer_first_name": shipment_request.customer_first_name,
        "customer_last_name": shipment_request.customer_last_name,
        "transport_method": shipment_request.transport_method,
        "status": shipment_request.status,
        "priority": shipment_request.priority,
        "assigned_to": assigned_expert,
        "shipping_type": shipment_request.shipping_type,
        "origin": {
            "province": origin_province.name_fa if origin_province else None,
            "county": origin_county.name_fa if origin_county else None,
            "city": origin_city.name_fa if origin_city else None,
            "country": shipment_request.origin_country,
            "international_city": shipment_request.origin_city_international,
            "address": shipment_request.origin_address_international,
        },
        "destination": {
            "province": dest_province.name_fa if dest_province else None,
            "county": dest_county.name_fa if dest_county else None,
            "city": dest_city.name_fa if dest_city else None,
            "country": shipment_request.dest_country,
            "international_city": shipment_request.dest_city_international,
            "address": shipment_request.dest_address_international,
        },
        "iran_destination": build_iran_destination_payload(shipment_request),
        "created_at": (
            serialize_legacy_utc_datetime(shipment_request.created_at)
            if shipment_request.created_at
            else None
        ),
        "sla_due_at": (
            shipment_request.sla_due_at.isoformat()
            if shipment_request.sla_due_at
            else None
        ),
    }


def build_location_lookups(shipment_requests: list[ShipmentRequest]) -> dict[str, dict[int, str]]:
    """Fetch list endpoint location names in bulk using the current lookup behavior."""
    origin_province_ids = {
        req.origin_province_id for req in shipment_requests if req.origin_province_id
    }
    dest_province_ids = {
        req.dest_province_id for req in shipment_requests if req.dest_province_id
    }
    province_ids = origin_province_ids | dest_province_ids

    origin_county_ids = {
        req.origin_county_id for req in shipment_requests if req.origin_county_id
    }
    dest_county_ids = {
        req.dest_county_id for req in shipment_requests if req.dest_county_id
    }
    county_ids = origin_county_ids | dest_county_ids

    origin_city_ids = {
        req.origin_city_id for req in shipment_requests if req.origin_city_id
    }
    dest_city_ids = {
        req.dest_city_id for req in shipment_requests if req.dest_city_id
    }
    city_ids = origin_city_ids | dest_city_ids

    provinces = Province.query.filter(Province.id.in_(province_ids)).all() if province_ids else []
    counties = County.query.filter(County.id.in_(county_ids)).all() if county_ids else []
    cities = City.query.filter(City.id.in_(city_ids)).all() if city_ids else []

    return {
        "provinces": {p.id: p.name_fa for p in provinces},
        "counties": {c.id: c.name_fa for c in counties},
        "cities": {c.id: c.name_fa for c in cities},
    }


def build_admin_request_list_item_payload(
    req: ShipmentRequest,
    location_lookups: dict[str, dict[int, str]],
) -> dict[str, Any]:
    """Build one list item using the existing response shape."""
    province_lookup = location_lookups["provinces"]
    county_lookup = location_lookups["counties"]
    city_lookup = location_lookups["cities"]

    return {
        "id": req.id,
        "contact_phone": req.contact_phone,
        "customer_first_name": req.customer_first_name,
        "customer_last_name": req.customer_last_name,
        "transport_method": req.transport_method,
        "status": req.status,
        "priority": req.priority,
        "assigned_to": req.assigned_to,
        "shipping_type": req.shipping_type,
        "origin": {
            "province": province_lookup.get(req.origin_province_id),
            "county": county_lookup.get(req.origin_county_id),
            "city": city_lookup.get(req.origin_city_id),
            "country": req.origin_country,
            "international_city": req.origin_city_international,
            "address": req.origin_address_international,
        },
        "destination": {
            "province": province_lookup.get(req.dest_province_id),
            "county": county_lookup.get(req.dest_county_id),
            "city": city_lookup.get(req.dest_city_id),
            "country": req.dest_country,
            "international_city": req.dest_city_international,
            "address": req.dest_address_international,
        },
        "iran_destination": build_iran_destination_payload(req),
        "created_at": serialize_legacy_utc_datetime(req.created_at),
    }


def build_admin_request_list_response_payload(
    items: list[dict[str, Any]],
    filters: AdminRequestFilters,
    total_count: int,
) -> dict[str, Any]:
    """Build the admin shipment request list response payload."""
    return {
        "requests": items,
        "pagination": {
            "total": total_count,
            "limit": filters.limit,
            "offset": filters.offset,
            "has_more": filters.offset + filters.limit < total_count,
        },
    }
