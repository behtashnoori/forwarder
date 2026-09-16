"""Real PostgreSQL additive migration, safe refusal and application rollback."""
import json
import os
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade

HEAD = '20260916_fwd03_transport_intent'
PREVIOUS = '20260916_fwd01_notifications'


def test_fwd03_migration_roundtrip_recovery():
    url = os.environ.get('FWD03_MIGRATION_DATABASE_URL')
    if not url:
        pytest.skip('Separate FWD-03 disposable PostgreSQL required')
    parsed = make_url(url)
    assert parsed.host == '127.0.0.1' and parsed.port == 55463 and parsed.database.startswith('forwarder_fwd03_test_')
    config = alembic_config(url)
    assert ScriptDirectory.from_config(config).get_heads() == [HEAD]
    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, PREVIOUS)
    engine = create_engine(url)
    with engine.begin() as conn:
        # Pre-upgrade incomplete historical request; no data repair/backfill.
        key = conn.execute(text("INSERT INTO shipment_request (public_id,contact_phone,ownership_scope,status,cargo_description,created_at,ready_at,status_request_status) VALUES ('a48a452a-83ae-4882-b54a-8b2326f4a8f4','09000000000','INTAKE','new',NULL,now(),now(),'new') RETURNING id")).scalar_one()
    command.upgrade(config, HEAD)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT transport_intent FROM shipment_request WHERE id=:id'), {'id': key}).scalar() is None
    command.downgrade(config, PREVIOUS)
    assert 'transport_intent' not in {c['name'] for c in inspect(engine).get_columns('shipment_request')}
    command.upgrade(config, HEAD)
    intent = {'version': 1, 'steps': [{'mode': 'road'}, {'mode': 'road'}, {'mode': 'sea'}, {'mode': 'road'}]}
    with engine.begin() as conn:
        conn.execute(text('UPDATE shipment_request SET transport_intent=CAST(:value AS json) WHERE id=:id'), {'id': key, 'value': json.dumps(intent)})
    with pytest.raises(RuntimeError, match='Transport intent history exists'):
        command.downgrade(config, PREVIOUS)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar() == HEAD
        assert conn.execute(text('SELECT transport_intent FROM shipment_request WHERE id=:id'), {'id': key}).scalar() == intent
        assert conn.execute(text('SELECT cargo_description FROM shipment_request WHERE id=:id'), {'id': key}).scalar() is None
    # Old application changes unrelated fields; retained JSON survives its SQL.
    with engine.begin() as conn:
        conn.execute(text("UPDATE shipment_request SET status='in_progress' WHERE id=:id"), {'id': key})
    with engine.connect() as conn:
        assert conn.execute(text('SELECT transport_intent FROM shipment_request WHERE id=:id'), {'id': key}).scalar() == intent
    command.upgrade(config, HEAD)
    engine.dispose()
