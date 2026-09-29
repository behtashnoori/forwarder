"""Explicit plan/apply CLI for qualified GeoNames Admin1/city data."""
from __future__ import annotations
import argparse
import json
from backend import create_app
from backend.geonames_geography_catalog import GeoNamesCatalogError, apply, load, plan


def run(argv=None):
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan")
    command = commands.add_parser("apply")
    command.add_argument("--confirm", action="store_true")
    command.add_argument("--operator")
    command.add_argument("--approval-reference")
    command.add_argument("--expected-checksum")
    args = parser.parse_args(argv)
    app = create_app(skip_startup=True)
    try:
        with app.app_context():
            payload = load()
            if args.command == "plan":
                result = plan(payload).as_dict()
                result["qualification"] = payload["qualification"]
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
                return 0 if not result["conflict_count"] else 3
            if not args.confirm:
                print("REFUSED: apply requires --confirm")
                return 2
            result, record = apply(
                expected_checksum=args.expected_checksum or "", operator=args.operator or "",
                approval_reference=args.approval_reference or "",
                environment=str(app.config.get("APP_ENV", "development")),
            )
            print(json.dumps({**result.as_dict(), "run_id": record.public_id, "status": record.status}, sort_keys=True))
            return 0
    except GeoNamesCatalogError as exc:
        print(f"GeoNames geography command failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
