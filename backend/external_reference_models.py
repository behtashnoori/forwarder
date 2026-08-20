"""Governed external operational references (ADR-039)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import event, inspect

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


TYPE_CODES = frozenset({"BILL_OF_LADING_NUMBER", "AIR_WAYBILL_NUMBER", "CMR_NUMBER"})
TYPE_LIFECYCLES = frozenset({"DRAFT", "ACTIVE", "DEPRECATED"})
SEARCH_POLICIES = frozenset({"EXACT", "PREFIX", "DISPLAY_ONLY", "NONE"})
UNIQUENESS_SCOPES = frozenset({"NONE", "OWNER", "TENANT", "ISSUER"})
REFERENCE_LIFECYCLES = frozenset({"ACTIVE", "SUPERSEDED", "CANCELLED"})


class ExternalReferenceType(db.Model):
    __tablename__ = "external_reference_type"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_external_reference_type_public_id"),
        db.UniqueConstraint("code", name="uq_external_reference_type_code"),
        db.CheckConstraint(
            "code IN ('BILL_OF_LADING_NUMBER','AIR_WAYBILL_NUMBER','CMR_NUMBER')",
            name="ck_external_reference_type_v1_code",
        ),
        db.CheckConstraint(
            "lifecycle_status IN ('DRAFT','ACTIVE','DEPRECATED')",
            name="ck_external_reference_type_lifecycle",
        ),
        db.CheckConstraint(
            "normalization_policy = 'TRIM_UPPERCASE_V1'",
            name="ck_external_reference_type_normalization",
        ),
        db.CheckConstraint(
            "search_policy IN ('EXACT','PREFIX','DISPLAY_ONLY','NONE')",
            name="ck_external_reference_type_search",
        ),
        db.CheckConstraint(
            "uniqueness_scope IN ('NONE','OWNER','TENANT','ISSUER')",
            name="ck_external_reference_type_uniqueness",
        ),
        db.CheckConstraint(
            "allows_operational_shipment OR allows_execution_unit",
            name="ck_external_reference_type_owner",
        ),
        db.CheckConstraint("revision >= 1", name="ck_external_reference_type_revision"),
        db.CheckConstraint(
            "lifecycle_status <> 'ACTIVE' OR (length(trim(source_authority)) > 0 AND length(trim(provenance_reference)) > 0)",
            name="ck_external_reference_type_active_provenance",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    code = db.Column(db.String(64), nullable=False)
    name_fa = db.Column(db.String(160), nullable=False)
    name_en = db.Column(db.String(160), nullable=False)
    lifecycle_status = db.Column(db.String(16), nullable=False, default="DRAFT")
    normalization_policy = db.Column(
        db.String(32), nullable=False, default="TRIM_UPPERCASE_V1"
    )
    search_policy = db.Column(db.String(16), nullable=False, default="EXACT")
    uniqueness_scope = db.Column(db.String(16), nullable=False, default="OWNER")
    masking_policy = db.Column(db.String(32), nullable=False, default="INTERNAL_FULL")
    source_authority = db.Column(db.String(255), nullable=True)
    provenance_reference = db.Column(db.String(500), nullable=True)
    allows_operational_shipment = db.Column(db.Boolean, nullable=False, default=True)
    allows_execution_unit = db.Column(db.Boolean, nullable=False, default=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by_user_id = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


@event.listens_for(ExternalReferenceType, "before_update")
def _external_reference_type_code_is_immutable(_mapper, _connection, target):
    if inspect(target).attrs.code.history.has_changes():
        raise ValueError("ExternalReferenceType.code is immutable")


class _ReferenceMixin:
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_reference_type_id = db.Column(
        BIGINT,
        db.ForeignKey("external_reference_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    raw_value = db.Column(db.String(255), nullable=False)
    normalized_value = db.Column(db.String(255), nullable=False)
    lifecycle_status = db.Column(db.String(16), nullable=False, default="ACTIVE")
    issuer_key = db.Column(db.String(160), nullable=True)
    source_system = db.Column(db.String(160), nullable=True)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=True)
    supersedes_reference_id = db.Column(BIGINT, nullable=True)
    evidence_document_file_id = db.Column(
        BIGINT,
        db.ForeignKey("case_document_file.id", ondelete="RESTRICT"),
        nullable=True,
    )
    evidence_version = db.Column(db.Integer, nullable=True)
    revision = db.Column(db.Integer, nullable=False, default=1)
    reason = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by_user_id = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class OperationalShipmentExternalReference(_ReferenceMixin, db.Model):
    __tablename__ = "operational_shipment_external_reference"
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    __table_args__ = (
        db.UniqueConstraint(
            "public_id", name="uq_shipment_external_reference_public_id"
        ),
        db.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_shipment_external_reference_owner_org",
            ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["supersedes_reference_id"],
            ["operational_shipment_external_reference.id"],
            name="fk_shipment_external_reference_supersedes",
            ondelete="RESTRICT",
        ),
        db.CheckConstraint(
            "lifecycle_status IN ('ACTIVE','SUPERSEDED','CANCELLED')",
            name="ck_shipment_external_reference_lifecycle",
        ),
        db.CheckConstraint(
            "revision >= 1", name="ck_shipment_external_reference_revision"
        ),
        db.CheckConstraint(
            "(evidence_document_file_id IS NULL AND evidence_version IS NULL) OR (evidence_document_file_id IS NOT NULL AND evidence_version >= 1)",
            name="ck_shipment_external_reference_evidence",
        ),
        db.Index(
            "ix_shipment_external_reference_search",
            "organization_id",
            "external_reference_type_id",
            "normalized_value",
            "lifecycle_status",
        ),
        db.Index(
            "ix_shipment_external_reference_owner",
            "operational_shipment_id",
            "lifecycle_status",
        ),
    )
    reference_type = db.relationship("ExternalReferenceType")


class ExecutionUnitExternalReference(_ReferenceMixin, db.Model):
    __tablename__ = "execution_unit_external_reference"
    execution_unit_id = db.Column(
        BIGINT, db.ForeignKey("execution_unit.id", ondelete="RESTRICT"), nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint(
            "public_id", name="uq_execution_unit_external_reference_public_id"
        ),
        db.ForeignKeyConstraint(
            ["supersedes_reference_id"],
            ["execution_unit_external_reference.id"],
            name="fk_execution_unit_external_reference_supersedes",
            ondelete="RESTRICT",
        ),
        db.CheckConstraint(
            "lifecycle_status IN ('ACTIVE','SUPERSEDED','CANCELLED')",
            name="ck_execution_unit_external_reference_lifecycle",
        ),
        db.CheckConstraint(
            "revision >= 1", name="ck_execution_unit_external_reference_revision"
        ),
        db.CheckConstraint(
            "(evidence_document_file_id IS NULL AND evidence_version IS NULL) OR (evidence_document_file_id IS NOT NULL AND evidence_version >= 1)",
            name="ck_execution_unit_external_reference_evidence",
        ),
        db.Index(
            "ix_execution_unit_external_reference_search",
            "organization_id",
            "external_reference_type_id",
            "normalized_value",
            "lifecycle_status",
        ),
        db.Index(
            "ix_execution_unit_external_reference_owner",
            "execution_unit_id",
            "lifecycle_status",
        ),
    )
    reference_type = db.relationship("ExternalReferenceType")
