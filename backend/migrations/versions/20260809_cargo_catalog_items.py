"""Add cargo catalog, aliases, and shipment cargo snapshots.

Revision ID: 20260809_cargo_catalog_items
Revises: 20260808_reference_seed
"""

from alembic import op
import sqlalchemy as sa

revision = "20260809_cargo_catalog_items"
down_revision = "20260808_reference_seed"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def audit_columns():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", BIGINT, nullable=False),
        sa.Column("updated_by", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["expert_user.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["expert_user.id"], ondelete="RESTRICT"
        ),
    )


def upgrade():
    op.create_table(
        "cargo_catalog_item",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("immutable_code", sa.String(64), nullable=False),
        sa.Column("fa_name", sa.String(160), nullable=False),
        sa.Column("en_name", sa.String(160)),
        sa.Column("cargo_type_id", BIGINT, nullable=False),
        sa.Column("default_uom_id", BIGINT),
        sa.Column("description", sa.Text()),
        sa.Column("part_number", sa.String(120)),
        sa.Column("customer_item_code", sa.String(120)),
        sa.Column("hs_code", sa.String(32)),
        sa.Column("brand", sa.String(120)),
        sa.Column("model", sa.String(120)),
        sa.Column("search_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        *audit_columns(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["cargo_type_id"], ["cargo_type.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["default_uom_id"], ["unit_of_measure.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("public_id", name="uq_cargo_catalog_item_public_id"),
        sa.UniqueConstraint(
            "organization_id", "immutable_code", name="uq_cargo_catalog_item_org_code"
        ),
        sa.UniqueConstraint(
            "id", "organization_id", name="uq_cargo_catalog_item_id_org"
        ),
        sa.CheckConstraint(
            "version >= 1", name="ck_cargo_catalog_item_version_positive"
        ),
    )
    op.create_index(
        "ix_cargo_catalog_item_org_active",
        "cargo_catalog_item",
        ["organization_id", "is_active"],
    )
    op.create_index(
        "ix_cargo_catalog_item_org_cargo_type",
        "cargo_catalog_item",
        ["organization_id", "cargo_type_id"],
    )
    op.create_index(
        "ix_cargo_catalog_item_org_fa_name",
        "cargo_catalog_item",
        ["organization_id", "fa_name"],
    )
    op.create_index(
        "ix_cargo_catalog_item_org_part_number",
        "cargo_catalog_item",
        ["organization_id", "part_number"],
    )
    op.create_table(
        "cargo_item_alias",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("catalog_item_id", BIGINT, nullable=False),
        sa.Column("alias_text", sa.String(200), nullable=False),
        sa.Column("normalized_alias", sa.String(200), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("alias_type", sa.String(24), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *audit_columns(),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["cargo_catalog_item.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("public_id", name="uq_cargo_item_alias_public_id"),
        sa.UniqueConstraint(
            "catalog_item_id",
            "normalized_alias",
            name="uq_cargo_item_alias_item_normalized",
        ),
        sa.CheckConstraint(
            "language IN ('fa','en','und')", name="ck_cargo_item_alias_language"
        ),
        sa.CheckConstraint(
            "alias_type IN ('COMMON_NAME','CUSTOMER_TERM','ABBREVIATION','LEGACY_TERM','OTHER_GOVERNED')",
            name="ck_cargo_item_alias_type",
        ),
    )
    op.create_index(
        "ix_cargo_item_alias_item_active",
        "cargo_item_alias",
        ["catalog_item_id", "is_active"],
    )
    op.create_table(
        "shipment_cargo_item",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("catalog_item_id", BIGINT),
        sa.Column("cargo_type_id", BIGINT, nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("uom_id", BIGINT, nullable=False),
        sa.Column("display_name_snapshot", sa.String(200), nullable=False),
        sa.Column("cargo_type_code_snapshot", sa.String(64), nullable=False),
        sa.Column("cargo_type_fa_snapshot", sa.String(160), nullable=False),
        sa.Column("cargo_type_en_snapshot", sa.String(160), nullable=False),
        sa.Column("uom_code_snapshot", sa.String(64), nullable=False),
        sa.Column("uom_symbol_snapshot", sa.String(32), nullable=False),
        sa.Column("part_number_snapshot", sa.String(120)),
        sa.Column("customer_item_code_snapshot", sa.String(120)),
        sa.Column("hs_code_snapshot", sa.String(32)),
        sa.Column("brand_snapshot", sa.String(120)),
        sa.Column("model_snapshot", sa.String(120)),
        sa.Column("description_snapshot", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        *audit_columns(),
        sa.ForeignKeyConstraint(
            ["operational_shipment_id"],
            ["operational_shipment.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["cargo_catalog_item.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["cargo_type_id"], ["cargo_type.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["uom_id"], ["unit_of_measure.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("public_id", name="uq_shipment_cargo_item_public_id"),
        sa.UniqueConstraint(
            "operational_shipment_id",
            "line_number",
            name="uq_shipment_cargo_item_shipment_line",
        ),
        sa.CheckConstraint(
            "line_number >= 1", name="ck_shipment_cargo_item_line_positive"
        ),
        sa.CheckConstraint(
            "quantity > 0", name="ck_shipment_cargo_item_quantity_positive"
        ),
        sa.CheckConstraint(
            "version >= 1", name="ck_shipment_cargo_item_version_positive"
        ),
    )
    op.create_index(
        "ix_shipment_cargo_item_shipment",
        "shipment_cargo_item",
        ["operational_shipment_id", "line_number"],
    )


def downgrade():
    op.drop_index("ix_shipment_cargo_item_shipment", table_name="shipment_cargo_item")
    op.drop_table("shipment_cargo_item")
    op.drop_index("ix_cargo_item_alias_item_active", table_name="cargo_item_alias")
    op.drop_table("cargo_item_alias")
    op.drop_index(
        "ix_cargo_catalog_item_org_part_number", table_name="cargo_catalog_item"
    )
    op.drop_index("ix_cargo_catalog_item_org_fa_name", table_name="cargo_catalog_item")
    op.drop_index(
        "ix_cargo_catalog_item_org_cargo_type", table_name="cargo_catalog_item"
    )
    op.drop_index("ix_cargo_catalog_item_org_active", table_name="cargo_catalog_item")
    op.drop_table("cargo_catalog_item")
