"""Add governed simple Quote communication.

Revision ID: 20260925_quote_communication
Revises: 20260924_request_cargo_items
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260925_quote_communication"
down_revision = "20260924_request_cargo_items"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("expert_quote", schema=None) as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(36), nullable=True))
        batch_op.add_column(
            sa.Column("customer_response_message", sa.String(500), nullable=True)
        )
        batch_op.add_column(
            sa.Column("responded_by_customer_id", BIGINT, nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_expert_quote_responded_by_customer",
            "customer_gamification",
            ["responded_by_customer_id"],
            ["id"],
            ondelete="SET NULL",
        )

    bind = op.get_bind()
    quote_ids = bind.execute(
        sa.text("SELECT id FROM expert_quote WHERE public_id IS NULL ORDER BY id")
    ).scalars()
    for quote_id in quote_ids:
        bind.execute(
            sa.text("UPDATE expert_quote SET public_id = :public_id WHERE id = :id"),
            {"public_id": str(uuid4()), "id": quote_id},
        )

    with op.batch_alter_table("expert_quote", schema=None) as batch_op:
        batch_op.alter_column(
            "public_id", existing_type=sa.String(36), nullable=False
        )
        batch_op.create_unique_constraint(
            "uq_expert_quote_public_id", ["public_id"]
        )
        batch_op.drop_constraint(
            "ck_expert_quote_customer_response", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_expert_quote_customer_response",
            "customer_response IS NULL OR "
            "customer_response IN ('accepted', 'discussion', 'declined')",
        )
        batch_op.create_check_constraint(
            "ck_expert_quote_response_message",
            "(customer_response IS NULL AND customer_response_message IS NULL) OR "
            "(customer_response IN ('accepted', 'declined') AND "
            "customer_response_message IS NULL) OR "
            "(customer_response = 'discussion' AND "
            "customer_response_message IS NOT NULL AND "
            "length(trim(customer_response_message)) BETWEEN 1 AND 500)",
        )
        batch_op.create_index(
            "ix_expert_quote_responded_by_customer_id",
            ["responded_by_customer_id"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    evidence_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM expert_quote "
            "WHERE customer_response = 'discussion' "
            "OR customer_response_message IS NOT NULL "
            "OR responded_by_customer_id IS NOT NULL"
        )
    ).scalar_one()
    if evidence_count:
        raise RuntimeError(
            "Cannot downgrade while Quote communication evidence exists."
        )

    with op.batch_alter_table("expert_quote", schema=None) as batch_op:
        batch_op.drop_index("ix_expert_quote_responded_by_customer_id")
        batch_op.drop_constraint(
            "ck_expert_quote_response_message", type_="check"
        )
        batch_op.drop_constraint(
            "ck_expert_quote_customer_response", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_expert_quote_customer_response",
            "customer_response IS NULL OR "
            "customer_response IN ('accepted', 'declined')",
        )
        batch_op.drop_constraint(
            "uq_expert_quote_public_id", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_expert_quote_responded_by_customer", type_="foreignkey"
        )
        batch_op.drop_column("responded_by_customer_id")
        batch_op.drop_column("customer_response_message")
        batch_op.drop_column("public_id")
