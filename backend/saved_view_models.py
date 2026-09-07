"""Private personal saved analytical/list view configuration."""
from __future__ import annotations

import uuid

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


class SavedView(db.Model):
    __tablename__ = "saved_view"
    __table_args__ = (
        db.CheckConstraint("visibility = 'PRIVATE'", name="ck_saved_view_private_only"),
        db.CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_saved_view_status"),
        db.CheckConstraint("version >= 1", name="ck_saved_view_version_positive"),
        db.Index("ix_saved_view_org_owner_status", "organization_id", "owner_user_id", "status"),
    )
    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey("operational_organization.id", ondelete="RESTRICT"), nullable=False)
    owner_user_id = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(1000), nullable=False, default="")
    visibility = db.Column(db.String(16), nullable=False, default="PRIVATE")
    status = db.Column(db.String(16), nullable=False, default="ACTIVE")
    semantic_version = db.Column(db.String(64), nullable=False)
    saved_view_schema_version = db.Column(db.String(64), nullable=False)
    definition_json = db.Column(db.JSON, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    updated_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)


class SavedViewRevision(db.Model):
    __tablename__ = "saved_view_revision"
    __table_args__ = (db.UniqueConstraint("saved_view_id", "revision_number", name="uq_saved_view_revision_number"),)
    id = db.Column(BIGINT, primary_key=True)
    saved_view_id = db.Column(BIGINT, db.ForeignKey("saved_view.id", ondelete="RESTRICT"), nullable=False, index=True)
    revision_number = db.Column(db.Integer, nullable=False)
    definition_json = db.Column(db.JSON, nullable=False)
    semantic_version = db.Column(db.String(64), nullable=False)
    saved_view_schema_version = db.Column(db.String(64), nullable=False)
    name_snapshot = db.Column(db.String(120), nullable=False)
    description_snapshot = db.Column(db.String(1000), nullable=False, default="")
    changed_by = db.Column(BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    change_reason = db.Column(db.String(255))
