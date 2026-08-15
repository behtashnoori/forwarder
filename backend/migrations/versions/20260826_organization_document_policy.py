"""Add tenant-owned organization document policy.

Revision ID: 20260826_org_document_policy
Revises: 20260825_admin_multitenant
"""
from alembic import op
import sqlalchemy as sa

revision = "20260826_org_document_policy"
down_revision = "20260825_admin_multitenant"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organization_document_requirement",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("document_definition_id", sa.BigInteger(), nullable=False),
        sa.Column("requirement_level", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_definition_id"], ["document_definition.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["expert_user.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("public_id", name="uq_organization_document_requirement_public_id"),
        sa.UniqueConstraint("organization_id", "document_definition_id", name="uq_organization_document_requirement_logical"),
        sa.CheckConstraint("requirement_level IN ('REQUIRED','OPTIONAL','CONDITIONAL','DISABLED')", name="ck_organization_document_requirement_level"),
        sa.CheckConstraint("version >= 1", name="ck_organization_document_requirement_version"),
    )
    op.create_index(
        "ix_organization_document_requirement_active",
        "organization_document_requirement",
        ["organization_id", "is_active"],
    )
    with op.batch_alter_table("operational_document_requirement") as batch:
        batch.alter_column("source_project_requirement_id", existing_type=sa.BigInteger(), nullable=True)
        batch.alter_column("source_project_requirement_public_id", existing_type=sa.String(36), nullable=True)
        batch.alter_column("source_project_requirement_version", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("target_milestone_type", existing_type=sa.String(64), nullable=True)
        batch.alter_column("target_status", existing_type=sa.String(20), nullable=True)
        batch.add_column(sa.Column("source_organization_policy_id", sa.BigInteger(), nullable=True))
        batch.create_foreign_key("fk_operational_doc_requirement_org_policy",
            "organization_document_requirement", ["source_organization_policy_id"], ["id"], ondelete="RESTRICT")


def downgrade():
    bind = op.get_bind()
    incompatible_rows = bind.execute(
        sa.text(
            "SELECT count(*) FROM operational_document_requirement "
            "WHERE source_organization_policy_id IS NOT NULL "
            "OR source_project_requirement_id IS NULL "
            "OR source_project_requirement_public_id IS NULL "
            "OR source_project_requirement_version IS NULL "
            "OR target_milestone_type IS NULL OR target_status IS NULL"
        )
    ).scalar_one()
    if incompatible_rows:
        raise RuntimeError(
            "Downgrade refused: organization-policy document snapshots or other "
            "rows incompatible with the pre-policy schema exist. Preserve or "
            "migrate those tenant-owned records before downgrading."
        )
    with op.batch_alter_table("operational_document_requirement") as batch:
        batch.drop_constraint("fk_operational_doc_requirement_org_policy", type_="foreignkey")
        batch.drop_column("source_organization_policy_id")
        batch.alter_column("target_status", existing_type=sa.String(20), nullable=False)
        batch.alter_column("target_milestone_type", existing_type=sa.String(64), nullable=False)
        batch.alter_column("source_project_requirement_version", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("source_project_requirement_public_id", existing_type=sa.String(36), nullable=False)
        batch.alter_column("source_project_requirement_id", existing_type=sa.BigInteger(), nullable=False)
    op.drop_index("ix_organization_document_requirement_active", table_name="organization_document_requirement")
    op.drop_table("organization_document_requirement")
