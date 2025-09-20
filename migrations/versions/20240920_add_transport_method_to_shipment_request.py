"""Add transport_method to shipment_request.

Revision ID: 20240920_add_transport_method_to_shipment_request
Revises: 20240919_add_code_to_province
Create Date: 2024-09-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240920_add_transport_method_to_shipment_request"
down_revision = "20240919_add_code_to_province"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the transport_method column to shipment_request."""
    op.add_column(
        "shipment_request",
        sa.Column("transport_method", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    """Remove the transport_method column from shipment_request."""
    op.drop_column("shipment_request", "transport_method")
