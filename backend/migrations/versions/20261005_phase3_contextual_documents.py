"""P3-06 exact-version typed document context and explicit audience.

Revision ID: 20261005_phase3_contextual_documents
Revises: 20261004_phase3_cargo_allocation_trace
"""

from alembic import op
import sqlalchemy as sa


revision = "20261005_phase3_contextual_documents"
down_revision = "20261004_phase3_cargo_allocation_trace"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_unique_constraint(
        "uq_case_document_file_shipment_org", "case_document_file",
        ["id", "operational_shipment_id", "operational_organization_id"],
    )
    op.create_table(
        "operational_document_context",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operational_shipment_id", BIGINT, sa.ForeignKey("operational_shipment.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_file_id", BIGINT, sa.ForeignKey("case_document_file.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("context_type", sa.String(20), nullable=False),
        sa.Column("cargo_item_id", BIGINT, sa.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT")),
        sa.Column("route_leg_id", BIGINT, sa.ForeignKey("route_leg.id", ondelete="RESTRICT")),
        sa.Column("execution_unit_id", BIGINT, sa.ForeignKey("execution_unit.id", ondelete="RESTRICT")),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="INTERNAL"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_id", name="uq_operational_document_context_public_id"),
        sa.UniqueConstraint("document_file_id", name="uq_operational_document_context_file"),
        sa.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_operational_document_context_shipment_org", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_file_id", "operational_shipment_id", "organization_id"],
            ["case_document_file.id", "case_document_file.operational_shipment_id",
             "case_document_file.operational_organization_id"],
            name="fk_operational_document_context_file_parent", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cargo_item_id", "operational_shipment_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"],
            name="fk_operational_document_context_cargo_parent", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_unit_id", "organization_id"],
            ["execution_unit.id", "execution_unit.organization_id"],
            name="fk_operational_document_context_execution_org", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("context_type IN ('SHIPMENT','CARGO','ROUTE_LEG','EXECUTION_UNIT')", name="ck_operational_document_context_type"),
        sa.CheckConstraint("visibility IN ('INTERNAL','CARGO_OWNER','EXPLICIT_SHARED')", name="ck_operational_document_context_visibility"),
        sa.CheckConstraint(
            "(context_type = 'SHIPMENT' AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL) OR "
            "(context_type = 'CARGO' AND cargo_item_id IS NOT NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL) OR "
            "(context_type = 'ROUTE_LEG' AND cargo_item_id IS NULL AND route_leg_id IS NOT NULL AND execution_unit_id IS NULL) OR "
            "(context_type = 'EXECUTION_UNIT' AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NOT NULL)",
            name="ck_operational_document_context_one_target",
        ),
        sa.CheckConstraint("visibility <> 'CARGO_OWNER' OR context_type = 'CARGO'", name="ck_operational_document_cargo_owner_scope"),
    )
    op.create_index("ix_operational_document_context_parent", "operational_document_context", ["organization_id", "operational_shipment_id", "context_type"])
    op.create_table(
        "operational_document_audience",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("context_id", BIGINT, sa.ForeignKey("operational_document_context.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_portal_account_id", BIGINT, sa.ForeignKey("customer_gamification.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by_user_id", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("context_id", "customer_portal_account_id", name="uq_operational_document_audience_account"),
    )
    op.create_index("ix_operational_document_audience_account", "operational_document_audience", ["customer_portal_account_id", "context_id"])
    op.create_table(
        "operational_document_context_event",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, sa.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("context_id", BIGINT, sa.ForeignKey("operational_document_context.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_file_id", BIGINT, sa.ForeignKey("case_document_file.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("before_fact", sa.JSON()),
        sa.Column("after_fact", sa.JSON(), nullable=False),
        sa.Column("actor_user_id", BIGINT, sa.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_id", name="uq_operational_document_context_event_public_id"),
    )
    op.create_index("ix_operational_document_context_event_history", "operational_document_context_event", ["context_id", "recorded_at", "id"])


def downgrade():
    connection = op.get_bind()
    for table in ("operational_document_context_event", "operational_document_audience", "operational_document_context"):
        if connection.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("P3-06 document facts exist; downgrade would erase context or audience history")
    op.drop_index("ix_operational_document_context_event_history", table_name="operational_document_context_event")
    op.drop_table("operational_document_context_event")
    op.drop_index("ix_operational_document_audience_account", table_name="operational_document_audience")
    op.drop_table("operational_document_audience")
    op.drop_index("ix_operational_document_context_parent", table_name="operational_document_context")
    op.drop_table("operational_document_context")
    op.drop_constraint("uq_case_document_file_shipment_org", "case_document_file", type_="unique")
