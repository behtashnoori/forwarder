"""Derived Expert Request commercial state; persisted lifecycle stays unchanged."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from backend.models import ExpertQuote, ShipmentRequest


TERMINAL_REQUEST_STATUSES = frozenset({"won", "lost", "closed"})
CUSTOMER_RESPONSE_STATES = frozenset({"accepted", "discussion", "declined"})


def latest_quote_id_expression():
    return (
        select(ExpertQuote.id)
        .where(ExpertQuote.shipment_request_id == ShipmentRequest.id)
        .order_by(ExpertQuote.created_at.desc(), ExpertQuote.id.desc())
        .limit(1)
        .correlate(ShipmentRequest)
        .scalar_subquery()
    )


def latest_quote_response_expression():
    latest_id = latest_quote_id_expression()
    return (
        select(ExpertQuote.customer_response)
        .where(ExpertQuote.id == latest_id)
        .correlate(ShipmentRequest)
        .scalar_subquery()
    )


def request_bucket_condition(bucket: str):
    """Return the SQL predicate used by both list rows and bucket counts."""
    latest_id = latest_quote_id_expression()
    latest_response = latest_quote_response_expression()
    if bucket == "all":
        return ShipmentRequest.id.is_not(None)
    if bucket in {"new", "assigned", "in_progress", "quoted"}:
        return ShipmentRequest.status == bucket
    if bucket == "waiting_for_customer":
        return (
            (ShipmentRequest.status == "waiting_for_customer")
            & latest_id.is_not(None)
            & latest_response.is_(None)
        )
    if bucket == "needs_action":
        return (
            ~ShipmentRequest.status.in_(TERMINAL_REQUEST_STATUSES)
            & latest_response.in_(CUSTOMER_RESPONSE_STATES)
        )
    if bucket == "completed":
        return ShipmentRequest.status.in_(TERMINAL_REQUEST_STATUSES)
    return None


def latest_quote_for_request(request_id: int) -> ExpertQuote | None:
    return (
        ExpertQuote.query.filter_by(shipment_request_id=request_id)
        .order_by(ExpertQuote.created_at.desc(), ExpertQuote.id.desc())
        .first()
    )


def commercial_status_label(status: str, customer_response: str | None) -> str:
    if status == "waiting_for_customer" and customer_response in CUSTOMER_RESPONSE_STATES:
        return "در انتظار جمع‌بندی کارشناس"
    return {
        "new": "ثبت شده",
        "assigned": "در انتظار بررسی",
        "in_progress": "در حال پیگیری",
        "quoted": "پیشنهاد آماده شده",
        "waiting_for_customer": "در انتظار مشتری",
        "won": "پذیرفته شد",
        "lost": "ردشده / از دست‌رفته",
        "closed": "بسته شده",
    }.get(status, "وضعیت نامشخص")


def build_commercial_projection(
    request_status: str,
    latest_quote: ExpertQuote | dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(latest_quote, dict):
        response = latest_quote.get("customer_response")
        has_quote = True
    else:
        response = latest_quote.customer_response if latest_quote is not None else None
        has_quote = latest_quote is not None

    if request_status in TERMINAL_REQUEST_STATUSES:
        next_action = {
            "code": "commercial_result_recorded",
            "actor": "none",
            "label_fa": "نتیجه تجاری ثبت شده است",
        }
    elif response == "accepted":
        next_action = {
            "code": "expert_finalize_accepted",
            "actor": "expert",
            "label_fa": "ثبت نتیجه تجاری توسط کارشناس",
        }
    elif response == "discussion":
        next_action = {
            "code": "expert_review_negotiation",
            "actor": "expert",
            "label_fa": "بررسی درخواست مذاکره و ارسال پیشنهاد جدید",
        }
    elif response == "declined":
        next_action = {
            "code": "expert_conclude_declined",
            "actor": "expert",
            "label_fa": "تعیین نتیجه تجاری توسط کارشناس",
        }
    elif has_quote:
        next_action = {
            "code": "waiting_for_customer",
            "actor": "customer",
            "label_fa": "در انتظار پاسخ مشتری",
        }
    elif request_status == "new":
        next_action = {
            "code": "expert_review_request",
            "actor": "expert",
            "label_fa": "بررسی و پذیرش درخواست توسط کارشناس",
        }
    else:
        next_action = {
            "code": "expert_continue_review",
            "actor": "expert",
            "label_fa": "ادامه بررسی تجاری توسط کارشناس",
        }

    return {
        "request_status": request_status,
        "request_status_label_fa": commercial_status_label(request_status, response),
        "latest_quote_response": response,
        "next_action": next_action,
    }


__all__ = [
    "CUSTOMER_RESPONSE_STATES",
    "TERMINAL_REQUEST_STATUSES",
    "build_commercial_projection",
    "commercial_status_label",
    "latest_quote_for_request",
    "request_bucket_condition",
]

