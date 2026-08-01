"""Explicit plan/apply CLI for the approved initial reference-data catalog."""
from __future__ import annotations

import argparse
import json
import sys

from backend import create_app
from backend.config import is_production_environment
from backend.reference_data_catalog import (
    CatalogApplyError,
    CatalogValidationError,
    apply_catalog,
    load_catalog,
    plan_catalog,
)

ALLOWED_APPLY_ENVIRONMENTS = {
    "development", "dev", "local", "testing", "test", "uat", "staging",
    "production", "prod",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governed initial reference-data catalog")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="validate and compare without writes")
    apply = commands.add_parser("apply", help="explicit transactional apply")
    apply.add_argument("--confirm", action="store_true", help="confirm the reviewed target")
    apply.add_argument("--operator", help="named human or service principal")
    apply.add_argument("--approval-reference", help="approved change or execution reference")
    apply.add_argument("--expected-checksum", help="approved sha256 checksum")
    apply.add_argument(
        "--confirm-production",
        action="store_true",
        help="additional explicit Production confirmation",
    )
    return parser


def main(argv: list[str] | None = None, *, app=None) -> int:
    args = _parser().parse_args(argv)
    catalog = load_catalog()
    app = app or create_app(skip_startup=True)
    environment = str(app.config.get("APP_ENV", "development")).strip().lower()
    with app.app_context():
        if args.command == "plan":
            print(json.dumps(plan_catalog(catalog, environment).as_dict(), ensure_ascii=False, sort_keys=True))
            return 0
        if not args.confirm:
            print("REFUSED: apply requires --confirm.", file=sys.stderr)
            return 2
        if not args.operator or not args.approval_reference or not args.expected_checksum:
            print(
                "REFUSED: apply requires --operator, --approval-reference, and --expected-checksum.",
                file=sys.stderr,
            )
            return 2
        if environment not in ALLOWED_APPLY_ENVIRONMENTS:
            print("REFUSED: apply requires a recognized explicit environment.", file=sys.stderr)
            return 2
        if is_production_environment(environment) and not args.confirm_production:
            print("REFUSED: Production apply requires --confirm-production.", file=sys.stderr)
            return 2
        plan, run = apply_catalog(
            catalog,
            environment=environment,
            executed_by=args.operator,
            approval_reference=args.approval_reference,
            expected_checksum=args.expected_checksum,
        )
        output = plan.as_dict()
        output.update(run_id=run.public_id, status=run.status)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 3 if run.status == "refused" else 0


def run(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except (CatalogValidationError, CatalogApplyError) as exc:
        print(f"Reference-data command failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Reference-data command failed ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
