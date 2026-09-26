"""Focused graph, upgrade, and recovery checks for Customer Portal lifecycle."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa

from backend.migration_runtime import alembic_config


PREVIOUS = "20260926_fixed_shipment_responsible_expert"
HEAD = "20260927_customer_portal_account_lifecycle"
REPOSITORY_HEAD = "20261012_phase3_cargo_eta"


def _legacy_schema(url: str) -> sa.Engine:
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    organization = sa.Table(
        "operational_organization",
        metadata,
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
    )
    expert = sa.Table(
        "expert_user",
        metadata,
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
    )
    customer = sa.Table(
        "customer_gamification",
        metadata,
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("email", sa.String(100), nullable=False),
    )
    quote = sa.Table(
        "expert_quote",
        metadata,
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(organization.insert().values(id=3))
        connection.execute(expert.insert().values(id=7))
        connection.execute(
            customer.insert(),
            [
                {"id": 1, "email": "legacy-one@example.test"},
                {"id": 2, "email": "legacy-two@example.test"},
            ],
        )
        connection.execute(quote.insert().values(id=11))
    return engine


def _upgrade(tmp_path: Path, name: str) -> tuple[sa.Engine, object]:
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    engine = _legacy_schema(url)
    config = alembic_config(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)
    return engine, config


def test_customer_portal_lifecycle_is_the_single_linear_repository_head():
    config = alembic_config("sqlite://")
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS
    assert script.get_bases() == ["20240917_initial_schema"]


def test_customer_portal_lifecycle_upgrade_backfills_and_roundtrips_legacy_data(tmp_path):
    engine, config = _upgrade(tmp_path, "customer-portal-roundtrip.db")
    inspector = sa.inspect(engine)

    customer_columns = {
        column["name"] for column in inspector.get_columns("customer_gamification")
    }
    assert customer_columns >= {
        "public_id",
        "password_hash",
        "account_status",
        "session_generation",
        "password_changed_at",
        "disabled_at",
        "disabled_by_user_id",
        "operational_organization_id",
    }
    assert {
        "customer_portal_account_audit",
        "customer_portal_recovery_request",
        "customer_portal_recovery_token",
    } <= set(inspector.get_table_names())
    assert {
        "purpose",
        "delivery_channel",
        "delivery_status",
        "delivery_attempted_at",
    } <= {
        column["name"]
        for column in inspector.get_columns("customer_portal_recovery_request")
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("customer_portal_recovery_request")
    } >= {
        "ck_customer_portal_recovery_request_purpose",
        "ck_customer_portal_recovery_request_channel",
        "ck_customer_portal_recovery_request_status",
    }
    assert "response_version" in {
        column["name"] for column in inspector.get_columns("expert_quote")
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("customer_gamification")
    } >= {
        "ck_customer_portal_account_status",
        "ck_customer_portal_session_generation_nonnegative",
    }
    assert {
        foreign_key["name"]
        for foreign_key in inspector.get_foreign_keys("customer_gamification")
    } >= {
        "fk_customer_portal_disabled_by_user",
        "fk_customer_portal_operational_organization",
    }
    assert "ix_customer_gamification_operational_organization_id" in {
        index["name"] for index in inspector.get_indexes("customer_gamification")
    }

    with engine.connect() as connection:
        customers = connection.execute(
            sa.text(
                "SELECT id, public_id, account_status, session_generation "
                "FROM customer_gamification ORDER BY id"
            )
        ).mappings().all()
        quote_version = connection.execute(
            sa.text("SELECT response_version FROM expert_quote WHERE id = 11")
        ).scalar_one()
    assert [row["id"] for row in customers] == [1, 2]
    assert all(len(row["public_id"]) == 36 for row in customers)
    assert len({row["public_id"] for row in customers}) == 2
    assert all(row["account_status"] == "ACTIVE" for row in customers)
    assert all(row["session_generation"] == 0 for row in customers)
    assert quote_version == 0

    command.downgrade(config, PREVIOUS)
    downgraded = sa.inspect(engine)
    assert "public_id" not in {
        column["name"] for column in downgraded.get_columns("customer_gamification")
    }
    assert "response_version" not in {
        column["name"] for column in downgraded.get_columns("expert_quote")
    }
    assert "customer_portal_recovery_request" not in downgraded.get_table_names()
    assert "customer_portal_recovery_token" not in downgraded.get_table_names()
    assert "customer_portal_account_audit" not in downgraded.get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT COUNT(*) FROM customer_gamification")
        ).scalar_one() == 2
        assert connection.execute(
            sa.text("SELECT COUNT(*) FROM expert_quote")
        ).scalar_one() == 1
    engine.dispose()


def test_customer_portal_lifecycle_downgrade_refuses_account_evidence(tmp_path):
    engine, config = _upgrade(tmp_path, "customer-portal-guard.db")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE customer_gamification "
                "SET account_status = 'DISABLED', session_generation = 1 "
                "WHERE id = 1"
            )
        )

    with pytest.raises(RuntimeError, match="Cannot downgrade while Customer Portal"):
        command.downgrade(config, PREVIOUS)

    inspector = sa.inspect(engine)
    assert "account_status" in {
        column["name"] for column in inspector.get_columns("customer_gamification")
    }
    assert "customer_portal_recovery_token" in inspector.get_table_names()
    engine.dispose()
