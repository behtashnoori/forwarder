"""Add referral rule, state, and assignment log tables.

Revision ID: 20250221_referral
Revises: 20250220_merge_final
Create Date: 2025-02-21

"""
from alembic import op
import sqlalchemy as sa

revision = "20250221_referral"
down_revision = "20250220_merge_final"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "referral_rule",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("priority", sa.Integer(), default=1),
        sa.Column("conditions", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("stop_on_match", sa.Boolean(), default=True),
        sa.Column("created_by", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["expert_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "referral_rule_state",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("rule_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("rr_index", sa.Integer(), default=0),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["referral_rule.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", name="uq_referral_rule_state_rule_id"),
    )
    op.create_table(
        "referral_assignment_log",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("request_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("rule_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("selected_expert_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("strategy_used", sa.String(length=32), nullable=False),
        sa.Column("candidate_expert_ids", sa.Text(), nullable=True),
        sa.Column("debug", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["shipment_request.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["referral_rule.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_expert_id"], ["expert_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_referral_rule_priority", "referral_rule", ["priority"])
    op.create_index("idx_referral_rule_active", "referral_rule", ["is_active"])
    op.create_index("idx_referral_assignment_log_request", "referral_assignment_log", ["request_id"])
    op.create_index("idx_referral_assignment_log_rule", "referral_assignment_log", ["rule_id"])


def downgrade():
    op.drop_index("idx_referral_assignment_log_rule", "referral_assignment_log")
    op.drop_index("idx_referral_assignment_log_request", "referral_assignment_log")
    op.drop_index("idx_referral_rule_active", "referral_rule")
    op.drop_index("idx_referral_rule_priority", "referral_rule")
    op.drop_table("referral_assignment_log")
    op.drop_table("referral_rule_state")
    op.drop_table("referral_rule")
