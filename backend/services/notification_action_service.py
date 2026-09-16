"""Bounded ADR-045 consumer, controlled commands and independently committed worker.

The internal worker derives authority only from committed Commercial events.
Interactive commands derive identity from authenticated context, never input IDs.
"""
from datetime import timedelta, timezone
from functools import wraps
from uuid import uuid4
from flask import has_request_context
from sqlalchemy import or_, select
from backend.auth import get_current_user
from backend.census_context import census_unit_of_work, clear_census_context
from backend.extensions import db
from backend.notification_models import NotificationAction, NotificationAttempt, now
from backend.notification_provider import ProviderResult, configured_provider
from backend.operational_models import OperationalOutbox
from backend.services.quote_notification_contract import (
    EVENT, POLICY, TEMPLATE, REISSUE_EVENT, REISSUE_POLICY, NotificationDenied, digest, quote_intent,
)

MAX_ATTEMPTS = 3
LEASE_SECONDS = 60


def _transaction_command(function):
    @wraps(function)
    def command(*args, **kwargs):
        if db.session.new or db.session.dirty or db.session.deleted:
            raise ValueError('NOTIFICATION_COMMAND_REQUIRES_CLEAN_UNIT_OF_WORK')
        db.session.rollback()
        if not has_request_context():
            clear_census_context(db.session)
        try:
            with census_unit_of_work(db.session):
                return function(*args, **kwargs)
        finally:
            db.session.rollback()
    return command


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _event(action):
    event = db.session.scalar(select(OperationalOutbox).where(
        OperationalOutbox.id == action.event_id,
        OperationalOutbox.organization_id == action.organization_id))
    if not event or event.event_type not in {EVENT, REISSUE_EVENT} or event.aggregate_type != 'ExpertQuote':
        raise NotificationDenied('EVENT_MISMATCH')
    body = event.payload
    if (body.get('actor_id') != action.actor_id or body.get('request_id') != action.request_id
            or action.policy != (REISSUE_POLICY if event.event_type == REISSUE_EVENT else POLICY) or action.channel != 'EMAIL'
            or body.get('intent_digest') != action.intent_digest
            or body.get('intent') is None or digest(body['intent']) != action.intent_digest):
        raise NotificationDenied('INTENT_MISMATCH')
    return event


def _validate(action, *, lock=False):
    event = _event(action)
    from backend.models import ExpertQuote
    quote = db.session.get(ExpertQuote, event.aggregate_id)
    governed = quote is not None and quote.money_contract == 'quote-major.v1'
    if governed:
        from backend.services.quote_response_authorization import lock_quote_scope, lock_grants, validate_live_grant, ScopeChanged
        from backend.services.quote_capability_crypto import CapabilityDenied
        try:
            scope = lock_quote_scope(action.request_id, actor_id=action.actor_id)
            grant = next((g for g in lock_grants(scope) if g.id == event.payload.get('grant_id')), None)
            quote = next((q for q in scope['quotes'] if q.id == event.aggregate_id), None)
            if grant is None or quote is None:
                raise CapabilityDenied('GRANT_UNAVAILABLE')
            validate_live_grant(grant, scope, quote, write=event.event_type != REISSUE_EVENT)
        except CapabilityDenied as exc:
            if isinstance(exc, ScopeChanged):
                raise
            raise NotificationDenied(str(exc)) from None
    intent, email = quote_intent(event.aggregate_id, action.actor_id, action.organization_id, lock=lock and not governed, read_delivery=event.event_type == REISSUE_EVENT)
    if digest(intent) != action.intent_digest:
        raise NotificationDenied('PREPARED_INTENT_STALE')
    if action.approval != 'POLICY_DELEGATED':
        raise NotificationDenied('APPROVAL_REQUIRED_OR_STALE')
    return email


@_transaction_command
def consume_one():
    """Only this event family has a single consumer; published_at means action persisted.

    Row lock plus unique event/policy/channel fence duplicate consumers. This
    function owns its short transaction and must not be called inside business
    writes. Replaying a previously consumed event uses the same action record.
    """
    try:
        event = db.session.scalar(select(OperationalOutbox).where(
            OperationalOutbox.event_type.in_([EVENT, REISSUE_EVENT]),
            OperationalOutbox.published_at.is_(None),
        ).order_by(OperationalOutbox.id).with_for_update(skip_locked=True).limit(1))
        if event is None:
            db.session.rollback()
            return None
        policy = REISSUE_POLICY if event.event_type == REISSUE_EVENT else POLICY
        action = db.session.scalar(select(NotificationAction).where(
            NotificationAction.event_id == event.id, NotificationAction.policy == policy,
            NotificationAction.channel == 'EMAIL'))
        if action is None:
            body = event.payload
            action = NotificationAction(organization_id=event.organization_id,
                request_id=body['request_id'], event_id=event.id, actor_id=body['actor_id'],
                policy=policy, channel='EMAIL', intent_digest=body['intent_digest'],
                state='PREPARED', reason='POLICY_DELEGATED', approval='POLICY_DELEGATED')
            db.session.add(action)
            try:
                _validate(action)
            except NotificationDenied as exc:
                action.state, action.reason = 'BLOCKED', str(exc)
        event.published_at = now()
        db.session.flush()
        action_id = action.id
        db.session.commit()
        return action_id
    except Exception:
        db.session.rollback()
        raise


def _interactive(action_id):
    actor = get_current_user()
    if not actor:
        raise NotificationDenied('AUTHENTICATED_ACTOR_REQUIRED')
    from backend.services.ownership_service import OwnershipContractError, tenant_organization_for_user
    try:
        organization_id = tenant_organization_for_user(actor)
    except OwnershipContractError as exc:
        raise NotificationDenied('ACTION_NOT_AVAILABLE') from exc
    action = db.session.scalar(select(NotificationAction).where(
        NotificationAction.id == action_id, NotificationAction.organization_id == organization_id,
        NotificationAction.actor_id == actor['id']).execution_options(populate_existing=True))
    if not action:
        raise NotificationDenied('ACTION_NOT_AVAILABLE')
    # Result reads also require current scope. Do not require still-unanswered
    # quote merely to view prior evidence, but always enforce current root auth.
    from backend.models import ShipmentRequest
    from backend.services.assigned_work_authorization import authorize_work_action
    root = db.session.get(ShipmentRequest, action.request_id)
    if not root or not authorize_work_action(actor, root, 'request.quote').allowed:
        raise NotificationDenied('ACTION_NOT_AVAILABLE')
    return action


def propose(action_id):
    action = _interactive(action_id)
    try:
        _validate(action)
        allowed, reason = action.state == 'PREPARED', action.reason
    except NotificationDenied as exc:
        allowed, reason = False, str(exc)
    return {'action_id': action.id, 'can_prepare': allowed, 'reason': reason,
            'channel': 'EMAIL', 'policy': POLICY, 'approval_required': False}


def prepare(action_id):
    action = _interactive(action_id)
    _validate(action)
    if action.state != 'PREPARED':
        raise NotificationDenied('ACTION_NOT_PREPARED')
    return {'action_id': action.id, 'intent_digest': action.intent_digest, 'approval': action.approval}


def approve_when_required(action_id):
    """No caller-provided approval boolean or invented elevated approval grant.

    The sole fixed policy already delegates this synthetic notification. Future
    human-required policies must implement a separately authorized approval rule.
    """
    prepared = prepare(action_id)
    return {**prepared, 'approval_required': False, 'authority': POLICY}


def result(action_id):
    action = _interactive(action_id)
    attempts = db.session.scalars(select(NotificationAttempt).where(
        NotificationAttempt.action_id == action.id,
        NotificationAttempt.organization_id == action.organization_id).order_by(NotificationAttempt.number)).all()
    return {'action_id': action.id, 'state': action.state, 'reason': action.reason,
            'attempts': [{'id': a.id, 'outcome': a.outcome, 'reason': a.reason,
                          'simulated': a.simulated, 'provider': a.provider} for a in attempts]}


def execute(action_id):
    _interactive(action_id)
    db.session.rollback()  # command boundary owns subsequent short transactions
    return _dispatch(action_id)


@_transaction_command
def _claim_once(action_id):
    provider = configured_provider()  # fail before claiming, no silent fallback
    try:
        action = db.session.scalar(select(NotificationAction).where(
            NotificationAction.id == action_id).with_for_update(skip_locked=True))
        if action is None or action.state != 'PREPARED' or (action.next_attempt_at and _aware(action.next_attempt_at) > now()):
            db.session.rollback()
            return None
        try:
            email = _validate(action, lock=True)
        except NotificationDenied as exc:
            action.state, action.reason, action.updated_at = 'BLOCKED', str(exc), now()
            db.session.commit()
            return None
        if action.attempt_count >= MAX_ATTEMPTS:
            action.state, action.reason = 'FAILED', 'ATTEMPTS_EXHAUSTED'
            db.session.commit()
            return None
        attempt_id = str(uuid4())
        reference = 'fake:' + attempt_id
        action.attempt_count += 1
        attempt = NotificationAttempt(id=attempt_id, organization_id=action.organization_id,
            action_id=action.id, number=action.attempt_count, provider=provider.name,
            provider_reference=reference, simulated=True, outcome='IN_FLIGHT',
            reason='DISPATCH_AUTHORIZED', lease_until=now() + timedelta(seconds=LEASE_SECONDS))
        db.session.add(attempt)
        action.active_attempt_id, action.state = attempt_id, 'IN_FLIGHT'
        action.reason, action.updated_at = 'DISPATCH_AUTHORIZED', now()
        token = (action.id, action.organization_id, attempt_id, reference, email, _event(action).payload.get('grant_id'), action.policy == REISSUE_POLICY)
        # Linearization point: commit decision while actor/member/root/recipient
        # locks still held. Revocation committed before this decision denies.
        db.session.commit()
        return token
    except Exception:
        db.session.rollback()
        raise


def _claim(action_id):
    from backend.services.quote_response_authorization import ScopeChanged
    for _attempt in range(3):
        try:
            return _claim_once(action_id)
        except ScopeChanged:
            db.session.rollback()
    return None  # still PREPARED; no grant/send on unstable hints


@_transaction_command
def _apply_result(token, response, *, reconciliation=False):
    action_id, org_id, attempt_id, reference = token[:4]
    action = db.session.scalar(select(NotificationAction).where(
        NotificationAction.id == action_id, NotificationAction.organization_id == org_id).with_for_update())
    attempt = db.session.scalar(select(NotificationAttempt).where(
        NotificationAttempt.id == attempt_id, NotificationAttempt.action_id == action_id,
        NotificationAttempt.organization_id == org_id).with_for_update())
    expected = 'UNKNOWN' if reconciliation else 'IN_FLIGHT'
    if (not action or not attempt or action.active_attempt_id != attempt_id
            or action.state != expected or attempt.outcome != expected
            or reference != attempt.provider_reference or response.reference != reference):
        db.session.rollback()
        return False
    if response.outcome not in {'ACCEPTED', 'SENT', 'DELIVERED', 'FAILED', 'UNKNOWN'}:
        response = ProviderResult('UNKNOWN', reference, 'INVALID_PROVIDER_RESULT')
    if not reconciliation and _aware(attempt.lease_until) <= now():
        response = ProviderResult('UNKNOWN', reference, 'LEASE_EXPIRED')
    # Reason codes only. Never persist provider exceptions, bodies or destinations.
    safe_reasons = {'INVALID_PROVIDER_RESULT', 'LEASE_EXPIRED', 'PROVIDER_EXCEPTION',
                   'RECONCILIATION_EXCEPTION', 'SYNTHETIC_RECIPIENT_REQUIRED', 'CAPABILITY_UNAVAILABLE', 'PRIVATE_CAPTURE_REQUIRED'}
    safe_reason = response.reason if response.reason in safe_reasons or response.reason in {
        prefix + outcome for prefix in ('SIMULATED_', 'SIMULATED_RECONCILIATION_')
        for outcome in ('ACCEPTED', 'SENT', 'DELIVERED', 'FAILED', 'UNKNOWN')
    } else 'PROVIDER_RESULT'
    attempt.outcome, attempt.reason, attempt.finished_at = response.outcome, safe_reason, now()
    action.state, action.reason, action.updated_at = response.outcome, safe_reason, now()
    action.next_attempt_at = None
    if response.outcome == 'FAILED' and response.retryable and action.attempt_count < MAX_ATTEMPTS:
        action.state = 'PREPARED'
        action.next_attempt_at = now() + timedelta(seconds=30 * 2 ** (action.attempt_count - 1))
    db.session.commit()
    return True


def _dispatch(action_id):
    token = _claim(action_id)
    if not token:
        return False
    try:
        provider = configured_provider()
        if token[5]:
            response = provider.send_quote(reference=token[3], recipient=token[4], template=TEMPLATE, grant_id=token[5], read_delivery=token[6])
        else:
            response = provider.send(reference=token[3], recipient=token[4], template=TEMPLATE)
    except Exception:
        response = ProviderResult('UNKNOWN', token[3], 'PROVIDER_EXCEPTION')
    return _apply_result(token, response)


@_transaction_command
def recover_expired(limit=100):
    """A lost worker may already have sent: expiry never creates a retry."""
    ids = db.session.scalars(select(NotificationAction.id).join(
        NotificationAttempt, NotificationAttempt.id == NotificationAction.active_attempt_id).where(
        NotificationAction.state == 'IN_FLIGHT', NotificationAttempt.lease_until <= now()
    ).order_by(NotificationAttempt.lease_until).limit(limit)).all()
    db.session.rollback()
    count = 0
    for action_id in ids:
        action = db.session.scalar(select(NotificationAction).where(NotificationAction.id == action_id).with_for_update(skip_locked=True))
        if action is not None and action.state == 'IN_FLIGHT':
            attempt = db.session.get(NotificationAttempt, action.active_attempt_id)
            if attempt and _aware(attempt.lease_until) <= now():
                action.state = attempt.outcome = 'UNKNOWN'
                action.reason = attempt.reason = 'LEASE_EXPIRED'
                action.updated_at = attempt.finished_at = now()
                count += 1
        db.session.commit()
    return count


def reconcile(action_id):
    """Internal worker-only provider query; no new send, arbitrary result or actor."""
    provider = configured_provider()
    action = db.session.get(NotificationAction, action_id)
    if not action or action.state != 'UNKNOWN':
        db.session.rollback()
        return False
    attempt = db.session.get(NotificationAttempt, action.active_attempt_id)
    token = (action.id, action.organization_id, attempt.id, attempt.provider_reference)
    db.session.rollback()
    try:
        response = provider.reconcile(reference=token[3])
    except Exception:
        response = ProviderResult('UNKNOWN', token[3], 'RECONCILIATION_EXCEPTION')
    return _apply_result(token, response, reconciliation=True)


def run_batch(limit=25):
    configured_provider()
    if not 1 <= limit <= 100:
        raise ValueError('BATCH_LIMIT')
    consumed = 0
    for _ in range(limit):
        if consume_one() is None:
            break
        consumed += 1
    recovered = recover_expired(limit)
    ids = db.session.scalars(select(NotificationAction.id).where(
        NotificationAction.state == 'PREPARED',
        or_(NotificationAction.next_attempt_at.is_(None), NotificationAction.next_attempt_at <= now())
    ).order_by(NotificationAction.created_at).limit(limit)).all()
    db.session.rollback()
    dispatched = sum(bool(_dispatch(action_id)) for action_id in ids)
    return {'consumed': consumed, 'dispatched': dispatched, 'recovered_unknown': recovered, 'simulated': True}
