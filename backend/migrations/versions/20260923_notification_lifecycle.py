"""Add minimal durable notification claim fencing.

Revision ID: 20260923_notification_lifecycle
Revises: 20260922_notification_foundation
"""
from alembic import op
import sqlalchemy as sa


revision = "20260923_notification_lifecycle"
down_revision = "20260922_notification_foundation"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notification_attempt") as batch_op:
        batch_op.add_column(sa.Column("claim_token", sa.String(36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "claim_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.create_unique_constraint(
            "uq_notification_attempt_claim_token", ["claim_token"]
        )
        batch_op.create_check_constraint(
            "ck_notification_attempt_claim_pair",
            "(claim_token IS NULL AND claim_expires_at IS NULL) OR "
            "(claim_token IS NOT NULL AND claim_expires_at IS NOT NULL)",
        )


def downgrade():
    bind = op.get_bind()
    active_claim_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM notification_attempt "
            "WHERE claim_token IS NOT NULL OR claim_expires_at IS NOT NULL"
        )
    ).scalar_one()
    if active_claim_count:
        raise RuntimeError(
            "Cannot downgrade while notification lifecycle claims exist."
        )

    with op.batch_alter_table("notification_attempt") as batch_op:
        batch_op.drop_constraint(
            "ck_notification_attempt_claim_pair", type_="check"
        )
        batch_op.drop_constraint(
            "uq_notification_attempt_claim_token", type_="unique"
        )
        batch_op.drop_column("claim_expires_at")
        batch_op.drop_column("claim_token")
