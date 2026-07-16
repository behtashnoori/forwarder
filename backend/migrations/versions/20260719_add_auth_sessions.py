"""Add server-side authentication sessions and refresh rotation state.

Revision ID: 20260719_add_auth_sessions
Revises: 20260718_add_token_revocation
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_add_auth_sessions"
down_revision = "20260718_add_token_revocation"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

OLD_REASONS = "'logout', 'password_changed', 'account_deactivated', 'admin_revoked', 'security_event'"
NEW_REASONS = (
    "'logout', 'logout_all', 'refresh_rotated', 'refresh_reuse_detected', 'password_changed', "
    "'account_deactivated', 'account_deleted', 'admin_revoked', 'expired', 'security_event'"
)


def upgrade() -> None:
    op.create_table(
        "auth_session",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("user_id", BIGINT, nullable=False),
        sa.Column("refresh_jti", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_rotated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "revoked_reason IS NULL OR revoked_reason IN ('logout', 'logout_all', 'refresh_reuse_detected', "
            "'password_changed', 'account_deactivated', 'account_deleted', 'admin_revoked', 'expired', 'security_event')",
            name="ck_auth_session_revoked_reason",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["expert_user.id"], name="fk_auth_session_user", ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", name="uq_auth_session_session_id"),
        sa.UniqueConstraint("refresh_jti", name="uq_auth_session_refresh_jti"),
    )
    op.create_index("ix_auth_session_user_id", "auth_session", ["user_id"])
    op.create_index("ix_auth_session_expires_at", "auth_session", ["expires_at"])
    op.create_index("ix_auth_session_is_active", "auth_session", ["is_active"])

    # PostgreSQL unique constraints already provide exact-key indexes for these columns.
    op.drop_index("ix_revoked_token_jti", table_name="revoked_token")
    with op.batch_alter_table("revoked_token") as batch:
        batch.drop_constraint("ck_revoked_token_reason", type_="check")
        batch.create_check_constraint("ck_revoked_token_reason", f"reason IN ({NEW_REASONS})")


def downgrade() -> None:
    op.execute(
        "DELETE FROM revoked_token WHERE reason IN "
        "('logout_all', 'refresh_rotated', 'refresh_reuse_detected', 'account_deleted', 'expired')"
    )
    with op.batch_alter_table("revoked_token") as batch:
        batch.drop_constraint("ck_revoked_token_reason", type_="check")
        batch.create_check_constraint("ck_revoked_token_reason", f"reason IN ({OLD_REASONS})")
    op.create_index("ix_revoked_token_jti", "revoked_token", ["jti"])
    op.drop_index("ix_auth_session_is_active", table_name="auth_session")
    op.drop_index("ix_auth_session_expires_at", table_name="auth_session")
    op.drop_index("ix_auth_session_user_id", table_name="auth_session")
    op.drop_table("auth_session")
