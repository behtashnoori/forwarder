"""Phase 3 P3-03 branched planned route and actual traversal facts.

Revision ID: 20261002_phase3_branched_route
Revises: 20261001_phase3_cargo_lineage
"""

from alembic import op
import sqlalchemy as sa


revision = "20261002_phase3_branched_route"
down_revision = "20261001_phase3_cargo_lineage"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("shipment_cargo_item") as batch:
        batch.create_unique_constraint(
            "uq_shipment_cargo_item_id_shipment",
            ["id", "operational_shipment_id"],
        )

    with op.batch_alter_table("route_leg") as batch:
        batch.add_column(sa.Column("parent_route_leg_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("branch_label", sa.String(160), nullable=True))
        batch.alter_column(
            "transport_mode", existing_type=sa.String(32), nullable=True
        )
        batch.alter_column(
            "planned_departure", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch.alter_column(
            "planned_arrival", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch.create_foreign_key(
            "fk_route_leg_parent_same_plan",
            "route_leg",
            ["parent_route_leg_id", "route_plan_id"],
            ["id", "route_plan_id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_route_leg_parent_route_leg_id", "route_leg", ["parent_route_leg_id"]
    )

    op.create_table(
        "route_cargo_destination",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("route_plan_id", BIGINT, nullable=False),
        sa.Column("shipment_cargo_item_id", BIGINT, nullable=False),
        sa.Column("destination_route_leg_id", BIGINT, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "route_plan_id",
            "shipment_cargo_item_id",
            name="uq_route_cargo_destination_plan_cargo",
        ),
        sa.CheckConstraint(
            "version >= 1", name="ck_route_cargo_destination_version"
        ),
        sa.ForeignKeyConstraint(
            ["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"],
            name="fk_route_cargo_destination_plan_shipment",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["destination_route_leg_id", "route_plan_id"],
            ["route_leg.id", "route_leg.route_plan_id"],
            name="fk_route_cargo_destination_leg_plan",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["shipment_cargo_item_id", "operational_shipment_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"],
            name="fk_route_cargo_destination_cargo_shipment",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["expert_user.id"],
            name="fk_route_cargo_destination_creator",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_route_cargo_destination_shipment_plan",
        "route_cargo_destination",
        ["operational_shipment_id", "route_plan_id"],
    )

    op.create_table(
        "route_traversal_fact",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("route_plan_id", BIGINT, nullable=False),
        sa.Column("planned_route_leg_id", BIGINT, nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("origin_location_id", BIGINT, nullable=False),
        sa.Column("destination_location_id", BIGINT, nullable=False),
        sa.Column("origin_logistics_point_id", BIGINT, nullable=True),
        sa.Column("destination_logistics_point_id", BIGINT, nullable=True),
        sa.Column("origin_snapshot", sa.JSON(), nullable=False),
        sa.Column("destination_snapshot", sa.JSON(), nullable=False),
        sa.Column("departed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("recorded_by_user_id", BIGINT, nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "route_plan_id",
            "sequence_number",
            name="uq_route_traversal_plan_sequence",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1", name="ck_route_traversal_sequence_positive"
        ),
        sa.CheckConstraint(
            "departed_at IS NOT NULL OR arrived_at IS NOT NULL",
            name="ck_route_traversal_has_occurrence",
        ),
        sa.CheckConstraint(
            "arrived_at IS NULL OR departed_at IS NULL OR arrived_at >= departed_at",
            name="ck_route_traversal_timeline",
        ),
        sa.CheckConstraint(
            "origin_location_id <> destination_location_id OR "
            "COALESCE(origin_logistics_point_id, 0) <> "
            "COALESCE(destination_logistics_point_id, 0)",
            name="ck_route_traversal_distinct_locations",
        ),
        sa.CheckConstraint("version >= 1", name="ck_route_traversal_version"),
        sa.ForeignKeyConstraint(
            ["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"],
            name="fk_route_traversal_plan_shipment",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["planned_route_leg_id", "route_plan_id"],
            ["route_leg.id", "route_leg.route_plan_id"],
            name="fk_route_traversal_leg_plan",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_location_id"],
            ["canonical_location.id"],
            name="fk_route_traversal_origin_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_location_id"],
            ["canonical_location.id"],
            name="fk_route_traversal_destination_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_logistics_point_id"],
            ["logistics_point.id"],
            name="fk_route_traversal_origin_point",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_logistics_point_id"],
            ["logistics_point.id"],
            name="fk_route_traversal_destination_point",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["expert_user.id"],
            name="fk_route_traversal_recorder",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_route_traversal_shipment_plan",
        "route_traversal_fact",
        ["operational_shipment_id", "route_plan_id"],
    )


def downgrade():
    bind = op.get_bind()
    used = bind.execute(
        sa.text(
            "SELECT "
            "(SELECT count(*) FROM route_cargo_destination) + "
            "(SELECT count(*) FROM route_traversal_fact) + "
            "(SELECT count(*) FROM route_leg WHERE parent_route_leg_id IS NOT NULL "
            "OR branch_label IS NOT NULL OR transport_mode IS NULL "
            "OR planned_departure IS NULL OR planned_arrival IS NULL)"
        )
    ).scalar_one()
    if used:
        raise RuntimeError(
            "Downgrade refused: Phase 3 P3-03 branch, Cargo-destination, "
            "actual-route, or incomplete-route data exists."
        )

    op.drop_index(
        "ix_route_traversal_shipment_plan", table_name="route_traversal_fact"
    )
    op.drop_table("route_traversal_fact")
    op.drop_index(
        "ix_route_cargo_destination_shipment_plan",
        table_name="route_cargo_destination",
    )
    op.drop_table("route_cargo_destination")

    op.drop_index("ix_route_leg_parent_route_leg_id", table_name="route_leg")
    with op.batch_alter_table("route_leg") as batch:
        batch.drop_constraint("fk_route_leg_parent_same_plan", type_="foreignkey")
        batch.alter_column(
            "planned_arrival", existing_type=sa.DateTime(timezone=True), nullable=False
        )
        batch.alter_column(
            "planned_departure", existing_type=sa.DateTime(timezone=True), nullable=False
        )
        batch.alter_column(
            "transport_mode", existing_type=sa.String(32), nullable=False
        )
        batch.drop_column("branch_label")
        batch.drop_column("parent_route_leg_id")

    with op.batch_alter_table("shipment_cargo_item") as batch:
        batch.drop_constraint("uq_shipment_cargo_item_id_shipment", type_="unique")
