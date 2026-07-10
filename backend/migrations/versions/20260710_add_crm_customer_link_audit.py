"""Add CRM customer link audit table.

Revision ID: 20260710_crm_link_audit
Revises: 20250224_allow_quoted_status
Create Date: 2026-07-10

"""
from alembic import op
import sqlalchemy as sa


revision = "20260710_crm_link_audit"
down_revision = "20250224_allow_quoted_status"
branch_labels = None
depends_on = None

SQLITE_BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "crm_customer_link_audit",
        sa.Column("id", SQLITE_BIGINT, nullable=False),
        sa.Column("shipment_request_id", SQLITE_BIGINT, nullable=False),
        sa.Column("old_customer_id", SQLITE_BIGINT, nullable=True),
        sa.Column("new_customer_id", SQLITE_BIGINT, nullable=True),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("performed_by_user_id", SQLITE_BIGINT, nullable=True),
        sa.Column("performed_by_role", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="crm_api"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_status_at_time", sa.String(length=32), nullable=True),
        sa.Column("assigned_to_at_time", SQLITE_BIGINT, nullable=True),
        sa.Column("gamification_customer_id_at_time", SQLITE_BIGINT, nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["shipment_request_id"], ["shipment_request.id"]),
        sa.ForeignKeyConstraint(["old_customer_id"], ["customer.id"]),
        sa.ForeignKeyConstraint(["new_customer_id"], ["customer.id"]),
        sa.ForeignKeyConstraint(["performed_by_user_id"], ["expert_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_crm_customer_link_audit_request_created",
        "crm_customer_link_audit",
        ["shipment_request_id", "created_at"],
    )
    op.create_index(
        "idx_crm_customer_link_audit_old_customer",
        "crm_customer_link_audit",
        ["old_customer_id"],
    )
    op.create_index(
        "idx_crm_customer_link_audit_new_customer",
        "crm_customer_link_audit",
        ["new_customer_id"],
    )
    op.create_index(
        "idx_crm_customer_link_audit_performed_by",
        "crm_customer_link_audit",
        ["performed_by_user_id"],
    )
    op.create_index(
        "idx_crm_customer_link_audit_operation",
        "crm_customer_link_audit",
        ["operation"],
    )


def downgrade():
    op.drop_index("idx_crm_customer_link_audit_operation", table_name="crm_customer_link_audit")
    op.drop_index("idx_crm_customer_link_audit_performed_by", table_name="crm_customer_link_audit")
    op.drop_index("idx_crm_customer_link_audit_new_customer", table_name="crm_customer_link_audit")
    op.drop_index("idx_crm_customer_link_audit_old_customer", table_name="crm_customer_link_audit")
    op.drop_index("idx_crm_customer_link_audit_request_created", table_name="crm_customer_link_audit")
    op.drop_table("crm_customer_link_audit")
