"""Shipment Economics authoritative facts (FE-2 bounded context)."""
from uuid import uuid4

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class EconomicLine(db.Model):
    __tablename__ = "economic_line"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_economic_line_public_id"),
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"], ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_economic_line_shipment_org", ondelete="RESTRICT"),
        db.CheckConstraint("side IN ('REVENUE','COST')", name="ck_economic_line_side"),
        db.CheckConstraint("lifecycle IN ('ACTIVE','CANCELLED')", name="ck_economic_line_lifecycle"),
        db.CheckConstraint("version >= 1", name="ck_economic_line_version"),
        db.CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_economic_line_quantity"),
        db.Index("ix_economic_line_shipment_side", "organization_id", "operational_shipment_id", "side"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    service_type_id = db.Column(BIGINT, db.ForeignKey("service_type.id", ondelete="RESTRICT"), nullable=False)
    side = db.Column(db.String(12), nullable=False)
    counterparty_type = db.Column(db.String(32))
    counterparty_public_id = db.Column(db.String(64))
    quantity = db.Column(db.Numeric(20, 6))
    uom_code = db.Column(db.String(24))
    description = db.Column(db.String(240))
    lifecycle = db.Column(db.String(12), nullable=False, default="ACTIVE")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class EconomicObservation(db.Model):
    __tablename__ = "economic_observation"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_economic_observation_public_id"),
        db.UniqueConstraint("organization_id", "idempotency_key", name="uq_economic_observation_idempotency"),
        db.CheckConstraint("stage IN ('ESTIMATE','COMMITMENT','ACTUAL')", name="ck_economic_observation_stage"),
        db.CheckConstraint("status IN ('AUTHORIZED','SUPERSEDED','REVERSED')", name="ck_economic_observation_status"),
        db.CheckConstraint("correction_type IS NULL OR correction_type IN ('SUPERSESSION','ADJUSTMENT','REVERSAL')", name="ck_economic_observation_correction"),
        db.CheckConstraint("amount >= 0", name="ck_economic_observation_amount"),
        db.CheckConstraint("length(currency)=3 AND currency=upper(currency)", name="ck_economic_observation_currency"),
        db.CheckConstraint("version >= 1", name="ck_economic_observation_version"),
        db.Index("ix_economic_observation_current", "line_id", "stage", "status", "effective_at"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    line_id = db.Column(BIGINT, db.ForeignKey("economic_line.id", ondelete="RESTRICT"), nullable=False)
    stage = db.Column(db.String(12), nullable=False)
    amount = db.Column(db.Numeric(24, 6), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    effective_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    authority = db.Column(db.String(100), nullable=False)
    source_type = db.Column(db.String(40), nullable=False)
    source_public_id = db.Column(db.String(100))
    source_version = db.Column(db.String(64))
    reason = db.Column(db.Text)
    status = db.Column(db.String(16), nullable=False, default="AUTHORIZED")
    correction_type = db.Column(db.String(16))
    corrects_observation_id = db.Column(BIGINT, db.ForeignKey("economic_observation.id", ondelete="RESTRICT"))
    version = db.Column(db.Integer, nullable=False, default=1)
    idempotency_key = db.Column(db.String(100), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    correlation_id = db.Column(db.String(100))
    line = db.relationship("EconomicLine", backref=db.backref("observations", lazy="selectin"))


class EconomicEvidenceAssociation(db.Model):
    __tablename__ = "economic_evidence_association"
    __table_args__ = (db.UniqueConstraint("observation_id", "document_file_id", "artifact_version", name="uq_economic_evidence_exact_version"),)
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    observation_id = db.Column(BIGINT, db.ForeignKey("economic_observation.id", ondelete="RESTRICT"), nullable=False)
    document_file_id = db.Column(BIGINT, db.ForeignKey("case_document_file.id", ondelete="RESTRICT"), nullable=False)
    artifact_public_id = db.Column(db.String(36), nullable=False)
    artifact_version = db.Column(db.Integer, nullable=False)
    evidence_role = db.Column(db.String(40), nullable=False)
    associated_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    associated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    observation = db.relationship("EconomicObservation", backref=db.backref("evidence_associations", lazy="selectin"))


class EconomicFxRate(db.Model):
    __tablename__ = "economic_fx_rate"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_economic_fx_rate_public_id"),
        db.CheckConstraint("rate_type IN ('CONTRACTUAL','MANUAL_APPROVED')", name="ck_economic_fx_rate_type"),
        db.CheckConstraint("status IN ('AUTHORIZED','SUPERSEDED')", name="ck_economic_fx_rate_status"),
        db.CheckConstraint("rate > 0", name="ck_economic_fx_rate_positive"),
        db.CheckConstraint("from_currency <> to_currency", name="ck_economic_fx_rate_pair"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Numeric(24, 12), nullable=False)
    rate_type = db.Column(db.String(24), nullable=False)
    source = db.Column(db.String(120), nullable=False)
    authority = db.Column(db.String(120), nullable=False)
    effective_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True))
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="AUTHORIZED")
    supersedes_rate_id = db.Column(BIGINT, db.ForeignKey("economic_fx_rate.id", ondelete="RESTRICT"))
    version = db.Column(db.Integer, nullable=False, default=1)


class EconomicObservationFx(db.Model):
    """Immutable provenance for the exact FX fact consumed by an observation."""
    __tablename__ = "economic_observation_fx"
    __table_args__ = (
        db.UniqueConstraint("observation_id", name="uq_economic_observation_fx_observation"),
        db.UniqueConstraint("public_id", name="uq_economic_observation_fx_public_id"),
        db.CheckConstraint("rate > 0", name="ck_economic_observation_fx_positive"),
        db.CheckConstraint("from_currency <> to_currency", name="ck_economic_observation_fx_pair"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    observation_id = db.Column(BIGINT, db.ForeignKey("economic_observation.id", ondelete="RESTRICT"), nullable=False)
    fx_rate_id = db.Column(BIGINT, db.ForeignKey("economic_fx_rate.id", ondelete="RESTRICT"), nullable=False)
    fx_rate_public_id = db.Column(db.String(36), nullable=False)
    fx_rate_version = db.Column(db.Integer, nullable=False)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Numeric(24, 12), nullable=False)
    rate_type = db.Column(db.String(24), nullable=False)
    effective_at = db.Column(db.DateTime(timezone=True), nullable=False)
    authority = db.Column(db.String(120), nullable=False)
    source = db.Column(db.String(120), nullable=False)
    bound_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    observation = db.relationship("EconomicObservation", backref=db.backref("fx_binding", uselist=False, lazy="joined"))
    fx_rate = db.relationship("EconomicFxRate")


class EconomicAudit(db.Model):
    __tablename__ = "economic_audit"
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False, index=True)
    operational_shipment_id = db.Column(BIGINT, nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    entity_public_id = db.Column(db.String(36), nullable=False)
    correlation_id = db.Column(db.String(100))
    details = db.Column(db.JSON, nullable=False, default=dict)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
