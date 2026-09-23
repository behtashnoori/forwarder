"""Security and environment-policy checks for Customer Portal recovery email."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from flask import Flask

from backend.services import customer_recovery_email_service as email_service


def _app(**overrides) -> Flask:
    app = Flask(__name__)
    app.config.update(
        APP_ENV="testing",
        CUSTOMER_RECOVERY_EMAIL_ENABLED=False,
        CUSTOMER_RECOVERY_EMAIL_FROM="portal@example.test",
        CUSTOMER_RECOVERY_SMTP_HOST="smtp.example.test",
        CUSTOMER_RECOVERY_SMTP_PORT=587,
        CUSTOMER_RECOVERY_SMTP_USERNAME="",
        CUSTOMER_RECOVERY_SMTP_PASSWORD="",
        CUSTOMER_RECOVERY_SMTP_USE_STARTTLS=False,
        CUSTOMER_RECOVERY_SMTP_USE_SSL=False,
        CUSTOMER_RECOVERY_SMTP_TIMEOUT_SECONDS=3,
        FRONTEND_URL="https://portal.example.test",
    )
    app.config.update(overrides)
    return app


def test_enabled_production_configuration_fails_closed_when_incomplete():
    with pytest.raises(RuntimeError):
        email_service.validate_recovery_email_configuration({
            "APP_ENV": "production",
            "CUSTOMER_RECOVERY_EMAIL_ENABLED": True,
        })


def test_nonproduction_delivery_is_suppressed_without_opening_smtp(monkeypatch):
    monkeypatch.setattr(
        email_service.smtplib,
        "SMTP",
        lambda *args, **kwargs: pytest.fail("SMTP must not open outside Production"),
    )
    app = _app(CUSTOMER_RECOVERY_EMAIL_ENABLED=True)
    with app.app_context():
        status = email_service.send_password_recovery_email(
            "customer@example.test",
            "https://portal.example.test/customer/reset-password?token=secret",
            datetime.utcnow() + timedelta(minutes=30),
        )
    assert status == email_service.DELIVERY_SUPPRESSED


def test_production_delivery_uses_smtp_without_logging_capability(monkeypatch, caplog):
    sent = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def ehlo(self): pass
        def starttls(self, **kwargs): pass
        def login(self, username, password): pass
        def send_message(self, message): sent.append(message)

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    app = _app(APP_ENV="production", CUSTOMER_RECOVERY_EMAIL_ENABLED=True)
    reset_url = "https://portal.example.test/customer/reset-password?token=top-secret"
    with app.app_context():
        status = email_service.send_password_recovery_email(
            "customer@example.test",
            reset_url,
            datetime.utcnow() + timedelta(minutes=30),
        )
    assert status == email_service.DELIVERY_SENT
    assert len(sent) == 1
    assert reset_url in sent[0].get_content()
    assert "customer@example.test" in sent[0]["To"]
    assert "top-secret" not in caplog.text
    assert reset_url not in caplog.text
    assert "customer@example.test" not in caplog.text


def test_smtp_failure_returns_failed_without_exposing_exception(monkeypatch, caplog):
    class BrokenSMTP:
        def __init__(self, *args, **kwargs):
            raise OSError("provider failed while handling token=secret")

    monkeypatch.setattr(email_service.smtplib, "SMTP", BrokenSMTP)
    app = _app(APP_ENV="production", CUSTOMER_RECOVERY_EMAIL_ENABLED=True)
    with app.app_context():
        status = email_service.send_password_recovery_email(
            "customer@example.test",
            "https://portal.example.test/customer/reset-password?token=secret",
            datetime.utcnow() + timedelta(minutes=30),
        )
    assert status == email_service.DELIVERY_FAILED
    assert "token=secret" not in caplog.text
    assert "customer@example.test" not in caplog.text
