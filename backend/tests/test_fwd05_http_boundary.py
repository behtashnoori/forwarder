"""Actual purpose API/failure boundaries; reuse the owned synthetic journey.

No operational credentials, transport, moved clock, HTTP stubs or secret logs.
"""
import json
import logging
from contextlib import contextmanager
import pytest
from backend.extensions import db
from backend.models import ExpertQuote
from backend.quote_response_models import QuoteResponseFact, QuoteResponseReceipt
from backend.tests.test_fwd05_runtime import journey, _headers, _payload


@contextmanager
def _record_application_logs(journey):
    records = []
    handler = logging.Handler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    handler.emit = lambda record: records.append(handler.format(record))
    target = journey.app.logger
    old_disabled, old_level = target.disabled, target.level
    old_threshold = logging.root.manager.disable
    target.disabled = False
    target.setLevel(logging.ERROR)
    logging.disable(logging.NOTSET)
    target.addHandler(handler)
    try:
        yield records
    finally:
        target.removeHandler(handler)
        target.disabled = old_disabled
        target.setLevel(old_level)
        logging.disable(old_threshold)


def _path(journey):
    return '/api/quote-capability/quotes/' + journey.quote_public_id


def _no_customer_effects(journey):
    assert db.session.get(ExpertQuote, journey.quote_id).response_version == 0
    assert db.session.query(QuoteResponseFact).count() == 0
    assert db.session.query(QuoteResponseReceipt).count() == 0


@pytest.mark.parametrize('origin', ['null', 'https://example.invalid',
    'http://127.0.0.1:8085, http://127.0.0.1:8086',
    'http://127.0.0.1:8085/path', 'http://127.0.0.1:8085#private'])
def test_actual_api_rejects_null_unknown_or_nonexact_origin(journey, origin):
    response = journey.app.test_client().post(_path(journey), json=_payload(journey),
        headers={**_headers(journey), 'Origin': origin, 'Idempotency-Key': 'denied-origin'})
    assert response.status_code == 403
    assert response.json == {'reason': 'CUSTOMER_ACTION_UNAVAILABLE'}
    assert 'Access-Control-Allow-Origin' not in response.headers
    _no_customer_effects(journey)


def test_explicit_multiple_origins_and_exact_idempotency_preflight(journey):
    allowed = ['http://127.0.0.1:8085', 'http://127.0.0.1:8086']
    journey.app.config['QUOTE_CAPABILITY_ALLOWED_ORIGINS'] = allowed
    client = journey.app.test_client()
    for origin in allowed:
        response = client.options(_path(journey), headers={'Origin': origin,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'authorization, content-type, idempotency-key'})
        assert response.status_code == 204
        assert response.headers['Access-Control-Allow-Origin'] == origin
        assert set(response.headers['Access-Control-Allow-Headers'].lower().split(', ')) == {'authorization', 'content-type', 'idempotency-key'}
        assert response.headers['Access-Control-Allow-Methods'] == 'GET, POST, OPTIONS'
        assert 'Access-Control-Allow-Credentials' not in response.headers
        assert 'Origin' in response.headers['Vary']
    for method, headers in [('DELETE', 'authorization'), ('POST', 'authorization,x-unknown')]:
        response = client.options(_path(journey), headers={'Origin': allowed[0],
            'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': headers})
        assert response.status_code == 403
        assert 'Access-Control-Allow-Credentials' not in response.headers
    assert client.options(_path(journey)).status_code == 403
    _no_customer_effects(journey)


def test_actual_api_cross_site_post_and_missing_origin_configuration_fail_closed(journey):
    client = journey.app.test_client()
    headers = {**_headers(journey), 'Origin': 'http://127.0.0.1:8085',
        'Sec-Fetch-Site': 'cross-site', 'Idempotency-Key': 'cross-site'}
    assert client.post(_path(journey), json=_payload(journey), headers=headers).status_code == 403
    for origins in (None, [], ['*'], ['https://example.invalid/path']):
        journey.app.config['QUOTE_CAPABILITY_ALLOWED_ORIGINS'] = origins
        response = client.get(_path(journey), headers=_headers(journey))
        assert response.status_code == 403
        assert 'Access-Control-Allow-Origin' not in response.headers
    _no_customer_effects(journey)


@pytest.mark.parametrize('body,content_type,status,reason', [
    ('{"response":"accepted","response":"declined"}', 'application/json', 400, 'RESPONSE_PAYLOAD_INVALID'),
    ('{"reason":{"x":1,"x":2}}', 'application/json', 400, 'RESPONSE_PAYLOAD_INVALID'),
    ('{', 'application/json', 400, 'RESPONSE_PAYLOAD_INVALID'),
    ('[]', 'application/json', 400, 'RESPONSE_PAYLOAD_INVALID'),
    ('x' * 2049, 'application/json', 413, 'BODY_TOO_LARGE'),
    ('response=accepted', 'application/x-www-form-urlencoded', 415, 'JSON_REQUIRED'),
    ('{}', 'text/plain', 415, 'JSON_REQUIRED')])
def test_actual_api_parser_content_type_and_size_do_not_mutate(journey, body, content_type, status, reason):
    response = journey.app.test_client().post(_path(journey), data=body, content_type=content_type,
        headers={**_headers(journey), 'Idempotency-Key': 'invalid-body'})
    assert response.status_code == status and response.json == {'reason': reason}
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    assert 'Set-Cookie' not in response.headers
    _no_customer_effects(journey)


def test_actual_api_rate_limit_is_peer_based_bounded_and_app_local(journey):
    from backend import create_app
    client = journey.app.test_client()
    for index in range(60):
        response = client.get(_path(journey), headers={**_headers(journey), 'X-Forwarded-For': '198.18.1.' + str(index)},
            environ_overrides={'REMOTE_ADDR': '198.18.0.1'})
        assert response.status_code == 200
    limited = client.get(_path(journey), headers=_headers(journey), environ_overrides={'REMOTE_ADDR': '198.18.0.1'})
    assert limited.status_code == 429 and limited.json == {'reason': 'RATE_LIMITED'}
    # Real requests fill process-local capacity; invalid tokens avoid business scope reads.
    for index in range(1023):
        response = client.get(_path(journey), headers={'Authorization': 'QuoteCapability malformed'},
            environ_overrides={'REMOTE_ADDR': 'synthetic-peer-' + str(index)})
        assert response.status_code == 403
    overflow = client.get(_path(journey), headers={'Authorization': 'QuoteCapability malformed'},
        environ_overrides={'REMOTE_ADDR': 'synthetic-overflow'})
    assert overflow.status_code == 429 and overflow.json == {'reason': 'RATE_LIMIT_CAPACITY'}
    assert len(journey.app.extensions['bounded_rate_limit']['buckets']) == 1024
    other = create_app({**dict(journey.app.config), 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'}, skip_startup=True)
    with other.app_context():
        db.create_all()  # the real application pins its census before every API
        try:
            assert other.test_client().get(_path(journey), headers={'Authorization': 'Bearer malformed'},
                environ_overrides={'REMOTE_ADDR': '198.18.0.1'}).status_code == 403
            assert len(other.extensions['bounded_rate_limit']['buckets']) == 1
        finally:
            db.session.remove()
            db.engine.dispose()  # only the explicitly owned in-memory engine
    _no_customer_effects(journey)


@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_deliberate_api_failure_never_echoes_or_logs_private_data(journey, monkeypatch, caplog, method):
    from backend.routes import quote_capability
    key_material = journey.app.config['QUOTE_CAPABILITY_KEYRING'][journey.app.config['QUOTE_CAPABILITY_ACTIVE_KEY']]['material']
    private = journey.token + '\n' + 'synthetic@example.test' + '\n' + key_material
    def fail(*args, **kwargs):
        raise RuntimeError(private)
    monkeypatch.setattr(quote_capability, 'customer_read' if method == 'GET' else 'respond', fail)
    with _record_application_logs(journey) as records:
        response = journey.app.test_client().open(_path(journey), method=method, json=_payload(journey),
            headers={**_headers(journey), 'Idempotency-Key': 'deliberate-failure'})
    assert response.status_code == 500 and response.json == {'reason': 'CUSTOMER_ACTION_FAILED'}
    rendered = response.get_data(as_text=True) + str(list(response.headers)) + caplog.text + '\n'.join(records)
    assert journey.token not in rendered and key_material not in rendered and 'synthetic@example.test' not in rendered
    assert 'Traceback' not in rendered and 'RuntimeError' not in rendered
    assert 'request data suppressed' in '\n'.join(records)
    _no_customer_effects(journey)


@pytest.mark.parametrize('failure', ['exception', 'untrusted_result', 'private_capture_exception'])
def test_deliberate_private_provider_failure_is_reason_only_and_unknown_not_resent(journey, monkeypatch, caplog, failure):
    from backend.notification_provider import FakeEmailProvider, ProviderResult, PrivateQuoteCapture
    from backend.notification_models import NotificationAction, NotificationAttempt
    from backend.operational_models import OperationalOutbox
    from backend.services.quote_service import manage_quote_capability
    from backend.services.notification_action_service import consume_one, _dispatch, reconcile
    key_material = journey.app.config['QUOTE_CAPABILITY_KEYRING'][journey.app.config['QUOTE_CAPABILITY_ACTIVE_KEY']]['material']
    private = journey.token + '\nsynthetic@example.test' + '\n' + key_material
    manage_quote_capability(journey.root_id, journey.quote_public_id, {'id': journey.expert_id}, 'REISSUE')
    action_id = consume_one()
    assert action_id is not None
    def fail_send(self, *, reference, **kwargs):
        if failure == 'exception':
            raise RuntimeError(private)
        return ProviderResult('UNKNOWN', reference, private)
    captured_private = []
    if failure == 'private_capture_exception':
        def fail_capture(self, reference, recipient, link):
            captured_private.append(link.split('#', 1)[1])
            raise RuntimeError(link + '\n' + key_material)
        monkeypatch.setattr(PrivateQuoteCapture, '_capture', fail_capture)
    else:
        monkeypatch.setattr(FakeEmailProvider, 'send_quote', fail_send)
    with _record_application_logs(journey) as records:
        assert _dispatch(action_id)
    action = db.session.get(NotificationAction, action_id)
    attempt = db.session.get(NotificationAttempt, action.active_attempt_id)
    assert action.state == attempt.outcome == 'UNKNOWN'
    assert action.reason == attempt.reason == ('PROVIDER_RESULT' if failure == 'untrusted_result' else 'PROVIDER_EXCEPTION')
    assert not _dispatch(action_id) and action.attempt_count == 1
    def fail_reconcile(self, **kwargs):
        raise RuntimeError(private)
    monkeypatch.setattr(FakeEmailProvider, 'reconcile', fail_reconcile)
    assert reconcile(action_id)
    assert db.session.get(NotificationAction, action_id).reason == 'RECONCILIATION_EXCEPTION'
    durable = []
    for model in (NotificationAction, NotificationAttempt, OperationalOutbox):
        durable.extend({column.name: getattr(row, column.name) for column in model.__table__.columns}
            for row in db.session.query(model).all())
    rendered = str(durable) + caplog.text + '\n'.join(records)
    assert all(token not in rendered for token in captured_private)
    assert journey.token not in rendered and key_material not in rendered and private not in rendered
    assert not journey.capture._messages
    _no_customer_effects(journey)


@pytest.mark.parametrize('decision', ['accepted', 'declined'])
def test_exact_terminal_decision_and_explicit_replacement_policy(journey, decision):
    from datetime import date, timedelta
    from backend.services.quote_service import create_quote_for_request, QuoteServiceError
    client = journey.app.test_client()
    response = client.post(_path(journey), json=_payload(journey, decision),
        headers={**_headers(journey), 'Idempotency-Key': 'terminal-decision'})
    assert response.status_code == 200
    payload = {'amount': '99.01', 'currency': 'EUR', 'valid_until': (date.today() + timedelta(days=4)).isoformat()}
    with pytest.raises(QuoteServiceError) as missing:
        create_quote_for_request(journey.root_id, payload, {'id': journey.expert_id})
    assert missing.value.status_code == 409
    payload['predecessor_public_id'] = journey.quote_public_id
    if decision == 'accepted':
        with pytest.raises(QuoteServiceError) as denied:
            create_quote_for_request(journey.root_id, payload, {'id': journey.expert_id})
        assert denied.value.status_code == 409
        assert db.session.get(ExpertQuote, journey.quote_id).superseded_by_id is None
    else:
        replacement = create_quote_for_request(journey.root_id, payload, {'id': journey.expert_id})
        assert replacement['quote']['amount_exact'] == '99.01'
        old = client.get(_path(journey), headers=_headers(journey))
        assert old.status_code == 200 and not old.json['can_respond']
        assert old.json['quote']['superseded'] and old.json['quote']['amount_exact'] == '1234.50'
        assert '99.01' not in json.dumps(old.json)
        assert len(old.json['history']) == 1
    assert db.session.query(QuoteResponseFact).count() == db.session.query(QuoteResponseReceipt).count() == 1


def test_stale_observed_digest_version_and_changed_idempotent_payload_do_not_create_facts(journey):
    client = journey.app.test_client()
    for field, value in [('content_digest', '0' * 64), ('expected_response_version', 1)]:
        payload = _payload(journey)
        payload[field] = value
        response = client.post(_path(journey), json=payload,
            headers={**_headers(journey), 'Idempotency-Key': 'stale-' + field})
        assert response.status_code == 409
        _no_customer_effects(journey)
    headers = {**_headers(journey), 'Idempotency-Key': 'same-receipt-key'}
    assert client.post(_path(journey), json=_payload(journey), headers=headers).status_code == 200
    conflict = client.post(_path(journey), json=_payload(journey, 'accepted'), headers=headers)
    assert conflict.status_code == 409 and conflict.json['reason'] == 'IDEMPOTENCY_PAYLOAD_CONFLICT'
    assert db.session.query(QuoteResponseFact).count() == db.session.query(QuoteResponseReceipt).count() == 1


def test_native_populated_downgrade_refusal_retains_running_customer_application(journey):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('Native PostgreSQL migration/application retain-schema recovery required')
    from alembic import command
    from backend.migration_runtime import alembic_config
    db.session.rollback()
    config = alembic_config(db.engine.url.render_as_string(hide_password=False))
    with pytest.raises(RuntimeError, match='FWD05 history/policy exists'):
        command.downgrade(config, '20260916_fwd03_transport_intent')
    # Refusal-before-DDL is useful recovery only if the current application
    # still reads its grant and can perform an ordinary authorized transaction.
    client = journey.app.test_client()
    read = client.get(_path(journey), headers=_headers(journey))
    assert read.status_code == 200 and read.json['quote']['amount_exact'] == '1234.50'
    response = client.post(_path(journey), json=_payload(journey),
        headers={**_headers(journey), 'Idempotency-Key': 'retained-schema-app'})
    assert response.status_code == 200
    assert db.session.query(QuoteResponseFact).count() == db.session.query(QuoteResponseReceipt).count() == 1
