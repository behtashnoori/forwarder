"""Immutable partial delivery facts and exact-version evidence under ADR-064."""
from uuid import uuid4
from sqlalchemy import event
from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class CargoDelivery(db.Model):
    __tablename__ = "cargo_delivery"
    __table_args__ = (
        db.UniqueConstraint("id", "cargo_item_id", name="uq_delivery_id_cargo"),
        db.UniqueConstraint("id", "operational_shipment_id", "organization_id", name="uq_delivery_id_shipment_org"),
        db.UniqueConstraint("supersedes_delivery_id", name="uq_delivery_successor"),
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"], name="fk_delivery_shipment_org", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["cargo_item_id", "operational_shipment_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"], name="fk_delivery_cargo_shipment", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["cargo_item_id", "uom_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.uom_id"], name="fk_delivery_cargo_uom", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["supersedes_delivery_id", "cargo_item_id"],
            ["cargo_delivery.id", "cargo_delivery.cargo_item_id"], name="fk_delivery_predecessor_cargo", ondelete="RESTRICT"),
        db.CheckConstraint("quantity > 0", name="ck_delivery_positive_quantity"),
        db.CheckConstraint("(supersedes_delivery_id IS NULL AND revision = 1) OR (supersedes_delivery_id IS NOT NULL AND revision > 1)", name="ck_delivery_revision"),
        db.Index("ix_delivery_shipment_history", "operational_shipment_id", "occurred_at", "id"),
        db.Index("ix_delivery_cargo_history", "cargo_item_id", "id"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    cargo_item_id = db.Column(BIGINT, nullable=False)
    quantity = db.Column(db.Numeric(18, 6), nullable=False)
    uom_id = db.Column(BIGINT, db.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"), nullable=False)
    uom_code_snapshot = db.Column(db.String(64), nullable=False)
    uom_symbol_snapshot = db.Column(db.String(32), nullable=False)
    destination_text = db.Column(db.String(255), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    supersedes_delivery_id = db.Column(BIGINT)
    revision = db.Column(db.Integer, nullable=False, default=1)
    reason = db.Column(db.String(500))


class CargoDeliveryEvidence(db.Model):
    __tablename__ = "cargo_delivery_evidence"
    __table_args__ = (
        db.ForeignKeyConstraint(["delivery_id", "operational_shipment_id", "organization_id"],
            ["cargo_delivery.id", "cargo_delivery.operational_shipment_id", "cargo_delivery.organization_id"], name="fk_delivery_evidence_parent", ondelete="RESTRICT"),
        db.ForeignKeyConstraint(["document_file_id", "operational_shipment_id", "organization_id"],
            ["case_document_file.id", "case_document_file.operational_shipment_id", "case_document_file.operational_organization_id"], name="fk_delivery_evidence_file", ondelete="RESTRICT"),
    )
    delivery_id = db.Column(BIGINT, primary_key=True)
    document_file_id = db.Column(BIGINT, primary_key=True)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


def _immutable(_mapper, _connection, _target):
    raise ValueError("Delivery facts and evidence are immutable; append a correction")


for model in (CargoDelivery, CargoDeliveryEvidence):
    event.listen(model, "before_update", _immutable)
    event.listen(model, "before_delete", _immutable)
