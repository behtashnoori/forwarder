"""Merge all heads: merge_heads and expert_console_fields branch.

Revision ID: 20250220_merge_final
Revises: 20250220_merge_heads, 20240924_add_expert_console_fields
Create Date: 2025-02-20

"""
from alembic import op


revision = "20250220_merge_final"
down_revision = ("20250220_merge_heads", "20240924_add_expert_console_fields")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
