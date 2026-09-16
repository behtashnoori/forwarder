"""ADR-045: tenant-owned notification intent and delivery evidence."""
from uuid import uuid4
from datetime import datetime, timezone
from backend.extensions import db

BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


def now():
    return datetime.now(timezone.utc)


class NotificationAction(db.Model):
    __tablename__ = 'notification_action'
    __table_args__ = (
        db.UniqueConstraint('id', 'organization_id', name='uq_notification_action_tenant'),
        db.UniqueConstraint('event_id', 'policy', 'channel', name='uq_notification_event_policy'),
        db.ForeignKeyConstraint(['request_id', 'organization_id'],
                                ['shipment_request.id', 'shipment_request.operational_organization_id'],
                                name='fk_notification_request_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['event_id', 'organization_id'],
                                ['operational_outbox.id', 'operational_outbox.organization_id'],
                                name='fk_notification_event_tenant', ondelete='RESTRICT'),
        db.CheckConstraint("state IN ('BLOCKED','PREPARED','IN_FLIGHT','ACCEPTED','SENT','DELIVERED','FAILED','UNKNOWN')", name='ck_notification_state'),
        db.Index('ix_notification_pending', 'state', 'next_attempt_at'),
    )
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey('operational_organization.id'), nullable=False)
    request_id = db.Column(BIGINT, nullable=False)
    event_id = db.Column(BIGINT, nullable=False)
    actor_id = db.Column(BIGINT, db.ForeignKey('expert_user.id'), nullable=False)
    policy = db.Column(db.String(80), nullable=False)
    channel = db.Column(db.String(20), nullable=False)
    intent_digest = db.Column(db.String(64), nullable=False)
    state = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(80), nullable=False)
    approval = db.Column(db.String(32), nullable=False, default='POLICY_DELEGATED')
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    active_attempt_id = db.Column(db.String(36))
    next_attempt_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)


class NotificationAttempt(db.Model):
    __tablename__ = 'notification_attempt'
    __table_args__ = (
        db.ForeignKeyConstraint(['action_id', 'organization_id'],
                                ['notification_action.id', 'notification_action.organization_id'],
                                name='fk_notification_attempt_tenant', ondelete='RESTRICT'),
        db.UniqueConstraint('action_id', 'number', name='uq_notification_attempt_number'),
        db.CheckConstraint("outcome IN ('IN_FLIGHT','ACCEPTED','SENT','DELIVERED','FAILED','UNKNOWN')", name='ck_notification_attempt_outcome'),
    )
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey('operational_organization.id'), nullable=False)
    action_id = db.Column(db.String(36), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    provider = db.Column(db.String(40), nullable=False)
    provider_reference = db.Column(db.String(80), nullable=False)
    simulated = db.Column(db.Boolean, nullable=False)
    outcome = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(80), nullable=False)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    lease_until = db.Column(db.DateTime(timezone=True), nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True))
