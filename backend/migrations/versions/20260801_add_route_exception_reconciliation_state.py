"""Add route-exception reconciliation transition state.

Revision ID: 20260801_route_exception
Revises: 20260730_multileg_route
"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_route_exception"
down_revision = "20260730_multileg_route"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("operational_idempotency") as batch:
        batch.add_column(sa.Column("response_json", sa.JSON()))
    with op.batch_alter_table("operational_work_item") as batch:
        batch.add_column(sa.Column("resolution_source", sa.String(20)))
        batch.add_column(sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("last_reconciled_at", sa.DateTime(timezone=True)))
        batch.create_check_constraint(
            "ck_route_exception_resolution_source",
            "resolution_source IS NULL OR resolution_source IN ('automatic','manual','supersession')",
        )


def downgrade():
    bind = op.get_bind()
    count = bind.execute(sa.text(
        "SELECT ("
        "  SELECT count(*) FROM operational_work_item "
        "  WHERE occurrence_count <> 1 "
        "     OR resolution_source IS NOT NULL "
        "     OR last_reconciled_at IS NOT NULL"
        ") + ("
        "  SELECT count(*) FROM operational_idempotency "
        "  WHERE response_json IS NOT NULL"
        ")"
    )).scalar_one()
    if count:
        raise RuntimeError("SAFE_DOWNGRADE_GUARD: route exception reconciliation history exists")
    with op.batch_alter_table("operational_work_item") as batch:
        batch.drop_constraint("ck_route_exception_resolution_source", type_="check")
        batch.drop_column("last_reconciled_at")
        batch.drop_column("occurrence_count")
        batch.drop_column("resolution_source")
    with op.batch_alter_table("operational_idempotency") as batch:
        batch.drop_column("response_json")
