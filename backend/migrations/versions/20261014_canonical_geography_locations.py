"""Canonical Admin1/city, governed organization locations, structured delivery."""
from alembic import op
import sqlalchemy as sa


revision = "20261014_canonical_geography_locations"
down_revision = "20261013_structured_route_progress_eta"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    for name, type_ in (
        ("name_en", sa.Text()), ("geoname_id", BIGINT), ("aliases", sa.JSON()),
        ("latitude", sa.Numeric(10, 7)), ("longitude", sa.Numeric(10, 7)),
        ("timezone", sa.String(64)),
    ):
        op.add_column("province", sa.Column(name, type_, nullable=True))
    op.create_unique_constraint("uq_province_geoname_id", "province", ["geoname_id"])
    op.create_index("ix_province_geoname_id", "province", ["geoname_id"])

    for name, type_ in (
        ("name_en", sa.Text()), ("geoname_id", BIGINT), ("country_id", BIGINT),
        ("feature_code", sa.String(16)), ("aliases", sa.JSON()),
        ("latitude", sa.Numeric(10, 7)), ("longitude", sa.Numeric(10, 7)),
        ("population", sa.BigInteger()), ("timezone", sa.String(64)),
    ):
        op.add_column("city", sa.Column(name, type_, nullable=True))
    with op.batch_alter_table("city") as batch:
        batch.alter_column("county_id", existing_type=BIGINT, nullable=True)
        batch.create_foreign_key("fk_city_country", "country", ["country_id"], ["id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_city_geoname_id", ["geoname_id"])
        batch.create_index("ix_city_geoname_id", ["geoname_id"])
        batch.create_index("ix_city_country_id", ["country_id"])

    with op.batch_alter_table("logistics_point") as batch:
        batch.alter_column("logistics_point_type_id", existing_type=BIGINT, nullable=True)
        batch.add_column(sa.Column("latitude", sa.Numeric(10, 7), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Numeric(10, 7), nullable=True))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("governance_state", sa.String(32), nullable=False, server_default="APPROVED"))
        batch.add_column(sa.Column("duplicate_of_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("reviewed_by", BIGINT, nullable=True))
        batch.create_foreign_key("fk_logistics_point_duplicate", "logistics_point", ["duplicate_of_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_logistics_point_reviewer", "expert_user", ["reviewed_by"], ["id"], ondelete="RESTRICT")
        batch.create_check_constraint("ck_logistics_point_governance", "governance_state IN ('PENDING_REVIEW','APPROVED','POTENTIAL_DUPLICATE','DEACTIVATED')")

    with op.batch_alter_table("cargo_delivery") as batch:
        batch.alter_column("destination_text", existing_type=sa.String(255), nullable=True)
        batch.add_column(sa.Column("destination_location_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("destination_logistics_point_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("destination_snapshot", sa.JSON(), nullable=True))
        batch.create_foreign_key("fk_delivery_destination_location", "canonical_location", ["destination_location_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_delivery_destination_point_org", "logistics_point", ["destination_logistics_point_id", "organization_id"], ["id", "organization_id"], ondelete="RESTRICT")
        batch.create_check_constraint(
            "ck_delivery_destination_identity",
            "destination_text IS NOT NULL OR (destination_location_id IS NOT NULL AND destination_snapshot IS NOT NULL)",
        )


def downgrade():
    bind = op.get_bind()
    checks = (
        ("city", "geoname_id IS NOT NULL"),
        ("logistics_point", "governance_state <> 'APPROVED' OR logistics_point_type_id IS NULL"),
        ("cargo_delivery", "destination_location_id IS NOT NULL OR destination_logistics_point_id IS NOT NULL"),
    )
    for table, predicate in checks:
        if bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE {predicate} LIMIT 1")).first():
            raise RuntimeError("Canonical geography/location history exists; downgrade would erase evidence")
    with op.batch_alter_table("cargo_delivery") as batch:
        batch.drop_constraint("ck_delivery_destination_identity", type_="check")
        batch.drop_constraint("fk_delivery_destination_point_org", type_="foreignkey")
        batch.drop_constraint("fk_delivery_destination_location", type_="foreignkey")
        batch.drop_column("destination_snapshot")
        batch.drop_column("destination_logistics_point_id")
        batch.drop_column("destination_location_id")
        batch.alter_column("destination_text", existing_type=sa.String(255), nullable=False)
    with op.batch_alter_table("logistics_point") as batch:
        batch.drop_constraint("ck_logistics_point_governance", type_="check")
        batch.drop_constraint("fk_logistics_point_reviewer", type_="foreignkey")
        batch.drop_constraint("fk_logistics_point_duplicate", type_="foreignkey")
        for name in ("reviewed_by", "reviewed_at", "duplicate_of_id", "governance_state", "description", "longitude", "latitude"):
            batch.drop_column(name)
        batch.alter_column("logistics_point_type_id", existing_type=BIGINT, nullable=False)
    with op.batch_alter_table("city") as batch:
        batch.drop_index("ix_city_country_id")
        batch.drop_index("ix_city_geoname_id")
        batch.drop_constraint("uq_city_geoname_id", type_="unique")
        batch.drop_constraint("fk_city_country", type_="foreignkey")
        for name in ("timezone", "population", "longitude", "latitude", "aliases", "feature_code", "country_id", "geoname_id", "name_en"):
            batch.drop_column(name)
        batch.alter_column("county_id", existing_type=BIGINT, nullable=False)
    op.drop_index("ix_province_geoname_id", table_name="province")
    op.drop_constraint("uq_province_geoname_id", "province", type_="unique")
    for name in ("timezone", "longitude", "latitude", "aliases", "geoname_id", "name_en"):
        op.drop_column("province", name)
