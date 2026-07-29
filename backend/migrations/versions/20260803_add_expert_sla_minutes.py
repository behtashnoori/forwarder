"""Add admin-managed response SLA duration to experts."""
from alembic import op
import sqlalchemy as sa

revision = "20260803_expert_sla"
down_revision = "20260802_expert_scope"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("expert_user") as batch:
        batch.add_column(sa.Column("sla_response_work_minutes", sa.Integer(), nullable=False, server_default="120"))
        batch.create_check_constraint(
            "ck_expert_user_sla_response_work_minutes",
            "sla_response_work_minutes BETWEEN 1 AND 10080",
        )


def downgrade():
    with op.batch_alter_table("expert_user") as batch:
        batch.drop_constraint("ck_expert_user_sla_response_work_minutes", type_="check")
        batch.drop_column("sla_response_work_minutes")
