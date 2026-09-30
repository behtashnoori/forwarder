"""Versioned Organization Shipment stages and append-only execution facts."""
from uuid import uuid4

from sqlalchemy import event, inspect

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


CANONICAL_STAGE_CODES = (
    "PREPARATION_LOADING",
    "ORIGIN_DEPARTURE",
    "IN_TRANSIT",
    "DESTINATION_ARRIVAL",
    "UNLOADING",
)


class OrganizationShipmentStagePolicy(db.Model):
    __tablename__ = "organization_shipment_stage_policy"
    __table_args__ = (
        db.UniqueConstraint("id", "organization_id", name="uq_org_shipment_stage_policy_org"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OrganizationShipmentStagePolicyVersion(db.Model):
    __tablename__ = "organization_shipment_stage_policy_version"
    __table_args__ = (
        db.UniqueConstraint("id", "organization_id", name="uq_org_shipment_stage_version_org"),
        db.UniqueConstraint("policy_id", "version", name="uq_org_shipment_stage_version_number"),
        db.UniqueConstraint("policy_id", "effective_from", name="uq_org_shipment_stage_version_effective"),
        db.ForeignKeyConstraint(
            ["policy_id", "organization_id"],
            ["organization_shipment_stage_policy.id", "organization_shipment_stage_policy.organization_id"],
            name="fk_org_shipment_stage_version_policy",
            ondelete="RESTRICT",
        ),
        db.CheckConstraint("version >= 1", name="ck_org_shipment_stage_version_positive"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    policy_id = db.Column(BIGINT, nullable=False)
    version = db.Column(db.Integer, nullable=False)
    effective_from = db.Column(db.DateTime(timezone=True), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OrganizationShipmentStageDefinition(db.Model):
    """Stable Organization-owned identity; version rows carry presentation and rules."""
    __tablename__ = "organization_shipment_stage_definition"
    __table_args__ = (
        db.UniqueConstraint("id", "organization_id", name="uq_org_shipment_stage_definition_org"),
        db.UniqueConstraint("organization_id", "code", name="uq_org_shipment_stage_definition_code"),
        db.CheckConstraint(
            "code IN ('PREPARATION_LOADING','ORIGIN_DEPARTURE','IN_TRANSIT','DESTINATION_ARRIVAL','UNLOADING')",
            name="ck_org_shipment_stage_definition_code",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    code = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OrganizationShipmentStageDefinitionVersion(db.Model):
    __tablename__ = "organization_shipment_stage_definition_version"
    __table_args__ = (
        db.UniqueConstraint("id", "policy_version_id", "organization_id", name="uq_org_shipment_stage_item_version_org"),
        db.UniqueConstraint("policy_version_id", "definition_id", name="uq_org_shipment_stage_item_definition"),
        db.UniqueConstraint("policy_version_id", "sequence", name="uq_org_shipment_stage_item_sequence"),
        db.ForeignKeyConstraint(
            ["policy_version_id", "organization_id"],
            ["organization_shipment_stage_policy_version.id", "organization_shipment_stage_policy_version.organization_id"],
            name="fk_org_shipment_stage_item_version",
            ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["definition_id", "organization_id"],
            ["organization_shipment_stage_definition.id", "organization_shipment_stage_definition.organization_id"],
            name="fk_org_shipment_stage_item_definition",
            ondelete="RESTRICT",
        ),
        db.CheckConstraint("sequence >= 1", name="ck_org_shipment_stage_item_sequence"),
        db.CheckConstraint("length(trim(display_name_fa)) > 0", name="ck_org_shipment_stage_item_name"),
        db.CheckConstraint("NOT required_for_completion OR is_active", name="ck_org_shipment_stage_required_active"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    policy_version_id = db.Column(BIGINT, nullable=False)
    definition_id = db.Column(BIGINT, nullable=False)
    display_name_fa = db.Column(db.String(160), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    required_for_completion = db.Column(db.Boolean, nullable=False, default=True)


class ShipmentOperationalStageInstance(db.Model):
    """Pins the exact Organization configuration used by one Shipment."""
    __tablename__ = "shipment_operational_stage_instance"
    __table_args__ = (
        db.UniqueConstraint("id", "policy_version_id", "operational_shipment_id", "organization_id", name="uq_shipment_stage_instance_version_org"),
        db.UniqueConstraint("operational_shipment_id", name="uq_shipment_stage_instance_shipment"),
        db.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_shipment_stage_instance_shipment",
            ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["policy_version_id", "organization_id"],
            ["organization_shipment_stage_policy_version.id", "organization_shipment_stage_policy_version.organization_id"],
            name="fk_shipment_stage_instance_policy_version",
            ondelete="RESTRICT",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    policy_version_id = db.Column(BIGINT, nullable=False)
    pinned_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    pinned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ShipmentOperationalStageEvent(db.Model):
    __tablename__ = "shipment_operational_stage_event"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["instance_id", "policy_version_id", "operational_shipment_id", "organization_id"],
            ["shipment_operational_stage_instance.id", "shipment_operational_stage_instance.policy_version_id", "shipment_operational_stage_instance.operational_shipment_id", "shipment_operational_stage_instance.organization_id"],
            name="fk_shipment_stage_event_instance",
            ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["definition_version_id", "policy_version_id", "organization_id"],
            ["organization_shipment_stage_definition_version.id", "organization_shipment_stage_definition_version.policy_version_id", "organization_shipment_stage_definition_version.organization_id"],
            name="fk_shipment_stage_event_definition_version",
            ondelete="RESTRICT",
        ),
        db.UniqueConstraint("organization_id", "idempotency_key", name="uq_shipment_stage_event_org_idempotency"),
        db.UniqueConstraint("instance_id", "definition_version_id", "event_type", name="uq_shipment_stage_event_transition"),
        db.CheckConstraint("event_type IN ('STARTED','COMPLETED')", name="ck_shipment_stage_event_type"),
        db.Index("ix_shipment_stage_event_history", "operational_shipment_id", "occurred_at", "id"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    instance_id = db.Column(BIGINT, nullable=False)
    policy_version_id = db.Column(BIGINT, nullable=False)
    definition_version_id = db.Column(BIGINT, nullable=False)
    event_type = db.Column(db.String(12), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    idempotency_key = db.Column(db.String(100), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)


def _immutable(_mapper, _connection, target):
    if any(inspect(target).attrs[column.key].history.has_changes() for column in target.__table__.columns):
        raise ValueError("Organization Shipment Stage history is immutable")


def _no_delete(_mapper, _connection, _target):
    raise ValueError("Organization Shipment Stage history cannot be deleted")


for _model in (
    OrganizationShipmentStagePolicy,
    OrganizationShipmentStagePolicyVersion,
    OrganizationShipmentStageDefinition,
    OrganizationShipmentStageDefinitionVersion,
    ShipmentOperationalStageInstance,
    ShipmentOperationalStageEvent,
):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _no_delete)

