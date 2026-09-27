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
from backend.organization_profile import (
    ProfileApplyError,
    ProfileValidationError,
    apply_profile,
    load_profile,
    plan_profile,
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
    profile_plan = commands.add_parser(
        "organization-profile-plan",
        help="compare the standard organization profile without writes",
    )
    profile_plan.add_argument("--organization-public-id", required=True)
    profile_plan.add_argument("--actor-username", required=True)
    profile_apply = commands.add_parser(
        "organization-profile-apply",
        help="explicit transactional standard organization profile apply",
    )
    profile_apply.add_argument("--organization-public-id", required=True)
    profile_apply.add_argument("--actor-username", required=True)
    profile_apply.add_argument("--confirm", action="store_true")
    profile_apply.add_argument("--operator")
    profile_apply.add_argument("--approval-reference")
    profile_apply.add_argument("--expected-checksum")
    profile_apply.add_argument(
        "--confirm-reactivation",
        action="store_true",
        help="explicitly approve audited reactivation candidates shown by plan",
    )
    profile_apply.add_argument("--confirm-production", action="store_true")
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
        if args.command == "organization-profile-plan":
            profile = load_profile(catalog=catalog)
            result = plan_profile(
                profile,
                organization_public_id=args.organization_public_id,
                actor_username=args.actor_username,
            )
            print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
            return 3 if result.conflict_count or result.rejected_count else 0
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
        if args.command == "organization-profile-apply":
            profile = load_profile(catalog=catalog)
            plan = apply_profile(
                profile,
                organization_public_id=args.organization_public_id,
                actor_username=args.actor_username,
                operator=args.operator,
                approval_reference=args.approval_reference,
                expected_checksum=args.expected_checksum,
                confirm_reactivation=args.confirm_reactivation,
            )
            output = plan.as_dict()
            output["status"] = "REFUSED" if plan.conflict_count or plan.rejected_count else "SUCCEEDED"
            print(json.dumps(output, ensure_ascii=False, sort_keys=True))
            return 3 if plan.conflict_count or plan.rejected_count else 0
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
    except (CatalogValidationError, CatalogApplyError, ProfileValidationError, ProfileApplyError) as exc:
        print(f"Reference-data command failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Reference-data command failed ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
