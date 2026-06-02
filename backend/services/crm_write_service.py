"""Write helpers for CRM route mutations."""
from datetime import datetime

from backend.extensions import db
from backend.models import Activity, Customer, Opportunity

CUSTOMER_WRITE_FIELDS = [
    "company_name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "mobile",
    "website",
    "industry",
    "company_size",
    "customer_type",
    "status",
    "source",
    "notes",
    "address",
    "city",
    "province",
    "postal_code",
    "country",
]


def create_customer(data: dict) -> Customer:
    """Create and commit a CRM customer using the existing route defaults."""
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
        country=data.get("country", "Iran"),
    )

    db.session.add(customer)
    db.session.commit()
    return customer


def update_customer(customer_id: int, data: dict) -> Customer | None:
    """Update and commit a CRM customer, or return None when absent."""
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    for field in CUSTOMER_WRITE_FIELDS:
        if field in data:
            setattr(customer, field, data[field])

    customer.updated_at = datetime.utcnow()
    db.session.commit()
    return customer


def create_opportunity(data: dict) -> Opportunity:
    """Create and commit a CRM opportunity using the existing route defaults."""
    opportunity = Opportunity(
        customer_id=data.get("customer_id"),
        title=data.get("title"),
        description=data.get("description"),
        stage=data.get("stage", "lead"),
        probability=data.get("probability", 0),
        value=data.get("value"),
        currency=data.get("currency", "IRR"),
        expected_close_date=datetime.strptime(data.get("expected_close_date"), "%Y-%m-%d").date()
        if data.get("expected_close_date")
        else None,
        source=data.get("source"),
        assigned_to=data.get("assigned_to"),
        notes=data.get("notes"),
    )

    db.session.add(opportunity)
    db.session.commit()
    return opportunity


def create_activity(data: dict) -> Activity:
    """Create and commit a CRM activity using the existing route defaults."""
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
        next_action=data.get("next_action"),
    )

    db.session.add(activity)
    db.session.commit()
    return activity
