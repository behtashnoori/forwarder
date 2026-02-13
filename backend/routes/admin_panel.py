"""Admin panel routes for shipment request insights."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import and_, or_, func, desc, case
from sqlalchemy.orm import joinedload

from backend.models import (
    City, County, Province, ShipmentRequest, ExpertUser, 
    TransportMethod, AssignmentLog, ExpertConsoleLog
)
from backend.extensions import db
from backend.security import require_role
from backend.auth import get_current_user

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
