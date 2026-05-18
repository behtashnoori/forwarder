"""Read helpers for CRM dashboard payloads."""
from sqlalchemy import and_, desc, func

from backend.extensions import db
from backend.models import Activity, Customer, ExpertUser, Opportunity


def get_crm_dashboard_kpis() -> dict:
    """Return the CRM dashboard KPI payload."""
    total_customers = db.session.query(Customer).count()
    new_customers_this_month = db.session.query(Customer).filter(
        func.date_trunc('month', Customer.created_at) == func.date_trunc('month', func.now())
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
        customer = db.session.query(Customer).get(activity.customer_id) if activity.customer_id else None
        expert = db.session.query(ExpertUser).get(activity.expert_user_id)

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
