"""Contract tests for the local initial-administrator command."""
from __future__ import annotations

import bcrypt
import pytest
from sqlalchemy.exc import SQLAlchemyError

import manage
from backend import create_app
from backend.auth import can_manage_user
from backend.extensions import db
from backend.models import ExpertUser
from backend.security import can_access_role


@pytest.fixture
def admin_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        },
        skip_startup=True,
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _run(
    admin_app,
    *,
    answers=None,
    passwords=None,
    output=None,
    app_factory=None,
):
    answers = iter(answers or ["مدیر آزمایشی", "synthetic_admin", "y"])
    passwords = iter(passwords or ["SyntheticPass123!", "SyntheticPass123!"])
    output = output if output is not None else []
    return manage.run_create_admin(
        app_factory=app_factory or (lambda **_: admin_app),
        input_func=lambda prompt: next(answers),
        password_func=lambda prompt: next(passwords),
        output_func=output.append,
    ), output


def test_command_exists_and_unknown_command_is_rejected():
    parser = manage.build_parser()
    assert parser.parse_args(["create-admin"]).command == "create-admin"
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["unsupported"])
    assert exc_info.value.code != 0


def test_console_encoding_configuration_is_safe(monkeypatch):
    configured = []

    class Stream:
        def reconfigure(self, **kwargs):
            configured.append(kwargs)

    monkeypatch.setattr(manage.sys, "stdout", Stream())
    monkeypatch.setattr(manage.sys, "stderr", Stream())
    manage.configure_console_encoding()
    assert configured == [{"encoding": "utf-8"}, {"encoding": "utf-8"}]


def test_success_creates_exactly_one_compatible_active_admin(admin_app):
    code, output = _run(admin_app)
    assert code == 0

    with admin_app.app_context():
        users = ExpertUser.query.all()
        assert len(users) == 1
        created = users[0]
        assert created.full_name == "مدیر آزمایشی"
        assert created.username == "synthetic_admin"
        assert created.role == "admin"
        assert created.is_active is True
        assert created.email is None
        assert created.phone is None
        assert created.password_hash != "SyntheticPass123!"
        assert bcrypt.checkpw(
            b"SyntheticPass123!", created.password_hash.encode("utf-8")
        )
        assert can_access_role(created.role, "admin") is True

        expert = ExpertUser(
            full_name="کارشناس آزمایشی",
            username="synthetic_expert",
            password_hash=manage.hash_password("SyntheticExpert123!"),
            role="expert",
        )
        db.session.add(expert)
        db.session.flush()
        assert can_manage_user(created, expert) is True

    rendered = "\n".join(output)
    assert "حساب مدیر با موفقیت ایجاد شد." in rendered
    assert "SyntheticPass123!" not in rendered
    with admin_app.app_context():
        assert ExpertUser.query.one().password_hash not in rendered


@pytest.mark.parametrize(
    ("answers", "passwords", "expected"),
    [
        (["   ", "synthetic_admin"], [], "نام مدیر نمی‌تواند خالی باشد"),
        (["مدیر آزمایشی", "   "], [], "نام کاربری نمی‌تواند خالی باشد"),
        (
            ["مدیر آزمایشی", "synthetic_admin"],
            ["SyntheticPass123!", "DifferentPass123!"],
            "یکسان نیستند",
        ),
    ],
)
def test_invalid_interactive_values_are_rejected_without_insert(
    admin_app, answers, passwords, expected
):
    code, output = _run(admin_app, answers=answers, passwords=passwords)
    assert code == 1
    assert expected in "\n".join(output)
    with admin_app.app_context():
        assert ExpertUser.query.count() == 0


def test_confirmation_defaults_to_no_and_never_opens_database_context(admin_app):
    factory_called = False

    def forbidden_factory(**_):
        nonlocal factory_called
        factory_called = True
        raise AssertionError("factory must not be called on cancellation")

    code, output = _run(
        admin_app,
        answers=["مدیر آزمایشی", "synthetic_admin", ""],
        app_factory=forbidden_factory,
    )
    assert code == 0
    assert factory_called is False
    assert "ایجاد حساب مدیر لغو شد." in output
    with admin_app.app_context():
        assert ExpertUser.query.count() == 0


def test_duplicate_does_not_overwrite_promote_or_reset_existing_user(admin_app):
    original_hash = manage.hash_password("OriginalSynthetic123!")
    with admin_app.app_context():
        existing = ExpertUser(
            full_name="کارشناس موجود",
            username="duplicate_user",
            password_hash=original_hash,
            role="expert",
            is_active=True,
        )
        db.session.add(existing)
        db.session.commit()

    code, output = _run(
        admin_app,
        answers=["مدیر جایگزین", " duplicate_user ", "y"],
    )
    assert code == 1
    assert "قبلاً استفاده شده است" in "\n".join(output)

    with admin_app.app_context():
        users = ExpertUser.query.all()
        assert len(users) == 1
        assert users[0].full_name == "کارشناس موجود"
        assert users[0].role == "expert"
        assert users[0].password_hash == original_hash


def test_database_failure_rolls_back_without_sensitive_output(admin_app, monkeypatch):
    password = "RollbackSynthetic123!"
    output = []

    def fail_commit():
        raise SQLAlchemyError("synthetic database failure")

    with admin_app.app_context():
        monkeypatch.setattr(db.session, "commit", fail_commit)
        code, output = _run(
            admin_app,
            passwords=[password, password],
            output=output,
        )
        assert code == 1
        assert ExpertUser.query.count() == 0

    rendered = "\n".join(output)
    assert rendered == "\nنام مدیر: مدیر آزمایشی\nنام کاربری: synthetic_admin\nنقش: admin\nوضعیت: فعال\nخطا: ایجاد حساب مدیر انجام نشد."
    assert password not in rendered


def test_prompts_are_limited_to_required_values_and_role_is_not_prompted(admin_app):
    prompts = []
    answers = iter(["مدیر آزمایشی", "synthetic_admin", "n"])
    passwords = iter(["SyntheticPass123!", "SyntheticPass123!"])

    code = manage.run_create_admin(
        app_factory=lambda **_: admin_app,
        input_func=lambda prompt: prompts.append(prompt) or next(answers),
        password_func=lambda prompt: prompts.append(prompt) or next(passwords),
        output_func=lambda _: None,
    )

    assert code == 0
    assert prompts == [
        "نام مدیر: ",
        "نام کاربری: ",
        "رمز عبور: ",
        "تکرار رمز عبور: ",
        "آیا حساب مدیر ایجاد شود؟ [y/N] ",
    ]
    prompt_text = " ".join(prompts)
    for forbidden in ("ایمیل", "موبایل", "تلفن", "شرکت", "سازمان", "نقش"):
        assert forbidden not in prompt_text


def test_model_schema_and_scope_are_unchanged():
    columns = set(ExpertUser.__table__.columns.keys())
    assert {"full_name", "username", "password_hash", "role", "is_active"} <= columns
    assert {"email", "phone"} <= columns
    assert "company_id" not in columns
    assert "organization_id" not in columns
    assert "tenant_id" not in columns
    assert manage.ADMIN_ROLE == "admin"
    assert "super_admin" not in vars(manage).values()
