"""Add canonical ExecutionUnit and OperationalEvent vertical slice.

Revision ID: 20260806_execution_units
Revises: 20260805_project_foundation
"""
from alembic import op
import sqlalchemy as sa

revision = "20260806_execution_units"
down_revision = "20260805_project_foundation"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("project") as batch:
        batch.add_column(sa.Column("tracking_code", sa.String(48), nullable=True))
        batch.create_unique_constraint("uq_project_tracking_code", ["tracking_code"])

    op.create_table(
        "execution_unit",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("project_id", BIGINT, nullable=False),
        sa.Column("operational_shipment_id", BIGINT),
        sa.Column("legacy_unit_id", BIGINT),
        sa.Column("unit_code", sa.String(64), nullable=False),
        sa.Column("unit_type", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(160)),
        sa.Column("vehicle_reference", sa.String(160)),
        sa.Column("lifecycle_status", sa.String(24), nullable=False, server_default="not_started"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("attention_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delayed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("latest_checkpoint", sa.String(255)),
        sa.Column("last_event_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operational_shipment_id"], ["operational_shipment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["legacy_unit_id"], ["shipment_transport_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("public_id", name="uq_execution_unit_public_id"),
        sa.UniqueConstraint("project_id", "unit_code", name="uq_execution_unit_project_code"),
        sa.UniqueConstraint("legacy_unit_id", name="uq_execution_unit_legacy_unit"),
        sa.CheckConstraint("lifecycle_status IN ('not_started','ready','in_progress','arrived','delivered','cancelled')", name="ck_execution_unit_lifecycle_status"),
        sa.CheckConstraint("version >= 1", name="ck_execution_unit_version_positive"),
    )
    op.create_index("ix_execution_unit_project_status_active", "execution_unit", ["project_id", "lifecycle_status", "is_active"])
    op.create_index("ix_execution_unit_project_updated", "execution_unit", ["project_id", "updated_at"])
    op.create_table(
        "operational_event",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("project_id", BIGINT, nullable=False),
        sa.Column("execution_unit_id", BIGINT, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("lifecycle_status", sa.String(24)),
        sa.Column("checkpoint_text", sa.String(255)),
        sa.Column("customer_message", sa.Text()),
        sa.Column("internal_note", sa.Text()),
        sa.Column("visibility", sa.String(16), nullable=False, server_default="internal"),
        sa.Column("attention_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delayed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", BIGINT, nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="expert"),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(100)),
        sa.Column("batch_id", sa.String(100)),
        sa.Column("supersedes_event_id", BIGINT),
        sa.Column("threshold_policy_version", sa.String(32)),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["execution_unit_id"], ["execution_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_event_id"], ["operational_event.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("public_id", name="uq_operational_event_public_id"),
        sa.UniqueConstraint("execution_unit_id", "idempotency_key", name="uq_operational_event_unit_idempotency"),
        sa.CheckConstraint("visibility IN ('internal','customer')", name="ck_operational_event_visibility"),
    )
    op.create_index("ix_operational_event_unit_occurred", "operational_event", ["execution_unit_id", "occurred_at", "id"])
    op.create_index("ix_operational_event_project_recorded", "operational_event", ["project_id", "recorded_at", "id"])


def downgrade():
    op.drop_index("ix_operational_event_project_recorded", table_name="operational_event")
    op.drop_index("ix_operational_event_unit_occurred", table_name="operational_event")
    op.drop_table("operational_event")
    op.drop_index("ix_execution_unit_project_updated", table_name="execution_unit")
    op.drop_index("ix_execution_unit_project_status_active", table_name="execution_unit")
    op.drop_table("execution_unit")
    with op.batch_alter_table("project") as batch:
        batch.drop_constraint("uq_project_tracking_code", type_="unique")
        batch.drop_column("tracking_code")
