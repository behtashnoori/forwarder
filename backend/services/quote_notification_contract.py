"""Commercial read contract for the single ADR-045 notification policy.

Reads only: all business writes remain in quote_service. No provider imports.
"""
import hashlib
import json
from datetime import date, datetime, timezone
from sqlalchemy import select
from backend.extensions import db
from backend.models import Customer, CustomerGamification, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.assigned_work_authorization import authorize_work_action

EVENT = 'commercial.quote.available.v1'
POLICY = 'quote-available.v1'
TEMPLATE = 'quote-available-email.v1'
REISSUE_EVENT = 'commercial.quote.capability-reissued.v1'
REISSUE_POLICY = 'quote-capability-reissued.v1'


class NotificationDenied(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def _row(model, row_id, lock):
    query = select(model).where(model.id == row_id).execution_options(populate_existing=True)
    return db.session.scalar(query.with_for_update() if lock else query)


def quote_intent(quote_id, actor_id, organization_id, *, lock=False, read_delivery=False):
    """Resolve current intent. Locks define the dispatch authorization point.

    Lock actor, all memberships/organizations, root, quote and both customer
    identities. PostgreSQL FK key-share locks also serialize new memberships
    and new quotes against the referenced locked actor/root. No locks survive
    the short claim commit. Caller uses only a trusted event/authenticated actor.
    """
    actor = _row(ExpertUser, actor_id, lock)
    if not actor or not actor.is_active:
        raise NotificationDenied('ACTOR_INACTIVE')
    if actor.authority not in {'EXPERT', 'ORGANIZATION_ADMIN'}:
        raise NotificationDenied('ACTOR_AUTHORITY_DENIED')
    query = select(OperationalMembership).where(OperationalMembership.user_id == actor_id).order_by(OperationalMembership.id)
    members = db.session.scalars(query.with_for_update() if lock else query).all()
    for org_id in sorted({m.organization_id for m in members}):
        _row(OperationalOrganization, org_id, lock)
    quote = _row(ExpertQuote, quote_id, False)
    if not quote or quote.operational_organization_id != organization_id:
        raise NotificationDenied('QUOTE_SCOPE')
    req = _row(ShipmentRequest, quote.shipment_request_id, lock)
    quote = _row(ExpertQuote, quote_id, lock)
    if (not req or req.ownership_scope != 'TENANT'
            or req.operational_organization_id != organization_id
            or quote.shipment_request_id != req.id
            or (not read_delivery and quote.created_by_expert_id != actor_id)):
        raise NotificationDenied('TARGET_SCOPE')
    if not authorize_work_action({'id': actor_id}, req, 'request.quote').allowed:
        raise NotificationDenied('AUTHORIZATION_REVOKED')
    governed = quote.money_contract == 'quote-major.v1'
    latest = db.session.scalar(select(ExpertQuote.id).where(
        ExpertQuote.shipment_request_id == req.id).order_by(ExpertQuote.created_at.desc(), ExpertQuote.id.desc()).limit(1)) if not governed else quote.id
    if not read_delivery and (req.status != 'waiting_for_customer' or latest != quote.id
            or quote.customer_response is not None
            or (governed and (quote.superseded_by_id is not None or quote.expires_at is None
                or datetime.now(timezone.utc) >= (quote.expires_at.replace(tzinfo=timezone.utc) if quote.expires_at.tzinfo is None else quote.expires_at)))
            or (not governed and quote.valid_until is not None and quote.valid_until < date.today())):
        raise NotificationDenied('QUOTE_NOT_AVAILABLE')
    # Both exact parent references are required. No lookup by arbitrary email.
    customer = _row(Customer, req.customer_id, lock) if req.customer_id else None
    verified = _row(CustomerGamification, req.gamification_customer_id, lock) if req.gamification_customer_id else None
    if (not customer or customer.ownership_scope != 'TENANT'
            or customer.operational_organization_id != organization_id
            or customer.status != 'active' or not verified or not verified.is_email_verified):
        raise NotificationDenied('RECIPIENT_NOT_CERTIFIED')
    email = (customer.email or '').strip().lower()
    if email != (verified.email or '').strip().lower() or email.count('@') != 1 or any(c.isspace() for c in email) or '.' not in email.split('@')[-1]:
        raise NotificationDenied('RECIPIENT_EMAIL_INVALID')
    intent = {'quote_id': quote.id, 'request_id': req.id, 'actor_id': actor_id,
              'authority': (actor.authority or 'EXPERT').upper(),
              'organization_id': organization_id, 'customer_id': customer.id,
              'verified_customer_id': verified.id, 'recipient_hash': digest(email),
              'quote_hash': quote.content_digest if governed else digest([quote.amount, quote.currency, quote.note, quote.valid_until]),
              'policy': REISSUE_POLICY if read_delivery else POLICY, 'template': TEMPLATE, 'tool_version': 'notification.v1', 'channel': 'EMAIL'}
    return intent, email


def availability_payload(quote):
    """Capture immutable effective intent; invalid recipient never aborts quote."""
    base = {'actor_id': quote.created_by_expert_id, 'request_id': quote.shipment_request_id,
            'occurred_at': datetime.now(timezone.utc).isoformat()}
    try:
        intent, _ = quote_intent(quote.id, quote.created_by_expert_id, quote.operational_organization_id)
        return {**base, 'intent': intent, 'intent_digest': digest(intent), 'reason': 'READY'}
    except NotificationDenied as exc:
        return {**base, 'intent': None, 'intent_digest': digest(base), 'reason': str(exc)}
