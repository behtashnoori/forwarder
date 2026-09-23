"""Password and account lifecycle primitives for Customer Portal identities."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from flask import current_app

from backend.extensions import db
from backend.models import (
    CustomerGamification,
    CustomerPortalAccountAudit,
    CustomerPortalRecoveryRequest,
    CustomerPortalRecoveryToken,
)
from backend.security import security
from backend.services import customer_recovery_email_service
from backend.services.customer_portal_auth import CustomerPortalAuthError, normalize_email, validate_password


def _digest(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _revoke_open_tokens(customer_id: int, now: datetime) -> None:
    CustomerPortalRecoveryToken.query.filter(
        CustomerPortalRecoveryToken.customer_id == customer_id,
        CustomerPortalRecoveryToken.used_at.is_(None),
        CustomerPortalRecoveryToken.revoked_at.is_(None),
    ).update({"revoked_at": now}, synchronize_session=False)


def _audit(customer: CustomerGamification, action: str, source: str, *, actor_user_id: int | None = None, detail: str | None = None) -> None:
    db.session.add(CustomerPortalAccountAudit(
        customer_id=customer.id,
        operational_organization_id=customer.operational_organization_id,
        actor_user_id=actor_user_id,
        action=action,
        source=source,
        detail=detail,
    ))


def request_password_recovery(email: Any) -> None:
    """Attempt email delivery while preserving an account-existence-safe response."""
    customer = CustomerGamification.query.filter_by(email=normalize_email(email)).first()
    if customer is not None and customer.account_status == "ACTIVE" and customer.password_hash:
        initiate_password_recovery(customer, source="customer_forgot")


def queue_admin_recovery_request(customer: CustomerGamification, actor_user_id: int, purpose: str) -> CustomerPortalRecoveryRequest:
    row = CustomerPortalRecoveryRequest(
        customer_id=customer.id,
        purpose=purpose,
        delivery_channel="MANUAL_LINK",
        delivery_status="PENDING",
    )
    db.session.add(row)
    _audit(customer, "recovery_requested", "organization_admin", actor_user_id=actor_user_id, detail=f"purpose={purpose}")
    db.session.commit()
    return row


def initiate_password_recovery(
    customer: CustomerGamification,
    *,
    source: str,
    actor_user_id: int | None = None,
) -> str:
    """Issue and email a reset capability without exposing it to the caller."""
    if customer.account_status != "ACTIVE":
        raise CustomerPortalAuthError("Account is disabled.", 409, "ACCOUNT_DISABLED")
    if not customer.password_hash:
        raise CustomerPortalAuthError(
            "Account enrollment must be completed first.",
            409,
            "ACCOUNT_ENROLLMENT_REQUIRED",
        )
    row = CustomerPortalRecoveryRequest(
        customer_id=customer.id,
        purpose="RESET",
        delivery_channel="EMAIL",
        delivery_status="PENDING",
    )
    db.session.add(row)
    _audit(
        customer,
        "recovery_requested",
        source,
        actor_user_id=actor_user_id,
        detail="purpose=RESET;channel=EMAIL",
    )
    db.session.commit()

    raw_token = issue_recovery_token(
        customer,
        "RESET",
        created_by_user_id=actor_user_id,
        recovery_request=row,
    )
    token = CustomerPortalRecoveryToken.query.filter_by(token_digest=_digest(raw_token)).one()
    try:
        reset_url = customer_recovery_email_service.build_password_reset_url(raw_token)
        delivery_status = customer_recovery_email_service.send_password_recovery_email(
            customer.email,
            reset_url,
            token.expires_at,
        )
    except Exception as exc:
        current_app.logger.error(
            "Customer recovery delivery boundary failed closed (%s).",
            type(exc).__name__,
        )
        delivery_status = customer_recovery_email_service.DELIVERY_FAILED
    if delivery_status not in {
        customer_recovery_email_service.DELIVERY_SENT,
        customer_recovery_email_service.DELIVERY_FAILED,
        customer_recovery_email_service.DELIVERY_SUPPRESSED,
    }:
        delivery_status = customer_recovery_email_service.DELIVERY_FAILED
    now = datetime.utcnow()
    row.delivery_status = delivery_status
    row.delivery_attempted_at = now
    if delivery_status != customer_recovery_email_service.DELIVERY_SENT:
        token.revoked_at = now
    _audit(
        customer,
        f"recovery_email_{delivery_status.lower()}",
        source,
        actor_user_id=actor_user_id,
        detail="purpose=RESET;channel=EMAIL",
    )
    db.session.commit()
    return delivery_status


def issue_recovery_token(
    customer: CustomerGamification,
    purpose: str,
    *,
    created_by_user_id: int | None = None,
    recovery_request: CustomerPortalRecoveryRequest | None = None,
) -> str:
    """Issue a digest-only capability for an approved delivery adapter."""
    if purpose not in {"RESET", "ENROLLMENT"}:
        raise ValueError("Unsupported customer recovery token purpose")
    if customer.account_status != "ACTIVE":
        raise CustomerPortalAuthError("Account is disabled.", 409, "ACCOUNT_DISABLED")
    if purpose == "ENROLLMENT" and customer.password_hash:
        raise CustomerPortalAuthError("Account enrollment is already complete.", 409, "ACCOUNT_ALREADY_ENROLLED")
    if purpose == "RESET" and not customer.password_hash:
        raise CustomerPortalAuthError("Account enrollment must be completed first.", 409, "ACCOUNT_ENROLLMENT_REQUIRED")
    now = datetime.utcnow()
    raw_token = secrets.token_urlsafe(48)
    lifetime = int(current_app.config.get("CUSTOMER_RECOVERY_TOKEN_LIFETIME_SECONDS", 1800))
    _revoke_open_tokens(customer.id, now)
    db.session.add(CustomerPortalRecoveryToken(
        token_digest=_digest(raw_token), customer_id=customer.id, purpose=purpose,
        recovery_request_id=recovery_request.id if recovery_request else None,
        created_by_user_id=created_by_user_id, created_at=now,
        expires_at=now + timedelta(seconds=lifetime),
    ))
    _audit(customer, "token_issued", "organization_admin" if created_by_user_id else "system", actor_user_id=created_by_user_id, detail=f"purpose={purpose}")
    db.session.commit()
    return raw_token


def change_password(customer: CustomerGamification, current_password: Any, new_password: Any) -> None:
    validate_password(new_password)
    if not isinstance(current_password, str) or not customer.password_hash or not security.verify_password(current_password, customer.password_hash):
        raise CustomerPortalAuthError("Current password is incorrect.", 400, "CURRENT_PASSWORD_INVALID")
    now = datetime.utcnow()
    customer.password_hash = security.hash_password(new_password)
    customer.password_changed_at = now
    customer.session_generation = int(customer.session_generation or 0) + 1
    _revoke_open_tokens(customer.id, now)
    _audit(customer, "password_changed", "customer_session")
    db.session.commit()


def consume_recovery_token(raw_token: Any, new_password: Any, purpose: str) -> CustomerGamification:
    validate_password(new_password)
    if not isinstance(raw_token, str) or not raw_token:
        raise CustomerPortalAuthError("Recovery token is invalid or expired.", 400, "RECOVERY_TOKEN_INVALID")
    now = datetime.utcnow()
    token = CustomerPortalRecoveryToken.query.filter_by(
        token_digest=_digest(raw_token), purpose=purpose
    ).with_for_update().one_or_none()
    if token is None or token.used_at is not None or token.revoked_at is not None or token.expires_at <= now:
        raise CustomerPortalAuthError("Recovery token is invalid or expired.", 400, "RECOVERY_TOKEN_INVALID")
    customer = db.session.get(CustomerGamification, token.customer_id)
    if customer is None or customer.account_status != "ACTIVE":
        raise CustomerPortalAuthError("Recovery token is invalid or expired.", 400, "RECOVERY_TOKEN_INVALID")
    if purpose == "ENROLLMENT" and customer.password_hash:
        raise CustomerPortalAuthError("Recovery token is invalid or expired.", 400, "RECOVERY_TOKEN_INVALID")
    if purpose == "RESET" and not customer.password_hash:
        raise CustomerPortalAuthError("Recovery token is invalid or expired.", 400, "RECOVERY_TOKEN_INVALID")
    customer.password_hash = security.hash_password(new_password)
    customer.password_changed_at = now
    customer.session_generation = int(customer.session_generation or 0) + 1
    token.used_at = now
    if token.recovery_request is not None:
        token.recovery_request.handled_at = now
    CustomerPortalRecoveryToken.query.filter(
        CustomerPortalRecoveryToken.customer_id == customer.id,
        CustomerPortalRecoveryToken.id != token.id,
        CustomerPortalRecoveryToken.used_at.is_(None),
        CustomerPortalRecoveryToken.revoked_at.is_(None),
    ).update({"revoked_at": now}, synchronize_session=False)
    _audit(customer, "password_reset" if purpose == "RESET" else "enrollment_completed", "customer_token", detail=f"purpose={purpose}")
    db.session.commit()
    return customer


def set_account_enabled(customer: CustomerGamification, enabled: bool, actor_user_id: int) -> None:
    now = datetime.utcnow()
    customer.account_status = "ACTIVE" if enabled else "DISABLED"
    customer.disabled_at = None if enabled else now
    customer.disabled_by_user_id = None if enabled else actor_user_id
    customer.session_generation = int(customer.session_generation or 0) + 1
    if not enabled:
        _revoke_open_tokens(customer.id, now)
    _audit(
        customer,
        "account_enabled" if enabled else "account_disabled",
        "organization_admin",
        actor_user_id=actor_user_id,
    )
    db.session.commit()


__all__ = [
    "change_password", "consume_recovery_token", "issue_recovery_token",
    "initiate_password_recovery", "queue_admin_recovery_request",
    "request_password_recovery", "set_account_enabled",
]
