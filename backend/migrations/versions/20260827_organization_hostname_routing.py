"""Add exact hostname routing for operational organizations.

Revision ID: 20260827_org_hostname
Revises: 20260826_org_document_policy
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_org_hostname"
down_revision = "20260826_org_document_policy"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organization_hostname",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("hostname", sa.String(253), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["operational_organization.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("public_id", name="uq_organization_hostname_public_id"),
        sa.CheckConstraint("hostname = lower(hostname)", name="ck_organization_hostname_lowercase"),
    )
    op.create_index("ix_organization_hostname_organization_id", "organization_hostname", ["organization_id"])
    op.create_index(
        "uq_organization_hostname_active_hostname", "organization_hostname", ["hostname"],
        unique=True, postgresql_where=sa.text("is_active = true"), sqlite_where=sa.text("is_active = 1"),
    )
    op.create_index(
        "uq_organization_hostname_primary", "organization_hostname", ["organization_id"],
        unique=True, postgresql_where=sa.text("is_active = true AND is_primary = true"),
        sqlite_where=sa.text("is_active = 1 AND is_primary = 1"),
    )


def downgrade():
    op.drop_index("uq_organization_hostname_primary", table_name="organization_hostname")
    op.drop_index("uq_organization_hostname_active_hostname", table_name="organization_hostname")
    op.drop_index("ix_organization_hostname_organization_id", table_name="organization_hostname")
    op.drop_table("organization_hostname")
