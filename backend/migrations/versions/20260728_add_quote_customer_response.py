"""Add customer response fields to expert_quote

Revision ID: 20260728_add_quote_customer_response
Revises: 20260727_add_iran_destination_point
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260728_add_quote_customer_response"
down_revision = "20260727_add_iran_destination_point"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("expert_quote", schema=None) as batch_op:
        batch_op.add_column(sa.Column("customer_response", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("responded_at", sa.DateTime(), nullable=True))
        batch_op.create_check_constraint(
            "ck_expert_quote_customer_response",
            "customer_response IS NULL OR customer_response IN ('accepted', 'declined')",
        )


def downgrade():
    with op.batch_alter_table("expert_quote", schema=None) as batch_op:
        batch_op.drop_constraint("ck_expert_quote_customer_response", type_="check")
        batch_op.drop_column("responded_at")
        batch_op.drop_column("customer_response")
