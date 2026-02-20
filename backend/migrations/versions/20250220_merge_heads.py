"""Merge heads: tracking_code and iran_entry_point branches.

Revision ID: 20250220_merge_heads
Revises: 20250220_add_tracking_code, 20250115_add_iran_entry_point_fields
Create Date: 2025-02-20

"""
from alembic import op


revision = "20250220_merge_heads"
down_revision = ("20250220_add_tracking_code", "20250115_add_iran_entry_point_fields")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
