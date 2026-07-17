"""Local management commands for authorized Forwarder operators."""
from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.security import sanitize_input
from backend.services.user_service import hash_password
from backend.services.reference_schema_service import build_readiness_report, export_backfill_inventory, write_json_report
from backend.services.reference_backfill_service import apply_package, diff_package, export_inventory_package, validate_package
from backend.services.tracking_location_bootstrap_service import bootstrap as bootstrap_tracking_locations
from backend.config import get_database_uri


ADMIN_ROLE = "admin"
FULL_NAME_MAX_LENGTH = 100
USERNAME_MAX_LENGTH = 50
PASSWORD_MAX_LENGTH = 100


class AdminInputError(ValueError):
    """Raised when an interactive administrator value is invalid."""


def normalize_full_name(value: str) -> str:
    """Trim and validate a full name using the existing model limit."""
    normalized = value.strip()
    if not normalized:
        raise AdminInputError("نام مدیر نمی‌تواند خالی باشد.")
    if len(normalized) > FULL_NAME_MAX_LENGTH:
        raise AdminInputError(
            f"نام مدیر نباید بیشتر از {FULL_NAME_MAX_LENGTH} نویسه باشد."
        )
    return normalized


def normalize_username(value: str) -> str:
    """Apply the login flow's existing username normalization and limit."""
    normalized = sanitize_input({"username": value})["username"]
    if not normalized:
        raise AdminInputError("نام کاربری نمی‌تواند خالی باشد.")
    if len(normalized) > USERNAME_MAX_LENGTH:
        raise AdminInputError(
            f"نام کاربری نباید بیشتر از {USERNAME_MAX_LENGTH} نویسه باشد."
        )
    return normalized


def validate_password(password: str, confirmation: str) -> None:
    """Validate the password against the current login contract."""
    if not password:
        raise AdminInputError("رمز عبور نمی‌تواند خالی باشد.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise AdminInputError(
            f"رمز عبور نباید بیشتر از {PASSWORD_MAX_LENGTH} نویسه باشد."
        )
    if password != confirmation:
        raise AdminInputError("رمز عبور و تکرار آن یکسان نیستند.")


def create_admin_record(app, full_name: str, username: str, password: str) -> ExpertUser:
    """Insert one administrator atomically using the existing model and hash."""
    with app.app_context():
        try:
            full_name = normalize_full_name(full_name)
            username = normalize_username(username)
            validate_password(password, password)

            if ExpertUser.query.filter_by(username=username).first() is not None:
                raise AdminInputError("این نام کاربری قبلاً استفاده شده است.")

            administrator = ExpertUser(
                full_name=full_name,
                username=username,
                password_hash=hash_password(password),
                role=ADMIN_ROLE,
                is_active=True,
                email=None,
                phone=None,
            )
            db.session.add(administrator)
            db.session.commit()

            created = ExpertUser.query.filter_by(username=username).one_or_none()
            if created is None:
                raise SQLAlchemyError("created administrator could not be verified")
            return created
        except (AdminInputError, IntegrityError, SQLAlchemyError):
            db.session.rollback()
            raise
        except Exception:
            db.session.rollback()
            raise


def run_create_admin(
    *,
    app_factory: Callable[..., object] = create_app,
    input_func: Callable[[str], str] = input,
    password_func: Callable[[str], str] = getpass.getpass,
    output_func: Callable[[str], None] = print,
) -> int:
    """Run the interactive create-admin workflow."""
    try:
        full_name = normalize_full_name(input_func("نام مدیر: "))
        username = normalize_username(input_func("نام کاربری: "))
        password = password_func("رمز عبور: ")
        confirmation = password_func("تکرار رمز عبور: ")
        validate_password(password, confirmation)
    except AdminInputError as exc:
        output_func(f"خطا: {exc}")
        return 1

    output_func("")
    output_func(f"نام مدیر: {full_name}")
    output_func(f"نام کاربری: {username}")
    output_func(f"نقش: {ADMIN_ROLE}")
    output_func("وضعیت: فعال")

    answer = input_func("آیا حساب مدیر ایجاد شود؟ [y/N] ").strip().lower()
    if answer != "y":
        output_func("ایجاد حساب مدیر لغو شد.")
        return 0

    try:
        app = app_factory(skip_startup=True)
        created = create_admin_record(app, full_name, username, password)
    except AdminInputError as exc:
        output_func(f"خطا: {exc}")
        return 1
    except (IntegrityError, SQLAlchemyError):
        output_func("خطا: ایجاد حساب مدیر انجام نشد.")
        return 1
    except Exception:
        output_func("خطا: ایجاد حساب مدیر انجام نشد.")
        return 1

    output_func("حساب مدیر با موفقیت ایجاد شد.")
    output_func(f"نام کاربری: {created.username}")
    output_func(f"نقش: {created.role}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the standard-library command parser."""
    parser = argparse.ArgumentParser(description="فرمان‌های مدیریتی محلی Forwarder")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("create-admin", help="ایجاد مدیر اولیه شرکت")
    readiness = subparsers.add_parser("reference-schema-readiness", help="read-only reference schema readiness report")
    readiness.add_argument("--database", help="authorized database name; credentials come from secure configuration")
    readiness.add_argument("--json-report", type=Path, help="external JSON report path")
    readiness.add_argument("--strict", action="store_true", help="return non-zero when backfill is required")
    inventory = subparsers.add_parser("export-reference-backfill-inventory", help="read-only owner-review inventory; generates no codes")
    inventory.add_argument("--database", help="authorized database name; credentials come from secure configuration")
    inventory.add_argument("--output", type=Path, help="legacy external CSV output path")
    inventory.add_argument("--output-directory", type=Path, help="external versioned package directory")
    inventory.add_argument("--domains", help="comma-separated domain names")
    inventory.add_argument("--json-summary", type=Path)
    inventory.add_argument("--strict", action="store_true")
    validator = subparsers.add_parser("validate-reference-backfill", help="validate a Backfill package without writes")
    validator.add_argument("--path", type=Path, required=True); validator.add_argument("--against-database")
    validator.add_argument("--strict", action="store_true"); validator.add_argument("--json-report", type=Path); validator.add_argument("--markdown-report", type=Path)
    diff = subparsers.add_parser("diff-reference-backfill", help="deterministic read-only Backfill diff")
    diff.add_argument("--path", type=Path, required=True); diff.add_argument("--database", required=True)
    apply_cmd = subparsers.add_parser("apply-reference-backfill", help="guarded Backfill dry-run/apply")
    apply_cmd.add_argument("--path", type=Path, required=True); apply_cmd.add_argument("--database", required=True); apply_cmd.add_argument("--apply", action="store_true")
    tracking_locations = subparsers.add_parser("bootstrap-china-iran-tracking-locations", help="dry-run/apply curated internal tracking checkpoints")
    tracking_locations.add_argument("--database", required=True, help="explicit authorized database name")
    tracking_locations.add_argument("--apply", action="store_true", help="persist the idempotent bootstrap")
    return parser


def _database_config(database: str | None):
    if database is None:
        return None
    if "://" in database or not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise ValueError("--database accepts a database name only; credentials must come from secure configuration")
    current = urlsplit(get_database_uri())
    return {"SQLALCHEMY_DATABASE_URI": urlunsplit((current.scheme, current.netloc, "/" + database, current.query, current.fragment))}


def _run_reference_command(args) -> int:
    try:
        config = _database_config(args.database)
    except ValueError as exc:
        print(f"BLOCKED: {exc}")
        return 2
    app = create_app(config, skip_startup=True)
    with app.app_context():
        try:
            if db.engine.dialect.name == "postgresql":
                db.session.execute(text("SET TRANSACTION READ ONLY"))
                if db.session.execute(text("SHOW transaction_read_only")).scalar_one() != "on":
                    print("BLOCKED: database transaction is not read-only")
                    return 2
            if args.command == "reference-schema-readiness":
                report = build_readiness_report()
                if args.json_report:
                    write_json_report(report, args.json_report)
                print(json.dumps(report, ensure_ascii=False, sort_keys=True))
                return 1 if args.strict and report["status"] != "SCHEMA_READY" else 0
            if args.output_directory:
                domains=set(args.domains.split(",")) if args.domains else None
                summary=export_inventory_package(args.output_directory,database_name=db.session.execute(text("select current_database()" )).scalar_one() if db.engine.dialect.name=="postgresql" else "sqlite",domains=domains)
                if args.json_summary: write_json_report(summary,args.json_summary)
                print(json.dumps(summary,sort_keys=True)); return 3
            if not args.output: print("BLOCKED: --output or --output-directory is required"); return 2
            count = export_backfill_inventory(args.output)
            print(f"BACKFILL_REQUIRED: exported {count} reconciliation rows; generated codes=0")
            return 0
        finally:
            db.session.rollback()


def configure_console_encoding() -> None:
    """Ensure Persian prompts render correctly in Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch a supported management command."""
    configure_console_encoding()
    args = build_parser().parse_args(argv)
    if args.command == "create-admin":
        return run_create_admin()
    if args.command == "bootstrap-china-iran-tracking-locations":
        if args.database == "forwarder_db":
            print("BLOCKED: forwarder_db is permanently read-only")
            return 2
        try: config=_database_config(args.database)
        except ValueError as exc: print(f"BLOCKED: {exc}"); return 2
        app=create_app(config,skip_startup=True)
        with app.app_context():
            payload=bootstrap_tracking_locations(apply=args.apply)
            print(json.dumps(payload,ensure_ascii=False,sort_keys=True))
            return 0
    if args.command in {"reference-schema-readiness", "export-reference-backfill-inventory"}:
        return _run_reference_command(args)
    def result_exit(payload: dict) -> int:
        if payload.get("code") == "FORBIDDEN_TARGET": return 4
        if payload.get("code") == "TRANSACTION_ROLLED_BACK": return 5
        return {"PASS":0,"PASS_WITH_WARNINGS":0,"REJECTED":1,"BLOCKED":2,"AWAITING_OWNER_INPUT":3}.get(payload.get("status"),6)
    if args.command == "validate-reference-backfill" and not args.against_database:
        result=validate_package(args.path); payload=result.as_dict()
        if args.json_report: write_json_report(payload,args.json_report)
        if args.markdown_report:
            args.markdown_report.write_text("# Backfill validation\n\nStatus: " + payload["status"] + "\n",encoding="utf-8")
        print(json.dumps(payload,sort_keys=True)); return result_exit(payload)
    if args.command in {"validate-reference-backfill","diff-reference-backfill","apply-reference-backfill"}:
        database=args.against_database if args.command=="validate-reference-backfill" else args.database
        try: config=_database_config(database)
        except ValueError as exc: print(f"BLOCKED: {exc}"); return 2
        app=create_app(config,skip_startup=True)
        with app.app_context():
            try:
                if db.engine.dialect.name=="postgresql" and not (args.command=="apply-reference-backfill" and args.apply):
                    db.session.execute(text("SET TRANSACTION READ ONLY"))
                    if db.session.execute(text("SHOW transaction_read_only")).scalar_one()!="on":
                        print(json.dumps({"status":"BLOCKED","code":"READ_ONLY_NOT_ENFORCED"})); return 2
                if args.command=="validate-reference-backfill": payload=validate_package(args.path,against_database=True).as_dict()
                elif args.command=="diff-reference-backfill": payload=diff_package(args.path)
                else: payload=apply_package(args.path,database_name=database,apply=args.apply)
                if args.command=="validate-reference-backfill":
                    if args.json_report: write_json_report(payload,args.json_report)
                    if args.markdown_report: args.markdown_report.write_text("# Backfill validation\n\nStatus: " + payload["status"] + "\n",encoding="utf-8")
                print(json.dumps(payload,sort_keys=True)); return result_exit(payload)
            finally: db.session.rollback()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
