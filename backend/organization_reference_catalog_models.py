"""Explicit tenant activation records for platform-governed reference data."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import declared_attr

from backend.extensions import db
from backend.operational_models import BIGINT


def utcnow():
    return datetime.now(timezone.utc)


class _OrganizationReferenceActivationMixin:
    """Shared lifecycle columns; every definition reference remains concrete."""

    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = db.Column(db.String(16), nullable=False, default="ACTIVE")
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

    @declared_attr
    def organization(cls):
        return db.relationship("OperationalOrganization")

    @declared_attr
    def __mapper_args__(cls):
        return {"version_id_col": cls.version, "version_id_generator": False}


class OrganizationCargoTypeActivation(_OrganizationReferenceActivationMixin, db.Model):
    __tablename__ = "organization_cargo_type_activation"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "cargo_type_id", name="uq_org_cargo_type_activation"
        ),
        db.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')", name="ck_org_cargo_type_activation_status"
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_org_cargo_type_activation_version"
        ),
        db.Index(
            "ix_org_cargo_type_activation_org_status", "organization_id", "status"
        ),
        db.Index("ix_org_cargo_type_activation_definition", "cargo_type_id"),
    )
    cargo_type_id = db.Column(
        BIGINT, db.ForeignKey("cargo_type.id", ondelete="RESTRICT"), nullable=False
    )
    definition = db.relationship("CargoType")


class OrganizationUnitOfMeasureActivation(
    _OrganizationReferenceActivationMixin, db.Model
):
    __tablename__ = "organization_unit_of_measure_activation"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id",
            "unit_of_measure_id",
            name="uq_org_unit_of_measure_activation",
        ),
        db.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')",
            name="ck_org_unit_of_measure_activation_status",
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_org_unit_of_measure_activation_version"
        ),
        db.Index(
            "ix_org_unit_of_measure_activation_org_status", "organization_id", "status"
        ),
        db.Index(
            "ix_org_unit_of_measure_activation_definition", "unit_of_measure_id"
        ),
    )
    unit_of_measure_id = db.Column(
        BIGINT,
        db.ForeignKey("unit_of_measure.id", ondelete="RESTRICT"),
        nullable=False,
    )
    definition = db.relationship("UnitOfMeasure")


class OrganizationPackagingTypeActivation(
    _OrganizationReferenceActivationMixin, db.Model
):
    __tablename__ = "organization_packaging_type_activation"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id",
            "packaging_type_id",
            name="uq_org_packaging_type_activation",
        ),
        db.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')",
            name="ck_org_packaging_type_activation_status",
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_org_packaging_type_activation_version"
        ),
        db.Index(
            "ix_org_packaging_type_activation_org_status", "organization_id", "status"
        ),
        db.Index("ix_org_packaging_type_activation_definition", "packaging_type_id"),
    )
    packaging_type_id = db.Column(
        BIGINT, db.ForeignKey("packaging_type.id", ondelete="RESTRICT"), nullable=False
    )
    definition = db.relationship("PackagingType")


class OrganizationTransportMeansTypeActivation(
    _OrganizationReferenceActivationMixin, db.Model
):
    __tablename__ = "organization_transport_means_type_activation"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id",
            "transport_means_type_id",
            name="uq_org_transport_means_type_activation",
        ),
        db.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')",
            name="ck_org_transport_means_type_activation_status",
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_org_transport_means_type_activation_version"
        ),
        db.Index(
            "ix_org_transport_means_type_activation_org_status",
            "organization_id",
            "status",
        ),
        db.Index(
            "ix_org_transport_means_type_activation_definition",
            "transport_means_type_id",
        ),
    )
    transport_means_type_id = db.Column(
        BIGINT,
        db.ForeignKey("transport_means_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    definition = db.relationship("TransportMeansType")


class OrganizationTransportEquipmentTypeActivation(
    _OrganizationReferenceActivationMixin, db.Model
):
    __tablename__ = "organization_transport_equipment_type_activation"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id",
            "transport_equipment_type_id",
            name="uq_org_transport_equipment_type_activation",
        ),
        db.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')",
            name="ck_org_transport_equipment_type_activation_status",
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_org_transport_equipment_type_activation_version"
        ),
        db.Index(
            "ix_org_transport_equipment_type_activation_org_status",
            "organization_id",
            "status",
        ),
        db.Index(
            "ix_org_transport_equipment_type_activation_definition",
            "transport_equipment_type_id",
        ),
    )
    transport_equipment_type_id = db.Column(
        BIGINT,
        db.ForeignKey("transport_equipment_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    definition = db.relationship("TransportEquipmentType")


__all__ = [
    "OrganizationCargoTypeActivation",
    "OrganizationUnitOfMeasureActivation",
    "OrganizationPackagingTypeActivation",
    "OrganizationTransportMeansTypeActivation",
    "OrganizationTransportEquipmentTypeActivation",
]
