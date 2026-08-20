"""User management API routes for CRM hierarchy system."""
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, current_app, g
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from backend.extensions import db
from backend.models import (
    ExpertUser, ExpertSpecialization, AssignmentRule, AssignmentLog,
    ExpertConsoleLog, ExpertConsoleMessage, ExpertConsoleNotification,
    ShipmentRequest, Opportunity, Activity, Task, Report,
)
from backend.auth import require_auth, get_current_user
from backend.security import require_role, validate_input, sanitize_input
from backend.services import (
    assignment_rule_service,
    assignment_service,
    assignment_statistics_service,
    transport_method_service,
    user_delete_service,
    user_service,
)
from backend.services.admin_authorization_service import require_organization_admin_context, require_platform_admin

user_management_bp = Blueprint("user_management", __name__, url_prefix="/api/user-management")


# Transport Methods Management (admin only for consistency with user management panel)
@user_management_bp.get("/transport-methods")
@require_organization_admin_context()
def get_transport_methods():
    """Get all transport methods."""
    try:
        methods_data = transport_method_service.list_transport_methods()
        
        return jsonify({
            "transport_methods": methods_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting transport methods: {e}")
        return jsonify({"error": "خطا در دریافت روش‌های حمل"}), 500


@user_management_bp.post("/transport-methods")
@require_platform_admin()
def create_transport_method():
    """Create a new transport method."""
    try:
        data = request.get_json()
        transport_method = transport_method_service.create_transport_method(data)
        
        return jsonify({
            "message": "روش حمل با موفقیت ایجاد شد",
            "transport_method_id": transport_method.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating transport method: {e}")
        return jsonify({"error": "خطا در ایجاد روش حمل"}), 500


# User Management (admin only)
@user_management_bp.get("/users")
@require_organization_admin_context()
def get_users():
    """Get all users with hierarchy information."""
    try:
        users_data = user_service.list_users_payload(getattr(g, "organization_context", None))
        
        return jsonify({
            "users": users_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting users: {e}")
        return jsonify({"error": "خطا در دریافت کاربران"}), 500


@user_management_bp.post("/users")
@require_organization_admin_context()
def create_user():
    """Create a new user."""
    try:
        data = request.get_json()
        user = user_service.create_user(data, getattr(g, "organization_context", None))
        
        return jsonify({
            "message": "کاربر با موفقیت ایجاد شد",
            "user_id": user.id
        }), 201

    except user_service.UserValidationError as e:
        return jsonify({"error": e.message}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "ایمیل تکراری است یا قبلاً استفاده شده است."}), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {e}", exc_info=True)
        err_msg = "خطا در ایجاد کاربر"
        if current_app.debug or current_app.config.get("TESTING"):
            err_msg += f": {str(e)}"
        return jsonify({"error": err_msg}), 500


@user_management_bp.get("/users/<int:user_id>")
@require_organization_admin_context()
def get_user(user_id: int):
    try:
        user = user_service.get_user_or_raise(user_id, getattr(g, "organization_context", None))
        context = getattr(g, "organization_context", None)
        if context is not None:
            from backend.services.expert_workload_service import organization_workloads, workload_payload
            counts = organization_workloads(context.organization_id, [user.id])
            workload = workload_payload(context.organization_id, user, counts.get(user.id, 0))
        else:
            workload = None
        return jsonify({"user": user_service.build_user_payload(user, workload=workload)})
    except user_service.UserNotFoundError:
        return jsonify({"error": "User not found"}), 404


@user_management_bp.put("/users/<int:user_id>")
@require_organization_admin_context()
def update_user(user_id: int):
    """Update user information."""
    try:
        data = request.get_json()
        user_service.update_user(user_id, data, getattr(g, "organization_context", None))
        
        return jsonify({
            "message": "اطلاعات کاربر به‌روزرسانی شد"
        })
        
    except user_service.UserNotFoundError:
        return jsonify({"error": "کاربر یافت نشد"}), 404
    except user_service.UserValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی کاربر"}), 500


@user_management_bp.delete("/users/<int:user_id>")
@require_organization_admin_context()
def delete_user(user_id: int):
    """
    Delete an expert user and all related data.
    Only admin can delete. Cannot delete self. Cannot delete other admins (only experts/supervisors/etc).
    """
    try:
        current_user = get_current_user()
        payload = user_delete_service.delete_user_with_cleanup(user_id, current_user, getattr(g, "organization_context", None))
        return jsonify(payload)

    except user_delete_service.DeleteAuthenticationRequired:
        return jsonify({"error": "احراز هویت نشده"}), 401
    except user_delete_service.SelfDeleteNotAllowed:
        return jsonify({"error": "امکان حذف حساب خودتان وجود ندارد"}), 400
    except user_delete_service.DeleteTargetNotFound:
        return jsonify({"error": "کاربر یافت نشد"}), 404
    except user_delete_service.AdminDeleteNotAllowed:
        return jsonify({"error": "امکان حذف کاربر با نقش مدیر وجود ندارد"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {e}", exc_info=True)
        return jsonify({"error": "خطا در حذف کاربر"}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {e}", exc_info=True)
        return jsonify({"error": "خطا در حذف کاربر"}), 500


# Assignment Rules Management (admin only for consistency)
@user_management_bp.get("/assignment-rules")
@require_organization_admin_context()
def get_assignment_rules():
    """Get all assignment rules."""
    try:
        rules_data = assignment_rule_service.list_assignment_rules(getattr(g, "organization_context", None))
        
        return jsonify({
            "assignment_rules": rules_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting assignment rules: {e}")
        return jsonify({"error": "خطا در دریافت قوانین ارجاع"}), 500


@user_management_bp.post("/assignment-rules")
@require_organization_admin_context()
def create_assignment_rule():
    """Create a new assignment rule."""
    try:
        current_user = get_current_user()
        data = request.get_json()
        rule = assignment_rule_service.create_assignment_rule(data, current_user.get("id"), getattr(g, "organization_context", None))
        
        return jsonify({
            "message": "قانون ارجاع با موفقیت ایجاد شد",
            "rule_id": rule.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating assignment rule: {e}")
        return jsonify({"error": "خطا در ایجاد قانون ارجاع"}), 500


@user_management_bp.put("/assignment-rules/<int:rule_id>")
@require_organization_admin_context()
def update_assignment_rule(rule_id: int):
    """Update an assignment rule."""
    try:
        existing_rule = assignment_rule_service.get_assignment_rule_or_none(rule_id, getattr(g, "organization_context", None))
        if not existing_rule:
            return jsonify({"error": "قانون ارجاع یافت نشد"}), 404

        data = request.get_json()
        rule = assignment_rule_service.update_assignment_rule(rule_id, data, getattr(g, "organization_context", None))
        if not rule:
            return jsonify({"error": "قانون ارجاع یافت نشد"}), 404
        
        return jsonify({
            "message": "قانون ارجاع به‌روزرسانی شد"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating assignment rule: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی قانون ارجاع"}), 500


# Assignment Statistics (admin only)
@user_management_bp.get("/assignment-statistics")
@require_organization_admin_context()
def get_assignment_statistics():
    """Get assignment statistics."""
    try:
        stats = assignment_statistics_service.get_assignment_statistics_payload(getattr(g, "organization_context", None))
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error getting assignment statistics: {e}")
        return jsonify({"error": "خطا در دریافت آمار ارجاع"}), 500


# Manual Assignment (admin only)
@user_management_bp.post("/manual-assignment")
@require_organization_admin_context()
def manual_assignment():
    """Manually assign a request to an expert."""
    try:
        payload = assignment_service.manual_assign_request(
            request.get_json(silent=True) or {},
            actor=get_current_user(),
            remote_addr=request.remote_addr,
            organization_context=getattr(g, "organization_context", None),
        )
        return jsonify(payload)

    except assignment_service.AssignmentServiceError as e:
        return jsonify({"error": e.message}), e.status_code

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in manual assignment: {e}")
        return jsonify({"error": "خطا در ارجاع دستی"}), 500


@user_management_bp.get("/ping")
def ping():
    """Health check endpoint for user management API."""
    return jsonify({"message": "User Management API is running"})
