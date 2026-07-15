"""Add production-safe manual multi-unit shipment tracking.

Revision ID: 20260715_multi_unit_tracking
Revises: 20260710_crm_link_audit
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa


revision = "20260715_multi_unit_tracking"
down_revision = "20260710_crm_link_audit"
branch_labels = None
depends_on = None

SQLITE_BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "shipment_tracking",
        sa.Column("id", SQLITE_BIGINT, nullable=False),
        sa.Column("shipment_request_id", SQLITE_BIGINT, nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled_at", sa.DateTime(), nullable=True),
        sa.Column("enabled_by_user_id", SQLITE_BIGINT, nullable=True),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.Column("disabled_by_user_id", SQLITE_BIGINT, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["shipment_request_id"], ["shipment_request.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enabled_by_user_id"], ["expert_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["disabled_by_user_id"], ["expert_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_request_id", name="uq_shipment_tracking_request"),
    )
    op.create_index("idx_shipment_tracking_enabled", "shipment_tracking", ["is_enabled"])

    op.create_table(
        "shipment_transport_unit",
        sa.Column("id", SQLITE_BIGINT, nullable=False),
        sa.Column("tracking_id", SQLITE_BIGINT, nullable=False),
        sa.Column("unit_code", sa.String(length=64), nullable=False),
        sa.Column("unit_type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", SQLITE_BIGINT, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("sort_order >= 0", name="ck_tracking_unit_sort_order_nonnegative"),
        sa.ForeignKeyConstraint(["tracking_id"], ["shipment_tracking.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["expert_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_id", "unit_code", name="uq_tracking_unit_code"),
    )
    op.create_index("idx_tracking_unit_tracking_active", "shipment_transport_unit", ["tracking_id", "is_active"])

    op.create_table(
        "shipment_transport_unit_update",
        sa.Column("id", SQLITE_BIGINT, nullable=False),
        sa.Column("unit_id", SQLITE_BIGINT, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("customer_message", sa.Text(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("is_customer_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", SQLITE_BIGINT, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["shipment_transport_unit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["expert_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tracking_update_unit_occurred",
        "shipment_transport_unit_update",
        ["unit_id", "occurred_at"],
    )
    op.create_index(
        "idx_tracking_update_unit_visible_occurred",
        "shipment_transport_unit_update",
        ["unit_id", "is_customer_visible", "occurred_at"],
    )


def downgrade():
    op.drop_index("idx_tracking_update_unit_visible_occurred", table_name="shipment_transport_unit_update")
    op.drop_index("idx_tracking_update_unit_occurred", table_name="shipment_transport_unit_update")
    op.drop_table("shipment_transport_unit_update")
    op.drop_index("idx_tracking_unit_tracking_active", table_name="shipment_transport_unit")
    op.drop_table("shipment_transport_unit")
    op.drop_index("idx_shipment_tracking_enabled", table_name="shipment_tracking")
    op.drop_table("shipment_tracking")
