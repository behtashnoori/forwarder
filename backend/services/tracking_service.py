"""Read helpers for public tracking response assembly."""
from backend.extensions import db
from backend.models import City, County, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.services import timeline_service
from backend.services.multi_unit_tracking_service import build_public_unit_tracking


def resolve_request(identifier: str):
    """Resolve identifier (numeric id or tracking_code) to ShipmentRequest or None."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    if identifier.isdigit():
        return db.session.query(ShipmentRequest).filter(ShipmentRequest.id == int(identifier)).first()
    return db.session.query(ShipmentRequest).filter(ShipmentRequest.tracking_code == identifier).first()


def get_latest_quote(req):
    """Return the latest quote for this request, or None."""
    row = (
        db.session.query(ExpertQuote)
        .filter(ExpertQuote.shipment_request_id == req.id)
        .order_by(ExpertQuote.created_at.desc())
        .first()
    )
    if not row:
        return None
    created_by_name = None
    if row.created_by_expert:
        created_by_name = row.created_by_expert.full_name
    return {
        "id": row.id,
        "amount": int(row.amount) if row.amount is not None else None,
        "currency": row.currency or "IRR",
        "note": row.note,
        "valid_until": row.valid_until.isoformat() if row.valid_until else None,
        "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
        "created_by": created_by_name,
        "customer_response": row.customer_response,
        "responded_at": row.responded_at.isoformat() if row.responded_at else None,
    }


def date_iso(value):
    """Return an ISO-like string for date/datetime values while preserving existing fallbacks."""
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def build_assigned_expert(req):
    """Return assigned expert public summary, or None."""
    if not req.assigned_to:
        return None
    exp = db.session.query(ExpertUser).filter(ExpertUser.id == req.assigned_to).first()
    if not exp:
        return None
    return {
        "id": exp.id,
        "full_name": exp.full_name,
        "phone": exp.phone or "",
        "email": getattr(exp, "email", None) or "",
    }


def build_route_summary(req):
    """Return public origin/destination route summary for a shipment request."""
    origin_province = None
    origin_county = None
    origin_city = None
    dest_province = None
    dest_county = None
    dest_city = None
    if req.shipping_type == "domestic":
        if req.origin_province_id:
            origin_province = db.session.query(Province).filter(Province.id == req.origin_province_id).first()
        if req.origin_county_id:
            origin_county = db.session.query(County).filter(County.id == req.origin_county_id).first()
        if req.origin_city_id:
            origin_city = db.session.query(City).filter(City.id == req.origin_city_id).first()
        if req.dest_province_id:
            dest_province = db.session.query(Province).filter(Province.id == req.dest_province_id).first()
        if req.dest_county_id:
            dest_county = db.session.query(County).filter(County.id == req.dest_county_id).first()
        if req.dest_city_id:
            dest_city = db.session.query(City).filter(City.id == req.dest_city_id).first()

    return {
        "origin": {
            "province": origin_province.name_fa if origin_province else None,
            "county": origin_county.name_fa if origin_county else None,
            "city": origin_city.name_fa if origin_city else None,
            "country": req.origin_country,
            "city_international": req.origin_city_international,
            "address": getattr(req, "origin_address_international", None),
        },
        "destination": {
            "province": dest_province.name_fa if dest_province else None,
            "county": dest_county.name_fa if dest_county else None,
            "city": dest_city.name_fa if dest_city else None,
            "country": req.dest_country,
            "city_international": req.dest_city_international,
            "address": getattr(req, "dest_address_international", None),
        },
    }


def build_tracking_response(req, *, include_unit_tracking: bool = False):
    """Build the public tracking response payload for a shipment request."""
    tracking_number = req.tracking_code if req.tracking_code else f"SR{req.id:06d}"

    created_at = req.created_at
    created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)

    assigned_at = timeline_service.get_assigned_at(req)
    assigned_at_iso = assigned_at.isoformat() if assigned_at and hasattr(assigned_at, "isoformat") else (str(assigned_at) if assigned_at else None)

    latest_quote = get_latest_quote(req)

    response = {
        "id": req.id,
        "tracking_number": tracking_number,
        "status": req.status or "new",
        "created_at": created_iso,
        "shipping_type": req.shipping_type or "domestic",
        "contact_phone": req.contact_phone,
        "customer_first_name": req.customer_first_name,
        "customer_last_name": req.customer_last_name,
        "route": build_route_summary(req),
        "transport_method": req.transport_method,
        "domestic_transport_method": req.domestic_transport_method,
        "international_transport_method": req.international_transport_method,
        "transport_method_preference": req.transport_method_preference,
        "cargo_description": req.cargo_description,
        "cargo_weight": req.cargo_weight,
        "cargo_volume": req.cargo_volume,
        "cargo_value": req.cargo_value,
        "special_instructions": req.special_instructions,
        "pickup_date": date_iso(req.pickup_date),
        "delivery_date": date_iso(req.delivery_date),
        "assigned_expert": build_assigned_expert(req),
        "assigned_at": assigned_at_iso,
        "last_customer_touch_at": date_iso(req.last_customer_touch_at),
        "latest_quote": latest_quote,
        "workflow_steps": timeline_service.build_workflow_steps_from_status(
            req.status or "new",
            req.created_at,
            assigned_at=assigned_at,
            quote_created_at=latest_quote.get("created_at") if latest_quote else None,
        ),
        "workflow_steps_simple": timeline_service.build_workflow_steps_simple_4(req, assigned_at=assigned_at),
    }
    if include_unit_tracking:
        response["unit_tracking"] = build_public_unit_tracking(req)
    return response


def get_public_tracking_payload(identifier: str):
    """Return the public tracking payload for an identifier, or None when not found."""
    req = resolve_request(identifier)
    if not req:
        return None
    normalized_identifier = (identifier or "").strip()
    include_unit_tracking = bool(req.tracking_code and normalized_identifier == req.tracking_code)
    return build_tracking_response(req, include_unit_tracking=include_unit_tracking)
