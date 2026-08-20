"""Converge expert tracking location writes on LogisticsPoint.

Revision ID: 20260830_logistics_point_tracking_convergence
Revises: 20260829_cargo_traceability_index
"""

from alembic import op
import sqlalchemy as sa


revision = "20260830_logistics_point_tracking_convergence"
down_revision = "20260829_cargo_traceability_index"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("shipment_transport_unit_update") as batch:
        batch.add_column(sa.Column("logistics_point_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("location_name_en_snapshot", sa.String(160), nullable=True))
        batch.add_column(sa.Column("location_type_code_snapshot", sa.String(64), nullable=True))
        batch.add_column(sa.Column("location_city_name_snapshot", sa.String(160), nullable=True))
        batch.create_foreign_key(
            "fk_tracking_update_logistics_point_org",
            "logistics_point",
            ["logistics_point_id", "operational_organization_id"],
            ["id", "organization_id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_shipment_transport_unit_update_logistics_point_id",
        "shipment_transport_unit_update",
        ["logistics_point_id"],
    )


def downgrade():
    connection = op.get_bind()
    linked = connection.execute(
        sa.text(
            "SELECT 1 FROM shipment_transport_unit_update "
            "WHERE logistics_point_id IS NOT NULL LIMIT 1"
        )
    ).first()
    if linked:
        raise RuntimeError(
            "Downgrade prohibited while canonical LogisticsPoint-linked tracking data exists"
        )
    op.drop_index(
        "ix_shipment_transport_unit_update_logistics_point_id",
        table_name="shipment_transport_unit_update",
    )
    with op.batch_alter_table("shipment_transport_unit_update") as batch:
        batch.drop_constraint("fk_tracking_update_logistics_point_org", type_="foreignkey")
        batch.drop_column("location_city_name_snapshot")
        batch.drop_column("location_type_code_snapshot")
        batch.drop_column("location_name_en_snapshot")
        batch.drop_column("logistics_point_id")
