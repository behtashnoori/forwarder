"""Dormant, channel-neutral notification persistence foundation."""
from __future__ import annotations

import uuid

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


NOTIFICATION_ACTION_STATUSES = (
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
)

NOTIFICATION_ATTEMPT_STATUSES = (
    "PENDING",
    "IN_PROGRESS",
    "SUCCEEDED",
    "FAILED",
    "UNKNOWN",
)


class NotificationAction(db.Model):
    """Tenant-owned durable notification work, without delivery policy."""

    __tablename__ = "notification_action"
    __table_args__ = (
        db.UniqueConstraint(
            "id", "organization_id", name="uq_notification_action_tenant"
        ),
        db.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_notification_action_idempotency",
        ),
        db.ForeignKeyConstraint(
            ["source_event_id", "organization_id"],
            ["operational_outbox.id", "operational_outbox.organization_id"],
            name="fk_notification_action_source_event_tenant",
            ondelete="RESTRICT",
        ),
        db.CheckConstraint(
            "status IN ('PENDING','IN_PROGRESS','COMPLETED','FAILED','CANCELLED')",
            name="ck_notification_action_status",
        ),
        db.Index(
            "ix_notification_action_org_status",
            "organization_id",
            "status",
            "created_at",
        ),
        db.Index(
            "ix_notification_action_correlation",
            "organization_id",
            "correlation_key",
        ),
    )

    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4())
    )
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_event_id = db.Column(BIGINT, nullable=True)
    idempotency_key = db.Column(db.String(160), nullable=False)
    correlation_key = db.Column(db.String(160), nullable=True)
    purpose = db.Column(db.String(80), nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="PENDING", server_default="PENDING"
    )

    # These are deliberately nullable. C1 does not select a recipient or channel.
    recipient_reference = db.Column(db.String(255), nullable=True)
    channel = db.Column(db.String(32), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    attempts = db.relationship(
        "NotificationAttempt",
        back_populates="action",
        order_by="NotificationAttempt.attempt_number",
        passive_deletes=True,
    )


class NotificationAttempt(db.Model):
    """Durable audit row for a future delivery attempt."""

    __tablename__ = "notification_attempt"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["action_id", "organization_id"],
            ["notification_action.id", "notification_action.organization_id"],
            name="fk_notification_attempt_action_tenant",
            ondelete="RESTRICT",
        ),
        db.UniqueConstraint(
            "action_id",
            "attempt_number",
            name="uq_notification_attempt_number",
        ),
        db.CheckConstraint(
            "attempt_number >= 1", name="ck_notification_attempt_number_positive"
        ),
        db.CheckConstraint(
            "status IN ('PENDING','IN_PROGRESS','SUCCEEDED','FAILED','UNKNOWN')",
            name="ck_notification_attempt_status",
        ),
        db.Index(
            "ix_notification_attempt_org_status",
            "organization_id",
            "status",
            "created_at",
        ),
    )

    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4())
    )
    organization_id = db.Column(
        BIGINT,
        db.ForeignKey("operational_organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action_id = db.Column(BIGINT, nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="PENDING", server_default="PENDING"
    )

    # No channel or provider is selected by the foundation.
    channel = db.Column(db.String(32), nullable=True)
    provider = db.Column(db.String(80), nullable=True)
    provider_reference = db.Column(db.String(160), nullable=True)
    result_code = db.Column(db.String(80), nullable=True)
    failure_code = db.Column(db.String(80), nullable=True)
    failure_summary = db.Column(db.String(255), nullable=True)

    attempted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    action = db.relationship("NotificationAction", back_populates="attempts")


__all__ = [
    "NOTIFICATION_ACTION_STATUSES",
    "NOTIFICATION_ATTEMPT_STATUSES",
    "NotificationAction",
    "NotificationAttempt",
]
