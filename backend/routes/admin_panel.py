"""Admin panel routes for shipment request insights."""
from io import BytesIO

from flask import Blueprint, jsonify, request, current_app, send_file, g
from sqlalchemy.exc import IntegrityError
from backend.extensions import db
from backend.models import ShipmentRequest
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
from backend.services.admin_authorization_service import require_organization_admin_context, require_platform_admin
from backend.services import assignment_service
from backend.services.organization_hostname_service import (
    HostnameValidationError,
    create_hostname,
    list_hostnames,
    serialize_hostname,
    update_hostname,
)
from backend.referral_engine import referral_engine

admin_bp = Blueprint("admin_panel", __name__, url_prefix="/api/admin")


@admin_bp.get("/shipment-requests/<int:request_id>")
@require_organization_admin_context()
def get_shipment_request_detail(request_id: int):
    """Return a shipment request with human-readable location names."""
    payload = admin_shipment_request_service.get_admin_shipment_request_detail(request_id, getattr(g, "organization_context", None))

    if payload is None:
        return jsonify({"error": "درخواست موردنظر یافت نشد"}), 404

    return jsonify(payload)


@admin_bp.get("/shipment-requests")
@require_organization_admin_context()
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
        return jsonify(admin_shipment_request_service.list_admin_shipment_requests(request.args, getattr(g, "organization_context", None)))
    except admin_shipment_request_service.AdminShipmentRequestFilterError as e:
        return jsonify({"error": e.message}), e.status_code

    except Exception as e:
        current_app.logger.error(f"Error listing shipment requests: {e}")
        return jsonify({"error": "خطا در دریافت درخواست‌ها"}), 500


@admin_bp.get("/unassigned-requests")
@require_organization_admin_context(allow_platform=False)
def list_unassigned_requests():
    return jsonify(admin_shipment_request_service.list_unassigned_tenant_requests(g.organization_context))


@admin_bp.post("/shipment-requests/<int:request_id>/assign")
@require_organization_admin_context(allow_platform=False)
def assign_unassigned_request(request_id: int):
    try:
        return jsonify(assignment_service.assign_request_to_expert(
            request_id,
            payload=request.get_json(silent=True) or {},
            actor=get_current_user(),
            remote_addr=request.remote_addr,
            organization_context=g.organization_context,
        ))
    except assignment_service.AssignmentServiceError as exc:
        return jsonify({"error": exc.message}), exc.status_code


@admin_bp.post("/shipment-requests/<int:request_id>/auto-assign")
@require_organization_admin_context(allow_platform=False)
def auto_assign_unassigned_request(request_id: int):
    row = db.session.get(ShipmentRequest, request_id)
    if not row or row.ownership_scope != "TENANT" or row.operational_organization_id != g.organization_context.organization_id:
        return jsonify({"error": "Request not found"}), 404
    expert_id = referral_engine.auto_assign_request(request_id)
    db.session.commit()
    return jsonify({"assigned_expert_id": expert_id, "assigned": expert_id is not None})


@admin_bp.get("/organization-hostnames")
@require_organization_admin_context()
def get_organization_hostnames():
    organization_id = g.organization_context.organization_id if g.organization_context else None
    return jsonify({"hostnames": list_hostnames(organization_id)})


@admin_bp.post("/organization-hostnames")
@require_platform_admin()
def add_organization_hostname():
    try:
        return jsonify(serialize_hostname(create_hostname(request.get_json(silent=True) or {}))), 201
    except (HostnameValidationError, IntegrityError) as exc:
        db.session.rollback()
        message = str(exc) if isinstance(exc, HostnameValidationError) else "Hostname routing conflicts with an existing active mapping."
        return jsonify({"error": message}), 409 if isinstance(exc, IntegrityError) else 400


@admin_bp.patch("/organization-hostnames/<public_id>")
@require_platform_admin()
def change_organization_hostname(public_id: str):
    try:
        return jsonify(serialize_hostname(update_hostname(public_id, request.get_json(silent=True) or {})))
    except (HostnameValidationError, IntegrityError) as exc:
        db.session.rollback()
        message = str(exc) if isinstance(exc, HostnameValidationError) else "Hostname routing conflicts with an existing active mapping."
        return jsonify({"error": message}), 409 if isinstance(exc, IntegrityError) else 400


@admin_bp.get("/platform-intake")
@require_platform_admin()
def list_platform_intake():
    from backend.services.expert_request_list_service import build_request_list_item_payload
    rows = ShipmentRequest.query.filter(
        ShipmentRequest.ownership_scope == "INTAKE",
        ShipmentRequest.operational_organization_id.is_(None),
    ).order_by(ShipmentRequest.created_at.asc()).all()
    return jsonify({"requests": [build_request_list_item_payload(row) for row in rows], "total": len(rows)})


@admin_bp.post("/platform-intake/<int:request_id>/route")
@require_platform_admin()
def route_platform_intake(request_id: int):
    from backend.services.ownership_service import OwnershipContractError, route_intake_to_organization
    try:
        organization_id = int((request.get_json(silent=True) or {}).get("organization_id"))
        row = route_intake_to_organization(request_id, organization_id, get_current_user())
        expert_id = referral_engine.auto_assign_request(row.id)
        db.session.commit()
        return jsonify({
            "request_id": row.id, "operational_organization_id": row.operational_organization_id,
            "assigned_expert_id": expert_id,
        })
    except (TypeError, ValueError, OwnershipContractError) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 409


@admin_bp.get("/dashboard")
@require_organization_admin_context()
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
        return jsonify(admin_dashboard_service.get_admin_dashboard_payload(getattr(g, "organization_context", None)))
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin dashboard: {e}")
        return jsonify({"error": "خطا در دریافت آمار داشبورد"}), 500


@admin_bp.get("/reports/assignment-summary")
@require_organization_admin_context()
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
        return jsonify(admin_report_service.get_assignment_summary_payload(getattr(g, "organization_context", None)))
        
    except Exception as e:
        current_app.logger.error(f"Error generating assignment summary: {e}")
        return jsonify({"error": "خطا در تولید گزارش"}), 500


@admin_bp.get("/reports/overview")
@require_organization_admin_context()
def get_report_overview():
    """Return admin report overview JSON for a supported reporting period."""
    try:
        return jsonify(admin_report_overview_service.get_report_overview_payload(request.args.get("period"), getattr(g, "organization_context", None)))
    except admin_report_overview_service.AdminReportOverviewError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error generating report overview: {e}")
        return jsonify({"error": "خطا در تولید گزارش"}), 500


@admin_bp.get("/reports/export.xlsx")
@require_organization_admin_context()
def export_report_xlsx():
    """Return admin report overview as an XLSX workbook download."""
    try:
        workbook_bytes, filename = admin_report_xlsx_service.build_report_xlsx(request.args.get("period"), getattr(g, "organization_context", None))
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
@require_organization_admin_context()
def get_referral_rules():
    """List all referral rules ordered by priority ASC."""
    try:
        return jsonify(referral_service.list_referral_rules(context=getattr(g, "organization_context", None)))
    except Exception as e:
        current_app.logger.error(f"Error getting referral rules: {e}")
        return jsonify({"error": "خطا در دریافت قوانین ارجاع"}), 500


@admin_bp.post("/referral-rules")
@require_organization_admin_context()
def create_referral_rule():
    """Create a new referral rule."""
    try:
        payload = referral_service.create_referral_rule(request.get_json() or {}, get_current_user(), getattr(g, "organization_context", None))
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
@require_organization_admin_context()
def update_referral_rule(rule_id: int):
    """Update a referral rule."""
    try:
        return jsonify(referral_service.update_referral_rule(rule_id, request.get_json() or {}, getattr(g, "organization_context", None)))
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
@require_organization_admin_context()
def delete_referral_rule(rule_id: int):
    """Delete a referral rule and its state (logs kept for audit)."""
    try:
        return jsonify(referral_service.delete_referral_rule(rule_id, getattr(g, "organization_context", None)))
    except referral_service.ReferralServiceError as e:
        db.session.rollback()
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting referral rule: {e}")
        return jsonify({"error": "خطا در حذف قانون ارجاع"}), 500


@admin_bp.post("/referral-rules/preview")
@require_organization_admin_context()
def preview_referral_rule():
    """
    Preview which rule would match and which expert would be selected for a request.
    Body: { "request_id": number }. Does not change DB.
    """
    try:
        return jsonify(referral_service.preview_referral_assignment(request.get_json() or {}, getattr(g, "organization_context", None)))
    except referral_service.ReferralServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error in referral preview: {e}")
        return jsonify({"error": "خطا در پیش‌نمایش ارجاع"}), 500
