"""Tests for Phase 2 security and runtime configuration hardening."""
from __future__ import annotations

import os

import pytest

from backend import config as runtime_config
from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser


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

CANONICAL_ORIGIN = "https://samand.forwarderet.ir"
LEGACY_ORIGIN = "https://server.logisticmarket.ir"


def _clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in PRODUCTION_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_env_loader_respects_process_database_url(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Local env files must not override an explicit process DATABASE_URL."""
    project_root = tmp_path / "project"
    backend_dir = project_root / "backend"
    backend_dir.mkdir(parents=True)
    (project_root / ".env").write_text(
        "DATABASE_URL=postgresql://test_user:change_me@localhost:5432/forwarder_test",
        encoding="utf-8",
    )
    process_url = "postgresql://test_user:change_me@localhost:5432/forwarder_test"
    monkeypatch.setenv("DATABASE_URL", process_url)

    loaded = runtime_config.load_env_files(
        project_root=str(project_root),
        backend_dir=str(backend_dir),
        emit_log=False,
    )

    assert loaded == (str(project_root / ".env"),)
    assert os.environ["DATABASE_URL"] == process_url


def test_env_loader_supports_backend_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """backend/.env is supported when a root .env is absent."""
    project_root = tmp_path / "project"
    backend_dir = project_root / "backend"
    backend_dir.mkdir(parents=True)
    backend_url = "postgresql://test_user:change_me@localhost:5432/forwarder_test"
    (backend_dir / ".env").write_text(f"DATABASE_URL={backend_url}\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    loaded = runtime_config.load_env_files(
        project_root=str(project_root),
        backend_dir=str(backend_dir),
        emit_log=False,
    )

    assert loaded == (str(backend_dir / ".env"),)
    assert os.environ["DATABASE_URL"] == backend_url


def test_database_url_diagnostics_do_not_expose_password():
    """Startup diagnostics should identify the DB without printing secrets."""
    summary = runtime_config.format_database_url_diagnostics(
        "postgresql+psycopg2://test_user:change_me@localhost:5432/forwarder_db"
    )

    assert "super-secret" not in summary
    assert "postgresql" in summary
    assert "psycopg2" in summary
    assert "localhost" in summary
    assert "forwarder_db" in summary


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
    monkeypatch.setenv("DATABASE_URL", "postgresql://test_user:change_me@localhost:5432/forwarder_test")
    monkeypatch.setenv("SECRET_KEY", "development-secret-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "deployment-specific-jwt-secret")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.forwarder.test")

    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        create_app(skip_startup=True)


def test_production_rejects_open_cors(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Production must not allow wildcard/allow-all CORS."""
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test_user:change_me@localhost:5432/forwarder_test")
    monkeypatch.setenv("SECRET_KEY", "deployment-specific-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "deployment-specific-jwt-secret")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "durable-documents"))

    with pytest.raises(RuntimeError, match="Wildcard CORS origins"):
        create_app(skip_startup=True)


def _production_cors_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test_user:change_me@localhost:5432/forwarder_test")
    monkeypatch.setenv("SECRET_KEY", "deployment-specific-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "deployment-specific-jwt-secret")
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "durable-documents"))
    monkeypatch.setenv("CORS_ALLOW_ALL_ORIGINS", "0")


def test_production_requires_and_allows_the_canonical_cors_origin(monkeypatch, tmp_path):
    _production_cors_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("CORS_ORIGINS", CANONICAL_ORIGIN)

    app = create_app(skip_startup=True)
    client = app.test_client()
    response = client.open("/api/health", method="OPTIONS", headers={
        "Origin": CANONICAL_ORIGIN, "Access-Control-Request-Method": "GET",
    })
    assert response.headers["Access-Control-Allow-Origin"] == CANONICAL_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"

    rejected = client.open("/api/health", method="OPTIONS", headers={
        "Origin": "https://unknown.forwarderet.ir", "Access-Control-Request-Method": "GET",
    })
    assert "Access-Control-Allow-Origin" not in rejected.headers


def test_production_rejects_legacy_or_missing_canonical_cors_origin(monkeypatch, tmp_path):
    _production_cors_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("CORS_ORIGINS", LEGACY_ORIGIN)

    with pytest.raises(RuntimeError, match="canonical Production CORS origin"):
        create_app(skip_startup=True)


def test_cors_origin_alias_and_plural_value_must_not_disagree(monkeypatch):
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", CANONICAL_ORIGIN)
    monkeypatch.setenv("CORS_ORIGIN", LEGACY_ORIGIN)

    with pytest.raises(RuntimeError, match="must not disagree"):
        runtime_config.get_configured_cors_origins()


def test_cors_origin_alias_parses_when_plural_value_is_absent(monkeypatch):
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGIN", CANONICAL_ORIGIN)

    assert runtime_config.get_configured_cors_origins() == [CANONICAL_ORIGIN]


def test_testing_mode_uses_isolated_database_even_with_production_env(monkeypatch: pytest.MonkeyPatch):
    """Testing mode must remain isolated from production DATABASE_URL."""
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test_user:change_me@localhost:5432/forwarder_test")
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///:memory:")

    app = create_app({"TESTING": True}, skip_startup=True)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["SECRET_KEY"] == "test-secret-key"
    assert app.config["JWT_SECRET_KEY"].startswith("test-jwt-secret-key")


def test_crm_customers_requires_authentication():
    """CRM customer data is sensitive and must require a bearer token."""
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
    client = app.test_client()

    response = client.get("/api/crm/customers")

    assert response.status_code == 401


def test_crm_customers_rejects_expert_role():
    """Basic experts should not receive CRM customer listings."""
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
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
        from backend.services.auth_session_service import create_session_tokens
        token = create_session_tokens(user_id)["access_token"]

    client = app.test_client()
    response = client.get("/api/crm/customers", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_monitoring_metrics_rejects_expert_role():
    """Operational monitoring metrics require supervisor-level access or higher."""
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
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
        from backend.services.auth_session_service import create_session_tokens
        token = create_session_tokens(user_id)["access_token"]

    client = app.test_client()
    response = client.get("/api/monitoring/metrics", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
