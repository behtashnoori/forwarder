"""Synthetic command/API evidence only; SQLite never proves PG races or Browser UAT."""
import base64
import secrets
from uuid import uuid4
from datetime import date, timedelta
import pytest
from backend import create_app
from backend.extensions import db
from backend.models import Customer, CustomerGamification, ExpertUser, ShipmentRequest, ExpertQuote
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalOutbox
from backend.quote_response_models import QuoteResponseGrant, QuoteResponseFact, QuoteResponseReceipt
from backend.notification_provider import PrivateQuoteCapture
from backend.services.quote_response_authorization import qualification_key_policy
from backend.services.quote_service import create_quote_for_request
from backend.services.notification_action_service import consume_one, _dispatch


class SyntheticJourney:
    def __repr__(self):
        return '<SyntheticJourney: capability/private material redacted>'


@pytest.fixture(params=['sqlite', 'postgresql'])
def journey(request):
    fixture = SyntheticJourney()
    capture = PrivateQuoteCapture()
    fixture.capture = capture
    url = 'sqlite:///:memory:'
    administrator = None
    if request.param == 'postgresql':
        from backend.tests.test_fwd05_postgresql import own_url
        from sqlalchemy import create_engine
        from sqlalchemy.engine import make_url
        from alembic import command
        from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
        own = own_url()
        database = 'fwd05_runtime_' + uuid4().hex
        administrator = create_engine(own, isolation_level='AUTOCOMMIT')
        with administrator.connect() as connection:
            connection.exec_driver_sql('CREATE DATABASE ' + database)
        url = make_url(own).set(database=database).render_as_string(hide_password=False)
        config = alembic_config(url)
        prepare_version_table_for_upgrade(url, config)
        command.upgrade(config, '20260916_fwd05_quote_response')
    fixture.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': url,
        'NOTIFICATION_PROVIDER': 'fake', 'NOTIFICATION_ENVIRONMENT': 'qualification',
        'QUOTE_CAPABILITY_KEYRING': {'new': {'material': base64.b64encode(secrets.token_bytes(64)).decode(), 'state': 'ACTIVE'}},
        'QUOTE_CAPABILITY_ACTIVE_KEY': 'new', 'QUOTE_CAPABILITY_POLICY_EPOCH': 1,
        'QUOTE_CAPABILITY_PRIVATE_CAPTURE': capture,
        'QUOTE_CAPABILITY_CUSTOMER_ORIGIN': 'http://127.0.0.1:8085',
        'QUOTE_CAPABILITY_ALLOWED_ORIGINS': ['http://127.0.0.1:8085']}, skip_startup=True)
    with fixture.app.app_context():
        db.create_all()
        org = OperationalOrganization(name='synthetic', quotation_validity_timezone='America/New_York')
        expert = ExpertUser(username='synthetic-fwd05-expert', password_hash='synthetic-unusable',
            full_name='کارشناس آزمون', authority='EXPERT', role='expert', is_active=True)
        verified = CustomerGamification(email='synthetic@example.test', phone='09000000001', is_email_verified=True)
        db.session.add_all([org, expert, verified]); db.session.flush()
        customer = Customer(operational_organization_id=org.id, ownership_scope='TENANT',
            first_name='Synthetic', last_name='Customer', email=verified.email, status='active')
        db.session.add(customer); db.session.flush()
        db.session.add(OperationalMembership(organization_id=org.id, user_id=expert.id, is_active=True, permissions=[]))
        root = ShipmentRequest(shipping_type='domestic', contact_phone='09000000001', ownership_scope='TENANT',
            operational_organization_id=org.id, customer_id=customer.id, gamification_customer_id=verified.id,
            assigned_to=expert.id, status='assigned')
        db.session.add(root); db.session.flush()
        fixture.root_id, fixture.expert_id, fixture.customer_id = root.id, expert.id, customer.id
        qualification_key_policy(); db.session.commit()
        result = create_quote_for_request(root.id, {'amount': '1234.50', 'currency': 'EUR',
            'note': 'پیشنهاد مصنوعی', 'valid_until': (date.today() + timedelta(days=3)).isoformat()}, {'id': expert.id})
        fixture.quote_public_id = result['quote']['public_id']
        fixture.quote_id = result['quote']['id']
        fixture.content_digest = result['quote']['content_digest']
        action_id = consume_one()
        assert _dispatch(action_id)
        from backend.notification_models import NotificationAction, NotificationAttempt
        action = db.session.get(NotificationAction, action_id)
        attempt = db.session.get(NotificationAttempt, action.active_attempt_id)
        _recipient, link = capture.consume_for_fixture(attempt.provider_reference)
        fixture.token = link.split('#', 1)[1]
        yield fixture
        capture.clear(); db.session.remove()
        if request.param == 'sqlite':
            db.drop_all()
        else:
            db.engine.dispose()
            with administrator.connect() as connection:
                connection.exec_driver_sql('DROP DATABASE ' + database)
            administrator.dispose()


def _headers(fixture):
    return {'Authorization': 'QuoteCapability ' + fixture.token}


def _payload(fixture, response='negotiation_requested', version=0):
    return {'response': response, 'content_revision': 1, 'content_digest': fixture.content_digest,
        'expected_response_version': version, 'reason': 'CUSTOMER_DECISION'}


@pytest.mark.parametrize('claim', ['tenant','request','quote','content_digest','jti','sub'])
def test_signed_and_digest_consistent_synthetic_grant_still_requires_exact_live_binding(journey, claim):
    from backend.census_context import census_unit_of_work
    from backend.services.quote_capability_crypto import QuoteKeyring, token_digest
    source=db.session.query(QuoteResponseGrant).one()
    identity=str(uuid4())
    claims={**source.claims,'jti':identity}
    claims[claim]='0'*64 if claim=='content_digest' else str(uuid4())
    token=QuoteKeyring(journey.app.config).sign(claims,source.key_version,new=True)
    values={column.name:getattr(source,column.name) for column in source.__table__.columns}
    values.update(id=identity,claims=claims,token_digest=token_digest(token))
    # Deliberately inconsistent trusted-row fixture reaches live binding checks:
    # signature and exact stored digest are both valid, not masking the threat.
    with census_unit_of_work(db.session):
        db.session.add(QuoteResponseGrant(**values));db.session.commit()
    path='/api/quote-capability/quotes/'+journey.quote_public_id
    headers={'Authorization':'QuoteCapability '+token}
    client=journey.app.test_client()
    assert client.get(path,headers=headers).status_code==403
    assert client.post(path,headers={**headers,'Idempotency-Key':'bad-binding'},json=_payload(journey)).status_code==403
    assert db.session.query(QuoteResponseFact).count()==db.session.query(QuoteResponseReceipt).count()==0


@pytest.mark.parametrize('attack', ['wrong_key','unknown_kid','wrong_typ','wrong_issuer','wrong_audience',
    'wrong_token_type','wrong_algorithm','internal_access','internal_refresh','capability_as_staff'])
def test_actual_api_rejects_wrong_crypto_purpose_and_internal_token_families(journey, attack):
    import jwt
    from backend.services.quote_capability_crypto import TYPE
    source=db.session.query(QuoteResponseGrant).one()
    client=journey.app.test_client()
    path='/api/quote-capability/quotes/'+journey.quote_public_id
    if attack=='capability_as_staff':
        root_public_id=db.session.get(ShipmentRequest,journey.root_id).public_id
        result=client.get('/api/expert/requests/'+root_public_id+'/quote/latest',
            headers={'Authorization':'Bearer '+journey.token})
    else:
        if attack in {'internal_access','internal_refresh'}:
            from backend.services.auth_session_service import create_session_tokens
            tokens=create_session_tokens(journey.expert_id);db.session.commit()
            token=tokens['access_token' if attack=='internal_access' else 'refresh_token']
        else:
            claims=dict(source.claims)
            headers={'typ':TYPE,'kid':source.key_version}
            material=base64.b64decode(journey.app.config['QUOTE_CAPABILITY_KEYRING'][source.key_version]['material'])
            algorithm='HS256'
            if attack=='wrong_key': material=secrets.token_bytes(64)
            elif attack=='unknown_kid': headers['kid']='unregistered'
            elif attack=='wrong_typ': headers['typ']='JWT'
            elif attack=='wrong_issuer': claims['iss']='another-purpose'
            elif attack=='wrong_audience': claims['aud']='internal-staff'
            elif attack=='wrong_token_type': claims['token_type']='access'
            elif attack=='wrong_algorithm': algorithm='HS512'
            token=jwt.encode({key:claims[key] for key in sorted(claims)},material,algorithm=algorithm,headers=headers)
        result=client.get(path,headers={'Authorization':'QuoteCapability '+token})
    assert result.status_code==(401 if attack=='capability_as_staff' else 403)
    assert db.session.query(QuoteResponseFact).count()==db.session.query(QuoteResponseReceipt).count()==0


def test_synthetic_prior_receipt_replays_after_write_expiry_only_while_live_read_grant_remains(journey):
    import calendar
    from decimal import Decimal
    from backend.census_context import census_unit_of_work
    from backend.services.governed_quote_service import resolve_expiry, content_snapshot, fact_projection
    from backend.services.quote_capability_crypto import QuoteKeyring, ISSUER, AUDIENCE, token_digest
    from backend.services.quote_notification_contract import digest
    from backend.services.quote_service import manage_quote_capability
    current=db.session.query(QuoteResponseGrant).one()
    source=db.session.get(ShipmentRequest,journey.root_id)
    organization=db.session.get(OperationalOrganization,source.operational_organization_id)
    local_date=date.today()-timedelta(days=1)
    expiry=resolve_expiry(local_date,'America/New_York')
    issued,received,horizon=expiry-timedelta(days=2),expiry-timedelta(hours=1),expiry+timedelta(days=30)
    # All prior timestamps/data are explicit synthetic fixtures with correct
    # issued < received < write expiry < current DB time. This is not a real
    # historical replay proof or a backfill path in the product.
    with census_unit_of_work(db.session):
        root=ShipmentRequest(shipping_type='domestic',contact_phone='09000000001',ownership_scope='TENANT',
            operational_organization_id=organization.id,customer_id=source.customer_id,gamification_customer_id=source.gamification_customer_id,
            assigned_to=journey.expert_id,status='waiting_for_customer')
        db.session.add(root);db.session.flush()
        quote=ExpertQuote(shipment_request_id=root.id,operational_organization_id=organization.id,
            created_by_expert_id=journey.expert_id,amount=None,amount_exact=Decimal('42.50'),currency='EUR',
            public_id=str(uuid4()),money_contract='quote-major.v1',content_revision=1,response_version=1,
            customer_response='negotiation_requested',response_received_at=received,responded_at=received.replace(tzinfo=None),
            created_at=issued.replace(tzinfo=None),published_at=issued,expires_at=expiry,valid_until=local_date,
            validity_timezone='America/New_York',validity_policy='TIME-BIZ-003.v1')
        quote.content_digest=digest(content_snapshot(quote));db.session.add(quote);db.session.flush()
        identity,subject=str(uuid4()),str(uuid4())
        claims={'iss':ISSUER,'aud':AUDIENCE,'token_type':'quote-response','v':1,'sub':subject,'jti':identity,
            'iat':calendar.timegm(issued.utctimetuple()),'nbf':calendar.timegm(issued.utctimetuple()),
            'exp':calendar.timegm(horizon.utctimetuple()),'tenant':organization.public_id,'request':root.public_id,
            'quote':quote.public_id,'revision':1,'content_digest':quote.content_digest}
        token=QuoteKeyring(journey.app.config).sign(claims,current.key_version,new=True)
        grant=QuoteResponseGrant(id=identity,organization_id=organization.id,request_id=root.id,quote_id=quote.id,
            customer_id=root.customer_id,verified_customer_id=root.gamification_customer_id,subject=subject,
            claims=claims,key_version=current.key_version,token_digest=token_digest(token),recipient_hash=current.recipient_hash,
            root_generation=0,customer_generation=current.customer_generation,verified_generation=current.verified_generation,
            issued_at=issued,read_expires_at=horizon,write_expires_at=expiry)
        db.session.add(grant);db.session.flush()
        fact=QuoteResponseFact(id=str(uuid4()),organization_id=organization.id,request_id=root.id,quote_id=quote.id,
            grant_id=grant.id,subject=subject,sequence=1,prior_response=None,response='negotiation_requested',reason='CUSTOMER_DECISION',
            snapshot=content_snapshot(quote),response_received_at=received,recorded_at=received)
        db.session.add(fact);db.session.flush()
        payload={'response':'negotiation_requested','content_revision':1,'content_digest':quote.content_digest,
            'expected_response_version':0,'reason':'CUSTOMER_DECISION'}
        result={'receipt_id':str(uuid4()),'fact':fact_projection(fact),'response_version':1,'noop':False}
        receipt=QuoteResponseReceipt(id=result['receipt_id'],organization_id=organization.id,request_id=root.id,quote_id=quote.id,
            grant_id=grant.id,fact_id=fact.id,idempotency_key='pre-expiry-synthetic',request_digest=digest(payload),result=result,recorded_at=received)
        db.session.add(receipt);db.session.commit()
    path='/api/quote-capability/quotes/'+quote.public_id
    headers={'Authorization':'QuoteCapability '+token,'Idempotency-Key':'pre-expiry-synthetic'}
    client=journey.app.test_client()
    replay=client.post(path,json=payload,headers=headers)
    assert replay.status_code==200 and replay.json==result
    fresh=client.post(path,json=payload,headers={**headers,'Idempotency-Key':'expired-new-key'})
    assert fresh.status_code==403
    manage_quote_capability(root.id,quote.public_id,{'id':journey.expert_id},'REVOKE')
    revoked=client.post(path,json=payload,headers=headers)
    assert revoked.status_code==403
    assert db.session.query(QuoteResponseFact).count()==db.session.query(QuoteResponseReceipt).count()==1


@pytest.mark.parametrize('age_days', [1, 31])
def test_actual_database_clock_expired_write_separate_read_horizon_and_reissue(journey, age_days):
    from decimal import Decimal
    from datetime import datetime, timezone
    from backend.census_context import census_unit_of_work
    from backend.services.governed_quote_service import content_snapshot, resolve_expiry
    from backend.services.quote_notification_contract import digest
    from backend.services.quote_response_authorization import lock_quote_scope, issue_grant, capability_for_adapter, aware
    from backend.services.quote_service import manage_quote_capability, QuoteAccessError
    from backend.services.quote_capability_crypto import CapabilityDenied
    from backend.notification_models import NotificationAction, NotificationAttempt
    source = db.session.get(ShipmentRequest, journey.root_id)
    org_id, customer_id, verified_id = source.operational_organization_id, source.customer_id, source.gamification_customer_id
    local_date = date.today() - timedelta(days=age_days)
    expiry = resolve_expiry(local_date, 'America/New_York')
    # A clearly synthetic prior publication fixture; the product publication
    # command still refuses expired dates. No clock is mocked or moved.
    with census_unit_of_work(db.session):
        root = ShipmentRequest(shipping_type='domestic',contact_phone='09000000001',ownership_scope='TENANT',
            operational_organization_id=org_id,customer_id=customer_id,gamification_customer_id=verified_id,
            assigned_to=journey.expert_id,status='waiting_for_customer')
        db.session.add(root); db.session.flush()
        quote = ExpertQuote(shipment_request_id=root.id,operational_organization_id=org_id,
            created_by_expert_id=journey.expert_id,amount=None,amount_exact=Decimal('42.50'),currency='EUR',
            public_id=str(uuid4()),money_contract='quote-major.v1',content_revision=1,response_version=0,
            valid_until=local_date,validity_timezone='America/New_York',validity_policy='TIME-BIZ-003.v1',
            published_at=expiry-timedelta(days=2),expires_at=expiry)
        quote.content_digest=digest(content_snapshot(quote))
        db.session.add(quote);db.session.commit()
    root_id, quote_public_id = root.id, quote.public_id
    scope=lock_quote_scope(root_id,actor_id=journey.expert_id)
    quote=next(q for q in scope['quotes'] if q.public_id==quote_public_id)
    if age_days==31:
        with pytest.raises(CapabilityDenied):
            issue_grant(quote,scope)
        db.session.rollback()
        with pytest.raises(QuoteAccessError):
            manage_quote_capability(root_id,quote_public_id,{'id':journey.expert_id},'REISSUE')
        return
    grant=issue_grant(quote,scope);grant_id=grant.id;horizon=aware(grant.read_expires_at);db.session.commit()
    token,_=capability_for_adapter(grant_id,write=False);db.session.rollback()
    path='/api/quote-capability/quotes/'+quote_public_id
    headers={'Authorization':'QuoteCapability '+token}
    client=journey.app.test_client()
    read=client.get(path,headers=headers)
    assert read.status_code==200 and read.json['can_respond'] is False
    assert client.post(path,headers={**headers,'Idempotency-Key':'expired-fresh'},json={
        'response':'accepted','content_revision':1,'content_digest':quote.content_digest,
        'expected_response_version':0,'reason':'CUSTOMER_DECISION'}).status_code==403
    manage_quote_capability(root_id,quote_public_id,{'id':journey.expert_id},'REISSUE')
    pending=consume_one();assert _dispatch(pending)
    action=db.session.get(NotificationAction,pending);attempt=db.session.get(NotificationAttempt,action.active_attempt_id)
    _,link=journey.capture.consume_for_fixture(attempt.provider_reference)
    new_token=link.split('#',1)[1]
    assert client.get(path,headers=headers).status_code==403
    reissued=client.get(path,headers={'Authorization':'QuoteCapability '+new_token})
    assert reissued.status_code==200 and reissued.json['can_respond'] is False
    new_grant=db.session.query(QuoteResponseGrant).filter_by(quote_id=quote.id,revoked_at=None).one()
    assert aware(new_grant.read_expires_at)==horizon


def test_real_owner_chain_exact_money_private_dispatch_and_customer_read(journey):
    response = journey.app.test_client().get('/api/quote-capability/quotes/' + journey.quote_public_id, headers=_headers(journey))
    assert response.status_code == 200
    assert response.json['quote']['amount_exact'] == '1234.50'
    assert response.json['quote']['amount'] is None
    assert response.json['quote']['validity_timezone'] == 'America/New_York'
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    assert db.session.get(ExpertQuote, journey.quote_id).amount is None
    assert journey.token not in str(db.session.query(OperationalOutbox.payload).all())


def test_negotiation_final_replay_and_append_only_facts(journey):
    client = journey.app.test_client()
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    headers = {**_headers(journey), 'Idempotency-Key': 'synthetic-first'}
    first = client.post(path, headers=headers, json=_payload(journey))
    assert first.status_code == 200
    replay = client.post(path, headers=headers, json=_payload(journey))
    assert replay.status_code == 200 and replay.json == first.json
    final = client.post(path, headers={**_headers(journey), 'Idempotency-Key': 'synthetic-final'},
        json=_payload(journey, 'accepted', 1))
    assert final.status_code == 200 and final.json['response_version'] == 2
    assert db.session.query(QuoteResponseFact).count() == 2
    assert db.session.query(QuoteResponseReceipt).count() == 2
    assert db.session.get(ShipmentRequest, journey.root_id).status == 'waiting_for_customer'
    from backend.economics_models import EconomicObservation
    from backend.operational_models import OperationalShipment
    assert db.session.query(EconomicObservation).count() == db.session.query(OperationalShipment).count() == 0


def test_legacy_cookie_staff_wrong_scope_and_origin_are_denied(journey):
    client = journey.app.test_client()
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    assert client.post('/api/customer/quote-response/arbitrary', json={'response': 'accepted'}).status_code == 403
    assert client.post(path, json=_payload(journey)).status_code == 403
    assert client.get(path, headers={'Authorization': 'Bearer ' + journey.token}).status_code == 403
    assert client.get('/api/quote-capability/quotes/00000000-0000-4000-8000-000000000000', headers=_headers(journey)).status_code == 403
    denied = client.post(path, headers={**_headers(journey), 'Origin': 'http://127.0.0.1:9999'}, json=_payload(journey))
    assert denied.status_code == 403 and 'Access-Control-Allow-Origin' not in denied.headers
    assert db.session.query(QuoteResponseFact).count() == 0


def test_revocation_denies_read_and_successful_replay(journey):
    client = journey.app.test_client()
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    headers = {**_headers(journey), 'Idempotency-Key': 'synthetic-revoke'}
    assert client.post(path, headers=headers, json=_payload(journey)).status_code == 200
    grant = db.session.query(QuoteResponseGrant).one()
    from backend.services.quote_response_authorization import database_instant
    grant.revoked_at, grant.revoked_reason = database_instant(), 'OWNER_REVOKED'
    db.session.commit()
    assert client.get(path, headers=_headers(journey)).status_code == 403
    assert client.post(path, headers=headers, json=_payload(journey)).status_code == 403
    assert db.session.query(QuoteResponseFact).count() == 1


def test_exact_governed_quote_read_adapter_keeps_existing_manual_economic_confirmation(journey):
    from backend.census_context import census_unit_of_work
    from backend.models import ServiceType
    from backend.operational_models import OperationalShipment
    from backend.economics_models import EconomicObservation
    from backend.services import economics_service
    client=journey.app.test_client()
    path='/api/quote-capability/quotes/'+journey.quote_public_id
    accepted=client.post(path,json=_payload(journey,'accepted'),headers={**_headers(journey),'Idempotency-Key':'manual-adapter-accept'})
    assert accepted.status_code==200
    assert db.session.query(EconomicObservation).count()==db.session.query(OperationalShipment).count()==0
    root=db.session.get(ShipmentRequest,journey.root_id)
    membership=db.session.query(OperationalMembership).filter_by(user_id=journey.expert_id).one()
    membership.permissions=['economics.revenue.view','economics.commitment.create']
    # Explicit synthetic operation fixture; customer acceptance did not create it.
    with census_unit_of_work(db.session):
        service=ServiceType(immutable_code='FWD05-FREIGHT',fa_name='Freight',en_name='Freight',is_active=True)
        shipment=OperationalShipment(organization_id=root.operational_organization_id,shipment_request_id=root.id,
            customer_id=root.customer_id,accepted_quote_id=journey.quote_id,source_type='accepted_quote',
            lifecycle_status='planned',created_by_user_id=journey.expert_id)
        db.session.add_all([service,shipment]);db.session.commit()
    preview=economics_service.quote_preview(shipment.public_id,{'id':journey.expert_id})
    assert preview['commercial_intent']['amount']=='1234.50'
    assert preview['commercial_intent']['accepted_at']==accepted.json['fact']['response_received_at']
    assert db.session.query(EconomicObservation).count()==0
    confirmed=economics_service.quote_confirm(shipment.public_id,{'service_public_id':service.public_id,
        'authority':'explicit synthetic manual confirmation','reason':'exact source adapter qualification',
        'idempotency_key':'manual-source-confirm'},{'id':journey.expert_id})
    assert confirmed['line']['observations'][0]['money']['amount']=='1234.500000'


def test_reissue_revokes_old_capability_preserves_original_horizon_and_private_delivery(journey):
    from backend.services.quote_service import manage_quote_capability
    from backend.notification_models import NotificationAction, NotificationAttempt
    old = db.session.query(QuoteResponseGrant).one()
    horizon, old_id = old.read_expires_at, old.id
    result = manage_quote_capability(journey.root_id, journey.quote_public_id,
        {'id': journey.expert_id}, 'REISSUE')
    assert result['state'] == 'PREPARED'
    assert journey.token not in str(result)
    grants = db.session.query(QuoteResponseGrant).all()
    assert len(grants) == 2 and all(g.read_expires_at == horizon for g in grants)
    assert db.session.get(QuoteResponseGrant, old_id).revoked_reason == 'REISSUED'
    client = journey.app.test_client()
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    assert client.get(path, headers=_headers(journey)).status_code == 403
    action_id = consume_one()
    assert _dispatch(action_id)
    action = db.session.get(NotificationAction, action_id)
    attempt = db.session.get(NotificationAttempt, action.active_attempt_id)
    _, link = journey.capture.consume_for_fixture(attempt.provider_reference)
    replacement = link.split('#', 1)[1]
    assert replacement != journey.token
    assert client.get(path, headers={'Authorization': 'QuoteCapability ' + replacement}).status_code == 200
    assert db.session.query(ExpertQuote).count() == 1


def test_recipient_change_away_and_back_cannot_revive_existing_grant(journey):
    customer = db.session.get(Customer, journey.customer_id)
    original = customer.email
    customer.email = 'other@example.test'
    db.session.commit()
    customer.email = original
    db.session.commit()
    assert customer.quote_recipient_generation == 2
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    assert journey.app.test_client().get(path, headers=_headers(journey)).status_code == 403


@pytest.mark.parametrize('change', ['crm_status', 'verified_email', 'verification', 'crm_link', 'verified_link'])
def test_every_recipient_generation_invalidates_read_write_and_existing_receipt_replay(journey, change):
    client = journey.app.test_client()
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    headers = {**_headers(journey), 'Idempotency-Key': 'generation-receipt'}
    assert client.post(path, json=_payload(journey), headers=headers).status_code == 200
    root = db.session.get(ShipmentRequest, journey.root_id)
    if change == 'crm_status':
        target, field, temporary = db.session.get(Customer, journey.customer_id), 'status', 'inactive'
    elif change in {'verified_email', 'verification'}:
        target = db.session.get(CustomerGamification, root.gamification_customer_id)
        field, temporary = ('email', 'other@example.test') if change == 'verified_email' else ('is_email_verified', False)
    else:
        target = root
        field = 'customer_id' if change == 'crm_link' else 'gamification_customer_id'
        temporary = None
    original, generation = getattr(target, field), target.quote_recipient_generation
    setattr(target, field, temporary); db.session.commit()
    assert target.quote_recipient_generation == generation + 1
    assert client.get(path, headers=_headers(journey)).status_code == 403
    assert client.post(path, json=_payload(journey), headers=headers).status_code == 403
    setattr(target, field, original); db.session.commit()
    assert target.quote_recipient_generation == generation + 2
    assert client.get(path, headers=_headers(journey)).status_code == 403
    assert client.post(path, json=_payload(journey), headers=headers).status_code == 403
    assert client.post(path, json=_payload(journey, 'accepted', 1),
        headers={**_headers(journey), 'Idempotency-Key': 'generation-new'}).status_code == 403
    assert db.session.query(QuoteResponseFact).count() == db.session.query(QuoteResponseReceipt).count() == 1


def test_response_inbox_and_external_dependency_are_atomic_and_replay_does_not_duplicate(journey):
    from backend.models import ExpertConsoleNotification
    from backend.notification_models import NotificationAction
    client = journey.app.test_client()
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    headers = {**_headers(journey), 'Idempotency-Key': 'inbox-proof'}
    assert client.post(path, json=_payload(journey), headers=headers).status_code == 200
    assert client.post(path, json=_payload(journey), headers=headers).status_code == 200
    inbox = db.session.query(ExpertConsoleNotification).filter_by(notification_type='customer_quote_response').all()
    external = db.session.query(NotificationAction).filter_by(policy='quote-response-expert.v1').all()
    assert len(inbox) == 1 and inbox[0].expert_user_id == journey.expert_id
    assert len(external) == 1 and external[0].state == 'BLOCKED'
    assert external[0].reason == 'EXPERT_DESTINATION_NOT_CERTIFIED'


def test_rotation_restart_reconstructs_exact_old_token_then_compromise_denies(journey):
    from backend.services.quote_response_authorization import capability_for_adapter
    original_material = journey.app.config['QUOTE_CAPABILITY_KEYRING']['new']['material']
    journey.app.config.update(QUOTE_CAPABILITY_KEYRING={
        'new': {'material': original_material, 'state': 'VERIFY_ONLY'},
        'rotated': {'material': base64.b64encode(secrets.token_bytes(64)).decode(), 'state': 'ACTIVE'}},
        QUOTE_CAPABILITY_ACTIVE_KEY='rotated', QUOTE_CAPABILITY_POLICY_EPOCH=2)
    qualification_key_policy('ROTATED'); db.session.commit()
    grant_id = db.session.query(QuoteResponseGrant.id).scalar()
    # Session removal loses every ORM object; private derivation is from durable
    # claims/digest and admitted trusted keys, not an in-memory token cache.
    db.session.remove()
    reconstructed, recipient = capability_for_adapter(grant_id)
    assert reconstructed == journey.token and recipient == 'synthetic@example.test'
    db.session.rollback()
    if db.engine.dialect.name == 'postgresql':
        import json
        import subprocess
        import sys
        probe = subprocess.run([sys.executable,'-B','-m','scripts.uat.fwd05_reconstruction_probe'],
            input=json.dumps({'database_url':journey.app.config['SQLALCHEMY_DATABASE_URI'],
                'ring':journey.app.config['QUOTE_CAPABILITY_KEYRING'],
                'active':journey.app.config['QUOTE_CAPABILITY_ACTIVE_KEY'],
                'epoch':journey.app.config['QUOTE_CAPABILITY_POLICY_EPOCH'],'grant_id':grant_id}),
            text=True,capture_output=True,timeout=30)
        # Existing application initialization emits unrelated startup lines;
        # retain only the probe's bounded boolean JSON, never private diagnostics.
        safe_probe=json.loads(next(line for line in reversed(probe.stdout.splitlines()) if line.startswith('{')))
        assert probe.returncode == 0,'Separate-process reconstruction: '+str(safe_probe.get('stage'))+'/'+str(safe_probe.get('exception_type'))
        assert safe_probe=={'status':'PASS','exact_durable_digest_matches':True}
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    client = journey.app.test_client()
    assert client.get(path, headers=_headers(journey)).status_code == 200
    journey.app.config['QUOTE_CAPABILITY_POLICY_EPOCH'] = 1
    assert client.get(path, headers=_headers(journey)).status_code == 403
    journey.app.config['QUOTE_CAPABILITY_POLICY_EPOCH'] = 3
    journey.app.config['QUOTE_CAPABILITY_KEYRING']['new']['state'] = 'COMPROMISED'
    qualification_key_policy('COMPROMISED'); db.session.commit()
    assert client.get(path, headers=_headers(journey)).status_code == 403


def test_pending_dispatch_denied_after_revocation_without_private_capture(journey):
    from backend.services.quote_service import manage_quote_capability
    from backend.notification_models import NotificationAction, NotificationAttempt
    manage_quote_capability(journey.root_id, journey.quote_public_id, {'id':journey.expert_id}, 'REISSUE')
    pending = consume_one()
    manage_quote_capability(journey.root_id, journey.quote_public_id, {'id':journey.expert_id}, 'REVOKE')
    assert not _dispatch(pending)
    assert db.session.get(NotificationAction, pending).state == 'BLOCKED'
    assert db.session.query(NotificationAttempt).count() == 1  # original fixture dispatch only


def test_latest_quote_owner_denies_revoked_membership_and_spoofed_admin_label(journey):
    from backend.services.quote_service import get_latest_quote_for_request, QuoteAccessError
    membership = db.session.query(OperationalMembership).filter_by(user_id=journey.expert_id).one()
    membership.is_active = False; db.session.commit()
    with pytest.raises(QuoteAccessError):
        get_latest_quote_for_request(journey.root_id, {'id':journey.expert_id,'role':'admin'})


def test_response_attention_old_owner_denied_and_current_assignee_receives_one_entry(journey):
    from backend.services.notification_service import list_notifications_for_expert, get_unread_count, mark_notifications_read
    from backend.services.assignment_service import assign_request_to_expert
    from backend.models import ExpertConsoleNotification
    client = journey.app.test_client()
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    assert client.post(path, json=_payload(journey), headers={**_headers(journey),'Idempotency-Key':'attention-proof'}).status_code == 200
    old_entry = db.session.query(ExpertConsoleNotification).filter_by(notification_type='customer_quote_response').one()
    old_id = old_entry.id
    root = db.session.get(ShipmentRequest, journey.root_id)
    org_id = root.operational_organization_id
    new = ExpertUser(username='new-attention-owner',password_hash='synthetic-unusable',full_name='Synthetic',authority='EXPERT',role='expert',is_active=True)
    db.session.add(new); db.session.flush()
    db.session.add(OperationalMembership(organization_id=org_id,user_id=new.id,is_active=True,permissions=[]))
    new_id = new.id
    db.session.commit()
    assign_request_to_expert(journey.root_id, expert_id=new_id, actor={'id':journey.expert_id})
    assert not list_notifications_for_expert(journey.expert_id)['notifications']
    assert get_unread_count(journey.expert_id) == 0
    assert mark_notifications_read(journey.expert_id,{'notification_ids':[old_id]})['marked_count'] == 0
    current = list_notifications_for_expert(new_id)['notifications']
    responses = [n for n in current if n['type']=='customer_quote_response']
    assert len(responses) == 1 and journey.quote_public_id in responses[0]['message']
    # Repeating attention staging cannot duplicate the fact/recipient fence.
    from backend.services.quote_response_authorization import lock_quote_scope
    from backend.services.quote_response_notification import reroute_response_attention
    db.session.rollback()
    scope = lock_quote_scope(journey.root_id,actor_id=new_id)
    reroute_response_attention(scope); db.session.commit()
    assert db.session.query(ExpertConsoleNotification).filter_by(notification_type='customer_quote_response',expert_user_id=new_id).count() == 1
    db.session.query(OperationalMembership).filter_by(user_id=new_id).one().is_active=False
    db.session.commit()
    assert not list_notifications_for_expert(new_id)['notifications'] or all(n['type']!='customer_quote_response' for n in list_notifications_for_expert(new_id)['notifications'])


@pytest.mark.parametrize('terminal', ['COMPROMISED','REVOKED','RETIRED'])
@pytest.mark.parametrize('reactivation', ['ACTIVE','VERIFY_ONLY'])
def test_terminal_key_version_cannot_reappear_after_configured_absence_and_session_removal(journey,terminal,reactivation):
    from backend.services.quote_capability_crypto import CapabilityDenied
    material = journey.app.config['QUOTE_CAPABILITY_KEYRING']['new']['material']
    rotated = {'material':base64.b64encode(secrets.token_bytes(64)).decode(),'state':'ACTIVE'}
    journey.app.config.update(QUOTE_CAPABILITY_KEYRING={'new':{'material':material,'state':terminal},'rotated':rotated},
        QUOTE_CAPABILITY_ACTIVE_KEY='rotated',QUOTE_CAPABILITY_POLICY_EPOCH=2)
    qualification_key_policy(terminal);db.session.commit()
    journey.app.config.update(QUOTE_CAPABILITY_KEYRING={'rotated':rotated},QUOTE_CAPABILITY_POLICY_EPOCH=3)
    qualification_key_policy('ABSENT');db.session.commit();db.session.remove()
    journey.app.config.update(QUOTE_CAPABILITY_KEYRING={'new':{'material':material,'state':reactivation},
        'rotated':{'material':rotated['material'],'state':'VERIFY_ONLY' if reactivation=='ACTIVE' else 'ACTIVE'}},
        QUOTE_CAPABILITY_ACTIVE_KEY='new' if reactivation=='ACTIVE' else 'rotated',QUOTE_CAPABILITY_POLICY_EPOCH=4)
    with pytest.raises(CapabilityDenied,match='KEY_QUARANTINE_TERMINAL'):
        qualification_key_policy('REAPPEARED')
    db.session.rollback()


def test_staff_grant_management_has_attributable_append_only_audit(journey):
    from backend.services.quote_service import manage_quote_capability
    from backend.operational_models import OperationalAudit
    manage_quote_capability(journey.root_id,journey.quote_public_id,{'id':journey.expert_id},'REVOKE')
    audit = db.session.query(OperationalAudit).filter_by(action='authorization.quote-capability.revoke').one()
    assert audit.actor_user_id==journey.expert_id and audit.entity_id==journey.quote_id
    assert audit.metadata_json['quote_public_id']==journey.quote_public_id
    assert len(audit.metadata_json['revoked_grant_ids'])==1 and journey.token not in str(audit.metadata_json)
    audit.metadata_json={'forged':True}
    with pytest.raises(ValueError,match='QUOTE_GRANT_AUDIT_APPEND_ONLY'):
        db.session.commit()
    db.session.rollback()


def test_published_money_cannot_be_mutated_or_deleted_through_orm(journey):
    quote = db.session.get(ExpertQuote,journey.quote_id)
    quote.amount = 999
    with pytest.raises(ValueError,match='QUOTE_PUBLISHED_CONTENT_IMMUTABLE'):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(ExpertQuote,journey.quote_id).amount_exact.__str__()=='1234.50'
    db.session.delete(db.session.get(ExpertQuote,journey.quote_id))
    with pytest.raises(ValueError,match='QUOTE_PUBLICATION_HISTORY_RETAINED'):
        db.session.commit()
    db.session.rollback()


def test_native_postgresql_direct_sql_cannot_mutate_publication_receipts_or_attention_envelopes(journey):
    if db.engine.dialect.name!='postgresql':
        pytest.skip('Physical PostgreSQL triggers required')
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from backend.models import ExpertConsoleNotification
    path='/api/quote-capability/quotes/'+journey.quote_public_id
    assert journey.app.test_client().post(path,json=_payload(journey),headers={**_headers(journey),'Idempotency-Key':'sql-history'}).status_code==200
    fact_id=db.session.query(QuoteResponseFact.id).scalar()
    receipt_id=db.session.query(QuoteResponseReceipt.id).scalar()
    attention_id=db.session.query(ExpertConsoleNotification.id).filter_by(notification_type='customer_quote_response').scalar()
    grant_id=db.session.query(QuoteResponseGrant.id).scalar()
    from backend.services.quote_service import manage_quote_capability
    from backend.operational_models import OperationalAudit
    from backend.quote_response_models import QuoteKeyPolicyAudit
    manage_quote_capability(journey.root_id, journey.quote_public_id, {'id':journey.expert_id}, 'REVOKE')
    audit_id=db.session.query(OperationalAudit.id).filter_by(action='authorization.quote-capability.revoke').scalar()
    policy_audit_id=db.session.query(QuoteKeyPolicyAudit.id).scalar()
    statements=[
        ('UPDATE expert_quote SET amount_exact=999 WHERE id=:id',journey.quote_id),
        ('DELETE FROM expert_quote WHERE id=:id',journey.quote_id),
        ('UPDATE quote_response_grant SET subject=\'00000000-0000-4000-8000-000000000000\' WHERE id=:id',grant_id),
        ('DELETE FROM quote_response_grant WHERE id=:id',grant_id),
        ('UPDATE quote_response_fact SET response=\'accepted\' WHERE id=:id',fact_id),
        ('DELETE FROM quote_response_fact WHERE id=:id',fact_id),
        ('DELETE FROM quote_response_receipt WHERE id=:id',receipt_id),
        ('UPDATE expert_console_notification SET quote_response_fact_id=NULL WHERE id=:id',attention_id),
        ('DELETE FROM expert_console_notification WHERE id=:id',attention_id),
        ('UPDATE operational_audit SET action=\'legacy.changed\' WHERE id=:id',audit_id),
        ('DELETE FROM operational_audit WHERE id=:id',audit_id),
        ('DELETE FROM quote_key_policy_audit WHERE id=:id',policy_audit_id)]
    db.session.rollback()
    for statement,identity in statements:
        with pytest.raises(DBAPIError):
            with db.engine.begin() as connection:
                # Qualification-only raw SQL bypasses the application census
                # fence so this assertion proves the actual PostgreSQL trigger.
                connection.execution_options(include_quarantined_for_certification=True).execute(text(statement),{'id':identity})
    db.session.remove()
    assert db.session.get(ExpertQuote,journey.quote_id).amount_exact.__str__()=='1234.50'
    assert db.session.query(QuoteResponseFact).count()==db.session.query(QuoteResponseReceipt).count()==1
    assert db.session.query(ExpertConsoleNotification).filter_by(quote_response_fact_id=fact_id).count()==1


def test_native_postgresql_waiting_response_checks_actual_clock_after_scope_lock(journey):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('Physical PostgreSQL lock and wall clock required')
    from concurrent.futures import ThreadPoolExecutor
    from decimal import Decimal
    from time import monotonic, sleep
    from sqlalchemy import text
    from backend.census_context import census_unit_of_work
    from backend.services.governed_quote_service import content_snapshot
    from backend.services.quote_notification_contract import digest
    from backend.services.quote_response_authorization import database_instant, lock_quote_scope, issue_grant, capability_for_adapter
    source=db.session.get(ShipmentRequest,journey.root_id)
    # Explicit technical cutoff fixture, not a normative LocalDate publication.
    # TIME-BIZ-003 derivation is independently tested; neither DB clock nor
    # product publication command is mocked or changed to make this race pass.
    expiry=database_instant()+timedelta(seconds=8)
    with census_unit_of_work(db.session):
        root=ShipmentRequest(shipping_type='domestic',contact_phone='09000000001',ownership_scope='TENANT',
            operational_organization_id=source.operational_organization_id,customer_id=source.customer_id,
            gamification_customer_id=source.gamification_customer_id,assigned_to=journey.expert_id,status='waiting_for_customer')
        db.session.add(root);db.session.flush()
        quote=ExpertQuote(shipment_request_id=root.id,operational_organization_id=root.operational_organization_id,
            created_by_expert_id=journey.expert_id,amount=None,amount_exact=Decimal('42.50'),currency='EUR',
            public_id=str(uuid4()),money_contract='quote-major.v1',content_revision=1,response_version=0,
            valid_until=date.today(),validity_timezone='America/New_York',validity_policy='QUALIFICATION-CLOCK-FENCE',
            published_at=database_instant(),expires_at=expiry)
        quote.content_digest=digest(content_snapshot(quote));db.session.add(quote);db.session.commit()
    root_id,quote_id,public_id,content_digest=root.id,quote.id,quote.public_id,quote.content_digest
    scope=lock_quote_scope(root_id,actor_id=journey.expert_id)
    grant=issue_grant(next(q for q in scope['quotes'] if q.id==quote_id),scope)
    grant_id=grant.id;db.session.commit()
    token,_=capability_for_adapter(grant_id,write=False);db.session.rollback()
    lock_quote_scope(root_id,actor_id=journey.expert_id)
    path='/api/quote-capability/quotes/'+public_id
    headers={'Authorization':'QuoteCapability '+token,'Idempotency-Key':'post-lock-clock'}
    def waiting_response():
        with journey.app.app_context():
            try:
                return journey.app.test_client().post(path,json={'response':'accepted','content_revision':1,
                    'content_digest':content_digest,'expected_response_version':0,'reason':'CUSTOMER_DECISION'},headers=headers).status_code
            finally:
                db.session.remove()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future=executor.submit(waiting_response)
        deadline=monotonic()+20
        blocked=False
        try:
            while monotonic()<deadline:
                db.session.execute(text("SELECT pg_stat_clear_snapshot()"))
                blocked=db.session.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND wait_event_type='Lock')"))
                if blocked and database_instant()>=expiry:
                    break
                sleep(0.03)
            assert blocked and database_instant()>=expiry and not future.done()
        finally:
            db.session.rollback()
        assert future.result(timeout=20)==403
    db.session.remove()
    assert db.session.get(ExpertQuote,quote_id).response_version==0
    assert db.session.query(QuoteResponseFact).filter_by(quote_id=quote_id).count()==0
    assert db.session.query(QuoteResponseReceipt).filter_by(quote_id=quote_id).count()==0
    readable=journey.app.test_client().get(path,headers=headers)
    assert readable.status_code==200 and readable.json['can_respond'] is False


@pytest.mark.parametrize('competitor', ['response', 'revoke', 'replacement', 'assignment', 'unlink'])
def test_native_postgresql_response_competing_transactions_persist_one_legal_outcome(journey, competitor):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('SQLite cannot establish row-lock/concurrency behavior')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from backend.services.quote_service import manage_quote_capability, QuoteServiceError
    barrier = Barrier(2)
    path = '/api/quote-capability/quotes/' + journey.quote_public_id
    new_expert_id=None
    if competitor=='assignment':
        from backend.census_context import census_unit_of_work
        root=db.session.get(ShipmentRequest,journey.root_id)
        org_id=root.operational_organization_id
        with census_unit_of_work(db.session):
            new=ExpertUser(username='concurrent-new-assignee',password_hash='synthetic-unusable',full_name='Concurrent owner',
                authority='EXPERT',role='expert',is_active=True)
            db.session.add(new);db.session.flush()
            db.session.add(OperationalMembership(organization_id=org_id,user_id=new.id,is_active=True,permissions=[]))
            new_expert_id=new.id;db.session.commit()
    db.session.rollback()
    def first():
        barrier.wait(timeout=20)
        response = journey.app.test_client().post(path, json=_payload(journey, 'accepted'),
            headers={**_headers(journey), 'Idempotency-Key':'race-first'})
        return response.status_code
    def second():
        with journey.app.app_context():
            barrier.wait(timeout=20)
            try:
                if competitor == 'response':
                    return journey.app.test_client().post(path, json=_payload(journey, 'declined'),
                        headers={**_headers(journey), 'Idempotency-Key':'race-second'}).status_code
                if competitor == 'revoke':
                    manage_quote_capability(journey.root_id, journey.quote_public_id,
                        {'id':journey.expert_id}, 'REVOKE')
                elif competitor=='assignment':
                    from backend.services.assignment_service import assign_request_to_expert
                    assign_request_to_expert(journey.root_id,expert_id=new_expert_id,actor={'id':journey.expert_id})
                elif competitor=='unlink':
                    from backend.services.crm_customer_link_service import unlink_customer_from_request
                    unlink_customer_from_request(journey.root_id,{}, {'id':journey.expert_id,'role':'expert'})
                else:
                    create_quote_for_request(journey.root_id, {'amount':'999.50','currency':'EUR',
                        'valid_until':(date.today()+timedelta(days=4)).isoformat(),
                        'predecessor_public_id':journey.quote_public_id}, {'id':journey.expert_id})
                return 200
            except QuoteServiceError as exc:
                return exc.status_code
            finally:
                db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as executor:
        a, b = executor.submit(first), executor.submit(second)
        outcomes = (a.result(timeout=45), b.result(timeout=45))
    db.session.remove()
    quote = db.session.get(ExpertQuote, journey.quote_id)
    facts = db.session.query(QuoteResponseFact).filter_by(quote_id=quote.id).all()
    assert len(facts) <= 1 and quote.response_version == len(facts)
    assert db.session.query(QuoteResponseReceipt).count() == len(facts)
    if competitor == 'response':
        assert sorted(outcomes) == [200,409]
        assert len(facts) == 1 and quote.customer_response in {'accepted','declined'}
    elif competitor == 'revoke':
        assert outcomes in {(200,200),(403,200)}
        assert db.session.query(QuoteResponseGrant).one().revoked_at is not None
        assert journey.app.test_client().get(path, headers=_headers(journey)).status_code == 403
    elif competitor=='unlink':
        assert outcomes in {(200,200),(403,200)}
        root=db.session.get(ShipmentRequest,journey.root_id)
        assert root.customer_id is None and root.quote_recipient_generation==1
        assert journey.app.test_client().get(path,headers=_headers(journey)).status_code==403
    elif competitor=='assignment':
        from backend.services.notification_service import list_notifications_for_expert
        assert outcomes in {(200,200),(403,200)}
        assert db.session.get(ShipmentRequest,journey.root_id).assigned_to==new_expert_id
        assert not list_notifications_for_expert(journey.expert_id)['notifications']
        visible=list_notifications_for_expert(new_expert_id)['notifications']
        assert len([entry for entry in visible if entry['type']=='customer_quote_response'])==len(facts)
        assert journey.app.test_client().get(path,headers=_headers(journey)).status_code==200
    else:
        assert outcomes in {(200,409),(403,200)}
        if outcomes[0] == 200:
            assert quote.customer_response == 'accepted' and quote.superseded_by_id is None
            assert db.session.query(ExpertQuote).count() == 1
        else:
            assert quote.superseded_by_id is not None and not facts
            assert db.session.query(ExpertQuote).count() == 2
            old_read = journey.app.test_client().get(path, headers=_headers(journey))
            assert old_read.status_code == 200 and old_read.json['quote']['superseded'] is True
            assert not old_read.json['can_respond']
            assert '999.50' not in str(old_read.json)
