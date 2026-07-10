"""Service helpers for manually linking CRM customers to shipment requests."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_

from backend.extensions import db
from backend.models import CRMCustomerLinkAudit, Customer, ExpertConsoleLog, ShipmentRequest


class CrmCustomerLinkError(Exception):
    """Base CRM customer-link exception with an HTTP status code."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CrmCustomerLinkValidationError(CrmCustomerLinkError):
    """Raised when link input is invalid."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class CrmCustomerLinkNotFoundError(CrmCustomerLinkError):
    """Raised when the target shipment request or CRM customer is missing."""


def build_customer_summary(customer: Customer | None) -> dict[str, Any] | None:
    """Return a compact customer payload for linking workflows."""
    if customer is None:
        return None

    return {
        "id": customer.id,
        "name": f"{customer.first_name} {customer.last_name}",
        "company_name": customer.company_name,
        "email": customer.email,
        "phone": customer.phone,
        "mobile": customer.mobile,
        "customer_type": customer.customer_type,
        "status": customer.status,
    }


def build_request_link_payload(
    shipment_request: ShipmentRequest,
    operation: str = "read",
) -> dict[str, Any]:
    """Return the current CRM link state for a shipment request."""
    return {
        "operation": operation,
        "shipment_request": {
            "id": shipment_request.id,
            "customer_id": shipment_request.customer_id,
            "status": shipment_request.status,
            "assigned_to": shipment_request.assigned_to,
            "gamification_customer_id": shipment_request.gamification_customer_id,
        },
        "customer": build_customer_summary(shipment_request.customer),
    }


def search_linkable_customers(filters: dict[str, Any]) -> dict[str, Any]:
    """Search CRM customers for manual shipment-request linking."""
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
                Customer.mobile.like(search_term),
            )
        )

    query = query.order_by(Customer.first_name.asc(), Customer.last_name.asc(), Customer.id.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "customers": [build_customer_summary(customer) for customer in pagination.items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    }


def get_request_customer_link(request_id: int) -> dict[str, Any]:
    """Return the CRM customer link state for a shipment request."""
    shipment_request = db.session.get(ShipmentRequest, request_id)
    if shipment_request is None:
        raise CrmCustomerLinkNotFoundError("Shipment request not found", 404)

    return build_request_link_payload(shipment_request)


def link_customer_to_request(
    request_id: int,
    payload: dict[str, Any],
    user: dict[str, Any],
    remote_addr: str | None = None,
) -> dict[str, Any]:
    """Manually link a shipment request to an existing CRM customer."""
    customer_id = payload.get("customer_id")
    if customer_id is None:
        raise CrmCustomerLinkValidationError("customer_id is required")

    try:
        customer_id = int(customer_id)
    except (TypeError, ValueError) as exc:
        raise CrmCustomerLinkValidationError("customer_id must be an integer") from exc

    shipment_request = db.session.get(ShipmentRequest, request_id)
    if shipment_request is None:
        raise CrmCustomerLinkNotFoundError("Shipment request not found", 404)

    customer = db.session.get(Customer, customer_id)
    if customer is None:
        raise CrmCustomerLinkNotFoundError("CRM customer not found", 404)

    old_customer_id = shipment_request.customer_id
    if old_customer_id == customer_id:
        operation = "noop"
    else:
        operation = "link" if old_customer_id is None else "relink"
        shipment_request.customer_id = customer_id
        add_customer_link_audit_records(
            shipment_request=shipment_request,
            user=user,
            operation=operation,
            old_customer_id=old_customer_id,
            new_customer_id=customer_id,
            note=payload.get("note"),
            remote_addr=remote_addr,
        )

    db.session.commit()
    return build_request_link_payload(shipment_request, operation)


def unlink_customer_from_request(
    request_id: int,
    payload: dict[str, Any],
    user: dict[str, Any],
    remote_addr: str | None = None,
) -> dict[str, Any]:
    """Remove a manual CRM customer link from a shipment request."""
    shipment_request = db.session.get(ShipmentRequest, request_id)
    if shipment_request is None:
        raise CrmCustomerLinkNotFoundError("Shipment request not found", 404)

    old_customer_id = shipment_request.customer_id
    if old_customer_id is None:
        operation = "noop"
    else:
        operation = "unlink"
        shipment_request.customer_id = None
        add_customer_link_audit_records(
            shipment_request=shipment_request,
            user=user,
            operation=operation,
            old_customer_id=old_customer_id,
            new_customer_id=None,
            note=payload.get("note"),
            remote_addr=remote_addr,
        )

    db.session.commit()
    return build_request_link_payload(shipment_request, operation)


def add_customer_link_audit_records(
    shipment_request: ShipmentRequest,
    user: dict[str, Any],
    operation: str,
    old_customer_id: int | None,
    new_customer_id: int | None,
    note: str | None,
    remote_addr: str | None,
) -> None:
    """Add structured CRM audit and existing console timeline records."""
    add_structured_customer_link_audit(
        shipment_request=shipment_request,
        user=user,
        operation=operation,
        old_customer_id=old_customer_id,
        new_customer_id=new_customer_id,
        note=note,
        remote_addr=remote_addr,
    )
    add_customer_link_console_log(
        shipment_request=shipment_request,
        user=user,
        operation=operation,
        old_customer_id=old_customer_id,
        new_customer_id=new_customer_id,
        note=note,
        remote_addr=remote_addr,
    )


def add_structured_customer_link_audit(
    shipment_request: ShipmentRequest,
    user: dict[str, Any],
    operation: str,
    old_customer_id: int | None,
    new_customer_id: int | None,
    note: str | None,
    remote_addr: str | None,
) -> None:
    """Add the durable structured CRM customer-link audit record."""
    db.session.add(
        CRMCustomerLinkAudit(
            shipment_request_id=shipment_request.id,
            old_customer_id=old_customer_id,
            new_customer_id=new_customer_id,
            operation=operation,
            performed_by_user_id=user.get("id"),
            performed_by_role=user.get("role"),
            source="crm_api",
            reason=note,
            request_status_at_time=shipment_request.status,
            assigned_to_at_time=shipment_request.assigned_to,
            gamification_customer_id_at_time=shipment_request.gamification_customer_id,
            ip_address=remote_addr,
            created_at=datetime.utcnow(),
        )
    )


def add_customer_link_console_log(
    shipment_request: ShipmentRequest,
    user: dict[str, Any],
    operation: str,
    old_customer_id: int | None,
    new_customer_id: int | None,
    note: str | None,
    remote_addr: str | None,
) -> None:
    """Add a minimal timeline record using the existing request log table."""
    audit_note = (
        f"CRM customer link {operation}: "
        f"old_customer_id={old_customer_id}; new_customer_id={new_customer_id}"
    )
    if note:
        audit_note = f"{audit_note}; note={note}"

    db.session.add(
        ExpertConsoleLog(
            shipment_request_id=shipment_request.id,
            expert_user_id=user.get("id"),
            action="crm_customer_link",
            old_status=shipment_request.status,
            new_status=shipment_request.status,
            note=audit_note,
            ip_address=remote_addr,
            created_at=datetime.utcnow(),
        )
    )
