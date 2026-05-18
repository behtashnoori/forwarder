"""CRM API routes for customer, sales, and activity management."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.security import require_role
from backend.models import (
    Customer, CustomerContact, Opportunity, Activity, Task, Report,
    ExpertUser, ShipmentRequest
)

crm_bp = Blueprint("crm", __name__, url_prefix="/api/crm")


# Customer Management Routes
@crm_bp.get("/customers")
@require_role("business_expert")
def get_customers():
    """Get filtered and paginated customers."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        search = request.args.get("search")
        customer_type = request.args.get("customer_type")
        status = request.args.get("status")
        sort_by = request.args.get("sort_by", "created_at")
        sort_order = request.args.get("sort_order", "desc")
        
        query = db.session.query(Customer)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Customer.first_name.like(search_term),
                    Customer.last_name.like(search_term),
                    Customer.company_name.like(search_term),
                    Customer.email.like(search_term),
                    Customer.phone.like(search_term)
                )
            )
        
        if customer_type:
            query = query.filter(Customer.customer_type == customer_type)
        if status:
            query = query.filter(Customer.status == status)
        
        # Apply sorting
        if sort_by == "name":
            sort_column = Customer.first_name
        elif sort_by == "company":
            sort_column = Customer.company_name
        elif sort_by == "last_contact":
            sort_column = Customer.last_contact_at
        else:
            sort_column = Customer.created_at
            
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Get paginated results
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        customers_data = []
        for customer in pagination.items:
            customers_data.append({
                "id": customer.id,
                "name": f"{customer.first_name} {customer.last_name}",
                "company_name": customer.company_name,
                "email": customer.email,
                "phone": customer.phone,
                "customer_type": customer.customer_type,
                "status": customer.status,
                "industry": customer.industry,
                "last_contact_at": customer.last_contact_at.isoformat() if customer.last_contact_at else None,
                "created_at": customer.created_at.isoformat(),
                "total_opportunities": len(customer.opportunities),
                "total_activities": len(customer.activities)
            })
        
        return jsonify({
            "customers": customers_data,
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
        customer = db.session.query(Customer).get(customer_id)
        if not customer:
            return jsonify({"error": "مشتری یافت نشد"}), 404
        
        # Get related data
        contacts = db.session.query(CustomerContact).filter(
            CustomerContact.customer_id == customer_id
        ).all()
        
        opportunities = db.session.query(Opportunity).filter(
            Opportunity.customer_id == customer_id
        ).all()
        
        activities = db.session.query(Activity).filter(
            Activity.customer_id == customer_id
        ).order_by(desc(Activity.created_at)).limit(10).all()
        
        # Format contacts
        contacts_data = []
        for contact in contacts:
            contacts_data.append({
                "id": contact.id,
                "name": f"{contact.first_name} {contact.last_name}",
                "email": contact.email,
                "phone": contact.phone,
                "position": contact.position,
                "is_primary": contact.is_primary,
                "is_decision_maker": contact.is_decision_maker
            })
        
        # Format opportunities
        opportunities_data = []
        for opp in opportunities:
            opportunities_data.append({
                "id": opp.id,
                "title": opp.title,
                "stage": opp.stage,
                "value": opp.value,
                "probability": opp.probability,
                "status": opp.status,
                "expected_close_date": opp.expected_close_date.isoformat() if opp.expected_close_date else None,
                "created_at": opp.created_at.isoformat()
            })
        
        # Format activities
        activities_data = []
        for activity in activities:
            activities_data.append({
                "id": activity.id,
                "type": activity.activity_type,
                "subject": activity.subject,
                "status": activity.status,
                "created_at": activity.created_at.isoformat(),
                "expert": activity.expert_user.full_name if activity.expert_user else "نامشخص"
            })
        
        return jsonify({
            "id": customer.id,
            "name": f"{customer.first_name} {customer.last_name}",
            "company_name": customer.company_name,
            "email": customer.email,
            "phone": customer.phone,
            "mobile": customer.mobile,
            "website": customer.website,
            "industry": customer.industry,
            "company_size": customer.company_size,
            "customer_type": customer.customer_type,
            "status": customer.status,
            "source": customer.source,
            "notes": customer.notes,
            "address": customer.address,
            "city": customer.city,
            "province": customer.province,
            "postal_code": customer.postal_code,
            "country": customer.country,
            "last_contact_at": customer.last_contact_at.isoformat() if customer.last_contact_at else None,
            "created_at": customer.created_at.isoformat(),
            "contacts": contacts_data,
            "opportunities": opportunities_data,
            "recent_activities": activities_data
        })
        
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
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        stage = request.args.get("stage")
        assigned_to = request.args.get("assigned_to")
        search = request.args.get("search")
        
        query = db.session.query(Opportunity)
        
        # Apply filters
        if stage:
            query = query.filter(Opportunity.stage == stage)
        if assigned_to:
            query = query.filter(Opportunity.assigned_to == assigned_to)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Opportunity.title.like(search_term),
                    Opportunity.description.like(search_term)
                )
            )
        
        query = query.order_by(desc(Opportunity.created_at))
        
        # Get paginated results
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        opportunities_data = []
        for opp in pagination.items:
            customer = db.session.query(Customer).get(opp.customer_id)
            assigned_expert = db.session.query(ExpertUser).get(opp.assigned_to) if opp.assigned_to else None
            
            opportunities_data.append({
                "id": opp.id,
                "title": opp.title,
                "customer": {
                    "id": customer.id,
                    "name": f"{customer.first_name} {customer.last_name}",
                    "company_name": customer.company_name
                } if customer else None,
                "stage": opp.stage,
                "value": opp.value,
                "probability": opp.probability,
                "status": opp.status,
                "expected_close_date": opp.expected_close_date.isoformat() if opp.expected_close_date else None,
                "assigned_to": {
                    "id": assigned_expert.id,
                    "name": assigned_expert.full_name
                } if assigned_expert else None,
                "created_at": opp.created_at.isoformat()
            })
        
        return jsonify({
            "opportunities": opportunities_data,
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
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        activity_type = request.args.get("activity_type")
        expert_id = request.args.get("expert_id")
        customer_id = request.args.get("customer_id")
        status = request.args.get("status")
        
        query = db.session.query(Activity)
        
        # Apply filters
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        if expert_id:
            query = query.filter(Activity.expert_user_id == expert_id)
        if customer_id:
            query = query.filter(Activity.customer_id == customer_id)
        if status:
            query = query.filter(Activity.status == status)
        
        query = query.order_by(desc(Activity.created_at))
        
        # Get paginated results
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        activities_data = []
        for activity in pagination.items:
            customer = db.session.query(Customer).get(activity.customer_id) if activity.customer_id else None
            expert = db.session.query(ExpertUser).get(activity.expert_user_id)
            
            activities_data.append({
                "id": activity.id,
                "type": activity.activity_type,
                "subject": activity.subject,
                "description": activity.description,
                "status": activity.status,
                "priority": activity.priority,
                "due_date": activity.due_date.isoformat() if activity.due_date else None,
                "completed_at": activity.completed_at.isoformat() if activity.completed_at else None,
                "outcome": activity.outcome,
                "customer": {
                    "id": customer.id,
                    "name": f"{customer.first_name} {customer.last_name}"
                } if customer else None,
                "expert": {
                    "id": expert.id,
                    "name": expert.full_name
                } if expert else None,
                "created_at": activity.created_at.isoformat()
            })
        
        return jsonify({
            "activities": activities_data,
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
        # Customer metrics
        total_customers = db.session.query(Customer).count()
        new_customers_this_month = db.session.query(Customer).filter(
            func.date_trunc('month', Customer.created_at) == func.date_trunc('month', func.now())
        ).count()
        
        # Opportunity metrics
        total_opportunities = db.session.query(Opportunity).count()
        open_opportunities = db.session.query(Opportunity).filter(
            Opportunity.status == "open"
        ).count()
        won_opportunities = db.session.query(Opportunity).filter(
            Opportunity.status == "won"
        ).count()
        
        # Calculate total pipeline value
        pipeline_value = db.session.query(func.sum(Opportunity.value)).filter(
            and_(
                Opportunity.status == "open",
                Opportunity.value.isnot(None)
            )
        ).scalar() or 0
        
        # Activity metrics
        total_activities = db.session.query(Activity).count()
        completed_activities = db.session.query(Activity).filter(
            Activity.status == "completed"
        ).count()
        
        # Recent activities
        recent_activities = db.session.query(Activity).order_by(
            desc(Activity.created_at)
        ).limit(5).all()
        
        recent_activities_data = []
        for activity in recent_activities:
            customer = db.session.query(Customer).get(activity.customer_id) if activity.customer_id else None
            expert = db.session.query(ExpertUser).get(activity.expert_user_id)
            
            recent_activities_data.append({
                "id": activity.id,
                "type": activity.activity_type,
                "subject": activity.subject,
                "customer_name": f"{customer.first_name} {customer.last_name}" if customer else "نامشخص",
                "expert_name": expert.full_name if expert else "نامشخص",
                "created_at": activity.created_at.isoformat()
            })
        
        return jsonify({
            "customers": {
                "total": total_customers,
                "new_this_month": new_customers_this_month
            },
            "opportunities": {
                "total": total_opportunities,
                "open": open_opportunities,
                "won": won_opportunities,
                "pipeline_value": pipeline_value
            },
            "activities": {
                "total": total_activities,
                "completed": completed_activities
            },
            "recent_activities": recent_activities_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting CRM KPIs: {e}")
        return jsonify({"error": "خطا در دریافت آمار CRM"}), 500


@crm_bp.get("/ping")
def ping():
    """Health check endpoint for CRM API."""
    return jsonify({"message": "CRM API is running"})
