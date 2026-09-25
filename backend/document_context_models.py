"""P3-06 typed, exact-version document context and audience facts.

CaseDocumentFile remains the physical-file/version authority.  These rows
describe the operational use and visibility of one exact file version.
"""
from uuid import uuid4

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class OperationalDocumentContext(db.Model):
    __tablename__ = "operational_document_context"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_operational_document_context_public_id"),
        db.UniqueConstraint("document_file_id", name="uq_operational_document_context_file"),
        db.ForeignKeyConstraint(
            ["operational_shipment_id", "organization_id"],
            ["operational_shipment.id", "operational_shipment.organization_id"],
            name="fk_operational_document_context_shipment_org", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["document_file_id", "operational_shipment_id", "organization_id"],
            ["case_document_file.id", "case_document_file.operational_shipment_id",
             "case_document_file.operational_organization_id"],
            name="fk_operational_document_context_file_parent", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["cargo_item_id", "operational_shipment_id"],
            ["shipment_cargo_item.id", "shipment_cargo_item.operational_shipment_id"],
            name="fk_operational_document_context_cargo_parent", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["execution_unit_id", "organization_id"],
            ["execution_unit.id", "execution_unit.organization_id"],
            name="fk_operational_document_context_execution_org", ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["delivery_id", "operational_shipment_id", "organization_id"],
            ["cargo_delivery.id", "cargo_delivery.operational_shipment_id", "cargo_delivery.organization_id"],
            name="fk_document_context_delivery_parent", ondelete="RESTRICT",
        ),
        db.CheckConstraint(
            "context_type IN ('SHIPMENT','CARGO','ROUTE_LEG','EXECUTION_UNIT','DELIVERY')",
            name="ck_operational_document_context_type",
        ),
        db.CheckConstraint(
            "visibility IN ('INTERNAL','CARGO_OWNER','EXPLICIT_SHARED')",
            name="ck_operational_document_context_visibility",
        ),
        db.CheckConstraint(
            "(context_type = 'SHIPMENT' AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL AND delivery_id IS NULL) OR "
            "(context_type = 'CARGO' AND cargo_item_id IS NOT NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL AND delivery_id IS NULL) OR "
            "(context_type = 'ROUTE_LEG' AND cargo_item_id IS NULL AND route_leg_id IS NOT NULL AND execution_unit_id IS NULL AND delivery_id IS NULL) OR "
            "(context_type = 'EXECUTION_UNIT' AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NOT NULL AND delivery_id IS NULL) OR "
            "(context_type = 'DELIVERY' AND cargo_item_id IS NULL AND route_leg_id IS NULL AND execution_unit_id IS NULL AND delivery_id IS NOT NULL)",
            name="ck_operational_document_context_one_target",
        ),
        db.CheckConstraint(
            "visibility <> 'CARGO_OWNER' OR context_type IN ('CARGO','DELIVERY')",
            name="ck_operational_document_cargo_owner_scope",
        ),
        db.Index("ix_operational_document_context_parent", "organization_id", "operational_shipment_id", "context_type"),
    )

    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="RESTRICT"), nullable=False)
    document_file_id = db.Column(BIGINT, db.ForeignKey("case_document_file.id", ondelete="RESTRICT"), nullable=False)
    context_type = db.Column(db.String(20), nullable=False)
    cargo_item_id = db.Column(BIGINT, db.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT"))
    route_leg_id = db.Column(BIGINT, db.ForeignKey("route_leg.id", ondelete="RESTRICT"))
    execution_unit_id = db.Column(BIGINT, db.ForeignKey("execution_unit.id", ondelete="RESTRICT"))
    delivery_id = db.Column(BIGINT)
    visibility = db.Column(db.String(20), nullable=False, default="INTERNAL")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class OperationalDocumentAudience(db.Model):
    __tablename__ = "operational_document_audience"
    __table_args__ = (
        db.UniqueConstraint("context_id", "customer_portal_account_id", name="uq_operational_document_audience_account"),
        db.Index("ix_operational_document_audience_account", "customer_portal_account_id", "context_id"),
    )

    id = db.Column(BIGINT, primary_key=True)
    context_id = db.Column(BIGINT, db.ForeignKey("operational_document_context.id", ondelete="RESTRICT"), nullable=False)
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    customer_portal_account_id = db.Column(BIGINT, db.ForeignKey("customer_gamification.id", ondelete="RESTRICT"), nullable=False)
    created_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OperationalDocumentContextEvent(db.Model):
    """Append-only before/after fact; JSON here is audit, never permission SOR."""

    __tablename__ = "operational_document_context_event"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_operational_document_context_event_public_id"),
        db.Index("ix_operational_document_context_event_history", "context_id", "recorded_at", "id"),
    )

    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    context_id = db.Column(BIGINT, db.ForeignKey("operational_document_context.id", ondelete="RESTRICT"), nullable=False)
    document_file_id = db.Column(BIGINT, db.ForeignKey("case_document_file.id", ondelete="RESTRICT"), nullable=False)
    action = db.Column(db.String(24), nullable=False)
    before_fact = db.Column(db.JSON)
    after_fact = db.Column(db.JSON, nullable=False)
    actor_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    reason = db.Column(db.String(500))
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
