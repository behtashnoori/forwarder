"""Add SLA policy table.

Revision ID: 20250529_sla_policy
Revises: 20250223_ensure_quote
Create Date: 2026-05-29

"""
from alembic import op
import sqlalchemy as sa


revision = "20250529_sla_policy"
down_revision = "20250223_ensure_quote"
branch_labels = None
depends_on = None

SQLITE_BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "sla_policy",
        sa.Column("id", SQLITE_BIGINT, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("priority_scope", sa.String(length=20), nullable=False, server_default="all"),
        sa.Column("request_status_scope", sa.Text(), nullable=False),
        sa.Column("transport_method_scope", sa.String(length=50), nullable=True),
        sa.Column("shipping_type_scope", sa.String(length=20), nullable=True),
        sa.Column("response_time_minutes", sa.Integer(), nullable=False),
        sa.Column("near_deadline_threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sla_policy_active", "sla_policy", ["is_active"])
    op.create_index("idx_sla_policy_priority", "sla_policy", ["priority_scope"])
    op.create_index("idx_sla_policy_sort", "sla_policy", ["sort_order", "name"])


def downgrade():
    op.drop_index("idx_sla_policy_sort", "sla_policy")
    op.drop_index("idx_sla_policy_priority", "sla_policy")
    op.drop_index("idx_sla_policy_active", "sla_policy")
    op.drop_table("sla_policy")
