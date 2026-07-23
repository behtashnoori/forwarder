"""Service helpers for expert quote workflows."""
from datetime import date, datetime
from typing import Any, Optional

from backend.extensions import db
from backend.models import (
    ExpertConsoleLog,
    ExpertConsoleNotification,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)


class QuoteServiceError(Exception):
    """Base service exception that maps to the current quote API error payload."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QuoteValidationError(QuoteServiceError):
    """Raised for current quote validation failures."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class QuoteNotFoundError(QuoteServiceError):
    """Raised when the target request or expert is missing."""


class QuoteAccessError(QuoteServiceError):
    """Raised when the current user cannot access the quote target request."""


def create_quote_for_request(
    request_id: int,
    payload: dict[str, Any],
    user: dict[str, Any],
    remote_addr: Optional[str] = None,
) -> dict[str, Any]:
    """Create a quote and return the current POST quote response payload."""
    normalized = normalize_quote_payload(payload)
    expert_id = user["id"]

    req = get_quote_target_request_or_none(request_id)
    if not req:
        raise QuoteNotFoundError("درخواست یافت نشد", 404)
    if not can_access_quote_request(req, user):
        raise QuoteAccessError("شما به این درخواست دسترسی ندارید", 403)

    expert = db.session.get(ExpertUser, expert_id)
    if not expert:
        raise QuoteNotFoundError("کارشناس یافت نشد", 404)

    quote = ExpertQuote(
        shipment_request_id=request_id,
        amount=normalized["amount"],
        currency=normalized["currency"],
        note=normalized["note"],
        valid_until=normalized["valid_until"],
        created_by_expert_id=expert_id,
        created_at=datetime.utcnow(),
    )
    from backend.operational_models import OperationalMembership, OperationalOrganization
    memberships = db.session.query(OperationalMembership).join(
        OperationalOrganization,
        OperationalMembership.organization_id == OperationalOrganization.id,
    ).filter(
        OperationalMembership.user_id == expert_id,
        OperationalMembership.is_active.is_(True),
        OperationalOrganization.is_active.is_(True),
    ).all()
    if len(memberships) == 1:
        quote.operational_organization_id = memberships[0].organization_id
    db.session.add(quote)
    db.session.flush()

    old_status = req.status
    req.status = "waiting_for_customer"
    req.last_customer_touch_at = datetime.utcnow()
    req.has_unread_for_assignee = True

    log = ExpertConsoleLog(
        shipment_request_id=request_id,
        expert_user_id=expert_id,
        action="status_change",
        old_status=old_status,
        new_status="waiting_for_customer",
        note="ارسال پیشنهاد و انتظار پاسخ مشتری",
        ip_address=remote_addr,
        created_at=datetime.utcnow(),
    )
    db.session.add(log)

    if req.assigned_to:
        notification = ExpertConsoleNotification(
            expert_user_id=req.assigned_to,
            shipment_request_id=request_id,
            notification_type="quote_sent",
            title="پیشنهاد ارسال شد",
            message=f"پیشنهاد برای درخواست {request_id} ثبت و وضعیت به منتظر مشتری تغییر یافت",
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.session.add(notification)

    db.session.commit()

    return {
        "ok": True,
        "quote": build_quote_payload(quote),
        "request": {"id": req.id, "status": req.status},
    }


def get_latest_quote_for_request(request_id: int, user: dict[str, Any]) -> ExpertQuote | None:
    """Return latest quote for a request, preserving current not-found/access behavior."""
    req = get_quote_target_request_or_none(request_id)
    if not req:
        raise QuoteNotFoundError("درخواست یافت نشد", 404)
    if not can_access_quote_request(req, user):
        raise QuoteAccessError("شما به این درخواست دسترسی ندارید", 403)

    return (
        db.session.query(ExpertQuote)
        .filter(ExpertQuote.shipment_request_id == request_id)
        .order_by(ExpertQuote.created_at.desc())
        .first()
    )


def build_latest_quote_response_payload(quote: ExpertQuote | None) -> dict[str, Any]:
    """Build the current GET latest quote response payload."""
    return {"quote": build_quote_payload(quote, include_created_by=True) if quote else None}


def build_quote_payload(quote: ExpertQuote, include_created_by: bool = False) -> dict[str, Any]:
    """Build quote payloads used by current quote endpoints."""
    payload = {
        "id": quote.id,
        "amount": int(quote.amount) if quote.amount is not None else None,
        "currency": quote.currency or "IRR",
        "note": quote.note,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "created_at": quote.created_at.isoformat(),
        "customer_response": quote.customer_response,
        "responded_at": quote.responded_at.isoformat() if quote.responded_at else None,
    }
    if include_created_by:
        payload["created_by"] = quote.created_by_expert.full_name if quote.created_by_expert else None
    return payload


def normalize_quote_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize quote payload while preserving current tolerant parsing."""
    amount = payload.get("amount")
    currency = (payload.get("currency") or "IRR").strip() or "IRR"
    note = (payload.get("note") or "").strip() or None
    valid_until = payload.get("valid_until")

    if amount is None:
        raise QuoteValidationError("مبلغ الزامی است")
    try:
        amount_int = int(amount)
    except (TypeError, ValueError):
        raise QuoteValidationError("مبلغ باید عدد باشد") from None
    if amount_int < 0:
        raise QuoteValidationError("مبلغ نامعتبر است")

    valid_until_date = None
    if valid_until:
        try:
            valid_until_date = date.fromisoformat(valid_until.replace("Z", "").split("T")[0])
        except Exception:
            pass

    return {
        "amount": amount_int,
        "currency": currency,
        "note": note,
        "valid_until": valid_until_date,
    }


def get_quote_target_request_or_none(request_id: int) -> ShipmentRequest | None:
    """Return the target shipment request for quote operations, or None."""
    return db.session.get(ShipmentRequest, request_id)


def can_access_quote_request(req: ShipmentRequest, user: dict[str, Any] | None) -> bool:
    """Preserve current quote access behavior: admin or assigned expert only."""
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    return req.assigned_to == user.get("id")
