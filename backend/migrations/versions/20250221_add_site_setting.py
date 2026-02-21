"""Add site_setting table for editable site content.

Revision ID: 20250221_site
Revises: 20250221_auto
Create Date: 2025-02-21

"""
from alembic import op
import sqlalchemy as sa

revision = "20250221_site"
down_revision = "20250221_auto"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_setting",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade():
    op.drop_table("site_setting")
