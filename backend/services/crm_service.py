"""Read helpers for CRM route payloads."""
from sqlalchemy import or_, desc

from backend.extensions import db
from backend.models import Customer, CustomerContact, Opportunity, Activity, ExpertUser, ShipmentRequest


def pagination_payload(pagination, page: int, per_page: int) -> dict:
    """Return the current pagination response shape."""
    return {
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


def build_customer_list_item(customer: Customer) -> dict:
    """Build a customer row for the CRM customers list."""
    return {
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
        "total_activities": len(customer.activities),
    }


def list_customers(filters: dict) -> dict:
    """Return filtered and paginated CRM customers."""
    page = filters["page"]
    per_page = filters["per_page"]
    query = db.session.query(Customer)

    search = filters.get("search")
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Customer.first_name.like(search_term),
                Customer.last_name.like(search_term),
                Customer.company_name.like(search_term),
                Customer.email.like(search_term),
                Customer.phone.like(search_term),
            )
        )

    customer_type = filters.get("customer_type")
    status = filters.get("status")
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)
    if status:
        query = query.filter(Customer.status == status)

    sort_by = filters.get("sort_by", "created_at")
    sort_order = filters.get("sort_order", "desc")
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

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "customers": [build_customer_list_item(customer) for customer in pagination.items],
        "pagination": pagination_payload(pagination, page, per_page),
    }


def get_customer_detail(customer_id: int):
    """Return detailed information about a customer, or None when absent."""
    customer = db.session.query(Customer).get(customer_id)
    if not customer:
        return None

    contacts = db.session.query(CustomerContact).filter(
        CustomerContact.customer_id == customer_id
    ).all()
    opportunities = db.session.query(Opportunity).filter(
        Opportunity.customer_id == customer_id
    ).all()
    activities = db.session.query(Activity).filter(
        Activity.customer_id == customer_id
    ).order_by(desc(Activity.created_at)).limit(10).all()

    return build_customer_detail_payload(customer, contacts, opportunities, activities)


def build_customer_detail_payload(customer: Customer, contacts, opportunities, activities) -> dict:
    """Build the CRM customer detail payload."""
    contacts_data = []
    for contact in contacts:
        contacts_data.append({
            "id": contact.id,
            "name": f"{contact.first_name} {contact.last_name}",
            "email": contact.email,
            "phone": contact.phone,
            "position": contact.position,
            "is_primary": contact.is_primary,
            "is_decision_maker": contact.is_decision_maker,
        })

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
            "created_at": opp.created_at.isoformat(),
        })

    activities_data = []
    for activity in activities:
        activities_data.append({
            "id": activity.id,
            "type": activity.activity_type,
            "subject": activity.subject,
            "status": activity.status,
            "created_at": activity.created_at.isoformat(),
            "expert": activity.expert_user.full_name if activity.expert_user else "نامشخص",
        })

    return {
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
        "recent_activities": activities_data,
    }


def list_opportunities(filters: dict) -> dict:
    """Return filtered and paginated CRM opportunities."""
    page = filters["page"]
    per_page = filters["per_page"]
    query = db.session.query(Opportunity)

    stage = filters.get("stage")
    assigned_to = filters.get("assigned_to")
    search = filters.get("search")
    if stage:
        query = query.filter(Opportunity.stage == stage)
    if assigned_to:
        query = query.filter(Opportunity.assigned_to == assigned_to)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Opportunity.title.like(search_term),
                Opportunity.description.like(search_term),
            )
        )

    query = query.order_by(desc(Opportunity.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "opportunities": [build_opportunity_payload(opp) for opp in pagination.items],
        "pagination": pagination_payload(pagination, page, per_page),
    }


def build_opportunity_payload(opp: Opportunity) -> dict:
    """Build a CRM opportunity list payload."""
    customer = db.session.query(Customer).get(opp.customer_id)
    assigned_expert = db.session.query(ExpertUser).get(opp.assigned_to) if opp.assigned_to else None

    return {
        "id": opp.id,
        "title": opp.title,
        "customer": {
            "id": customer.id,
            "name": f"{customer.first_name} {customer.last_name}",
            "company_name": customer.company_name,
        } if customer else None,
        "stage": opp.stage,
        "value": opp.value,
        "probability": opp.probability,
        "status": opp.status,
        "expected_close_date": opp.expected_close_date.isoformat() if opp.expected_close_date else None,
        "assigned_to": {
            "id": assigned_expert.id,
            "name": assigned_expert.full_name,
        } if assigned_expert else None,
        "created_at": opp.created_at.isoformat(),
    }


def list_activities(filters: dict) -> dict:
    """Return filtered and paginated CRM activities."""
    page = filters["page"]
    per_page = filters["per_page"]
    query = db.session.query(Activity)

    activity_type = filters.get("activity_type")
    expert_id = filters.get("expert_id")
    customer_id = filters.get("customer_id")
    status = filters.get("status")
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    if expert_id:
        query = query.filter(Activity.expert_user_id == expert_id)
    if customer_id:
        query = query.filter(Activity.customer_id == customer_id)
    if status:
        query = query.filter(Activity.status == status)

    query = query.order_by(desc(Activity.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "activities": [build_activity_payload(activity) for activity in pagination.items],
        "pagination": pagination_payload(pagination, page, per_page),
    }


def build_activity_payload(activity: Activity) -> dict:
    """Build a CRM activity list payload."""
    customer = db.session.query(Customer).get(activity.customer_id) if activity.customer_id else None
    expert = db.session.query(ExpertUser).get(activity.expert_user_id)

    return {
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
            "name": f"{customer.first_name} {customer.last_name}",
        } if customer else None,
        "expert": {
            "id": expert.id,
            "name": expert.full_name,
        } if expert else None,
        "created_at": activity.created_at.isoformat(),
    }
