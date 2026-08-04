"""Disable accounts that retain the historical shared credential hash.

Revision ID: security_credential_remediation
Revises: 20260811_project_configuration
Create Date: 2026-08-04

The 20240926 migration is immutable and must remain replayable. This additive
revision preserves users, identifiers, relationships, and password hashes while
making the legacy shared credential non-executable.
"""

from alembic import op
import sqlalchemy as sa


revision = "security_credential_remediation"
down_revision = "20260811_project_configuration"
branch_labels = None
depends_on = None


LEGACY_SHARED_PASSWORD_HASH = (
    "$2b$12$LQv3c1yqBWVHxkd0LQ4Q2e7Tq4lY8k9Z6p5v3nF7j8K2w4N9m1X8d"
)


def upgrade():
    expert_user = sa.table(
        "expert_user",
        sa.column("password_hash", sa.String(length=128)),
        sa.column("is_active", sa.Boolean()),
    )
    op.execute(
        expert_user.update()
        .where(expert_user.c.password_hash == LEGACY_SHARED_PASSWORD_HASH)
        .values(is_active=False)
    )


def downgrade():
    # Deliberately irreversible: re-enabling a known shared credential would
    # recreate the vulnerability. Rows and hashes remain available for audit.
    pass
