"""Organization cargo catalog and immutable shipment cargo snapshots (ADR-022)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import event, inspect

from backend.extensions import db
from backend.operational_models import BIGINT


def utcnow():
    return datetime.now(timezone.utc)


class CargoCatalogItem(db.Model):
    __tablename__ = "cargo_catalog_item"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "immutable_code", name="uq_cargo_catalog_item_org_code"
        ),
        db.UniqueConstraint(
            "id", "organization_id", name="uq_cargo_catalog_item_id_org"
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_cargo_catalog_item_version_positive"
        ),
        db.Index("ix_cargo_catalog_item_org_active", "organization_id", "is_active"),
        db.Index(
            "ix_cargo_catalog_item_org_cargo_type", "organization_id", "cargo_type_id"
        ),
        db.Index("ix_cargo_catalog_item_org_fa_name", "organization_id", "fa_name"),
        db.Index(
            "ix_cargo_catalog_item_org_part_number", "organization_id", "part_number"
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    immutable_code = db.Column(db.String(64), nullable=False)
    fa_name = db.Column(db.String(160), nullable=False)
    en_name = db.Column(db.String(160), nullable=True)
    cargo_type_id = db.Column(
        BIGINT, db.ForeignKey("cargo_type.id", ondelete="RESTRICT"), nullable=False
    )
    default_uom_id = db.Column(
        BIGINT, db.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"), nullable=True
    )
    description = db.Column(db.Text, nullable=True)
    part_number = db.Column(db.String(120), nullable=True)
    customer_item_code = db.Column(db.String(120), nullable=True)
    hs_code = db.Column(db.String(32), nullable=True)
    brand = db.Column(db.String(120), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    search_text = db.Column(db.Text, nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    created_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    cargo_type = db.relationship("CargoType")
    default_uom = db.relationship("UnitOfMeasure")
    aliases = db.relationship(
        "CargoItemAlias", back_populates="catalog_item", lazy="selectin"
    )

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class CargoItemAlias(db.Model):
    __tablename__ = "cargo_item_alias"
    __table_args__ = (
        db.UniqueConstraint(
            "catalog_item_id",
            "normalized_alias",
            name="uq_cargo_item_alias_item_normalized",
        ),
        db.CheckConstraint(
            "language IN ('fa','en','und')", name="ck_cargo_item_alias_language"
        ),
        db.CheckConstraint(
            "alias_type IN ('COMMON_NAME','CUSTOMER_TERM','ABBREVIATION','LEGACY_TERM','OTHER_GOVERNED')",
            name="ck_cargo_item_alias_type",
        ),
        db.Index("ix_cargo_item_alias_item_active", "catalog_item_id", "is_active"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )
    catalog_item_id = db.Column(
        BIGINT,
        db.ForeignKey("cargo_catalog_item.id", ondelete="RESTRICT"),
        nullable=False,
    )
    alias_text = db.Column(db.String(200), nullable=False)
    normalized_alias = db.Column(db.String(200), nullable=False)
    language = db.Column(db.String(8), nullable=False, default="und")
    alias_type = db.Column(db.String(24), nullable=False, default="COMMON_NAME")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    created_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    catalog_item = db.relationship("CargoCatalogItem", back_populates="aliases")


class ProjectCargoCatalogItem(db.Model):
    """Project-specific ranking metadata for an organization catalog item."""

    __tablename__ = "project_cargo_catalog_item"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["project_id", "organization_id"],
            ["project.id", "project.organization_id"],
            name="fk_project_cargo_item_project_same_org",
            ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["cargo_catalog_item_id", "organization_id"],
            ["cargo_catalog_item.id", "cargo_catalog_item.organization_id"],
            name="fk_project_cargo_item_catalog_same_org",
            ondelete="RESTRICT",
        ),
        db.UniqueConstraint(
            "project_id",
            "cargo_catalog_item_id",
            name="uq_project_cargo_catalog_item_pair",
        ),
        db.CheckConstraint(
            "display_order >= 0", name="ck_project_cargo_catalog_item_order"
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_project_cargo_catalog_item_version"
        ),
        db.Index(
            "ix_project_cargo_catalog_item_preference",
            "project_id",
            "is_active",
            "display_order",
        ),
        db.Index(
            "ix_project_cargo_catalog_item_catalog",
            "cargo_catalog_item_id",
            "project_id",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id = db.Column(BIGINT, nullable=False)
    cargo_catalog_item_id = db.Column(BIGINT, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    created_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    catalog_item = db.relationship("CargoCatalogItem")

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class ShipmentCargoItem(db.Model):
    __tablename__ = "shipment_cargo_item"
    __table_args__ = (
        db.UniqueConstraint("id", "uom_id", name="uq_shipment_cargo_id_uom"),
        db.ForeignKeyConstraint(
            ["source_request_cargo_item_id", "source_shipment_request_id"],
            ["request_cargo_item.id", "request_cargo_item.shipment_request_id"],
            name="fk_shipment_cargo_source_item_request",
            ondelete="RESTRICT",
        ),
        db.UniqueConstraint(
            "operational_shipment_id",
            "line_number",
            name="uq_shipment_cargo_item_shipment_line",
        ),
        db.UniqueConstraint(
            "id",
            "operational_shipment_id",
            name="uq_shipment_cargo_item_id_shipment",
        ),
        db.CheckConstraint(
            "line_number >= 1", name="ck_shipment_cargo_item_line_positive"
        ),
        db.CheckConstraint(
            "quantity > 0", name="ck_shipment_cargo_item_quantity_positive"
        ),
        db.CheckConstraint(
            "requested_quantity IS NULL OR requested_quantity > 0",
            name="ck_shipment_cargo_requested_quantity_positive",
        ),
        db.CheckConstraint(
            "planned_quantity IS NULL OR planned_quantity > 0",
            name="ck_shipment_cargo_planned_quantity_positive",
        ),
        db.CheckConstraint(
            "actual_quantity IS NULL OR actual_quantity > 0",
            name="ck_shipment_cargo_actual_quantity_positive",
        ),
        db.CheckConstraint(
            "requested_quantity IS NULL OR source_shipment_request_id IS NOT NULL",
            name="ck_shipment_cargo_requested_has_source",
        ),
        db.CheckConstraint(
            "source_request_cargo_item_id IS NULL OR source_shipment_request_id IS NOT NULL",
            name="ck_shipment_cargo_source_item_has_request",
        ),
        db.CheckConstraint(
            "(gross_weight IS NULL AND gross_weight_uom_id IS NULL) OR "
            "(gross_weight > 0 AND gross_weight_uom_id IS NOT NULL)",
            name="ck_shipment_cargo_weight_pair",
        ),
        db.CheckConstraint(
            "(volume IS NULL AND volume_uom_id IS NULL) OR "
            "(volume > 0 AND volume_uom_id IS NOT NULL)",
            name="ck_shipment_cargo_volume_pair",
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_shipment_cargo_item_version_positive"
        ),
        db.Index(
            "ix_shipment_cargo_item_shipment", "operational_shipment_id", "line_number"
        ),
        db.Index(
            "ix_shipment_cargo_item_catalog_shipment",
            "catalog_item_id",
            "operational_shipment_id",
        ),
        db.Index(
            "ix_shipment_cargo_item_source_request",
            "source_shipment_request_id",
            "operational_shipment_id",
        ),
        db.Index(
            "ix_shipment_cargo_item_source_request_cargo",
            "source_request_cargo_item_id",
        ),
        db.Index(
            "ix_shipment_cargo_item_customer_shipment",
            "cargo_owner_customer_id",
            "operational_shipment_id",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )
    operational_shipment_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_shipment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # NULL is intentional for historical lines: migration must not guess the
    # cargo owner.  New shared-transport commands require this field.
    cargo_owner_customer_id = db.Column(
        BIGINT, db.ForeignKey("customer.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    source_shipment_request_id = db.Column(
        BIGINT,
        db.ForeignKey("shipment_request.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_request_cargo_item_id = db.Column(BIGINT, nullable=True)
    line_number = db.Column(db.Integer, nullable=False)
    catalog_item_id = db.Column(
        BIGINT,
        db.ForeignKey("cargo_catalog_item.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cargo_type_id = db.Column(
        BIGINT, db.ForeignKey("cargo_type.id", ondelete="RESTRICT"), nullable=False
    )
    quantity = db.Column(db.Numeric(18, 6), nullable=False)
    requested_quantity = db.Column(db.Numeric(18, 6), nullable=True)
    planned_quantity = db.Column(db.Numeric(18, 6), nullable=True)
    actual_quantity = db.Column(db.Numeric(18, 6), nullable=True)
    uom_id = db.Column(
        BIGINT, db.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"), nullable=False
    )
    packaging_type_id = db.Column(
        BIGINT, db.ForeignKey("packaging_type.id", ondelete="RESTRICT"), nullable=True
    )
    gross_weight = db.Column(db.Numeric(18, 6), nullable=True)
    gross_weight_uom_id = db.Column(
        BIGINT, db.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"), nullable=True
    )
    volume = db.Column(db.Numeric(18, 6), nullable=True)
    volume_uom_id = db.Column(
        BIGINT, db.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"), nullable=True
    )
    display_name_snapshot = db.Column(db.String(200), nullable=False)
    cargo_type_code_snapshot = db.Column(db.String(64), nullable=False)
    cargo_type_fa_snapshot = db.Column(db.String(160), nullable=False)
    cargo_type_en_snapshot = db.Column(db.String(160), nullable=False)
    uom_code_snapshot = db.Column(db.String(64), nullable=False)
    uom_symbol_snapshot = db.Column(db.String(32), nullable=False)
    part_number_snapshot = db.Column(db.String(120), nullable=True)
    customer_item_code_snapshot = db.Column(db.String(120), nullable=True)
    hs_code_snapshot = db.Column(db.String(32), nullable=True)
    brand_snapshot = db.Column(db.String(120), nullable=True)
    model_snapshot = db.Column(db.String(120), nullable=True)
    description_snapshot = db.Column(db.Text, nullable=True)
    packaging_code_snapshot = db.Column(db.String(64), nullable=True)
    packaging_fa_snapshot = db.Column(db.String(160), nullable=True)
    packaging_en_snapshot = db.Column(db.String(160), nullable=True)
    gross_weight_uom_code_snapshot = db.Column(db.String(64), nullable=True)
    gross_weight_uom_symbol_snapshot = db.Column(db.String(32), nullable=True)
    volume_uom_code_snapshot = db.Column(db.String(64), nullable=True)
    volume_uom_symbol_snapshot = db.Column(db.String(32), nullable=True)
    destination_description = db.Column(db.String(300), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    created_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    catalog_item = db.relationship("CargoCatalogItem")
    cargo_type = db.relationship("CargoType")
    uom = db.relationship("UnitOfMeasure", foreign_keys=[uom_id])
    packaging_type = db.relationship("PackagingType")
    gross_weight_uom = db.relationship(
        "UnitOfMeasure", foreign_keys=[gross_weight_uom_id]
    )
    volume_uom = db.relationship("UnitOfMeasure", foreign_keys=[volume_uom_id])
    cargo_owner_customer = db.relationship("Customer", foreign_keys=[cargo_owner_customer_id])
    source_shipment_request = db.relationship(
        "ShipmentRequest", foreign_keys=[source_shipment_request_id]
    )
    source_request_cargo_item = db.relationship(
        "RequestCargoItem", foreign_keys=[source_request_cargo_item_id]
    )

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class ShipmentCargoTransportAllocation(db.Model):
    """Quantity of one immutable cargo line assigned to one execution unit."""
    __tablename__ = "shipment_cargo_transport_allocation"
    __table_args__ = (
        db.UniqueConstraint("shipment_cargo_item_id", "transport_unit_id", name="uq_cargo_transport_allocation_pair"),
        db.CheckConstraint("allocated_quantity > 0", name="ck_cargo_transport_allocation_positive"),
        db.Index("ix_cargo_transport_allocation_shipment", "operational_shipment_id"),
        db.Index("ix_cargo_transport_allocation_unit", "transport_unit_id"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="RESTRICT"), nullable=False)
    shipment_cargo_item_id = db.Column(BIGINT, db.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT"), nullable=False)
    transport_unit_id = db.Column(BIGINT, db.ForeignKey("shipment_transport_unit.id", ondelete="RESTRICT"), nullable=False)
    allocated_quantity = db.Column(db.Numeric(18, 6), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    updated_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    cargo_item = db.relationship("ShipmentCargoItem")
    transport_unit = db.relationship("ShipmentTransportUnit")


class ExecutionUnitCargoAllocation(db.Model):
    """Canonical cargo-to-tenant-execution allocation.

    Shipment/project columns retain auditable lineage; they are derived from
    the cargo line at creation and never serve as alternate ownership truth.
    """
    __tablename__ = "execution_unit_cargo_allocation"
    __table_args__ = (
        db.CheckConstraint("allocated_quantity > 0", name="ck_execution_unit_cargo_allocation_positive"),
        db.CheckConstraint("dimension IS NULL OR dimension IN ('PLANNED','ACTUAL')", name="ck_execution_cargo_allocation_dimension"),
        db.CheckConstraint("version >= 1", name="ck_execution_cargo_allocation_version"),
        db.CheckConstraint("(route_stage_execution_id IS NULL AND dimension IS NULL) OR (route_stage_execution_id IS NOT NULL AND dimension IS NOT NULL)", name="ck_execution_cargo_allocation_stage_dimension"),
        db.Index("uq_execution_cargo_allocation_current_stage", "shipment_cargo_item_id", "route_stage_execution_id", "dimension", unique=True, postgresql_where=db.text("is_current AND route_stage_execution_id IS NOT NULL"), sqlite_where=db.text("is_current = 1 AND route_stage_execution_id IS NOT NULL")),
        db.Index("uq_execution_cargo_allocation_current_legacy", "shipment_cargo_item_id", "execution_unit_id", unique=True, postgresql_where=db.text("is_current AND route_stage_execution_id IS NULL"), sqlite_where=db.text("is_current = 1 AND route_stage_execution_id IS NULL")),
        db.Index("ix_execution_unit_cargo_allocation_execution", "execution_unit_id"),
        db.Index("ix_execution_unit_cargo_allocation_shipment", "operational_shipment_id"),
        db.Index("ix_execution_unit_cargo_allocation_project", "project_id"),
        db.Index("ix_execution_cargo_allocation_stage", "route_stage_execution_id", "dimension"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    execution_unit_id = db.Column(BIGINT, db.ForeignKey("execution_unit.id", ondelete="RESTRICT"), nullable=False)
    shipment_cargo_item_id = db.Column(BIGINT, db.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT"), nullable=False)
    operational_shipment_id = db.Column(BIGINT, db.ForeignKey("operational_shipment.id", ondelete="RESTRICT"), nullable=False)
    project_id = db.Column(BIGINT, db.ForeignKey("project.id", ondelete="RESTRICT"), nullable=True)
    # NULL on pre-P3-05 rows means the stage and plan/actual meaning are unknown.
    route_stage_execution_id = db.Column(BIGINT, db.ForeignKey("route_stage_execution.id", ondelete="RESTRICT"), nullable=True)
    dimension = db.Column(db.String(8), nullable=True)
    is_current = db.Column(db.Boolean, nullable=False, default=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    allocated_quantity = db.Column(db.Numeric(18, 6), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    updated_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    execution_unit = db.relationship("ExecutionUnit")
    cargo_item = db.relationship("ShipmentCargoItem")
    route_stage_execution = db.relationship("RouteStageExecution")


class CargoAllocationTransfer(db.Model):
    """One atomic movement between two ACTUAL allocations of the same Cargo."""

    __tablename__ = "cargo_allocation_transfer"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "idempotency_key", name="uq_cargo_allocation_transfer_key"),
        db.CheckConstraint("quantity > 0", name="ck_cargo_allocation_transfer_positive"),
        db.CheckConstraint("source_allocation_id <> target_allocation_id", name="ck_cargo_allocation_transfer_distinct"),
        db.Index("ix_cargo_allocation_transfer_cargo_time", "shipment_cargo_item_id", "recorded_at"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    shipment_cargo_item_id = db.Column(BIGINT, db.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT"), nullable=False)
    source_allocation_id = db.Column(BIGINT, db.ForeignKey("execution_unit_cargo_allocation.id", ondelete="RESTRICT"), nullable=False)
    target_allocation_id = db.Column(BIGINT, db.ForeignKey("execution_unit_cargo_allocation.id", ondelete="RESTRICT"), nullable=False)
    quantity = db.Column(db.Numeric(18, 6), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    recorded_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    context = db.Column(db.String(300), nullable=True)
    reason = db.Column(db.String(500), nullable=True)
    idempotency_key = db.Column(db.String(100), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)


class CargoAllocationRevision(db.Model):
    """Immutable before/after fact for a planned, actual or legacy allocation."""

    __tablename__ = "cargo_allocation_revision"
    __table_args__ = (
        db.UniqueConstraint("allocation_id", "revision_number", name="uq_cargo_allocation_revision_number"),
        db.UniqueConstraint("organization_id", "idempotency_key", name="uq_cargo_allocation_revision_key"),
        db.CheckConstraint("revision_number >= 1", name="ck_cargo_allocation_revision_number"),
        db.CheckConstraint("before_quantity >= 0 AND after_quantity >= 0", name="ck_cargo_allocation_revision_quantities"),
        db.Index("ix_cargo_allocation_revision_cargo_time", "shipment_cargo_item_id", "recorded_at"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    shipment_cargo_item_id = db.Column(BIGINT, db.ForeignKey("shipment_cargo_item.id", ondelete="RESTRICT"), nullable=False)
    allocation_id = db.Column(BIGINT, db.ForeignKey("execution_unit_cargo_allocation.id", ondelete="RESTRICT"), nullable=False)
    revision_number = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(24), nullable=False)
    before_quantity = db.Column(db.Numeric(18, 6), nullable=False)
    after_quantity = db.Column(db.Numeric(18, 6), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    recorded_by_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    reason = db.Column(db.String(500), nullable=True)
    transfer_id = db.Column(BIGINT, db.ForeignKey("cargo_allocation_transfer.id", ondelete="RESTRICT"), nullable=True)
    idempotency_key = db.Column(db.String(100), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)


@event.listens_for(CargoAllocationRevision, "before_update")
@event.listens_for(CargoAllocationTransfer, "before_update")
def _prevent_allocation_history_rewrite(_mapper, _connection, _target) -> None:
    raise ValueError("Cargo allocation history is immutable")


@event.listens_for(CargoCatalogItem, "before_update")
def _prevent_catalog_code_change(_mapper, _connection, target) -> None:
    if inspect(target).attrs.immutable_code.history.has_changes():
        raise ValueError("immutable_code cannot be changed")


_SHIPMENT_SNAPSHOT_FIELDS = (
    "catalog_item_id",
    "cargo_type_id",
    "uom_id",
    "display_name_snapshot",
    "cargo_type_code_snapshot",
    "cargo_type_fa_snapshot",
    "cargo_type_en_snapshot",
    "uom_code_snapshot",
    "uom_symbol_snapshot",
    "part_number_snapshot",
    "customer_item_code_snapshot",
    "brand_snapshot",
    "model_snapshot",
)


@event.listens_for(ShipmentCargoItem, "before_update")
def _prevent_shipment_snapshot_rewrite(_mapper, _connection, target) -> None:
    state = inspect(target)
    if any(state.attrs[field].history.has_changes() for field in _SHIPMENT_SNAPSHOT_FIELDS):
        raise ValueError("shipment cargo snapshots are immutable")
