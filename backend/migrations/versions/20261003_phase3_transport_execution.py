"""Phase 3 P3-04 route-stage transport execution and immutable history.

Revision ID: 20261003_phase3_transport_execution
Revises: 20261002_phase3_branched_route
"""

from alembic import op
import sqlalchemy as sa


revision = "20261003_phase3_transport_execution"
down_revision = "20261002_phase3_branched_route"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("execution_unit") as batch:
        batch.create_unique_constraint(
            "uq_execution_unit_id_org", ["id", "organization_id"]
        )

    op.create_table(
        "route_stage_execution",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("route_plan_id", BIGINT, nullable=False),
        sa.Column("route_leg_id", BIGINT, nullable=False),
        sa.Column("execution_unit_id", BIGINT, nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("public_id", name="uq_route_stage_execution_public_id"),
        sa.UniqueConstraint(
            "route_leg_id",
            "execution_unit_id",
            name="uq_route_stage_execution_leg_unit",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_route_stage_execution_org_idempotency",
        ),
        sa.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_route_stage_execution_shipment_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"],
            name="fk_route_stage_execution_plan_shipment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_leg_id", "route_plan_id"],
            ["route_leg.id", "route_leg.route_plan_id"],
            name="fk_route_stage_execution_leg_plan",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_unit_id", "organization_id"],
            ["execution_unit.id", "execution_unit.organization_id"],
            name="fk_route_stage_execution_unit_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["expert_user.id"],
            name="fk_route_stage_execution_creator",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_route_stage_execution_shipment_plan_leg",
        "route_stage_execution",
        ["operational_shipment_id", "route_plan_id", "route_leg_id"],
    )
    op.create_index(
        "ix_route_stage_execution_org_created",
        "route_stage_execution",
        ["organization_id", "created_at"],
    )

    op.create_table(
        "execution_transport_revision",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("execution_unit_id", BIGINT, nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("transport_means_type_id", BIGINT, nullable=False),
        sa.Column("means_type_code_snapshot", sa.String(64), nullable=False),
        sa.Column("means_type_fa_snapshot", sa.String(160), nullable=False),
        sa.Column("means_type_en_snapshot", sa.String(160), nullable=False),
        sa.Column("carrier_customer_id", BIGINT, nullable=True),
        sa.Column("carrier_label_snapshot", sa.String(200), nullable=True),
        sa.Column("means_identifier", sa.String(160), nullable=True),
        sa.Column("means_details", sa.String(500), nullable=True),
        sa.Column("driver_name", sa.String(160), nullable=True),
        sa.Column("driver_contact", sa.String(160), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("recorded_by_user_id", BIGINT, nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "public_id", name="uq_execution_transport_revision_public_id"
        ),
        sa.UniqueConstraint(
            "execution_unit_id",
            "revision_number",
            name="uq_execution_transport_revision_unit_number",
        ),
        sa.UniqueConstraint(
            "execution_unit_id",
            "idempotency_key",
            name="uq_execution_transport_revision_unit_idempotency",
        ),
        sa.UniqueConstraint(
            "id",
            "execution_unit_id",
            name="uq_execution_transport_revision_id_unit",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_execution_transport_revision_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["execution_unit_id", "organization_id"],
            ["execution_unit.id", "execution_unit.organization_id"],
            name="fk_execution_transport_revision_unit_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transport_means_type_id"],
            ["transport_means_type.id"],
            name="fk_execution_transport_revision_means_type",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["carrier_customer_id", "organization_id"],
            ["customer.id", "customer.operational_organization_id"],
            name="fk_execution_transport_revision_carrier_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["expert_user.id"],
            name="fk_execution_transport_revision_recorder",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_execution_transport_revision_unit_recorded",
        "execution_transport_revision",
        ["execution_unit_id", "recorded_at", "id"],
    )

    op.create_table(
        "execution_transport_equipment_snapshot",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("transport_revision_id", BIGINT, nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("transport_equipment_type_id", BIGINT, nullable=False),
        sa.Column("equipment_type_code_snapshot", sa.String(64), nullable=False),
        sa.Column("equipment_type_fa_snapshot", sa.String(160), nullable=False),
        sa.Column("equipment_type_en_snapshot", sa.String(160), nullable=False),
        sa.Column("identifier", sa.String(160), nullable=True),
        sa.Column("details", sa.String(500), nullable=True),
        sa.UniqueConstraint(
            "transport_revision_id",
            "sequence_number",
            name="uq_execution_transport_equipment_revision_sequence",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_execution_transport_equipment_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["transport_revision_id"],
            ["execution_transport_revision.id"],
            name="fk_execution_transport_equipment_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transport_equipment_type_id"],
            ["transport_equipment_type.id"],
            name="fk_execution_transport_equipment_type",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_execution_transport_equipment_type",
        "execution_transport_equipment_snapshot",
        ["transport_equipment_type_id"],
    )

    with op.batch_alter_table("operational_event") as batch:
        batch.add_column(
            sa.Column("transport_revision_id", BIGINT, nullable=True)
        )
        batch.create_foreign_key(
            "fk_operational_event_transport_revision_unit",
            "execution_transport_revision",
            ["transport_revision_id", "execution_unit_id"],
            ["id", "execution_unit_id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_operational_event_transport_revision_id",
        "operational_event",
        ["transport_revision_id"],
    )


def downgrade():
    bind = op.get_bind()
    used = bind.execute(
        sa.text(
            "SELECT "
            "(SELECT count(*) FROM route_stage_execution) + "
            "(SELECT count(*) FROM execution_transport_revision) + "
            "(SELECT count(*) FROM operational_event "
            "WHERE transport_revision_id IS NOT NULL)"
        )
    ).scalar_one()
    if used:
        raise RuntimeError(
            "Downgrade refused: Phase 3 P3-04 route-stage execution, "
            "transport history, or event-context data exists."
        )

    op.drop_index(
        "ix_operational_event_transport_revision_id",
        table_name="operational_event",
    )
    with op.batch_alter_table("operational_event") as batch:
        batch.drop_constraint(
            "fk_operational_event_transport_revision_unit", type_="foreignkey"
        )
        batch.drop_column("transport_revision_id")

    op.drop_index(
        "ix_execution_transport_equipment_type",
        table_name="execution_transport_equipment_snapshot",
    )
    op.drop_table("execution_transport_equipment_snapshot")
    op.drop_index(
        "ix_execution_transport_revision_unit_recorded",
        table_name="execution_transport_revision",
    )
    op.drop_table("execution_transport_revision")
    op.drop_index(
        "ix_route_stage_execution_org_created",
        table_name="route_stage_execution",
    )
    op.drop_index(
        "ix_route_stage_execution_shipment_plan_leg",
        table_name="route_stage_execution",
    )
    op.drop_table("route_stage_execution")

    with op.batch_alter_table("execution_unit") as batch:
        batch.drop_constraint("uq_execution_unit_id_org", type_="unique")
