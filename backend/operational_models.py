"""Phase 1A operational execution aggregate models."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from backend.extensions import db


BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OperationalOrganization(db.Model):
    __tablename__ = "operational_organization"
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(160), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OperationalMembership(db.Model):
    __tablename__ = "operational_membership"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "user_id", name="uq_operational_membership_org_user"),
    )
    id = db.Column(BIGINT, primary_key=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    permissions = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class CanonicalLocation(db.Model):
    __tablename__ = "canonical_location"
    __table_args__ = (
        db.UniqueConstraint("source_type", "source_id", name="uq_canonical_location_source"),
        db.CheckConstraint("source_type IN ('province','city','country','international_city','iran_port','customs_office')", name="ck_canonical_location_source_type"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    source_type = db.Column(db.String(32), nullable=False)
    source_id = db.Column(BIGINT, nullable=False)
    location_type = db.Column(db.String(32), nullable=False)
    display_name = db.Column(db.String(200), nullable=False)
    country_code = db.Column(db.String(3), nullable=True)
    verification_state = db.Column(db.String(20), nullable=False, default="verified")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OperationalShipment(db.Model):
    __tablename__ = "operational_shipment"
    __table_args__ = (
        db.UniqueConstraint("accepted_quote_id", name="uq_operational_shipment_accepted_quote"),
        db.CheckConstraint("lifecycle_status IN ('planned','in_progress','completed','cancelled')", name="ck_operational_shipment_status"),
        db.Index("ix_operational_shipment_org_status", "organization_id", "lifecycle_status"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    shipment_request_id = db.Column(BIGINT, db.ForeignKey("shipment_request.id", ondelete="RESTRICT"), nullable=False, index=True)
    accepted_quote_id = db.Column(BIGINT, db.ForeignKey("expert_quote.id", ondelete="RESTRICT"), nullable=False)
    lifecycle_status = db.Column(db.String(20), nullable=False, default="planned")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class RoutePlan(db.Model):
    __tablename__ = "route_plan"
    __table_args__ = (
        db.UniqueConstraint("operational_shipment_id", "revision", name="uq_route_plan_shipment_revision"),
        db.Index("uq_route_plan_one_active", "operational_shipment_id", unique=True, postgresql_where=db.text("is_active"), sqlite_where=db.text("is_active = 1")),
    )
    id = db.Column(BIGINT, primary_key=True)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="CASCADE"), nullable=False, index=True)
    revision = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class RouteLeg(db.Model):
    __tablename__ = "route_leg"
    __table_args__ = (
        db.UniqueConstraint("route_plan_id", "sequence_number", name="uq_route_leg_plan_sequence"),
        db.CheckConstraint("sequence_number >= 1", name="ck_route_leg_sequence_positive"),
        db.CheckConstraint("origin_location_id <> destination_location_id", name="ck_route_leg_distinct_locations"),
        db.CheckConstraint("planned_arrival >= planned_departure", name="ck_route_leg_timeline"),
        db.CheckConstraint("status IN ('planned','in_progress','completed','cancelled')", name="ck_route_leg_status"),
    )
    id = db.Column(BIGINT, primary_key=True)
    route_plan_id = db.Column(BIGINT, db.ForeignKey("route_plan.id", ondelete="CASCADE"), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    origin_location_id = db.Column(BIGINT, db.ForeignKey("canonical_location.id", ondelete="RESTRICT"), nullable=False)
    destination_location_id = db.Column(BIGINT, db.ForeignKey("canonical_location.id", ondelete="RESTRICT"), nullable=False)
    origin_snapshot = db.Column(db.JSON, nullable=False)
    destination_snapshot = db.Column(db.JSON, nullable=False)
    transport_mode = db.Column(db.String(32), nullable=False)
    planned_departure = db.Column(db.DateTime(timezone=True), nullable=False)
    planned_arrival = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="planned")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Milestone(db.Model):
    __tablename__ = "operational_milestone"
    __table_args__ = (
        db.UniqueConstraint("route_leg_id", "milestone_type", name="uq_operational_milestone_leg_type"),
        db.CheckConstraint("milestone_type IN ('departure','arrival')", name="ck_operational_milestone_type"),
        db.CheckConstraint("verification_state IN ('planned','reported','verified')", name="ck_operational_milestone_verification"),
    )
    id = db.Column(BIGINT, primary_key=True)
    route_leg_id = db.Column(BIGINT, db.ForeignKey("route_leg.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_type = db.Column(db.String(20), nullable=False)
    planned_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    projected_state = db.Column(db.String(20), nullable=False, default="planned")
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=True)
    verification_state = db.Column(db.String(20), nullable=False, default="planned")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class MilestoneEvent(db.Model):
    __tablename__ = "milestone_event"
    __table_args__ = (
        db.UniqueConstraint("milestone_id", "idempotency_key", name="uq_milestone_event_idempotency"),
        db.CheckConstraint("event_type IN ('reported','verified','corrected')", name="ck_milestone_event_type"),
        db.CheckConstraint("event_type <> 'corrected' OR (reason IS NOT NULL AND length(trim(reason)) > 0 AND supersedes_event_id IS NOT NULL)", name="ck_milestone_event_correction"),
        db.Index("ix_milestone_event_milestone_recorded", "milestone_id", "recorded_at", "id"),
    )
    id = db.Column(BIGINT, primary_key=True)
    milestone_id = db.Column(BIGINT, db.ForeignKey("operational_milestone.id", ondelete="RESTRICT"), nullable=False)
    event_type = db.Column(db.String(20), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    supersedes_event_id = db.Column(BIGINT, db.ForeignKey("milestone_event.id", ondelete="RESTRICT"), nullable=True)
    idempotency_key = db.Column(db.String(100), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)


class OperationalWorkItem(db.Model):
    __tablename__ = "operational_work_item"
    __table_args__ = (
        db.CheckConstraint("work_type IN ('OVERDUE_MILESTONE')", name="ck_operational_work_item_type"),
        db.CheckConstraint("status IN ('open','resolved')", name="ck_operational_work_item_status"),
        db.Index("uq_operational_work_item_open", "milestone_id", "work_type", unique=True, postgresql_where=db.text("status = 'open'"), sqlite_where=db.text("status = 'open'")),
        db.Index("ix_operational_work_item_queue", "organization_id", "work_type", "status", "due_at"),
    )
    id = db.Column(BIGINT, primary_key=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id = db.Column(BIGINT, db.ForeignKey("operational_milestone.id", ondelete="CASCADE"), nullable=False)
    work_type = db.Column(db.String(40), nullable=False, default="OVERDUE_MILESTONE")
    status = db.Column(db.String(20), nullable=False, default="open")
    due_at = db.Column(db.DateTime(timezone=True), nullable=False)
    assignee_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True)
    reason = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OperationalAudit(db.Model):
    __tablename__ = "operational_audit"
    id = db.Column(BIGINT, primary_key=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False, index=True)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(BIGINT, nullable=False)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OperationalOutbox(db.Model):
    __tablename__ = "operational_outbox"
    __table_args__ = (db.Index("ix_operational_outbox_unpublished", "published_at", "created_at"),)
    id = db.Column(BIGINT, primary_key=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    aggregate_type = db.Column(db.String(50), nullable=False)
    aggregate_id = db.Column(BIGINT, nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)


class OperationalIdempotency(db.Model):
    __tablename__ = "operational_idempotency"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "operation", "idempotency_key", name="uq_operational_idempotency_key"),
    )
    id = db.Column(BIGINT, primary_key=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="CASCADE"), nullable=False)
    operation = db.Column(db.String(60), nullable=False)
    idempotency_key = db.Column(db.String(100), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    resource_id = db.Column(BIGINT, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


ALL_OPERATIONAL_MODELS = [
    OperationalOrganization, OperationalMembership, CanonicalLocation,
    OperationalShipment, RoutePlan, RouteLeg, Milestone, MilestoneEvent,
    OperationalWorkItem, OperationalAudit, OperationalOutbox,
    OperationalIdempotency,
]
