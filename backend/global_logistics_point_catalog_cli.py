"""Explicit PLAN/APPLY entrypoint for the approved ADR-041 baseline."""

from __future__ import annotations

import argparse
import json
import sys

from backend import create_app
from backend.config import is_production_environment
from backend.global_logistics_point_catalog import (
    CATALOG_VERSION,
    GlobalCatalogApplyError,
    GlobalCatalogValidationError,
    apply_catalog,
    load_catalog,
    plan_catalog,
)

ALLOWED_ENVIRONMENTS = {
    "development",
    "dev",
    "local",
    "testing",
    "test",
    "uat",
    "staging",
    "production",
    "prod",
}


def _parser():
    parser = argparse.ArgumentParser(
        description="Governed Global Logistics Point baseline"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--package")
    plan.add_argument("--catalog-version", required=True)
    plan.add_argument("--expected-checksum", required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--package")
    apply.add_argument("--catalog-version", required=True)
    apply.add_argument("--expected-checksum", required=True)
    apply.add_argument("--operator", required=True)
    apply.add_argument("--approval-reference", required=True)
    apply.add_argument("--actor-user-id", required=True, type=int)
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--confirm-production", action="store_true")
    return parser


def main(argv=None, *, app=None):
    args = _parser().parse_args(argv)
    if args.catalog_version != CATALOG_VERSION:
        raise GlobalCatalogValidationError(
            "catalog version is not the approved version"
        )
    catalog = load_catalog(args.package) if args.package else load_catalog()
    if args.expected_checksum != catalog.checksum:
        raise GlobalCatalogValidationError(
            "expected checksum does not match the approved package"
        )
    app = app or create_app(skip_startup=True)
    environment = str(app.config.get("APP_ENV", "development")).strip().lower()
    with app.app_context():
        if args.command == "plan":
            print(
                json.dumps(
                    plan_catalog(catalog, environment).as_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        if not args.confirm:
            print("REFUSED: apply requires --confirm.", file=sys.stderr)
            return 2
        if environment not in ALLOWED_ENVIRONMENTS:
            print(
                "REFUSED: apply requires a recognized explicit environment.",
                file=sys.stderr,
            )
            return 2
        if is_production_environment(environment) and not args.confirm_production:
            print(
                "REFUSED: Production apply requires --confirm-production.",
                file=sys.stderr,
            )
            return 2
        plan, run = apply_catalog(
            catalog,
            environment=environment,
            operator=args.operator,
            approval_reference=args.approval_reference,
            expected_checksum=args.expected_checksum,
            user_id=args.actor_user_id,
        )
        output = plan.as_dict()
        output.update(run_id=run.public_id, status=run.status)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 3 if run.status == "refused" else 0


def run(argv=None):
    try:
        return main(argv)
    except (GlobalCatalogValidationError, GlobalCatalogApplyError) as exc:
        print(f"Global catalog command failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Global catalog command failed ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
