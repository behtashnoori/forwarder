"""Immutable receipts for the one exceptional Shipment owner command (ADR-069)."""
from sqlalchemy import event
from backend.extensions import db
from backend.operational_models import BIGINT


class ShipmentOwnerTransfer(db.Model):
    __tablename__ = "shipment_owner_transfer"
    __table_args__ = (
        db.ForeignKeyConstraint(["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_owner_transfer_shipment", ondelete="RESTRICT"),
        db.UniqueConstraint("id", "operational_shipment_id", "organization_id", name="uq_owner_transfer_parent"),
        db.ForeignKeyConstraint(["previous_transfer_id", "operational_shipment_id", "organization_id"],
            ["shipment_owner_transfer.id", "shipment_owner_transfer.operational_shipment_id", "shipment_owner_transfer.organization_id"],
            name="fk_owner_transfer_predecessor", ondelete="RESTRICT"),
        db.UniqueConstraint("operational_shipment_id", "sequence_number", name="uq_owner_transfer_sequence"),
        db.UniqueConstraint("operational_shipment_id", "next_shipment_version", name="uq_owner_transfer_version"),
        db.UniqueConstraint("operational_shipment_id", "idempotency_key", name="uq_owner_transfer_command"),
        db.CheckConstraint("old_owner_id != new_owner_id", name="ck_owner_transfer_changed"),
        db.CheckConstraint("previous_shipment_version >= 1 AND next_shipment_version = previous_shipment_version + 1", name="ck_owner_transfer_version"),
        db.CheckConstraint("sequence_number >= 1 AND ((sequence_number = 1 AND previous_transfer_id IS NULL) OR (sequence_number > 1 AND previous_transfer_id IS NOT NULL))", name="ck_owner_transfer_chain"),
        db.CheckConstraint("length(trim(reason)) > 0 AND length(reason) <= 1000", name="ck_owner_transfer_reason"),
        db.CheckConstraint("length(trim(idempotency_key)) > 0 AND length(idempotency_key) <= 100", name="ck_owner_transfer_key"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True)
    organization_id = db.Column(BIGINT, nullable=False)
    operational_shipment_id = db.Column(BIGINT, nullable=False)
    old_owner_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    new_owner_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    old_owner_label = db.Column(db.String(100), nullable=False)
    new_owner_label = db.Column(db.String(100), nullable=False)
    actor_label = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.String(1000), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    previous_shipment_version = db.Column(db.Integer, nullable=False)
    next_shipment_version = db.Column(db.Integer, nullable=False)
    previous_transfer_id = db.Column(BIGINT, nullable=True)
    idempotency_key = db.Column(db.String(100), nullable=False)


@event.listens_for(ShipmentOwnerTransfer, "before_insert")
@event.listens_for(ShipmentOwnerTransfer, "before_update")
@event.listens_for(ShipmentOwnerTransfer, "before_delete")
def _only_dedicated_command(_mapper, _connection, _target):
    raise ValueError("Owner transfer history is immutable; use the dedicated transfer command")
