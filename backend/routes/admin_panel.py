"""Admin panel routes for shipment request insights."""
from io import BytesIO

from flask import Blueprint, jsonify, request, current_app, send_file
from backend.extensions import db
from backend.security import require_role
from backend.auth import get_current_user
from backend.services import (
    admin_dashboard_service,
    admin_report_overview_service,
    admin_report_service,
    admin_report_xlsx_service,
    admin_shipment_request_service,
    referral_service,
)

admin_bp = Blueprint("admin_panel", __name__, url_prefix="/api/admin")


@admin_bp.get("/shipment-requests/<int:request_id>")
@require_role('admin')
def get_shipment_request_detail(request_id: int):
    """Return a shipment request with human-readable location names."""
    payload = admin_shipment_request_service.get_admin_shipment_request_detail(request_id)

    if payload is None:
        return jsonify({"error": "درخواست موردنظر یافت نشد"}), 404

    return jsonify(payload)


@admin_bp.get("/shipment-requests")
@require_role('admin')
def list_shipment_requests():
    """
    Return shipment requests with pagination and filtering.
    
    Query parameters:
    - limit: Number of results per page (default: 50, max: 200)
    - offset: Number of results to skip (default: 0)
    - status: Filter by status
    - transport_method: Filter by transport method
    - province_id: Filter by origin province
    - date_from: Filter from date (ISO format)
    - date_to: Filter to date (ISO format)
    """
    try:
        return jsonify(admin_shipment_request_service.list_admin_shipment_requests(request.args))
    except admin_shipment_request_service.AdminShipmentRequestFilterError as e:
        return jsonify({"error": e.message}), e.status_code

    except Exception as e:
        current_app.logger.error(f"Error listing shipment requests: {e}")
        return jsonify({"error": "خطا در دریافت درخواست‌ها"}), 500


@admin_bp.get("/dashboard")
@require_role('admin')
def get_admin_dashboard():
    """
    Get admin dashboard statistics.
    
    Returns:
    - total_requests: Total number of requests
    - requests_per_transport_method: Count by transport method
    - requests_per_status: Count by status
    - last_7_days_count: Requests created in last 7 days
    - top_provinces: Top 10 provinces by request count
    """
    try:
        return jsonify(admin_dashboard_service.get_admin_dashboard_payload())
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin dashboard: {e}")
        return jsonify({"error": "خطا در دریافت آمار داشبورد"}), 500


@admin_bp.get("/reports/assignment-summary")
@require_role('admin')
def get_assignment_summary():
    """
    Get comprehensive assignment summary report.
    
    Returns:
    - assignments_per_expert: List of experts with assignment stats
    - avg_response_time: Average time from assignment to first action
    - conversion_rate: Percentage of won requests
    - sla_violations: Count of SLA violations
    """
    try:
        return jsonify(admin_report_service.get_assignment_summary_payload())
        
    except Exception as e:
        current_app.logger.error(f"Error generating assignment summary: {e}")
        return jsonify({"error": "خطا در تولید گزارش"}), 500


@admin_bp.get("/reports/overview")
@require_role('admin')
def get_report_overview():
    """Return admin report overview JSON for a supported reporting period."""
    try:
        return jsonify(admin_report_overview_service.get_report_overview_payload(request.args.get("period")))
    except admin_report_overview_service.AdminReportOverviewError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error generating report overview: {e}")
        return jsonify({"error": "خطا در تولید گزارش"}), 500


@admin_bp.get("/reports/export.xlsx")
@require_role('admin')
def export_report_xlsx():
    """Return admin report overview as an XLSX workbook download."""
    try:
        workbook_bytes, filename = admin_report_xlsx_service.build_report_xlsx(request.args.get("period"))
        return send_file(
            BytesIO(workbook_bytes),
            mimetype=admin_report_xlsx_service.XLSX_MIME_TYPE,
            as_attachment=True,
            download_name=filename,
        )
    except admin_report_overview_service.AdminReportOverviewError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error exporting report XLSX: {e}")
        return jsonify({"error": "خطا در تولید خروجی گزارش"}), 500


# --- Referral rules (قوانین ارجاع) ---

@admin_bp.get("/referral-rules")
@require_role('admin')
def get_referral_rules():
    """List all referral rules ordered by priority ASC."""
    try:
        return jsonify(referral_service.list_referral_rules())
    except Exception as e:
        current_app.logger.error(f"Error getting referral rules: {e}")
        return jsonify({"error": "خطا در دریافت قوانین ارجاع"}), 500


@admin_bp.post("/referral-rules")
@require_role('admin')
def create_referral_rule():
    """Create a new referral rule."""
    try:
        payload = referral_service.create_referral_rule(request.get_json() or {}, get_current_user())
        return jsonify(payload), 201
    except referral_service.ReferralServiceError as e:
        db.session.rollback()
        return jsonify({"error": e.message}), e.status_code
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating referral rule: {e}")
        return jsonify({"error": "خطا در ایجاد قانون ارجاع"}), 500


@admin_bp.put("/referral-rules/<int:rule_id>")
@require_role('admin')
def update_referral_rule(rule_id: int):
    """Update a referral rule."""
    try:
        return jsonify(referral_service.update_referral_rule(rule_id, request.get_json() or {}))
    except referral_service.ReferralServiceError as e:
        db.session.rollback()
        return jsonify({"error": e.message}), e.status_code
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating referral rule: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی قانون ارجاع"}), 500


@admin_bp.delete("/referral-rules/<int:rule_id>")
@require_role('admin')
def delete_referral_rule(rule_id: int):
    """Delete a referral rule and its state (logs kept for audit)."""
    try:
        return jsonify(referral_service.delete_referral_rule(rule_id))
    except referral_service.ReferralServiceError as e:
        db.session.rollback()
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting referral rule: {e}")
        return jsonify({"error": "خطا در حذف قانون ارجاع"}), 500


@admin_bp.post("/referral-rules/preview")
@require_role('admin')
def preview_referral_rule():
    """
    Preview which rule would match and which expert would be selected for a request.
    Body: { "request_id": number }. Does not change DB.
    """
    try:
        return jsonify(referral_service.preview_referral_assignment(request.get_json() or {}))
    except referral_service.ReferralServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error in referral preview: {e}")
        return jsonify({"error": "خطا در پیش‌نمایش ارجاع"}), 500
