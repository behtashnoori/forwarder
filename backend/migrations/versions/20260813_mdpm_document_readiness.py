"""MDPM-1 operational document readiness.

Revision ID: 20260813_mdpm_readiness
Revises: 20260812_operational_execution
"""
from alembic import op
import sqlalchemy as sa

revision = "20260813_mdpm_readiness"
down_revision = "20260812_operational_execution"
branch_labels = None
depends_on = None

def _identity():
    return [sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("public_id", sa.String(36), nullable=False, unique=True)]

def upgrade():
    op.add_column("project_document_requirement", sa.Column("required_assessment_level", sa.String(16), nullable=False, server_default="APPROVED"))
    op.add_column("project_document_requirement", sa.Column("target_milestone_type_id", sa.BigInteger()))
    op.add_column("project_document_requirement", sa.Column("target_status", sa.String(20)))
    op.create_foreign_key("fk_project_doc_requirement_target_type", "project_document_requirement", "milestone_type", ["target_milestone_type_id"], ["id"], ondelete="RESTRICT")
    op.create_check_constraint("ck_project_doc_requirement_assessment", "project_document_requirement", "required_assessment_level IN ('APPROVED','VERIFIED')")
    op.create_check_constraint("ck_project_doc_requirement_target", "project_document_requirement", "(target_milestone_type_id IS NULL AND target_status IS NULL) OR (target_milestone_type_id IS NOT NULL AND target_status IN ('READY','IN_PROGRESS','COMPLETED','SKIPPED','CANCELLED'))")
    op.add_column("case_document_file", sa.Column("public_id", sa.String(36)))
    op.execute("UPDATE case_document_file SET public_id=gen_random_uuid()::text WHERE public_id IS NULL")
    op.alter_column("case_document_file", "public_id", nullable=False)
    op.create_unique_constraint("uq_case_document_file_public_id", "case_document_file", ["public_id"])

    op.create_table("operational_document_requirement", *_identity(),
        sa.Column("organization_id",sa.BigInteger(),nullable=False), sa.Column("operational_shipment_id",sa.BigInteger(),nullable=False),
        sa.Column("document_definition_id",sa.BigInteger(),nullable=False), sa.Column("source_project_requirement_id",sa.BigInteger(),nullable=False),
        sa.Column("source_project_requirement_public_id",sa.String(36),nullable=False), sa.Column("source_project_requirement_version",sa.Integer(),nullable=False),
        sa.Column("requirement_level",sa.String(16),nullable=False), sa.Column("applicability_state",sa.String(20),nullable=False),
        sa.Column("required_assessment_level",sa.String(16),nullable=False), sa.Column("target_milestone_type",sa.String(64),nullable=False),
        sa.Column("target_status",sa.String(20),nullable=False), sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column("version",sa.Integer(),nullable=False,server_default="1"), sa.Column("created_by_user_id",sa.BigInteger(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()), sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["operational_shipment_id","organization_id"],["operational_shipment.id","operational_shipment.organization_id"],name="fk_operational_doc_requirement_shipment_org",ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_definition_id"],["document_definition.id"],ondelete="RESTRICT"), sa.ForeignKeyConstraint(["source_project_requirement_id"],["project_document_requirement.id"],ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"],["expert_user.id"],ondelete="RESTRICT"),
        sa.UniqueConstraint("operational_shipment_id","source_project_requirement_id",name="uq_operational_doc_requirement_source"),
        sa.CheckConstraint("requirement_level IN ('REQUIRED','OPTIONAL','CONDITIONAL')",name="ck_operational_doc_requirement_level"),
        sa.CheckConstraint("applicability_state IN ('APPLICABLE','NOT_APPLICABLE','UNRESOLVED')",name="ck_operational_doc_requirement_applicability"),
        sa.CheckConstraint("required_assessment_level IN ('APPROVED','VERIFIED')",name="ck_operational_doc_requirement_assessment"), sa.CheckConstraint("version >= 1",name="ck_operational_doc_requirement_version"))
    op.create_index("ix_operational_doc_requirement_readiness","operational_document_requirement",["organization_id","operational_shipment_id","target_milestone_type","target_status","is_active"])
    op.create_table("operational_artifact_association", *_identity(), sa.Column("organization_id",sa.BigInteger(),nullable=False),sa.Column("requirement_id",sa.BigInteger(),nullable=False),sa.Column("document_file_id",sa.BigInteger(),nullable=False),sa.Column("artifact_version",sa.Integer(),nullable=False),sa.Column("state",sa.String(16),nullable=False),sa.Column("reason",sa.Text()),sa.Column("associated_by_user_id",sa.BigInteger(),nullable=False),sa.Column("associated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("superseded_at",sa.DateTime(timezone=True)),sa.ForeignKeyConstraint(["organization_id"],["operational_organization.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["requirement_id"],["operational_document_requirement.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["document_file_id"],["case_document_file.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["associated_by_user_id"],["expert_user.id"],ondelete="RESTRICT"),sa.CheckConstraint("state IN ('ACTIVE','SUPERSEDED')",name="ck_operational_artifact_assoc_state"))
    op.create_index("ix_operational_artifact_assoc_active","operational_artifact_association",["requirement_id","state"])
    op.create_table("operational_document_assessment", *_identity(),sa.Column("organization_id",sa.BigInteger(),nullable=False),sa.Column("association_id",sa.BigInteger(),nullable=False),sa.Column("decision",sa.String(20),nullable=False),sa.Column("reason",sa.Text()),sa.Column("actor_user_id",sa.BigInteger(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.ForeignKeyConstraint(["organization_id"],["operational_organization.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["association_id"],["operational_artifact_association.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["actor_user_id"],["expert_user.id"],ondelete="RESTRICT"),sa.CheckConstraint("decision IN ('REVIEW_STARTED','APPROVED','REJECTED','VERIFIED')",name="ck_operational_doc_assessment_decision"))
    op.create_index("ix_operational_doc_assessment_projection","operational_document_assessment",["association_id","created_at","id"])
    op.create_table("operational_requirement_applicability", *_identity(),sa.Column("organization_id",sa.BigInteger(),nullable=False),sa.Column("requirement_id",sa.BigInteger(),nullable=False),sa.Column("decision",sa.String(20),nullable=False),sa.Column("reason",sa.Text(),nullable=False),sa.Column("actor_user_id",sa.BigInteger(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.ForeignKeyConstraint(["organization_id"],["operational_organization.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["requirement_id"],["operational_document_requirement.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["actor_user_id"],["expert_user.id"],ondelete="RESTRICT"),sa.CheckConstraint("decision IN ('APPLICABLE','NOT_APPLICABLE')",name="ck_operational_requirement_applicability_decision"))
    op.create_index("ix_operational_requirement_applicability_requirement","operational_requirement_applicability",["requirement_id"])
    op.create_table("operational_transition_override", *_identity(),sa.Column("organization_id",sa.BigInteger(),nullable=False),sa.Column("operational_shipment_id",sa.BigInteger(),nullable=False),sa.Column("requirement_id",sa.BigInteger(),nullable=False),sa.Column("milestone_id",sa.BigInteger(),nullable=False),sa.Column("target_status",sa.String(20),nullable=False),sa.Column("authority",sa.String(200),nullable=False),sa.Column("reason",sa.Text(),nullable=False),sa.Column("evidence_reference",sa.String(500)),sa.Column("state",sa.String(16),nullable=False),sa.Column("actor_user_id",sa.BigInteger(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("expires_at",sa.DateTime(timezone=True)),sa.Column("revoked_at",sa.DateTime(timezone=True)),sa.Column("revoked_by_user_id",sa.BigInteger()),sa.Column("consumed_at",sa.DateTime(timezone=True)),sa.ForeignKeyConstraint(["organization_id"],["operational_organization.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["operational_shipment_id"],["operational_shipment.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["requirement_id"],["operational_document_requirement.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["milestone_id"],["operational_milestone.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["actor_user_id"],["expert_user.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["revoked_by_user_id"],["expert_user.id"],ondelete="RESTRICT"),sa.CheckConstraint("state IN ('ACTIVE','REVOKED','CONSUMED','EXPIRED')",name="ck_operational_transition_override_state"))
    op.create_index("ix_operational_transition_override_lookup","operational_transition_override",["organization_id","operational_shipment_id","requirement_id","milestone_id","target_status","state"])
    op.create_table("document_readiness_audit", *_identity(),sa.Column("organization_id",sa.BigInteger(),nullable=False),sa.Column("operational_shipment_id",sa.BigInteger(),nullable=False),sa.Column("event_type",sa.String(64),nullable=False),sa.Column("actor_user_id",sa.BigInteger(),nullable=False),sa.Column("requirement_id",sa.BigInteger()),sa.Column("milestone_id",sa.BigInteger()),sa.Column("correlation_id",sa.String(36),nullable=False),sa.Column("evidence",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.ForeignKeyConstraint(["organization_id"],["operational_organization.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["operational_shipment_id"],["operational_shipment.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["actor_user_id"],["expert_user.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["requirement_id"],["operational_document_requirement.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["milestone_id"],["operational_milestone.id"],ondelete="RESTRICT"))
    op.create_index("ix_document_readiness_audit_org","document_readiness_audit",["organization_id"]);op.create_index("ix_document_readiness_audit_shipment","document_readiness_audit",["operational_shipment_id"]);op.create_index("ix_document_readiness_audit_event","document_readiness_audit",["event_type"]);op.create_index("ix_document_readiness_audit_created","document_readiness_audit",["created_at"])

def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM document_readiness_audit) OR EXISTS (SELECT 1 FROM operational_document_assessment) OR EXISTS (SELECT 1 FROM operational_artifact_association) OR EXISTS (SELECT 1 FROM operational_requirement_applicability) OR EXISTS (SELECT 1 FROM operational_transition_override) OR EXISTS (SELECT 1 FROM operational_document_requirement) THEN RAISE EXCEPTION 'cannot downgrade: MDPM business evidence exists' USING ERRCODE='23503'; END IF; END $$""")
    for table in ("document_readiness_audit","operational_transition_override","operational_requirement_applicability","operational_document_assessment","operational_artifact_association","operational_document_requirement"): op.drop_table(table)
    op.drop_constraint("uq_case_document_file_public_id","case_document_file",type_="unique");op.drop_column("case_document_file","public_id")
    op.drop_constraint("ck_project_doc_requirement_target","project_document_requirement",type_="check");op.drop_constraint("ck_project_doc_requirement_assessment","project_document_requirement",type_="check");op.drop_constraint("fk_project_doc_requirement_target_type","project_document_requirement",type_="foreignkey")
    op.drop_column("project_document_requirement","target_status");op.drop_column("project_document_requirement","target_milestone_type_id");op.drop_column("project_document_requirement","required_assessment_level")
