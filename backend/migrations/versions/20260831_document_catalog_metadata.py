"""Add governed Document Master Catalog metadata and relations.

Revision ID: 20260831_document_catalog_metadata
Revises: 20260830_logistics_point_tracking_convergence
"""

from alembic import op
import sqlalchemy as sa

revision = "20260831_document_catalog_metadata"
down_revision = "20260830_logistics_point_tracking_convergence"
branch_labels = None
depends_on = None

FAMILIES = "'COMMERCIAL','TRANSPORT','FORWARDING','CUSTOMS','WAREHOUSE','RELEASE','CERTIFICATE','PERMIT_AUTHORIZATION','INSURANCE','FINANCE','SAFETY','OPERATIONAL_NOTICE'"
REVIEWS = "'VERIFIED','SOURCE_CONFIRMED','SOURCE_CONFIRMATION_REQUIRED','DOMAIN_CONFIRMATION_REQUIRED','SUPERSEDED'"


def _identity_columns():
    return [
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "document_definition_id",
            sa.BigInteger(),
            sa.ForeignKey("document_definition.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    ]


def upgrade():
    with op.batch_alter_table("document_definition") as batch:
        batch.add_column(sa.Column("name_fa", sa.String(200), nullable=True))
        batch.add_column(sa.Column("name_en", sa.String(200), nullable=True))
        batch.add_column(sa.Column("description_fa", sa.Text(), nullable=True))
        batch.add_column(sa.Column("description_en", sa.Text(), nullable=True))
        batch.add_column(sa.Column("family_code", sa.String(32), nullable=True))
        batch.add_column(
            sa.Column("reference_number_label_fa", sa.String(160), nullable=True)
        )
        batch.add_column(
            sa.Column("reference_number_label_en", sa.String(160), nullable=True)
        )
        batch.add_column(sa.Column("expiry_applicable", sa.Boolean(), nullable=True))
        batch.add_column(
            sa.Column(
                "organization_overridable",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch.add_column(
            sa.Column(
                "catalog_lifecycle_status",
                sa.String(24),
                nullable=False,
                server_default="DRAFT",
            )
        )
        batch.add_column(
            sa.Column(
                "source_review_status",
                sa.String(40),
                nullable=False,
                server_default="SOURCE_CONFIRMATION_REQUIRED",
            )
        )
        batch.create_check_constraint(
            "ck_document_definition_family",
            f"family_code IS NULL OR family_code IN ({FAMILIES})",
        )
        batch.create_check_constraint(
            "ck_document_definition_catalog_lifecycle",
            "catalog_lifecycle_status IN ('DRAFT','REVIEWED','SOURCE_CONFIRMED','ACTIVE','DEPRECATED')",
        )
        batch.create_check_constraint(
            "ck_document_definition_source_review",
            f"source_review_status IN ({REVIEWS})",
        )
    op.create_index(
        "ix_document_definition_family_code", "document_definition", ["family_code"]
    )
    op.create_index(
        "ix_document_definition_catalog_lifecycle_status",
        "document_definition",
        ["catalog_lifecycle_status"],
    )
    op.create_index(
        "ix_document_definition_source_review_status",
        "document_definition",
        ["source_review_status"],
    )

    op.create_table(
        "document_definition_alias",
        *_identity_columns(),
        sa.Column("locale", sa.String(16)),
        sa.Column("display_value", sa.String(200), nullable=False),
        sa.Column("normalized_value", sa.String(200), nullable=False),
        sa.Column("alias_kind", sa.String(24), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("expert_user.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "updated_by",
            sa.BigInteger(),
            sa.ForeignKey("expert_user.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint(
            "normalized_value", name="uq_document_definition_alias_normalized"
        ),
        sa.CheckConstraint(
            "alias_kind IN ('ABBREVIATION','TRANSLITERATION','COMMON_NAME','FORMER_NAME')",
            name="ck_document_definition_alias_kind",
        ),
    )
    op.create_index(
        "ix_document_definition_alias_document_definition_id",
        "document_definition_alias",
        ["document_definition_id"],
    )
    op.create_table(
        "document_definition_jurisdiction",
        *_identity_columns(),
        sa.Column("applicability_kind", sa.String(16), nullable=False),
        sa.Column("applicability_key", sa.String(32), nullable=False),
        sa.Column(
            "country_id",
            sa.BigInteger(),
            sa.ForeignKey("country.id", ondelete="RESTRICT"),
        ),
        sa.UniqueConstraint(
            "document_definition_id",
            "applicability_key",
            name="uq_document_definition_jurisdiction_key",
        ),
        sa.CheckConstraint(
            "applicability_kind IN ('GLOBAL','INTERNATIONAL','COUNTRY')",
            name="ck_document_definition_jurisdiction_kind",
        ),
        sa.CheckConstraint(
            "(applicability_kind = 'COUNTRY' AND country_id IS NOT NULL) OR (applicability_kind <> 'COUNTRY' AND country_id IS NULL)",
            name="ck_document_definition_jurisdiction_country",
        ),
    )
    op.create_index(
        "ix_document_definition_jurisdiction_document_definition_id",
        "document_definition_jurisdiction",
        ["document_definition_id"],
    )
    op.create_table(
        "document_definition_mode",
        *_identity_columns(),
        sa.Column("mode_code", sa.String(24), nullable=False),
        sa.UniqueConstraint(
            "document_definition_id", "mode_code", name="uq_document_definition_mode"
        ),
        sa.CheckConstraint(
            "mode_code IN ('ROAD','SEA','AIR','RAIL','MULTIMODAL','MODE_INDEPENDENT')",
            name="ck_document_definition_mode_code",
        ),
    )
    op.create_index(
        "ix_document_definition_mode_document_definition_id",
        "document_definition_mode",
        ["document_definition_id"],
    )
    op.create_table(
        "document_definition_stage",
        *_identity_columns(),
        sa.Column("stage_code", sa.String(32), nullable=False),
        sa.UniqueConstraint(
            "document_definition_id", "stage_code", name="uq_document_definition_stage"
        ),
        sa.CheckConstraint(
            "stage_code IN ('PRE_SHIPMENT','BOOKING','ORIGIN','IN_TRANSIT','ARRIVAL','WAREHOUSE','CUSTOMS_DECLARATION','CUSTOMS_CLEARANCE','RELEASE','DELIVERY','POST_DELIVERY','PAYMENT_FINANCE')",
            name="ck_document_definition_stage_code",
        ),
    )
    op.create_index(
        "ix_document_definition_stage_document_definition_id",
        "document_definition_stage",
        ["document_definition_id"],
    )
    op.create_table(
        "document_definition_business_scope",
        *_identity_columns(),
        sa.Column("scope_code", sa.String(32), nullable=False),
        sa.UniqueConstraint(
            "document_definition_id",
            "scope_code",
            name="uq_document_definition_business_scope",
        ),
        sa.CheckConstraint(
            "scope_code IN ('REQUEST','PROJECT','OPERATIONAL_SHIPMENT','CARGO','MULTIPLE')",
            name="ck_document_definition_business_scope_code",
        ),
    )
    op.create_index(
        "ix_document_definition_business_scope_document_definition_id",
        "document_definition_business_scope",
        ["document_definition_id"],
    )
    op.create_table(
        "document_definition_provenance",
        *_identity_columns(),
        sa.Column("source_authority_code", sa.String(64), nullable=False),
        sa.Column("source_authority_name", sa.String(200), nullable=False),
        sa.Column("source_title", sa.String(300), nullable=False),
        sa.Column("source_reference", sa.String(500)),
        sa.Column("source_version", sa.String(100)),
        sa.Column("source_date", sa.Date()),
        sa.Column("jurisdiction_key", sa.String(32)),
        sa.Column("review_status", sa.String(40), nullable=False),
        sa.Column(
            "reviewed_by",
            sa.BigInteger(),
            sa.ForeignKey("expert_user.id", ondelete="SET NULL"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            f"review_status IN ({REVIEWS})",
            name="ck_document_definition_provenance_review",
        ),
    )
    op.create_index(
        "ix_document_definition_provenance_document_definition_id",
        "document_definition_provenance",
        ["document_definition_id"],
    )
    op.create_table(
        "document_catalog_audit_event",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("definition_public_id", sa.String(36), nullable=False),
        sa.Column("definition_code", sa.String(64), nullable=False),
        sa.Column(
            "actor_id",
            sa.BigInteger(),
            sa.ForeignKey("expert_user.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("previous_revision", sa.Integer()),
        sa.Column("resulting_revision", sa.Integer()),
        sa.Column("previous_lifecycle", sa.String(24)),
        sa.Column("resulting_lifecycle", sa.String(24)),
        sa.Column("approval_reference", sa.String(200)),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("details", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_document_catalog_audit_idempotency"
        ),
    )
    op.create_index(
        "ix_document_catalog_audit_event_definition_public_id",
        "document_catalog_audit_event",
        ["definition_public_id"],
    )
    op.create_index(
        "ix_document_catalog_audit_event_action",
        "document_catalog_audit_event",
        ["action"],
    )
    op.create_index(
        "ix_document_catalog_audit_event_created_at",
        "document_catalog_audit_event",
        ["created_at"],
    )


def downgrade():
    connection = op.get_bind()
    child_tables = (
        "document_catalog_audit_event",
        "document_definition_provenance",
        "document_definition_business_scope",
        "document_definition_stage",
        "document_definition_mode",
        "document_definition_jurisdiction",
        "document_definition_alias",
    )
    if any(
        connection.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first()
        for table in child_tables
    ):
        raise RuntimeError(
            "Downgrade refused while governed document catalog child/audit records exist"
        )
    enriched = connection.execute(
        sa.text(
            "SELECT 1 FROM document_definition WHERE name_fa IS NOT NULL OR name_en IS NOT NULL OR description_fa IS NOT NULL OR description_en IS NOT NULL OR family_code IS NOT NULL OR reference_number_label_fa IS NOT NULL OR reference_number_label_en IS NOT NULL OR expiry_applicable IS NOT NULL OR organization_overridable = false OR catalog_lifecycle_status <> 'DRAFT' OR source_review_status <> 'SOURCE_CONFIRMATION_REQUIRED' LIMIT 1"
        )
    ).first()
    if enriched:
        raise RuntimeError(
            "Downgrade refused while governed document catalog metadata exists"
        )
    for table in (
        "document_catalog_audit_event",
        "document_definition_provenance",
        "document_definition_business_scope",
        "document_definition_stage",
        "document_definition_mode",
        "document_definition_jurisdiction",
        "document_definition_alias",
    ):
        op.drop_table(table)
    for name in ("source_review_status", "catalog_lifecycle_status", "family_code"):
        op.drop_index(
            f"ix_document_definition_{name}", table_name="document_definition"
        )
    with op.batch_alter_table("document_definition") as batch:
        batch.drop_constraint("ck_document_definition_source_review", type_="check")
        batch.drop_constraint("ck_document_definition_catalog_lifecycle", type_="check")
        batch.drop_constraint("ck_document_definition_family", type_="check")
        for column in (
            "source_review_status",
            "catalog_lifecycle_status",
            "organization_overridable",
            "expiry_applicable",
            "reference_number_label_en",
            "reference_number_label_fa",
            "family_code",
            "description_en",
            "description_fa",
            "name_en",
            "name_fa",
        ):
            batch.drop_column(column)
