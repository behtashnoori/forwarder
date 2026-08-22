"""Add operational LogisticsPoint provenance for global adoption materialization."""
from alembic import op
import sqlalchemy as sa

revision = "20260906_global_logistics_point_materialization"
down_revision = "20260905_global_logistics_point_adoption"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("logistics_point") as batch:
        batch.add_column(sa.Column("global_logistics_point_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("global_adoption_id", BIGINT, nullable=True))
        batch.create_foreign_key("fk_logistics_point_global_point", "global_logistics_point",
                                 ["global_logistics_point_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_logistics_point_global_adoption_org",
                                 "organization_global_logistics_point_adoption",
                                 ["global_adoption_id", "organization_id"], ["id", "organization_id"],
                                 ondelete="RESTRICT")
        batch.create_unique_constraint("uq_logistics_point_global_adoption", ["global_adoption_id"])
    op.create_index("ix_logistics_point_global_point", "logistics_point", ["global_logistics_point_id"])


def downgrade():
    count = op.get_bind().execute(sa.text(
        "SELECT count(*) FROM logistics_point WHERE global_logistics_point_id IS NOT NULL OR global_adoption_id IS NOT NULL"
    )).scalar_one()
    if count:
        raise RuntimeError("Downgrade refused: LogisticsPoint global provenance exists.")
    op.drop_index("ix_logistics_point_global_point", table_name="logistics_point")
    with op.batch_alter_table("logistics_point") as batch:
        batch.drop_constraint("uq_logistics_point_global_adoption", type_="unique")
        batch.drop_constraint("fk_logistics_point_global_adoption_org", type_="foreignkey")
        batch.drop_constraint("fk_logistics_point_global_point", type_="foreignkey")
        batch.drop_column("global_adoption_id")
        batch.drop_column("global_logistics_point_id")
