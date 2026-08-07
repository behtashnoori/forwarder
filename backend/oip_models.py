"""OIP-2 durable derived-intelligence models. Operational truth stays elsewhere."""
from __future__ import annotations

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


SITUATION_TYPES = (
    "NEXT_MILESTONE_OVERDUE", "CHECKPOINT_OVERDUE", "ROUTE_DEPENDENCY_BLOCKED",
    "REPLAN_REQUIRED", "DOCUMENT_READINESS_BLOCKED", "ACTIVE_DELAY_OR_EXCEPTION",
    "EXECUTION_UNIT_STALE",
)
SITUATION_STATUSES = ("OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "SNOOZED", "RESOLVED", "DISMISSED", "EXPIRED")


class OipSituation(db.Model):
    __tablename__ = "oip_situation"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "identity_key", name="uq_oip_situation_identity"),
        db.CheckConstraint("occurrence_count >= 1", name="ck_oip_situation_occurrence"),
        db.CheckConstraint("version >= 1", name="ck_oip_situation_version"),
        db.Index("ix_oip_attention_queue", "organization_id", "status", "priority", "due_at"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    identity_key = db.Column(db.String(64), nullable=False)
    situation_type = db.Column(db.String(48), nullable=False)
    subject_type = db.Column(db.String(32), nullable=False)
    subject_public_id = db.Column(db.String(64), nullable=False)
    identity_dimensions = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="OPEN")
    severity = db.Column(db.String(16), nullable=False)
    urgency = db.Column(db.String(16), nullable=False)
    priority = db.Column(db.String(16), nullable=False)
    priority_explanation = db.Column(db.JSON, nullable=False)
    first_detected_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_detected_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    due_at = db.Column(db.DateTime(timezone=True))
    assignee_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"))
    occurrence_count = db.Column(db.Integer, nullable=False, default=1)
    policy_id = db.Column(db.String(40), nullable=False)
    policy_version = db.Column(db.String(32), nullable=False)
    projection_version = db.Column(db.String(32), nullable=False)
    calculated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    source_watermark = db.Column(db.String(160), nullable=False)
    freshness_status = db.Column(db.String(16), nullable=False)
    freshness_reason = db.Column(db.String(200))
    snoozed_until = db.Column(db.DateTime(timezone=True))
    disposition_reason = db.Column(db.Text)
    acknowledged_at = db.Column(db.DateTime(timezone=True))
    intervention_started_at = db.Column(db.DateTime(timezone=True))
    resolved_at = db.Column(db.DateTime(timezone=True))
    version = db.Column(db.Integer, nullable=False, default=1)


class OipFactReference(db.Model):
    __tablename__ = "oip_fact_reference"
    __table_args__ = (db.UniqueConstraint("organization_id", "source_domain", "source_type", "source_public_id", "source_version", name="uq_oip_fact_version"),)
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    source_domain = db.Column(db.String(40), nullable=False)
    source_type = db.Column(db.String(48), nullable=False)
    source_public_id = db.Column(db.String(64), nullable=False)
    subject_type = db.Column(db.String(32), nullable=False)
    subject_public_id = db.Column(db.String(64), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True))
    source_version = db.Column(db.String(80), nullable=False)
    correlation_id = db.Column(db.String(100))
    evidence_reference = db.Column(db.JSON, nullable=False)
    validity = db.Column(db.String(16), nullable=False, default="CURRENT")
    superseded_by_public_id = db.Column(db.String(36))
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OipSignal(db.Model):
    __tablename__ = "oip_signal"
    __table_args__ = (db.UniqueConstraint("organization_id", "dedup_key", "source_watermark", name="uq_oip_signal_observation"),)
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    signal_type = db.Column(db.String(48), nullable=False)
    policy_id = db.Column(db.String(40), nullable=False)
    policy_version = db.Column(db.String(32), nullable=False)
    subject_type = db.Column(db.String(32), nullable=False)
    subject_public_id = db.Column(db.String(64), nullable=False)
    dedup_key = db.Column(db.String(64), nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    derivation = db.Column(db.JSON, nullable=False)
    observed_at = db.Column(db.DateTime(timezone=True), nullable=False)
    source_watermark = db.Column(db.String(160), nullable=False)


class OipSituationEvidence(db.Model):
    __tablename__ = "oip_situation_evidence"
    situation_id = db.Column(BIGINT, db.ForeignKey("oip_situation.id", ondelete="CASCADE"), primary_key=True)
    fact_reference_id = db.Column(BIGINT, db.ForeignKey("oip_fact_reference.id", ondelete="RESTRICT"), primary_key=True)
    signal_id = db.Column(BIGINT, db.ForeignKey("oip_signal.id", ondelete="RESTRICT"), primary_key=True)
    is_current = db.Column(db.Boolean, nullable=False, default=True)
    linked_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OipSituationHistory(db.Model):
    __tablename__ = "oip_situation_history"
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    situation_id = db.Column(BIGINT, db.ForeignKey("oip_situation.id", ondelete="RESTRICT"), nullable=False)
    event_type = db.Column(db.String(32), nullable=False)
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"))
    reason = db.Column(db.Text)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OipAttentionProjection(db.Model):
    __tablename__ = "oip_attention_projection"
    situation_id = db.Column(BIGINT, db.ForeignKey("oip_situation.id", ondelete="CASCADE"), primary_key=True)
    operational_work_item_id = db.Column(BIGINT, db.ForeignKey("operational_work_item.id", ondelete="SET NULL"), unique=True)
    calculated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    source_watermark = db.Column(db.String(160), nullable=False)
    projection_version = db.Column(db.String(32), nullable=False)


class OipProjectionState(db.Model):
    __tablename__ = "oip_projection_state"
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="CASCADE"), primary_key=True)
    status = db.Column(db.String(16), nullable=False)
    source_watermark = db.Column(db.String(160), nullable=False)
    projection_version = db.Column(db.String(32), nullable=False)
    calculated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_error = db.Column(db.Text)

