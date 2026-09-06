"""Tenant-owned dashboard configuration; system templates deliberately have no rows."""
from __future__ import annotations
import uuid
from backend.extensions import db
from backend.operational_models import BIGINT, utcnow

class Dashboard(db.Model):
    __tablename__ = "dashboard"
    __table_args__ = (
        db.CheckConstraint("dashboard_type = 'PERSONAL'", name="ck_dashboard_personal_only"),
        db.CheckConstraint("visibility = 'PRIVATE'", name="ck_dashboard_private_only"),
        db.CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_dashboard_status"),
        db.CheckConstraint("version >= 1", name="ck_dashboard_version_positive"),
        db.Index("ix_dashboard_org_owner_status", "organization_id", "owner_user_id", "status"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    owner_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    dashboard_type = db.Column(db.String(16), nullable=False, default="PERSONAL")
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(1000), nullable=False, default="")
    visibility = db.Column(db.String(16), nullable=False, default="PRIVATE")
    status = db.Column(db.String(16), nullable=False, default="ACTIVE")
    semantic_version = db.Column(db.String(64), nullable=False)
    dashboard_schema_version = db.Column(db.String(64), nullable=False)
    definition_json = db.Column(db.JSON, nullable=False)
    source_dashboard_public_id = db.Column(db.String(128))
    source_version = db.Column(db.Integer)
    source_type = db.Column(db.String(16))
    cloned_at = db.Column(db.DateTime(timezone=True))
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    updated_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)

class DashboardRevision(db.Model):
    __tablename__ = "dashboard_revision"
    __table_args__ = (db.UniqueConstraint("dashboard_id", "revision_number", name="uq_dashboard_revision_number"),)
    id = db.Column(BIGINT, primary_key=True)
    dashboard_id = db.Column(BIGINT, db.ForeignKey("dashboard.id", ondelete="RESTRICT"), nullable=False, index=True)
    revision_number = db.Column(db.Integer, nullable=False)
    definition_json = db.Column(db.JSON, nullable=False)
    semantic_version = db.Column(db.String(64), nullable=False)
    dashboard_schema_version = db.Column(db.String(64), nullable=False)
    name_snapshot = db.Column(db.String(120), nullable=False)
    description_snapshot = db.Column(db.String(1000), nullable=False, default="")
    changed_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    change_reason = db.Column(db.String(255))
