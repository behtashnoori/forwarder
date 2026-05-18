"""CRM API routes for customer, sales, and activity management."""
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from backend.extensions import db
from backend.security import require_role
from backend.models import Customer, Opportunity, Activity
from backend.services import crm_dashboard_service, crm_service

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
        
        customer = Customer(
            company_name=data.get("company_name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            mobile=data.get("mobile"),
            website=data.get("website"),
            industry=data.get("industry"),
            company_size=data.get("company_size"),
            customer_type=data.get("customer_type", "prospect"),
            status=data.get("status", "active"),
            source=data.get("source"),
            notes=data.get("notes"),
            address=data.get("address"),
            city=data.get("city"),
            province=data.get("province"),
            postal_code=data.get("postal_code"),
            country=data.get("country", "Iran")
        )
        
        db.session.add(customer)
        db.session.commit()
        
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
        customer = db.session.query(Customer).get(customer_id)
        
        if not customer:
            return jsonify({"error": "مشتری یافت نشد"}), 404
        
        # Update fields
        for field in ['company_name', 'first_name', 'last_name', 'email', 'phone', 
                     'mobile', 'website', 'industry', 'company_size', 'customer_type',
                     'status', 'source', 'notes', 'address', 'city', 'province',
                     'postal_code', 'country']:
            if field in data:
                setattr(customer, field, data[field])
        
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
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
        
        opportunity = Opportunity(
            customer_id=data.get("customer_id"),
            title=data.get("title"),
            description=data.get("description"),
            stage=data.get("stage", "lead"),
            probability=data.get("probability", 0),
            value=data.get("value"),
            currency=data.get("currency", "IRR"),
            expected_close_date=datetime.strptime(data.get("expected_close_date"), "%Y-%m-%d").date() if data.get("expected_close_date") else None,
            source=data.get("source"),
            assigned_to=data.get("assigned_to"),
            notes=data.get("notes")
        )
        
        db.session.add(opportunity)
        db.session.commit()
        
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
        
        activity = Activity(
            customer_id=data.get("customer_id"),
            opportunity_id=data.get("opportunity_id"),
            shipment_request_id=data.get("shipment_request_id"),
            expert_user_id=data.get("expert_user_id"),
            activity_type=data.get("activity_type"),
            subject=data.get("subject"),
            description=data.get("description"),
            priority=data.get("priority", "normal"),
            due_date=datetime.fromisoformat(data.get("due_date")) if data.get("due_date") else None,
            outcome=data.get("outcome"),
            next_action=data.get("next_action")
        )
        
        db.session.add(activity)
        db.session.commit()
        
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
