"""Explicit, loopback disposable-database-only fake qualification consumer."""
import argparse
import json
import os
from sqlalchemy.engine import make_url


def run(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--fake-qualification', action='store_true', required=True)
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--reconcile')
    args = parser.parse_args(argv)
    url = os.environ.get('FWD01_QUALIFICATION_DATABASE_URL', '')
    target = make_url(url)
    if (target.get_backend_name() != 'postgresql' or target.host != '127.0.0.1'
            or not (target.database or '').startswith('forwarder_fwd01_test_')):
        parser.error('Explicit disposable loopback FWD-01 PostgreSQL database required')
    from backend import create_app
    from backend.services.notification_action_service import run_batch, reconcile
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': url,
                      'NOTIFICATION_PROVIDER': 'fake', 'NOTIFICATION_ENVIRONMENT': 'qualification'}, skip_startup=True)
    with app.app_context():
        value = {'reconciled': reconcile(args.reconcile), 'simulated': True} if args.reconcile else run_batch(args.limit)
        print(json.dumps(value))


if __name__ == '__main__':
    run()
