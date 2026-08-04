"""Add governed Project Configuration foundation.

Revision ID: 20260811_project_configuration
Revises: 20260810_logistics_network
"""

from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = "20260811_project_configuration"
down_revision = "20260810_logistics_network"
branch_labels = None
depends_on = None
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def audit_columns():
    return (
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
    with op.batch_alter_table("project_logistics_point") as batch:
        batch.create_unique_constraint(
            "uq_project_logistics_point_project_id_id", ["project_id", "id"]
        )
    with op.batch_alter_table("document_definition") as batch:
        batch.add_column(sa.Column("public_id", sa.String(36), nullable=True))
    bind = op.get_bind()
    ids = (
        bind.execute(
            sa.text("SELECT id FROM document_definition WHERE public_id IS NULL")
        )
        .scalars()
        .all()
    )
    for row_id in ids:
        bind.execute(
            sa.text(
                "UPDATE document_definition SET public_id=:public_id WHERE id=:id AND public_id IS NULL"
            ),
            {"public_id": str(uuid4()), "id": row_id},
        )
    with op.batch_alter_table("document_definition") as batch:
        batch.create_unique_constraint(
            "uq_document_definition_public_id", ["public_id"]
        )
        batch.alter_column("public_id", existing_type=sa.String(36), nullable=False)
    op.create_table(
        "milestone_type",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("immutable_code", sa.String(64), nullable=False),
        sa.Column("fa_name", sa.String(160), nullable=False),
        sa.Column("en_name", sa.String(160), nullable=False),
        sa.Column("definition", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        *audit_columns(),
        sa.UniqueConstraint("public_id", name="uq_milestone_type_public_id"),
        sa.UniqueConstraint("immutable_code", name="uq_milestone_type_code"),
        sa.CheckConstraint("version >= 1", name="ck_milestone_type_version_positive"),
    )
    op.create_index(
        "ix_milestone_type_active_order",
        "milestone_type",
        ["is_active", "display_order"],
    )
    op.create_table(
        "project_service",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "project_id",
            BIGINT,
            sa.ForeignKey("project.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "service_type_id",
            BIGINT,
            sa.ForeignKey("service_type.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_required", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("display_label", sa.String(160)),
        sa.Column("notes", sa.Text()),
        *audit_columns(),
        sa.UniqueConstraint("public_id", name="uq_project_service_public_id"),
        sa.UniqueConstraint(
            "project_id", "service_type_id", name="uq_project_service_logical"
        ),
        sa.CheckConstraint("display_order >= 0", name="ck_project_service_order"),
        sa.CheckConstraint("version >= 1", name="ck_project_service_version"),
    )
    op.create_index(
        "uq_project_service_active_primary",
        "project_service",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND is_primary"),
        sqlite_where=sa.text("is_active = 1 AND is_primary = 1"),
    )
    op.create_table(
        "project_document_requirement",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "project_id",
            BIGINT,
            sa.ForeignKey("project.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_definition_id",
            BIGINT,
            sa.ForeignKey("document_definition.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("requirement_level", sa.String(16), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conditional_description", sa.Text()),
        sa.Column("notes", sa.Text()),
        *audit_columns(),
        sa.UniqueConstraint(
            "public_id", name="uq_project_document_requirement_public_id"
        ),
        sa.UniqueConstraint(
            "project_id",
            "document_definition_id",
            name="uq_project_document_requirement_logical",
        ),
        sa.CheckConstraint(
            "requirement_level IN ('REQUIRED','OPTIONAL','CONDITIONAL')",
            name="ck_project_document_requirement_level",
        ),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_project_document_requirement_order"
        ),
        sa.CheckConstraint(
            "version >= 1", name="ck_project_document_requirement_version"
        ),
    )
    op.create_table(
        "project_milestone_definition",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "project_id",
            BIGINT,
            sa.ForeignKey("project.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "milestone_type_id",
            BIGINT,
            sa.ForeignKey("milestone_type.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_logistics_point_id",
            BIGINT,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "is_required", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("display_label", sa.String(160)),
        sa.Column("target_duration_value", sa.Integer()),
        sa.Column("warning_duration_value", sa.Integer()),
        sa.Column("duration_unit", sa.String(8)),
        sa.Column("notes", sa.Text()),
        *audit_columns(),
        sa.ForeignKeyConstraint(
            ["project_id", "project_logistics_point_id"],
            ["project_logistics_point.project_id", "project_logistics_point.id"],
            name="fk_project_milestone_definition_project_point",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "public_id", name="uq_project_milestone_definition_public_id"
        ),
        sa.UniqueConstraint(
            "project_id",
            "milestone_type_id",
            name="uq_project_milestone_definition_logical",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_project_milestone_sequence"),
        sa.CheckConstraint(
            "duration_unit IS NULL OR duration_unit IN ('MINUTE','HOUR','DAY')",
            name="ck_project_milestone_duration_unit",
        ),
        sa.CheckConstraint(
            "target_duration_value IS NULL OR target_duration_value > 0",
            name="ck_project_milestone_target",
        ),
        sa.CheckConstraint(
            "warning_duration_value IS NULL OR warning_duration_value > 0",
            name="ck_project_milestone_warning",
        ),
        sa.CheckConstraint(
            "target_duration_value IS NULL OR warning_duration_value IS NULL OR warning_duration_value >= target_duration_value",
            name="ck_project_milestone_warning_target",
        ),
        sa.CheckConstraint("version >= 1", name="ck_project_milestone_version"),
    )
    op.create_index(
        "uq_project_milestone_active_sequence",
        "project_milestone_definition",
        ["project_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active = 1"),
    )


def downgrade():
    op.drop_index(
        "uq_project_milestone_active_sequence",
        table_name="project_milestone_definition",
    )
    op.drop_table("project_milestone_definition")
    op.drop_table("project_document_requirement")
    op.drop_index("uq_project_service_active_primary", table_name="project_service")
    op.drop_table("project_service")
    op.drop_index("ix_milestone_type_active_order", table_name="milestone_type")
    op.drop_table("milestone_type")
    with op.batch_alter_table("project_logistics_point") as batch:
        batch.drop_constraint(
            "uq_project_logistics_point_project_id_id", type_="unique"
        )
    with op.batch_alter_table("document_definition") as batch:
        batch.drop_constraint("uq_document_definition_public_id", type_="unique")
        batch.drop_column("public_id")
