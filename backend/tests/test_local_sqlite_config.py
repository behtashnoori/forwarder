"""Local SQLite resolution, safety, precedence, and side-effect tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from backend import config as runtime_config


DATABASE_ENV_KEYS = (
    "APP_ENV", "ENV", "FLASK_ENV", "DATABASE_URL", "TEST_DATABASE_URL",
    "FORWARDER_LOCAL_DB_PATH", "XDG_DATA_HOME",
)


def _clear_database_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in DATABASE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_explicit_database_url_precedes_explicit_local_path(monkeypatch, tmp_path):
    _clear_database_env(monkeypatch)
    url = "postgresql://user:password@127.0.0.1/forwarder"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FORWARDER_LOCAL_DB_PATH", str(tmp_path / "local.db"))
    assert runtime_config.get_database_uri() == url


def test_explicit_local_path_precedes_default(monkeypatch, tmp_path):
    _clear_database_env(monkeypatch)
    path = tmp_path / "Unicode داده" / "forwarder dev.db"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FORWARDER_LOCAL_DB_PATH", str(path))
    assert Path(make_url(runtime_config.get_database_uri()).database) == path


def test_testing_is_isolated_from_runtime_database_settings(monkeypatch, tmp_path):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@127.0.0.1/live")
    monkeypatch.setenv("FORWARDER_LOCAL_DB_PATH", str(tmp_path / "local.db"))
    assert runtime_config.get_database_uri(testing=True) == "sqlite:///:memory:"


def test_production_without_url_fails_closed(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        runtime_config.get_database_uri()


def test_uat_without_url_fails_closed(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "uat")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        runtime_config.get_database_uri()


def test_uat_rejects_sqlite_and_accepts_postgresql(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "uat")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        runtime_config.get_database_uri()
    url = "postgresql://user:password@127.0.0.1/forwarder_phase1b_uat"
    monkeypatch.setenv("DATABASE_URL", url)
    assert runtime_config.get_database_uri() == url


@pytest.mark.parametrize("relative", ["forwarder.db", "data/forwarder.db"])
def test_relative_local_path_is_rejected(relative, tmp_path):
    with pytest.raises(RuntimeError, match="absolute"):
        runtime_config.resolve_local_sqlite_path(relative, project_root=tmp_path)


@pytest.mark.parametrize("suffix", ["forwarder.db", "instance/forwarder.db"])
def test_repository_local_path_is_rejected(suffix, tmp_path):
    with pytest.raises(RuntimeError, match="outside the repository"):
        runtime_config.resolve_local_sqlite_path(
            tmp_path / suffix, project_root=tmp_path
        )


def test_external_absolute_path_is_accepted(tmp_path):
    repository = tmp_path / "repo"
    external = tmp_path / "external" / "forwarder.db"
    assert runtime_config.resolve_local_sqlite_path(
        external, project_root=repository
    ) == external


def test_windows_local_app_data_convention():
    result = runtime_config.resolve_user_data_directory(
        system="Windows",
        environ={"LOCALAPPDATA": r"C:\Users\Example\AppData\Local"},
        home=r"C:\Users\Example",
    )
    assert str(result) == str(
        Path(r"C:\Users\Example\AppData\Local") / "Forwarder" / "15-forwarder" / "data"
    )


def test_linux_xdg_and_fallback_conventions():
    assert runtime_config.resolve_user_data_directory(
        system="Linux", environ={"XDG_DATA_HOME": "/data/user"}, home="/home/user"
    ) == Path("/data/user/forwarder/15-forwarder")
    assert runtime_config.resolve_user_data_directory(
        system="Linux", environ={}, home="/home/user"
    ) == Path("/home/user/.local/share/forwarder/15-forwarder")


def test_macos_convention():
    assert runtime_config.resolve_user_data_directory(
        system="Darwin", environ={}, home="/Users/example"
    ) == Path("/Users/example/Library/Application Support/Forwarder/15-forwarder")


def test_resolution_does_not_create_directory_or_database(monkeypatch, tmp_path):
    _clear_database_env(monkeypatch)
    target = tmp_path / "missing parent" / "forwarder.db"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FORWARDER_LOCAL_DB_PATH", str(target))
    runtime_config.get_database_uri()
    assert not target.parent.exists()
    assert not target.exists()
