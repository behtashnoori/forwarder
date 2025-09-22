"""Add customer name fields to shipment_request.

Revision ID: 20240924_add_customer_name_fields
Revises: 20240923_add_cargo_details
Create Date: 2024-09-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240924_add_customer_name_fields"
down_revision = "20240923_add_cargo_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add customer name columns to shipment_request."""
    op.add_column(
        "shipment_request",
        sa.Column("customer_first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("customer_last_name", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Remove customer name columns from shipment_request."""
    op.drop_column("shipment_request", "customer_last_name")
    op.drop_column("shipment_request", "customer_first_name")




