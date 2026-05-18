"""Public tracking API routes for customers to track their requests."""
from flask import Blueprint, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from backend.services import timeline_service, tracking_service

public_tracking_bp = Blueprint("public_tracking", __name__, url_prefix="/api/public")

# Backward-compatible aliases for existing characterization tests and imports.
WORKFLOW_STEP_DEFS = timeline_service.WORKFLOW_STEP_DEFS
STATUS_TO_COMPLETED_UP_TO = timeline_service.STATUS_TO_COMPLETED_UP_TO
WORKFLOW_STEP_DEFS_SIMPLE_4 = timeline_service.WORKFLOW_STEP_DEFS_SIMPLE_4
_workflow_steps_from_status = timeline_service.build_workflow_steps_from_status
_get_final_decision_from_logs = timeline_service.get_final_decision_from_logs
_workflow_steps_simple_4 = timeline_service.build_workflow_steps_simple_4
_resolve_request = tracking_service.resolve_request
_get_assigned_at = timeline_service.get_assigned_at
_get_latest_quote = tracking_service.get_latest_quote


@public_tracking_bp.get("/track/<identifier>")
def get_public_tracking_info(identifier: str):
    """Get public tracking information by request id (numeric) or tracking_code."""
    try:
        response_data = tracking_service.get_public_tracking_payload(identifier)
        if not response_data:
            return jsonify({"message": "درخواست یافت نشد"}), 404
        return jsonify(response_data), 200

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in public tracking: {e}")
        return jsonify({"message": "خطا در دریافت اطلاعات"}), 500
    except Exception as e:
        current_app.logger.error(f"Error in public tracking: {e}")
        return jsonify({"message": "خطای داخلی سرور"}), 500
