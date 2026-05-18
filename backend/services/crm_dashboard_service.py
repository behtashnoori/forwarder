"""Read helpers for CRM dashboard payloads."""
from datetime import UTC, datetime

from sqlalchemy import and_, desc, func

from backend.extensions import db
from backend.models import Activity, Customer, ExpertUser, Opportunity


def _current_month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return naive UTC datetime bounds for the current calendar month."""
    now = now or datetime.now(UTC).replace(tzinfo=None)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)
    return month_start, next_month_start


def get_crm_dashboard_kpis() -> dict:
    """Return the CRM dashboard KPI payload."""
    month_start, next_month_start = _current_month_bounds()

    total_customers = db.session.query(Customer).count()
    new_customers_this_month = db.session.query(Customer).filter(
        Customer.created_at >= month_start,
        Customer.created_at < next_month_start,
    ).count()

    total_opportunities = db.session.query(Opportunity).count()
    open_opportunities = db.session.query(Opportunity).filter(
        Opportunity.status == "open"
    ).count()
    won_opportunities = db.session.query(Opportunity).filter(
        Opportunity.status == "won"
    ).count()

    pipeline_value = db.session.query(func.sum(Opportunity.value)).filter(
        and_(
            Opportunity.status == "open",
            Opportunity.value.isnot(None),
        )
    ).scalar() or 0

    total_activities = db.session.query(Activity).count()
    completed_activities = db.session.query(Activity).filter(
        Activity.status == "completed"
    ).count()

    recent_activities = db.session.query(Activity).order_by(
        desc(Activity.created_at)
    ).limit(5).all()

    recent_activities_data = []
    for activity in recent_activities:
        customer = db.session.get(Customer, activity.customer_id) if activity.customer_id else None
        expert = db.session.get(ExpertUser, activity.expert_user_id)

        recent_activities_data.append({
            "id": activity.id,
            "type": activity.activity_type,
            "subject": activity.subject,
            "customer_name": f"{customer.first_name} {customer.last_name}" if customer else "نامشخص",
            "expert_name": expert.full_name if expert else "نامشخص",
            "created_at": activity.created_at.isoformat(),
        })

    return {
        "customers": {
            "total": total_customers,
            "new_this_month": new_customers_this_month,
        },
        "opportunities": {
            "total": total_opportunities,
            "open": open_opportunities,
            "won": won_opportunities,
            "pipeline_value": pipeline_value,
        },
        "activities": {
            "total": total_activities,
            "completed": completed_activities,
        },
        "recent_activities": recent_activities_data,
    }
