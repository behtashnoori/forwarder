"""Two-phase operator command for one historical Cargo continuity repair."""

from __future__ import annotations

import argparse
import json
import os

from sqlalchemy.engine import make_url

from backend import create_app
from backend.config import get_runtime_environment, is_production_environment
from backend.extensions import db
from backend.services.cargo_continuity_repair_service import (
    CargoContinuityRepairError,
    apply_repair,
    plan_repair,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cargo-continuity-repair")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="Read and prove one repair without writes.")
    plan.add_argument("--shipment", required=True)
    plan.add_argument("--actor-username", required=True)
    plan.add_argument("--expected-request-tracking-code", required=True)
    plan.add_argument("--expected-cargo-public-id", required=True)
    plan.add_argument("--expected-source-request-cargo-public-id", required=True)
    plan.add_argument("--expected-route-plan-id", required=True, type=int)
    plan.add_argument("--expected-terminal-route-leg-id", required=True, type=int)
    plan.add_argument("--expected-database-name", required=True)

    apply = commands.add_parser("apply", help="Apply one reviewed exact repair.")
    apply.add_argument("--shipment", required=True)
    apply.add_argument("--actor-username", required=True)
    apply.add_argument("--expected-request-tracking-code", required=True)
    apply.add_argument("--expected-cargo-public-id", required=True)
    apply.add_argument("--expected-source-request-cargo-public-id", required=True)
    apply.add_argument("--expected-route-plan-id", required=True, type=int)
    apply.add_argument("--expected-terminal-route-leg-id", required=True, type=int)
    apply.add_argument("--expected-database-name", required=True)
    apply.add_argument("--operator", required=True)
    apply.add_argument("--approval-reference", required=True)
    apply.add_argument("--expected-plan-fingerprint", required=True)
    apply.add_argument("--confirm", action="store_true")
    return parser


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _production_requested() -> bool:
    names = ("APP_ENV", "ENV", "FLASK_ENV")
    return any(
        is_production_environment(os.getenv(name, ""))
        for name in names
        if os.getenv(name)
    ) or is_production_environment(get_runtime_environment())


def _guard_database(app, expected_database_name: str) -> None:
    environment = str(app.config.get("APP_ENV") or "").strip().lower()
    if is_production_environment(environment):
        raise CargoContinuityRepairError(
            "PRODUCTION_REPAIR_NOT_AUTHORIZED",
            "Production repair is not authorized by this bounded mission.",
            403,
        )
    if environment not in {"testing", "uat"}:
        raise CargoContinuityRepairError(
            "REPAIR_RUNTIME_NOT_AUTHORIZED",
            "This bounded repair requires an explicit testing or UAT runtime.",
            403,
        )
    configured = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    actual_name = configured.database or ""
    expected_name = str(expected_database_name or "").strip()
    if actual_name != expected_name:
        raise CargoContinuityRepairError(
            "REPAIR_DATABASE_IDENTITY_MISMATCH",
            "The connected database does not match the operator-reviewed database identity.",
            403,
        )
    if bool(app.config.get("TESTING")) and configured.get_backend_name() == "sqlite":
        if actual_name != ":memory:":
            raise CargoContinuityRepairError(
                "REPAIR_DATABASE_NOT_AUTHORIZED",
                "Only an in-memory SQLite database is authorized for focused tests.",
                403,
            )
        return
    allowed_name = actual_name == "forwarder_human_walkthrough" or actual_name.startswith(
        "forwarder_cargo_continuity_repair_"
    )
    if (
        configured.get_backend_name() != "postgresql"
        or configured.host not in {"127.0.0.1", "localhost"}
        or not allowed_name
    ):
        raise CargoContinuityRepairError(
            "REPAIR_DATABASE_NOT_AUTHORIZED",
            "Only the preserved local walkthrough or an owned local qualification database is authorized.",
            403,
        )


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if _production_requested():
        _emit({"error": "PRODUCTION_REPAIR_NOT_AUTHORIZED"})
        return 3
    if args.command == "apply" and not args.confirm:
        _emit({"error": "CONFIRMATION_REQUIRED"})
        return 2
    app = create_app(skip_startup=True)
    with app.app_context():
        try:
            _guard_database(app, args.expected_database_name)
            if args.command == "plan":
                result = plan_repair(
                    args.shipment,
                    args.actor_username,
                    args.expected_request_tracking_code,
                    args.expected_cargo_public_id,
                    args.expected_source_request_cargo_public_id,
                    args.expected_route_plan_id,
                    args.expected_terminal_route_leg_id,
                )
                db.session.rollback()
                _emit(result)
                return 0 if result["eligibility"] == "YES" else 3
            result = apply_repair(
                args.shipment,
                args.actor_username,
                operator=args.operator,
                expected_request_tracking_code=args.expected_request_tracking_code,
                expected_cargo_public_id=args.expected_cargo_public_id,
                expected_source_request_cargo_public_id=(
                    args.expected_source_request_cargo_public_id
                ),
                expected_route_plan_id=args.expected_route_plan_id,
                expected_terminal_route_leg_id=args.expected_terminal_route_leg_id,
                approval_reference=args.approval_reference,
                expected_plan_fingerprint=args.expected_plan_fingerprint,
            )
            _emit(result)
            return 0
        except CargoContinuityRepairError as exc:
            db.session.rollback()
            _emit({"error": exc.code, "message": str(exc)})
            return 3
        except Exception:
            db.session.rollback()
            _emit({"error": "CARGO_CONTINUITY_REPAIR_FAILED"})
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
