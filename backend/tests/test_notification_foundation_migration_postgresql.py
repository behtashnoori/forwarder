"""Real disposable PostgreSQL proof for the Phase C1 migration."""
from __future__ import annotations

import os

from alembic import command
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend.migration_runtime import (
    alembic_config,
    prepare_version_table_for_upgrade,
    revision_status,
)


HEAD = "20260922_notification_foundation"
CURRENT_HEAD = "20260923_notification_lifecycle"
PREVIOUS = "20260921_shipment_evidence_ownership"
DONOR_REVISION = "20260916_fwd01_notifications"


def _disposable_url() -> str:
    url = os.environ.get("PHASE_C1_POSTGRES_URL")
    if not url:
        pytest.skip("owned disposable Phase C1 PostgreSQL URL required")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.database and parsed.database.startswith("phase_c1_disposable")
    return url


def _reset_owned_database(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


def _constraint_names(inspector, table: str) -> set[str]:
    return {
        item["name"]
        for item in inspector.get_unique_constraints(table)
        if item.get("name")
    }


def test_phase_c1_from_golden_upgrade_constraints_sentinel_and_rollback():
    url = _disposable_url()
    engine = create_engine(url)
    _reset_owned_database(engine)
    config = alembic_config(url)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [CURRENT_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS
    assert DONOR_REVISION not in {
        item.revision for item in script.walk_revisions(base="base", head="heads")
    }

    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, PREVIOUS)

    with engine.begin() as connection:
        organization_id = connection.execute(
            text(
                """
                INSERT INTO operational_organization
                    (public_id, name, is_active, created_at)
                VALUES
                    ('phase-c1-sentinel-org', 'Phase C1 preserved sentinel', true, now())
                RETURNING id
                """
            )
        ).scalar_one()
        source_event_id = connection.execution_options(
            include_quarantined_for_certification=True
        ).execute(
            text(
                """
                INSERT INTO operational_outbox
                    (organization_id, event_type, aggregate_type, aggregate_id,
                     payload, created_at)
                VALUES
                    (:organization_id, 'synthetic.pre-c1.v1', 'Synthetic', 1,
                     CAST('{}' AS json), now())
                RETURNING id
                """
            ),
            {"organization_id": organization_id},
        ).scalar_one()

    command.upgrade(config, HEAD)
    inspector = inspect(engine)
    assert {"notification_action", "notification_attempt"}.issubset(
        inspector.get_table_names()
    )
    assert _constraint_names(inspector, "notification_action") >= {
        "uq_notification_action_public_id",
        "uq_notification_action_tenant",
        "uq_notification_action_idempotency",
    }
    assert _constraint_names(inspector, "notification_attempt") >= {
        "uq_notification_attempt_public_id",
        "uq_notification_attempt_number",
    }
    assert "uq_operational_outbox_tenant" in _constraint_names(
        inspector, "operational_outbox"
    )
    action_columns = {
        item["name"]: item for item in inspector.get_columns("notification_action")
    }
    attempt_columns = {
        item["name"]: item for item in inspector.get_columns("notification_attempt")
    }
    assert action_columns["recipient_reference"]["nullable"] is True
    assert action_columns["channel"]["nullable"] is True
    assert attempt_columns["channel"]["nullable"] is True
    assert attempt_columns["provider"]["nullable"] is True
    for name in ("created_at", "updated_at"):
        assert action_columns[name]["type"].timezone
        assert attempt_columns[name]["type"].timezone
    for name in ("attempted_at", "completed_at", "delivered_at"):
        assert attempt_columns[name]["type"].timezone

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM notification_action")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM notification_attempt")).scalar_one() == 0
        second_organization_id = connection.execute(
            text(
                """
                INSERT INTO operational_organization
                    (public_id, name, is_active, created_at)
                VALUES
                    ('phase-c1-other-org', 'Phase C1 other tenant', true, now())
                RETURNING id
                """
            )
        ).scalar_one()
        connection.commit()

    with engine.begin() as connection:
        action_id = connection.execute(
            text(
                """
                INSERT INTO notification_action
                    (public_id, organization_id, source_event_id, idempotency_key,
                     purpose)
                VALUES
                    ('phase-c1-action', :organization_id, :source_event_id,
                     'phase-c1-idempotency', 'SYNTHETIC_FOUNDATION_PROOF')
                RETURNING id
                """
            ),
            {
                "organization_id": organization_id,
                "source_event_id": source_event_id,
            },
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO notification_attempt
                    (public_id, organization_id, action_id, attempt_number)
                VALUES
                    ('phase-c1-attempt', :organization_id, :action_id, 1)
                """
            ),
            {"organization_id": organization_id, "action_id": action_id},
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO notification_action
                        (public_id, organization_id, source_event_id,
                         idempotency_key, purpose)
                    VALUES
                        ('phase-c1-cross-event', :other_organization_id,
                         :source_event_id, 'phase-c1-cross-event',
                         'SYNTHETIC_FOUNDATION_PROOF')
                    """
                ),
                {
                    "other_organization_id": second_organization_id,
                    "source_event_id": source_event_id,
                },
            )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO notification_attempt
                        (public_id, organization_id, action_id, attempt_number)
                    VALUES
                        ('phase-c1-cross-attempt', :other_organization_id,
                         :action_id, 2)
                    """
                ),
                {
                    "other_organization_id": second_organization_id,
                    "action_id": action_id,
                },
            )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO notification_attempt
                        (public_id, organization_id, action_id, attempt_number)
                    VALUES
                        ('phase-c1-zero-attempt', :organization_id, :action_id, 0)
                    """
                ),
                {"organization_id": organization_id, "action_id": action_id},
            )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM notification_action WHERE id = :action_id"),
                {"action_id": action_id},
            )

    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM notification_attempt WHERE action_id = :action_id"),
            {"action_id": action_id},
        )
        connection.execute(
            text("DELETE FROM notification_action WHERE id = :action_id"),
            {"action_id": action_id},
        )

    command.downgrade(config, PREVIOUS)
    inspector = inspect(engine)
    assert "notification_action" not in inspector.get_table_names()
    assert "notification_attempt" not in inspector.get_table_names()
    assert "uq_operational_outbox_tenant" not in _constraint_names(
        inspector, "operational_outbox"
    )
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT name FROM operational_organization WHERE id = :organization_id"
            ),
            {"organization_id": organization_id},
        ).scalar_one() == "Phase C1 preserved sentinel"
        assert connection.execute(
            text("SELECT event_type FROM operational_outbox WHERE id = :source_event_id"),
            {"source_event_id": source_event_id},
        ).scalar_one() == "synthetic.pre-c1.v1"

    command.upgrade(config, HEAD)
    assert revision_status(url).current == (HEAD,)
    assert revision_status(url).heads == (CURRENT_HEAD,)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM notification_action")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM notification_attempt")).scalar_one() == 0
    engine.dispose()
