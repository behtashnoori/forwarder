"""Local management commands for authorized Forwarder operators."""
from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.security import sanitize_input
from backend.services.user_service import hash_password


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
    return parser


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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
