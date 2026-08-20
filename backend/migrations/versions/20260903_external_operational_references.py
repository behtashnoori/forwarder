"""Add governed external operational reference schema.

Revision ID: 20260903_external_operational_references
Revises: 20260902_shipment_request_public_id
"""

from alembic import op
import sqlalchemy as sa

revision = "20260903_external_operational_references"
down_revision = "20260902_shipment_request_public_id"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _common(owner_name: str):
    return [
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.Column("external_reference_type_id", BIGINT, nullable=False),
        sa.Column(owner_name, BIGINT, nullable=False),
        sa.Column("raw_value", sa.String(255), nullable=False),
        sa.Column("normalized_value", sa.String(255), nullable=False),
        sa.Column(
            "lifecycle_status", sa.String(16), nullable=False, server_default="ACTIVE"
        ),
        sa.Column("issuer_key", sa.String(160)),
        sa.Column("source_system", sa.String(160)),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("supersedes_reference_id", BIGINT),
        sa.Column("evidence_document_file_id", BIGINT),
        sa.Column("evidence_version", sa.Integer()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text()),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column("updated_by_user_id", BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        "external_reference_type",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_fa", sa.String(160), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column(
            "lifecycle_status", sa.String(16), nullable=False, server_default="DRAFT"
        ),
        sa.Column(
            "normalization_policy",
            sa.String(32),
            nullable=False,
            server_default="TRIM_UPPERCASE_V1",
        ),
        sa.Column(
            "search_policy", sa.String(16), nullable=False, server_default="EXACT"
        ),
        sa.Column(
            "uniqueness_scope", sa.String(16), nullable=False, server_default="OWNER"
        ),
        sa.Column(
            "masking_policy",
            sa.String(32),
            nullable=False,
            server_default="INTERNAL_FULL",
        ),
        sa.Column("source_authority", sa.String(255)),
        sa.Column("provenance_reference", sa.String(500)),
        sa.Column(
            "allows_operational_shipment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "allows_execution_unit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_by_user_id",
            BIGINT,
            sa.ForeignKey("expert_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_by_user_id",
            BIGINT,
            sa.ForeignKey("expert_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("public_id", name="uq_external_reference_type_public_id"),
        sa.UniqueConstraint("code", name="uq_external_reference_type_code"),
        sa.CheckConstraint(
            "code IN ('BILL_OF_LADING_NUMBER','AIR_WAYBILL_NUMBER','CMR_NUMBER')",
            name="ck_external_reference_type_v1_code",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('DRAFT','ACTIVE','DEPRECATED')",
            name="ck_external_reference_type_lifecycle",
        ),
        sa.CheckConstraint(
            "normalization_policy = 'TRIM_UPPERCASE_V1'",
            name="ck_external_reference_type_normalization",
        ),
        sa.CheckConstraint(
            "search_policy IN ('EXACT','PREFIX','DISPLAY_ONLY','NONE')",
            name="ck_external_reference_type_search",
        ),
        sa.CheckConstraint(
            "uniqueness_scope IN ('NONE','OWNER','TENANT','ISSUER')",
            name="ck_external_reference_type_uniqueness",
        ),
        sa.CheckConstraint(
            "allows_operational_shipment OR allows_execution_unit",
            name="ck_external_reference_type_owner",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_external_reference_type_revision"),
        sa.CheckConstraint(
            "lifecycle_status <> 'ACTIVE' OR (length(trim(source_authority)) > 0 AND length(trim(provenance_reference)) > 0)",
            name="ck_external_reference_type_active_provenance",
        ),
    )

    op.create_table(
        "operational_shipment_external_reference",
        *_common("operational_shipment_id"),
        sa.UniqueConstraint(
            "public_id", name="uq_shipment_external_reference_public_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["external_reference_type_id"],
            ["external_reference_type.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_shipment_external_reference_owner_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_reference_id"],
            ["operational_shipment_external_reference.id"],
            name="fk_shipment_external_reference_supersedes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_document_file_id"],
            ["case_document_file.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('ACTIVE','SUPERSEDED','CANCELLED')",
            name="ck_shipment_external_reference_lifecycle",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_shipment_external_reference_revision"
        ),
        sa.CheckConstraint(
            "(evidence_document_file_id IS NULL AND evidence_version IS NULL) OR (evidence_document_file_id IS NOT NULL AND evidence_version >= 1)",
            name="ck_shipment_external_reference_evidence",
        ),
    )
    op.create_index(
        "ix_shipment_external_reference_search",
        "operational_shipment_external_reference",
        [
            "organization_id",
            "external_reference_type_id",
            "normalized_value",
            "lifecycle_status",
        ],
    )
    op.create_index(
        "ix_shipment_external_reference_owner",
        "operational_shipment_external_reference",
        ["operational_shipment_id", "lifecycle_status"],
    )

    op.create_table(
        "execution_unit_external_reference",
        *_common("execution_unit_id"),
        sa.UniqueConstraint(
            "public_id", name="uq_execution_unit_external_reference_public_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["operational_organization.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["external_reference_type_id"],
            ["external_reference_type.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_unit_id"], ["execution_unit.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_reference_id"],
            ["execution_unit_external_reference.id"],
            name="fk_execution_unit_external_reference_supersedes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_document_file_id"],
            ["case_document_file.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["expert_user.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('ACTIVE','SUPERSEDED','CANCELLED')",
            name="ck_execution_unit_external_reference_lifecycle",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_execution_unit_external_reference_revision"
        ),
        sa.CheckConstraint(
            "(evidence_document_file_id IS NULL AND evidence_version IS NULL) OR (evidence_document_file_id IS NOT NULL AND evidence_version >= 1)",
            name="ck_execution_unit_external_reference_evidence",
        ),
    )
    op.create_index(
        "ix_execution_unit_external_reference_search",
        "execution_unit_external_reference",
        [
            "organization_id",
            "external_reference_type_id",
            "normalized_value",
            "lifecycle_status",
        ],
    )
    op.create_index(
        "ix_execution_unit_external_reference_owner",
        "execution_unit_external_reference",
        ["execution_unit_id", "lifecycle_status"],
    )


def downgrade():
    op.drop_index(
        "ix_execution_unit_external_reference_owner",
        table_name="execution_unit_external_reference",
    )
    op.drop_index(
        "ix_execution_unit_external_reference_search",
        table_name="execution_unit_external_reference",
    )
    op.drop_table("execution_unit_external_reference")
    op.drop_index(
        "ix_shipment_external_reference_owner",
        table_name="operational_shipment_external_reference",
    )
    op.drop_index(
        "ix_shipment_external_reference_search",
        table_name="operational_shipment_external_reference",
    )
    op.drop_table("operational_shipment_external_reference")
    op.drop_table("external_reference_type")
