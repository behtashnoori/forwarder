"""ADR-047 bounded Authorization grants and Commercial append-only response facts."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from backend.extensions import db

BIGINT = db.BigInteger().with_variant(db.Integer, 'sqlite')


def instant():
    return datetime.now(timezone.utc)


class QuoteKeyPolicy(db.Model):
    __tablename__ = 'quote_key_policy'
    id = db.Column(db.Integer, primary_key=True)
    epoch = db.Column(db.Integer, nullable=False)
    active_key = db.Column(db.String(32), nullable=False)
    states = db.Column(db.JSON, nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=instant)
    __table_args__ = (db.CheckConstraint('id = 1 AND epoch > 0', name='ck_quote_key_policy_singleton'),)


class QuoteKeyPolicyAudit(db.Model):
    __tablename__ = 'quote_key_policy_audit'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    epoch = db.Column(db.Integer, nullable=False, unique=True)
    active_key = db.Column(db.String(32), nullable=False)
    states = db.Column(db.JSON, nullable=False)
    reason = db.Column(db.String(32), nullable=False)
    provenance = db.Column(db.String(32), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=instant)


class QuoteResponseGrant(db.Model):
    __tablename__ = 'quote_response_grant'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey('operational_organization.id', ondelete='RESTRICT'), nullable=False)
    request_id = db.Column(BIGINT, nullable=False)
    quote_id = db.Column(BIGINT, nullable=False)
    customer_id = db.Column(BIGINT, nullable=False)
    verified_customer_id = db.Column(BIGINT, db.ForeignKey('customer_gamification.id', ondelete='RESTRICT'), nullable=False)
    subject = db.Column(db.String(36), nullable=False)
    claims = db.Column(db.JSON, nullable=False)
    key_version = db.Column(db.String(32), nullable=False)
    token_digest = db.Column(db.String(64), nullable=False)
    recipient_hash = db.Column(db.String(64), nullable=False)
    root_generation = db.Column(BIGINT, nullable=False)
    customer_generation = db.Column(BIGINT, nullable=False)
    verified_generation = db.Column(BIGINT, nullable=False)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=False)
    read_expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    write_expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))
    revoked_reason = db.Column(db.String(32))
    __table_args__ = (
        db.UniqueConstraint('id', 'organization_id', name='uq_quote_grant_tenant'),
        db.ForeignKeyConstraint(['request_id', 'organization_id'], ['shipment_request.id', 'shipment_request.operational_organization_id'], name='fk_quote_grant_root_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['quote_id', 'organization_id'], ['expert_quote.id', 'expert_quote.operational_organization_id'], name='fk_quote_grant_quote_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['customer_id', 'organization_id'], ['customer.id', 'customer.operational_organization_id'], name='fk_quote_grant_customer_tenant', ondelete='RESTRICT'),
        db.CheckConstraint('root_generation >= 0 AND customer_generation >= 0 AND verified_generation >= 0', name='ck_quote_grant_generations'),
        db.CheckConstraint('read_expires_at > issued_at AND write_expires_at < read_expires_at', name='ck_quote_grant_horizon'),
        db.Index('ix_quote_grant_quote', 'quote_id'),
    )


class QuoteResponseFact(db.Model):
    __tablename__ = 'quote_response_fact'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey('operational_organization.id', ondelete='RESTRICT'), nullable=False)
    request_id = db.Column(BIGINT, nullable=False)
    quote_id = db.Column(BIGINT, nullable=False)
    grant_id = db.Column(db.String(36), nullable=False)
    subject = db.Column(db.String(36), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    prior_response = db.Column(db.String(24))
    response = db.Column(db.String(24), nullable=False)
    reason = db.Column(db.String(32), nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    response_received_at = db.Column(db.DateTime(timezone=True), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=instant)
    __table_args__ = (
        db.UniqueConstraint('id', 'organization_id', name='uq_quote_fact_tenant'),
        db.UniqueConstraint('quote_id', 'sequence', name='uq_quote_fact_sequence'),
        db.ForeignKeyConstraint(['request_id', 'organization_id'], ['shipment_request.id', 'shipment_request.operational_organization_id'], name='fk_quote_fact_root_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['quote_id', 'organization_id'], ['expert_quote.id', 'expert_quote.operational_organization_id'], name='fk_quote_fact_quote_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['grant_id', 'organization_id'], ['quote_response_grant.id', 'quote_response_grant.organization_id'], name='fk_quote_fact_grant_tenant', ondelete='RESTRICT'),
        db.CheckConstraint("sequence > 0 AND response IN ('accepted','negotiation_requested','declined')", name='ck_quote_fact_response'),
    )


class QuoteResponseReceipt(db.Model):
    __tablename__ = 'quote_response_receipt'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = db.Column(BIGINT, db.ForeignKey('operational_organization.id', ondelete='RESTRICT'), nullable=False)
    request_id = db.Column(BIGINT, nullable=False)
    quote_id = db.Column(BIGINT, nullable=False)
    grant_id = db.Column(db.String(36), nullable=False)
    fact_id = db.Column(db.String(36), nullable=False)
    idempotency_key = db.Column(db.String(64), nullable=False)
    request_digest = db.Column(db.String(64), nullable=False)
    result = db.Column(db.JSON, nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=instant)
    __table_args__ = (
        db.UniqueConstraint('grant_id', 'quote_id', 'idempotency_key', name='uq_quote_receipt_operation'),
        db.ForeignKeyConstraint(['request_id', 'organization_id'], ['shipment_request.id', 'shipment_request.operational_organization_id'], name='fk_quote_receipt_root_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['quote_id', 'organization_id'], ['expert_quote.id', 'expert_quote.operational_organization_id'], name='fk_quote_receipt_quote_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['grant_id', 'organization_id'], ['quote_response_grant.id', 'quote_response_grant.organization_id'], name='fk_quote_receipt_grant_tenant', ondelete='RESTRICT'),
        db.ForeignKeyConstraint(['fact_id', 'organization_id'], ['quote_response_fact.id', 'quote_response_fact.organization_id'], name='fk_quote_receipt_fact_tenant', ondelete='RESTRICT'),
    )


@event.listens_for(Session, 'before_flush')
def _quote_history_guard(session, _context, _instances):
    from backend.operational_models import OperationalAudit
    from backend.models import ExpertQuote, ExpertConsoleNotification
    immutable = (QuoteResponseFact, QuoteResponseReceipt, QuoteKeyPolicyAudit)
    for row in session.dirty.union(session.deleted):
        if isinstance(row, ExpertConsoleNotification):
            state = inspect(row)
            if row.quote_response_fact_id is not None or any(state.attrs.quote_response_fact_id.history.deleted):
                if row in session.deleted or any(column.name != 'is_read' and state.attrs[column.name].history.has_changes() for column in row.__table__.columns):
                    raise ValueError('QUOTE_RESPONSE_ATTENTION_ENVELOPE_IMMUTABLE')
        if isinstance(row, ExpertQuote):
            state = inspect(row)
            old_contract = state.attrs.money_contract.history.deleted
            if row.money_contract == 'quote-major.v1' or 'quote-major.v1' in old_contract:
                if row in session.deleted:
                    raise ValueError('QUOTE_PUBLICATION_HISTORY_RETAINED')
                changed = {column.name for column in row.__table__.columns if state.attrs[column.name].history.has_changes()}
                if changed - {'superseded_by_id','customer_response','response_version','response_received_at','responded_at'}:
                    raise ValueError('QUOTE_PUBLISHED_CONTENT_IMMUTABLE')
                prior = state.attrs.superseded_by_id.history.deleted
                if prior and prior[0] is not None:
                    raise ValueError('QUOTE_REPLACEMENT_HISTORY_IMMUTABLE')
        if isinstance(row, OperationalAudit):
            values = inspect(row).attrs.action.history
            if any(str(value).startswith('authorization.quote-capability.') for value in [row.action, *values.deleted]):
                raise ValueError('QUOTE_GRANT_AUDIT_APPEND_ONLY')
        if isinstance(row, immutable):
            raise ValueError('QUOTE_HISTORY_APPEND_ONLY')
        if isinstance(row, QuoteResponseGrant):
            if row in session.deleted:
                raise ValueError('QUOTE_GRANT_HISTORY_RETAINED')
            changed = {a.key for a in inspect(row).attrs if a.history.has_changes()}
            if changed - {'revoked_at', 'revoked_reason'}:
                raise ValueError('QUOTE_GRANT_IMMUTABLE')
            history = inspect(row).attrs.revoked_at.history
            if (history.deleted and history.deleted[0] is not None) or (
                    row.revoked_at is not None and 'revoked_at' not in changed and changed):
                raise ValueError('QUOTE_GRANT_REVOCATION_TERMINAL')
