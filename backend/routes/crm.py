"""CRM API routes for customer, sales, and activity management."""
from flask import Blueprint, jsonify, request, current_app
from backend.extensions import db
from backend.security import require_role
from backend.services import crm_dashboard_service, crm_service, crm_write_service

crm_bp = Blueprint("crm", __name__, url_prefix="/api/crm")


# Customer Management Routes
@crm_bp.get("/customers")
@require_role("business_expert")
def get_customers():
    """Get filtered and paginated customers."""
    try:
        filters = {
            "page": request.args.get("page", 1, type=int),
            "per_page": min(request.args.get("per_page", 20, type=int), 100),
            "search": request.args.get("search"),
            "customer_type": request.args.get("customer_type"),
            "status": request.args.get("status"),
            "sort_by": request.args.get("sort_by", "created_at"),
            "sort_order": request.args.get("sort_order", "desc"),
        }
        return jsonify(crm_service.list_customers(filters))

    except Exception as e:
        current_app.logger.error(f"Error getting customers: {e}")
        return jsonify({"error": "خطا در دریافت مشتریان"}), 500


@crm_bp.post("/customers")
@require_role("business_expert")
def create_customer():
    """Create a new customer."""
    try:
        data = request.get_json()
        
        customer = crm_write_service.create_customer(data)
        
        return jsonify({
            "message": "مشتری با موفقیت ایجاد شد",
            "customer_id": customer.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating customer: {e}")
        return jsonify({"error": "خطا در ایجاد مشتری"}), 500


@crm_bp.get("/customers/<int:customer_id>")
@require_role("business_expert")
def get_customer_detail(customer_id: int):
    """Get detailed information about a customer."""
    try:
        customer_payload = crm_service.get_customer_detail(customer_id)
        if not customer_payload:
            return jsonify({"error": "مشتری یافت نشد"}), 404
        return jsonify(customer_payload)

    except Exception as e:
        current_app.logger.error(f"Error getting customer detail: {e}")
        return jsonify({"error": "خطا در دریافت جزئیات مشتری"}), 500


@crm_bp.put("/customers/<int:customer_id>")
@require_role("business_expert")
def update_customer(customer_id: int):
    """Update customer information."""
    try:
        data = request.get_json()
        customer = crm_write_service.update_customer(customer_id, data)
        
        if not customer:
            return jsonify({"error": "مشتری یافت نشد"}), 404
        
        return jsonify({"message": "اطلاعات مشتری به‌روزرسانی شد"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating customer: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی مشتری"}), 500


# Opportunity Management Routes
@crm_bp.get("/opportunities")
@require_role("business_expert")
def get_opportunities():
    """Get filtered and paginated opportunities."""
    try:
        filters = {
            "page": request.args.get("page", 1, type=int),
            "per_page": min(request.args.get("per_page", 20, type=int), 100),
            "stage": request.args.get("stage"),
            "assigned_to": request.args.get("assigned_to"),
            "search": request.args.get("search"),
        }
        return jsonify(crm_service.list_opportunities(filters))

    except Exception as e:
        current_app.logger.error(f"Error getting opportunities: {e}")
        return jsonify({"error": "خطا در دریافت فرصت‌های فروش"}), 500


@crm_bp.post("/opportunities")
@require_role("business_expert")
def create_opportunity():
    """Create a new opportunity."""
    try:
        data = request.get_json()
        
        opportunity = crm_write_service.create_opportunity(data)
        
        return jsonify({
            "message": "فرصت فروش با موفقیت ایجاد شد",
            "opportunity_id": opportunity.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating opportunity: {e}")
        return jsonify({"error": "خطا در ایجاد فرصت فروش"}), 500


# Activity Management Routes
@crm_bp.get("/activities")
@require_role("business_expert")
def get_activities():
    """Get filtered and paginated activities."""
    try:
        filters = {
            "page": request.args.get("page", 1, type=int),
            "per_page": min(request.args.get("per_page", 20, type=int), 100),
            "activity_type": request.args.get("activity_type"),
            "expert_id": request.args.get("expert_id"),
            "customer_id": request.args.get("customer_id"),
            "status": request.args.get("status"),
        }
        return jsonify(crm_service.list_activities(filters))

    except Exception as e:
        current_app.logger.error(f"Error getting activities: {e}")
        return jsonify({"error": "خطا در دریافت فعالیت‌ها"}), 500


@crm_bp.post("/activities")
@require_role("business_expert")
def create_activity():
    """Create a new activity."""
    try:
        data = request.get_json()
        
        activity = crm_write_service.create_activity(data)
        
        return jsonify({
            "message": "فعالیت با موفقیت ایجاد شد",
            "activity_id": activity.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating activity: {e}")
        return jsonify({"error": "خطا در ایجاد فعالیت"}), 500


# Dashboard and Analytics Routes
@crm_bp.get("/dashboard/kpis")
@require_role("business_expert")
def get_crm_dashboard_kpis():
    """Get CRM dashboard KPIs."""
    try:
        return jsonify(crm_dashboard_service.get_crm_dashboard_kpis())

    except Exception as e:
        current_app.logger.error(f"Error getting CRM KPIs: {e}")
        return jsonify({"error": "خطا در دریافت آمار CRM"}), 500


@crm_bp.get("/ping")
def ping():
    """Health check endpoint for CRM API."""
    return jsonify({"message": "CRM API is running"})
