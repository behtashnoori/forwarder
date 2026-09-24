"""Operational monitoring reliability and recoverable evaluation evidence.

Revision ID: 20260929_operational_monitoring_reliability
Revises: 20260928_operational_workspace_phase2
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_operational_monitoring_reliability"
down_revision = "20260928_operational_workspace_phase2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("oip_projection_state") as batch:
        batch.add_column(sa.Column("last_evaluation_attempt_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("last_evaluation_success_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("next_evaluation_due_at", sa.DateTime(timezone=True)))
    with op.batch_alter_table("oip_projection_health_history") as batch:
        batch.add_column(sa.Column("details_json", sa.JSON()))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM oip_projection_state
                    WHERE last_evaluation_attempt_at IS NOT NULL
                       OR last_evaluation_success_at IS NOT NULL
                       OR next_evaluation_due_at IS NOT NULL
                ) OR EXISTS (
                    SELECT 1 FROM oip_projection_health_history
                    WHERE details_json IS NOT NULL
                ) THEN
                    RAISE EXCEPTION
                        'cannot downgrade: operational monitoring reliability evidence exists'
                        USING ERRCODE='23503';
                END IF;
            END $$
        """))
    with op.batch_alter_table("oip_projection_health_history") as batch:
        batch.drop_column("details_json")
    with op.batch_alter_table("oip_projection_state") as batch:
        batch.drop_column("next_evaluation_due_at")
        batch.drop_column("last_evaluation_success_at")
        batch.drop_column("last_evaluation_attempt_at")
