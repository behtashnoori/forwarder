"""OIP-D20 projection health lifecycle.

Revision ID: 20260816_oip_projection_health
Revises: 20260815_oip_threshold_policy
"""
from alembic import op
import sqlalchemy as sa

revision = "20260816_oip_projection_health"
down_revision = "20260815_oip_threshold_policy"
branch_labels = None
depends_on = None

BIG = sa.BigInteger()


def upgrade():
    with op.batch_alter_table("oip_projection_state") as batch:
        batch.add_column(sa.Column("processed_watermark", sa.String(160)))
        batch.add_column(sa.Column("policy_version", sa.String(32), nullable=False, server_default="oip-health-watermark-v1"))
        batch.add_column(sa.Column("last_success_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("rebuild_started_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("rebuild_completed_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("last_failure_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("failure_code", sa.String(64)))
        batch.add_column(sa.Column("active_run_id", sa.String(36)))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_check_constraint("ck_oip_projection_health_state", "status IN ('FRESH','STALE','REBUILDING','DEGRADED')")
        batch.create_check_constraint("ck_oip_projection_health_version", "version >= 1")
    # Existing FRESH rows already carry successful reconciliation evidence in
    # source_watermark/calculated_at. No other historical state is guessed.
    op.execute("""UPDATE oip_projection_state
        SET processed_watermark = source_watermark,
            last_success_at = calculated_at
        WHERE status = 'FRESH'""")
    op.create_table(
        "oip_projection_health_history",
        sa.Column("id", BIG, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", BIG, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
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
        sa.CheckConstraint("to_state IN ('FRESH','STALE','REBUILDING','DEGRADED')", name="ck_oip_health_history_state"),
    )
    op.create_index("ix_oip_health_history_org_time", "oip_projection_health_history", ["organization_id", "occurred_at"])


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM oip_projection_health_history) THEN
            RAISE EXCEPTION 'cannot downgrade: durable OIP projection-health evidence exists' USING ERRCODE='23503';
        END IF;
    END $$""")
    op.drop_table("oip_projection_health_history")
    with op.batch_alter_table("oip_projection_state") as batch:
        batch.drop_constraint("ck_oip_projection_health_version", type_="check")
        batch.drop_constraint("ck_oip_projection_health_state", type_="check")
        for name in ("version", "active_run_id", "failure_code", "last_failure_at", "rebuild_completed_at", "rebuild_started_at", "last_success_at", "policy_version", "processed_watermark"):
            batch.drop_column(name)
