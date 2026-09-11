"""Evolve execution units into tenant-owned shared transport executions.

Additive compatibility migration: legacy project/shipment ownership and legacy
ShipmentTransportUnit allocations remain untouched.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260917_shared_transport_execution"
down_revision = "20260916_personal_dashboard_permissions"
branch_labels = None
depends_on = None


def upgrade():
    # Backfill is deterministic: every pre-existing unit is project-owned.
    op.add_column("execution_unit", sa.Column("organization_id", sa.BigInteger(), nullable=True))
    op.execute(
        "UPDATE execution_unit eu SET organization_id = p.organization_id "
        "FROM project p WHERE eu.project_id = p.id AND eu.organization_id IS NULL"
    )
    op.alter_column("execution_unit", "organization_id", nullable=False)
    op.create_foreign_key("fk_execution_unit_organization", "execution_unit", "operational_organization", ["organization_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_execution_unit_org_status_active", "execution_unit", ["organization_id", "lifecycle_status", "is_active"])
    op.drop_constraint("uq_execution_unit_project_code", "execution_unit", type_="unique")
    op.create_unique_constraint("uq_execution_unit_org_code", "execution_unit", ["organization_id", "unit_code"])
    op.alter_column("execution_unit", "project_id", existing_type=sa.BigInteger(), nullable=True)
    op.alter_column("operational_event", "project_id", existing_type=sa.BigInteger(), nullable=True)

    # Reuse the canonical tenant-scoped CRM party/customer master for the
    # execution carrier.  NULL preserves historical executions without
    # inventing a carrier identity.
    op.add_column("execution_unit", sa.Column("carrier_customer_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_execution_unit_carrier_customer", "execution_unit", "customer", ["carrier_customer_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_execution_unit_carrier_customer", "execution_unit", ["carrier_customer_id"])

    op.add_column("shipment_cargo_item", sa.Column("cargo_owner_customer_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_shipment_cargo_item_owner_customer", "shipment_cargo_item", "customer", ["cargo_owner_customer_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_shipment_cargo_item_owner_customer", "shipment_cargo_item", ["cargo_owner_customer_id"])

    op.create_table(
        "execution_unit_cargo_allocation",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("execution_unit_id", sa.BigInteger(), nullable=False),
        sa.Column("shipment_cargo_item_id", sa.BigInteger(), nullable=False),
        sa.Column("operational_shipment_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("allocated_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["execution_unit_id"], ["execution_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_cargo_item_id"], ["shipment_cargo_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operational_shipment_id"], ["operational_shipment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("shipment_cargo_item_id", "execution_unit_id", name="uq_execution_unit_cargo_allocation_pair"),
        sa.CheckConstraint("allocated_quantity > 0", name="ck_execution_unit_cargo_allocation_positive"),
    )
    op.create_index("ix_execution_unit_cargo_allocation_execution", "execution_unit_cargo_allocation", ["execution_unit_id"])
    op.create_index("ix_execution_unit_cargo_allocation_shipment", "execution_unit_cargo_allocation", ["operational_shipment_id"])
    op.create_index("ix_execution_unit_cargo_allocation_project", "execution_unit_cargo_allocation", ["project_id"])


def downgrade():
    op.drop_index("ix_execution_unit_carrier_customer", table_name="execution_unit")
    op.drop_constraint("fk_execution_unit_carrier_customer", "execution_unit", type_="foreignkey")
    op.drop_column("execution_unit", "carrier_customer_id")
    op.drop_index("ix_execution_unit_cargo_allocation_project", table_name="execution_unit_cargo_allocation")
    op.drop_index("ix_execution_unit_cargo_allocation_shipment", table_name="execution_unit_cargo_allocation")
    op.drop_index("ix_execution_unit_cargo_allocation_execution", table_name="execution_unit_cargo_allocation")
    op.drop_table("execution_unit_cargo_allocation")
    op.drop_index("ix_shipment_cargo_item_owner_customer", table_name="shipment_cargo_item")
    op.drop_constraint("fk_shipment_cargo_item_owner_customer", "shipment_cargo_item", type_="foreignkey")
    op.drop_column("shipment_cargo_item", "cargo_owner_customer_id")
    op.alter_column("operational_event", "project_id", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("execution_unit", "project_id", existing_type=sa.BigInteger(), nullable=False)
    op.drop_constraint("uq_execution_unit_org_code", "execution_unit", type_="unique")
    op.create_unique_constraint("uq_execution_unit_project_code", "execution_unit", ["project_id", "unit_code"])
    op.drop_index("ix_execution_unit_org_status_active", table_name="execution_unit")
    op.drop_constraint("fk_execution_unit_organization", "execution_unit", type_="foreignkey")
    op.drop_column("execution_unit", "organization_id")
