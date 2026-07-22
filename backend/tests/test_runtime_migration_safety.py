"""Regression tests for explicit migration and non-mutating startup policy."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from backend import create_app
from backend.migration_runtime import (
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


def test_alembic_config_is_absolute_and_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = alembic_config("sqlite:///:memory:")
    assert Path(cfg.get_main_option("script_location")).is_absolute()
    assert Path(cfg.get_main_option("script_location")).name == "migrations"


def test_alembic_config_accepts_percent_encoded_credentials():
    cfg = alembic_config("postgresql://user:p%40ss@example.invalid/db")
    assert cfg.get_main_option("sqlalchemy.url") == (
        "postgresql://user:p%40ss@example.invalid/db"
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
    monkeypatch, environment
):
    import backend.runtime as runtime

    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": environment,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
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


def _cleanup_migration_module():
    path = (
        ROOT
        / "backend"
        / "migrations"
        / "versions"
        / "20260729_deduplicate_foreign_keys.py"
    )
    spec = importlib.util.spec_from_file_location("fk_cleanup_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_duplicate_fk_cleanup_prefers_explicit_project_name():
    migration = _cleanup_migration_module()
    common = {
        "constrained_columns": ["customer_id"],
        "referred_schema": None,
        "referred_table": "customer",
        "referred_columns": ["id"],
    }
    constraints = [
        {**common, "name": "customer_contact_customer_id_fkey"},
        {**common, "name": "fk_customer_contact_customer_id"},
        {
            "name": "fk_other",
            "constrained_columns": ["other_id"],
            "referred_schema": None,
            "referred_table": "other",
            "referred_columns": ["id"],
        },
    ]
    assert migration.duplicate_constraint_names(constraints) == [
        "customer_contact_customer_id_fkey"
    ]


def test_fk_cleanup_does_not_merge_different_delete_semantics():
    migration = _cleanup_migration_module()
    common = {
        "constrained_columns": ["customer_id"],
        "referred_schema": None,
        "referred_table": "customer",
        "referred_columns": ["id"],
    }
    constraints = [
        {**common, "name": "fk_customer_restrict", "options": {"ondelete": "RESTRICT"}},
        {**common, "name": "fk_customer_cascade", "options": {"ondelete": "CASCADE"}},
    ]
    assert migration.duplicate_constraint_names(constraints) == []
