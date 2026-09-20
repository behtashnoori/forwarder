"""Owned PostgreSQL upgrade/downgrade proof for the C2 claim fields."""
from __future__ import annotations

import os

from alembic import command
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend.migration_runtime import (
    alembic_config,
    prepare_version_table_for_upgrade,
    revision_status,
)


HEAD = "20260923_notification_lifecycle"
PREVIOUS = "20260922_notification_foundation"


def _url() -> str:
    url = os.environ.get("PHASE_C2_POSTGRES_URL")
    if not url:
        pytest.skip("owned disposable Phase C2 PostgreSQL URL required")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.database and parsed.database.startswith("phase_c2_disposable")
    return url


def test_c1_to_c2_upgrade_safe_downgrade_and_reupgrade():
    url = _url()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    config = alembic_config(url)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS
    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, PREVIOUS)

    with engine.begin() as connection:
        organization_id = connection.execute(
            text(
                """
                INSERT INTO operational_organization
                    (public_id, name, is_active, created_at)
                VALUES ('phase-c2-org', 'C2 preserved sentinel', true, now())
                RETURNING id
                """
            )
        ).scalar_one()
        action_id = connection.execute(
            text(
                """
                INSERT INTO notification_action
                    (public_id, organization_id, idempotency_key, purpose)
                VALUES ('phase-c2-action', :organization_id,
                        'phase-c2-idempotency', 'C2_MIGRATION_PROOF')
                RETURNING id
                """
            ),
            {"organization_id": organization_id},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO notification_attempt
                    (public_id, organization_id, action_id, attempt_number)
                VALUES ('phase-c2-attempt', :organization_id, :action_id, 1)
                """
            ),
            {"organization_id": organization_id, "action_id": action_id},
        )

    command.upgrade(config, HEAD)
    columns = {item["name"]: item for item in inspect(engine).get_columns("notification_attempt")}
    assert columns["claim_token"]["nullable"] is True
    assert columns["claim_expires_at"]["nullable"] is True
    assert columns["claim_expires_at"]["type"].timezone
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM notification_action WHERE public_id='phase-c2-action'")
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT COUNT(*) FROM notification_attempt WHERE public_id='phase-c2-attempt'")
        ).scalar_one() == 1

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE notification_attempt
                SET claim_token='11111111-1111-1111-1111-111111111111',
                    claim_expires_at=now() + interval '1 minute'
                WHERE public_id='phase-c2-attempt'
                """
            )
        )
    with pytest.raises(RuntimeError, match="lifecycle claims exist"):
        command.downgrade(config, PREVIOUS)
    assert revision_status(url).current == (HEAD,)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE notification_attempt
                SET claim_token=NULL, claim_expires_at=NULL
                WHERE public_id='phase-c2-attempt'
                """
            )
        )
    command.downgrade(config, PREVIOUS)
    assert "claim_token" not in {
        item["name"] for item in inspect(engine).get_columns("notification_attempt")
    }
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM notification_action WHERE public_id='phase-c2-action'")
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT COUNT(*) FROM notification_attempt WHERE public_id='phase-c2-attempt'")
        ).scalar_one() == 1

    command.upgrade(config, HEAD)
    assert revision_status(url).current == (HEAD,)
    assert revision_status(url).heads == (HEAD,)
    engine.dispose()
