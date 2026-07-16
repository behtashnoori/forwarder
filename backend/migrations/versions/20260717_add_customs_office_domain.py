"""Add canonical customs office domain.

Revision ID: 20260717_add_customs_office_domain
Revises: 20260716_drop_invalid_shipment_update_trigger
"""
from alembic import op
import sqlalchemy as sa

revision = "20260717_add_customs_office_domain"
down_revision = "20260716_drop_invalid_shipment_update_trigger"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "customs_office",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_fa", sa.String(160), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=True),
        sa.Column("customs_type", sa.String(32), nullable=False),
        sa.Column("country_id", BIGINT, nullable=False),
        sa.Column("province_id", BIGINT, nullable=True),
        sa.Column("county_id", BIGINT, nullable=True),
        sa.Column("city_id", BIGINT, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("customs_type IN ('seaport','road_border','rail','airport','inland','free_zone','special_economic_zone','other')", name="ck_customs_office_type"),
        sa.ForeignKeyConstraint(["country_id"], ["country.id"], name="fk_customs_office_country", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["province_id"], ["province.id"], name="fk_customs_office_province", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["county_id"], ["county.id"], name="fk_customs_office_county", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["city_id"], ["city.id"], name="fk_customs_office_city", ondelete="RESTRICT"),
        sa.UniqueConstraint("code", name="uq_customs_office_code"),
    )
    for column in ("country_id", "province_id", "county_id", "city_id", "is_active"):
        op.create_index(f"ix_customs_office_{column}", "customs_office", [column])
    op.create_table(
        "port_customs_office",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("port_id", BIGINT, nullable=False),
        sa.Column("customs_office_id", BIGINT, nullable=False),
        sa.Column("relationship_type", sa.String(32), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("relationship_type IN ('located_at','serves_port','associated','other')", name="ck_port_customs_relationship_type"),
        sa.ForeignKeyConstraint(["port_id"], ["iran_port.id"], name="fk_port_customs_port", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customs_office_id"], ["customs_office.id"], name="fk_port_customs_customs_office", ondelete="CASCADE"),
        sa.UniqueConstraint("port_id", "customs_office_id", "relationship_type", name="uq_port_customs_relationship"),
    )
    op.create_index("ix_port_customs_port_id", "port_customs_office", ["port_id"])
    op.create_index("ix_port_customs_customs_office_id", "port_customs_office", ["customs_office_id"])


def downgrade() -> None:
    op.drop_index("ix_port_customs_customs_office_id", table_name="port_customs_office")
    op.drop_index("ix_port_customs_port_id", table_name="port_customs_office")
    op.drop_table("port_customs_office")
    for column in reversed(("country_id", "province_id", "county_id", "city_id", "is_active")):
        op.drop_index(f"ix_customs_office_{column}", table_name="customs_office")
    op.drop_table("customs_office")
