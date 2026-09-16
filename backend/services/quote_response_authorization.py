"""Authorization-owned exact quote grant lifecycle and shared serialization seam."""
import calendar
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from functools import wraps
from flask import current_app
from sqlalchemy import select, func
from backend.extensions import db
from backend.models import Customer, CustomerGamification, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.quote_response_models import QuoteKeyPolicy, QuoteKeyPolicyAudit, QuoteResponseGrant
from backend.services.quote_capability_crypto import (
    AUDIENCE, ISSUER, CapabilityDenied, QuoteKeyring, token_digest,
)
from backend.services.quote_notification_contract import digest
from backend.services.ownership_service import require_tenant_resource


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def database_instant():
    if db.engine.dialect.name == 'postgresql':
        return aware(db.session.scalar(select(func.clock_timestamp())))
    return datetime.now(timezone.utc)


class ScopeChanged(CapabilityDenied):
    pass


def serialized_recipient_write(function):
    """CRM owner retains its commit; retry changed hints only from a clean unit."""
    @wraps(function)
    def command(*args, **kwargs):
        from backend.census_context import census_unit_of_work
        if db.session.new or db.session.dirty or db.session.deleted:
            raise CapabilityDenied('RECIPIENT_COMMAND_REQUIRES_CLEAN_UNIT_OF_WORK')
        for attempt in range(3):
            db.session.rollback()
            try:
                with census_unit_of_work(db.session):
                    return function(*args, **kwargs)
            except ScopeChanged:
                db.session.rollback()
                if attempt == 2:
                    raise CapabilityDenied('SCOPE_CHANGED_RETRY') from None
            except Exception:
                db.session.rollback()
                raise
    return command


def _row(model, identity, *, lock=True):
    query = select(model).where(model.id == identity).execution_options(populate_existing=True)
    return db.session.scalar(query.with_for_update() if lock else query)


def _hints(root):
    return (root.assigned_to, root.operational_organization_id,
            root.customer_id, root.gamification_customer_id)


def lock_quote_scope(request_id, *, actor_id=None, extra_customer_ids=(), extra_actor_ids=(), allow_legacy_uncertified=False):
    """Action/attempt (worker only) -> policy -> actors/members/orgs/root/quotes/recipients.

    Caller owns transaction. Changed pre-lock hints require full rollback/retry;
    never acquire earlier-order locks late. Existing actions/events are untouched.
    """
    hint = _row(ShipmentRequest, request_id, lock=False)
    if hint is None:
        raise CapabilityDenied('TARGET_UNAVAILABLE')
    hints = _hints(hint)
    quote_hints = db.session.execute(select(ExpertQuote.id, ExpertQuote.created_by_expert_id).where(
        ExpertQuote.shipment_request_id == request_id).order_by(ExpertQuote.id)).all()
    actors = sorted({v for v in [actor_id, hint.assigned_to, *extra_actor_ids, *(q.created_by_expert_id for q in quote_hints)] if v})
    policy = _row(QuoteKeyPolicy, 1)
    for identity in actors:
        _row(ExpertUser, identity)
    members = db.session.scalars(select(OperationalMembership).where(
        OperationalMembership.user_id.in_(actors)).order_by(OperationalMembership.id)
        .execution_options(populate_existing=True).with_for_update()).all()
    org_ids = sorted({v for v in [hint.operational_organization_id, *(m.organization_id for m in members)] if v})
    orgs = {identity: _row(OperationalOrganization, identity) for identity in org_ids}
    root = _row(ShipmentRequest, request_id)
    if root is None or _hints(root) != hints:
        raise ScopeChanged('SCOPE_CHANGED')
    quotes = db.session.scalars(select(ExpertQuote).where(ExpertQuote.shipment_request_id == request_id)
        .order_by(ExpertQuote.id).execution_options(populate_existing=True).with_for_update()).all()
    if [(q.id, q.created_by_expert_id) for q in quotes] != [(q.id, q.created_by_expert_id) for q in quote_hints]:
        raise ScopeChanged('SCOPE_CHANGED')
    customers = {identity: _row(Customer, identity) for identity in sorted(
        {v for v in [root.customer_id, *extra_customer_ids] if v})}
    customer = customers.get(root.customer_id)
    verified = _row(CustomerGamification, root.gamification_customer_id) if root.gamification_customer_id else None
    legacy = root.ownership_scope != 'TENANT' or root.operational_organization_id is None
    if legacy and allow_legacy_uncertified and not any(q.money_contract == 'quote-major.v1' for q in quotes):
        return {'policy':policy, 'root':root, 'quotes':quotes, 'organization':None,
            'customer':customer, 'verified':verified, 'customers':customers, 'legacy_uncertified':True}
    organization_id = require_tenant_resource(root)
    organization = orgs.get(organization_id)
    if not organization or not organization.is_active:
        raise CapabilityDenied('ORGANIZATION_UNAVAILABLE')
    return {'policy': policy, 'root': root, 'quotes': quotes, 'organization': organization,
            'customer': customer, 'verified': verified, 'customers': customers}


def certified_recipient(scope):
    root, customer, verified = scope['root'], scope['customer'], scope['verified']
    if (not customer or not verified or customer.ownership_scope != 'TENANT'
            or require_tenant_resource(customer) != root.operational_organization_id
            or customer.status != 'active' or not verified.is_email_verified):
        raise CapabilityDenied('RECIPIENT_NOT_CERTIFIED')
    email = (customer.email or '').strip().lower()
    if (email != (verified.email or '').strip().lower() or email.count('@') != 1
            or any(c.isspace() for c in email) or '.' not in email.split('@')[-1]):
        raise CapabilityDenied('RECIPIENT_EMAIL_INVALID')
    return email


def lock_grants(scope):
    return db.session.scalars(select(QuoteResponseGrant).where(
        QuoteResponseGrant.request_id == scope['root'].id).order_by(QuoteResponseGrant.id)
        .execution_options(populate_existing=True).with_for_update()).all()


def issue_grant(quote, scope, *, reissue=False):
    """Caller transaction; Commercial invokes owner command, never gets raw token."""
    ring = QuoteKeyring(current_app.config)
    ring.check_policy(scope['policy'])
    email = certified_recipient(scope)
    root, customer, verified = scope['root'], scope['customer'], scope['verified']
    now = database_instant()
    horizon = max(aware(quote.published_at), aware(quote.expires_at)) + timedelta(days=30)
    if now >= horizon:
        raise CapabilityDenied('READ_HORIZON_EXPIRED')
    existing = lock_grants(scope)
    if reissue:
        for grant in existing:
            if grant.quote_id == quote.id and grant.revoked_at is None:
                grant.revoked_at, grant.revoked_reason = now, 'REISSUED'
    elif any(g.quote_id == quote.id for g in existing):
        raise CapabilityDenied('GRANT_ALREADY_ISSUED')
    identity, subject = str(uuid4()), str(uuid4())
    epoch = calendar.timegm(now.utctimetuple())
    claims = {'iss': ISSUER, 'aud': AUDIENCE, 'token_type': 'quote-response', 'v': 1,
        'sub': subject, 'jti': identity, 'iat': epoch, 'nbf': epoch,
        'exp': calendar.timegm(horizon.utctimetuple()) + int(bool(horizon.microsecond)),
        'tenant': scope['organization'].public_id, 'request': root.public_id,
        'quote': quote.public_id, 'revision': quote.content_revision,
        'content_digest': quote.content_digest}
    token = ring.sign(claims, ring.active, new=True)
    grant = QuoteResponseGrant(id=identity, organization_id=root.operational_organization_id,
        request_id=root.id, quote_id=quote.id, customer_id=customer.id,
        verified_customer_id=verified.id, subject=subject, claims=claims,
        key_version=ring.active, token_digest=token_digest(token), recipient_hash=digest(email),
        root_generation=root.quote_recipient_generation,
        customer_generation=customer.quote_recipient_generation,
        verified_generation=verified.quote_recipient_generation,
        issued_at=now, read_expires_at=horizon, write_expires_at=aware(quote.expires_at))
    db.session.add(grant)
    db.session.flush()
    return grant


def validate_live_grant(grant, scope, quote, *, write=False):
    ring = QuoteKeyring(current_app.config)
    ring.check_policy(scope['policy'])
    ring._material(grant.key_version)
    email = certified_recipient(scope)
    root, customer, verified = scope['root'], scope['customer'], scope['verified']
    now = database_instant()
    if (grant.revoked_at is not None or now >= aware(grant.read_expires_at)
            or grant.organization_id != root.operational_organization_id
            or grant.request_id != root.id or grant.quote_id != quote.id
            or grant.customer_id != customer.id or grant.verified_customer_id != verified.id
            or grant.root_generation != root.quote_recipient_generation
            or grant.customer_generation != customer.quote_recipient_generation
            or grant.verified_generation != verified.quote_recipient_generation
            or not secrets.compare_digest(grant.recipient_hash, digest(email))
            or grant.claims.get('tenant') != scope['organization'].public_id
            or grant.claims.get('request') != root.public_id
            or grant.claims.get('quote') != quote.public_id
            or grant.claims.get('revision') != quote.content_revision
            or grant.claims.get('content_digest') != quote.content_digest
            or grant.claims.get('jti') != grant.id or grant.claims.get('sub') != grant.subject):
        raise CapabilityDenied('GRANT_UNAVAILABLE')
    from backend.services.governed_quote_service import content_snapshot
    if quote.content_digest != digest(content_snapshot(quote)):
        raise CapabilityDenied('CONTENT_CHANGED')
    if write and (now >= aware(grant.write_expires_at) or now >= aware(quote.expires_at)
            or quote.superseded_by_id is not None
            or root.status not in {'waiting_for_customer', 'quoted'}):
        raise CapabilityDenied('QUOTE_WRITE_UNAVAILABLE')
    return now, email, ring


def authorize_token(token, quote_public_id, *, write=False):
    ring = QuoteKeyring(current_app.config)
    claims, kid = ring.verify(token)
    hint = _row(QuoteResponseGrant, claims['jti'], lock=False)
    if hint is None:
        raise CapabilityDenied('GRANT_UNAVAILABLE')
    request_id = hint.request_id
    scope = lock_quote_scope(request_id)
    grants = lock_grants(scope)
    grant = next((g for g in grants if g.id == claims['jti']), None)
    quote = next((q for q in scope['quotes'] if q.public_id == quote_public_id), None)
    if (grant is None or quote is None or grant.claims != claims or grant.key_version != kid
            or not secrets.compare_digest(grant.token_digest, token_digest(token))):
        raise CapabilityDenied('GRANT_UNAVAILABLE')
    now, _, _ = validate_live_grant(grant, scope, quote, write=write)
    return scope, grant, quote, now


def capability_for_adapter(grant_id, *, write=True):
    """Private adapter contract only; no route/staff query returns this value."""
    hint = _row(QuoteResponseGrant, grant_id, lock=False)
    if hint is None:
        raise CapabilityDenied('GRANT_UNAVAILABLE')
    scope = lock_quote_scope(hint.request_id)
    grant = next((g for g in lock_grants(scope) if g.id == grant_id), None)
    quote = next((q for q in scope['quotes'] if grant and q.id == grant.quote_id), None)
    if grant is None or quote is None:
        raise CapabilityDenied('GRANT_UNAVAILABLE')
    _, email, ring = validate_live_grant(grant, scope, quote, write=write)
    return ring.sign(grant.claims, grant.key_version, expected_digest=grant.token_digest), email


def quote_readiness_metadata(quote):
    """Staff read metadata only. No key, bearer, email or grant identifier escapes."""
    root=_row(ShipmentRequest,quote.shipment_request_id,lock=False)
    result={'state':'BLOCKED','reason':'NO_CURRENT_READ_GRANT',
        'follow_up_assignee_id':root.assigned_to if root else None,
        'dependency':'DELIVERY/ONBOARDING_DEPENDENCY_OPEN','remediation_url':None,
        'real_delivery_proven':False}
    try:
        if not root or require_tenant_resource(root)!=quote.operational_organization_id:
            raise CapabilityDenied('TARGET_UNAVAILABLE')
        org=_row(OperationalOrganization,root.operational_organization_id,lock=False)
        if not org or not org.is_active:
            raise CapabilityDenied('ORGANIZATION_UNAVAILABLE')
        scope={'root':root,'organization':org,'policy':_row(QuoteKeyPolicy,1,lock=False),
            'customer':_row(Customer,root.customer_id,lock=False) if root.customer_id else None,
            'verified':_row(CustomerGamification,root.gamification_customer_id,lock=False) if root.gamification_customer_id else None}
        certified_recipient(scope)
        QuoteKeyring(current_app.config).check_policy(scope['policy'])
        grants=db.session.scalars(select(QuoteResponseGrant).where(
            QuoteResponseGrant.quote_id==quote.id,QuoteResponseGrant.request_id==root.id,
            QuoteResponseGrant.organization_id==org.id,QuoteResponseGrant.revoked_at.is_(None))
            .order_by(QuoteResponseGrant.issued_at.desc())).all()
        for grant in grants:
            try:
                _,_,ring=validate_live_grant(grant,scope,quote,write=False)
                # Confirm current trusted material matches the immutable digest.
                # Reconstruction remains inside Authorization, never returned.
                ring.sign(grant.claims,grant.key_version,expected_digest=grant.token_digest)
                return {**result,'state':'RECIPIENT_READY','reason':'REAL_DELIVERY_NOT_PROVEN'}
            except CapabilityDenied:
                continue
    except CapabilityDenied as exc:
        result['reason']=str(exc)
    return result


def manage_grant(request_id, quote_public_id, user, operation):
    """Staff command stages only metadata; no capability escapes this owner."""
    from backend.services.assigned_work_authorization import authorize_work_action
    from backend.services.quote_notification_contract import REISSUE_EVENT, quote_intent
    from backend.services.outbox_service import record_event
    if operation not in {'REISSUE', 'REVOKE'}:
        raise ValueError('GRANT_OPERATION_INVALID')
    scope = lock_quote_scope(request_id, actor_id=user['id'])
    if not authorize_work_action(user, scope['root'], 'request.quote').allowed:
        raise CapabilityDenied('GRANT_MANAGEMENT_DENIED')
    quote = next((q for q in scope['quotes'] if q.public_id == quote_public_id), None)
    if quote is None:
        raise CapabilityDenied('TARGET_UNAVAILABLE')
    from backend.operational_models import OperationalAudit
    def audit(changed, new_grant=None):
        db.session.add(OperationalAudit(organization_id=scope['organization'].id,
            actor_user_id=user['id'], action='authorization.quote-capability.' + operation.lower(),
            entity_type='ExpertQuote', entity_id=quote.id,
            metadata_json={'request_public_id':scope['root'].public_id, 'quote_public_id':quote.public_id,
                'revoked_grant_ids':changed, 'issued_grant_id':new_grant.id if new_grant else None,
                'reason':'STAFF_REQUEST', 'policy_epoch':scope['policy'].epoch if scope['policy'] else None},
            recorded_at=database_instant()))
    if operation == 'REVOKE':
        instant = database_instant()
        changed = []
        for grant in lock_grants(scope):
            if grant.quote_id == quote.id and grant.revoked_at is None:
                grant.revoked_at, grant.revoked_reason = instant, 'STAFF_REVOKED'
                changed.append(grant.id)
        audit(changed)
        return {'state': 'REVOKED', 'quote_public_id': quote.public_id}
    previous = [g.id for g in lock_grants(scope) if g.quote_id == quote.id and g.revoked_at is None]
    grant = issue_grant(quote, scope, reissue=True)
    audit(previous, grant)
    intent, _ = quote_intent(quote.id, user['id'], scope['organization'].id, read_delivery=True)
    event = record_event(scope['organization'].id, REISSUE_EVENT, 'ExpertQuote', quote.id,
        {'actor_id': user['id'], 'request_id': request_id, 'grant_id': grant.id,
         'intent': intent, 'intent_digest': digest(intent), 'reason': 'READY'})
    return {'state': 'PREPARED', 'quote_public_id': quote.public_id,
        'read_expires_at': aware(grant.read_expires_at).isoformat()}


def qualification_key_policy(reason='INITIALIZED'):
    """Explicit synthetic fixture-only provisioning, never startup or product HTTP."""
    if (not current_app.testing or current_app.config.get('NOTIFICATION_PROVIDER') != 'fake'
            or current_app.config.get('NOTIFICATION_ENVIRONMENT') != 'qualification'):
        raise CapabilityDenied('QUALIFICATION_ONLY')
    ring = QuoteKeyring(current_app.config)
    old = _row(QuoteKeyPolicy, 1)
    if old:
        if ring.epoch != old.epoch + 1:
            raise CapabilityDenied('POLICY_EPOCH')
        # Immutable audit survives configured absence and process restart.
        # A missing material entry never erases a quarantined version.
        history = db.session.scalars(select(QuoteKeyPolicyAudit).order_by(QuoteKeyPolicyAudit.epoch)).all()
        prior_states = [(kid, state) for audit in history for kid, state in audit.states.items()]
        prior_states.extend(old.states.items())
        for kid, state in prior_states:
            if state in {'REVOKED', 'COMPROMISED', 'RETIRED'} and ring.states.get(kid) in {'ACTIVE', 'VERIFY_ONLY'}:
                raise CapabilityDenied('KEY_QUARANTINE_TERMINAL')
            if state == 'VERIFY_ONLY' and ring.states.get(kid) == 'ACTIVE':
                raise CapabilityDenied('OLD_KEY_NO_NEW_ISSUANCE')
        old.epoch, old.active_key, old.states, old.changed_at = ring.epoch, ring.active, dict(ring.states), database_instant()
    else:
        if ring.epoch != 1:
            raise CapabilityDenied('POLICY_EPOCH')
        db.session.add(QuoteKeyPolicy(id=1, epoch=1, active_key=ring.active, states=dict(ring.states)))
    db.session.add(QuoteKeyPolicyAudit(epoch=ring.epoch, active_key=ring.active,
        states=dict(ring.states), reason=reason, provenance='OWNER_DELEGATED_QUALIFICATION'))
    db.session.flush()
