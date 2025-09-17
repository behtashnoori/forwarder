"""add shipment request log table

Revision ID: 20240918_add_shipment_request_log
Revises: 20240917_initial_schema
Create Date: 2024-09-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


# revision identifiers, used by Alembic.
revision = "20240918_add_shipment_request_log"
down_revision = "20240917_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create shipment_request_log table."""
    op.create_table(
        "shipment_request_log",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("shipment_request_id", BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["shipment_request_id"],
            ["shipment_request.id"],
            name="fk_shipment_request_log_shipment_request_id",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Drop shipment_request_log table."""
    op.drop_table("shipment_request_log")
