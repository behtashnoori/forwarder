"""Add Iran ports and port-province mapping models.

Revision ID: 20250115_add_iran_ports_models
Revises: 20251006_124249_add_international_shipping_fields
Create Date: 2025-01-15 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


# revision identifiers, used by Alembic.
revision = "20250115_add_iran_ports_models"
down_revision = "20250110_add_international_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Iran ports and port-province mapping tables."""
    
    # Create iran_port table
    op.create_table(
        "iran_port",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("name_fa", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("port_type", sa.String(20), nullable=False, default="sea"),
        sa.Column("province_id", BIGINT, nullable=False),
        sa.Column("is_major_port", sa.Boolean(), default=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["province_id"],
            ["province.id"],
            name="fk_iran_port_province_id",
            ondelete="CASCADE",
        ),
    )
    
    # Create port_province_mapping table
    op.create_table(
        "port_province_mapping",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("port_id", BIGINT, nullable=False),
        sa.Column("province_id", BIGINT, nullable=False),
        sa.Column("suitability_score", sa.Float(), default=1.0),
        sa.Column("transport_method", sa.String(50), nullable=True),
        sa.Column("estimated_days", sa.Integer(), nullable=True),
        sa.Column("is_recommended", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["port_id"],
            ["iran_port.id"],
            name="fk_port_province_mapping_port_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["province_id"],
            ["province.id"],
            name="fk_port_province_mapping_province_id",
            ondelete="CASCADE",
        ),
    )
    
    # Create indexes for better performance
    op.create_index("ix_iran_port_province_id", "iran_port", ["province_id"])
    op.create_index("ix_iran_port_is_active", "iran_port", ["is_active"])
    op.create_index("ix_iran_port_port_type", "iran_port", ["port_type"])
    op.create_index("ix_port_province_mapping_port_id", "port_province_mapping", ["port_id"])
    op.create_index("ix_port_province_mapping_province_id", "port_province_mapping", ["province_id"])
    op.create_index("ix_port_province_mapping_suitability", "port_province_mapping", ["suitability_score"])


def downgrade() -> None:
    """Drop Iran ports and port-province mapping tables."""
    op.drop_index("ix_port_province_mapping_suitability", "port_province_mapping")
    op.drop_index("ix_port_province_mapping_province_id", "port_province_mapping")
    op.drop_index("ix_port_province_mapping_port_id", "port_province_mapping")
    op.drop_index("ix_iran_port_port_type", "iran_port")
    op.drop_index("ix_iran_port_is_active", "iran_port")
    op.drop_index("ix_iran_port_province_id", "iran_port")
    op.drop_table("port_province_mapping")
    op.drop_table("iran_port")
