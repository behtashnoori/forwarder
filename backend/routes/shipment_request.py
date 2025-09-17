"""Routes for shipment request creation."""
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import ShipmentRequest, ShipmentRequestLog

shipment_request_bp = Blueprint("shipment_request", __name__, url_prefix="/api")

VALID_TRANSPORT_METHODS = {
    "road",
    "rail",
    "sea",
    "combined",
    "road-sea",
    "rail-sea",
    "multi-modal",
}


@shipment_request_bp.post("/shipment-request")
def create_shipment_request():
    """Create a shipment request from public form submissions."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        origin_province_id = int(data["origin_province_id"])
        origin_county_id = int(data["origin_county_id"])
        origin_city_id = int(data["origin_city_id"])
        dest_province_id = int(data["dest_province_id"])
        dest_county_id = int(data["dest_county_id"])
        dest_city_id = int(data["dest_city_id"])
    except (KeyError, TypeError, ValueError):
        return (
            jsonify({"message": "اطلاعات مبدا و مقصد نامعتبر است."}),
            400,
        )

    contact_phone = data.get("contact_phone", "")
    if not _is_valid_phone(contact_phone):
        return (
            jsonify({
                "message": "شماره تماس نامعتبر است. لطفاً شماره‌ای با پیش‌شماره 09 و ۱۱ رقم وارد کنید.",
            }),
            400,
        )

    transport_method = data.get("transport_method")
    if transport_method not in VALID_TRANSPORT_METHODS:
        return (
            jsonify({
                "message": "روش حمل انتخاب‌شده نامعتبر است.",
            }),
            400,
        )

    timestamp = datetime.utcnow()

    try:
        shipment_request = ShipmentRequest(
            origin_province_id=origin_province_id,
            origin_county_id=origin_county_id,
            origin_city_id=origin_city_id,
            dest_province_id=dest_province_id,
            dest_county_id=dest_county_id,
            dest_city_id=dest_city_id,
            contact_phone=contact_phone,
            transport_method=transport_method,
            created_at=timestamp,
            ready_at=timestamp,
            status_request_status="new",
        )
        db.session.add(shipment_request)
        db.session.flush()

        log_entry = ShipmentRequestLog(
            shipment_request_id=shipment_request.id,
            created_at=timestamp,
            note="ثبت اولیه درخواست",
            ip_address=request.remote_addr,
        )
        db.session.add(log_entry)
        db.session.commit()
    except (SQLAlchemyError, Exception):
        db.session.rollback()
        return (
            jsonify({"message": "خطای داخلی سرور رخ داده است. لطفاً بعداً تلاش کنید."}),
            500,
        )

    return (
        jsonify(
            {
                "message": "درخواست شما ثبت شد. کارشناسان ما ظرف دو ساعت با شما تماس خواهند گرفت.",
            }
        ),
        200,
    )


@shipment_request_bp.get("/shipment-request/ping")
def ping():
    """Health check endpoint for the shipment request blueprint."""
    return jsonify({"message": "pong"})


def _is_valid_phone(phone: str) -> bool:
    """Validate Iranian mobile phone number format."""
    if not isinstance(phone, str):
        return False
    return phone.startswith("09") and len(phone) == 11 and phone.isdigit()
