"""Expert console API routes."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import (
    ShipmentRequest, ShipmentRequestLog, Province, County, City,
    ExpertUser, ExpertConsoleLog, ExpertConsoleMessage, ExpertConsoleNotification
)
from backend.auth import auth_manager, login_required, get_current_user
from backend.security import require_auth, validate_input, sanitize_input
from backend.cache import cached, cache_manager, performance_monitor

expert_console_bp = Blueprint("expert_console", __name__, url_prefix="/api/expert")


@expert_console_bp.get("/requests")
@require_auth
def get_shipment_requests():
    """Get filtered and paginated shipment requests for expert console."""
    try:
        # Query parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        status = request.args.get("status")
        assigned_to = request.args.get("assigned_to")
        priority = request.args.get("priority")
        search = request.args.get("search")
        sort_by = request.args.get("sort_by", "created_at")
        sort_order = request.args.get("sort_order", "desc")
        
        # Build query
        query = db.session.query(ShipmentRequest)
        
        # Apply filters
        if status:
            # Handle comma-separated status values (e.g., "won,lost,closed")
            if "," in status:
                status_list = [s.strip() for s in status.split(",")]
                query = query.filter(
                    or_(
                        ShipmentRequest.status.in_(status_list),
                        ShipmentRequest.status_request_status.in_(status_list)
                    )
                )
            else:
                query = query.filter(
                    or_(
                        ShipmentRequest.status == status,
                        ShipmentRequest.status_request_status == status
                    )
                )
        if assigned_to:
            query = query.filter(ShipmentRequest.assigned_to == assigned_to)
        if priority:
            query = query.filter(ShipmentRequest.priority == priority)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ShipmentRequest.contact_phone.like(search_term),
                    ShipmentRequest.customer_first_name.like(search_term),
                    ShipmentRequest.customer_last_name.like(search_term),
                    ShipmentRequest.cargo_description.like(search_term)
                )
            )
        
        # Apply sorting
        if sort_by == "created_at":
            sort_column = ShipmentRequest.created_at
        elif sort_by == "sla_due_at":
            sort_column = ShipmentRequest.sla_due_at
        elif sort_by == "priority":
            sort_column = ShipmentRequest.priority
        else:
            sort_column = ShipmentRequest.created_at
            
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Get paginated results
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format response
        requests_data = []
        for req in pagination.items:
            # Get related data
            origin_province = db.session.query(Province).get(req.origin_province_id)
            origin_county = db.session.query(County).get(req.origin_county_id)
            origin_city = db.session.query(City).get(req.origin_city_id)
            dest_province = db.session.query(Province).get(req.dest_province_id)
            dest_county = db.session.query(County).get(req.dest_county_id)
            dest_city = db.session.query(City).get(req.dest_city_id)
            assigned_expert = db.session.query(ExpertUser).get(req.assigned_to) if req.assigned_to else None
            
            # Calculate SLA status
            sla_status = "on_time"
            if req.sla_due_at:
                if datetime.utcnow() > req.sla_due_at:
                    sla_status = "overdue"
                elif datetime.utcnow() + timedelta(hours=2) > req.sla_due_at:
                    sla_status = "due_soon"
            
            requests_data.append({
                "id": req.id,
                "tracking_number": f"SR{req.id:06d}",
                "status": req.status,
                "priority": req.priority,
                "created_at": req.created_at.isoformat(),
                "sla_due_at": req.sla_due_at.isoformat() if req.sla_due_at else None,
                "sla_status": sla_status,
                "assigned_to": {
                    "id": assigned_expert.id,
                    "name": assigned_expert.full_name
                } if assigned_expert else None,
                "customer": {
                    "name": f"{req.customer_first_name or ''} {req.customer_last_name or ''}".strip() or "نامشخص",
                    "phone": req.contact_phone
                },
                "route": {
                    "origin": {
                        "province": origin_province.name_fa if origin_province else "نامشخص",
                        "county": origin_county.name_fa if origin_county else "نامشخص", 
                        "city": origin_city.name_fa if origin_city else "نامشخص"
                    },
                    "destination": {
                        "province": dest_province.name_fa if dest_province else "نامشخص",
                        "county": dest_county.name_fa if dest_county else "نامشخص",
                        "city": dest_city.name_fa if dest_city else "نامشخص"
                    }
                },
                "transport_method": req.transport_method,
                "cargo": {
                    "description": req.cargo_description,
                    "weight": req.cargo_weight,
                    "volume": req.cargo_volume,
                    "value": req.cargo_value
                },
                "has_unread": req.has_unread_for_assignee
            })
        
        return jsonify({
            "requests": requests_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting shipment requests: {e}")
        return jsonify({"error": "خطا در دریافت درخواست‌ها"}), 500


@expert_console_bp.get("/requests/<int:request_id>")
def get_shipment_request_detail(request_id: int):
    """Get detailed information about a specific shipment request."""
    try:
        req = db.session.query(ShipmentRequest).get(request_id)
        if not req:
            return jsonify({"error": "درخواست یافت نشد"}), 404
        
        # Get related data
        origin_province = db.session.query(Province).get(req.origin_province_id)
        origin_county = db.session.query(County).get(req.origin_county_id)
        origin_city = db.session.query(City).get(req.origin_city_id)
        dest_province = db.session.query(Province).get(req.dest_province_id)
        dest_county = db.session.query(County).get(req.dest_county_id)
        dest_city = db.session.query(City).get(req.dest_city_id)
        assigned_expert = db.session.query(ExpertUser).get(req.assigned_to) if req.assigned_to else None
        
        # Get timeline logs
        logs = db.session.query(ExpertConsoleLog).filter(
            ExpertConsoleLog.shipment_request_id == request_id
        ).order_by(ExpertConsoleLog.created_at.desc()).all()
        
        # Get messages
        messages = db.session.query(ExpertConsoleMessage).filter(
            ExpertConsoleMessage.shipment_request_id == request_id
        ).order_by(ExpertConsoleMessage.created_at.desc()).all()
        
        # Format timeline
        timeline = []
        for log in logs:
            timeline.append({
                "id": log.id,
                "action": log.action,
                "old_status": log.old_status,
                "new_status": log.new_status,
                "note": log.note,
                "created_at": log.created_at.isoformat(),
                "created_by": log.created_by_user.full_name if log.created_by_user else "سیستم"
            })
        
        # Format messages
        messages_data = []
        for msg in messages:
            messages_data.append({
                "id": msg.id,
                "type": msg.message_type,
                "subject": msg.subject,
                "content": msg.content,
                "is_read_by_customer": msg.is_read_by_customer,
                "customer_response": msg.customer_response,
                "created_at": msg.created_at.isoformat(),
                "created_by": msg.created_by_user.full_name if msg.created_by_user else "سیستم"
            })
        
        # Calculate SLA status
        sla_status = "on_time"
        if req.sla_due_at:
            if datetime.utcnow() > req.sla_due_at:
                sla_status = "overdue"
            elif datetime.utcnow() + timedelta(hours=2) > req.sla_due_at:
                sla_status = "due_soon"
        
        return jsonify({
            "id": req.id,
            "tracking_number": f"SR{req.id:06d}",
            "status": req.status,
            "priority": req.priority,
            "created_at": req.created_at.isoformat(),
            "sla_due_at": req.sla_due_at.isoformat() if req.sla_due_at else None,
            "sla_status": sla_status,
            "assigned_to": {
                "id": assigned_expert.id,
                "name": assigned_expert.full_name,
                "username": assigned_expert.username
            } if assigned_expert else None,
            "customer": {
                "first_name": req.customer_first_name,
                "last_name": req.customer_last_name,
                "phone": req.contact_phone,
                "full_name": f"{req.customer_first_name or ''} {req.customer_last_name or ''}".strip() or "نامشخص"
            },
            "route": {
                "origin": {
                    "province": origin_province.name_fa if origin_province else "نامشخص",
                    "county": origin_county.name_fa if origin_county else "نامشخص",
                    "city": origin_city.name_fa if origin_city else "نامشخص"
                },
                "destination": {
                    "province": dest_province.name_fa if dest_province else "نامشخص",
                    "county": dest_county.name_fa if dest_county else "نامشخص",
                    "city": dest_city.name_fa if dest_city else "نامشخص"
                }
            },
            "transport_method": req.transport_method,
            "cargo": {
                "description": req.cargo_description,
                "weight": req.cargo_weight,
                "volume": req.cargo_volume,
                "value": req.cargo_value,
                "special_instructions": req.special_instructions
            },
            "dates": {
                "pickup_date": req.pickup_date.isoformat() if req.pickup_date else None,
                "delivery_date": req.delivery_date.isoformat() if req.delivery_date else None
            },
            "timeline": timeline,
            "messages": messages_data,
            "has_unread": req.has_unread_for_assignee
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting shipment request detail: {e}")
        return jsonify({"error": "خطا در دریافت جزئیات درخواست"}), 500


@expert_console_bp.post("/requests/<int:request_id>/assign")
def assign_request(request_id: int):
    """Assign a shipment request to an expert."""
    try:
        data = request.get_json() or {}
        expert_id = data.get("expert_id")
        
        if not expert_id:
            return jsonify({"error": "شناسه کارشناس الزامی است"}), 400
        
        req = db.session.query(ShipmentRequest).get(request_id)
        if not req:
            return jsonify({"error": "درخواست یافت نشد"}), 404
        
        expert = db.session.query(ExpertUser).get(expert_id)
        if not expert:
            return jsonify({"error": "کارشناس یافت نشد"}), 404
        
        old_assigned_to = req.assigned_to
        old_status = req.status
        
        # Update request
        req.assigned_to = expert_id
        req.status = "assigned"
        req.has_unread_for_assignee = True
        
        # Create log entry
        log = ExpertConsoleLog(
            shipment_request_id=request_id,
            expert_user_id=expert_id,
            action="assignment",
            old_status=old_status,
            new_status="assigned",
            note=f"ارجاع به کارشناس: {expert.full_name}",
            ip_address=request.remote_addr,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        
        # Create notification
        notification = ExpertConsoleNotification(
            expert_user_id=expert_id,
            shipment_request_id=request_id,
            notification_type="assignment",
            title="ارجاع درخواست جدید",
            message=f"درخواست {request_id} به شما ارجاع داده شد",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            "message": "درخواست با موفقیت ارجاع داده شد",
            "assigned_to": {
                "id": expert.id,
                "name": expert.full_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning request: {e}")
        return jsonify({"error": "خطا در ارجاع درخواست"}), 500


@expert_console_bp.post("/requests/<int:request_id>/status")
def update_request_status(request_id: int):
    """Update the status of a shipment request."""
    try:
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


@expert_console_bp.post("/requests/<int:request_id>/messages")
def add_message(request_id: int):
    """Add a message to a shipment request."""
    try:
        data = request.get_json() or {}
        message_type = data.get("type")  # internal_note or customer_message
        subject = data.get("subject", "")
        content = data.get("content")
        expert_id = data.get("expert_id")
        
        if not content:
            return jsonify({"error": "محتوای پیام الزامی است"}), 400
        
        if not expert_id:
            return jsonify({"error": "شناسه کارشناس الزامی است"}), 400
        
        req = db.session.query(ShipmentRequest).get(request_id)
        if not req:
            return jsonify({"error": "درخواست یافت نشد"}), 404
        
        expert = db.session.query(ExpertUser).get(expert_id)
        if not expert:
            return jsonify({"error": "کارشناس یافت نشد"}), 404
        
        # Create message
        message = ExpertConsoleMessage(
            shipment_request_id=request_id,
            expert_user_id=expert_id,
            message_type=message_type,
            subject=subject,
            content=content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(message)
        
        # Create log entry
        log = ExpertConsoleLog(
            shipment_request_id=request_id,
            expert_user_id=expert_id,
            action="message_added",
            note=f"پیام {message_type} اضافه شد",
            ip_address=request.remote_addr,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        
        # If customer message, update status and touch time
        if message_type == "customer_message":
            req.status = "waiting_for_customer"
            req.last_customer_touch_at = datetime.utcnow()
            req.has_unread_for_assignee = True
        
        db.session.commit()
        
        return jsonify({
            "message": "پیام با موفقیت اضافه شد",
            "message_id": message.id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding message: {e}")
        return jsonify({"error": "خطا در اضافه کردن پیام"}), 500


@expert_console_bp.get("/notifications")
def get_notifications():
    """Get notifications for expert console."""
    try:
        expert_id = request.args.get("expert_id")
        unread_only = request.args.get("unread_only", "false").lower() == "true"
        
        if not expert_id:
            return jsonify({"error": "شناسه کارشناس الزامی است"}), 400
        
        query = db.session.query(ExpertConsoleNotification).filter(
            ExpertConsoleNotification.expert_user_id == expert_id
        )
        
        if unread_only:
            query = query.filter(ExpertConsoleNotification.is_read == False)
        
        notifications = query.order_by(
            ExpertConsoleNotification.created_at.desc()
        ).limit(50).all()
        
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                "id": notif.id,
                "type": notif.notification_type,
                "title": notif.title,
                "message": notif.message,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat(),
                "shipment_request_id": notif.shipment_request_id
            })
        
        return jsonify({
            "notifications": notifications_data,
            "unread_count": len([n for n in notifications_data if not n["is_read"]])
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {e}")
        return jsonify({"error": "خطا در دریافت اعلان‌ها"}), 500


@expert_console_bp.post("/auth/login")
@validate_input({
    "username": {"type": str, "required": True, "max_length": 50},
    "password": {"type": str, "required": True, "max_length": 100}
})
def expert_login():
    """Authenticate expert user with enhanced security."""
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
            return jsonify({"error": "نام کاربری یا رمز عبور اشتباه است"}), 401
        
        # Generate tokens
        tokens = auth_manager.generate_tokens(user_data['id'])
        
        return jsonify({
            "success": True,
            "expert": user_data,
            "tokens": tokens
        })
            
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "خطا در ورود"}), 500


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
@cached(ttl=300, key_prefix="dashboard_kpis")
def get_dashboard_kpis():
    """Get KPI data for expert console dashboard."""
    try:
        expert_id = request.args.get("expert_id")
        
        # Base query - show all requests for dashboard overview
        query = db.session.query(ShipmentRequest)
        # Don't filter by expert_id for dashboard KPIs to show all requests
        
        # Today's date
        today = datetime.utcnow().date()
        
        # Count by status - use both status fields
        new_count = query.filter(
            or_(ShipmentRequest.status == "new", ShipmentRequest.status_request_status == "new")
        ).count()
        in_progress_count = query.filter(
            or_(ShipmentRequest.status == "in_progress", ShipmentRequest.status_request_status == "in_progress")
        ).count()
        waiting_count = query.filter(
            or_(ShipmentRequest.status == "waiting_for_customer", ShipmentRequest.status_request_status == "waiting_for_customer")
        ).count()
        closed_today = query.filter(
            and_(
                or_(
                    ShipmentRequest.status.in_(["won", "lost", "closed"]),
                    ShipmentRequest.status_request_status.in_(["won", "lost", "closed"])
                ),
                func.date(ShipmentRequest.created_at) == today
            )
        ).count()
        
        # SLA metrics
        overdue_count = query.filter(
            and_(
                ShipmentRequest.sla_due_at < datetime.utcnow(),
                or_(
                    ShipmentRequest.status.in_(["assigned", "in_progress"]),
                    ShipmentRequest.status_request_status.in_(["assigned", "in_progress"])
                )
            )
        ).count()
        
        due_soon_count = query.filter(
            and_(
                ShipmentRequest.sla_due_at <= datetime.utcnow() + timedelta(hours=2),
                ShipmentRequest.sla_due_at > datetime.utcnow(),
                or_(
                    ShipmentRequest.status.in_(["assigned", "in_progress"]),
                    ShipmentRequest.status_request_status.in_(["assigned", "in_progress"])
                )
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
def mark_request_read(request_id: int):
    """Mark a request as read for the assigned expert."""
    try:
        expert_id = request.args.get("expert_id")
        
        if not expert_id:
            return jsonify({"error": "شناسه کارشناس الزامی است"}), 400
        
        req = db.session.query(ShipmentRequest).get(request_id)
        if not req:
            return jsonify({"error": "درخواست یافت نشد"}), 404
        
        if req.assigned_to != int(expert_id):
            return jsonify({"error": "شما مسئول این درخواست نیستید"}), 403
        
        req.has_unread_for_assignee = False
        db.session.commit()
        
        return jsonify({"message": "درخواست به عنوان خوانده شده علامت‌گذاری شد"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking request as read: {e}")
        return jsonify({"error": "خطا در علامت‌گذاری درخواست"}), 500


@expert_console_bp.get("/experts")
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