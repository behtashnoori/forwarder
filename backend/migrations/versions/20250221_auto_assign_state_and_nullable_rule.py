"""Add auto-assign state table and make referral_assignment_log.rule_id nullable.

Revision ID: 20250221_auto
Revises: 20250221_referral
Create Date: 2025-02-21

"""
from alembic import op
import sqlalchemy as sa

revision = "20250221_auto"
down_revision = "20250221_referral"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "referral_auto_assign_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_index", sa.Integer(), default=0),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Seed single row for round-robin state (SQLite: datetime('now'); PostgreSQL: NOW())
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        op.execute("INSERT INTO referral_auto_assign_state (id, last_index, updated_at) VALUES (1, 0, datetime('now'))")
    else:
        op.execute("INSERT INTO referral_auto_assign_state (id, last_index, updated_at) VALUES (1, 0, NOW())")
    # SQLite doesn't support ALTER COLUMN; use batch for SQLite
    with op.batch_alter_table("referral_assignment_log", schema=None) as batch_op:
        batch_op.alter_column(
            "rule_id",
            existing_type=sa.BigInteger(),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table("referral_assignment_log", schema=None) as batch_op:
        batch_op.alter_column(
            "rule_id",
            existing_type=sa.BigInteger(),
            nullable=False,
        )
    op.drop_table("referral_auto_assign_state")
