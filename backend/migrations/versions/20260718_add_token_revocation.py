"""Add server-side JWT revocation storage.

Revision ID: 20260718_add_token_revocation
Revises: 20260717_add_customs_office_domain
"""
from alembic import op
import sqlalchemy as sa

revision = "20260718_add_token_revocation"
down_revision = "20260717_add_customs_office_domain"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "revoked_token",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("jti", sa.String(36), nullable=False),
        sa.Column("user_id", BIGINT, nullable=True),
        sa.Column("token_type", sa.String(16), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("token_type IN ('access', 'refresh')", name="ck_revoked_token_type"),
        sa.CheckConstraint("reason IN ('logout', 'password_changed', 'account_deactivated', 'admin_revoked', 'security_event')", name="ck_revoked_token_reason"),
        sa.ForeignKeyConstraint(["user_id"], ["expert_user.id"], name="fk_revoked_token_user", ondelete="SET NULL"),
        sa.UniqueConstraint("jti", name="uq_revoked_token_jti"),
    )
    op.create_index("ix_revoked_token_jti", "revoked_token", ["jti"])
    op.create_index("ix_revoked_token_user_id", "revoked_token", ["user_id"])
    op.create_index("ix_revoked_token_expires_at", "revoked_token", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_revoked_token_expires_at", table_name="revoked_token")
    op.drop_index("ix_revoked_token_user_id", table_name="revoked_token")
    op.drop_index("ix_revoked_token_jti", table_name="revoked_token")
    op.drop_table("revoked_token")
