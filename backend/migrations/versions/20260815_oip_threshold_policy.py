"""Governed OIP timing thresholds.

Revision ID: 20260815_oip_threshold_policy
Revises: 20260814_oip_situations
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_oip_threshold_policy"
down_revision = "20260814_oip_situations"
branch_labels = None
depends_on = None

BIG = sa.BigInteger()

def upgrade():
    op.create_table(
        "oip_threshold_policy",
        sa.Column("id", BIG, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", BIG, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("signal_type", sa.String(48), nullable=False),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column("scope_public_id", sa.String(64), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(8), nullable=False),
        sa.Column("authority", sa.String(120), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("updated_by_user_id", BIG, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("organization_id", "signal_type", "scope_type", "scope_public_id", "version", name="uq_oip_threshold_policy_version"),
        sa.CheckConstraint("signal_type IN ('NEXT_MILESTONE_OVERDUE','EXECUTION_UNIT_STALE')", name="ck_oip_threshold_policy_signal"),
        sa.CheckConstraint("scope_type IN ('PROJECT','SERVICE_MODE','ENTERPRISE')", name="ck_oip_threshold_policy_scope"),
        sa.CheckConstraint("value > 0", name="ck_oip_threshold_policy_value"),
        sa.CheckConstraint("unit IN ('MINUTE','HOUR','DAY')", name="ck_oip_threshold_policy_unit"),
        sa.CheckConstraint("version >= 1", name="ck_oip_threshold_policy_version"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="ck_oip_threshold_policy_effective"),
    )
    op.create_index("ix_oip_threshold_policy_resolution", "oip_threshold_policy", ["organization_id", "signal_type", "scope_type", "scope_public_id", "is_active", "effective_from"])

def downgrade():
    op.drop_table("oip_threshold_policy")
