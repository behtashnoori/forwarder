"""Add ADR-043 direct-shipment primary responsibility evidence."""
from alembic import op
import sqlalchemy as sa

revision = "20260907_direct_shipment_responsibility"
down_revision = "20260906_global_logistics_point_materialization"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("operational_shipment") as batch:
        batch.add_column(sa.Column("primary_responsible_expert_id", BIGINT, nullable=True))
        batch.create_foreign_key("fk_operational_shipment_primary_responsible", "expert_user", ["primary_responsible_expert_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_operational_shipment_primary_responsible", "operational_shipment", ["primary_responsible_expert_id"])


def downgrade():
    bound = op.get_bind()
    count = bound.execute(sa.text("SELECT count(*) FROM operational_shipment WHERE primary_responsible_expert_id IS NOT NULL")).scalar_one()
    if count:
        raise RuntimeError("Downgrade refused: direct shipment responsibility evidence exists.")
    op.drop_index("ix_operational_shipment_primary_responsible", table_name="operational_shipment")
    with op.batch_alter_table("operational_shipment") as batch:
        batch.drop_constraint("fk_operational_shipment_primary_responsible", type_="foreignkey")
        batch.drop_column("primary_responsible_expert_id")
