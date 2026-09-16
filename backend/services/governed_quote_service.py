"""Commercial's ADR-047 exact money, immutable publication and response commands."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import re
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from backend.extensions import db
from backend.models import ExpertQuote
from backend.quote_response_models import QuoteResponseFact, QuoteResponseReceipt
from backend.services.assigned_work_authorization import authorize_work_action
from backend.services.quote_notification_contract import digest, EVENT, availability_payload
from backend.services import outbox_service
from backend.services.quote_capability_crypto import CapabilityDenied
from backend.services.quote_response_authorization import (
    aware, authorize_token, database_instant, issue_grant, lock_quote_scope,
)

CURRENCIES = ({'code': 'IRR', 'label': 'ریال (IRR)', 'scale': 0},
              {'code': 'USD', 'label': 'دلار (USD)', 'scale': 2},
              {'code': 'EUR', 'label': 'یورو (EUR)', 'scale': 2})
LIMIT = Decimal('9223372036854775807')
RESPONSES = frozenset({'accepted', 'negotiation_requested', 'declined'})


class QuoteConflict(ValueError):
    pass


def normalize_money(value, currency):
    if type(currency) is not str or currency not in {'IRR', 'USD', 'EUR'}:
        raise ValueError('CURRENCY_UNSUPPORTED')
    pattern = r'(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?' if currency != 'IRR' else r'(?:0|[1-9][0-9]*)'
    if type(value) is not str or len(value) > 22 or not re.fullmatch(pattern, value, re.ASCII):
        raise ValueError('AMOUNT_CANONICAL_STRING_REQUIRED')
    amount = Decimal(value)
    if amount > LIMIT:
        raise ValueError('AMOUNT_OVERFLOW')
    return amount


def exact_string(amount, currency):
    return format(amount, '.0f' if currency == 'IRR' else '.2f')


def normalize_publish(payload):
    if type(payload) is not dict or set(payload) - {'amount', 'currency', 'note', 'valid_until', 'predecessor_public_id'}:
        raise ValueError('QUOTE_PAYLOAD_INVALID')
    currency = payload.get('currency')
    amount = normalize_money(payload.get('amount'), currency)
    note = payload.get('note')
    if note is not None and (type(note) is not str or len(note) > 2000):
        raise ValueError('QUOTE_NOTE_INVALID')
    value = payload.get('valid_until')
    if type(value) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value, re.ASCII):
        raise ValueError('QUOTE_LOCAL_DATE_REQUIRED')
    try:
        local_date = date.fromisoformat(value)
    except ValueError:
        raise ValueError('QUOTE_LOCAL_DATE_INVALID') from None
    predecessor = payload.get('predecessor_public_id')
    if predecessor is not None and (type(predecessor) is not str or len(predecessor) != 36):
        raise ValueError('QUOTE_PREDECESSOR_INVALID')
    return amount, currency, (note.strip() or None) if note else None, local_date, predecessor


def resolve_expiry(local_date, zone_name):
    if type(zone_name) is not str or not zone_name or len(zone_name) > 64:
        raise ValueError('QUOTATION_TIMEZONE_NOT_CONFIGURED')
    try:
        zone = ZoneInfo(zone_name)
        midnight = datetime.combine(local_date + timedelta(days=1), datetime.min.time())
    except (ZoneInfoNotFoundError, ValueError, OverflowError):
        raise ValueError('QUOTATION_TIMEZONE_OR_DATE_INVALID') from None
    # Roundtrip distinguishes nonexistent wall times; first valid second, earliest fold.
    # Entire skipped dates are bounded at 48h (e.g. Pacific/Apia).
    for offset in range(48 * 60 * 60 + 1):
        wall = midnight + timedelta(seconds=offset)
        candidates = []
        for fold in (0, 1):
            instant = wall.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
            if instant.astimezone(zone).replace(tzinfo=None) == wall:
                candidates.append(instant)
        if candidates:
            return min(candidates)
    raise ValueError('QUOTATION_DEADLINE_UNRESOLVABLE')


def content_snapshot(quote):
    return {'quote_public_id': quote.public_id, 'content_revision': quote.content_revision,
        'money_contract': quote.money_contract, 'amount_exact': exact_string(quote.amount_exact, quote.currency),
        'currency': quote.currency, 'note': quote.note, 'valid_until': quote.valid_until.isoformat(),
        'validity_timezone': quote.validity_timezone, 'validity_source': 'issuer-organization',
        'validity_policy': quote.validity_policy, 'expires_at': aware(quote.expires_at).isoformat()}


def quote_projection(quote):
    if quote.money_contract != 'quote-major.v1':
        return {'id': quote.id, 'public_id': None, 'money_contract': 'legacy-unspecified',
            'amount_exact': str(quote.amount) if quote.amount is not None else None,
            'currency': quote.currency, 'unit': 'unknown', 'note': quote.note,
            'valid_until': quote.valid_until.isoformat() if quote.valid_until else None,
            'customer_response': quote.customer_response, 'legacy_evidence': True,
            'amount': quote.amount if quote.amount is not None and abs(quote.amount) <= 9007199254740991 else None,
            'legacy_money_supported': quote.amount is not None and abs(quote.amount) <= 9007199254740991}
    snapshot = content_snapshot(quote)
    safe = quote.amount_exact == quote.amount_exact.to_integral_value() and quote.amount_exact <= 9007199254740991
    return {**snapshot, 'id': quote.id, 'public_id': quote.public_id, 'unit': 'major',
        'content_digest': quote.content_digest, 'amount': int(quote.amount_exact) if safe else None,
        'legacy_money_supported': safe, 'compatibility_reason': None if safe else 'CLIENT_UPGRADE_REQUIRED',
        'published_at': aware(quote.published_at).isoformat(), 'response_version': quote.response_version,
        'customer_response': quote.customer_response,
        'response_received_at': aware(quote.response_received_at).isoformat() if quote.response_received_at else None,
        'superseded': quote.superseded_by_id is not None}


def publish(request_id, payload, actor):
    """Stage publication/grant/event in the caller's transaction, no provider call."""
    scope = lock_quote_scope(request_id, actor_id=actor['id'])
    root = scope['root']
    if not authorize_work_action(actor, root, 'request.quote').allowed:
        raise CapabilityDenied('QUOTE_PUBLICATION_DENIED')
    amount, currency, note, local_date, predecessor_id = normalize_publish(payload)
    if root.status not in {'assigned', 'in_progress', 'waiting_for_customer', 'quoted'}:
        raise QuoteConflict('REQUEST_NOT_QUOTABLE')
    governed = [q for q in scope['quotes'] if q.public_id and q.superseded_by_id is None]
    predecessor = next((q for q in governed if q.public_id == predecessor_id), None)
    if governed and (len(governed) != 1 or predecessor is None):
        raise QuoteConflict('EXPLICIT_EFFECTIVE_PREDECESSOR_REQUIRED')
    if predecessor_id and predecessor is None:
        raise QuoteConflict('PREDECESSOR_NOT_EFFECTIVE')
    if predecessor and predecessor.customer_response == 'accepted':
        raise QuoteConflict('ACCEPTED_QUOTE_REPLACEMENT_DENIED')
    expiry = resolve_expiry(local_date, scope['organization'].quotation_validity_timezone)
    now = database_instant()
    if now >= expiry:
        raise ValueError('QUOTE_DATE_EXPIRED')
    quote = ExpertQuote(shipment_request_id=root.id, operational_organization_id=root.operational_organization_id,
        amount=int(amount) if amount == amount.to_integral_value() else None,
        amount_exact=amount, money_contract='quote-major.v1', currency=currency, note=note,
        valid_until=local_date, created_by_expert_id=actor['id'], created_at=now.replace(tzinfo=None),
        public_id=str(uuid4()), content_revision=1, response_version=0, published_at=now,
        expires_at=expiry, validity_timezone=scope['organization'].quotation_validity_timezone,
        validity_policy='TIME-BIZ-003.v1', predecessor_id=predecessor.id if predecessor else None)
    quote.content_digest = digest(content_snapshot(quote))
    db.session.add(quote)
    db.session.flush()
    if predecessor:
        predecessor.superseded_by_id = quote.id
    root.status, root.has_unread_for_assignee = 'waiting_for_customer', True
    grant, reason = None, 'READY'
    try:
        grant = issue_grant(quote, scope)
    except CapabilityDenied as exc:
        reason = str(exc)
    body = availability_payload(quote)
    body['grant_id'] = grant.id if grant else None
    if grant is None:
        body['intent'], body['reason'] = None, reason
    outbox_service.record_event(root.operational_organization_id, EVENT, 'ExpertQuote', quote.id, body)
    return {'ok': True, 'quote': quote_projection(quote), 'request': {'id': root.id, 'status': root.status},
        'delivery': {'state': 'READY' if grant else 'BLOCKED', 'reason': reason,
                     'follow_up_assignee_id': root.assigned_to,
                     'dependency': 'DELIVERY/ONBOARDING_DEPENDENCY_OPEN', 'remediation_url': None}}


def customer_read(token, quote_public_id):
    scope, grant, quote, now = authorize_token(token, quote_public_id)
    facts = db.session.scalars(select(QuoteResponseFact).where(
        QuoteResponseFact.quote_id == quote.id, QuoteResponseFact.organization_id == grant.organization_id)
        .order_by(QuoteResponseFact.sequence)).all()
    projection = quote_projection(quote)
    projection.pop('id', None)
    return {'quote': projection, 'history': [fact_projection(f) for f in facts],
        'can_respond': now < aware(quote.expires_at) and quote.superseded_by_id is None
            and scope['root'].status in {'waiting_for_customer', 'quoted'}
            and quote.customer_response not in {'accepted', 'declined'},
        'read_expires_at': aware(grant.read_expires_at).isoformat()}


def fact_projection(fact):
    return {'id': fact.id, 'sequence': fact.sequence, 'prior_response': fact.prior_response,
        'response': fact.response, 'reason': fact.reason, 'snapshot': fact.snapshot,
        'response_received_at': aware(fact.response_received_at).isoformat(),
        'recorded_at': aware(fact.recorded_at).isoformat()}


def effective_quote_for_root(request_id):
    """Commercial owner read; timestamps never supersede governed content."""
    governed = db.session.scalars(select(ExpertQuote).where(
        ExpertQuote.shipment_request_id == request_id, ExpertQuote.public_id.is_not(None),
        ExpertQuote.superseded_by_id.is_(None)).order_by(ExpertQuote.id)).all()
    if governed:
        if len(governed) != 1:
            raise CapabilityDenied('EFFECTIVE_QUOTE_AMBIGUOUS')
        return governed[0]
    return db.session.scalar(select(ExpertQuote).where(ExpertQuote.shipment_request_id == request_id)
        .order_by(ExpertQuote.created_at.desc(), ExpertQuote.id.desc()).limit(1))


def has_governed_response_expression(request_model):
    """Commercial response axis; never changes the canonical request lifecycle."""
    return select(ExpertQuote.id).where(ExpertQuote.shipment_request_id == request_model.id,
        ExpertQuote.money_contract == 'quote-major.v1', ExpertQuote.superseded_by_id.is_(None),
        ExpertQuote.customer_response.is_not(None)).exists()


def respond(token, quote_public_id, payload, idempotency_key):
    """One caller-owned unit stages fact/projection/receipt/event/inbox, no commit."""
    if (type(payload) is not dict or set(payload) != {'response', 'expected_response_version',
            'content_revision', 'content_digest', 'reason'} or type(payload['response']) is not str
            or payload['response'] not in RESPONSES
            or type(payload['expected_response_version']) is not int or payload['expected_response_version'] < 0
            or type(payload['content_revision']) is not int or payload['content_revision'] != 1
            or type(payload['content_digest']) is not str or not re.fullmatch('[0-9a-f]{64}', payload['content_digest'])
            or type(payload['reason']) is not str or payload['reason'] not in {'CUSTOMER_DECISION', 'CUSTOMER_NEGOTIATION'}
            or type(idempotency_key) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', idempotency_key)):
        raise ValueError('RESPONSE_PAYLOAD_INVALID')
    scope, grant, quote, now = authorize_token(token, quote_public_id, write=False)
    if payload['content_revision'] != quote.content_revision or payload['content_digest'] != quote.content_digest:
        raise QuoteConflict('OBSERVED_CONTENT_STALE')
    request_digest = digest(payload)
    receipt = db.session.scalar(select(QuoteResponseReceipt).where(
        QuoteResponseReceipt.grant_id == grant.id, QuoteResponseReceipt.quote_id == quote.id,
        QuoteResponseReceipt.idempotency_key == idempotency_key)
        .execution_options(populate_existing=True).with_for_update())
    if receipt:
        if receipt.request_digest != request_digest:
            raise QuoteConflict('IDEMPOTENCY_PAYLOAD_CONFLICT')
        return receipt.result  # live grant checked even when write window has closed
    from backend.services.quote_response_authorization import validate_live_grant
    now, _, _ = validate_live_grant(grant, scope, quote, write=True)
    if payload['expected_response_version'] != quote.response_version:
        raise QuoteConflict('RESPONSE_VERSION_STALE')
    prior, response = quote.customer_response, payload['response']
    if prior in {'accepted', 'declined'} and prior != response:
        raise QuoteConflict('QUOTE_RESPONSE_TERMINAL')
    if prior == 'negotiation_requested' and response not in RESPONSES:
        raise QuoteConflict('QUOTE_RESPONSE_INVALID_TRANSITION')
    noop = prior == response
    if noop:
        fact = db.session.scalar(select(QuoteResponseFact).where(
            QuoteResponseFact.quote_id == quote.id, QuoteResponseFact.sequence == quote.response_version).with_for_update())
        if fact is None:
            raise CapabilityDenied('RESPONSE_HISTORY_UNAVAILABLE')
    else:
        fact = QuoteResponseFact(id=str(uuid4()), organization_id=grant.organization_id,
            request_id=grant.request_id, quote_id=quote.id, grant_id=grant.id, subject=grant.subject,
            sequence=quote.response_version + 1, prior_response=prior, response=response,
            reason=payload['reason'], snapshot=content_snapshot(quote), response_received_at=now, recorded_at=now)
        db.session.add(fact)
        quote.customer_response, quote.response_version, quote.response_received_at = response, fact.sequence, now
        quote.responded_at = now.replace(tzinfo=None)  # new fact's documented UTC compatibility only
        scope['root'].has_unread_for_assignee = True
        db.session.flush()
        event = outbox_service.record_event(grant.organization_id, 'commercial.quote.customer-response.v1', 'ExpertQuote', quote.id,
            {'fact_id': fact.id, 'request_id': grant.request_id, 'quote_public_id': quote.public_id,
             'response_sequence': fact.sequence, 'response': response})
        from backend.services.quote_response_notification import stage_response_inbox
        stage_response_inbox(scope['root'], fact, event, quote)
    result = {'receipt_id': str(uuid4()), 'fact': fact_projection(fact), 'response_version': quote.response_version, 'noop': noop}
    db.session.add(QuoteResponseReceipt(id=result['receipt_id'], organization_id=grant.organization_id,
        request_id=grant.request_id, quote_id=quote.id, grant_id=grant.id, fact_id=fact.id,
        idempotency_key=idempotency_key, request_digest=request_digest, result=result, recorded_at=now))
    db.session.flush()
    return result
