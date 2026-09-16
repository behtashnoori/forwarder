"""Native PG migration and direct SQL generation evidence, separate from SQLite."""
import os
from pathlib import Path
import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade

HEAD = '20260916_fwd05_quote_response'
PREVIOUS = '20260916_fwd03_transport_intent'


def own_url():
    url = os.environ.get('FWD05_DISPOSABLE_DATABASE_URL')
    if not url:
        pytest.skip('Own disposable native PG cluster required')
    parsed = make_url(url)
    assert parsed.host == '127.0.0.1' and parsed.username == 'fwd05_qualification'
    assert parsed.database == 'forwarder_fwd05_qualification'
    data = Path(os.environ['FWD05_OWN_CLUSTER_DATA']).resolve()
    assert data.parent.name.startswith('forwarder-fwd05-qualification-')
    lines = (data / 'postmaster.pid').read_text().splitlines()
    assert Path(lines[1]).resolve() == data and int(lines[3]) == parsed.port
    return url


def test_native_migration_empty_roundtrip_generation_aba_and_safe_refusal():
    url = own_url()
    config = alembic_config(url)
    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, PREVIOUS)
    # Explicit certification connection reaches physical SQL constraints; the
    # application's separate census fence must not mask a missing DB trigger.
    engine = create_engine(url).execution_options(include_quarantined_for_certification=True)
    with engine.begin() as connection:
        expert = connection.execute(text("INSERT INTO expert_user (username,password_hash,full_name,role,is_active,created_at) VALUES ('fwd05-sentinel','synthetic-unusable','Synthetic','expert',true,now()) RETURNING id")).scalar_one()
        root = connection.execute(text("INSERT INTO shipment_request (public_id,contact_phone,ownership_scope,status,created_at,ready_at,status_request_status) VALUES ('c54a2d3f-ecec-4aee-93ca-681ea6fbdcd4','09000000000','INTAKE','new',now(),now(),'new') RETURNING id")).scalar_one()
        old = connection.execute(text("INSERT INTO expert_quote (shipment_request_id,created_by_expert_id,amount,currency,created_at) VALUES (:root,:expert,9223372036854775807,'HIST',now()) RETURNING id"), {'root': root, 'expert': expert}).scalar_one()
        legacy_attention = connection.execute(text("INSERT INTO expert_console_notification (expert_user_id,shipment_request_id,notification_type,title,message,is_read,created_at) VALUES (:expert,:root,'customer_quote_response','Legacy','Original unspecified history',false,now()) RETURNING id"), {'expert':expert,'root':root}).scalar_one()
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        row = connection.execute(text('SELECT amount,currency,money_contract FROM expert_quote WHERE id=:id'), {'id': old}).one()
        assert tuple(row) == (9223372036854775807, 'HIST', None)
        assert connection.execute(text('SELECT message,quote_response_fact_id FROM expert_console_notification WHERE id=:id'), {'id':legacy_attention}).one() == ('Original unspecified history',None)
    command.downgrade(config, PREVIOUS)
    assert 'quote_response_grant' not in inspect(engine).get_table_names()
    command.upgrade(config, HEAD)
    with engine.begin() as connection:
        customer = connection.execute(text("INSERT INTO customer_gamification (email,phone,is_email_verified,created_at) VALUES ('original@example.test','09000000001',true,now()) RETURNING id")).scalar_one()
        connection.execute(text("UPDATE customer_gamification SET email='other@example.test' WHERE id=:id"), {'id': customer})
        connection.execute(text("UPDATE customer_gamification SET email='original@example.test' WHERE id=:id"), {'id': customer})
        assert connection.execute(text('SELECT quote_recipient_generation FROM customer_gamification WHERE id=:id'), {'id': customer}).scalar_one() == 2
        connection.execute(text("UPDATE customer_gamification SET email=' ORIGINAL@EXAMPLE.TEST ' WHERE id=:id"), {'id': customer})
        assert connection.execute(text('SELECT quote_recipient_generation FROM customer_gamification WHERE id=:id'), {'id': customer}).scalar_one() == 2
    with pytest.raises(Exception):
        with engine.begin() as connection:
            connection.execute(text('UPDATE customer_gamification SET quote_recipient_generation=0 WHERE id=:id'), {'id': customer})
    with pytest.raises(RuntimeError):
        command.downgrade(config, PREVIOUS)
    with engine.begin() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == HEAD
        connection.execute(text("UPDATE shipment_request SET contact_phone='09000000002' WHERE id=:id"), {'id': root})
        assert connection.execute(text('SELECT amount FROM expert_quote WHERE id=:id'), {'id': old}).scalar_one() == 9223372036854775807
    engine.dispose()
