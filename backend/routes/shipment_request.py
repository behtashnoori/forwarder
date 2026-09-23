"""Routes for shipment request creation."""
import traceback
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app

from backend.extensions import db
from backend.services import shipment_service
from backend.services.customer_portal_auth import current_customer
from backend.services.customer_portal_auth import SESSION_CSRF
from backend.security import security
from flask import session

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


@shipment_request_bp.get("/request-cargo-options")
def get_request_cargo_options():
    """Return active governed references safe for optional Customer intake."""
    try:
        return jsonify(shipment_service.get_request_cargo_options_payload())
    except Exception as e:
        current_app.logger.exception("Error fetching Request Cargo options")
        return jsonify({"error": "Unable to load Request Cargo options", "message": str(e)}), 500


@shipment_request_bp.post("/shipment-request")
def create_shipment_request():
    """Create a shipment request from public form submissions."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    canonical_submission = any(
        data.get(key) not in (None, "")
        for key in ("origin_country_id", "origin_international_city_id", "dest_country_id", "dest_international_city_id")
    )
    customer = current_customer()
    if customer is not None:
        supplied = request.headers.get("X-CSRF-Token", "")
        expected = session.get(SESSION_CSRF, "")
        if not supplied or not expected or not security.verify_csrf_token(supplied, expected):
            return jsonify({"code": "CSRF_FAILED", "message": "CSRF validation failed."}), 403

    try:
        shipment_request = shipment_service.create_shipment_request(
            data, request.remote_addr, request.host,
            gamification_customer_id=customer.id if customer is not None else None,
        )
    except shipment_service.ShipmentValidationError as e:
        body = {"message": e.message}
        if canonical_submission or e.code != "VALIDATION_FAILED":
            body["error"] = {"code": e.code, "message": e.message}
            if e.fields:
                body["error"]["fields"] = e.fields
        return jsonify(body), e.status_code
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to create shipment request")
        current_app.logger.error(f"Error details: {str(e)}")
        return (
            jsonify({"message": f"خطای داخلی سرور: {str(e)}"}),
            500,
        )

    payload = shipment_service.build_shipment_request_payload(shipment_request)
    if customer is not None:
        payload.update({
            "request_public_id": shipment_request.public_id,
            "customer_workspace_path": f"/customer/requests/{shipment_request.public_id}",
        })
    return jsonify(payload), 201


@shipment_request_bp.get("/shipment-request/ping")
def ping():
    """Health check endpoint for the shipment request blueprint."""
    return jsonify({"message": "pong"})
