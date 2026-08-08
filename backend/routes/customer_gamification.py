"""Routes for customer gamification and email verification."""
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app

from backend.services import customer_gamification_service

customer_gamification_bp = Blueprint("customer_gamification", __name__, url_prefix="/api/customer")


@customer_gamification_bp.post("/register")
def register_customer():
    """Register a new customer for gamification tracking."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    payload, status_code = customer_gamification_service.register_customer(data)
    return jsonify(payload), status_code


@customer_gamification_bp.get("/verify-email")
def verify_email():
    """Verify customer email with token."""
    token = request.args.get("token")
    payload, status_code = customer_gamification_service.verify_customer_email(token)
    return jsonify(payload), status_code


@customer_gamification_bp.get("/profile/<int:customer_id>")
def get_customer_profile(customer_id: int):
    """Get customer profile with gamification data."""
    try:
        payload = customer_gamification_service.get_customer_profile_payload(customer_id)
        if payload is None:
            return jsonify({"message": "مشتری یافت نشد"}), 404

        return jsonify(payload), 200

    except Exception as e:
        current_app.logger.error(f"Error getting customer profile: {e}")
        return jsonify({"message": "خطا در دریافت اطلاعات مشتری"}), 500


@customer_gamification_bp.get("/workflow/<int:customer_id>")
def get_customer_workflow(customer_id: int):
    """Get customer workflow steps and request detail for a specific request."""
    request_id_arg = request.args.get("request_id")
    if not request_id_arg:
        return jsonify({"message": "شناسه درخواست الزامی است"}), 400
    try:
        request_id = int(request_id_arg)
    except (TypeError, ValueError):
        return jsonify({"message": "شناسه درخواست نامعتبر است"}), 400

    try:
        payload = customer_gamification_service.get_customer_workflow_payload(customer_id, request_id)
        if payload is None:
            return jsonify({"message": "درخواست یافت نشد یا به این مشتری تعلق ندارد"}), 404

        return jsonify(payload), 200

    except Exception as e:
        current_app.logger.error(f"Error getting customer workflow: {e}")
        return jsonify({"message": "خطا در دریافت گردش کار"}), 500


@customer_gamification_bp.post("/quote-response/<tracking_code>")
def respond_to_quote(tracking_code: str):
    """Record a customer's accept/decline on the latest quote for one of their requests."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    payload, status_code = customer_gamification_service.record_quote_response(
        tracking_code, data.get("response"), request.remote_addr
    )
    return jsonify(payload), status_code


@customer_gamification_bp.post("/complete-step")
def complete_workflow_step():
    """Mark a workflow step as completed."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    payload, status_code = customer_gamification_service.complete_customer_workflow_step(data)
    return jsonify(payload), status_code


@customer_gamification_bp.get("/leaderboard")
def get_leaderboard():
    """Get customer leaderboard based on loyalty points."""
    try:
        return jsonify(customer_gamification_service.list_leaderboard_payload()), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting leaderboard: {e}")
        return jsonify({"message": "خطا در دریافت جدول امتیازات"}), 500
