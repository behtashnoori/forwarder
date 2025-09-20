"""Add expert console fields to shipment_request.

Revision ID: 20240924_add_expert_console_fields
Revises: 20240924_add_customer_name_fields
Create Date: 2024-09-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240924_add_expert_console_fields"
down_revision = "20240924_add_customer_name_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add expert console fields to shipment_request."""
    # Add expert console fields
    op.add_column(
        "shipment_request",
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
    )
    op.add_column(
        "shipment_request",
        sa.Column("sla_due_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("last_customer_touch_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("has_unread_for_assignee", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "shipment_request",
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="normal"),
    )
    op.add_column(
        "shipment_request",
        sa.Column("estimated_value", sa.Float(), nullable=True),
    )
    
    # Create expert_user table
    op.create_table(
        "expert_user",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    
    # Create expert_console_log table
    op.create_table(
        "expert_console_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("shipment_request_id", sa.BigInteger(), nullable=False),
        sa.Column("expert_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("old_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["expert_user_id"], ["expert_user.id"]),
        sa.ForeignKeyConstraint(["shipment_request_id"], ["shipment_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create expert_console_message table
    op.create_table(
        "expert_console_message",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("shipment_request_id", sa.BigInteger(), nullable=False),
        sa.Column("expert_user_id", sa.BigInteger(), nullable=False),
        sa.Column("message_type", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_read_by_customer", sa.Boolean(), nullable=False),
        sa.Column("customer_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["expert_user_id"], ["expert_user.id"]),
        sa.ForeignKeyConstraint(["shipment_request_id"], ["shipment_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create expert_console_notification table
    op.create_table(
        "expert_console_notification",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("expert_user_id", sa.BigInteger(), nullable=False),
        sa.Column("shipment_request_id", sa.BigInteger(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["expert_user_id"], ["expert_user.id"]),
        sa.ForeignKeyConstraint(["shipment_request_id"], ["shipment_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Add foreign key constraint for assigned_to
    op.create_foreign_key(
        "fk_shipment_request_assigned_to",
        "shipment_request", "expert_user",
        ["assigned_to"], ["id"]
    )


def downgrade() -> None:
    """Remove expert console fields and tables."""
    # Drop foreign key constraint
    op.drop_constraint("fk_shipment_request_assigned_to", "shipment_request", type_="foreignkey")
    
    # Drop tables
    op.drop_table("expert_console_notification")
    op.drop_table("expert_console_message")
    op.drop_table("expert_console_log")
    op.drop_table("expert_user")
    
    # Drop columns from shipment_request
    op.drop_column("shipment_request", "estimated_value")
    op.drop_column("shipment_request", "priority")
    op.drop_column("shipment_request", "has_unread_for_assignee")
    op.drop_column("shipment_request", "last_customer_touch_at")
    op.drop_column("shipment_request", "sla_due_at")
    op.drop_column("shipment_request", "status")
    op.drop_column("shipment_request", "assigned_to")



