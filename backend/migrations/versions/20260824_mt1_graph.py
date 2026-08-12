"""Complete canonical ownership for CRM multi-parent and transport graphs.

Revision ID: 20260824_mt1_graph
Revises: 20260823_mt1_ownership_expand
"""
from alembic import op
import sqlalchemy as sa


revision = "20260824_mt1_graph"
down_revision = "20260823_mt1_ownership_expand"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger()
SCOPED_TABLES = (
    "activity",
    "task",
    "shipment_transport_unit",
    "shipment_transport_unit_update",
)


def _add_scope(table: str) -> None:
    op.add_column(table, sa.Column("operational_organization_id", BIGINT, nullable=True))
    op.add_column(table, sa.Column("ownership_scope", sa.String(24), nullable=True))
    op.create_index(f"ix_{table}_operational_organization_id", table, ["operational_organization_id"])
    op.create_foreign_key(
        f"fk_{table}_operational_organization_id",
        table,
        "operational_organization",
        ["operational_organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        f"ck_{table}_ownership_envelope",
        table,
        "ownership_scope IS NULL OR "
        "(ownership_scope = 'TENANT' AND operational_organization_id IS NOT NULL) OR "
        "(ownership_scope = 'LEGACY_QUARANTINED' AND operational_organization_id IS NULL)",
    )


def upgrade():
    for table in SCOPED_TABLES:
        _add_scope(table)

    op.create_unique_constraint(
        "uq_opportunity_id_operational_org", "opportunity", ["id", "operational_organization_id"]
    )
    op.create_unique_constraint(
        "uq_shipment_tracking_id_operational_org",
        "shipment_tracking",
        ["id", "operational_organization_id"],
    )
    op.create_unique_constraint(
        "uq_transport_unit_id_operational_org",
        "shipment_transport_unit",
        ["id", "operational_organization_id"],
    )

    for table in ("activity", "task"):
        for parent_column, parent_table in (
            ("customer_id", "customer"),
            ("opportunity_id", "opportunity"),
            ("shipment_request_id", "shipment_request"),
        ):
            op.create_foreign_key(
                f"fk_{table}_{parent_table}_same_org",
                table,
                parent_table,
                [parent_column, "operational_organization_id"],
                ["id", "operational_organization_id"],
            )

    op.create_foreign_key(
        "fk_transport_unit_tracking_same_org",
        "shipment_transport_unit",
        "shipment_tracking",
        ["tracking_id", "operational_organization_id"],
        ["id", "operational_organization_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_transport_unit_update_unit_same_org",
        "shipment_transport_unit_update",
        "shipment_transport_unit",
        ["unit_id", "operational_organization_id"],
        ["id", "operational_organization_id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "fk_transport_unit_update_unit_same_org", "shipment_transport_unit_update", type_="foreignkey"
    )
    op.drop_constraint("fk_transport_unit_tracking_same_org", "shipment_transport_unit", type_="foreignkey")
    for table in ("task", "activity"):
        for parent_table in ("shipment_request", "opportunity", "customer"):
            op.drop_constraint(f"fk_{table}_{parent_table}_same_org", table, type_="foreignkey")
    op.drop_constraint("uq_transport_unit_id_operational_org", "shipment_transport_unit", type_="unique")
    op.drop_constraint("uq_shipment_tracking_id_operational_org", "shipment_tracking", type_="unique")
    op.drop_constraint("uq_opportunity_id_operational_org", "opportunity", type_="unique")
    for table in reversed(SCOPED_TABLES):
        op.drop_constraint(f"ck_{table}_ownership_envelope", table, type_="check")
        op.drop_constraint(f"fk_{table}_operational_organization_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_operational_organization_id", table_name=table)
        op.drop_column(table, "ownership_scope")
        op.drop_column(table, "operational_organization_id")
