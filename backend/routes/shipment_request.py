"""Routes for shipment request creation."""
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import ShipmentRequest, ShipmentRequestLog

shipment_request_bp = Blueprint("shipment_request", __name__, url_prefix="/api")

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

    # Customer details (optional)
    customer_first_name = data.get("customer_first_name", "").strip() or None
    customer_last_name = data.get("customer_last_name", "").strip() or None

    transport_method_raw = data.get("transport_method") or data.get("shipment_mode")
    transport_method = None
    if isinstance(transport_method_raw, str):
        sanitized = transport_method_raw.strip()
        if sanitized:
            transport_method = sanitized.lower()

    # Process cargo details (optional)
    cargo_description = data.get("cargo_description", "").strip() or None
    cargo_weight = data.get("cargo_weight")
    cargo_volume = data.get("cargo_volume")
    cargo_value = data.get("cargo_value")
    special_instructions = data.get("special_instructions", "").strip() or None
    pickup_date = data.get("pickup_date")
    delivery_date = data.get("delivery_date")

    # Convert numeric fields
    if cargo_weight is not None:
        try:
            cargo_weight = float(cargo_weight)
        except (ValueError, TypeError):
            cargo_weight = None

    if cargo_volume is not None:
        try:
            cargo_volume = float(cargo_volume)
        except (ValueError, TypeError):
            cargo_volume = None

    if cargo_value is not None:
        try:
            cargo_value = float(cargo_value)
        except (ValueError, TypeError):
            cargo_value = None

    # Convert date fields
    pickup_date_obj = None
    delivery_date_obj = None
    if pickup_date:
        try:
            pickup_date_obj = datetime.strptime(pickup_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pickup_date_obj = None

    if delivery_date:
        try:
            delivery_date_obj = datetime.strptime(delivery_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            delivery_date_obj = None

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
            customer_first_name=customer_first_name,
            customer_last_name=customer_last_name,
            transport_method=transport_method,
            cargo_description=cargo_description,
            cargo_weight=cargo_weight,
            cargo_volume=cargo_volume,
            cargo_value=cargo_value,
            special_instructions=special_instructions,
            pickup_date=pickup_date_obj,
            delivery_date=delivery_date_obj,
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
        current_app.logger.exception("Failed to create shipment request")
        return (
            jsonify({"message": "خطای داخلی سرور رخ داده است. لطفاً بعداً تلاش کنید."}),
            500,
        )

    return (
        jsonify(
            {
                "message": "درخواست شما ثبت شد. کارشناسان ما ظرف دو ساعت با شما تماس خواهند گرفت.",
                "id": shipment_request.id,
            }
        ),
        201,
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
