"""Focused provider-free tests for the inactive C2 lifecycle service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from backend import create_app
from backend.extensions import db
from backend.notification_models import NotificationAction, NotificationAttempt
from backend.operational_models import OperationalOrganization
from backend.services import notification_lifecycle_service as lifecycle


@pytest.fixture()
def lifecycle_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "phase-c2-lifecycle-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        db.create_all()
        first = OperationalOrganization(name="C2 tenant A")
        second = OperationalOrganization(name="C2 tenant B")
        db.session.add_all([first, second])
        db.session.commit()
        app.config["C2_ORGANIZATIONS"] = (first.id, second.id)
        yield app
        db.session.remove()
        db.drop_all()


def _action(organization_id: int, key: str = "c2-action") -> NotificationAction:
    return lifecycle.create_or_get_action(
        organization_id=organization_id,
        idempotency_key=key,
        purpose="SYNTHETIC_LIFECYCLE_PROOF",
    )


def test_action_creation_is_idempotent_tenant_scoped_and_conflict_safe(lifecycle_app):
    with lifecycle_app.app_context():
        tenant_a, tenant_b = lifecycle_app.config["C2_ORGANIZATIONS"]
        first = _action(tenant_a, "same-key")
        repeated = _action(tenant_a, "same-key")
        other_tenant = _action(tenant_b, "same-key")

        assert repeated.id == first.id
        assert other_tenant.id != first.id
        assert NotificationAction.query.count() == 2
        with pytest.raises(lifecycle.IdempotencyConflict):
            lifecycle.create_or_get_action(
                organization_id=tenant_a,
                idempotency_key="same-key",
                purpose="DIFFERENT_PURPOSE",
            )


def test_attempt_claim_unknown_success_and_duplicate_result(lifecycle_app):
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    with lifecycle_app.app_context():
        tenant_a, _ = lifecycle_app.config["C2_ORGANIZATIONS"]
        action = _action(tenant_a)
        attempt = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        )
        assert lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        ).id == attempt.id

        claim = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            lease_seconds=30,
            now=now,
        )
        with pytest.raises(lifecycle.ClaimUnavailable):
            lifecycle.claim_attempt(
                organization_id=tenant_a,
                attempt_public_id=attempt.public_id,
                lease_seconds=30,
                now=now + timedelta(seconds=1),
            )

        unknown = lifecycle.record_result(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim.token,
            outcome="UNKNOWN",
            result_code="OUTCOME_NOT_ESTABLISHED",
            now=now + timedelta(seconds=2),
        )
        assert unknown.status == "UNKNOWN"
        assert db.session.get(NotificationAction, action.id).status == "IN_PROGRESS"

        succeeded = lifecycle.reconcile_unknown(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim.token,
            outcome="SUCCEEDED",
            result_code="AUTHORITATIVE_SUCCESS",
            provider_reference="neutral-reference",
            now=now + timedelta(seconds=3),
        )
        completed_at = succeeded.completed_at
        duplicate = lifecycle.record_result(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim.token,
            outcome="SUCCEEDED",
            result_code="AUTHORITATIVE_SUCCESS",
            provider_reference="neutral-reference",
            now=now + timedelta(seconds=4),
        )
        assert duplicate.completed_at == completed_at
        assert db.session.get(NotificationAction, action.id).status == "COMPLETED"
        with pytest.raises(lifecycle.InvalidTransition):
            lifecycle.create_attempt(
                organization_id=tenant_a, action_public_id=action.public_id
            )


def test_unknown_can_reconcile_to_failure_without_automatic_retry(lifecycle_app):
    now = datetime(2026, 9, 20, 13, 0, tzinfo=timezone.utc)
    with lifecycle_app.app_context():
        tenant_a, _ = lifecycle_app.config["C2_ORGANIZATIONS"]
        action = _action(tenant_a, "unknown-failure")
        attempt = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        )
        claim = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            lease_seconds=30,
            now=now,
        )
        lifecycle.record_result(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim.token,
            outcome="UNKNOWN",
            result_code="AMBIGUOUS",
            now=now + timedelta(seconds=1),
        )
        failed = lifecycle.reconcile_unknown(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim.token,
            outcome="FAILED",
            result_code="AUTHORITATIVE_FAILURE",
            failure_code="DELIVERY_NOT_CONFIRMED",
            now=now + timedelta(seconds=2),
        )
        assert failed.status == "FAILED"
        assert db.session.get(NotificationAction, action.id).status == "FAILED"
        assert NotificationAttempt.query.count() == 1


def test_expired_claim_is_unknown_and_new_fence_rejects_old_result(lifecycle_app):
    now = datetime(2026, 9, 20, 14, 0, tzinfo=timezone.utc)
    with lifecycle_app.app_context():
        tenant_a, _ = lifecycle_app.config["C2_ORGANIZATIONS"]
        action = _action(tenant_a, "expired")
        attempt = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        )
        claim_a = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            lease_seconds=5,
            now=now,
        )
        claim_b = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            lease_seconds=30,
            now=now + timedelta(seconds=6),
        )
        assert claim_b.token != claim_a.token
        assert claim_b.attempt_status == "UNKNOWN"
        with pytest.raises(lifecycle.StaleClaim):
            lifecycle.record_result(
                organization_id=tenant_a,
                attempt_public_id=attempt.public_id,
                claim_token=claim_a.token,
                outcome="SUCCEEDED",
                result_code="LATE_OLD_SUCCESS",
                now=now + timedelta(seconds=7),
            )
        lifecycle.reconcile_unknown(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim_b.token,
            outcome="SUCCEEDED",
            result_code="CURRENT_SUCCESS",
            now=now + timedelta(seconds=8),
        )
        assert db.session.get(NotificationAction, action.id).status == "COMPLETED"


def test_explicit_expiry_revokes_old_token_and_never_creates_retry(lifecycle_app):
    now = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)
    with lifecycle_app.app_context():
        tenant_a, _ = lifecycle_app.config["C2_ORGANIZATIONS"]
        action = _action(tenant_a, "explicit-expiry")
        attempt = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        )
        claim = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            lease_seconds=5,
            now=now,
        )
        expired = lifecycle.expire_claim(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim.token,
            now=now + timedelta(seconds=6),
        )
        assert expired.status == "UNKNOWN"
        assert expired.claim_token is None
        assert NotificationAttempt.query.count() == 1
        with pytest.raises(lifecycle.StaleClaim):
            lifecycle.record_result(
                organization_id=tenant_a,
                attempt_public_id=attempt.public_id,
                claim_token=claim.token,
                outcome="FAILED",
                failure_code="LATE_FAILURE",
                now=now + timedelta(seconds=7),
            )


def test_failed_action_explicit_next_attempt_and_late_attempt_fence(lifecycle_app):
    now = datetime(2026, 9, 20, 16, 0, tzinfo=timezone.utc)
    with lifecycle_app.app_context():
        tenant_a, _ = lifecycle_app.config["C2_ORGANIZATIONS"]
        action = _action(tenant_a, "explicit-next")
        first = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        )
        first_claim = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=first.public_id,
            lease_seconds=30,
            now=now,
        )
        lifecycle.record_result(
            organization_id=tenant_a,
            attempt_public_id=first.public_id,
            claim_token=first_claim.token,
            outcome="FAILED",
            failure_code="FIRST_FAILED",
            now=now + timedelta(seconds=1),
        )
        second = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        )
        assert second.attempt_number == 2
        assert NotificationAttempt.query.count() == 2
        with pytest.raises(lifecycle.StaleAttempt):
            lifecycle.record_result(
                organization_id=tenant_a,
                attempt_public_id=first.public_id,
                claim_token=first_claim.token,
                outcome="SUCCEEDED",
                result_code="LATE_SUCCESS",
                now=now + timedelta(seconds=2),
            )
        assert db.session.get(NotificationAttempt, second.id).status == "PENDING"
        assert db.session.get(NotificationAction, action.id).status == "PENDING"


def test_tenant_and_opaque_identity_checks_cover_every_write(lifecycle_app):
    now = datetime(2026, 9, 20, 17, 0, tzinfo=timezone.utc)
    with lifecycle_app.app_context():
        tenant_a, tenant_b = lifecycle_app.config["C2_ORGANIZATIONS"]
        action = _action(tenant_a, "tenant-fence")
        attempt = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=action.public_id
        )
        claim = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            lease_seconds=30,
            now=now,
        )
        with pytest.raises(lifecycle.NotificationNotFound):
            lifecycle.create_attempt(
                organization_id=tenant_b, action_public_id=action.public_id
            )
        with pytest.raises(lifecycle.NotificationNotFound):
            lifecycle.claim_attempt(
                organization_id=tenant_b,
                attempt_public_id=attempt.public_id,
                lease_seconds=30,
                now=now,
            )
        with pytest.raises(lifecycle.NotificationNotFound):
            lifecycle.record_result(
                organization_id=tenant_b,
                attempt_public_id=attempt.public_id,
                claim_token=claim.token,
                outcome="SUCCEEDED",
                now=now,
            )
        with pytest.raises(lifecycle.NotificationNotFound):
            lifecycle.claim_attempt(
                organization_id=tenant_a,
                attempt_public_id=str(attempt.id),
                lease_seconds=30,
                now=now,
            )


def test_cancelled_and_completed_actions_cannot_reopen(lifecycle_app):
    now = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    with lifecycle_app.app_context():
        tenant_a, _ = lifecycle_app.config["C2_ORGANIZATIONS"]
        cancelled = _action(tenant_a, "cancelled")
        lifecycle.cancel_action(
            organization_id=tenant_a, action_public_id=cancelled.public_id
        )
        with pytest.raises(lifecycle.InvalidTransition):
            lifecycle.create_attempt(
                organization_id=tenant_a, action_public_id=cancelled.public_id
            )

        completed = _action(tenant_a, "completed")
        attempt = lifecycle.create_attempt(
            organization_id=tenant_a, action_public_id=completed.public_id
        )
        claim = lifecycle.claim_attempt(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            lease_seconds=30,
            now=now,
        )
        lifecycle.record_result(
            organization_id=tenant_a,
            attempt_public_id=attempt.public_id,
            claim_token=claim.token,
            outcome="SUCCEEDED",
            result_code="DONE",
            now=now + timedelta(seconds=1),
        )
        with pytest.raises(lifecycle.InvalidTransition):
            lifecycle.cancel_action(
                organization_id=tenant_a, action_public_id=completed.public_id
            )
