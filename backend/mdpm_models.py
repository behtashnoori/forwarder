"""MDPM-1 document-readiness source facts for operational shipments."""

from uuid import uuid4

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class OperationalDocumentRequirement(db.Model):
    __tablename__ = "operational_document_requirement"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_operational_doc_requirement_public_id"),
        db.UniqueConstraint("operational_shipment_id", "source_project_requirement_id", name="uq_operational_doc_requirement_source"),
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"], ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_operational_doc_requirement_shipment_org", ondelete="RESTRICT"),
        db.CheckConstraint("requirement_level IN ('REQUIRED','OPTIONAL','CONDITIONAL')", name="ck_operational_doc_requirement_level"),
        db.CheckConstraint("applicability_state IN ('APPLICABLE','NOT_APPLICABLE','UNRESOLVED')", name="ck_operational_doc_requirement_applicability"),
        db.CheckConstraint("required_assessment_level IN ('APPROVED','VERIFIED')", name="ck_operational_doc_requirement_assessment"),
        db.CheckConstraint("version >= 1", name="ck_operational_doc_requirement_version"),
        db.Index("ix_operational_doc_requirement_readiness", "organization_id", "operational_shipment_id", "target_milestone_type", "target_status", "is_active"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    document_definition_id = db.Column(BIGINT, db.ForeignKey("document_definition.id", ondelete="RESTRICT"), nullable=False)
    source_project_requirement_id = db.Column(BIGINT, db.ForeignKey("project_document_requirement.id", ondelete="RESTRICT"), nullable=True)
    source_project_requirement_public_id = db.Column(db.String(36), nullable=True)
    source_project_requirement_version = db.Column(db.Integer, nullable=True)
    source_organization_policy_id = db.Column(BIGINT, db.ForeignKey("organization_document_requirement.id", ondelete="RESTRICT"), nullable=True)
    requirement_level = db.Column(db.String(16), nullable=False)
    applicability_state = db.Column(db.String(20), nullable=False)
    required_assessment_level = db.Column(db.String(16), nullable=False, default="APPROVED")
    target_milestone_type = db.Column(db.String(64), nullable=True)
    target_status = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    definition = db.relationship("DocumentDefinition")


class ArtifactAssociation(db.Model):
    __tablename__ = "operational_artifact_association"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_operational_artifact_assoc_public_id"),
        db.CheckConstraint("state IN ('ACTIVE','SUPERSEDED')", name="ck_operational_artifact_assoc_state"),
        db.Index("ix_operational_artifact_assoc_active", "requirement_id", "state"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    requirement_id = db.Column(BIGINT, db.ForeignKey("operational_document_requirement.id", ondelete="RESTRICT"), nullable=False)
    document_file_id = db.Column(BIGINT, db.ForeignKey("case_document_file.id", ondelete="RESTRICT"), nullable=False)
    artifact_version = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String(16), nullable=False, default="ACTIVE")
    reason = db.Column(db.Text)
    associated_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    associated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    superseded_at = db.Column(db.DateTime(timezone=True))
    artifact = db.relationship("CaseDocumentFile")


class DocumentAssessment(db.Model):
    __tablename__ = "operational_document_assessment"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_operational_doc_assessment_public_id"),
        db.CheckConstraint("decision IN ('REVIEW_STARTED','APPROVED','REJECTED','VERIFIED')", name="ck_operational_doc_assessment_decision"),
        db.Index("ix_operational_doc_assessment_projection", "association_id", "created_at", "id"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    association_id = db.Column(BIGINT, db.ForeignKey("operational_artifact_association.id", ondelete="RESTRICT"), nullable=False)
    decision = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class RequirementApplicabilityDecision(db.Model):
    __tablename__ = "operational_requirement_applicability"
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    requirement_id = db.Column(BIGINT, db.ForeignKey("operational_document_requirement.id", ondelete="RESTRICT"), nullable=False, index=True)
    decision = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class TransitionOverride(db.Model):
    __tablename__ = "operational_transition_override"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_operational_transition_override_public_id"),
        db.CheckConstraint("state IN ('ACTIVE','REVOKED','CONSUMED','EXPIRED')", name="ck_operational_transition_override_state"),
        db.Index("ix_operational_transition_override_lookup", "organization_id", "operational_shipment_id", "requirement_id", "milestone_id", "target_status", "state"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="RESTRICT"), nullable=False)
    requirement_id = db.Column(BIGINT, db.ForeignKey("operational_document_requirement.id", ondelete="RESTRICT"), nullable=False)
    milestone_id = db.Column(BIGINT, db.ForeignKey("operational_milestone.id", ondelete="RESTRICT"), nullable=False)
    target_status = db.Column(db.String(20), nullable=False)
    authority = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    evidence_reference = db.Column(db.String(500))
    state = db.Column(db.String(16), nullable=False, default="ACTIVE")
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True))
    revoked_at = db.Column(db.DateTime(timezone=True))
    revoked_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"))
    consumed_at = db.Column(db.DateTime(timezone=True))


class DocumentReadinessAudit(db.Model):
    __tablename__ = "document_readiness_audit"
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False, index=True)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    requirement_id = db.Column(BIGINT, db.ForeignKey("operational_document_requirement.id", ondelete="RESTRICT"))
    milestone_id = db.Column(BIGINT, db.ForeignKey("operational_milestone.id", ondelete="RESTRICT"))
    correlation_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    evidence = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
