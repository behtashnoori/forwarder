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


project_party_relationship = db.Table(
    "project_party_relationship",
    db.Column(
        "project_id",
        BIGINT,
        db.ForeignKey("project.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "customer_id",
        BIGINT,
        db.ForeignKey("customer.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    db.Column("party_role", db.String(32), primary_key=True),
    db.Column("source", db.String(64), nullable=False),
    db.Column("valid_from", db.DateTime(timezone=True), nullable=False, default=utcnow),
    db.Column("valid_until", db.DateTime(timezone=True), nullable=True),
    db.CheckConstraint(
        "party_role IN ('payer','consignee','cargo_owner','notify_party','other')",
        name="ck_project_party_relationship_role",
    ),
    db.CheckConstraint(
        "valid_until IS NULL OR valid_until >= valid_from",
        name="ck_project_party_relationship_validity",
    ),
)


class Project(db.Model):
    """Business coordination boundary; Slice-001 exposes no Project workflow."""

    __tablename__ = "project"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_project_public_id"),
        db.UniqueConstraint(
            "organization_id", "project_code", name="uq_project_org_code"
        ),
        db.UniqueConstraint("id", "organization_id", name="uq_project_id_org"),
        db.CheckConstraint(
            "lifecycle_status IN "
            "('not_started','in_progress','partially_delivered','completed','cancelled')",
            name="ck_project_lifecycle_status",
        ),
        db.CheckConstraint("version >= 1", name="ck_project_version_positive"),
        db.Index("ix_project_org_customer", "organization_id", "primary_customer_id"),
    )

    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, default=lambda: str(uuid.uuid4())
    )
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    primary_customer_id = db.Column(
        BIGINT, db.ForeignKey("customer.id", ondelete="RESTRICT"), nullable=False
    )
    project_code = db.Column(db.String(64), nullable=False)
    lifecycle_status = db.Column(
        db.String(24), nullable=False, default="not_started"
    )
    version = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    shipment_requests = db.relationship(
        "ShipmentRequest", back_populates="project", lazy="selectin"
    )


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
        db.UniqueConstraint("id", "organization_id", name="uq_operational_shipment_id_org"),
        db.ForeignKeyConstraint(
            ["project_id", "organization_id"],
            ["project.id", "project.organization_id"],
            name="fk_operational_shipment_project_same_org",
            ondelete="RESTRICT",
        ),
        db.CheckConstraint("lifecycle_status IN ('planned','in_progress','completed','cancelled')", name="ck_operational_shipment_status"),
        db.Index("ix_operational_shipment_org_status", "organization_id", "lifecycle_status"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    project_id = db.Column(BIGINT, nullable=True, index=True)
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
        db.UniqueConstraint("id", "operational_shipment_id", name="uq_route_plan_id_shipment"),
        db.CheckConstraint("status IN ('draft','active','superseded','cancelled')", name="ck_route_plan_status"),
        db.Index("uq_route_plan_one_active", "operational_shipment_id", unique=True, postgresql_where=db.text("is_active"), sqlite_where=db.text("is_active = 1")),
    )
    id = db.Column(BIGINT, primary_key=True)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number = db.Column("revision", db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="active")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_from_plan_id = db.Column(BIGINT, db.ForeignKey("route_plan.id", ondelete="RESTRICT"), nullable=True)
    replan_reason = db.Column(db.Text, nullable=True)
    effective_at = db.Column(db.DateTime(timezone=True), nullable=True)
    timeline_reconciled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    @property
    def revision(self):
        return self.revision_number

    @revision.setter
    def revision(self, value):
        self.revision_number = value


class RouteLeg(db.Model):
    __tablename__ = "route_leg"
    __table_args__ = (
        db.UniqueConstraint("route_plan_id", "sequence_number", name="uq_route_leg_plan_sequence"),
        db.UniqueConstraint("id", "route_plan_id", name="uq_route_leg_id_plan"),
        db.CheckConstraint("sequence_number >= 1", name="ck_route_leg_sequence_positive"),
        db.CheckConstraint("origin_location_id <> destination_location_id", name="ck_route_leg_distinct_locations"),
        db.CheckConstraint("planned_arrival >= planned_departure", name="ck_route_leg_timeline"),
        db.CheckConstraint("status IN ('planned','ready','in_progress','completed','blocked','cancelled')", name="ck_route_leg_status"),
    )
    id = db.Column(BIGINT, primary_key=True)
    source_route_leg_id = db.Column(BIGINT, db.ForeignKey("route_leg.id", ondelete="RESTRICT"), nullable=True)
    route_plan_id = db.Column(BIGINT, db.ForeignKey("route_plan.id", ondelete="CASCADE"), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    origin_location_id = db.Column(BIGINT, db.ForeignKey("canonical_location.id", ondelete="RESTRICT"), nullable=False)
    destination_location_id = db.Column(BIGINT, db.ForeignKey("canonical_location.id", ondelete="RESTRICT"), nullable=False)
    origin_snapshot = db.Column(db.JSON, nullable=False)
    destination_snapshot = db.Column(db.JSON, nullable=False)
    transport_mode = db.Column(db.String(32), nullable=False)
    carrier_reference = db.Column(db.String(120), nullable=True)
    planned_departure = db.Column(db.DateTime(timezone=True), nullable=False)
    planned_arrival = db.Column(db.DateTime(timezone=True), nullable=False)
    projected_departure = db.Column(db.DateTime(timezone=True), nullable=True)
    projected_arrival = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_departure = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_arrival = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="planned")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Milestone(db.Model):
    __tablename__ = "operational_milestone"
    __table_args__ = (
        db.UniqueConstraint("route_leg_id", "milestone_type", name="uq_operational_milestone_leg_type"),
        db.UniqueConstraint("id", "route_plan_id", name="uq_operational_milestone_id_plan"),
        db.CheckConstraint("milestone_type IN ('departure','arrival','checkpoint_arrival','checkpoint_processing_complete','checkpoint_departure')", name="ck_operational_milestone_type"),
        db.CheckConstraint("verification_state IN ('planned','reported','verified')", name="ck_operational_milestone_verification"),
        db.CheckConstraint("(route_leg_id IS NOT NULL AND checkpoint_id IS NULL) OR (route_leg_id IS NULL AND checkpoint_id IS NOT NULL)", name="ck_operational_milestone_single_owner"),
        db.ForeignKeyConstraint(["checkpoint_id", "route_plan_id"], ["operational_checkpoint.id", "operational_checkpoint.route_plan_id"], name="fk_milestone_checkpoint_same_plan", ondelete="CASCADE"),
    )
    id = db.Column(BIGINT, primary_key=True)
    route_plan_id = db.Column(BIGINT, db.ForeignKey("route_plan.id", ondelete="CASCADE"), nullable=True)
    route_leg_id = db.Column(BIGINT, db.ForeignKey("route_leg.id", ondelete="CASCADE"), nullable=True, index=True)
    checkpoint_id = db.Column(BIGINT, nullable=True, index=True)
    source_milestone_id = db.Column(BIGINT, db.ForeignKey("operational_milestone.id", ondelete="RESTRICT"), nullable=True)
    milestone_type = db.Column(db.String(40), nullable=False)
    planned_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    projected_at = db.Column(db.DateTime(timezone=True), nullable=True)
    projected_state = db.Column(db.String(20), nullable=False, default="planned")
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=True)
    verification_state = db.Column(db.String(20), nullable=False, default="planned")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class OperationalCheckpoint(db.Model):
    __tablename__ = "operational_checkpoint"
    __table_args__ = (
        db.UniqueConstraint("route_plan_id", "sequence_number", name="uq_operational_checkpoint_plan_sequence"),
        db.UniqueConstraint("id", "route_plan_id", name="uq_operational_checkpoint_id_plan"),
        db.CheckConstraint("sequence_number >= 1", name="ck_operational_checkpoint_sequence_positive"),
        db.CheckConstraint("planned_departure_at IS NULL OR planned_arrival_at IS NULL OR planned_departure_at >= planned_arrival_at", name="ck_operational_checkpoint_planned_timeline"),
        db.CheckConstraint("actual_departure_at IS NULL OR actual_arrival_at IS NOT NULL", name="ck_operational_checkpoint_actual_timeline"),
        db.CheckConstraint("status IN ('planned','approaching','arrived','processing','ready_to_depart','departed','completed','blocked','cancelled')", name="ck_operational_checkpoint_status"),
        db.CheckConstraint("checkpoint_type IN ('origin_loading','export_customs','border_exit','transit_border_entry','transit_border_exit','border_entry','import_customs','port_entry','port_exit','terminal_arrival','transshipment','destination_arrival','unloading','final_delivery')", name="ck_operational_checkpoint_type"),
        db.CheckConstraint("verification_state IN ('planned','reported','verified')", name="ck_operational_checkpoint_verification"),
        db.ForeignKeyConstraint(["route_leg_id", "route_plan_id"], ["route_leg.id", "route_leg.route_plan_id"], name="fk_checkpoint_leg_same_plan", ondelete="RESTRICT"),
        db.Index("ix_operational_checkpoint_plan_status", "route_plan_id", "status"),
    )
    id = db.Column(BIGINT, primary_key=True)
    source_checkpoint_id = db.Column(BIGINT, db.ForeignKey("operational_checkpoint.id", ondelete="RESTRICT"), nullable=True)
    route_plan_id = db.Column(BIGINT, db.ForeignKey("route_plan.id", ondelete="CASCADE"), nullable=False)
    route_leg_id = db.Column(BIGINT, db.ForeignKey("route_leg.id", ondelete="RESTRICT"), nullable=True)
    sequence_number = db.Column(db.Integer, nullable=False)
    checkpoint_type = db.Column(db.String(40), nullable=False)
    canonical_location_id = db.Column(BIGINT, db.ForeignKey("canonical_location.id", ondelete="RESTRICT"), nullable=False)
    planned_arrival_at = db.Column(db.DateTime(timezone=True), nullable=True)
    planned_departure_at = db.Column(db.DateTime(timezone=True), nullable=True)
    projected_arrival_at = db.Column(db.DateTime(timezone=True), nullable=True)
    projected_departure_at = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_arrival_at = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_departure_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(24), nullable=False, default="planned")
    verification_state = db.Column(db.String(20), nullable=False, default="planned")
    responsible_party = db.Column(db.String(160), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class RouteDependency(db.Model):
    __tablename__ = "route_dependency"
    __table_args__ = (
        db.UniqueConstraint("route_plan_id", "predecessor_checkpoint_id", "successor_checkpoint_id", "dependency_type", name="uq_route_dependency_edge"),
        db.CheckConstraint("predecessor_checkpoint_id <> successor_checkpoint_id", name="ck_route_dependency_no_self_reference"),
        db.CheckConstraint("dependency_type IN ('finish_to_start','arrival_before_departure','previous_leg_arrival_before_next_leg_departure','customs_clearance_before_border_exit','unloading_before_final_delivery')", name="ck_route_dependency_type"),
        db.ForeignKeyConstraint(["predecessor_checkpoint_id", "route_plan_id"], ["operational_checkpoint.id", "operational_checkpoint.route_plan_id"], name="fk_dependency_predecessor_same_plan", ondelete="CASCADE"),
        db.ForeignKeyConstraint(["successor_checkpoint_id", "route_plan_id"], ["operational_checkpoint.id", "operational_checkpoint.route_plan_id"], name="fk_dependency_successor_same_plan", ondelete="CASCADE"),
    )
    id = db.Column(BIGINT, primary_key=True)
    route_plan_id = db.Column(BIGINT, db.ForeignKey("route_plan.id", ondelete="CASCADE"), nullable=False)
    predecessor_checkpoint_id = db.Column(BIGINT, db.ForeignKey("operational_checkpoint.id", ondelete="CASCADE"), nullable=False)
    successor_checkpoint_id = db.Column(BIGINT, db.ForeignKey("operational_checkpoint.id", ondelete="CASCADE"), nullable=False)
    dependency_type = db.Column(db.String(60), nullable=False, default="finish_to_start")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


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
        db.CheckConstraint("work_type IN ('OVERDUE_MILESTONE','CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED')", name="ck_operational_work_item_type"),
        db.CheckConstraint("status IN ('open','resolved')", name="ck_operational_work_item_status"),
        db.CheckConstraint(
            "resolution_source IS NULL OR resolution_source IN ('automatic','manual','supersession')",
            name="ck_route_exception_resolution_source",
        ),
        db.CheckConstraint(
            "(work_type = 'OVERDUE_MILESTONE' AND milestone_id IS NOT NULL AND route_plan_id IS NULL AND checkpoint_id IS NULL) "
            "OR (work_type IN ('CHECKPOINT_OVERDUE','ROUTE_DEPENDENCY_BLOCKED','REPLAN_REQUIRED') "
            "AND milestone_id IS NULL AND route_plan_id IS NOT NULL AND checkpoint_id IS NOT NULL)",
            name="ck_operational_work_item_owner_scope",
        ),
        db.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_work_item_shipment_same_org",
            ondelete="CASCADE",
        ),
        db.ForeignKeyConstraint(
            ["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"],
            name="fk_work_item_plan_same_shipment",
            ondelete="CASCADE",
        ),
        db.ForeignKeyConstraint(
            ["checkpoint_id", "route_plan_id"],
            ["operational_checkpoint.id", "operational_checkpoint.route_plan_id"],
            name="fk_work_item_checkpoint_same_plan",
            ondelete="CASCADE",
        ),
        db.Index("uq_operational_work_item_open", "milestone_id", "work_type", unique=True, postgresql_where=db.text("status = 'open'"), sqlite_where=db.text("status = 'open'")),
        db.Index("ix_operational_work_item_queue", "organization_id", "work_type", "status", "due_at"),
        db.Index("uq_route_exception_open", "route_plan_id", "checkpoint_id", "work_type", unique=True, postgresql_where=db.text("status = 'open' AND route_plan_id IS NOT NULL"), sqlite_where=db.text("status = 'open' AND route_plan_id IS NOT NULL")),
    )
    id = db.Column(BIGINT, primary_key=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id = db.Column(BIGINT, db.ForeignKey("operational_milestone.id", ondelete="CASCADE"), nullable=True)
    route_plan_id = db.Column(BIGINT, db.ForeignKey("route_plan.id", ondelete="CASCADE"), nullable=True)
    checkpoint_id = db.Column(BIGINT, db.ForeignKey("operational_checkpoint.id", ondelete="CASCADE"), nullable=True)
    severity = db.Column(db.String(16), nullable=False, default="warning")
    detected_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    resolution_reason = db.Column(db.Text, nullable=True)
    resolution_source = db.Column(db.String(20), nullable=True)
    occurrence_count = db.Column(db.Integer, nullable=False, default=1)
    last_reconciled_at = db.Column(db.DateTime(timezone=True), nullable=True)
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
        db.UniqueConstraint("organization_id", "operation", "resource_type", "command_resource_id", "idempotency_key", name="uq_operational_idempotency_scope"),
    )
    id = db.Column(BIGINT, primary_key=True)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="CASCADE"), nullable=False)
    operation = db.Column(db.String(60), nullable=False)
    resource_type = db.Column(db.String(40), nullable=False, default="organization")
    command_resource_id = db.Column(BIGINT, nullable=False, default=0)
    idempotency_key = db.Column(db.String(100), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    result_resource_id = db.Column("resource_id", BIGINT, nullable=True)
    response_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


ALL_OPERATIONAL_MODELS = [
    OperationalOrganization, Project, OperationalMembership, CanonicalLocation,
    OperationalShipment, RoutePlan, RouteLeg, OperationalCheckpoint,
    RouteDependency, Milestone, MilestoneEvent,
    OperationalWorkItem, OperationalAudit, OperationalOutbox,
    OperationalIdempotency,
]
