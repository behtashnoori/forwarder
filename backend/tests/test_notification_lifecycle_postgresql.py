"""Real PostgreSQL concurrency gates for the dormant C2 lifecycle."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
import os

from alembic import command
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.notification_models import NotificationAction, NotificationAttempt
from backend.operational_models import OperationalOrganization
from backend.services import notification_lifecycle_service as lifecycle


HEAD = "20260923_notification_lifecycle"


def _url() -> str:
    url = os.environ.get("PHASE_C2_POSTGRES_URL")
    if not url:
        pytest.skip("owned disposable Phase C2 PostgreSQL URL required")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.database and parsed.database.startswith("phase_c2_disposable")
    return url


@pytest.fixture()
def pg_app():
    url = _url()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    config = alembic_config(url)
    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, HEAD)
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": url,
            "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
            "SECRET_KEY": "phase-c2-postgresql",
        },
        skip_startup=True,
    )
    with app.app_context():
        organization = OperationalOrganization(name="C2 PostgreSQL tenant")
        db.session.add(organization)
        db.session.commit()
        organization_id = organization.id
    yield app, organization_id
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    engine.dispose()


def _parallel(app, function):
    barrier = Barrier(2)

    def run():
        with app.app_context():
            try:
                barrier.wait(timeout=10)
                return function()
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run) for _ in range(2)]
        return [future.result(timeout=20) for future in futures]


def test_postgresql_idempotent_action_and_attempt_number_races(pg_app):
    app, organization_id = pg_app

    def create_action():
        return lifecycle.create_or_get_action(
            organization_id=organization_id,
            idempotency_key="postgres-race-action",
            purpose="POSTGRESQL_RACE_PROOF",
        ).public_id

    action_ids = _parallel(app, create_action)
    assert len(set(action_ids)) == 1
    with app.app_context():
        assert NotificationAction.query.count() == 1
        action_public_id = action_ids[0]

    def create_attempt():
        row = lifecycle.create_attempt(
            organization_id=organization_id,
            action_public_id=action_public_id,
        )
        return row.public_id, row.attempt_number

    attempts = _parallel(app, create_attempt)
    assert len({item[0] for item in attempts}) == 1
    assert [item[1] for item in attempts] == [1, 1]
    with app.app_context():
        assert [row.attempt_number for row in NotificationAttempt.query.all()] == [1]


def test_postgresql_competing_claim_expiry_stale_fence_and_unknown_reconcile(pg_app):
    app, organization_id = pg_app
    base = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    with app.app_context():
        action = lifecycle.create_or_get_action(
            organization_id=organization_id,
            idempotency_key="postgres-claim-race",
            purpose="POSTGRESQL_CLAIM_PROOF",
        )
        attempt = lifecycle.create_attempt(
            organization_id=organization_id,
            action_public_id=action.public_id,
        )
        attempt_public_id = attempt.public_id

    def claim():
        try:
            result = lifecycle.claim_attempt(
                organization_id=organization_id,
                attempt_public_id=attempt_public_id,
                lease_seconds=5,
                now=base,
            )
            return "won", result.token
        except lifecycle.ClaimUnavailable:
            return "lost", None

    claims = _parallel(app, claim)
    winners = [item for item in claims if item[0] == "won"]
    assert len(winners) == 1
    claim_a = winners[0][1]

    with app.app_context():
        claim_b = lifecycle.claim_attempt(
            organization_id=organization_id,
            attempt_public_id=attempt_public_id,
            lease_seconds=30,
            now=base + timedelta(seconds=6),
        )
        assert claim_b.token != claim_a
        assert claim_b.attempt_status == "UNKNOWN"
        with pytest.raises(lifecycle.StaleClaim):
            lifecycle.record_result(
                organization_id=organization_id,
                attempt_public_id=attempt_public_id,
                claim_token=claim_a,
                outcome="SUCCEEDED",
                result_code="STALE_SUCCESS",
                now=base + timedelta(seconds=7),
            )
        lifecycle.reconcile_unknown(
            organization_id=organization_id,
            attempt_public_id=attempt_public_id,
            claim_token=claim_b.token,
            outcome="SUCCEEDED",
            result_code="CURRENT_AUTHORITATIVE_SUCCESS",
            now=base + timedelta(seconds=8),
        )
        assert NotificationAction.query.one().status == "COMPLETED"
        assert NotificationAttempt.query.one().status == "SUCCEEDED"
