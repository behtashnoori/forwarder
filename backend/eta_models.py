"""Derived ETA history. Operational sources remain their own systems of record."""
from uuid import uuid4

from sqlalchemy import event, inspect

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class CargoEtaSnapshot(db.Model):
    __tablename__ = "cargo_eta_snapshot"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_cargo_eta_public"),
        db.UniqueConstraint("id", "organization_id", name="uq_cargo_eta_id_org"),
        db.UniqueConstraint("cargo_item_id", "audience", "sequence", name="uq_cargo_eta_sequence"),
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_cargo_eta_shipment", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["cargo_item_id", "operational_shipment_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"], name="fk_cargo_eta_cargo", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["route_plan_id", "operational_shipment_id"],
            ["route_plan.id", "route_plan.operational_shipment_id"], name="fk_cargo_eta_plan", ondelete="RESTRICT"),
        db.CheckConstraint("audience IN ('INTERNAL','CUSTOMER')", name="ck_cargo_eta_audience"),
        db.CheckConstraint("sequence >= 1", name="ck_cargo_eta_sequence"),
        db.CheckConstraint("ruleset = 'ETA_RULESET_V1'", name="ck_cargo_eta_ruleset"),
        db.Index("ix_cargo_eta_history", "organization_id", "cargo_item_id", "audience", "sequence"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    cargo_item_id = db.Column(BIGINT, nullable=False)
    route_plan_id = db.Column(BIGINT)
    audience = db.Column(db.String(12), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    ruleset = db.Column(db.String(32), nullable=False, default="ETA_RULESET_V1")
    source_fingerprint = db.Column(db.String(64), nullable=False)
    calculated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    # Immutable typed-service output and exact versioned input values, not rules.
    result = db.Column(db.JSON, nullable=False)
    source_basis = db.Column(db.JSON, nullable=False)


class CargoEtaInput(db.Model):
    __tablename__ = "cargo_eta_input"
    __table_args__ = (
        db.ForeignKeyConstraint(["snapshot_id", "organization_id"],
            ["cargo_eta_snapshot.id", "cargo_eta_snapshot.organization_id"], name="fk_eta_input_snapshot", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["reference_version_id", "organization_id"],
            ["organization_route_time_version.id", "organization_route_time_version.organization_id"], name="fk_eta_input_reference", ondelete="RESTRICT"),
        db.CheckConstraint(
            "(CASE WHEN reference_version_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN operational_event_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN milestone_event_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN traversal_id IS NULL THEN 0 ELSE 1 END) = 1", name="ck_eta_input_one_source"),
    )
    id = db.Column(BIGINT, primary_key=True)
    snapshot_id = db.Column(BIGINT, nullable=False)
    organization_id = db.Column(BIGINT, nullable=False)
    reference_version_id = db.Column(BIGINT)
    operational_event_id = db.Column(BIGINT, db.ForeignKey("operational_event.id", ondelete="RESTRICT"))
    milestone_event_id = db.Column(BIGINT, db.ForeignKey("milestone_event.id", ondelete="RESTRICT"))
    traversal_id = db.Column(BIGINT, db.ForeignKey("route_traversal_fact.id", ondelete="RESTRICT"))


def _immutable(_mapper, _connection, target):
    if any(inspect(target).attrs[column.key].history.has_changes() for column in target.__table__.columns):
        raise ValueError("ETA history is immutable; ensure a new snapshot")


def _no_delete(_mapper, _connection, _target):
    raise ValueError("ETA history cannot be deleted")


for _model in (CargoEtaSnapshot, CargoEtaInput):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _no_delete)
