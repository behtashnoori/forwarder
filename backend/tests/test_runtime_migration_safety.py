"""Regression tests for explicit migration and non-mutating startup policy."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from backend import create_app
from backend.migration_runtime import (
    RevisionStatus,
    alembic_config,
    prepare_version_table_for_upgrade,
    revision_status,
)


ROOT = Path(__file__).parents[2]


def test_create_app_does_not_connect_or_migrate(tmp_path):
    unavailable = tmp_path / "missing-parent" / "runtime.sqlite3"
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{unavailable.as_posix()}",
            "SECRET_KEY": "runtime-test-only",
            "JWT_SECRET_KEY": "runtime-test-only",
        }
    )
    assert app is not None
    assert not unavailable.exists()


def test_skip_startup_testing_does_not_create_schema(tmp_path):
    database = tmp_path / "skip-startup.sqlite3"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
        },
        skip_startup=True,
    )
    assert app is not None
    assert not database.exists()


def test_alembic_config_is_absolute_and_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = alembic_config("sqlite:///:memory:")
    assert Path(cfg.get_main_option("script_location")).is_absolute()
    assert Path(cfg.get_main_option("script_location")).name == "migrations"


def test_alembic_config_accepts_percent_encoded_credentials():
    cfg = alembic_config("postgresql://test_user:change_me@localhost:5432/forwarder_test")
    assert cfg.get_main_option("sqlalchemy.url") == (
        "postgresql://test_user:change_me@localhost:5432/forwarder_test"
    )


def test_revision_status_on_isolated_empty_database_is_read_only(tmp_path):
    database = tmp_path / "empty.sqlite3"
    status = revision_status(f"sqlite:///{database.as_posix()}")
    assert status.current == ()
    assert status.pending is True
    # Connecting creates only the SQLite file; no Alembic or domain tables.
    import sqlite3

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "select name from sqlite_master where type='table'"
        ).fetchall() == []


def test_explicit_upgrade_preparation_leaves_sqlite_to_alembic(tmp_path):
    database = tmp_path / "upgrade.sqlite3"
    url = f"sqlite:///{database.as_posix()}"
    cfg = alembic_config(url)
    prepare_version_table_for_upgrade(url, cfg)

    import sqlite3

    with sqlite3.connect(database) as connection:
        columns = connection.execute("pragma table_info(alembic_version)").fetchall()
    assert columns == []


def test_runtime_rejects_auto_migrate(monkeypatch):
    monkeypatch.setenv("AUTO_MIGRATE_ON_STARTUP", "true")
    from backend.runtime import create_runtime_app

    with pytest.raises(RuntimeError, match="unsupported"):
        create_runtime_app()


@pytest.mark.parametrize("environment", ["production", "prod"])
def test_production_runtime_fails_fast_when_migrations_are_pending(
    monkeypatch, environment, tmp_path
):
    import backend.runtime as runtime

    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": environment,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "DOCUMENT_STORAGE_ROOT": str(tmp_path / "durable-documents"),
        },
        skip_startup=True,
    )
    monkeypatch.delenv("AUTO_MIGRATE_ON_STARTUP", raising=False)
    monkeypatch.setattr(runtime, "create_app", lambda skip_startup=True: app)
    monkeypatch.setattr(
        runtime,
        "readiness_report",
        lambda _app: {
            "ready": False,
            "database": "connected",
            "migrations": "pending",
            "critical_tables": "ready",
        },
    )
    with pytest.raises(RuntimeError, match="Production startup blocked"):
        runtime.create_runtime_app()


def test_readiness_endpoint_returns_503_for_unversioned_schema():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        },
        skip_startup=True,
    )
    response = app.test_client().get("/api/health/ready")
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["database"] == "connected"
    assert payload["migrations"] == "pending"


def test_readiness_endpoint_returns_revisions_when_ready(monkeypatch):
    import backend.runtime as runtime

    app = create_app({"TESTING": True}, skip_startup=True)
    monkeypatch.setattr(
        runtime,
        "readiness_report",
        lambda _app: {
            "ready": True,
            "database": "connected",
            "migrations": "current",
            "critical_tables": "ready",
            "current_revisions": ["revision-a"],
            "head_revisions": ["revision-a"],
            "missing_tables": [],
        },
    )
    response = app.test_client().get("/api/health/ready")
    assert response.status_code == 200
    assert response.get_json()["current_revisions"] == ["revision-a"]
    assert response.get_json()["head_revisions"] == ["revision-a"]


def test_health_is_db_only_and_masks_failures(monkeypatch):
    from backend.extensions import db

    app = create_app({"TESTING": True}, skip_startup=True)

    def fail(_statement):
        raise RuntimeError("postgresql://test_user:change_me@localhost:5432/forwarder_test SELECT password")

    monkeypatch.setattr(db.session, "execute", fail)
    response = app.test_client().get("/api/health?readiness=1")
    body = response.get_data(as_text=True)
    assert response.status_code == 503
    assert "secret" not in body
    assert "private" not in body
    assert "SELECT" not in body


def test_ping_never_touches_database(monkeypatch):
    from backend.extensions import db

    app = create_app({"TESTING": True}, skip_startup=True)
    monkeypatch.setattr(
        db.session,
        "execute",
        lambda _statement: pytest.fail("ping must not query the database"),
    )
    assert app.test_client().get("/api/health/ping").status_code == 200


@pytest.mark.parametrize(
    ("command", "status", "expected"),
    [
        ("current", RevisionStatus(("a",), ("b",)), 0),
        ("check", RevisionStatus(("a",), ("a",)), 0),
        ("check", RevisionStatus(("a",), ("b",)), 2),
    ],
)
def test_migration_cli_read_only_exit_codes(monkeypatch, command, status, expected):
    import backend.migration_cli as cli

    monkeypatch.setattr(cli, "database_url", lambda: "postgresql://test_user:change_me@localhost:5432/forwarder_test")
    monkeypatch.setattr(cli, "revision_status", lambda _url: status)
    assert cli.main([command]) == expected


def test_migration_cli_refuses_unconfirmed_upgrade(monkeypatch):
    import backend.migration_cli as cli

    monkeypatch.setattr(cli, "database_url", lambda: "sqlite:///:memory:")
    monkeypatch.setattr(cli, "alembic_config", lambda _url: pytest.fail("must not configure upgrade"))
    assert cli.main(["upgrade"]) == 2


def test_migration_cli_confirmed_upgrade_is_explicit(monkeypatch):
    import backend.migration_cli as cli

    calls = []
    config = object()
    monkeypatch.setattr(cli, "database_url", lambda: "sqlite:///:memory:")
    monkeypatch.setattr(cli, "alembic_config", lambda _url: config)
    monkeypatch.setattr(cli, "prepare_version_table_for_upgrade", lambda url, cfg: calls.append(("prepare", url, cfg)))
    monkeypatch.setattr(cli.command, "upgrade", lambda cfg, revision: calls.append(("upgrade", cfg, revision)))
    assert cli.main(["upgrade", "head", "--confirm"]) == 0
    assert calls == [
        ("prepare", "sqlite:///:memory:", config),
        ("upgrade", config, "head"),
    ]


def test_migration_cli_error_boundary_masks_details(monkeypatch, capsys):
    import backend.migration_cli as cli

    monkeypatch.setattr(
        cli,
        "database_url",
        lambda: (_ for _ in ()).throw(RuntimeError("postgresql://test_user:change_me@localhost:5432/forwarder_test")),
    )
    assert cli.run(["current"]) == 1
    captured = capsys.readouterr()
    assert "secret" not in captured.err
    assert "private" not in captured.err


def test_wsgi_exports_runtime_app_without_root_wsgi(monkeypatch):
    import backend.runtime as runtime

    sentinel = SimpleNamespace(name="runtime-app")
    monkeypatch.setattr(runtime, "create_runtime_app", lambda: sentinel)
    sys.modules.pop("backend.wsgi", None)
    module = importlib.import_module("backend.wsgi")
    assert module.app is sentinel
    assert not (ROOT / "wsgi.py").exists()


def test_windows_launcher_has_ownership_and_health_guards():
    launcher = (ROOT / "scripts" / "backend-service.ps1").read_text(encoding="utf-8")
    lowered = launcher.lower()
    assert "get-nettcpconnection" in lowered
    assert "get-ciminstance win32_process" in lowered
    assert "executablepath" in lowered
    assert "backend.wsgi:app" in launcher
    assert "/api/health/ping" in launcher
    assert "/api/health/ready" in launcher
    assert "redirectstandardoutput" in lowered
    assert "redirectstandarderror" in lowered
    assert "$pid" not in lowered


def test_deployment_port_and_entrypoint_are_consistent():
    paths = [
        ROOT / "Dockerfile",
        ROOT / "backend" / "Dockerfile",
        ROOT / "docker-compose.yml",
        ROOT / "docker-compose.production.yml",
    ]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "5001" in content
        if path.name == "Dockerfile":
            assert "backend.wsgi:app" in content
