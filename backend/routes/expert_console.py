"""Expert console API routes."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, current_app, g
from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import (
    ShipmentRequest, ShipmentRequestLog, ExpertUser,
    ExpertConsoleLog, ExpertConsoleMessage, ExpertConsoleNotification, ExpertQuote
)
from backend.auth import auth_manager, login_required, get_current_user
from backend.security import require_auth, validate_input, sanitize_input
from backend.cache import cache_manager, performance_monitor
from backend.services import (
    assignment_service,
    expert_request_detail_service,
    expert_request_list_service,
    message_service,
    notification_service,
    quote_service,
    multi_unit_tracking_service,
)

expert_console_bp = Blueprint("expert_console", __name__, url_prefix="/api/expert")


def _parse_tracking_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise multi_unit_tracking_service.TrackingValidationError(f"{field} is required")
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise multi_unit_tracking_service.TrackingValidationError(
            f"{field} must be an ISO-8601 datetime"
        ) from exc


def _tracking_target(request_id: int, current_user: Optional[Dict]):
    req = db.session.get(ShipmentRequest, request_id)
    if not req:
        return None, (jsonify({"error": "shipment request not found"}), 404)
    if not _can_access_request(req, current_user):
        return None, (jsonify({"error": "access denied"}), 403)
    return req, None


def _tracking_management_payload(req: ShipmentRequest) -> Dict[str, Any]:
    tracking = req.shipment_tracking
    return {
        "eligible": req.status in multi_unit_tracking_service.TRACKING_ELIGIBLE_REQUEST_STATUSES
        and bool(req.tracking_code),
        "request_status": req.status,
        "tracking_code": req.tracking_code,
        "enabled": bool(tracking and tracking.is_enabled),
        "unit_tracking": multi_unit_tracking_service.build_public_unit_tracking(req),
    }


def _can_access_request(req: ShipmentRequest, current_user: Optional[Dict]) -> bool:
    """Admin can access any request; non-admin only if they are the assignee."""
    if not current_user:
        return False
    if current_user.get("role") == "admin":
        return True
    return req.assigned_to == current_user.get("id")


@expert_console_bp.get("/requests")
@require_auth
def get_shipment_requests():
    """Get filtered and paginated shipment requests for expert console."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "احراز هویت نشده"}), 401

        filters = expert_request_list_service.normalize_request_list_filters(request.args)
        response_payload = expert_request_list_service.list_expert_requests(current_user, filters)
        return jsonify(response_payload)

    except Exception as e:
        current_app.logger.error(f"Error getting shipment requests: {e}")
        return jsonify({"error": "خطا در دریافت درخواست‌ها"}), 500


@expert_console_bp.get("/requests/<int:request_id>")
@require_auth
def get_shipment_request_detail(request_id: int):
    """Get detailed information about a specific shipment request."""
    try:
        current_user = get_current_user()
        response_payload = expert_request_detail_service.get_expert_request_detail(request_id, current_user)
        return jsonify(response_payload)
    except expert_request_detail_service.ExpertRequestDetailServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error getting shipment request detail: {e}")
        return jsonify({"error": "خطا در دریافت جزئیات درخواست"}), 500


@expert_console_bp.get("/requests/<int:request_id>/tracking")
@require_auth
def get_multi_unit_tracking(request_id: int):
    current_user = get_current_user()
    req, error = _tracking_target(request_id, current_user)
    if error:
        return error
    return jsonify(_tracking_management_payload(req)), 200


@expert_console_bp.post("/requests/<int:request_id>/tracking/enable")
@require_auth
def enable_multi_unit_tracking(request_id: int):
    current_user = get_current_user()
    req, error = _tracking_target(request_id, current_user)
    if error:
        return error
    try:
        multi_unit_tracking_service.enable_tracking(req, current_user["id"])
        db.session.commit()
        return jsonify(_tracking_management_payload(req)), 200
    except multi_unit_tracking_service.TrackingValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to enable multi-unit tracking")
        return jsonify({"error": "tracking could not be enabled"}), 500


@expert_console_bp.post("/requests/<int:request_id>/tracking/units")
@require_auth
def create_tracking_unit(request_id: int):
    current_user = get_current_user()
    req, error = _tracking_target(request_id, current_user)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        if not req.shipment_tracking:
            raise multi_unit_tracking_service.TrackingValidationError("tracking is not enabled")
        multi_unit_tracking_service.add_unit(
            req.shipment_tracking,
            current_user["id"],
            unit_code=data.get("unit_code"),
            unit_type=data.get("unit_type"),
            display_name=data.get("display_name"),
            sort_order=data.get("sort_order", 0),
        )
        db.session.commit()
        return jsonify(_tracking_management_payload(req)), 201
    except multi_unit_tracking_service.TrackingValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to create tracking unit")
        return jsonify({"error": "tracking unit could not be created"}), 409


@expert_console_bp.post("/requests/<int:request_id>/tracking/units/<int:unit_id>/updates")
@require_auth
def create_tracking_unit_update(request_id: int, unit_id: int):
    current_user = get_current_user()
    req, error = _tracking_target(request_id, current_user)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    unit = db.session.get(multi_unit_tracking_service.ShipmentTransportUnit, unit_id)
    if not unit or not req.shipment_tracking or unit.tracking_id != req.shipment_tracking.id:
        return jsonify({"error": "tracking unit not found"}), 404
    try:
        multi_unit_tracking_service.add_update(
            unit,
            current_user["id"],
            status=data.get("status"),
            location=data.get("location"),
            customer_message=data.get("customer_message"),
            internal_note=data.get("internal_note"),
            is_customer_visible=data.get("is_customer_visible", True),
            occurred_at=_parse_tracking_datetime(data.get("occurred_at"), "occurred_at"),
        )
        db.session.commit()
        return jsonify(_tracking_management_payload(req)), 201
    except multi_unit_tracking_service.TrackingValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to append tracking update")
        return jsonify({"error": "tracking update could not be created"}), 500


@expert_console_bp.post("/requests/<int:request_id>/assign")
@require_auth
def assign_request(request_id: int):
    """Assign a shipment request to an expert. Only admin can assign (or reassign)."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "احراز هویت نشده"}), 401

        response_payload = assignment_service.assign_request_to_expert(
            request_id,
            actor=current_user,
            payload=request.get_json() or {},
            remote_addr=request.remote_addr,
        )
        return jsonify(response_payload)
    except assignment_service.AssignmentServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning request: {e}")
        return jsonify({"error": "خطا در ارجاع درخواست"}), 500


@expert_console_bp.post("/requests/<int:request_id>/status")
@require_auth
def update_request_status(request_id: int):
    """Update the status of a shipment request."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "احراز هویت نشده"}), 401
        data = request.get_json() or {}
        new_status = data.get("status")
        note = data.get("note", "")
        
        if not new_status:
            return jsonify({"error": "وضعیت جدید الزامی است"}), 400
        
        # Validate status
        valid_statuses = ["new", "assigned", "in_progress", "quoted", "waiting_for_customer", "won", "lost", "closed"]
        if new_status not in valid_statuses:
            return jsonify({"error": "وضعیت نامعتبر است"}), 400
        
        req = db.session.query(ShipmentRequest).get(request_id)
        if not req:
            return jsonify({"error": "درخواست یافت نشد"}), 404
        if not _can_access_request(req, current_user):
            return jsonify({"error": "شما به این درخواست دسترسی ندارید"}), 403
        
        old_status = req.status
        
        # Update request
        req.status = new_status
        req.has_unread_for_assignee = True
        
        # Set SLA due date for new requests
        if new_status == "assigned" and not req.sla_due_at:
            req.sla_due_at = datetime.utcnow() + timedelta(hours=2)  # 2 hour SLA
        
        # Create log entry
        log = ExpertConsoleLog(
            shipment_request_id=request_id,
            expert_user_id=req.assigned_to,
            action="status_change",
            old_status=old_status,
            new_status=new_status,
            note=note,
            ip_address=request.remote_addr,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        
        # Create notification if assigned
        if req.assigned_to:
            notification = ExpertConsoleNotification(
                expert_user_id=req.assigned_to,
                shipment_request_id=request_id,
                notification_type="status_change",
                title="تغییر وضعیت درخواست",
                message=f"وضعیت درخواست {request_id} به {new_status} تغییر یافت",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            "message": "وضعیت با موفقیت به‌روزرسانی شد",
            "status": new_status
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating status: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی وضعیت"}), 500


@expert_console_bp.post("/requests/<int:request_id>/quote")
@require_auth
def create_quote(request_id: int):
    """Create a quote for a request and set status to waiting_for_customer."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "کاربر احراز هویت نشده است"}), 401

        data = request.get_json() or {}
        response_payload = quote_service.create_quote_for_request(
            request_id,
            data,
            current_user,
            request.remote_addr,
        )
        return jsonify(response_payload)
    except quote_service.QuoteServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating quote: %s", e)
        err_msg = "خطا در ثبت پیشنهاد"
        if current_app.debug:
            err_msg += f" ({e!s})"
        return jsonify({"error": err_msg}), 500


@expert_console_bp.get("/requests/<int:request_id>/quote/latest")
@require_auth
def get_latest_quote(request_id: int):
    """Get the latest quote for a request, or null."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "احراز هویت نشده"}), 401
        latest = quote_service.get_latest_quote_for_request(request_id, current_user)
        return jsonify(quote_service.build_latest_quote_response_payload(latest))
    except quote_service.QuoteServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error getting latest quote: {e}")
        return jsonify({"error": "خطا در دریافت پیشنهاد"}), 500


@expert_console_bp.post("/requests/<int:request_id>/messages")
@require_auth
def add_message(request_id: int):
    """Add a message to a shipment request. Uses authenticated user as author."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "کاربر احراز هویت نشده است"}), 401

        response_payload = message_service.create_message_for_request(
            request_id,
            request.get_json() or {},
            current_user,
            request.remote_addr,
        )
        return jsonify(response_payload)
    except message_service.MessageServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding message: {e}")
        return jsonify({"error": "خطا در اضافه کردن پیام"}), 500


@expert_console_bp.get("/notifications")
@require_auth
def get_notifications():
    """Get notifications for current authenticated expert."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "کاربر احراز هویت نشده است"}), 401

        payload = notification_service.list_notifications_for_expert(
            current_user["id"],
            {
                "unread_only": request.args.get("unread_only", "false").lower() == "true",
                "limit": request.args.get("limit", 50),
            },
        )

        return jsonify(payload)

    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {e}")
        return jsonify({"error": "خطا در دریافت اعلان‌ها"}), 500


@expert_console_bp.post("/notifications/mark-read")
@require_auth
def mark_notifications_read():
    """Mark one or more notifications as read."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "کاربر احراز هویت نشده است"}), 401

        payload = notification_service.mark_notifications_read(
            current_user["id"],
            request.get_json() or {},
        )
        if payload is None:
            return jsonify({"error": "شناسه اعلان‌ها یا mark_all الزامی است"}), 400

        return jsonify(payload)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking notifications as read: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی اعلان‌ها"}), 500


@expert_console_bp.route("/auth/login", methods=["POST", "OPTIONS"])
@validate_input({
    "username": {"type": str, "required": True, "max_length": 50},
    "password": {"type": str, "required": True, "max_length": 100}
})
def expert_login():
    """Authenticate expert user with enhanced security."""
    
    # Get the origin from request headers
    origin = request.headers.get('Origin')
    
    # In development, echo back the requesting origin (Flask-CORS handles this, but we keep for compatibility)
    # Never use '*' when supports_credentials is true - browsers reject it
    cors_origin = origin if origin else None
    
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        if cors_origin:
            response.headers.add('Access-Control-Allow-Origin', cors_origin)
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        # Sanitize input
        username = sanitize_input({"username": username})["username"]
        password = sanitize_input({"password": password})["password"]
        
        # Authenticate user
        user_data = auth_manager.authenticate_user(username, password)
        
        if not user_data:
            response = jsonify({"error": "نام کاربری یا رمز عبور اشتباه است"})
            if cors_origin:
                response.headers.add('Access-Control-Allow-Origin', cors_origin)
            response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, 401
        
        # Generate tokens
        tokens = auth_manager.generate_tokens(user_data['id'])
        
        response = jsonify({
            "success": True,
            "expert": user_data,
            "tokens": tokens
        })
        
        # Add CORS headers - echo back the requesting origin (Flask-CORS also handles this)
        if cors_origin:
            response.headers.add('Access-Control-Allow-Origin', cors_origin)
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        return response
            
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        response = jsonify({"error": "خطا در ورود"})
        response.headers.add('Access-Control-Allow-Origin', cors_origin)
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 500


@expert_console_bp.post("/auth/refresh")
@validate_input({
    "refresh_token": {"type": str, "required": True}
})
def refresh_token():
    """Refresh access token using refresh token."""
    try:
        data = request.get_json()
        refresh_token = data.get("refresh_token")
        
        tokens = auth_manager.refresh_access_token(refresh_token)
        
        if not tokens:
            return jsonify({"error": "Invalid refresh token"}), 401
        
        return jsonify(tokens)
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({"error": "خطا در تازه‌سازی توکن"}), 500


@expert_console_bp.post("/auth/logout")
@require_auth
def logout():
    """Logout user (invalidate tokens)."""
    try:
        # In production, add token to blacklist
        return jsonify({"message": "با موفقیت خارج شدید"})
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({"error": "خطا در خروج"}), 500


@expert_console_bp.get("/dashboard/kpis")
@require_auth
def get_dashboard_kpis():
    """Get KPI data for expert console dashboard."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "احراز هویت نشده"}), 401
        
        query = db.session.query(ShipmentRequest)
        if current_user.get("role") != "admin":
            query = query.filter(ShipmentRequest.assigned_to == current_user["id"])
        
        # Today's date
        today = datetime.utcnow().date()
        
        # ShipmentRequest.status is the canonical lifecycle field.
        new_count = query.filter(ShipmentRequest.status == "new").count()
        in_progress_count = query.filter(ShipmentRequest.status == "in_progress").count()
        waiting_count = query.filter(ShipmentRequest.status == "waiting_for_customer").count()
        closed_today = query.filter(
            and_(
                ShipmentRequest.status.in_(["won", "lost", "closed"]),
                func.date(ShipmentRequest.created_at) == today
            )
        ).count()
        
        # SLA metrics
        overdue_count = query.filter(
            and_(
                ShipmentRequest.sla_due_at < datetime.utcnow(),
                ShipmentRequest.status.in_(["assigned", "in_progress"])
            )
        ).count()
        
        due_soon_count = query.filter(
            and_(
                ShipmentRequest.sla_due_at <= datetime.utcnow() + timedelta(hours=2),
                ShipmentRequest.sla_due_at > datetime.utcnow(),
                ShipmentRequest.status.in_(["assigned", "in_progress"])
            )
        ).count()
        
        return jsonify({
            "counts": {
                "new": new_count,
                "in_progress": in_progress_count,
                "waiting_for_customer": waiting_count,
                "closed_today": closed_today
            },
            "sla": {
                "overdue": overdue_count,
                "due_soon": due_soon_count
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting KPIs: {e}")
        return jsonify({"error": "خطا در دریافت آمار"}), 500


@expert_console_bp.post("/requests/<int:request_id>/mark-read")
@require_auth
def mark_request_read(request_id: int):
    """Mark a request as read for the assigned expert."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "احراز هویت نشده"}), 401
        
        req = db.session.query(ShipmentRequest).get(request_id)
        if not req:
            return jsonify({"error": "درخواست یافت نشد"}), 404
        if not _can_access_request(req, current_user):
            return jsonify({"error": "شما به این درخواست دسترسی ندارید"}), 403
        
        req.has_unread_for_assignee = False
        db.session.commit()
        
        return jsonify({"message": "درخواست به عنوان خوانده شده علامت‌گذاری شد"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking request as read: {e}")
        return jsonify({"error": "خطا در علامت‌گذاری درخواست"}), 500


@expert_console_bp.get("/experts")
@require_auth
def get_experts():
    """Get list of active experts."""
    try:
        experts = db.session.query(ExpertUser).filter(
            ExpertUser.is_active == True
        ).all()
        
        experts_data = []
        for expert in experts:
            experts_data.append({
                "id": expert.id,
                "username": expert.username,
                "full_name": expert.full_name,
                "role": expert.role
            })
        
        return jsonify({"experts": experts_data})
        
    except Exception as e:
        current_app.logger.error(f"Error getting experts: {e}")
        return jsonify({"error": "خطا در دریافت لیست کارشناسان"}), 500


@expert_console_bp.get("/ping")
def ping():
    """Health check endpoint for expert console."""
    return jsonify({"message": "Expert console API is running"})
