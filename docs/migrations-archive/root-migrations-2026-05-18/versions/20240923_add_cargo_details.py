"""Add cargo details to shipment_request.

Revision ID: 20240923_add_cargo_details
Revises: 20240922_make_transport_method_nullable
Create Date: 2024-09-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240923_add_cargo_details"
down_revision = "20240922_make_transport_method_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add cargo details columns to shipment_request."""
    op.add_column(
        "shipment_request",
        sa.Column("cargo_description", sa.Text(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("cargo_weight", sa.Float(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("cargo_volume", sa.Float(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("cargo_value", sa.Float(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("special_instructions", sa.Text(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("pickup_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("delivery_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    """Remove cargo details columns from shipment_request."""
    op.drop_column("shipment_request", "delivery_date")
    op.drop_column("shipment_request", "pickup_date")
    op.drop_column("shipment_request", "special_instructions")
    op.drop_column("shipment_request", "cargo_value")
    op.drop_column("shipment_request", "cargo_volume")
    op.drop_column("shipment_request", "cargo_weight")
    op.drop_column("shipment_request", "cargo_description")
