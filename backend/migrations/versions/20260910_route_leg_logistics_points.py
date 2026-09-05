"""Add optional organization facility identities to route legs."""
from alembic import op
import sqlalchemy as sa

revision = "20260910_route_leg_logistics_points"
down_revision = "20260909_cargo_transport_allocation"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("route_leg") as batch:
        batch.add_column(sa.Column("origin_logistics_point_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("destination_logistics_point_id", sa.BigInteger(), nullable=True))
        batch.create_foreign_key("fk_route_leg_origin_logistics_point", "logistics_point", ["origin_logistics_point_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_route_leg_destination_logistics_point", "logistics_point", ["destination_logistics_point_id"], ["id"], ondelete="RESTRICT")
        batch.drop_constraint("ck_route_leg_distinct_locations", type_="check")
        batch.create_check_constraint("ck_route_leg_distinct_locations", "origin_location_id <> destination_location_id OR COALESCE(origin_logistics_point_id, 0) <> COALESCE(destination_logistics_point_id, 0)")
    op.create_index("ix_route_leg_origin_logistics_point", "route_leg", ["origin_logistics_point_id"])
    op.create_index("ix_route_leg_destination_logistics_point", "route_leg", ["destination_logistics_point_id"])


def downgrade():
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM route_leg WHERE origin_logistics_point_id IS NOT NULL OR destination_logistics_point_id IS NOT NULL")).scalar_one()
    if count:
        raise RuntimeError("Downgrade refused: route legs reference logistics points.")
    op.drop_index("ix_route_leg_origin_logistics_point", table_name="route_leg")
    op.drop_index("ix_route_leg_destination_logistics_point", table_name="route_leg")
    with op.batch_alter_table("route_leg") as batch:
        batch.drop_constraint("ck_route_leg_distinct_locations", type_="check")
        batch.create_check_constraint("ck_route_leg_distinct_locations", "origin_location_id <> destination_location_id")
        batch.drop_constraint("fk_route_leg_destination_logistics_point", type_="foreignkey")
        batch.drop_constraint("fk_route_leg_origin_logistics_point", type_="foreignkey")
        batch.drop_column("destination_logistics_point_id")
        batch.drop_column("origin_logistics_point_id")
