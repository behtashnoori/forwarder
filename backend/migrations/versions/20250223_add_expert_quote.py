"""Add expert_quote table for storing quotes per request.

Revision ID: 20250223_quote
Revises: 20250221_site
Create Date: 2025-02-23

"""
from alembic import op
import sqlalchemy as sa

revision = "20250223_quote"
down_revision = "20250221_site"
branch_labels = None
depends_on = None

SQLITE_BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "expert_quote",
        sa.Column("id", SQLITE_BIGINT, primary_key=True, autoincrement=True),
        sa.Column("shipment_request_id", SQLITE_BIGINT, nullable=False),
        sa.Column("amount", SQLITE_BIGINT, nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="IRR"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_by_expert_id", SQLITE_BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["shipment_request_id"], ["shipment_request.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_expert_id"], ["expert_user.id"]),
    )
    op.create_index("idx_expert_quote_request_id", "expert_quote", ["shipment_request_id"])


def downgrade():
    op.drop_index("idx_expert_quote_request_id", "expert_quote")
    op.drop_table("expert_quote")
