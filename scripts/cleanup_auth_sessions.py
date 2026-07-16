"""Dry-run-first cleanup for expired and retention-eligible auth sessions."""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.engine import make_url

from backend import create_app
from backend.services.auth_session_service import cleanup_sessions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="delete eligible session rows")
    parser.add_argument("--retention-days", type=int, default=30)
    args = parser.parse_args()
    if args.retention_days < 0:
        raise SystemExit("retention-days must be non-negative")
    allowed = {
        "forwarder_session_test_20260719",
        "forwarder_candidate_session_clone_20260719",
        "forwarder_candidate_uat_20260717",
    }
    try:
        database_name = make_url(os.environ.get("DATABASE_URL", "")).database
    except Exception:
        raise SystemExit("Refusing cleanup without a valid database target")
    if database_name not in allowed:
        raise SystemExit("Refusing cleanup against an unapproved database")
    app = create_app()
    with app.app_context():
        count = cleanup_sessions(retention_days=args.retention_days, dry_run=not args.apply)
    print(f"eligible_auth_session_count={count} mode={'apply' if args.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
