"""Routes for shipment request creation."""
import traceback
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app

from backend.extensions import db
from backend.services import shipment_service

shipment_request_bp = Blueprint("shipment_request", __name__, url_prefix="/api")


@shipment_request_bp.get("/transport-methods")
def get_transport_methods():
    """Get available transport methods. Returns 200 with empty lists if table empty; 500 only on real DB errors."""
    try:
        return jsonify(shipment_service.get_transport_methods_payload())
    except Exception as e:
        current_app.logger.exception("Error fetching transport methods")
        traceback.print_exc()
        return (
            jsonify({
                "error": "خطا در دریافت روش‌های حمل",
                "message": str(e),
            }),
            500,
        )


@shipment_request_bp.post("/shipment-request")
def create_shipment_request():
    """Create a shipment request from public form submissions."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    canonical_submission = any(
        data.get(key) not in (None, "")
        for key in ("origin_country_id", "origin_international_city_id", "dest_country_id", "dest_international_city_id")
    )

    try:
        shipment_request = shipment_service.create_shipment_request(data, request.remote_addr)
    except shipment_service.ShipmentValidationError as e:
        body = {"message": e.message}
        if canonical_submission or e.code != "VALIDATION_FAILED":
            body["error"] = {"code": e.code, "message": e.message}
        return jsonify(body), e.status_code
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to create shipment request")
        current_app.logger.error(f"Error details: {str(e)}")
        return (
            jsonify({"message": f"خطای داخلی سرور: {str(e)}"}),
            500,
        )

    return jsonify(shipment_service.build_shipment_request_payload(shipment_request)), 201


@shipment_request_bp.get("/shipment-request/ping")
def ping():
    """Health check endpoint for the shipment request blueprint."""
    return jsonify({"message": "pong"})
