"""Governed Project Configuration persistence for Release 1.8.0."""

from uuid import uuid4
from sqlalchemy import event, inspect
from sqlalchemy.orm import declared_attr
from backend.extensions import db
from backend.operational_models import BIGINT, utcnow

REQUIREMENT_LEVELS = frozenset({"REQUIRED", "OPTIONAL", "CONDITIONAL"})
DURATION_UNITS = frozenset({"MINUTE", "HOUR", "DAY"})


class ConfigurationAuditMixin:
    public_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid4()))
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

    @declared_attr
    def __mapper_args__(cls):
        return {"version_id_col": cls.version, "version_id_generator": False}


class MilestoneType(ConfigurationAuditMixin, db.Model):
    __tablename__ = "milestone_type"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_milestone_type_public_id"),
        db.UniqueConstraint("immutable_code", name="uq_milestone_type_code"),
        db.CheckConstraint("version >= 1", name="ck_milestone_type_version_positive"),
        db.Index("ix_milestone_type_active_order", "is_active", "display_order"),
    )
    id = db.Column(BIGINT, primary_key=True)
    immutable_code = db.Column(db.String(64), nullable=False)
    fa_name = db.Column(db.String(160), nullable=False)
    en_name = db.Column(db.String(160), nullable=False)
    definition = db.Column(db.Text)
    display_order = db.Column(db.Integer, nullable=False, default=0)


class ProjectService(ConfigurationAuditMixin, db.Model):
    __tablename__ = "project_service"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_project_service_public_id"),
        db.UniqueConstraint(
            "project_id", "service_type_id", name="uq_project_service_logical"
        ),
        db.CheckConstraint("display_order >= 0", name="ck_project_service_order"),
        db.CheckConstraint("version >= 1", name="ck_project_service_version"),
        db.Index(
            "uq_project_service_active_primary",
            "project_id",
            unique=True,
            postgresql_where=db.text("is_active AND is_primary"),
            sqlite_where=db.text("is_active = 1 AND is_primary = 1"),
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    project_id = db.Column(
        BIGINT, db.ForeignKey("project.id", ondelete="RESTRICT"), nullable=False
    )
    service_type_id = db.Column(
        BIGINT, db.ForeignKey("service_type.id", ondelete="RESTRICT"), nullable=False
    )
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    display_label = db.Column(db.String(160))
    notes = db.Column(db.Text)
    service_type = db.relationship("ServiceType")


class ProjectDocumentRequirement(ConfigurationAuditMixin, db.Model):
    __tablename__ = "project_document_requirement"
    __table_args__ = (
        db.UniqueConstraint(
            "public_id", name="uq_project_document_requirement_public_id"
        ),
        db.UniqueConstraint(
            "project_id",
            "document_definition_id",
            name="uq_project_document_requirement_logical",
        ),
        db.CheckConstraint(
            "requirement_level IN ('REQUIRED','OPTIONAL','CONDITIONAL')",
            name="ck_project_document_requirement_level",
        ),
        db.CheckConstraint(
            "display_order >= 0", name="ck_project_document_requirement_order"
        ),
        db.CheckConstraint(
            "version >= 1", name="ck_project_document_requirement_version"
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    project_id = db.Column(
        BIGINT, db.ForeignKey("project.id", ondelete="RESTRICT"), nullable=False
    )
    document_definition_id = db.Column(
        BIGINT,
        db.ForeignKey("document_definition.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requirement_level = db.Column(db.String(16), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    conditional_description = db.Column(db.Text)
    notes = db.Column(db.Text)
    document_definition = db.relationship("DocumentDefinition")


class ProjectMilestoneDefinition(ConfigurationAuditMixin, db.Model):
    __tablename__ = "project_milestone_definition"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["project_id", "project_logistics_point_id"],
            ["project_logistics_point.project_id", "project_logistics_point.id"],
            name="fk_project_milestone_definition_project_point",
            ondelete="RESTRICT",
        ),
        db.UniqueConstraint(
            "public_id", name="uq_project_milestone_definition_public_id"
        ),
        db.UniqueConstraint(
            "project_id",
            "milestone_type_id",
            name="uq_project_milestone_definition_logical",
        ),
        db.CheckConstraint("sequence >= 1", name="ck_project_milestone_sequence"),
        db.CheckConstraint(
            "duration_unit IS NULL OR duration_unit IN ('MINUTE','HOUR','DAY')",
            name="ck_project_milestone_duration_unit",
        ),
        db.CheckConstraint(
            "target_duration_value IS NULL OR target_duration_value > 0",
            name="ck_project_milestone_target",
        ),
        db.CheckConstraint(
            "warning_duration_value IS NULL OR warning_duration_value > 0",
            name="ck_project_milestone_warning",
        ),
        db.CheckConstraint(
            "target_duration_value IS NULL OR warning_duration_value IS NULL OR warning_duration_value >= target_duration_value",
            name="ck_project_milestone_warning_target",
        ),
        db.CheckConstraint("version >= 1", name="ck_project_milestone_version"),
        db.Index(
            "uq_project_milestone_active_sequence",
            "project_id",
            "sequence",
            unique=True,
            postgresql_where=db.text("is_active"),
            sqlite_where=db.text("is_active = 1"),
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    project_id = db.Column(
        BIGINT, db.ForeignKey("project.id", ondelete="RESTRICT"), nullable=False
    )
    milestone_type_id = db.Column(
        BIGINT, db.ForeignKey("milestone_type.id", ondelete="RESTRICT"), nullable=False
    )
    project_logistics_point_id = db.Column(BIGINT)
    sequence = db.Column(db.Integer, nullable=False)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    display_label = db.Column(db.String(160))
    target_duration_value = db.Column(db.Integer)
    warning_duration_value = db.Column(db.Integer)
    duration_unit = db.Column(db.String(8))
    notes = db.Column(db.Text)
    milestone_type = db.relationship("MilestoneType")
    project_logistics_point = db.relationship(
        "ProjectLogisticsPoint",
        foreign_keys=[project_id, project_logistics_point_id],
    )


@event.listens_for(MilestoneType, "before_update")
def _immutable_code(_mapper, _connection, target):
    if inspect(target).attrs.immutable_code.history.has_changes():
        raise ValueError("immutable_code cannot be changed")
