"""P3-05 stage-scoped planned/actual allocation with immutable history.

Revision ID: 20261004_phase3_cargo_allocation_trace
Revises: 20261003_phase3_transport_execution
"""

from alembic import op
import sqlalchemy as sa


revision = "20261004_phase3_cargo_allocation_trace"
down_revision = "20261003_phase3_transport_execution"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("execution_unit_cargo_allocation") as batch:
        batch.drop_constraint("uq_execution_unit_cargo_allocation_pair", type_="unique")
        batch.add_column(sa.Column("route_stage_execution_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("dimension", sa.String(8), nullable=True))
        batch.add_column(sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_foreign_key("fk_execution_cargo_allocation_stage", "route_stage_execution", ["route_stage_execution_id"], ["id"], ondelete="RESTRICT")
        batch.create_check_constraint("ck_execution_cargo_allocation_dimension", "dimension IS NULL OR dimension IN ('PLANNED','ACTUAL')")
        batch.create_check_constraint("ck_execution_cargo_allocation_version", "version >= 1")
        batch.create_check_constraint("ck_execution_cargo_allocation_stage_dimension", "(route_stage_execution_id IS NULL AND dimension IS NULL) OR (route_stage_execution_id IS NOT NULL AND dimension IS NOT NULL)")
    op.create_index("uq_execution_cargo_allocation_current_stage", "execution_unit_cargo_allocation", ["shipment_cargo_item_id", "route_stage_execution_id", "dimension"], unique=True, postgresql_where=sa.text("is_current AND route_stage_execution_id IS NOT NULL"), sqlite_where=sa.text("is_current = 1 AND route_stage_execution_id IS NOT NULL"))
    op.create_index("uq_execution_cargo_allocation_current_legacy", "execution_unit_cargo_allocation", ["shipment_cargo_item_id", "execution_unit_id"], unique=True, postgresql_where=sa.text("is_current AND route_stage_execution_id IS NULL"), sqlite_where=sa.text("is_current = 1 AND route_stage_execution_id IS NULL"))
    op.create_index("ix_execution_cargo_allocation_stage", "execution_unit_cargo_allocation", ["route_stage_execution_id", "dimension"])

    op.create_table(
        "cargo_allocation_transfer",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("shipment_cargo_item_id", BIGINT, sa.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_allocation_id", BIGINT, sa.ForeignKey("execution_unit_cargo_allocation.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_allocation_id", BIGINT, sa.ForeignKey("execution_unit_cargo_allocation.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by_user_id", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("context", sa.String(300), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_cargo_allocation_transfer_key"),
        sa.CheckConstraint("quantity > 0", name="ck_cargo_allocation_transfer_positive"),
        sa.CheckConstraint("source_allocation_id <> target_allocation_id", name="ck_cargo_allocation_transfer_distinct"),
    )
    op.create_index("ix_cargo_allocation_transfer_cargo_time", "cargo_allocation_transfer", ["shipment_cargo_item_id", "recorded_at"])
    op.create_table(
        "cargo_allocation_revision",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("shipment_cargo_item_id", BIGINT, sa.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("allocation_id", BIGINT, sa.ForeignKey("execution_unit_cargo_allocation.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("before_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("after_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by_user_id", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("transfer_id", BIGINT, sa.ForeignKey("cargo_allocation_transfer.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("allocation_id", "revision_number", name="uq_cargo_allocation_revision_number"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_cargo_allocation_revision_key"),
        sa.CheckConstraint("revision_number >= 1", name="ck_cargo_allocation_revision_number"),
        sa.CheckConstraint("before_quantity >= 0 AND after_quantity >= 0", name="ck_cargo_allocation_revision_quantities"),
    )
    op.create_index("ix_cargo_allocation_revision_cargo_time", "cargo_allocation_revision", ["shipment_cargo_item_id", "recorded_at"])


def downgrade():
    connection = op.get_bind()
    for table in ("cargo_allocation_revision", "cargo_allocation_transfer"):
        if connection.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("P3-05 history exists; downgrade would erase operational facts")
    if connection.execute(sa.text("SELECT 1 FROM execution_unit_cargo_allocation WHERE route_stage_execution_id IS NOT NULL OR NOT is_current LIMIT 1")).first():
        raise RuntimeError("P3-05 allocation state exists; downgrade would erase meaning")
    op.drop_index("ix_cargo_allocation_revision_cargo_time", table_name="cargo_allocation_revision")
    op.drop_table("cargo_allocation_revision")
    op.drop_index("ix_cargo_allocation_transfer_cargo_time", table_name="cargo_allocation_transfer")
    op.drop_table("cargo_allocation_transfer")
    op.drop_index("ix_execution_cargo_allocation_stage", table_name="execution_unit_cargo_allocation")
    op.drop_index("uq_execution_cargo_allocation_current_legacy", table_name="execution_unit_cargo_allocation")
    op.drop_index("uq_execution_cargo_allocation_current_stage", table_name="execution_unit_cargo_allocation")
    with op.batch_alter_table("execution_unit_cargo_allocation") as batch:
        batch.drop_constraint("ck_execution_cargo_allocation_stage_dimension", type_="check")
        batch.drop_constraint("ck_execution_cargo_allocation_version", type_="check")
        batch.drop_constraint("ck_execution_cargo_allocation_dimension", type_="check")
        batch.drop_constraint("fk_execution_cargo_allocation_stage", type_="foreignkey")
        batch.drop_column("version")
        batch.drop_column("is_current")
        batch.drop_column("dimension")
        batch.drop_column("route_stage_execution_id")
        batch.create_unique_constraint("uq_execution_unit_cargo_allocation_pair", ["shipment_cargo_item_id", "execution_unit_id"])
