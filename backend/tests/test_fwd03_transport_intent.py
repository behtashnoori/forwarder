"""Commercial intent command/API, compatibility, authority and read proof."""
from copy import deepcopy
import os
import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest, TransportMethod, ExpertUser, ExpertQuote, Province
from backend.operational_models import OperationalMembership, OperationalOutbox, OrganizationHostname
from backend.services.commercial_transport_service import project_transport, ShipmentValidationError
from backend.services.shipment_service import create_shipment_request
from backend.services.expert_request_detail_service import get_expert_request_detail, RequestDetailAccessError
from backend.tests.test_fwd01_notifications import seed
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture()
def app():
    url = os.environ.get('FWD03_COMMAND_DATABASE_URL', 'sqlite:///:memory:')
    if url != 'sqlite:///:memory:':
        parsed = make_url(url)
        assert parsed.host == '127.0.0.1' and parsed.port == 55463 and parsed.database == 'forwarder_fwd03_test_commands'
    application = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": url,
        "NOTIFICATION_PROVIDER":"fake", "NOTIFICATION_ENVIRONMENT":"qualification"}, skip_startup=True)
    with application.app_context():
        if url == 'sqlite:///:memory:':
            db.create_all()
        else:
            names = [n for n in inspect(db.engine).get_table_names() if n != 'alembic_version']
            assert 'transport_intent' in {c['name'] for c in inspect(db.engine).get_columns('shipment_request')}
            connection = db.engine.raw_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('TRUNCATE ' + ','.join(db.engine.dialect.identifier_preparer.quote(n) for n in names) + ' RESTART IDENTITY CASCADE')
                connection.commit()
            finally:
                connection.close()
        db.session.add_all([Province(id=1, name_fa='Synthetic origin'), Province(id=2, name_fa='Synthetic destination')])
        for name in ("Road Transport", "Sea Freight", "Air Freight", "Rail Transport", "Rail Transport", "Unknown railway service"):
            db.session.add(TransportMethod(name=name, name_fa=name, is_active=True))
        db.session.commit()
        yield application
        db.session.remove()
        if url == 'sqlite:///:memory:':
            db.drop_all()


def payload(modes=("road", "sea", "road"), **kwargs):
    return {"shipping_type": "domestic", "origin_province_id": 1, "dest_province_id": 2,
            "contact_phone": "09000000000", "cargo_description": " synthetic cargo ",
            "transport_method_preference": "customer_choice",
            "transport_intent": {"version": 1, "steps": [{"mode": mode} for mode in modes]}, **kwargs}


@pytest.mark.parametrize("modes,classification", [(("road", "sea", "road"), "combined"), (("road", "road"), "single-mode"), (("rail",), "single-mode"), (("air", "sea"), "combined")])
def test_command_api_roundtrip_and_shared_projection_without_events(app, modes, classification):
    client = app.test_client()
    data = payload(modes, transport_classification=classification, organization_id=9999)
    preview = client.post('/api/v2/shipment-request/prepare', json=data)
    assert preview.status_code == 200 and ShipmentRequest.query.count() == 0
    response = client.post('/api/v2/shipment-request', json=data)
    assert response.status_code == 201, response.get_json()
    result = response.get_json()
    db.session.remove()
    row = db.session.get(ShipmentRequest, result['id'])
    assert row.transport_intent == data['transport_intent']
    assert row.cargo_description == 'synthetic cargo'
    assert row.operational_organization_id is None and row.ownership_scope == 'INTAKE'
    assert row.transport_method is None
    public = client.get('/api/public/track/' + result['tracking_code'])
    assert public.status_code == 200
    assert public.get_json()['transport_summary'] == preview.get_json()['transport_summary']
    assert public.get_json()['transport_intent'] == data['transport_intent']
    assert result['transport_summary']['classification'] == classification
    assert result['transport_summary']['legacy_display_limited'] == (classification == 'combined')
    assert OperationalOutbox.query.count() == 0


@pytest.mark.parametrize('change,code', [
    ({'transport_intent': None}, 'TRANSPORT_INTENT_REQUIRED'),
    ({'transport_intent': {'version': 1, 'steps': []}}, 'INVALID_TRANSPORT_INTENT'),
    ({'transport_intent': {'version': True, 'steps': [{'mode': 'road'}]}}, 'UNSUPPORTED_TRANSPORT_VERSION'),
    ({'transport_intent': {'version': 2, 'steps': [{'mode': 'road'}]}}, 'UNSUPPORTED_TRANSPORT_VERSION'),
    ({'transport_intent': {'version': 1, 'steps': [{'mode': 'space'}]}}, 'UNSUPPORTED_TRANSPORT_MODE'),
    ({'transport_intent': {'version': 1, 'steps': [{'mode': 'road', 'vehicle': 1}]}}, 'INVALID_TRANSPORT_INTENT'),
    ({'transport_intent': ['road']}, 'INVALID_TRANSPORT_INTENT'),
    ({'transport_sequence': ['road']}, 'UNSUPPORTED_TRANSPORT_FIELD'),
    ({'transport_classification': 'single-mode'}, 'TRANSPORT_CLASSIFICATION_MISMATCH'),
    ({'transport_method': 'road'}, 'TRANSPORT_INPUT_CONFLICT'),
    ({'domestic_transport_method': 'air'}, 'TRANSPORT_INPUT_CONFLICT'),
    ({'transport_method_preference': 'bad'}, 'INVALID_TRANSPORT_PREFERENCE'),
    ({'cargo_description': ' \t\n'}, 'CARGO_DESCRIPTION_REQUIRED'),
    ({'cargo_description': None}, 'CARGO_DESCRIPTION_REQUIRED'),
])
def test_structured_field_errors_atomicity_and_direct_command(app, change, code):
    data = payload(**change)
    with pytest.raises(ShipmentValidationError) as exc:
        create_shipment_request(data, new_contract=True)
    assert exc.value.code == code
    response = app.test_client().post('/api/v2/shipment-request', json=data)
    assert response.status_code == 400
    assert response.get_json()['error']['code'] == code
    assert response.get_json()['field_errors']
    assert ShipmentRequest.query.count() == OperationalOutbox.query.count() == 0


def test_contract_selection_and_legacy_scope_compatibility(app):
    client = app.test_client()
    data = payload(); data.pop('transport_intent')
    data.update(domestic_transport_method='Road Transport', international_transport_method='Sea Freight', new_contract=False)
    assert client.post('/api/v2/shipment-request', json=data).get_json()['error']['code'] == 'TRANSPORT_INTENT_REQUIRED'
    old = client.post('/api/shipment-request', json=data)
    assert old.status_code == 201
    row = db.session.get(ShipmentRequest, old.get_json()['id'])
    assert row.transport_intent is None
    summary = project_transport(row)['transport_summary']
    assert len(summary['legacy_scopes']) == 2 and not summary['steps']
    data['transport_intent'] = payload()['transport_intent']
    assert client.post('/api/shipment-request', json=data).status_code == 201
    data['cargo_description'] = ' '
    assert client.post('/api/shipment-request', json=data).get_json()['error']['code'] == 'CARGO_DESCRIPTION_REQUIRED'
    for intent in (None,):
        suggestion = payload(transport_intent=intent, transport_method_preference='forwarder_suggestion')
        assert client.post('/api/v2/shipment-request', json=suggestion).status_code == 201
    assert client.post('/api/v2/shipment-request', json=payload(('road','road'), transport_classification='combined')).status_code == 400
    historical = ShipmentRequest(contact_phone='09000000000', transport_method='unknown historical code', cargo_description=None)
    assert 'unknown historical code' in project_transport(historical)['transport_summary']['display']


def test_catalog_duplicate_ids_unknown_semantics_and_revalidation(app):
    client = app.test_client()
    options = client.get('/api/v2/transport-intent-options').get_json()['items']
    rail = [item for item in options if item['mode'] == 'rail']
    assert len(rail) == 1 and len(rail[0]['catalog_ids']) == 2
    assert TransportMethod.query.count() == 6
    assert len(options) == 4
    assert client.post('/api/v2/shipment-request/prepare', json=payload()).status_code == 200
    TransportMethod.query.filter_by(name='Sea Freight').one().is_active = False
    db.session.commit()
    assert client.post('/api/v2/shipment-request', json=payload()).get_json()['error']['code'] == 'TRANSPORT_MODE_UNAVAILABLE'
    assert ShipmentRequest.query.count() == 0


def test_authorized_reads_revoke_count_filters_and_legacy_status_preserve_intent(app):
    ids = seed()
    row = db.session.get(ShipmentRequest, ids['request'])
    row.status = 'new'; row.cargo_description = 'needle'; row.transport_intent = payload()['transport_intent']
    # Synthetic historical quotes: read/count must count one request, not joins.
    db.session.add_all([ExpertQuote(shipment_request_id=row.id, amount=100 + i,
        created_by_expert_id=ids['actor'], operational_organization_id=ids['org']) for i in range(2)])
    db.session.commit()
    actor = {'id': ids['actor'], 'role': 'expert'}
    expected = deepcopy(row.transport_intent)
    detail = get_expert_request_detail(row.id, actor)
    assert detail['transport_summary'] == project_transport(row)['transport_summary']
    with pytest.raises(RequestDetailAccessError):
        get_expert_request_detail(row.id, {'id': ids['foreign'], 'role': 'expert'})
    token = create_session_tokens(ids['actor'])['access_token']
    headers = {'Authorization': 'Bearer ' + token}
    client = app.test_client()
    for search, expected_count in [('needle', 1), ('absent', 0)]:
        listing = client.get('/api/expert/requests?status=new&search=' + search, headers=headers)
        counter = client.get('/api/expert/dashboard/kpis?search=' + search, headers=headers)
        assert listing.status_code == counter.status_code == 200
        assert listing.get_json()['pagination']['total'] == counter.get_json()['counts']['new'] == expected_count
    row.status = 'assigned'; db.session.commit()
    listing = client.get('/api/expert/requests', headers=headers)
    counts = client.get('/api/expert/dashboard/kpis', headers=headers).get_json()['counts']
    assert counts['new'] == 0
    assert counts['total_visible'] == listing.get_json()['pagination']['total'] == 1
    url = f'/api/expert/requests/{row.public_id}/status'
    for attempt in ({'transport_method': 'air'}, {'transport_intent': None}, {'transport_intent': payload(('air',))['transport_intent']}):
        denied = client.post(url, headers=headers, json={'status': 'assigned', **attempt})
        assert denied.status_code == 400
        assert denied.get_json()['error']['code'] == 'TRANSPORT_UPDATE_NOT_SUPPORTED'
    changed = client.post(url, headers=headers, json={'status': 'in_progress'})
    assert changed.status_code == 200
    db.session.expire_all()
    assert db.session.get(ShipmentRequest, row.id).transport_intent == expected
    assert client.patch(f'/api/shipment-request/{row.id}', json={'transport_intent': None}).status_code in (404, 405)
    membership = OperationalMembership.query.filter_by(user_id=ids['actor']).one()
    membership.is_active = False
    db.session.commit()
    with pytest.raises(RequestDetailAccessError):
        get_expert_request_detail(row.id, actor)
    assert OperationalOutbox.query.count() == 0


def test_trusted_host_overrides_body_and_scoped_reads(app):
    ids = seed()
    db.session.add(OrganizationHostname(organization_id=ids['org'], hostname='intake.example.test', is_active=True))
    db.session.commit()
    row = create_shipment_request(payload(organization_id=ids['other_org'], operational_organization_id=ids['other_org']), request_host='intake.example.test', new_contract=True)
    assert row.ownership_scope == 'TENANT' and row.operational_organization_id == ids['org']
    assert row.transport_intent == payload()['transport_intent']
    with pytest.raises(RequestDetailAccessError):
        get_expert_request_detail(row.id, {'id': ids['foreign'], 'role': 'admin'})
    assert OperationalOutbox.query.count() == 0


def test_same_tenant_unassigned_admin_capability_and_reassignment(app):
    ids = seed()
    row = db.session.get(ShipmentRequest, ids['request'])
    row.transport_intent = payload()['transport_intent']
    extra = ExpertUser(username='fwd03-unassigned', full_name='Synthetic unassigned', password_hash='unused', authority='EXPERT', role='expert', is_active=True)
    db.session.add(extra); db.session.flush()
    membership = OperationalMembership(user_id=extra.id, organization_id=ids['org'], permissions=[])
    db.session.add(membership); db.session.commit()
    actor = {'id': extra.id, 'role': 'admin'}
    with pytest.raises(RequestDetailAccessError):
        get_expert_request_detail(row.id, actor)  # role label is not authority
    extra.authority = 'ORGANIZATION_ADMIN'; db.session.commit()
    with pytest.raises(RequestDetailAccessError):
        get_expert_request_detail(row.id, actor)
    membership.permissions = ['request.read']; db.session.commit()
    assert get_expert_request_detail(row.id, actor)['transport_intent'] == row.transport_intent
    extra.authority = 'EXPERT'; row.assigned_to = extra.id; db.session.commit()
    assert get_expert_request_detail(row.id, actor)['transport_intent'] == row.transport_intent
    with pytest.raises(RequestDetailAccessError):
        get_expert_request_detail(row.id, {'id': ids['actor'], 'role': 'expert'})


def test_postgresql_concurrent_legacy_narrow_writes_preserve_intent(app):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('Real concurrent transaction proof requires PostgreSQL')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    ids = seed()
    row = db.session.get(ShipmentRequest, ids['request'])
    row.transport_intent = payload()['transport_intent']; db.session.commit()
    barrier = Barrier(2)
    def narrow_write(field, value):
        with app.app_context():
            target = db.session.get(ShipmentRequest, ids['request'])
            assert target.transport_intent == payload()['transport_intent']
            barrier.wait(timeout=10)
            setattr(target, field, value)
            db.session.commit()
            db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(narrow_write, 'status', 'assigned')
        two = pool.submit(narrow_write, 'priority', 'high')
        one.result(timeout=15); two.result(timeout=15)
    db.session.expire_all()
    saved = db.session.get(ShipmentRequest, ids['request'])
    assert saved.transport_intent == payload()['transport_intent']
    assert saved.status == 'assigned' and saved.priority == 'high'
