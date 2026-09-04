"""Governed quantity-aware cargo to transport allocation."""
from alembic import op
import sqlalchemy as sa

revision = "20260909_cargo_transport_allocation"
down_revision = "20260908_governed_international_geography"
branch_labels = None
depends_on = None

def upgrade():
    # Tracking is operationally rooted.  Request linkage remains optional for
    # public/request compatibility, while direct operations have no request.
    op.alter_column("shipment_tracking", "shipment_request_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column("shipment_tracking", sa.Column("operational_shipment_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_shipment_tracking_operational_shipment", "shipment_tracking", "operational_shipment", ["operational_shipment_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_shipment_tracking_operational_shipment", "shipment_tracking", ["operational_shipment_id"])
    op.create_index("ix_shipment_tracking_operational_shipment_id", "shipment_tracking", ["operational_shipment_id"])
    # Existing request-derived roots retain their identity and are linked to
    # their materialized operational shipment before unit convergence.
    op.execute("""UPDATE shipment_tracking st SET operational_shipment_id = os.id
                  FROM operational_shipment os
                  WHERE os.shipment_request_id = st.shipment_request_id""")
    op.alter_column("shipment_transport_unit", "tracking_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column("shipment_transport_unit", sa.Column("operational_shipment_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_transport_unit_operational_shipment", "shipment_transport_unit", "operational_shipment", ["operational_shipment_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_shipment_transport_unit_operational_shipment_id", "shipment_transport_unit", ["operational_shipment_id"])
    op.execute("""UPDATE shipment_transport_unit stu SET operational_shipment_id = st.operational_shipment_id
                  FROM shipment_tracking st
                  WHERE stu.tracking_id = st.id AND stu.operational_shipment_id IS NULL""")
    op.create_table("shipment_cargo_transport_allocation",
        sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("operational_shipment_id", sa.BigInteger(), nullable=False), sa.Column("shipment_cargo_item_id", sa.BigInteger(), nullable=False), sa.Column("transport_unit_id", sa.BigInteger(), nullable=False),
        sa.Column("allocated_quantity", sa.Numeric(18,6), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_by", sa.BigInteger(), nullable=False), sa.Column("updated_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["operational_shipment_id"],["operational_shipment.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["shipment_cargo_item_id"],["shipment_cargo_item.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["transport_unit_id"],["shipment_transport_unit.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["created_by"],["expert_user.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["updated_by"],["expert_user.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("shipment_cargo_item_id","transport_unit_id", name="uq_cargo_transport_allocation_pair"), sa.CheckConstraint("allocated_quantity > 0", name="ck_cargo_transport_allocation_positive"))
    op.create_index("ix_cargo_transport_allocation_shipment", "shipment_cargo_transport_allocation", ["operational_shipment_id"])
    op.create_index("ix_cargo_transport_allocation_unit", "shipment_cargo_transport_allocation", ["transport_unit_id"])

def downgrade():
    op.drop_table("shipment_cargo_transport_allocation")
    op.drop_index("ix_shipment_transport_unit_operational_shipment_id", table_name="shipment_transport_unit")
    op.drop_constraint("fk_transport_unit_operational_shipment", "shipment_transport_unit", type_="foreignkey")
    op.drop_column("shipment_transport_unit", "operational_shipment_id")
    op.alter_column("shipment_transport_unit", "tracking_id", existing_type=sa.BigInteger(), nullable=False)
    op.drop_index("ix_shipment_tracking_operational_shipment_id", table_name="shipment_tracking")
    op.drop_constraint("uq_shipment_tracking_operational_shipment", "shipment_tracking", type_="unique")
    op.drop_constraint("fk_shipment_tracking_operational_shipment", "shipment_tracking", type_="foreignkey")
    op.drop_column("shipment_tracking", "operational_shipment_id")
    op.alter_column("shipment_tracking", "shipment_request_id", existing_type=sa.BigInteger(), nullable=False)
