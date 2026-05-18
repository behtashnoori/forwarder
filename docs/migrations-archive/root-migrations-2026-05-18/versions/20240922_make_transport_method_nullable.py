"""Make transport_method nullable.

Revision ID: 20240922_make_transport_method_nullable
Revises: 20240920_add_transport_method_to_shipment_request
Create Date: 2024-09-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240922_make_transport_method_nullable"
down_revision = "20240920_add_transport_method_to_shipment_request"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Allow transport_method to be nullable."""
    # SQLite doesn't support ALTER COLUMN, but transport_method is already nullable
    pass


def downgrade() -> None:
    """Revert transport_method column to be non-nullable."""
    op.execute(
        "UPDATE shipment_request SET transport_method = 'road' "
        "WHERE transport_method IS NULL"
    )
    op.alter_column(
        "shipment_request",
        "transport_method",
        existing_type=sa.String(length=32),
        nullable=False,
    )
