"""add code column to province

Revision ID: 20240919_add_code_to_province
Revises: 20240918_add_shipment_request_log
Create Date: 2024-09-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240919_add_code_to_province"
down_revision = "20240918_add_shipment_request_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the code column to the province table."""
    op.add_column(
        "province",
        sa.Column("code", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    """Remove the code column from the province table."""
    op.drop_column("province", "code")
