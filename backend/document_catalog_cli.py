"""Explicit machine-readable CLI for ADR-036 document catalog packages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend import create_app
from backend.document_catalog_package import (
    PackageApplyError,
    PackageValidationError,
    apply_package,
    load_package,
    plan_package,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Governed Document Master Catalog package"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--file", required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--file", required=True)
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--operator")
    apply.add_argument("--approval-reference")
    apply.add_argument("--expected-checksum")
    apply.add_argument("--expected-plan-fingerprint")
    apply.add_argument("--idempotency-key")
    apply.add_argument("--confirm-production", action="store_true")
    return parser


def main(argv: list[str] | None = None, *, app=None) -> int:
    args = _parser().parse_args(argv)
    package = load_package(Path(args.file))
    app = app or create_app(skip_startup=True)
    environment = str(app.config.get("APP_ENV", "development")).strip().lower()
    with app.app_context():
        if args.command == "plan":
            print(
                json.dumps(
                    plan_package(package, environment).as_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        if not args.confirm:
            print("REFUSED: apply requires --confirm.", file=sys.stderr)
            return 2
        required = (
            args.operator,
            args.approval_reference,
            args.expected_checksum,
            args.expected_plan_fingerprint,
            args.idempotency_key,
        )
        if not all(required):
            print(
                "REFUSED: apply requires operator, approval, checksum, plan fingerprint, and idempotency key.",
                file=sys.stderr,
            )
            return 2
        plan, run = apply_package(
            package,
            environment=environment,
            operator=args.operator,
            approval_reference=args.approval_reference,
            expected_checksum=args.expected_checksum,
            expected_plan_fingerprint=args.expected_plan_fingerprint,
            idempotency_key=args.idempotency_key,
            confirm=True,
            confirm_production=args.confirm_production,
        )
        output = plan.as_dict()
        output.update(run_id=run.public_id, status=run.status)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 3 if run.status == "refused" else 0


def run(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except (PackageValidationError, PackageApplyError) as exc:
        print(f"Document catalog command failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"Document catalog command failed ({type(exc).__name__}).", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
