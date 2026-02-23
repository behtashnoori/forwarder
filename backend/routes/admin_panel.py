"""Admin panel routes for shipment request insights."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import and_, or_, func, desc, case
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from backend.models import (
    City, County, Province, ShipmentRequest, ExpertUser,
    TransportMethod, AssignmentLog, ExpertConsoleLog,
    ReferralRule, ReferralRuleState, ReferralAssignmentLog,
    SiteSettings,
)
from backend.extensions import db
from backend.security import require_role
from backend.auth import get_current_user
from backend.referral_engine import referral_engine
from backend.routes.site_settings import (
    _get_settings_row,
    _settings_to_dict,
    get_uploads_folder,
    get_or_create_settings_row,
)

admin_bp = Blueprint("admin_panel", __name__, url_prefix="/api/admin")


@admin_bp.get("/shipment-requests/<int:request_id>")
@require_role('admin')
def get_shipment_request_detail(request_id: int):
    """Return a shipment request with human-readable location names."""
    shipment_request = ShipmentRequest.query.options(
        joinedload(ShipmentRequest.assigned_expert)
    ).get(request_id)
    
    if shipment_request is None:
        return jsonify({"error": "درخواست موردنظر یافت نشد"}), 404

    origin_province = Province.query.get(shipment_request.origin_province_id) if shipment_request.origin_province_id else None
    origin_county = County.query.get(shipment_request.origin_county_id) if shipment_request.origin_county_id else None
    origin_city = City.query.get(shipment_request.origin_city_id) if shipment_request.origin_city_id else None

    dest_province = Province.query.get(shipment_request.dest_province_id) if shipment_request.dest_province_id else None
    dest_county = County.query.get(shipment_request.dest_county_id) if shipment_request.dest_county_id else None
    dest_city = City.query.get(shipment_request.dest_city_id) if shipment_request.dest_city_id else None

    assigned_expert = None
    if shipment_request.assigned_expert:
        assigned_expert = {
            "id": shipment_request.assigned_expert.id,
            "full_name": shipment_request.assigned_expert.full_name,
            "username": shipment_request.assigned_expert.username
        }

    response = {
        "id": shipment_request.id,
        "contact_phone": shipment_request.contact_phone,
        "customer_first_name": shipment_request.customer_first_name,
        "customer_last_name": shipment_request.customer_last_name,
        "transport_method": shipment_request.transport_method,
        "status": shipment_request.status,
        "priority": shipment_request.priority,
        "assigned_to": assigned_expert,
        "origin": {
            "province": origin_province.name_fa if origin_province else None,
            "county": origin_county.name_fa if origin_county else None,
            "city": origin_city.name_fa if origin_city else None,
        },
        "destination": {
            "province": dest_province.name_fa if dest_province else None,
            "county": dest_county.name_fa if dest_county else None,
            "city": dest_city.name_fa if dest_city else None,
        },
        "created_at": shipment_request.created_at.isoformat() if shipment_request.created_at else None,
        "sla_due_at": shipment_request.sla_due_at.isoformat() if shipment_request.sla_due_at else None,
    }

    return jsonify(response)


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
        # Pagination
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        
        # Filters
        status_filter = request.args.get('status')
        transport_method_filter = request.args.get('transport_method')
        province_id_filter = request.args.get('province_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query
        query = ShipmentRequest.query
        
        # Apply filters
        if status_filter:
            query = query.filter(ShipmentRequest.status == status_filter)
        
        if transport_method_filter:
            query = query.filter(
                or_(
                    ShipmentRequest.transport_method == transport_method_filter,
                    ShipmentRequest.domestic_transport_method == transport_method_filter,
                    ShipmentRequest.international_transport_method == transport_method_filter
                )
            )
        
        if province_id_filter:
            query = query.filter(
                or_(
                    ShipmentRequest.origin_province_id == province_id_filter,
                    ShipmentRequest.dest_province_id == province_id_filter
                )
            )
        
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(ShipmentRequest.created_at >= date_from_obj)
            except ValueError:
                return jsonify({"error": "فرمت تاریخ نامعتبر است"}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                # Include the entire day
                date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
                query = query.filter(ShipmentRequest.created_at <= date_to_obj)
            except ValueError:
                return jsonify({"error": "فرمت تاریخ نامعتبر است"}), 400
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply ordering and pagination
        shipment_requests = query.order_by(
            desc(ShipmentRequest.created_at)
        ).offset(offset).limit(limit).all()
        
        # Get unique location IDs
        origin_province_ids = {req.origin_province_id for req in shipment_requests if req.origin_province_id}
        dest_province_ids = {req.dest_province_id for req in shipment_requests if req.dest_province_id}
        province_ids = origin_province_ids | dest_province_ids
        
        origin_county_ids = {req.origin_county_id for req in shipment_requests if req.origin_county_id}
        dest_county_ids = {req.dest_county_id for req in shipment_requests if req.dest_county_id}
        county_ids = origin_county_ids | dest_county_ids
        
        origin_city_ids = {req.origin_city_id for req in shipment_requests if req.origin_city_id}
        dest_city_ids = {req.dest_city_id for req in shipment_requests if req.dest_city_id}
        city_ids = origin_city_ids | dest_city_ids
        
        # Fetch locations in bulk
        provinces = Province.query.filter(Province.id.in_(province_ids)).all() if province_ids else []
        counties = County.query.filter(County.id.in_(county_ids)).all() if county_ids else []
        cities = City.query.filter(City.id.in_(city_ids)).all() if city_ids else []
        
        # Create lookup dictionaries
        province_lookup = {p.id: p.name_fa for p in provinces}
        county_lookup = {c.id: c.name_fa for c in counties}
        city_lookup = {c.id: c.name_fa for c in cities}
        
        # Build response
        response = []
        for req in shipment_requests:
            response.append({
                "id": req.id,
                "contact_phone": req.contact_phone,
                "customer_first_name": req.customer_first_name,
                "customer_last_name": req.customer_last_name,
                "transport_method": req.transport_method,
                "status": req.status,
                "priority": req.priority,
                "assigned_to": req.assigned_to,
                "origin": {
                    "province": province_lookup.get(req.origin_province_id),
                    "county": county_lookup.get(req.origin_county_id),
                    "city": city_lookup.get(req.origin_city_id),
                },
                "destination": {
                    "province": province_lookup.get(req.dest_province_id),
                    "county": county_lookup.get(req.dest_county_id),
                    "city": city_lookup.get(req.dest_city_id),
                },
                "created_at": req.created_at.isoformat() if req.created_at else None,
            })
        
        return jsonify({
            "requests": response,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        })
        
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
        # Total requests
        total_requests = ShipmentRequest.query.count()
        
        # Requests per transport method
        transport_method_stats = db.session.query(
            func.coalesce(
                func.coalesce(
                    ShipmentRequest.domestic_transport_method,
                    ShipmentRequest.international_transport_method
                ),
                ShipmentRequest.transport_method,
                'unknown'
            ).label('method'),
            func.count(ShipmentRequest.id).label('count')
        ).group_by('method').all()
        
        requests_per_transport_method = {
            stat.method: stat.count for stat in transport_method_stats
        }
        
        # Requests per status
        status_stats = db.session.query(
            ShipmentRequest.status,
            func.count(ShipmentRequest.id).label('count')
        ).group_by(ShipmentRequest.status).all()
        
        requests_per_status = {
            stat.status: stat.count for stat in status_stats
        }
        
        # Last 7 days count
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        last_7_days_count = ShipmentRequest.query.filter(
            ShipmentRequest.created_at >= seven_days_ago
        ).count()
        
        # Top provinces (by origin)
        top_provinces_query = db.session.query(
            Province.name_fa,
            func.count(ShipmentRequest.id).label('count')
        ).join(
            ShipmentRequest, ShipmentRequest.origin_province_id == Province.id
        ).group_by(Province.id, Province.name_fa).order_by(
            desc('count')
        ).limit(10).all()
        
        top_provinces = [
            {"province": prov.name_fa, "count": prov.count}
            for prov in top_provinces_query
        ]
        
        # Recent activity (last 24 hours)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        last_24h_count = ShipmentRequest.query.filter(
            ShipmentRequest.created_at >= one_day_ago
        ).count()
        
        # Unassigned requests
        unassigned_count = ShipmentRequest.query.filter(
            and_(
                ShipmentRequest.assigned_to.is_(None),
                ShipmentRequest.status.in_(['new', 'pending'])
            )
        ).count()
        
        return jsonify({
            "total_requests": total_requests,
            "requests_per_transport_method": requests_per_transport_method,
            "requests_per_status": requests_per_status,
            "last_7_days_count": last_7_days_count,
            "last_24h_count": last_24h_count,
            "unassigned_count": unassigned_count,
            "top_provinces": top_provinces
        })
        
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
        from backend.models import ExpertConsoleLog, ExpertConsoleNotification
        
        # Get all experts with assignments
        experts_with_assignments = db.session.query(
            ExpertUser.id,
            ExpertUser.full_name,
            ExpertUser.username,
            ExpertUser.role,
            func.count(ShipmentRequest.id).label('total_assignments'),
            func.sum(case([(ShipmentRequest.status == 'won', 1)], else_=0)).label('won_count'),
            func.sum(case([(ShipmentRequest.status == 'lost', 1)], else_=0)).label('lost_count'),
            func.sum(case([(ShipmentRequest.status.in_(['assigned', 'in_progress']), 1)], else_=0)).label('active_count')
        ).join(
            ShipmentRequest, ShipmentRequest.assigned_to == ExpertUser.id
        ).filter(
            ExpertUser.is_active == True
        ).group_by(
            ExpertUser.id, ExpertUser.full_name, ExpertUser.username, ExpertUser.role
        ).all()
        
        assignments_per_expert = []
        total_won = 0
        total_assignments = 0
        
        for expert_stat in experts_with_assignments:
            expert_id = expert_stat.id
            total = expert_stat.total_assignments or 0
            won = expert_stat.won_count or 0
            lost = expert_stat.lost_count or 0
            active = expert_stat.active_count or 0
            
            # Calculate conversion rate for this expert
            conversion_rate = (won / total * 100) if total > 0 else 0
            
            # Calculate average response time (simplified - get from assignment logs)
            # This is an approximation - in production, you'd want a more detailed query
            avg_response_time = None
            
            assignments_per_expert.append({
                "expert_id": expert_id,
                "expert_name": expert_stat.full_name,
                "username": expert_stat.username,
                "role": expert_stat.role,
                "total_assignments": total,
                "won_count": won,
                "lost_count": lost,
                "active_count": active,
                "conversion_rate": round(conversion_rate, 2),
                "avg_response_time_hours": round(avg_response_time, 2) if avg_response_time else None
            })
            
            total_won += won
            total_assignments += total
        
        # Overall conversion rate
        overall_conversion_rate = (total_won / total_assignments * 100) if total_assignments > 0 else 0
        
        # Calculate overall average response time (optimized query)
        # Get response times using a single optimized query
        response_time_query = db.session.query(
            func.avg(
                func.extract('epoch', 
                    ExpertConsoleLog.created_at - AssignmentLog.created_at
                ) / 3600
            ).label('avg_hours')
        ).join(
            AssignmentLog, 
            ExpertConsoleLog.shipment_request_id == AssignmentLog.shipment_request_id
        ).filter(
            and_(
                ExpertConsoleLog.action.notin_(['status_change', 'assigned']),
                ExpertConsoleLog.created_at > AssignmentLog.created_at
            )
        ).scalar()
        
        avg_response_time = response_time_query if response_time_query else None
        
        # SLA violations (requests past SLA due date)
        sla_violations = db.session.query(func.count(ShipmentRequest.id)).filter(
            and_(
                ShipmentRequest.sla_due_at.isnot(None),
                ShipmentRequest.sla_due_at < datetime.utcnow(),
                ShipmentRequest.status.in_(['assigned', 'in_progress', 'waiting_for_customer'])
            )
        ).scalar() or 0
        
        return jsonify({
            "assignments_per_expert": assignments_per_expert,
            "overall_stats": {
                "total_assignments": total_assignments,
                "total_won": total_won,
                "overall_conversion_rate": round(overall_conversion_rate, 2),
                "avg_response_time_hours": round(avg_response_time, 2) if avg_response_time else None,
                "sla_violations": sla_violations
            },
            "generated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating assignment summary: {e}")
        return jsonify({"error": "خطا در تولید گزارش"}), 500


# --- Referral rules (قوانین ارجاع) ---

@admin_bp.get("/referral-rules")
@require_role('admin')
def get_referral_rules():
    """List all referral rules ordered by priority ASC."""
    try:
        rules = db.session.query(ReferralRule).order_by(
            ReferralRule.priority.asc(), ReferralRule.name
        ).all()
        rules_data = []
        for rule in rules:
            try:
                conditions = json.loads(rule.conditions) if rule.conditions else {}
            except Exception:
                conditions = {}
            try:
                action = json.loads(rule.action) if rule.action else {}
            except Exception:
                action = {}
            action_type = action.get("type", "")
            expert_ids = (action.get("expert_ids") or []) if action_type == "pool_assign" else []
            rules_data.append({
                "id": rule.id,
                "name": rule.name,
                "is_active": rule.is_active,
                "priority": rule.priority,
                "conditions": conditions,
                "action": action,
                "stop_on_match": getattr(rule, "stop_on_match", True),
                "created_by": rule.creator.id if rule.creator else None,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                "action_type": action_type,
                "pool_expert_count": len(expert_ids) if action_type == "pool_assign" else 0,
                "strategy": action.get("strategy") if action_type == "pool_assign" else None,
            })
        return jsonify({"referral_rules": rules_data})
    except Exception as e:
        current_app.logger.error(f"Error getting referral rules: {e}")
        return jsonify({"error": "خطا در دریافت قوانین ارجاع"}), 500


@admin_bp.post("/referral-rules")
@require_role('admin')
def create_referral_rule():
    """Create a new referral rule."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "احراز هویت نشده"}), 401
        data = request.get_json() or {}
        name = data.get("name")
        if not name or not name.strip():
            return jsonify({"error": "نام قانون الزامی است"}), 400
        conditions = data.get("conditions")
        if conditions is None:
            conditions = {}
        action = data.get("action")
        if not action or action.get("type") not in ("direct_assign", "pool_assign"):
            return jsonify({"error": "action باید نوع direct_assign یا pool_assign داشته باشد"}), 400
        if action.get("type") == "direct_assign" and action.get("expert_id") is None:
            return jsonify({"error": "برای direct_assign مقدار expert_id الزامی است"}), 400
        if action.get("type") == "pool_assign":
            if not action.get("expert_ids"):
                return jsonify({"error": "برای pool_assign لیست expert_ids الزامی است"}), 400
            if action.get("strategy") not in ("round_robin", "least_workload"):
                return jsonify({"error": "برای pool_assign strategy باید round_robin یا least_workload باشد"}), 400
        rule = ReferralRule(
            name=name.strip(),
            is_active=data.get("is_active", True),
            priority=int(data.get("priority", 1)),
            conditions=json.dumps(conditions),
            action=json.dumps(action),
            stop_on_match=data.get("stop_on_match", True),
            created_by=current_user.get("id"),
        )
        db.session.add(rule)
        db.session.commit()
        return jsonify({"message": "قانون ارجاع با موفقیت ایجاد شد", "rule_id": rule.id}), 201
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
        rule = db.session.query(ReferralRule).get(rule_id)
        if not rule:
            return jsonify({"error": "قانون ارجاع یافت نشد"}), 404
        data = request.get_json() or {}
        if "name" in data and data["name"]:
            rule.name = data["name"].strip()
        if "is_active" in data:
            rule.is_active = bool(data["is_active"])
        if "priority" in data:
            rule.priority = int(data["priority"])
        if "stop_on_match" in data:
            rule.stop_on_match = bool(data["stop_on_match"])
        if "conditions" in data:
            rule.conditions = json.dumps(data["conditions"])
        if "action" in data:
            action = data["action"]
            if action.get("type") not in ("direct_assign", "pool_assign"):
                return jsonify({"error": "action.type باید direct_assign یا pool_assign باشد"}), 400
            if action.get("type") == "pool_assign" and action.get("strategy") not in ("round_robin", "least_workload"):
                return jsonify({"error": "strategy باید round_robin یا least_workload باشد"}), 400
            rule.action = json.dumps(action)
        rule.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "قانون ارجاع به‌روزرسانی شد"})
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
        rule = db.session.query(ReferralRule).get(rule_id)
        if not rule:
            return jsonify({"error": "قانون ارجاع یافت نشد"}), 404
        db.session.query(ReferralRuleState).filter(ReferralRuleState.rule_id == rule_id).delete()
        db.session.delete(rule)
        db.session.commit()
        return jsonify({"message": "قانون ارجاع حذف شد"})
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
        data = request.get_json() or {}
        request_id = data.get("request_id")
        if request_id is None:
            return jsonify({"error": "request_id الزامی است"}), 400
        result = referral_engine.preview_assignment(int(request_id))
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error in referral preview: {e}")
        return jsonify({"error": "خطا در پیش‌نمایش ارجاع"}), 500


# --- Site settings (تنظیمات سایت) ---

ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


@admin_bp.get("/site-settings")
@require_role("admin")
def admin_get_site_settings():
    """Return site settings for admin form. Creates default row if missing."""
    try:
        row = get_or_create_settings_row()
        data = _settings_to_dict(row)
        return jsonify(data)
    except Exception as e:
        current_app.logger.exception("admin_get_site_settings: %s", e)
        return jsonify({"error": "خطا در دریافت تنظیمات"}), 500


@admin_bp.put("/site-settings")
@require_role("admin")
def admin_update_site_settings():
    """Update site settings (text fields only). Creates default row if missing."""
    try:
        row = get_or_create_settings_row()
        if not row:
            return jsonify({"error": "تنظیمات سایت در دسترس نیست"}), 500
        data = request.get_json()
        if not data:
            return jsonify({"error": "بدنه درخواست خالی است یا JSON معتبر نیست"}), 400
        if "company_name" in data:
            row.company_name = (data["company_name"] or "").strip() or "فورواردری سریع"
        if "tagline" in data:
            row.tagline = (data["tagline"] or "").strip()
        if "footer_description" in data:
            row.footer_description = (data["footer_description"] or "").strip()
        if "contact_phone" in data:
            row.contact_phone = (data["contact_phone"] or "").strip()
        if "contact_email" in data:
            row.contact_email = (data["contact_email"] or "").strip()
        if "contact_address" in data:
            row.contact_address = (data["contact_address"] or "").strip()
        if "working_hours_weekdays" in data:
            row.working_hours_weekdays = (data["working_hours_weekdays"] or "").strip()
        if "working_hours_thursday" in data:
            row.working_hours_thursday = (data["working_hours_thursday"] or "").strip()
        if "support_text" in data:
            row.support_text = (data["support_text"] or "").strip()
        if "copyright_text" in data:
            row.copyright_text = (data["copyright_text"] or "").strip()
        row.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "تنظیمات ذخیره شد", "settings": _settings_to_dict(row)})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("admin_update_site_settings: %s", e)
        return jsonify({"error": "خطا در ذخیره تنظیمات"}), 500


@admin_bp.post("/site-settings/logo")
@require_role("admin")
def admin_upload_site_logo():
    """Upload site logo image; update singleton row and return new logo_url. Creates row if missing."""
    try:
        if "file" not in request.files and "logo" not in request.files:
            return jsonify({"error": "فایلی ارسال نشده است"}), 400
        file = request.files.get("file") or request.files.get("logo")
        if not file or not file.filename:
            return jsonify({"error": "فایلی انتخاب نشده است"}), 400
        ext = (Path(secure_filename(file.filename)).suffix or "").lstrip(".").lower()
        if ext not in ALLOWED_LOGO_EXTENSIONS:
            return jsonify({"error": "فرمت فایل باید یکی از png, jpg, jpeg, gif, webp باشد"}), 400
        filename = f"site_logo.{ext}"
        uploads = get_uploads_folder()
        filepath = uploads / filename
        file.save(str(filepath))
        row = get_or_create_settings_row()
        if not row:
            return jsonify({"error": "تنظیمات سایت در دسترس نیست"}), 500
        logo_url = f"/api/uploads/{filename}"
        row.logo_url = logo_url
        row.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "لوگو با موفقیت آپلود شد", "logo_url": logo_url})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("admin_upload_site_logo: %s", e)
        return jsonify({"error": "خطا در آپلود لوگو"}), 500


@admin_bp.delete("/site-settings/logo")
@require_role("admin")
def admin_remove_site_logo():
    """Remove site logo (set logo_url to null)."""
    try:
        row = get_or_create_settings_row()
        if not row:
            return jsonify({"error": "تنظیمات سایت در دسترس نیست"}), 500
        row.logo_url = None
        row.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "لوگو حذف شد", "logo_url": None})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("admin_remove_site_logo: %s", e)
        return jsonify({"error": "خطا در حذف لوگو"}), 500
