"""Independent disposable PostgreSQL migration/recovery and real CLI proof."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.notification_models import NotificationAction, NotificationAttempt
from backend.tests.test_fwd01_notifications import seed, quote
from backend.services.notification_action_service import consume_one

HEAD = '20260916_fwd01_notifications'
PREVIOUS = '20260908_governed_international_geography'


def test_fwd01_postgresql_migration_recovery_and_cli(tmp_path):
    url = os.environ.get('FWD01_MIGRATION_DATABASE_URL')
    if not url:
        pytest.skip('Separate FWD-01 disposable PostgreSQL migration database required')
    target = make_url(url)
    assert target.host == '127.0.0.1' and target.database.startswith('forwarder_fwd01_test_migration_')
    config = alembic_config(url)
    assert ScriptDirectory.from_config(config).get_heads() == [HEAD]
    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, PREVIOUS)
    engine = create_engine(url)
    # Synthetic pre-migration sentinel, via DBAPI outside runtime. No passwords.
    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO operational_organization (public_id,name,is_active,created_at) VALUES ('fwd01-migration-sentinel','FWD01 preserved sentinel',true,now()) RETURNING id")
            sentinel = cursor.fetchone()[0]
        connection.commit()
    finally:
        connection.close()
    command.upgrade(config, HEAD)
    inspector = inspect(engine)
    for table in ('notification_action', 'notification_attempt'):
        for column in inspector.get_columns(table):
            if column['name'].endswith('_at') or column['name'] == 'lease_until':
                assert column['type'].timezone
        assert inspector.get_foreign_keys(table)
    assert {item['name'] for item in inspector.get_unique_constraints('notification_action')} >= {'uq_notification_event_policy', 'uq_notification_action_tenant'}
    command.downgrade(config, PREVIOUS)
    assert 'notification_action' not in inspect(engine).get_table_names()
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(text('SELECT name FROM operational_organization WHERE id=:id'), {'id': sentinel}).scalar() == 'FWD01 preserved sentinel'
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': url,
        'NOTIFICATION_PROVIDER': 'fake', 'NOTIFICATION_ENVIRONMENT': 'qualification'}, skip_startup=True)
    with app.app_context():
        ids = seed(); quote(ids); action_id = consume_one()
        db.session.remove()
    environment = {k:v for k,v in os.environ.items() if 'DATABASE_URL' not in k and 'POSTGRES_URL' not in k}
    environment.update(TEST_DATABASE_URL='sqlite:///:memory:', FWD01_QUALIFICATION_DATABASE_URL=url)
    completed = subprocess.run([sys.executable, '-m', 'backend.notification_cli', '--fake-qualification'],
        cwd=Path(__file__).resolve().parents[2], env=environment, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, 'Qualification CLI failed (output retained only for local debugging)'
    summary = json.loads(completed.stdout.strip().splitlines()[-1])
    assert summary == {'consumed': 0, 'dispatched': 1, 'recovered_unknown': 0, 'simulated': True}
    with app.app_context():
        assert db.session.get(NotificationAction, action_id).state == 'SENT'
        assert NotificationAttempt.query.one().simulated
        db.session.remove()
    with pytest.raises(RuntimeError, match='history exists'):
        command.downgrade(config, PREVIOUS)
    with app.app_context():
        assert db.session.get(NotificationAction, action_id).state == 'SENT'
        assert NotificationAttempt.query.count() == 1
    engine.dispose()
