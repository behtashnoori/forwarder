"""Tests for Phase 2 security and runtime configuration hardening."""
from __future__ import annotations

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.security import security


PRODUCTION_ENV_KEYS = (
    "APP_ENV",
    "ENV",
    "FLASK_ENV",
    "DATABASE_URL",
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "CORS_ORIGINS",
    "CORS_ORIGIN",
    "CORS_ALLOW_ALL_ORIGINS",
)


def _clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in PRODUCTION_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_production_requires_sensitive_environment(monkeypatch: pytest.MonkeyPatch):
    """Production must fail fast before connecting with incomplete config."""
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        create_app(skip_startup=True)


def test_production_rejects_placeholder_secret(monkeypatch: pytest.MonkeyPatch):
    """Production must not accept documented/dev placeholder secrets."""
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@db:5432/app")
    monkeypatch.setenv("SECRET_KEY", "development-secret-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "deployment-specific-jwt-secret")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.forwarder.test")

    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        create_app(skip_startup=True)


def test_production_rejects_open_cors(monkeypatch: pytest.MonkeyPatch):
    """Production must not allow wildcard/allow-all CORS."""
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@db:5432/app")
    monkeypatch.setenv("SECRET_KEY", "deployment-specific-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "deployment-specific-jwt-secret")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="Wildcard CORS origins"):
        create_app(skip_startup=True)


def test_testing_mode_uses_isolated_database_even_with_production_env(monkeypatch: pytest.MonkeyPatch):
    """Testing mode must remain isolated from production DATABASE_URL."""
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@db:5432/production")
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///:memory:")

    app = create_app({"TESTING": True}, skip_startup=True)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["SECRET_KEY"] == "test-secret-key"
    assert app.config["JWT_SECRET_KEY"].startswith("test-jwt-secret-key")


def test_crm_customers_requires_authentication():
    """CRM customer data is sensitive and must require a bearer token."""
    app = create_app({"TESTING": True}, skip_startup=True)
    client = app.test_client()

    response = client.get("/api/crm/customers")

    assert response.status_code == 401


def test_crm_customers_rejects_expert_role():
    """Basic experts should not receive CRM customer listings."""
    app = create_app({"TESTING": True}, skip_startup=True)
    with app.app_context():
        db.session.add(
            ExpertUser(
                username="expert_role_check",
                password_hash="unused",
                full_name="Expert Role Check",
                email="expert-role-check@example.test",
                role="expert",
                is_active=True,
            )
        )
        db.session.commit()
        user_id = ExpertUser.query.filter_by(username="expert_role_check").first().id
        token = security.generate_token(user_id, "access")

    client = app.test_client()
    response = client.get("/api/crm/customers", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_monitoring_metrics_rejects_expert_role():
    """Operational monitoring metrics require supervisor-level access or higher."""
    app = create_app({"TESTING": True}, skip_startup=True)
    with app.app_context():
        db.session.add(
            ExpertUser(
                username="monitoring_expert_role_check",
                password_hash="unused",
                full_name="Monitoring Expert Role Check",
                email="monitoring-expert-role-check@example.test",
                role="expert",
                is_active=True,
            )
        )
        db.session.commit()
        user_id = ExpertUser.query.filter_by(username="monitoring_expert_role_check").first().id
        token = security.generate_token(user_id, "access")

    client = app.test_client()
    response = client.get("/api/monitoring/metrics", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
