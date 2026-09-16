"""ADR-045 deterministic slice proof; same behavior on SQLite and real PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import os
from threading import Event

import pytest
from flask import g
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from backend import create_app
from backend.extensions import db
from backend.models import Customer, CustomerGamification, ExpertQuote, ExpertUser, ShipmentRequest
from backend.notification_models import NotificationAction, NotificationAttempt, now
from backend.notification_provider import FakeEmailProvider, ProviderResult
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalOutbox
from backend.services import notification_action_service as service
from backend.services import outbox_service, quote_service
from backend.services.quote_notification_contract import EVENT, NotificationDenied


@pytest.fixture(params=['sqlite', 'postgresql'])
def app(request):
    url = 'sqlite:///:memory:'
    if request.param == 'postgresql':
        url = os.environ.get('FWD01_QUALIFICATION_DATABASE_URL')
        if not url:
            pytest.skip('FWD-01 disposable PostgreSQL URL required; SQLite is not concurrency proof')
        parsed = make_url(url)
        assert parsed.host == '127.0.0.1' and parsed.database.startswith('forwarder_fwd01_test_')
    application = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': url,
        'NOTIFICATION_PROVIDER': 'fake', 'NOTIFICATION_ENVIRONMENT': 'qualification'}, skip_startup=True)
    with application.app_context():
        if request.param == 'sqlite':
            db.create_all()
        else:
            # Explicit disposable DB only. Migration gate upgrades it beforehand.
            names = [n for n in inspect(db.engine).get_table_names() if n != 'alembic_version']
            assert 'notification_action' in names
            quoted = ','.join(db.engine.dialect.identifier_preparer.quote(n) for n in names)
            # Qualification-only cleanup uses DBAPI, outside runtime census
            # repository. The loopback/database-name assertions above are mandatory.
            connection = db.engine.raw_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('TRUNCATE ' + quoted + ' RESTART IDENTITY CASCADE')
                connection.commit()
            finally:
                connection.close()
        yield application
        db.session.remove()


def seed():
    org = OperationalOrganization(name='Synthetic A')
    other_org = OperationalOrganization(name='Synthetic B')
    actor = ExpertUser(username='fwd01', full_name='Synthetic Expert', password_hash='unused', role='expert', authority='EXPERT', is_active=True)
    foreign = ExpertUser(username='fwd01-other', full_name='Other Expert', password_hash='unused', role='expert', authority='EXPERT', is_active=True)
    db.session.add_all([org, other_org, actor, foreign]); db.session.flush()
    db.session.add_all([OperationalMembership(user_id=actor.id, organization_id=org.id, permissions=[]),
                        OperationalMembership(user_id=foreign.id, organization_id=other_org.id, permissions=[])])
    customer = Customer(first_name='Synthetic', last_name='Only', email='customer@example.test',
                        ownership_scope='TENANT', operational_organization_id=org.id, status='active')
    verified = CustomerGamification(email='customer@example.test', phone='09000000000', is_email_verified=True)
    db.session.add_all([customer, verified]); db.session.flush()
    req = ShipmentRequest(contact_phone='09000000000', assigned_to=actor.id, status='in_progress',
        ownership_scope='TENANT', operational_organization_id=org.id, customer_id=customer.id,
        gamification_customer_id=verified.id)
    db.session.add(req); db.session.commit()
    return {'actor': actor.id, 'foreign': foreign.id, 'org': org.id, 'other_org': other_org.id,
            'request': req.id, 'customer': customer.id, 'verified': verified.id}


def quote(ids):
    return quote_service.create_quote_for_request(ids['request'], {'amount': 125, 'valid_until': str(date.today() + timedelta(days=3))}, {'id': ids['actor'], 'role': 'expert'})['quote']['id']


def prepared():
    ids = seed(); ids['quote'] = quote(ids); ids['action'] = service.consume_one()
    assert db.session.get(NotificationAction, ids['action']).state == 'PREPARED'
    db.session.rollback()
    return ids


def test_full_chain_and_controlled_commands(app, caplog):
    ids = prepared()
    with app.test_request_context():
        with pytest.raises(NotificationDenied):
            service.prepare(ids['action'])  # no identity passed by caller can grant authority
        g.current_user_id = ids['foreign']
        with pytest.raises(NotificationDenied):
            service.result(ids['action'])
        g.current_user_id = ids['actor']
        assert service.propose(ids['action'])['can_prepare']
        assert service.prepare(ids['action'])['intent_digest']
        assert service.approve_when_required(ids['action'])['authority'] == 'quote-available.v1'
        assert service.execute(ids['action'])
        result = service.result(ids['action'])
        assert result['state'] == 'SENT' and result['attempts'][0]['simulated'] is True
        assert result['attempts'][0]['provider'] == 'fake-email.v1'
        assert not service.execute(ids['action'])
    assert NotificationAttempt.query.count() == 1
    assert db.session.get(ShipmentRequest, ids['request']).status == 'waiting_for_customer'
    assert 'customer@example.test' not in caplog.text


def test_business_transaction_rollback_leaves_no_event(app, monkeypatch):
    ids = seed()
    original = outbox_service.record_event
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        db.session.flush()
        raise RuntimeError('injected after outbox flush')
    monkeypatch.setattr(outbox_service, 'record_event', fail)
    with pytest.raises(RuntimeError):
        quote(ids)
    db.session.rollback()
    assert ExpertQuote.query.count() == OperationalOutbox.query.count() == 0
    assert db.session.get(ShipmentRequest, ids['request']).status == 'in_progress'


def test_consumer_crash_replay_and_unrelated_event_preserved(app, monkeypatch):
    ids = seed(); quote(ids)
    other = outbox_service.record_event(ids['org'], 'milestone.reported', 'Milestone', 1)
    db.session.commit(); other_id = other.id
    original = db.session.commit
    monkeypatch.setattr(db.session, 'commit', lambda: (_ for _ in ()).throw(RuntimeError('before commit')))
    with pytest.raises(RuntimeError):
        service.consume_one()
    monkeypatch.setattr(db.session, 'commit', original)
    assert NotificationAction.query.count() == 0
    action_id = service.consume_one()
    db.session.remove()  # worker dies after successful commit
    assert service.consume_one() is None
    event = OperationalOutbox.query.filter_by(event_type=EVENT).one()
    event.published_at = None; db.session.commit()  # explicit replay of same event
    assert service.consume_one() == action_id
    assert NotificationAction.query.count() == 1
    assert db.session.get(OperationalOutbox, other_id).published_at is None


def test_distinct_quotes_and_old_quote_suppression(app):
    ids = prepared(); second = quote(ids)
    second_action = service.consume_one()
    assert second != ids['quote'] and second_action != ids['action']
    assert not service._dispatch(ids['action'])
    assert db.session.get(NotificationAction, ids['action']).reason == 'QUOTE_NOT_AVAILABLE'
    assert service._dispatch(second_action)


def test_same_quote_cannot_emit_duplicate_logical_event(app):
    from sqlalchemy.exc import IntegrityError
    ids = seed(); quote_id = quote(ids)
    outbox_service.record_event(ids['org'], EVENT, 'ExpertQuote', quote_id, {})
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert OperationalOutbox.query.filter_by(event_type=EVENT).count() == 1


@pytest.mark.parametrize('change', ['membership', 'actor', 'authority', 'platform_authority', 'unknown_authority', 'assignment', 'recipient', 'verified', 'quote', 'response', 'status', 'approval', 'channel', 'policy', 'ambiguous_membership'])
def test_execution_revalidates_prepared_intent(app, change):
    ids = prepared()
    if change == 'membership':
        OperationalMembership.query.filter_by(user_id=ids['actor']).one().is_active = False
    elif change == 'actor':
        db.session.get(ExpertUser, ids['actor']).is_active = False
    elif change == 'authority':
        db.session.get(ExpertUser, ids['actor']).authority = 'ORGANIZATION_ADMIN'
        OperationalMembership.query.filter_by(user_id=ids['actor']).one().permissions = ['request.quote']
    elif change == 'platform_authority':
        db.session.get(ExpertUser, ids['actor']).authority = 'PLATFORM_ADMIN'
    elif change == 'unknown_authority':
        db.session.get(ExpertUser, ids['actor']).authority = 'UNRECOGNIZED'
    elif change == 'assignment':
        db.session.get(ShipmentRequest, ids['request']).assigned_to = ids['foreign']
    elif change == 'recipient':
        db.session.get(Customer, ids['customer']).email = 'changed@example.test'
        db.session.get(CustomerGamification, ids['verified']).email = 'changed@example.test'
    elif change == 'verified':
        db.session.get(CustomerGamification, ids['verified']).is_email_verified = False
    elif change == 'quote':
        db.session.get(ExpertQuote, ids['quote']).amount = 999
    elif change == 'response':
        db.session.get(ExpertQuote, ids['quote']).customer_response = 'declined'
    elif change == 'status':
        db.session.get(ShipmentRequest, ids['request']).status = 'closed'
    elif change == 'approval':
        db.session.get(NotificationAction, ids['action']).approval = 'approved=true'
    elif change == 'channel':
        db.session.get(NotificationAction, ids['action']).channel = 'SMS'
    elif change == 'policy':
        db.session.get(NotificationAction, ids['action']).policy = 'forged'
    else:
        db.session.add(OperationalMembership(user_id=ids['actor'], organization_id=ids['other_org'], permissions=[]))
    if change == 'unknown_authority' and db.engine.dialect.name == 'postgresql':
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db.session.commit()  # Existing PostgreSQL authority constraint denies earlier.
        db.session.rollback()
        assert NotificationAttempt.query.count() == 0
        return
    db.session.commit()
    assert not service._dispatch(ids['action'])
    assert NotificationAttempt.query.count() == 0
    assert db.session.get(NotificationAction, ids['action']).state == 'BLOCKED'


def test_missing_recipient_preserves_business_and_observable_block(app):
    ids = seed()
    db.session.get(ShipmentRequest, ids['request']).gamification_customer_id = None
    db.session.commit(); quote(ids)
    action = db.session.get(NotificationAction, service.consume_one())
    assert action.state == 'BLOCKED'
    assert db.session.get(ShipmentRequest, ids['request']).status == 'waiting_for_customer'
    assert NotificationAttempt.query.count() == 0


def test_failure_backoff_exhaustion_and_business_preservation(app):
    ids = prepared(); app.config['NOTIFICATION_FAKE_OUTCOME'] = 'FAILED'
    for i in range(3):
        assert service._dispatch(ids['action'])
        action = db.session.get(NotificationAction, ids['action'])
        if i < 2:
            assert action.next_attempt_at is not None
            assert not service._dispatch(ids['action'])
            action = db.session.get(NotificationAction, ids['action'])
            action.next_attempt_at = now() - timedelta(seconds=1); db.session.commit()
    assert db.session.get(NotificationAction, ids['action']).state == 'FAILED'
    assert NotificationAttempt.query.count() == 3
    assert db.session.get(ShipmentRequest, ids['request']).status == 'waiting_for_customer'


def test_unknown_reconcile_and_stale_worker_fence(app):
    ids = prepared(); token = service._claim(ids['action'])
    attempt = db.session.get(NotificationAttempt, token[2]); attempt.lease_until = now() - timedelta(seconds=1)
    db.session.commit()
    assert service.recover_expired() == 1
    assert not service._dispatch(ids['action'])
    assert not service._apply_result(token, ProviderResult('SENT', token[3], 'SIMULATED_SENT'))
    assert service.reconcile(ids['action'])  # default remains UNKNOWN
    assert db.session.get(NotificationAction, ids['action']).state == 'UNKNOWN'
    app.config['NOTIFICATION_FAKE_RECONCILIATION'] = 'FAILED'
    assert service.reconcile(ids['action'])
    action = db.session.get(NotificationAction, ids['action']); action.next_attempt_at = now() - timedelta(seconds=1); db.session.commit()
    assert service._dispatch(ids['action'])
    assert not service._apply_result(token, ProviderResult('DELIVERED', token[3], 'SIMULATED_DELIVERED'))
    assert db.session.get(NotificationAction, ids['action']).state == 'SENT'
    assert NotificationAttempt.query.count() == 2


def test_provider_exception_redacted_and_no_fallback(app, monkeypatch, caplog):
    ids = prepared(); app.config['NOTIFICATION_PROVIDER'] = 'unconfigured'
    with pytest.raises(ValueError, match='EXPLICIT_FAKE'):
        service._dispatch(ids['action'])
    assert NotificationAttempt.query.count() == 0
    app.config['NOTIFICATION_PROVIDER'] = 'fake'
    def fail(**kwargs):
        raise RuntimeError('DO_NOT_LOG_PRIVATE_PROVIDER_DETAIL')
    monkeypatch.setattr(FakeEmailProvider, 'send', lambda self, **kwargs: fail(**kwargs))
    assert service._dispatch(ids['action'])
    assert db.session.get(NotificationAction, ids['action']).state == 'UNKNOWN'
    assert 'DO_NOT_LOG_PRIVATE_PROVIDER_DETAIL' not in caplog.text


def test_cross_tenant_recipient_cannot_be_attached(app):
    ids = prepared()
    foreign = Customer(first_name='Foreign', last_name='Synthetic', email='foreign@example.test',
        ownership_scope='TENANT', operational_organization_id=ids['other_org'])
    db.session.add(foreign); db.session.commit(); foreign_id = foreign.id
    db.session.get(ShipmentRequest, ids['request']).customer_id = foreign_id
    db.session.commit()  # Legacy FK permits this: new action boundary must deny.
    assert not service._dispatch(ids['action'])
    assert NotificationAttempt.query.count() == 0
    assert db.session.get(NotificationAction, ids['action']).state == 'BLOCKED'


@pytest.mark.parametrize('outcome', ['ACCEPTED', 'DELIVERED', 'UNKNOWN'])
def test_provider_outcomes_and_duplicate_results(app, outcome):
    ids = prepared(); app.config['NOTIFICATION_FAKE_OUTCOME'] = outcome
    assert service._dispatch(ids['action'])
    action = db.session.get(NotificationAction, ids['action'])
    assert action.state == outcome
    attempt = db.session.get(NotificationAttempt, action.active_attempt_id)
    token = (action.id, action.organization_id, attempt.id, attempt.provider_reference)
    assert not service._apply_result(token, ProviderResult('SENT', token[3], 'SIMULATED_SENT'))
    assert not service._dispatch(ids['action'])


def test_late_result_without_reaper_is_unknown(app):
    ids = prepared(); token = service._claim(ids['action'])
    attempt = db.session.get(NotificationAttempt, token[2]); attempt.lease_until = now() - timedelta(seconds=1)
    db.session.commit()
    assert service._apply_result(token, ProviderResult('SENT', token[3], 'SIMULATED_SENT'))
    assert db.session.get(NotificationAction, ids['action']).state == 'UNKNOWN'


def test_quarantined_target_cannot_dispatch(app):
    from backend.quarantine import OwnershipCertificationDecision
    ids = prepared()
    db.session.add(OwnershipCertificationDecision(entity_type='ShipmentRequest', entity_id=ids['request'],
        classification='QUARANTINED', census_id='fwd01-denied', decision_id='fwd01-denied'))
    db.session.commit(); db.session.remove()
    assert not service._dispatch(ids['action'])
    assert db.session.get(NotificationAction, ids['action']).state == 'BLOCKED'
    assert NotificationAttempt.query.count() == 0


def test_postgresql_competing_consumers(app):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL skip-locked consumer proof only')
    ids = seed(); quote(ids); db.session.remove()
    def consume():
        with app.app_context():
            return service.consume_one()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(consume), pool.submit(consume)]
        results = [f.result(timeout=10) for f in futures]
    assert len([value for value in results if value]) == 1
    assert NotificationAction.query.count() == 1


def test_postgresql_attempt_tenant_constraint(app):
    from sqlalchemy.exc import IntegrityError
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL physical FK proof only')
    ids = prepared()
    db.session.add(NotificationAttempt(organization_id=ids['other_org'], action_id=ids['action'],
        number=1, provider='fake-email.v1', provider_reference='synthetic-reference',
        simulated=True, outcome='IN_FLIGHT', reason='SYNTHETIC', lease_until=now()))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert NotificationAttempt.query.count() == 0


def test_real_api_quote_to_independent_worker(app):
    from backend.services.auth_session_service import create_session_tokens
    ids = seed()
    tokens = create_session_tokens(ids['actor'])
    public_id = db.session.get(ShipmentRequest, ids['request']).public_id
    db.session.commit()
    response = app.test_client().post('/api/expert/requests/' + public_id + '/quote',
        headers={'Authorization': 'Bearer ' + tokens['access_token']}, json={'amount': 999})
    assert response.status_code == 200
    db.session.remove()  # browser request/session has ended
    summary = service.run_batch()
    assert summary['dispatched'] == 1 and summary['simulated']
    assert NotificationAction.query.one().state == 'SENT'


def test_postgresql_competing_workers_release_locks_for_provider(app, monkeypatch):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('Row-lock proof requires PostgreSQL; SQLite companion behavior covered separately')
    ids = prepared(); db.session.remove()
    sending, finish = Event(), Event()
    original = FakeEmailProvider.send
    def slow(self, **kwargs):
        sending.set()
        assert finish.wait(10)
        return original(self, **kwargs)
    monkeypatch.setattr(FakeEmailProvider, 'send', slow)
    def dispatch():
        with app.app_context():
            return service._dispatch(ids['action'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(dispatch)
        assert sending.wait(10)
        try:
            assert pool.submit(dispatch).result(timeout=5) is False
            # Revocation AFTER the durable decision is allowed to commit even
            # while provider is blocked: no network-duration database lock.
            actor = db.session.get(ExpertUser, ids['actor']); actor.is_active = False
            db.session.commit()
        finally:
            finish.set()
        assert first.result(timeout=10)
    assert NotificationAttempt.query.count() == 1


@pytest.mark.parametrize('mutation', ['actor', 'assignment', 'membership'])
def test_postgresql_revocation_commits_before_dispatch_decision(app, mutation):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('Real PostgreSQL ordering proof only')
    ids = prepared(); db.session.remove()
    started = Event()
    def dispatch():
        with app.app_context():
            started.set()
            return service._dispatch(ids['action'])
    with ThreadPoolExecutor(max_workers=1) as pool:
        if mutation == 'actor':
            db.session.get(ExpertUser, ids['actor']).is_active = False
        elif mutation == 'assignment':
            db.session.get(ShipmentRequest, ids['request']).assigned_to = ids['foreign']
        else:
            OperationalMembership.query.filter_by(user_id=ids['actor']).one().is_active = False
        db.session.flush()  # real competing transaction holds row update lock
        future = pool.submit(dispatch); assert started.wait(10)
        db.session.commit()
        assert future.result(timeout=10) is False
    assert NotificationAttempt.query.count() == 0
