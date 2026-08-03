"""Add governed logistics network foundation.

Revision ID: 20260810_logistics_network
Revises: 20260809_cargo_catalog_items
"""
from alembic import op
import sqlalchemy as sa

revision = "20260810_logistics_network"
down_revision = "20260809_cargo_catalog_items"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def audit_columns():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", BIGINT, nullable=False),
        sa.Column("updated_by", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["expert_user.id"], ondelete="RESTRICT"),
    )


def upgrade():
    op.create_table("logistics_point_type",
        sa.Column("id", BIGINT, primary_key=True), sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("immutable_code", sa.String(64), nullable=False), sa.Column("fa_name", sa.String(160), nullable=False),
        sa.Column("en_name", sa.String(160), nullable=False), sa.Column("definition", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"), *audit_columns(),
        sa.UniqueConstraint("public_id", name="uq_logistics_point_type_public_id"),
        sa.UniqueConstraint("immutable_code", name="uq_logistics_point_type_code"),
        sa.CheckConstraint("version >= 1", name="ck_logistics_point_type_version_positive"))
    op.create_index("ix_logistics_point_type_active_order", "logistics_point_type", ["is_active", "display_order"])
    op.create_table("logistics_point",
        sa.Column("id", BIGINT, primary_key=True), sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False), sa.Column("immutable_code", sa.String(64), nullable=False),
        sa.Column("logistics_point_type_id", BIGINT, nullable=False), sa.Column("fa_name", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False), sa.Column("en_name", sa.String(160)),
        sa.Column("country_id", BIGINT, nullable=False), sa.Column("province_id", BIGINT), sa.Column("city_id", BIGINT),
        sa.Column("geography_key", sa.String(200), nullable=False), sa.Column("short_address", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"), *audit_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["logistics_point_type_id"], ["logistics_point_type.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["country_id"], ["country.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["province_id"], ["province.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["city_id"], ["city.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("public_id", name="uq_logistics_point_public_id"),
        sa.UniqueConstraint("organization_id", "immutable_code", name="uq_logistics_point_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_logistics_point_id_org"),
        sa.UniqueConstraint("organization_id", "normalized_name", "logistics_point_type_id", "country_id", "geography_key", name="uq_logistics_point_exact_duplicate"),
        sa.CheckConstraint("version >= 1", name="ck_logistics_point_version_positive"))
    op.create_index("ix_logistics_point_org_active", "logistics_point", ["organization_id", "is_active"])
    op.create_index("ix_logistics_point_org_type", "logistics_point", ["organization_id", "logistics_point_type_id"])
    op.create_index("ix_logistics_point_org_name", "logistics_point", ["organization_id", "normalized_name"])
    op.create_index("ix_logistics_point_org_geography", "logistics_point", ["organization_id", "country_id", "province_id", "city_id"])
    op.create_index("ix_logistics_point_org_updated", "logistics_point", ["organization_id", "updated_at"])
    op.create_table("project_logistics_point",
        sa.Column("id", BIGINT, primary_key=True), sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False), sa.Column("project_id", BIGINT, nullable=False),
        sa.Column("logistics_point_id", BIGINT, nullable=False), sa.Column("project_role", sa.String(32), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False), sa.Column("display_label", sa.String(160)),
        sa.Column("notes", sa.Text()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"), *audit_columns(),
        sa.ForeignKeyConstraint(["project_id", "organization_id"], ["project.id", "project.organization_id"], name="fk_project_logistics_point_project_org", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["logistics_point_id", "organization_id"], ["logistics_point.id", "logistics_point.organization_id"], name="fk_project_logistics_point_point_org", ondelete="RESTRICT"),
        sa.UniqueConstraint("public_id", name="uq_project_logistics_point_public_id"),
        sa.UniqueConstraint("project_id", "logistics_point_id", "project_role", name="uq_project_logistics_point_role"),
        sa.CheckConstraint("sequence_number >= 1", name="ck_project_logistics_point_sequence_positive"),
        sa.CheckConstraint("project_role IN ('ORIGIN','INTERMEDIATE','DESTINATION','CUSTOMS_PROCESSING','TRANSFER','STORAGE','LOADING','UNLOADING','OTHER_GOVERNED')", name="ck_project_logistics_point_role"),
        sa.CheckConstraint("version >= 1", name="ck_project_logistics_point_version_positive"))
    op.create_index("uq_project_logistics_point_active_sequence", "project_logistics_point", ["project_id", "sequence_number"], unique=True, postgresql_where=sa.text("is_active"), sqlite_where=sa.text("is_active = 1"))
    op.create_index("ix_project_logistics_point_project_active", "project_logistics_point", ["project_id", "is_active", "sequence_number"])


def downgrade():
    op.drop_index("ix_project_logistics_point_project_active", table_name="project_logistics_point")
    op.drop_index("uq_project_logistics_point_active_sequence", table_name="project_logistics_point")
    op.drop_table("project_logistics_point")
    for name in ["ix_logistics_point_org_updated", "ix_logistics_point_org_geography", "ix_logistics_point_org_name", "ix_logistics_point_org_type", "ix_logistics_point_org_active"]:
        op.drop_index(name, table_name="logistics_point")
    op.drop_table("logistics_point")
    op.drop_index("ix_logistics_point_type_active_order", table_name="logistics_point_type")
    op.drop_table("logistics_point_type")
