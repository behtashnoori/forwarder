"""Public tracking API routes for customers to track their requests."""
from flask import Blueprint, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from backend.extensions import db
from backend.models import (
    ShipmentRequest,
    Province,
    County,
    City,
    ExpertUser,
    ExpertQuote,
    AssignmentLog,
    ReferralAssignmentLog,
    ExpertConsoleLog,
)

public_tracking_bp = Blueprint("public_tracking", __name__, url_prefix="/api/public")

# Fixed 7 workflow steps (no email_verified). Order and completion derived from status.
WORKFLOW_STEP_DEFS = [
    {"name": "request_submitted", "order": 1, "title": "ارسال درخواست"},
    {"name": "expert_assigned", "order": 2, "title": "اختصاص کارشناس"},
    {"name": "expert_contacted", "order": 3, "title": "تماس کارشناس"},
    {"name": "quote_provided", "order": 4, "title": "ارائه پیشنهاد"},
    {"name": "contract_signed", "order": 5, "title": "امضای قرارداد"},
    {"name": "shipment_picked_up", "order": 6, "title": "تحویل مرسوله"},
    {"name": "shipment_delivered", "order": 7, "title": "تحویل به مقصد"},
]

# Status -> max completed step index (0-based). Steps 1..N are completed.
STATUS_TO_COMPLETED_UP_TO = {
    "new": 0,           # step 1 only
    "assigned": 1,      # 1,2
    "in_progress": 2,   # 1,2,3
    "quoted": 3,        # 1,2,3,4
    "waiting_for_customer": 3,  # 1,2,3,4
    "won": 6,           # all 7
    "lost": 1,          # 1,2
    "closed": 1,
    "cancelled": 1,
    "pending": 0,
}


def _workflow_steps_from_status(status: str, created_at, assigned_at=None, quote_created_at=None) -> list:
    """Build 7 workflow steps with is_completed and optional real completed_at."""
    max_completed = STATUS_TO_COMPLETED_UP_TO.get(status, 0)
    created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    steps = []
    for i, defn in enumerate(WORKFLOW_STEP_DEFS):
        is_completed = i <= max_completed
        completed_at = None
        if is_completed:
            if i == 0:
                completed_at = created_iso
            elif i == 1 and assigned_at:
                completed_at = assigned_at.isoformat() if hasattr(assigned_at, "isoformat") else str(assigned_at)
            elif i == 3 and quote_created_at:
                completed_at = quote_created_at.isoformat() if hasattr(quote_created_at, "isoformat") else str(quote_created_at)
            else:
                completed_at = created_iso
        steps.append({
            "name": defn["name"],
            "order": defn["order"],
            "title": defn["title"],
            "is_completed": is_completed,
            "completed_at": completed_at,
            "points_earned": 0,
        })
    return steps


def _resolve_request(identifier: str):
    """Resolve identifier (numeric id or tracking_code) to ShipmentRequest or None."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    if identifier.isdigit():
        return db.session.query(ShipmentRequest).filter(ShipmentRequest.id == int(identifier)).first()
    return db.session.query(ShipmentRequest).filter(ShipmentRequest.tracking_code == identifier).first()


def _get_assigned_at(req):
    """Return the earliest date when this request was assigned to an expert (from logs)."""
    dates = []
    first_al = (
        db.session.query(func.min(AssignmentLog.created_at))
        .filter(AssignmentLog.shipment_request_id == req.id)
        .scalar()
    )
    if first_al:
        dates.append(first_al)
    first_ral = (
        db.session.query(func.min(ReferralAssignmentLog.assigned_at))
        .filter(ReferralAssignmentLog.request_id == req.id)
        .scalar()
    )
    if first_ral:
        dates.append(first_ral)
    first_log = (
        db.session.query(func.min(ExpertConsoleLog.created_at))
        .filter(
            ExpertConsoleLog.shipment_request_id == req.id,
            ExpertConsoleLog.new_status == "assigned",
        )
        .scalar()
    )
    if first_log:
        dates.append(first_log)
    if not dates:
        return None
    return min(dates)


def _get_latest_quote(req):
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
    }


@public_tracking_bp.get("/track/<identifier>")
def get_public_tracking_info(identifier: str):
    """Get public tracking information by request id (numeric) or tracking_code."""
    try:
        req = _resolve_request(identifier)
        if not req:
            return jsonify({"message": "درخواست یافت نشد"}), 404

        # Tracking number for display: prefer tracking_code, fallback to legacy
        tracking_number = req.tracking_code if req.tracking_code else f"SR{req.id:06d}"

        # Location
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

        assigned_expert = None
        if req.assigned_to:
            exp = db.session.query(ExpertUser).filter(ExpertUser.id == req.assigned_to).first()
            if exp:
                assigned_expert = {
                    "id": exp.id,
                    "full_name": exp.full_name,
                    "phone": exp.phone or "",
                    "email": getattr(exp, "email", None) or "",
                }

        created_at = req.created_at
        created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)

        assigned_at = _get_assigned_at(req)
        assigned_at_iso = assigned_at.isoformat() if assigned_at and hasattr(assigned_at, "isoformat") else (str(assigned_at) if assigned_at else None)

        latest_quote = _get_latest_quote(req)

        def _date_iso(d):
            if d is None:
                return None
            return d.isoformat() if hasattr(d, "isoformat") else str(d)

        response_data = {
            "id": req.id,
            "tracking_number": tracking_number,
            "status": req.status or "new",
            "created_at": created_iso,
            "shipping_type": req.shipping_type or "domestic",
            "contact_phone": req.contact_phone,
            "customer_first_name": req.customer_first_name,
            "customer_last_name": req.customer_last_name,
            "route": {
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
            },
            "transport_method": req.transport_method,
            "domestic_transport_method": req.domestic_transport_method,
            "international_transport_method": req.international_transport_method,
            "transport_method_preference": req.transport_method_preference,
            "cargo_description": req.cargo_description,
            "cargo_weight": req.cargo_weight,
            "cargo_volume": req.cargo_volume,
            "cargo_value": req.cargo_value,
            "special_instructions": req.special_instructions,
            "pickup_date": _date_iso(req.pickup_date),
            "delivery_date": _date_iso(req.delivery_date),
            "assigned_expert": assigned_expert,
            "assigned_at": assigned_at_iso,
            "last_customer_touch_at": _date_iso(req.last_customer_touch_at),
            "latest_quote": latest_quote,
            "workflow_steps": _workflow_steps_from_status(
                req.status or "new",
                req.created_at,
                assigned_at=assigned_at,
                quote_created_at=latest_quote.get("created_at") if latest_quote else None,
            ),
        }
        return jsonify(response_data), 200

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in public tracking: {e}")
        return jsonify({"message": "خطا در دریافت اطلاعات"}), 500
    except Exception as e:
        current_app.logger.error(f"Error in public tracking: {e}")
        return jsonify({"message": "خطای داخلی سرور"}), 500
