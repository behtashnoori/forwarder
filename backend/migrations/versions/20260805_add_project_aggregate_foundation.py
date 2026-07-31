"""Add the Slice-001 Project aggregate foundation.

Revision ID: 20260805_project_foundation
Revises: 20260804_case_documents
"""
from alembic import op
import sqlalchemy as sa


revision = "20260805_project_foundation"
down_revision = "20260804_case_documents"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "project",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("primary_customer_id", BIGINT, nullable=False),
        sa.Column("project_code", sa.String(64), nullable=False),
        sa.Column(
            "lifecycle_status",
            sa.String(24),
            nullable=False,
            server_default="not_started",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["operational_organization.id"],
            name="fk_project_organization_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["primary_customer_id"],
            ["customer.id"],
            name="fk_project_primary_customer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["expert_user.id"],
            name="fk_project_created_by_user_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("public_id", name="uq_project_public_id"),
        sa.UniqueConstraint(
            "organization_id", "project_code", name="uq_project_org_code"
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_project_id_org"),
        sa.CheckConstraint(
            "lifecycle_status IN "
            "('not_started','in_progress','partially_delivered','completed','cancelled')",
            name="ck_project_lifecycle_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_project_version_positive"),
    )
    op.create_index(
        "ix_project_org_customer",
        "project",
        ["organization_id", "primary_customer_id"],
    )

    op.create_table(
        "project_party_relationship",
        sa.Column("project_id", BIGINT, nullable=False),
        sa.Column("customer_id", BIGINT, nullable=False),
        sa.Column("party_role", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_project_party_relationship_project_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customer.id"],
            name="fk_project_party_relationship_customer_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "customer_id",
            "party_role",
            name="pk_project_party_relationship",
        ),
        sa.CheckConstraint(
            "party_role IN ('payer','consignee','cargo_owner','notify_party','other')",
            name="ck_project_party_relationship_role",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_project_party_relationship_validity",
        ),
    )

    with op.batch_alter_table("operational_shipment") as batch:
        batch.add_column(sa.Column("project_id", BIGINT, nullable=True))
        batch.create_foreign_key(
            "fk_operational_shipment_project_same_org",
            "project",
            ["project_id", "organization_id"],
            ["id", "organization_id"],
            ondelete="RESTRICT",
        )
        batch.create_index(
            "ix_operational_shipment_project_id", ["project_id"], unique=False
        )
    with op.batch_alter_table("shipment_request") as batch:
        batch.add_column(sa.Column("project_id", BIGINT, nullable=True))
        batch.create_foreign_key(
            "fk_shipment_request_project_id",
            "project",
            ["project_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_shipment_request_project_id", ["project_id"])


def downgrade():
    with op.batch_alter_table("shipment_request") as batch:
        batch.drop_index("ix_shipment_request_project_id")
        batch.drop_constraint("fk_shipment_request_project_id", type_="foreignkey")
        batch.drop_column("project_id")
    with op.batch_alter_table("operational_shipment") as batch:
        batch.drop_index("ix_operational_shipment_project_id")
        batch.drop_constraint(
            "fk_operational_shipment_project_same_org", type_="foreignkey"
        )
        batch.drop_column("project_id")
    op.drop_table("project_party_relationship")
    op.drop_index("ix_project_org_customer", table_name="project")
    op.drop_table("project")
