"""Dry-run-first maintenance command for expired JWT revocations."""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.engine import make_url

from backend import create_app
from backend.services.token_revocation_service import cleanup_expired


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="delete expired rows")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL", "")
    allowed_databases = {
        "forwarder_security_test_20260718",
        "forwarder_candidate_clone_20260718",
        "forwarder_candidate_uat_20260717",
    }
    try:
        database_name = make_url(database_url).database
    except Exception:
        raise SystemExit("Refusing maintenance without a valid database target")
    if database_name not in allowed_databases:
        raise SystemExit("Refusing maintenance against an unapproved database")
    app = create_app()
    with app.app_context():
        count = cleanup_expired(dry_run=not args.apply)
    print(f"expired_revocation_count={count} mode={'apply' if args.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
