"""Add Iran entry point fields to shipment request.

Revision ID: 20250115_add_iran_entry_point_fields
Revises: 20250115_add_iran_ports_models
Create Date: 2025-01-15 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


# revision identifiers, used by Alembic.
revision = "20250115_add_iran_entry_point_fields"
down_revision = "20250115_add_iran_ports_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Iran entry point fields to shipment_request table."""
    
    # Add Iran entry point fields
    op.add_column("shipment_request", sa.Column("iran_entry_port", sa.String(100), nullable=True))
    op.add_column("shipment_request", sa.Column("iran_entry_province", sa.String(100), nullable=True))
    op.add_column("shipment_request", sa.Column("iran_entry_port_id", BIGINT, nullable=True))
    op.add_column("shipment_request", sa.Column("iran_entry_province_id", BIGINT, nullable=True))
    
    # Add foreign key constraints
    op.create_foreign_key(
        "fk_shipment_request_iran_entry_port_id",
        "shipment_request",
        "iran_port",
        ["iran_entry_port_id"],
        ["id"],
        ondelete="SET NULL"
    )
    
    op.create_foreign_key(
        "fk_shipment_request_iran_entry_province_id",
        "shipment_request",
        "province",
        ["iran_entry_province_id"],
        ["id"],
        ondelete="SET NULL"
    )
    
    # Create indexes for better performance
    op.create_index("ix_shipment_request_iran_entry_port_id", "shipment_request", ["iran_entry_port_id"])
    op.create_index("ix_shipment_request_iran_entry_province_id", "shipment_request", ["iran_entry_province_id"])


def downgrade() -> None:
    """Remove Iran entry point fields from shipment_request table."""
    op.drop_index("ix_shipment_request_iran_entry_province_id", "shipment_request")
    op.drop_index("ix_shipment_request_iran_entry_port_id", "shipment_request")
    op.drop_constraint("fk_shipment_request_iran_entry_province_id", "shipment_request", type_="foreignkey")
    op.drop_constraint("fk_shipment_request_iran_entry_port_id", "shipment_request", type_="foreignkey")
    op.drop_column("shipment_request", "iran_entry_province_id")
    op.drop_column("shipment_request", "iran_entry_port_id")
    op.drop_column("shipment_request", "iran_entry_province")
    op.drop_column("shipment_request", "iran_entry_port")
