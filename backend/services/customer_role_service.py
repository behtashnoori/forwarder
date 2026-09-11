"""Bounded Customer carrier-eligibility administration."""
from sqlalchemy import select
from backend.extensions import db
from backend.models import Customer, CustomerRoleAssignment
from backend.services.ownership_service import tenant_organization_for_user

def _customer(customer_id, user):
    return db.session.scalar(select(Customer).where(Customer.id == customer_id, Customer.ownership_scope == "TENANT", Customer.operational_organization_id == tenant_organization_for_user(user)))

def roles(customer_id, user):
    customer = _customer(customer_id, user)
    if not customer: return None
    row = db.session.scalar(select(CustomerRoleAssignment).where(CustomerRoleAssignment.customer_id == customer.id, CustomerRoleAssignment.role_code == "CARRIER"))
    return {"carrier_eligible": bool(row and row.is_active)}

def set_carrier(customer_id, active, user):
    customer = _customer(customer_id, user)
    if not customer: return False
    org = tenant_organization_for_user(user)
    row = db.session.scalar(select(CustomerRoleAssignment).where(CustomerRoleAssignment.customer_id == customer.id, CustomerRoleAssignment.role_code == "CARRIER"))
    if not row:
        db.session.add(CustomerRoleAssignment(customer_id=customer.id, operational_organization_id=org, role_code="CARRIER", is_active=active, created_by=int(user["id"]), updated_by=int(user["id"])))
    else:
        row.is_active = active; row.updated_by = int(user["id"])
    db.session.commit()
    return True
