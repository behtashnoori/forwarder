"""Repair referral auto-assignment state sequence compatibility.

Revision ID: 20260828_referral_state_compat
Revises: 20260827_org_hostname
"""

from alembic import op


revision = "20260828_referral_state_compat"
down_revision = "20260827_org_hostname"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return

    op.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('referral_auto_assign_state', 'id'),
            GREATEST(
                COALESCE((SELECT MAX(id) FROM referral_auto_assign_state), 1),
                (SELECT last_value FROM referral_auto_assign_state_id_seq)
            ),
            CASE
                WHEN EXISTS (SELECT 1 FROM referral_auto_assign_state) THEN true
                ELSE (SELECT is_called FROM referral_auto_assign_state_id_seq)
            END
        )
        """
    )


def downgrade():
    # Sequence advancement is intentionally not reversed: lowering it can
    # reintroduce duplicate primary-key allocation after application rollback.
    pass
