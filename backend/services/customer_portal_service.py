"""Private Customer Portal request and quote operations."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from sqlalchemy import or_

from backend.extensions import db
from backend.models import CustomerGamification, CustomerWorkflowStep, ExpertConsoleLog, ExpertQuote, ShipmentRequest
from backend.services.customer_portal_auth import customer_summary
from backend.services.request_transport_projection import project_existing_request_transport
from backend.services.shipment_service import build_legacy_cargo_payload, serialize_request_cargo_items

TERMINAL_REQUEST_STATUSES = {"won", "lost", "closed", "completed", "cancelled"}
VALID_RESPONSES = {"accepted", "discussion", "declined"}


class CustomerPortalError(Exception):
    def __init__(self, message: str, status_code: int, code: str):
        super().__init__(message)
        self.message, self.status_code, self.code = message, status_code, code


def _quote_payload(quote: ExpertQuote) -> dict[str, Any]:
    return {
        "public_id": quote.public_id,
        "amount": int(quote.amount) if quote.amount is not None else None,
        "currency": quote.currency,
        "note": quote.note,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "created_at": quote.created_at.isoformat() if quote.created_at else None,
        "customer_response": quote.customer_response,
        "customer_response_message": quote.customer_response_message,
        "response_version": int(quote.response_version or 0),
        "responded_at": quote.responded_at.isoformat() if quote.responded_at else None,
    }


def _request_summary(row: ShipmentRequest) -> dict[str, Any]:
    latest_quote = ExpertQuote.query.filter_by(shipment_request_id=row.id).order_by(
        ExpertQuote.created_at.desc(), ExpertQuote.id.desc()
    ).first()
    return {
        "public_id": row.public_id,
        "tracking_code": row.tracking_code,
        "shipping_type": row.shipping_type,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "request_transport_intent": (
            row.domestic_transport_method if row.shipping_type == "domestic"
            else row.international_transport_method
        ),
        "has_quote": latest_quote is not None,
        "quote_response": latest_quote.customer_response if latest_quote else None,
    }


def list_customer_requests(customer_id: int, page: int, per_page: int) -> dict[str, Any]:
    page, per_page = max(1, page), min(100, max(1, per_page))
    query = ShipmentRequest.query.filter_by(gamification_customer_id=customer_id).order_by(
        ShipmentRequest.created_at.desc(), ShipmentRequest.id.desc()
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    customer = db.session.get(CustomerGamification, customer_id)
    return {
        "customer": customer_summary(customer),
        "items": [_request_summary(row) for row in pagination.items],
        "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages, "has_next": pagination.has_next, "has_prev": pagination.has_prev},
    }


def customer_request_detail(customer_id: int, request_public_id: str) -> dict[str, Any]:
    row = ShipmentRequest.query.filter_by(
        public_id=request_public_id, gamification_customer_id=customer_id
    ).one_or_none()
    if row is None:
        raise CustomerPortalError("Not found", 404, "REQUEST_NOT_FOUND")
    quotes = ExpertQuote.query.filter_by(shipment_request_id=row.id).order_by(
        ExpertQuote.created_at.desc(), ExpertQuote.id.desc()
    ).all()
    workflow = CustomerWorkflowStep.query.filter_by(
        customer_id=customer_id, shipment_request_id=row.id
    ).order_by(CustomerWorkflowStep.step_order, CustomerWorkflowStep.id).all()
    return {
        **_request_summary(row),
        **project_existing_request_transport(row),
        "cargo_items": serialize_request_cargo_items(row),
        "legacy_cargo": build_legacy_cargo_payload(row),
        "pickup_date": row.pickup_date.isoformat() if row.pickup_date else None,
        "delivery_date": row.delivery_date.isoformat() if row.delivery_date else None,
        "workflow_steps": [{
            "name": step.step_name, "title": step.step_name,
            "is_completed": bool(step.is_completed),
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        } for step in workflow],
        "latest_quote": _quote_payload(quotes[0]) if quotes else None,
        "quote_history": [_quote_payload(quote) for quote in quotes],
    }


def _normalize_response(response: Any, message: Any) -> tuple[str, str | None]:
    if response not in VALID_RESPONSES:
        raise CustomerPortalError("Invalid quote response.", 400, "INVALID_QUOTE_RESPONSE")
    if response != "discussion":
        if message is not None and (not isinstance(message, str) or message.strip()):
            raise CustomerPortalError("Message is only allowed for discussion.", 400, "DISCUSSION_MESSAGE_NOT_ALLOWED")
        return response, None
    if not isinstance(message, str) or not message.strip():
        raise CustomerPortalError("Discussion message is required.", 400, "DISCUSSION_MESSAGE_REQUIRED")
    normalized = message.strip()
    if len(normalized) > 500 or "\n" in normalized or "\r" in normalized:
        raise CustomerPortalError("Discussion message is invalid.", 400, "DISCUSSION_MESSAGE_INVALID")
    return response, normalized


def respond_to_quote(
    customer_id: int,
    request_public_id: str,
    quote_public_id: str,
    payload: dict[str, Any],
    remote_addr: str | None,
) -> dict[str, Any]:
    response, message = _normalize_response(payload.get("response"), payload.get("message"))
    expected = payload.get("expected_response_version")
    if not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
        raise CustomerPortalError("Expected response version is required.", 400, "RESPONSE_VERSION_REQUIRED")
    row = ShipmentRequest.query.filter_by(
        public_id=request_public_id, gamification_customer_id=customer_id
    ).with_for_update().one_or_none()
    if row is None:
        raise CustomerPortalError("Not found", 404, "QUOTE_NOT_FOUND")
    quote = ExpertQuote.query.filter_by(
        public_id=quote_public_id, shipment_request_id=row.id
    ).with_for_update().one_or_none()
    latest = ExpertQuote.query.filter_by(shipment_request_id=row.id).order_by(
        ExpertQuote.created_at.desc(), ExpertQuote.id.desc()
    ).first()
    if quote is None or latest is None:
        raise CustomerPortalError("Not found", 404, "QUOTE_NOT_FOUND")
    if latest.id != quote.id:
        raise CustomerPortalError("Quote has been superseded.", 409, "QUOTE_SUPERSEDED")
    if quote.operational_organization_id != row.operational_organization_id:
        raise CustomerPortalError("Not found", 404, "QUOTE_NOT_FOUND")
    if row.status in TERMINAL_REQUEST_STATUSES:
        raise CustomerPortalError("Quote response is not allowed for this request.", 409, "QUOTE_RESPONSE_NOT_ALLOWED")
    if quote.valid_until is not None and quote.valid_until < date.today():
        raise CustomerPortalError("Quote has expired.", 400, "QUOTE_EXPIRED")
    current_version = int(quote.response_version or 0)
    if expected != current_version:
        raise CustomerPortalError("Quote response version conflict.", 409, "RESPONSE_VERSION_CONFLICT")
    if quote.customer_response is not None:
        if quote.customer_response == response and quote.customer_response_message == message:
            quote_payload = _quote_payload(quote)
            return {"code": "QUOTE_RESPONSE_REPLAYED", "message": "Quote response already recorded.", "quote": quote_payload, "latest_quote": quote_payload}
        raise CustomerPortalError("Quote already has a response.", 409, "QUOTE_RESPONSE_CONFLICT")
    now = datetime.utcnow()
    quote.customer_response = response
    quote.customer_response_message = message
    quote.responded_by_customer_id = customer_id
    quote.responded_at = now
    quote.response_version = current_version + 1
    row.last_customer_touch_at = now
    row.has_unread_for_assignee = True
    db.session.add(ExpertConsoleLog(
        operational_organization_id=row.operational_organization_id,
        shipment_request_id=row.id, expert_user_id=None,
        action="customer_quote_response", old_status=row.status, new_status=row.status,
        note=f"Customer recorded quote response: {response}", ip_address=remote_addr, created_at=now,
    ))
    db.session.commit()
    quote_payload = _quote_payload(quote)
    return {"code": "QUOTE_RESPONSE_RECORDED", "message": "Quote response recorded.", "quote": quote_payload, "latest_quote": quote_payload}


def list_tenant_accounts(organization_id: int, query_text: str, status: str | None, page: int, per_page: int) -> dict[str, Any]:
    page, per_page = max(1, page), min(100, max(1, per_page))
    query = CustomerGamification.query.filter_by(operational_organization_id=organization_id)
    if status in {"ACTIVE", "DISABLED"}:
        query = query.filter(CustomerGamification.account_status == status)
    if query_text:
        term = f"%{query_text.strip()}%"
        query = query.filter(or_(
            CustomerGamification.public_id.ilike(term),
            CustomerGamification.email.ilike(term),
            CustomerGamification.phone.ilike(term),
        ))
    pagination = query.order_by(CustomerGamification.created_at.desc(), CustomerGamification.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return {
        "items": [{
            "public_id": row.public_id, "email": row.email, "phone": row.phone,
            "first_name": row.first_name, "last_name": row.last_name,
            "is_email_verified": bool(row.is_email_verified),
            "account_status": row.account_status,
            "enrollment_state": "ENROLLED" if row.password_hash else "PENDING_ENROLLMENT",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "request_count": ShipmentRequest.query.filter_by(gamification_customer_id=row.id).count(),
            "linkage_source": "server_scoped_portal_identity",
        } for row in pagination.items],
        "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
    }


def tenant_account_or_404(organization_id: int, public_id: str) -> CustomerGamification:
    customer = CustomerGamification.query.filter_by(
        public_id=public_id, operational_organization_id=organization_id
    ).one_or_none()
    if customer is None:
        raise CustomerPortalError("Not found", 404, "ACCOUNT_NOT_FOUND")
    return customer


__all__ = [
    "CustomerPortalError", "customer_request_detail", "list_customer_requests",
    "list_tenant_accounts", "respond_to_quote", "tenant_account_or_404",
]
