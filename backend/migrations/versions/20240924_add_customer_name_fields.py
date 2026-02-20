"""Add customer name fields to shipment_request.

Revision ID: 20240924_add_customer_name_fields
Revises: 20240923_add_cargo_details
Create Date: 2024-09-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def _column_exists(conn, table, column):
    try:
        insp = inspect(conn)
        return column in [c["name"] for c in insp.get_columns(table)]
    except Exception:
        return False


# revision identifiers, used by Alembic.
revision = "20240924_add_customer_name_fields"
down_revision = "20240923_add_cargo_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add customer name columns to shipment_request (idempotent)."""
    conn = op.get_bind()
    if not _column_exists(conn, "shipment_request", "customer_first_name"):
        op.add_column(
            "shipment_request",
            sa.Column("customer_first_name", sa.String(length=100), nullable=True),
        )
    if not _column_exists(conn, "shipment_request", "customer_last_name"):
        op.add_column(
            "shipment_request",
            sa.Column("customer_last_name", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    """Remove customer name columns from shipment_request."""
    conn = op.get_bind()
    if _column_exists(conn, "shipment_request", "customer_last_name"):
        op.drop_column("shipment_request", "customer_last_name")
    if _column_exists(conn, "shipment_request", "customer_first_name"):
        op.drop_column("shipment_request", "customer_first_name")




