"""Internal-only lifecycle invariants for dormant notification records.

This module owns no event mapping, recipient/channel policy, provider, worker,
scheduler, API, or delivery behavior. Every operation is an explicit command.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.notification_models import NotificationAction, NotificationAttempt
from backend.operational_models import utcnow


class NotificationLifecycleError(RuntimeError):
    """Base predictable failure for internal notification lifecycle commands."""


class NotificationNotFound(NotificationLifecycleError):
    pass


class IdempotencyConflict(NotificationLifecycleError):
    pass


class InvalidTransition(NotificationLifecycleError):
    pass


class ClaimUnavailable(NotificationLifecycleError):
    pass


class StaleClaim(NotificationLifecycleError):
    pass


class StaleAttempt(NotificationLifecycleError):
    pass


@dataclass(frozen=True)
class AttemptClaim:
    attempt_public_id: str
    token: str
    expires_at: datetime
    attempt_status: str


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _command_start() -> None:
    if db.session.new or db.session.dirty or db.session.deleted:
        raise NotificationLifecycleError(
            "NOTIFICATION_COMMAND_REQUIRES_CLEAN_UNIT_OF_WORK"
        )
    db.session.rollback()


def _bounded(value: str | None, maximum: int, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(field)
    return value


def _action_values(
    *,
    source_event_id: int | None,
    correlation_key: str | None,
    purpose: str,
    recipient_reference: str | None,
    channel: str | None,
) -> tuple[object, ...]:
    return (
        source_event_id,
        correlation_key,
        purpose,
        recipient_reference,
        channel,
    )


def _assert_equivalent_action(
    action: NotificationAction,
    *,
    source_event_id: int | None,
    correlation_key: str | None,
    purpose: str,
    recipient_reference: str | None,
    channel: str | None,
) -> None:
    existing = _action_values(
        source_event_id=action.source_event_id,
        correlation_key=action.correlation_key,
        purpose=action.purpose,
        recipient_reference=action.recipient_reference,
        channel=action.channel,
    )
    requested = _action_values(
        source_event_id=source_event_id,
        correlation_key=correlation_key,
        purpose=purpose,
        recipient_reference=recipient_reference,
        channel=channel,
    )
    if existing != requested:
        raise IdempotencyConflict("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_ACTION")


def create_or_get_action(
    *,
    organization_id: int,
    idempotency_key: str,
    purpose: str,
    source_event_id: int | None = None,
    correlation_key: str | None = None,
    recipient_reference: str | None = None,
    channel: str | None = None,
) -> NotificationAction:
    """Create one tenant-owned logical action or return its exact equivalent."""
    _command_start()
    idempotency_key = _bounded(idempotency_key, 160, "IDEMPOTENCY_KEY")  # type: ignore[assignment]
    purpose = _bounded(purpose, 80, "PURPOSE")  # type: ignore[assignment]
    correlation_key = _bounded(correlation_key, 160, "CORRELATION_KEY")
    recipient_reference = _bounded(
        recipient_reference, 255, "RECIPIENT_REFERENCE"
    )
    channel = _bounded(channel, 32, "CHANNEL")

    query = select(NotificationAction).where(
        NotificationAction.organization_id == organization_id,
        NotificationAction.idempotency_key == idempotency_key,
    )
    existing = db.session.scalar(query)
    if existing is not None:
        _assert_equivalent_action(
            existing,
            source_event_id=source_event_id,
            correlation_key=correlation_key,
            purpose=purpose,
            recipient_reference=recipient_reference,
            channel=channel,
        )
        db.session.commit()
        return existing

    action = NotificationAction(
        organization_id=organization_id,
        source_event_id=source_event_id,
        idempotency_key=idempotency_key,
        correlation_key=correlation_key,
        purpose=purpose,
        recipient_reference=recipient_reference,
        channel=channel,
    )
    try:
        with db.session.begin_nested():
            db.session.add(action)
            db.session.flush()
    except IntegrityError:
        existing = db.session.scalar(query)
        if existing is None:
            db.session.rollback()
            raise
        _assert_equivalent_action(
            existing,
            source_event_id=source_event_id,
            correlation_key=correlation_key,
            purpose=purpose,
            recipient_reference=recipient_reference,
            channel=channel,
        )
        db.session.commit()
        return existing
    db.session.commit()
    return action


def _lock_action(organization_id: int, public_id: str) -> NotificationAction:
    action = db.session.scalar(
        select(NotificationAction)
        .where(
            NotificationAction.organization_id == organization_id,
            NotificationAction.public_id == public_id,
        )
        .with_for_update()
    )
    if action is None:
        raise NotificationNotFound("NOTIFICATION_ACTION_NOT_AVAILABLE")
    return action


def _lock_attempt(
    organization_id: int, attempt_public_id: str
) -> tuple[NotificationAction, NotificationAttempt]:
    identity = db.session.execute(
        select(NotificationAttempt.action_id).where(
            NotificationAttempt.organization_id == organization_id,
            NotificationAttempt.public_id == attempt_public_id,
        )
    ).scalar_one_or_none()
    if identity is None:
        raise NotificationNotFound("NOTIFICATION_ATTEMPT_NOT_AVAILABLE")
    action = db.session.scalar(
        select(NotificationAction)
        .where(
            NotificationAction.id == identity,
            NotificationAction.organization_id == organization_id,
        )
        .with_for_update()
    )
    attempt = db.session.scalar(
        select(NotificationAttempt)
        .where(
            NotificationAttempt.organization_id == organization_id,
            NotificationAttempt.action_id == identity,
            NotificationAttempt.public_id == attempt_public_id,
        )
        .with_for_update()
    )
    if action is None or attempt is None:
        raise NotificationNotFound("NOTIFICATION_ATTEMPT_NOT_AVAILABLE")
    return action, attempt


def _latest_attempt(action: NotificationAction) -> NotificationAttempt | None:
    return db.session.scalar(
        select(NotificationAttempt)
        .where(
            NotificationAttempt.organization_id == action.organization_id,
            NotificationAttempt.action_id == action.id,
        )
        .order_by(NotificationAttempt.attempt_number.desc())
        .limit(1)
        .with_for_update()
    )


def _require_latest(
    action: NotificationAction, attempt: NotificationAttempt
) -> None:
    latest = _latest_attempt(action)
    if latest is None or latest.id != attempt.id:
        raise StaleAttempt("ATTEMPT_SUPERSEDED")


def create_attempt(
    *, organization_id: int, action_public_id: str
) -> NotificationAttempt:
    """Create the single next pending attempt under an action row lock."""
    _command_start()
    try:
        action = _lock_action(organization_id, action_public_id)
        latest = _latest_attempt(action)
        if action.status in {"COMPLETED", "CANCELLED"}:
            raise InvalidTransition("TERMINAL_ACTION_CANNOT_CREATE_ATTEMPT")
        if latest is not None and latest.status in {"PENDING", "IN_PROGRESS", "UNKNOWN"}:
            db.session.commit()
            return latest
        if action.status not in {"PENDING", "FAILED"}:
            raise InvalidTransition("ACTION_NOT_READY_FOR_ATTEMPT")
        next_number = 1 if latest is None else latest.attempt_number + 1
        attempt = NotificationAttempt(
            organization_id=organization_id,
            action_id=action.id,
            attempt_number=next_number,
        )
        db.session.add(attempt)
        action.status = "PENDING"
        db.session.commit()
        return attempt
    except Exception:
        db.session.rollback()
        raise


def claim_attempt(
    *,
    organization_id: int,
    attempt_public_id: str,
    lease_seconds: int,
    now: datetime | None = None,
) -> AttemptClaim:
    """Claim pending work, or re-fence expired/UNKNOWN work, without executing it."""
    if not isinstance(lease_seconds, int) or not 1 <= lease_seconds <= 3600:
        raise ValueError("LEASE_SECONDS")
    _command_start()
    current = _aware(now or utcnow())
    try:
        action, attempt = _lock_attempt(organization_id, attempt_public_id)
        _require_latest(action, attempt)
        if action.status in {"COMPLETED", "CANCELLED"}:
            raise InvalidTransition("TERMINAL_ACTION_CANNOT_BE_CLAIMED")
        if attempt.status in {"SUCCEEDED", "FAILED"}:
            raise InvalidTransition("TERMINAL_ATTEMPT_CANNOT_BE_CLAIMED")
        if attempt.claim_token is not None:
            expires_at = _aware(attempt.claim_expires_at)
            if expires_at > current:
                raise ClaimUnavailable("ATTEMPT_ALREADY_CLAIMED")
            if attempt.status == "IN_PROGRESS":
                attempt.status = "UNKNOWN"
                attempt.result_code = "LEASE_EXPIRED"
                action.status = "IN_PROGRESS"

        token = str(uuid4())
        expires_at = current + timedelta(seconds=lease_seconds)
        attempt.claim_token = token
        attempt.claim_expires_at = expires_at
        if attempt.status == "PENDING":
            attempt.status = "IN_PROGRESS"
            attempt.attempted_at = current
            action.status = "IN_PROGRESS"
        db.session.commit()
        return AttemptClaim(
            attempt_public_id=attempt.public_id,
            token=token,
            expires_at=expires_at,
            attempt_status=attempt.status,
        )
    except Exception:
        db.session.rollback()
        raise


def expire_claim(
    *,
    organization_id: int,
    attempt_public_id: str,
    claim_token: str,
    now: datetime | None = None,
) -> NotificationAttempt:
    """Explicitly mark an expired ambiguous claim UNKNOWN; no scheduler is used."""
    _command_start()
    current = _aware(now or utcnow())
    try:
        action, attempt = _lock_attempt(organization_id, attempt_public_id)
        _require_latest(action, attempt)
        if attempt.claim_token != claim_token:
            raise StaleClaim("CLAIM_FENCE_MISMATCH")
        if attempt.claim_expires_at is None or _aware(attempt.claim_expires_at) > current:
            raise ClaimUnavailable("CLAIM_LEASE_STILL_ACTIVE")
        if attempt.status not in {"IN_PROGRESS", "UNKNOWN"}:
            raise InvalidTransition("CLAIM_NOT_EXPIRABLE")
        attempt.status = "UNKNOWN"
        attempt.result_code = "LEASE_EXPIRED"
        attempt.claim_token = None
        attempt.claim_expires_at = None
        action.status = "IN_PROGRESS"
        db.session.commit()
        return attempt
    except Exception:
        db.session.rollback()
        raise


def _same_result(
    attempt: NotificationAttempt,
    *,
    outcome: str,
    result_code: str | None,
    provider_reference: str | None,
    failure_code: str | None,
    failure_summary: str | None,
) -> bool:
    return (
        attempt.status == outcome
        and attempt.result_code == result_code
        and attempt.provider_reference == provider_reference
        and attempt.failure_code == failure_code
        and attempt.failure_summary == failure_summary
    )


def _record_result(
    *,
    organization_id: int,
    attempt_public_id: str,
    claim_token: str,
    outcome: str,
    result_code: str | None,
    provider_reference: str | None,
    failure_code: str | None,
    failure_summary: str | None,
    now: datetime | None,
    require_unknown: bool,
) -> NotificationAttempt:
    if outcome not in {"SUCCEEDED", "FAILED", "UNKNOWN"}:
        raise ValueError("OUTCOME")
    result_code = _bounded(result_code, 80, "RESULT_CODE")
    provider_reference = _bounded(provider_reference, 160, "PROVIDER_REFERENCE")
    failure_code = _bounded(failure_code, 80, "FAILURE_CODE")
    failure_summary = _bounded(failure_summary, 255, "FAILURE_SUMMARY")
    if outcome == "FAILED" and not failure_code:
        raise ValueError("FAILURE_CODE_REQUIRED")
    if outcome != "FAILED" and (failure_code is not None or failure_summary is not None):
        raise ValueError("FAILURE_FIELDS_REQUIRE_FAILED_OUTCOME")

    _command_start()
    current = _aware(now or utcnow())
    try:
        action, attempt = _lock_attempt(organization_id, attempt_public_id)
        _require_latest(action, attempt)
        if attempt.claim_token != claim_token:
            raise StaleClaim("CLAIM_FENCE_MISMATCH")
        if _same_result(
            attempt,
            outcome=outcome,
            result_code=result_code,
            provider_reference=provider_reference,
            failure_code=failure_code,
            failure_summary=failure_summary,
        ):
            db.session.commit()
            return attempt
        if require_unknown and attempt.status != "UNKNOWN":
            raise InvalidTransition("RECONCILIATION_REQUIRES_UNKNOWN")
        if attempt.status not in {"IN_PROGRESS", "UNKNOWN"}:
            raise InvalidTransition("ATTEMPT_NOT_RESULT_WRITABLE")
        if attempt.claim_expires_at is None or _aware(attempt.claim_expires_at) <= current:
            attempt.status = "UNKNOWN"
            attempt.result_code = "LEASE_EXPIRED"
            attempt.claim_token = None
            attempt.claim_expires_at = None
            action.status = "IN_PROGRESS"
            db.session.commit()
            raise StaleClaim("CLAIM_LEASE_EXPIRED")

        attempt.status = outcome
        attempt.result_code = result_code
        attempt.provider_reference = provider_reference
        attempt.failure_code = failure_code
        attempt.failure_summary = failure_summary
        if outcome == "UNKNOWN":
            action.status = "IN_PROGRESS"
            attempt.completed_at = None
            attempt.delivered_at = None
        elif outcome == "SUCCEEDED":
            action.status = "COMPLETED"
            attempt.completed_at = current
            attempt.delivered_at = current
        else:
            action.status = "FAILED"
            attempt.completed_at = current
            attempt.delivered_at = None
        db.session.commit()
        return attempt
    except StaleClaim as exc:
        if str(exc) == "CLAIM_LEASE_EXPIRED":
            raise
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


def record_result(
    *,
    organization_id: int,
    attempt_public_id: str,
    claim_token: str,
    outcome: str,
    result_code: str | None = None,
    provider_reference: str | None = None,
    failure_code: str | None = None,
    failure_summary: str | None = None,
    now: datetime | None = None,
) -> NotificationAttempt:
    return _record_result(
        organization_id=organization_id,
        attempt_public_id=attempt_public_id,
        claim_token=claim_token,
        outcome=outcome,
        result_code=result_code,
        provider_reference=provider_reference,
        failure_code=failure_code,
        failure_summary=failure_summary,
        now=now,
        require_unknown=False,
    )


def reconcile_unknown(
    *,
    organization_id: int,
    attempt_public_id: str,
    claim_token: str,
    outcome: str,
    result_code: str | None = None,
    provider_reference: str | None = None,
    failure_code: str | None = None,
    failure_summary: str | None = None,
    now: datetime | None = None,
) -> NotificationAttempt:
    """Resolve current UNKNOWN evidence without sending or creating an attempt."""
    if outcome not in {"SUCCEEDED", "FAILED"}:
        raise ValueError("RECONCILIATION_OUTCOME")
    return _record_result(
        organization_id=organization_id,
        attempt_public_id=attempt_public_id,
        claim_token=claim_token,
        outcome=outcome,
        result_code=result_code,
        provider_reference=provider_reference,
        failure_code=failure_code,
        failure_summary=failure_summary,
        now=now,
        require_unknown=True,
    )


def cancel_action(*, organization_id: int, action_public_id: str) -> NotificationAction:
    """Cancel only dormant or explicitly failed work; never reopen terminal work."""
    _command_start()
    try:
        action = _lock_action(organization_id, action_public_id)
        if action.status == "CANCELLED":
            db.session.commit()
            return action
        if action.status not in {"PENDING", "FAILED"}:
            raise InvalidTransition("ACTION_NOT_CANCELLABLE")
        latest = _latest_attempt(action)
        if latest is not None and latest.status in {"IN_PROGRESS", "UNKNOWN"}:
            raise InvalidTransition("ACTIVE_OR_UNKNOWN_ATTEMPT_NOT_CANCELLABLE")
        action.status = "CANCELLED"
        db.session.commit()
        return action
    except Exception:
        db.session.rollback()
        raise


__all__ = [
    "AttemptClaim",
    "ClaimUnavailable",
    "IdempotencyConflict",
    "InvalidTransition",
    "NotificationLifecycleError",
    "NotificationNotFound",
    "StaleAttempt",
    "StaleClaim",
    "cancel_action",
    "claim_attempt",
    "create_attempt",
    "create_or_get_action",
    "expire_claim",
    "reconcile_unknown",
    "record_result",
]
