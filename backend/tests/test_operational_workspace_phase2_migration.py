"""Focused graph, additive upgrade, and round-trip checks for Phase 2."""
from pathlib import Path
from datetime import datetime, timezone

from alembic import command
from alembic.script import ScriptDirectory
import sqlalchemy as sa

from backend.migration_runtime import alembic_config


PREVIOUS = "20260927_customer_portal_account_lifecycle"
PHASE2 = "20260928_operational_workspace_phase2"
RELIABILITY = "20260929_operational_monitoring_reliability"
P3_REFERENCE = "20260930_phase3_reference_catalog"
REPOSITORY_HEAD = "20261001_phase3_cargo_lineage"
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _parent_schema(url):
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    organization = sa.Table(
        "operational_organization",
        metadata,
        sa.Column("id", BIGINT, primary_key=True),
    )
    expert = sa.Table(
        "expert_user", metadata, sa.Column("id", BIGINT, primary_key=True)
    )
    shipment = sa.Table(
        "operational_shipment",
        metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.UniqueConstraint(
            "id", "organization_id", name="uq_operational_shipment_id_org"
        ),
    )
    exception = sa.Table(
        "operational_exception",
        metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("milestone_id", BIGINT),
        sa.Column("reason_id", BIGINT, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("note", sa.Text),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column("resolved_by_user_id", BIGINT),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    work = sa.Table(
        "operational_work_item",
        metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("milestone_id", BIGINT),
        sa.Column("route_plan_id", BIGINT),
        sa.Column("checkpoint_id", BIGINT),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_reason", sa.Text),
        sa.Column("resolution_source", sa.String(20)),
        sa.Column("occurrence_count", sa.Integer, nullable=False),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True)),
        sa.Column("work_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assignee_user_id", BIGINT),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by_user_id", BIGINT),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "work_type IN ('OVERDUE_MILESTONE','CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED')",
            name="ck_operational_work_item_type",
        ),
        sa.CheckConstraint(
            "(work_type = 'OVERDUE_MILESTONE' AND milestone_id IS NOT NULL AND route_plan_id IS NULL AND checkpoint_id IS NULL) "
            "OR (work_type IN ('CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED') "
            "AND milestone_id IS NULL AND route_plan_id IS NOT NULL AND checkpoint_id IS NOT NULL)",
            name="ck_operational_work_item_owner_scope",
        ),
    )
    sa.Table(
        "oip_projection_state",
        metadata,
        sa.Column("organization_id", BIGINT, primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("source_watermark", sa.String(160), nullable=False),
        sa.Column("projection_version", sa.String(32), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text),
        sa.Column("processed_watermark", sa.String(160)),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("rebuild_started_at", sa.DateTime(timezone=True)),
        sa.Column("rebuild_completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("active_run_id", sa.String(36)),
        sa.Column("version", sa.Integer, nullable=False),
    )
    sa.Table(
        "oip_projection_health_history",
        metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("from_state", sa.String(16)),
        sa.Column("to_state", sa.String(16), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(200)),
        sa.Column("projection_version", sa.String(32), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("run_id", sa.String(36)),
        sa.Column("source_watermark", sa.String(160)),
        sa.Column("processed_watermark", sa.String(160)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)
    now = datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(organization.insert().values(id=1))
        connection.execute(expert.insert().values(id=10))
        connection.execute(shipment.insert().values(id=20, organization_id=1))
        connection.execute(
            exception.insert().values(
                id=30,
                public_id="11111111-1111-4111-8111-111111111111",
                organization_id=1,
                operational_shipment_id=20,
                reason_id=1,
                occurred_at=now,
                version=1,
                created_by_user_id=10,
                created_at=now,
            )
        )
        connection.execute(
            work.insert().values(
                id=40,
                organization_id=1,
                operational_shipment_id=20,
                milestone_id=50,
                severity="warning",
                detected_at=now,
                occurrence_count=1,
                work_type="OVERDUE_MILESTONE",
                status="open",
                due_at=now,
                reason="legacy row",
                version=1,
                created_at=now,
            )
        )
    return engine


def test_phase2_and_reliability_are_the_single_linear_repository_head():
    config = alembic_config("sqlite://")
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(REPOSITORY_HEAD).down_revision == P3_REFERENCE
    assert script.get_revision(P3_REFERENCE).down_revision == RELIABILITY
    assert script.get_revision(RELIABILITY).down_revision == PHASE2
    assert script.get_revision(PHASE2).down_revision == PREVIOUS
    assert script.get_bases() == ["20240917_initial_schema"]


def test_phase2_upgrade_backfills_work_identity_and_roundtrips(tmp_path: Path):
    url = f"sqlite:///{(tmp_path / 'phase2-roundtrip.db').as_posix()}"
    engine = _parent_schema(url)
    config = alembic_config(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, PHASE2)
    inspector = sa.inspect(engine)

    assert {"organization_sla_rule", "operational_sla_commitment"} <= set(
        inspector.get_table_names()
    )
    work_columns = {
        column["name"] for column in inspector.get_columns("operational_work_item")
    }
    assert {
        "public_id",
        "exception_id",
        "action_context_type",
        "process_type",
        "expected_result",
        "latest_follow_up",
        "latest_follow_up_at",
        "created_by_user_id",
        "updated_at",
    } <= work_columns
    with engine.connect() as connection:
        identity, reason = connection.execute(
            sa.text("SELECT public_id, reason FROM operational_work_item WHERE id = 40")
        ).one()
    assert len(identity) == 36
    assert reason == "legacy row"

    command.downgrade(config, PREVIOUS)
    downgraded = sa.inspect(engine)
    assert "organization_sla_rule" not in downgraded.get_table_names()
    assert "public_id" not in {
        column["name"]
        for column in downgraded.get_columns("operational_work_item")
    }
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT reason FROM operational_work_item WHERE id = 40")
        ).scalar_one() == "legacy row"
    engine.dispose()


def test_reliability_migration_is_additive_and_cleanly_roundtrips(tmp_path: Path):
    url = f"sqlite:///{(tmp_path / 'phase2-5-roundtrip.db').as_posix()}"
    engine = _parent_schema(url)
    config = alembic_config(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, RELIABILITY)
    inspector = sa.inspect(engine)
    state_columns = {
        column["name"] for column in inspector.get_columns("oip_projection_state")
    }
    history_columns = {
        column["name"]
        for column in inspector.get_columns("oip_projection_health_history")
    }
    assert {
        "last_evaluation_attempt_at",
        "last_evaluation_success_at",
        "next_evaluation_due_at",
    } <= state_columns
    assert "details_json" in history_columns

    command.downgrade(config, PHASE2)
    downgraded = sa.inspect(engine)
    assert "last_evaluation_attempt_at" not in {
        column["name"] for column in downgraded.get_columns("oip_projection_state")
    }
    assert "details_json" not in {
        column["name"]
        for column in downgraded.get_columns("oip_projection_health_history")
    }

    command.upgrade(config, RELIABILITY)
    assert "last_evaluation_success_at" in {
        column["name"]
        for column in sa.inspect(engine).get_columns("oip_projection_state")
    }
    engine.dispose()
