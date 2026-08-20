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


class ShipmentCargoItem(db.Model):
    __tablename__ = "shipment_cargo_item"
    __table_args__ = (
        db.UniqueConstraint(
            "operational_shipment_id",
            "line_number",
            name="uq_shipment_cargo_item_shipment_line",
        ),
        db.CheckConstraint(
            "line_number >= 1", name="ck_shipment_cargo_item_line_positive"
        ),
        db.CheckConstraint(
            "quantity > 0", name="ck_shipment_cargo_item_quantity_positive"
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
    uom_id = db.Column(
        BIGINT, db.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"), nullable=False
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
    uom = db.relationship("UnitOfMeasure")

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


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
    "hs_code_snapshot",
    "brand_snapshot",
    "model_snapshot",
    "description_snapshot",
)


@event.listens_for(ShipmentCargoItem, "before_update")
def _prevent_shipment_snapshot_rewrite(_mapper, _connection, target) -> None:
    state = inspect(target)
    if any(state.attrs[field].history.has_changes() for field in _SHIPMENT_SNAPSHOT_FIELDS):
        raise ValueError("shipment cargo snapshots are immutable")
