"""Request-parented existing CRM Customer selection for the owning Expert."""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select

from backend.extensions import db
from backend.models import Customer, ExpertUser, ShipmentRequest
from backend.services.assigned_work_authorization import authorize_work_action
from backend.services.crm_customer_link_service import add_customer_link_audit_records


class ExpertRequestCustomerError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _actor_id(user: dict[str, Any] | None) -> int | None:
    try:
        return int((user or {}).get("id"))
    except (TypeError, ValueError):
        return None


def _authorized_request(
    request_id: int,
    user: dict[str, Any] | None,
    *,
    for_update: bool = False,
) -> ShipmentRequest:
    query = select(ShipmentRequest).where(ShipmentRequest.id == request_id)
    if for_update:
        query = query.with_for_update()
    row = db.session.scalar(query.execution_options(populate_existing=True))
    actor_id = _actor_id(user)
    actor = db.session.get(ExpertUser, actor_id) if actor_id is not None else None
    if (
        row is None
        or actor is None
        or not actor.is_active
        or (actor.authority or "EXPERT").upper() != "EXPERT"
        or row.assigned_to != actor_id
        or row.ownership_scope != "TENANT"
        or not authorize_work_action(user or {}, row, "request.read").allowed
    ):
        raise ExpertRequestCustomerError("درخواست یافت نشد", 404)
    return row


def _customer_summary(customer: Customer) -> dict[str, Any]:
    contact_name = " ".join(
        part.strip()
        for part in (customer.first_name or "", customer.last_name or "")
        if part.strip()
    )
    return {
        "id": customer.id,
        "name": contact_name or customer.company_name or "مشتری سازمان",
        "company_name": customer.company_name,
        "phone": customer.phone or customer.mobile,
        "email": customer.email,
    }


def _active_tenant_customers(row: ShipmentRequest):
    return db.session.query(Customer).filter(
        Customer.operational_organization_id == row.operational_organization_id,
        Customer.ownership_scope == "TENANT",
        Customer.status == "active",
    )


def get_link_state(request_id: int, user: dict[str, Any]) -> dict[str, Any]:
    row = _authorized_request(request_id, user)
    customer = None
    if row.customer_id is not None:
        customer = _active_tenant_customers(row).filter(Customer.id == row.customer_id).one_or_none()
    available_count = _active_tenant_customers(row).count()
    return {
        "operation": "read",
        "request_public_id": row.public_id,
        "customer": _customer_summary(customer) if customer else None,
        "has_available_customers": available_count > 0,
        "can_change": True,
    }


def search_candidates(
    request_id: int,
    user: dict[str, Any],
    *,
    search: str | None,
    page: int,
    per_page: int,
) -> dict[str, Any]:
    row = _authorized_request(request_id, user)
    page = max(1, page)
    per_page = min(50, max(1, per_page))
    query = _active_tenant_customers(row)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(
            Customer.first_name.ilike(pattern),
            Customer.last_name.ilike(pattern),
            Customer.company_name.ilike(pattern),
        ))
    pagination = query.order_by(
        Customer.company_name.asc(),
        Customer.first_name.asc(),
        Customer.last_name.asc(),
        Customer.id.asc(),
    ).paginate(page=page, per_page=per_page, error_out=False)
    return {
        "customers": [_customer_summary(customer) for customer in pagination.items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    }


def link_existing_customer(
    request_id: int,
    user: dict[str, Any],
    payload: dict[str, Any],
    remote_addr: str | None,
) -> dict[str, Any]:
    row = _authorized_request(request_id, user, for_update=True)
    try:
        customer_id = int(payload.get("customer_id"))
    except (TypeError, ValueError):
        raise ExpertRequestCustomerError("مشتری سازمان معتبر نیست", 404) from None
    customer = _active_tenant_customers(row).filter(Customer.id == customer_id).one_or_none()
    if customer is None:
        raise ExpertRequestCustomerError("مشتری سازمان معتبر نیست", 404)

    old_customer_id = row.customer_id
    if old_customer_id == customer.id:
        operation = "noop"
    else:
        operation = "link" if old_customer_id is None else "relink"
        row.customer_id = customer.id
        add_customer_link_audit_records(
            shipment_request=row,
            user=user,
            operation=operation,
            old_customer_id=old_customer_id,
            new_customer_id=customer.id,
            note=(payload.get("note") or "").strip() or None,
            remote_addr=remote_addr,
            source="expert_request_review",
        )
    db.session.commit()
    return {
        "operation": operation,
        "request_public_id": row.public_id,
        "customer": _customer_summary(customer),
        "has_available_customers": True,
        "can_change": True,
    }


__all__ = [
    "ExpertRequestCustomerError",
    "get_link_state",
    "link_existing_customer",
    "search_candidates",
]

