"""Expand reference-data identity, lifecycle and provenance schema.

Revision ID: 20260720_expand_reference_data_identity
Revises: 20260719_add_auth_sessions
"""
from alembic import op
import sqlalchemy as sa

revision = "20260720_expand_reference_data_identity"
down_revision = "20260719_add_auth_sessions"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

PROVENANCE = (
    ("source_organization", sa.String(160)),
    ("source_reference", sa.String(255)),
    ("source_version", sa.String(100)),
    ("dataset_id", sa.String(100)),
)


def _add_lifecycle(table: str, *, add_active: bool = True, add_updated: bool = False) -> None:
    if add_active:
        op.add_column(table, sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column(table, sa.Column("effective_from", sa.Date(), nullable=True))
    op.add_column(table, sa.Column("effective_to", sa.Date(), nullable=True))
    for name, type_ in PROVENANCE:
        op.add_column(table, sa.Column(name, type_, nullable=True))
    if add_updated:
        op.add_column(table, sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))


def _drop_lifecycle(table: str, *, drop_active: bool = True, drop_updated: bool = False) -> None:
    if drop_updated:
        op.drop_column(table, "updated_at")
    for name, _ in reversed(PROVENANCE):
        op.drop_column(table, name)
    op.drop_column(table, "effective_to")
    op.drop_column(table, "effective_from")
    if drop_active:
        op.drop_column(table, "is_active")


def _assert_no_duplicate_coverage() -> None:
    duplicate = op.get_bind().execute(sa.text(
        "SELECT 1 FROM port_province_mapping GROUP BY port_id, province_id HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicate is not None:
        raise RuntimeError("duplicate port/province coverage blocks reference schema expansion")


def upgrade() -> None:
    _assert_no_duplicate_coverage()
    _add_lifecycle("country", add_active=False)
    with op.batch_alter_table("country", recreate="auto") as batch:
        batch.create_check_constraint("ck_country_effective_range", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from")

    with op.batch_alter_table("province", recreate="auto") as batch:
        batch.add_column(sa.Column("country_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("effective_from", sa.Date(), nullable=True))
        batch.add_column(sa.Column("effective_to", sa.Date(), nullable=True))
        for name, type_ in PROVENANCE:
            batch.add_column(sa.Column(name, type_, nullable=True))
        batch.create_foreign_key("fk_province_country", "country", ["country_id"], ["id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_province_country_code", ["country_id", "code"])
        batch.create_check_constraint("ck_province_effective_range", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from")
    op.create_index("ix_province_country_id", "province", ["country_id"])
    op.create_index("ix_province_code", "province", ["code"])

    for table, parent, unique_name, check_name in (
        ("county", "province_id", "uq_county_province_code", "ck_county_effective_range"),
        ("city", "county_id", "uq_city_county_code", "ck_city_effective_range"),
    ):
        with op.batch_alter_table(table, recreate="auto") as batch:
            batch.add_column(sa.Column("code", sa.String(64), nullable=True))
            batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
            batch.add_column(sa.Column("effective_from", sa.Date(), nullable=True))
            batch.add_column(sa.Column("effective_to", sa.Date(), nullable=True))
            for name, type_ in PROVENANCE:
                batch.add_column(sa.Column(name, type_, nullable=True))
            batch.create_unique_constraint(unique_name, [parent, "code"])
            batch.create_check_constraint(check_name, "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from")
        op.create_index(f"ix_{table}_code", table, ["code"])

    with op.batch_alter_table("iran_port", recreate="auto") as batch:
        batch.add_column(sa.Column("code", sa.String(64), nullable=True))
        batch.add_column(sa.Column("country_id", BIGINT, nullable=True))
        batch.add_column(sa.Column("effective_from", sa.Date(), nullable=True))
        batch.add_column(sa.Column("effective_to", sa.Date(), nullable=True))
        for name, type_ in PROVENANCE:
            batch.add_column(sa.Column(name, type_, nullable=True))
        batch.create_foreign_key("fk_iran_port_country", "country", ["country_id"], ["id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_iran_port_country_code", ["country_id", "code"])
        batch.create_check_constraint("ck_iran_port_effective_range", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from")
    op.create_index("ix_iran_port_code", "iran_port", ["code"])
    op.create_index("ix_iran_port_country_id", "iran_port", ["country_id"])

    _add_lifecycle("port_province_mapping", add_active=True, add_updated=True)
    op.add_column("port_province_mapping", sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("port_province_mapping", recreate="auto") as batch:
        batch.create_unique_constraint("uq_port_province_mapping", ["port_id", "province_id"])
        batch.create_check_constraint("ck_port_province_mapping_effective_range", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from")

    for table, add_updated, check_name in (
        ("customs_office", False, "ck_customs_office_effective_range"),
        ("port_customs_office", True, "ck_port_customs_effective_range"),
    ):
        _add_lifecycle(table, add_active=False, add_updated=add_updated)
        with op.batch_alter_table(table, recreate="auto") as batch:
            batch.create_check_constraint(check_name, "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from")

    op.create_table(
        "port_location",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("port_id", BIGINT, nullable=False),
        sa.Column("country_id", BIGINT, nullable=True),
        sa.Column("province_id", BIGINT, nullable=True),
        sa.Column("county_id", BIGINT, nullable=True),
        sa.Column("city_id", BIGINT, nullable=True),
        sa.Column("location_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.Date(), nullable=True), sa.Column("effective_to", sa.Date(), nullable=True),
        *(sa.Column(name, type_, nullable=True) for name, type_ in PROVENANCE),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("location_status IN ('confirmed','provisional','historical','unknown')", name="ck_port_location_status"),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_port_location_effective_range"),
        sa.ForeignKeyConstraint(["port_id"], ["iran_port.id"], name="fk_port_location_port", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["country_id"], ["country.id"], name="fk_port_location_country", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["province_id"], ["province.id"], name="fk_port_location_province", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["county_id"], ["county.id"], name="fk_port_location_county", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["city_id"], ["city.id"], name="fk_port_location_city", ondelete="RESTRICT"),
    )
    for column in ("port_id", "country_id", "province_id", "county_id", "city_id"):
        op.create_index(f"ix_port_location_{column}", "port_location", [column])
    op.create_index("uq_port_location_active_port", "port_location", ["port_id"], unique=True,
                    postgresql_where=sa.text("is_active IS TRUE"), sqlite_where=sa.text("is_active = 1"))

    op.create_table(
        "customs_province_mapping",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("customs_office_id", BIGINT, nullable=False), sa.Column("province_id", BIGINT, nullable=False),
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.Date(), nullable=True), sa.Column("effective_to", sa.Date(), nullable=True),
        *(sa.Column(name, type_, nullable=True) for name, type_ in PROVENANCE),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_customs_province_mapping_effective_range"),
        sa.ForeignKeyConstraint(["customs_office_id"], ["customs_office.id"], name="fk_customs_province_mapping_customs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["province_id"], ["province.id"], name="fk_customs_province_mapping_province", ondelete="RESTRICT"),
        sa.UniqueConstraint("customs_office_id", "province_id", name="uq_customs_province_mapping"),
    )
    op.create_index("ix_customs_province_mapping_customs_office_id", "customs_province_mapping", ["customs_office_id"])
    op.create_index("ix_customs_province_mapping_province_id", "customs_province_mapping", ["province_id"])


def downgrade() -> None:
    op.drop_table("customs_province_mapping")
    op.drop_table("port_location")
    for table, drop_updated, check_name in (("port_customs_office", True, "ck_port_customs_effective_range"), ("customs_office", False, "ck_customs_office_effective_range")):
        with op.batch_alter_table(table, recreate="auto") as batch:
            batch.drop_constraint(check_name, type_="check")
        _drop_lifecycle(table, drop_active=False, drop_updated=drop_updated)
    with op.batch_alter_table("port_province_mapping", recreate="auto") as batch:
        batch.drop_constraint("ck_port_province_mapping_effective_range", type_="check")
        batch.drop_constraint("uq_port_province_mapping", type_="unique")
    op.drop_column("port_province_mapping", "is_preferred")
    _drop_lifecycle("port_province_mapping", drop_active=True, drop_updated=True)
    op.drop_index("ix_iran_port_country_id", table_name="iran_port"); op.drop_index("ix_iran_port_code", table_name="iran_port")
    with op.batch_alter_table("iran_port", recreate="auto") as batch:
        batch.drop_constraint("ck_iran_port_effective_range", type_="check"); batch.drop_constraint("uq_iran_port_country_code", type_="unique"); batch.drop_constraint("fk_iran_port_country", type_="foreignkey")
        for name, _ in reversed(PROVENANCE): batch.drop_column(name)
        batch.drop_column("effective_to"); batch.drop_column("effective_from"); batch.drop_column("country_id"); batch.drop_column("code")
    for table, check_name, unique_name in (("city", "ck_city_effective_range", "uq_city_county_code"), ("county", "ck_county_effective_range", "uq_county_province_code")):
        op.drop_index(f"ix_{table}_code", table_name=table)
        with op.batch_alter_table(table, recreate="auto") as batch:
            batch.drop_constraint(check_name, type_="check"); batch.drop_constraint(unique_name, type_="unique")
            for name, _ in reversed(PROVENANCE): batch.drop_column(name)
            batch.drop_column("effective_to"); batch.drop_column("effective_from"); batch.drop_column("is_active"); batch.drop_column("code")
    op.drop_index("ix_province_code", table_name="province"); op.drop_index("ix_province_country_id", table_name="province")
    with op.batch_alter_table("province", recreate="auto") as batch:
        batch.drop_constraint("ck_province_effective_range", type_="check"); batch.drop_constraint("uq_province_country_code", type_="unique"); batch.drop_constraint("fk_province_country", type_="foreignkey")
        for name, _ in reversed(PROVENANCE): batch.drop_column(name)
        batch.drop_column("effective_to"); batch.drop_column("effective_from"); batch.drop_column("is_active"); batch.drop_column("country_id")
    with op.batch_alter_table("country", recreate="auto") as batch:
        batch.drop_constraint("ck_country_effective_range", type_="check")
    _drop_lifecycle("country", drop_active=False)
