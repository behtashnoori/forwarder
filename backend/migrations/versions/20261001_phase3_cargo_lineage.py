"""Phase 3 P3-02 Cargo customer/request lineage and semantic quantities.

Revision ID: 20261001_phase3_cargo_lineage
Revises: 20260930_phase3_reference_catalog
"""

from alembic import op
import sqlalchemy as sa


revision = "20261001_phase3_cargo_lineage"
down_revision = "20260930_phase3_reference_catalog"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("request_cargo_item") as batch:
        batch.create_unique_constraint(
            "uq_request_cargo_item_id_request",
            ["id", "shipment_request_id"],
        )

    with op.batch_alter_table("shipment_cargo_item") as batch:
        batch.add_column(sa.Column("source_shipment_request_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("source_request_cargo_item_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("requested_quantity", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("planned_quantity", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("actual_quantity", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("packaging_type_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("packaging_code_snapshot", sa.String(64), nullable=True))
        batch.add_column(sa.Column("packaging_fa_snapshot", sa.String(160), nullable=True))
        batch.add_column(sa.Column("packaging_en_snapshot", sa.String(160), nullable=True))
        batch.add_column(sa.Column("gross_weight", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("gross_weight_uom_id", BIGINT, nullable=True))
        batch.add_column(
            sa.Column("gross_weight_uom_code_snapshot", sa.String(64), nullable=True)
        )
        batch.add_column(
            sa.Column("gross_weight_uom_symbol_snapshot", sa.String(32), nullable=True)
        )
        batch.add_column(sa.Column("volume", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("volume_uom_id", BIGINT, nullable=True))
        batch.add_column(
            sa.Column("volume_uom_code_snapshot", sa.String(64), nullable=True)
        )
        batch.add_column(
            sa.Column("volume_uom_symbol_snapshot", sa.String(32), nullable=True)
        )
        batch.add_column(sa.Column("destination_description", sa.String(300), nullable=True))

        batch.create_foreign_key(
            "fk_shipment_cargo_source_request",
            "shipment_request",
            ["source_shipment_request_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_shipment_cargo_source_item_request",
            "request_cargo_item",
            ["source_request_cargo_item_id", "source_shipment_request_id"],
            ["id", "shipment_request_id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_shipment_cargo_packaging_type",
            "packaging_type",
            ["packaging_type_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_shipment_cargo_weight_uom",
            "unit_of_measure",
            ["gross_weight_uom_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_shipment_cargo_volume_uom",
            "unit_of_measure",
            ["volume_uom_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_check_constraint(
            "ck_shipment_cargo_requested_quantity_positive",
            "requested_quantity IS NULL OR requested_quantity > 0",
        )
        batch.create_check_constraint(
            "ck_shipment_cargo_planned_quantity_positive",
            "planned_quantity IS NULL OR planned_quantity > 0",
        )
        batch.create_check_constraint(
            "ck_shipment_cargo_actual_quantity_positive",
            "actual_quantity IS NULL OR actual_quantity > 0",
        )
        batch.create_check_constraint(
            "ck_shipment_cargo_requested_has_source",
            "requested_quantity IS NULL OR source_shipment_request_id IS NOT NULL",
        )
        batch.create_check_constraint(
            "ck_shipment_cargo_source_item_has_request",
            "source_request_cargo_item_id IS NULL OR source_shipment_request_id IS NOT NULL",
        )
        batch.create_check_constraint(
            "ck_shipment_cargo_weight_pair",
            "(gross_weight IS NULL AND gross_weight_uom_id IS NULL) OR "
            "(gross_weight > 0 AND gross_weight_uom_id IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_shipment_cargo_volume_pair",
            "(volume IS NULL AND volume_uom_id IS NULL) OR "
            "(volume > 0 AND volume_uom_id IS NOT NULL)",
        )

    op.create_index(
        "ix_shipment_cargo_item_source_request",
        "shipment_cargo_item",
        ["source_shipment_request_id", "operational_shipment_id"],
    )
    op.create_index(
        "ix_shipment_cargo_item_source_request_cargo",
        "shipment_cargo_item",
        ["source_request_cargo_item_id"],
    )
    op.create_index(
        "ix_shipment_cargo_item_customer_shipment",
        "shipment_cargo_item",
        ["cargo_owner_customer_id", "operational_shipment_id"],
    )


def downgrade():
    bind = op.get_bind()
    used = bind.execute(
        sa.text(
            "SELECT count(*) FROM shipment_cargo_item WHERE "
            "source_shipment_request_id IS NOT NULL OR "
            "source_request_cargo_item_id IS NOT NULL OR "
            "requested_quantity IS NOT NULL OR planned_quantity IS NOT NULL OR "
            "actual_quantity IS NOT NULL OR packaging_type_id IS NOT NULL OR "
            "gross_weight IS NOT NULL OR volume IS NOT NULL OR "
            "destination_description IS NOT NULL"
        )
    ).scalar_one()
    if used:
        raise RuntimeError(
            "Downgrade refused: Phase 3 P3-02 Cargo lineage or semantic data exists."
        )

    op.drop_index(
        "ix_shipment_cargo_item_customer_shipment", table_name="shipment_cargo_item"
    )
    op.drop_index(
        "ix_shipment_cargo_item_source_request_cargo",
        table_name="shipment_cargo_item",
    )
    op.drop_index(
        "ix_shipment_cargo_item_source_request", table_name="shipment_cargo_item"
    )

    with op.batch_alter_table("shipment_cargo_item") as batch:
        batch.drop_constraint("ck_shipment_cargo_volume_pair", type_="check")
        batch.drop_constraint("ck_shipment_cargo_weight_pair", type_="check")
        batch.drop_constraint(
            "ck_shipment_cargo_source_item_has_request", type_="check"
        )
        batch.drop_constraint("ck_shipment_cargo_requested_has_source", type_="check")
        batch.drop_constraint(
            "ck_shipment_cargo_actual_quantity_positive", type_="check"
        )
        batch.drop_constraint(
            "ck_shipment_cargo_planned_quantity_positive", type_="check"
        )
        batch.drop_constraint(
            "ck_shipment_cargo_requested_quantity_positive", type_="check"
        )
        batch.drop_constraint("fk_shipment_cargo_volume_uom", type_="foreignkey")
        batch.drop_constraint("fk_shipment_cargo_weight_uom", type_="foreignkey")
        batch.drop_constraint("fk_shipment_cargo_packaging_type", type_="foreignkey")
        batch.drop_constraint(
            "fk_shipment_cargo_source_item_request", type_="foreignkey"
        )
        batch.drop_constraint("fk_shipment_cargo_source_request", type_="foreignkey")

        for name in (
            "destination_description",
            "volume_uom_symbol_snapshot",
            "volume_uom_code_snapshot",
            "volume_uom_id",
            "volume",
            "gross_weight_uom_symbol_snapshot",
            "gross_weight_uom_code_snapshot",
            "gross_weight_uom_id",
            "gross_weight",
            "packaging_en_snapshot",
            "packaging_fa_snapshot",
            "packaging_code_snapshot",
            "packaging_type_id",
            "actual_quantity",
            "planned_quantity",
            "requested_quantity",
            "source_request_cargo_item_id",
            "source_shipment_request_id",
        ):
            batch.drop_column(name)

    with op.batch_alter_table("request_cargo_item") as batch:
        batch.drop_constraint("uq_request_cargo_item_id_request", type_="unique")
