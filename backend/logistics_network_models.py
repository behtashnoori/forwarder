"""Governed Logistics Network models for Release 1.7.0."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import event, inspect

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


PROJECT_LOGISTICS_ROLES = frozenset(
    {
        "ORIGIN",
        "INTERMEDIATE",
        "DESTINATION",
        "CUSTOMS_PROCESSING",
        "TRANSFER",
        "STORAGE",
        "LOADING",
        "UNLOADING",
        "OTHER_GOVERNED",
    }
)


class LogisticsPointType(db.Model):
    __tablename__ = "logistics_point_type"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_logistics_point_type_public_id"),
        db.UniqueConstraint("immutable_code", name="uq_logistics_point_type_code"),
        db.CheckConstraint(
            "version >= 1", name="ck_logistics_point_type_version_positive"
        ),
        db.Index("ix_logistics_point_type_active_order", "is_active", "display_order"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    immutable_code = db.Column(db.String(64), nullable=False)
    fa_name = db.Column(db.String(160), nullable=False)
    en_name = db.Column(db.String(160), nullable=False)
    definition = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
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
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class LogisticsPoint(db.Model):
    __tablename__ = "logistics_point"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_logistics_point_public_id"),
        db.UniqueConstraint(
            "organization_id", "immutable_code", name="uq_logistics_point_org_code"
        ),
        db.UniqueConstraint("id", "organization_id", name="uq_logistics_point_id_org"),
        db.UniqueConstraint(
            "global_adoption_id", name="uq_logistics_point_global_adoption"
        ),
        db.ForeignKeyConstraint(
            ["global_adoption_id", "organization_id"],
            ["organization_global_logistics_point_adoption.id", "organization_global_logistics_point_adoption.organization_id"],
            name="fk_logistics_point_global_adoption_org",
            ondelete="RESTRICT",
        ),
        db.UniqueConstraint(
            "organization_id",
            "normalized_name",
            "logistics_point_type_id",
            "country_id",
            "geography_key",
            name="uq_logistics_point_exact_duplicate",
        ),
        db.CheckConstraint("version >= 1", name="ck_logistics_point_version_positive"),
        db.Index("ix_logistics_point_org_active", "organization_id", "is_active"),
        db.Index(
            "ix_logistics_point_org_type", "organization_id", "logistics_point_type_id"
        ),
        db.Index("ix_logistics_point_org_name", "organization_id", "normalized_name"),
        db.Index(
            "ix_logistics_point_org_geography",
            "organization_id",
            "country_id",
            "province_id",
            "city_id",
        ),
        db.Index("ix_logistics_point_org_updated", "organization_id", "updated_at"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    global_logistics_point_id = db.Column(
        BIGINT, db.ForeignKey("global_logistics_point.id", ondelete="RESTRICT"), nullable=True
    )
    global_adoption_id = db.Column(BIGINT, nullable=True)
    immutable_code = db.Column(db.String(64), nullable=False)
    logistics_point_type_id = db.Column(
        BIGINT,
        db.ForeignKey("logistics_point_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fa_name = db.Column(db.String(160), nullable=False)
    normalized_name = db.Column(db.String(200), nullable=False)
    en_name = db.Column(db.String(160), nullable=True)
    country_id = db.Column(
        BIGINT, db.ForeignKey("country.id", ondelete="RESTRICT"), nullable=False
    )
    province_id = db.Column(
        BIGINT, db.ForeignKey("province.id", ondelete="RESTRICT"), nullable=True
    )
    city_id = db.Column(
        BIGINT, db.ForeignKey("city.id", ondelete="RESTRICT"), nullable=True
    )
    geography_key = db.Column(db.String(200), nullable=False)
    short_address = db.Column(db.String(500), nullable=True)
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
    point_type = db.relationship("LogisticsPointType")
    country = db.relationship("Country")
    province = db.relationship("Province")
    city = db.relationship("City")
    global_point = db.relationship("GlobalLogisticsPoint")
    global_adoption = db.relationship("OrganizationGlobalLogisticsPointAdoption")
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class ProjectLogisticsPoint(db.Model):
    __tablename__ = "project_logistics_point"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_project_logistics_point_public_id"),
        db.UniqueConstraint(
            "project_id",
            "id",
            name="uq_project_logistics_point_project_id_id",
        ),
        db.UniqueConstraint(
            "project_id",
            "logistics_point_id",
            "project_role",
            name="uq_project_logistics_point_role",
        ),
        db.ForeignKeyConstraint(
            ["project_id", "organization_id"],
            ["project.id", "project.organization_id"],
            name="fk_project_logistics_point_project_org",
            ondelete="RESTRICT",
        ),
        db.ForeignKeyConstraint(
            ["logistics_point_id", "organization_id"],
            ["logistics_point.id", "logistics_point.organization_id"],
            name="fk_project_logistics_point_point_org",
            ondelete="RESTRICT",
        ),
        db.CheckConstraint(
            "sequence_number >= 1", name="ck_project_logistics_point_sequence_positive"
        ),
        db.CheckConstraint(
            "project_role IN ('ORIGIN','INTERMEDIATE','DESTINATION','CUSTOMS_PROCESSING','TRANSFER','STORAGE','LOADING','UNLOADING','OTHER_GOVERNED')",
            name="ck_project_logistics_point_role",
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_project_logistics_point_version_positive"
        ),
        db.Index(
            "uq_project_logistics_point_active_sequence",
            "project_id",
            "sequence_number",
            unique=True,
            postgresql_where=db.text("is_active"),
            sqlite_where=db.text("is_active = 1"),
        ),
        db.Index(
            "ix_project_logistics_point_project_active",
            "project_id",
            "is_active",
            "sequence_number",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, nullable=False)
    project_id = db.Column(BIGINT, nullable=False)
    logistics_point_id = db.Column(BIGINT, nullable=False)
    project_role = db.Column(db.String(32), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    display_label = db.Column(db.String(160), nullable=True)
    notes = db.Column(db.Text, nullable=True)
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
    project = db.relationship("Project", overlaps="logistics_point")
    logistics_point = db.relationship("LogisticsPoint", overlaps="project")
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


@event.listens_for(LogisticsPointType, "before_update")
@event.listens_for(LogisticsPoint, "before_update")
def _prevent_immutable_code_change(_mapper, _connection, target):
    if inspect(target).attrs.immutable_code.history.has_changes():
        raise ValueError("immutable_code cannot be changed")
