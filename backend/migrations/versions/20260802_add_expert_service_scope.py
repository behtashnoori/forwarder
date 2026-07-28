"""Add domestic and international expert assignment capabilities.

Revision ID: 20260802_expert_scope
Revises: 20260801_route_exception
"""
from alembic import op
import sqlalchemy as sa

revision = "20260802_expert_scope"
down_revision = "20260801_route_exception"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("expert_user") as batch:
        batch.add_column(sa.Column("can_handle_domestic", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("can_handle_international", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table("expert_user") as batch:
        batch.drop_column("can_handle_international")
        batch.drop_column("can_handle_domestic")
