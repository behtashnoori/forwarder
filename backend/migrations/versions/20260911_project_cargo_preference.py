"""Add project commodity catalog preferences.

Revision ID: 20260911_project_cargo_preference
Revises: 20260910_route_leg_logistics_points
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_project_cargo_preference"
down_revision = "20260910_route_leg_logistics_points"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "project_cargo_catalog_item",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("project_id", BIGINT, nullable=False),
        sa.Column("cargo_catalog_item_id", BIGINT, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", BIGINT, nullable=False),
        sa.Column("updated_by", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["operational_organization.id"],
            name="fk_project_cargo_item_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "organization_id"],
            ["project.id", "project.organization_id"],
            name="fk_project_cargo_item_project_same_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cargo_catalog_item_id", "organization_id"],
            ["cargo_catalog_item.id", "cargo_catalog_item.organization_id"],
            name="fk_project_cargo_item_catalog_same_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["expert_user.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["expert_user.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("public_id", name="uq_project_cargo_catalog_item_public_id"),
        sa.UniqueConstraint(
            "project_id",
            "cargo_catalog_item_id",
            name="uq_project_cargo_catalog_item_pair",
        ),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_project_cargo_catalog_item_order"
        ),
        sa.CheckConstraint(
            "version >= 1", name="ck_project_cargo_catalog_item_version"
        ),
    )
    op.create_index(
        "ix_project_cargo_catalog_item_preference",
        "project_cargo_catalog_item",
        ["project_id", "is_active", "display_order"],
    )
    op.create_index(
        "ix_project_cargo_catalog_item_catalog",
        "project_cargo_catalog_item",
        ["cargo_catalog_item_id", "project_id"],
    )


def downgrade():
    op.drop_index(
        "ix_project_cargo_catalog_item_catalog",
        table_name="project_cargo_catalog_item",
    )
    op.drop_index(
        "ix_project_cargo_catalog_item_preference",
        table_name="project_cargo_catalog_item",
    )
    op.drop_table("project_cargo_catalog_item")
