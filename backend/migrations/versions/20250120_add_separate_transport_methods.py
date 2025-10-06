"""Add separate transport methods for international and domestic shipping.

Revision ID: 20250120_add_separate_transport_methods
Revises: 20250115_add_iran_ports_models
Create Date: 2025-01-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250120_add_separate_transport_methods"
down_revision = "20250115_add_iran_ports_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add separate transport method columns for international and domestic shipping."""
    # Add new columns for separate transport methods
    op.add_column(
        "shipment_request",
        sa.Column("international_transport_method", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("domestic_transport_method", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "shipment_request",
        sa.Column("transport_method_preference", sa.String(length=20), nullable=True, default="customer_choice"),
    )
    
    # Migrate existing transport_method data to appropriate new columns
    # This will be handled by a data migration script
    op.execute("""
        UPDATE shipment_request 
        SET international_transport_method = transport_method,
            domestic_transport_method = transport_method
        WHERE transport_method IS NOT NULL
    """)


def downgrade() -> None:
    """Remove separate transport method columns."""
    op.drop_column("shipment_request", "transport_method_preference")
    op.drop_column("shipment_request", "domestic_transport_method")
    op.drop_column("shipment_request", "international_transport_method")
