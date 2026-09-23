"""Cookie-session authentication for optional Customer Portal accounts."""
from __future__ import annotations

import re
from datetime import datetime
from functools import wraps
from typing import Any, Callable, TypeVar

from flask import g, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import CustomerGamification
from backend.security import security

SESSION_CUSTOMER_ID = "customer_portal_customer_id"
SESSION_GENERATION = "customer_portal_session_generation"
SESSION_CSRF = "customer_portal_csrf"
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_F = TypeVar("_F", bound=Callable[..., Any])


class CustomerPortalAuthError(Exception):
    def __init__(self, message: str, status_code: int, code: str):
        super().__init__(message)
        self.message, self.status_code, self.code = message, status_code, code


def normalize_email(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def validate_password(password: Any) -> str:
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise CustomerPortalAuthError(
            "Password must be between 10 and 128 characters.", 400, "PASSWORD_POLICY_FAILED"
        )
    return password


def customer_summary(customer: CustomerGamification) -> dict[str, Any]:
    return {
        "public_id": customer.public_id,
        "email": customer.email,
        "phone": customer.phone,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "is_email_verified": bool(customer.is_email_verified),
        "account_status": customer.account_status,
        "total_requests": customer.total_requests,
        "completed_requests": customer.completed_requests,
        "loyalty_points": customer.loyalty_points,
        "customer_level": customer.customer_level,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


def _establish_session(customer: CustomerGamification) -> str:
    session.clear()
    session.permanent = True
    session[SESSION_CUSTOMER_ID] = int(customer.id)
    session[SESSION_GENERATION] = int(customer.session_generation or 0)
    session[SESSION_CSRF] = security.generate_csrf_token()
    customer.last_login_at = datetime.utcnow()
    return session[SESSION_CSRF]


def clear_customer_session() -> None:
    session.clear()


def resolve_customer_session() -> tuple[CustomerGamification | None, str | None]:
    customer_id = session.get(SESSION_CUSTOMER_ID)
    generation = session.get(SESSION_GENERATION)
    if customer_id is None or generation is None:
        return None, None
    try:
        customer = db.session.get(CustomerGamification, int(customer_id))
    except (TypeError, ValueError):
        clear_customer_session()
        return None, "INVALID_SESSION"
    if customer is None:
        clear_customer_session()
        return None, "INVALID_SESSION"
    if customer.account_status != "ACTIVE":
        clear_customer_session()
        return None, "ACCOUNT_DISABLED"
    try:
        generation_matches = int(customer.session_generation or 0) == int(generation)
    except (TypeError, ValueError):
        generation_matches = False
    if not generation_matches:
        clear_customer_session()
        return None, "SESSION_REVOKED"
    return customer, None


def current_customer() -> CustomerGamification | None:
    customer, _reason = resolve_customer_session()
    return customer


def session_payload(customer: CustomerGamification | None = None) -> dict[str, Any]:
    customer = customer or current_customer()
    if customer is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "csrf_token": session.get(SESSION_CSRF),
        "customer": customer_summary(customer),
    }


def register_customer(payload: dict[str, Any], *, organization_id: int | None) -> dict[str, Any]:
    email = normalize_email(payload.get("email"))
    phone = payload.get("phone", "").strip() if isinstance(payload.get("phone"), str) else ""
    password = validate_password(payload.get("password"))
    if not _EMAIL_RE.fullmatch(email):
        raise CustomerPortalAuthError("Invalid email address.", 400, "INVALID_EMAIL")
    if not (phone.startswith("09") and len(phone) == 11 and phone.isdigit()):
        raise CustomerPortalAuthError("Invalid phone number.", 400, "INVALID_PHONE")
    if CustomerGamification.query.filter_by(email=email).first() is not None:
        raise CustomerPortalAuthError("Account already exists.", 409, "ACCOUNT_EXISTS")
    customer = CustomerGamification(
        email=email,
        phone=phone,
        first_name=(payload.get("first_name") or "").strip() or None,
        last_name=(payload.get("last_name") or "").strip() or None,
        password_hash=security.hash_password(password),
        account_status="ACTIVE",
        operational_organization_id=organization_id,
        password_changed_at=datetime.utcnow(),
    )
    try:
        db.session.add(customer)
        db.session.flush()
        _establish_session(customer)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise CustomerPortalAuthError("Account already exists.", 409, "ACCOUNT_EXISTS") from exc
    return session_payload(customer)


def login_customer(payload: dict[str, Any]) -> dict[str, Any]:
    email = normalize_email(payload.get("email"))
    password = payload.get("password")
    customer = CustomerGamification.query.filter_by(email=email).first()
    if customer is not None and customer.account_status != "ACTIVE":
        raise CustomerPortalAuthError("Account is disabled.", 401, "ACCOUNT_DISABLED")
    if (
        customer is None
        or not customer.password_hash
        or not isinstance(password, str)
        or not security.verify_password(password, customer.password_hash)
    ):
        raise CustomerPortalAuthError("Invalid email or password.", 401, "INVALID_CREDENTIALS")
    _establish_session(customer)
    db.session.commit()
    return session_payload(customer)


def require_customer(fn: _F) -> _F:
    @wraps(fn)
    def wrapped(*args, **kwargs):
        customer, reason = resolve_customer_session()
        if customer is None:
            code = reason or "AUTHENTICATION_REQUIRED"
            return jsonify({"code": code, "message": "Customer authentication required."}), 401
        g.current_customer = customer
        return fn(*args, **kwargs)
    return wrapped  # type: ignore[return-value]


def require_customer_csrf(fn: _F) -> _F:
    @wraps(fn)
    @require_customer
    def wrapped(*args, **kwargs):
        supplied = request.headers.get("X-CSRF-Token", "")
        expected = session.get(SESSION_CSRF, "")
        if not supplied or not expected or not security.verify_csrf_token(supplied, expected):
            return jsonify({"code": "CSRF_FAILED", "message": "CSRF validation failed."}), 403
        return fn(*args, **kwargs)
    return wrapped  # type: ignore[return-value]


def error_payload(exc: CustomerPortalAuthError):
    return {"code": exc.code, "message": exc.message}, exc.status_code


__all__ = [
    "CustomerPortalAuthError", "clear_customer_session", "current_customer", "customer_summary",
    "error_payload", "login_customer", "register_customer", "require_customer",
    "require_customer_csrf", "session_payload", "validate_password",
]
