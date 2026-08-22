"""Add tenant-owned global logistics point adoption.

Revision ID: 20260905_global_logistics_point_adoption
Revises: 20260904_global_logistics_point_foundation
"""
from alembic import op
import sqlalchemy as sa

revision = "20260905_global_logistics_point_adoption"
down_revision = "20260904_global_logistics_point_foundation"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "organization_global_logistics_point_adoption",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("global_logistics_point_id", BIGINT, nullable=False),
        sa.Column("organization_reference_code", sa.String(64)),
        sa.Column("display_label", sa.String(160)),
        sa.Column("notes", sa.String(1000)),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", BIGINT, nullable=False),
        sa.Column("updated_by", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["global_logistics_point_id"], ["global_logistics_point.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("public_id", name="uq_org_global_point_adoption_public_id"),
        sa.UniqueConstraint("organization_id", "global_logistics_point_id", name="uq_org_global_point_adoption_logical"),
        sa.UniqueConstraint("id", "organization_id", name="uq_org_global_point_adoption_id_org"),
        sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="ck_org_global_point_adoption_status"),
        sa.CheckConstraint("version >= 1", name="ck_org_global_point_adoption_version"),
    )
    op.create_index("ix_org_global_point_adoption_catalog",
                    "organization_global_logistics_point_adoption", ["organization_id", "status"])
    op.create_index("ix_org_global_point_adoption_global",
                    "organization_global_logistics_point_adoption", ["global_logistics_point_id"])


def downgrade():
    count = op.get_bind().execute(sa.text(
        "SELECT count(*) FROM organization_global_logistics_point_adoption"
    )).scalar_one()
    if count:
        raise RuntimeError("Downgrade refused: tenant-owned global point adoption history exists.")
    op.drop_index("ix_org_global_point_adoption_global", table_name="organization_global_logistics_point_adoption")
    op.drop_index("ix_org_global_point_adoption_catalog", table_name="organization_global_logistics_point_adoption")
    op.drop_table("organization_global_logistics_point_adoption")
