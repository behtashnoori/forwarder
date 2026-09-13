"""Plan/apply command for the governed ADR-039 reference-type package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend import create_app
from backend.extensions import db
from backend.external_reference_type_package import (
    PackageApplyError,
    PackageValidationError,
    apply_package,
    load_package,
    plan_package,
)
from backend.models import ExpertUser


PACKAGE_PATH = (
    Path(__file__).with_name("reference_data")
    / "external_references"
    / "external-reference-types-v1.0.0.json"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="validate the package and report its exact database plan")
    apply = commands.add_parser("apply", help="apply a reviewed plan transactionally")
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--operator")
    apply.add_argument("--approval-reference")
    apply.add_argument("--actor-id", type=int)
    apply.add_argument("--expected-checksum")
    apply.add_argument("--expected-plan-fingerprint")
    apply.add_argument("--idempotency-key")
    apply.add_argument("--confirm-production", action="store_true")
    return parser


def _platform_admin(actor_id: int | None) -> ExpertUser:
    actor = db.session.get(ExpertUser, actor_id) if actor_id else None
    if not actor or not actor.is_active or actor.authority != "PLATFORM_ADMIN":
        raise PackageApplyError("apply requires an active Platform Admin actor")
    return actor


def main(argv: list[str] | None = None, *, app=None) -> int:
    args = _parser().parse_args(argv)
    package = load_package(PACKAGE_PATH)
    app = app or create_app(skip_startup=True)
    environment = str(app.config.get("APP_ENV", "development")).strip().lower()
    with app.app_context():
        if args.command == "plan":
            print(json.dumps(plan_package(package, environment).as_dict(), ensure_ascii=False, sort_keys=True))
            return 0
        required = (
            args.confirm, args.operator, args.approval_reference, args.actor_id,
            args.expected_checksum, args.expected_plan_fingerprint, args.idempotency_key,
        )
        if not all(required):
            print("REFUSED: apply requires confirmation, operator, approval, Platform Admin actor, checksum, plan fingerprint, and idempotency key.", file=sys.stderr)
            return 2
        actor = _platform_admin(args.actor_id)
        plan, run = apply_package(
            package, environment=environment, operator=args.operator,
            approval_reference=args.approval_reference,
            expected_checksum=args.expected_checksum,
            expected_plan_fingerprint=args.expected_plan_fingerprint,
            idempotency_key=args.idempotency_key, confirm=True,
            confirm_production=args.confirm_production, actor_id=actor.id,
        )
        output = plan.as_dict()
        output.update(run_id=run.public_id, status=run.status)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 3 if run.status == "refused" else 0


def run(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except (PackageValidationError, PackageApplyError) as exc:
        if db.session.is_active:
            db.session.rollback()
        print(f"External reference type command failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
