"""New-process synthetic owned-DB probe; stdout contains boolean evidence only."""
import json
import os
from pathlib import Path
import sys
stage = 'owned-identity'


def main():
    global stage
    from sqlalchemy.engine import make_url
    private = json.load(sys.stdin)
    own = make_url(os.environ['FWD05_DISPOSABLE_DATABASE_URL'])
    requested = make_url(private['database_url'])
    data = Path(os.environ['FWD05_OWN_CLUSTER_DATA']).resolve()
    lines = (data / 'postmaster.pid').read_text().splitlines()
    assert data.parent.name.startswith('forwarder-fwd05-qualification-')
    assert Path(lines[1]).resolve() == data and int(lines[3]) == own.port
    assert requested.host == own.host == '127.0.0.1'
    assert requested.username == own.username == 'fwd05_qualification'
    assert requested.port == own.port and requested.database.startswith('fwd05_runtime_')
    stage='application-setup'
    from backend import create_app
    from backend.extensions import db
    from backend.services.quote_response_authorization import capability_for_adapter
    from backend.services.quote_capability_crypto import token_digest
    from backend.quote_response_models import QuoteResponseGrant
    app = create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':private['database_url'],
        'QUOTE_CAPABILITY_KEYRING':private['ring'],
        'QUOTE_CAPABILITY_ACTIVE_KEY':private['active'],
        'QUOTE_CAPABILITY_POLICY_EPOCH':private['epoch']},skip_startup=True)
    with app.app_context():
        try:
            stage='durable-derivation'
            token,_ = capability_for_adapter(private['grant_id'],write=False)
            stored = db.session.get(QuoteResponseGrant,private['grant_id'])
            assert token_digest(token) == stored.token_digest
            print(json.dumps({'status':'PASS','exact_durable_digest_matches':True}))
        finally:
            db.session.rollback();db.session.remove();db.engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status':'FAIL','stage':stage,'exception_type':type(exc).__name__,
            'reason':'OWNED_PROCESS_RECONSTRUCTION_DENIED'}))
        sys.exit(1)
