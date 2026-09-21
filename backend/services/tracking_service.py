"""Fail-closed public Request tracking capability resolution and projection."""
from __future__ import annotations

import re

from backend.extensions import db
from backend.models import City, County, Province, ShipmentRequest
from backend.quarantine import assert_instance_current, is_quarantined
from backend.services import timeline_service
from backend.services.legacy_datetime import serialize_legacy_utc_datetime
from backend.services.multi_unit_tracking_service import build_public_unit_tracking


# 16 random bytes encoded with URL-safe base64 (without padding) produce
# exactly 22 characters. The version prefix makes legacy weak capabilities
# fail closed without guessing their entropy or origin.
PUBLIC_TRACKING_CAPABILITY_PATTERN = re.compile(r"^SR2-[A-Za-z0-9_-]{22}$")


def normalize_public_tracking_capability(value: str | None) -> str | None:
    """Return one canonical ADR-052 capability or ``None`` without DB access."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not PUBLIC_TRACKING_CAPABILITY_PATTERN.fullmatch(normalized):
        return None
    return normalized


def resolve_request(identifier: str):
    """Resolve only an exact opaque public capability to one Request."""
    capability = normalize_public_tracking_capability(identifier)
    if capability is None:
        return None
    return (
        db.session.query(ShipmentRequest)
        .filter(ShipmentRequest.tracking_code == capability)
        .one_or_none()
    )


def build_route_summary(req: ShipmentRequest) -> dict:
    """Return bounded public geography labels without exact address data."""
    origin_province = None
    origin_county = None
    origin_city = None
    dest_province = None
    dest_county = None
    dest_city = None
    if req.shipping_type == "domestic":
        if req.origin_province_id:
            origin_province = db.session.get(Province, req.origin_province_id)
        if req.origin_county_id:
            origin_county = db.session.get(County, req.origin_county_id)
        if req.origin_city_id:
            origin_city = db.session.get(City, req.origin_city_id)
        if req.dest_province_id:
            dest_province = db.session.get(Province, req.dest_province_id)
        if req.dest_county_id:
            dest_county = db.session.get(County, req.dest_county_id)
        if req.dest_city_id:
            dest_city = db.session.get(City, req.dest_city_id)

    return {
        "origin": {
            "province": origin_province.name_fa if origin_province else None,
            "county": origin_county.name_fa if origin_county else None,
            "city": origin_city.name_fa if origin_city else None,
            "country": req.origin_country,
            "city_international": req.origin_city_international,
        },
        "destination": {
            "province": dest_province.name_fa if dest_province else None,
            "county": dest_county.name_fa if dest_county else None,
            "city": dest_city.name_fa if dest_city else None,
            "country": req.dest_country,
            "city_international": req.dest_city_international,
        },
    }


def build_tracking_response(req: ShipmentRequest) -> dict:
    """Build the exact ADR-052 public-safe Request tracking allowlist."""
    assigned_at = timeline_service.get_assigned_at(req)
    assigned_at_iso = (
        assigned_at.isoformat()
        if assigned_at is not None and hasattr(assigned_at, "isoformat")
        else str(assigned_at) if assigned_at is not None else None
    )
    return {
        "tracking_number": req.tracking_code,
        "status": req.status or "new",
        "created_at": serialize_legacy_utc_datetime(req.created_at),
        "shipping_type": req.shipping_type or "domestic",
        "route": build_route_summary(req),
        "transport_method": req.transport_method,
        "domestic_transport_method": req.domestic_transport_method,
        "international_transport_method": req.international_transport_method,
        "transport_method_preference": req.transport_method_preference,
        "assigned_at": assigned_at_iso,
        "workflow_steps_simple": timeline_service.build_workflow_steps_simple_4(
            req, assigned_at=assigned_at
        ),
        "unit_tracking": build_public_unit_tracking(req),
    }


def get_public_tracking_payload(identifier: str) -> dict | None:
    """Return one authorized public projection, or ``None`` non-disclosively."""
    req = resolve_request(identifier)
    if req is None or is_quarantined("ShipmentRequest", req.id):
        return None
    assert_instance_current(req, purpose="public-tracking-serialize")
    return build_tracking_response(req)
