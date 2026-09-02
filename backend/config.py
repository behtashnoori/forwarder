"""
Single source of truth for backend server and runtime configuration.
Load env from .env / .env.backend in exactly one place.
All runtime code must read host/port/debug/reload ONLY from this module.
"""
from __future__ import annotations

import importlib
import importlib.util
import ipaddress
import os
from pathlib import Path
import platform
import re
from urllib.parse import urlsplit

from sqlalchemy.engine import URL, make_url

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEST_DATABASE_URI = "sqlite:///:memory:"
_TEST_SECRET_KEY = "test-secret-key"
_TEST_JWT_SECRET_KEY = "test-jwt-secret-key-for-pytest-only-32-key-for-pytest-only-32"
_DEV_SECRET_KEY = "dev-only-secret-key-change-before-production"
_DEV_JWT_SECRET_KEY = "dev-only-jwt-secret-key-change-before-production"
_PRODUCTION_ENVS = {"production", "prod"}
_PLACEHOLDER_SECRET_VALUES = {
    "",
    "development-secret-key",
    "dev-only-secret-key-change-before-production",
    "dev-only-jwt-secret-key-change-before-production",
    "test-secret-key",
    "test-jwt-secret-key-for-pytest-only-32",
    _TEST_JWT_SECRET_KEY,
    "your-super-secret-key-change-this-in-production",
}
CANONICAL_PRODUCTION_CORS_ORIGIN = "https://samand.forwarderet.ir"
LEGACY_PRODUCTION_CORS_ORIGIN = "https://server.logisticmarket.ir"
_PLACEHOLDER_ORIGIN_FRAGMENTS = ("yourdomain.com", "example.com", "localhost", "127.0.0.1")
_LOADED_ENV_FILES: tuple[str, ...] = ()
_HOSTNAME_PATTERN = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z",
    re.IGNORECASE,
)


def _load_env_file(path: str) -> bool:
    """Load simple KEY=VALUE env files without requiring optional packages."""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    return True


def load_env_files(
    *,
    project_root: str | None = None,
    backend_dir: str | None = None,
    emit_log: bool = True,
) -> tuple[str, ...]:
    """Load local env files with process env taking precedence.

    Root .env is preferred, backend/.env is supported for developers who run
    commands from the backend directory, and .env.backend remains a legacy
    fallback. Values already present in process env are never overwritten.
    """
    global _LOADED_ENV_FILES

    resolved_project_root = os.path.abspath(project_root or _PROJECT_ROOT)
    resolved_backend_dir = os.path.abspath(backend_dir or _BACKEND_DIR)
    dotenv_spec = importlib.util.find_spec("dotenv")
    env_paths = [
        os.path.join(resolved_project_root, ".env"),
        os.path.join(resolved_backend_dir, ".env"),
        os.path.join(resolved_project_root, ".env.backend"),
    ]
    loaded: list[str] = []
    if dotenv_spec is not None:
        dotenv_module = importlib.import_module("dotenv")
        for env_path in env_paths:
            if os.path.isfile(env_path):
                dotenv_module.load_dotenv(dotenv_path=env_path, override=False)
                loaded.append(env_path)
    else:
        for env_path in env_paths:
            if _load_env_file(env_path):
                loaded.append(env_path)

    loaded_tuple = tuple(loaded)
    if project_root is None and backend_dir is None:
        _LOADED_ENV_FILES = loaded_tuple

    if emit_log:
        if loaded_tuple:
            print("[startup] Loaded env from", ", ".join(loaded_tuple))
        else:
            print("[startup] No .env file found in project root or backend/ - using process env only")
    return loaded_tuple


def get_loaded_env_files() -> tuple[str, ...]:
    """Return env files loaded during backend config import."""
    return _LOADED_ENV_FILES


def get_database_url_diagnostics(database_url: str | None = None) -> dict[str, str | bool | None]:
    """Return safe DATABASE_URL diagnostics without credentials."""
    value = database_url if database_url is not None else os.getenv("DATABASE_URL")
    if not value:
        return {
            "detected": False,
            "dialect": None,
            "driver": None,
            "host": None,
            "database": None,
        }

    parsed = urlsplit(value)
    scheme = parsed.scheme or "unknown"
    dialect, _, driver = scheme.partition("+")
    database = parsed.path.lstrip("/") or None
    if database and "?" in database:
        database = database.split("?", 1)[0]
    return {
        "detected": True,
        "dialect": dialect or scheme,
        "driver": driver or None,
        "host": parsed.hostname,
        "database": database,
    }


def format_database_url_diagnostics(database_url: str | None = None) -> str:
    """Format safe DATABASE_URL diagnostics for startup logs."""
    info = get_database_url_diagnostics(database_url)
    if not info["detected"]:
        return "DATABASE_URL detected=no"
    details = [
        "DATABASE_URL detected=yes",
        f"dialect={info['dialect'] or 'unknown'}",
    ]
    if info["driver"]:
        details.append(f"driver={info['driver']}")
    if info["host"]:
        details.append(f"host={info['host']}")
    if info["database"]:
        details.append(f"database={info['database']}")
    return ", ".join(details)


# UAT is process-environment-only. In all other profiles, retain the existing
# local developer env-file convention.
if (os.getenv("APP_ENV") or os.getenv("ENV") or os.getenv("FLASK_ENV") or "").strip().lower() != "uat":
    load_env_files()


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "1" if default else "0").lower()
    return raw in ("1", "true", "yes")


def _int_env(name: str, default: int) -> int:
    if name == "PORT":
        raw = os.getenv("PORT") or os.getenv("FLASK_RUN_PORT") or str(default)
    else:
        raw = os.getenv(name) or str(default)
    return int(raw)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_runtime_environment(*, testing: bool = False) -> str:
    """Return normalized runtime environment name."""
    if testing:
        return "testing"
    return (os.getenv("APP_ENV") or os.getenv("ENV") or os.getenv("FLASK_ENV") or "development").strip().lower()


def is_production_environment(environment: str | None = None, *, testing: bool = False) -> bool:
    """Return True only for explicit production runtime names."""
    env = (environment or get_runtime_environment(testing=testing)).strip().lower()
    return env in _PRODUCTION_ENVS


def is_development_environment(environment: str | None = None, *, testing: bool = False) -> bool:
    """Return True for non-production, non-testing development-like runtimes."""
    env = (environment or get_runtime_environment(testing=testing)).strip().lower()
    return env in {"development", "dev", "local"}


def resolve_user_data_directory(
    *,
    system: str | None = None,
    environ: dict[str, str] | os._Environ[str] | None = None,
    home: str | os.PathLike[str] | None = None,
) -> Path:
    """Resolve Forwarder's user-local data directory without creating it."""
    runtime_system = (system or platform.system()).lower()
    runtime_environ = os.environ if environ is None else environ
    home_path = Path(home).expanduser() if home is not None else Path.home()

    if runtime_system == "windows":
        local_app_data = runtime_environ.get("LOCALAPPDATA")
        if not local_app_data:
            local_app_data = str(home_path / "AppData" / "Local")
        return Path(local_app_data) / "Forwarder" / "15-forwarder" / "data"
    if runtime_system == "darwin":
        return home_path / "Library" / "Application Support" / "Forwarder" / "15-forwarder"

    xdg_data_home = runtime_environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home).expanduser() if xdg_data_home else home_path / ".local" / "share"
    return base / "forwarder" / "15-forwarder"


def _path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=False))
    except ValueError:
        return False
    return True


def resolve_local_sqlite_path(
    explicit_path: str | os.PathLike[str] | None = None,
    *,
    project_root: str | os.PathLike[str] | None = None,
    system: str | None = None,
    environ: dict[str, str] | os._Environ[str] | None = None,
    home: str | os.PathLike[str] | None = None,
) -> Path:
    """Resolve and validate a local SQLite file path without touching disk."""
    runtime_environ = os.environ if environ is None else environ
    configured_path = explicit_path
    if configured_path is None:
        configured_path = runtime_environ.get("FORWARDER_LOCAL_DB_PATH")

    if configured_path is None:
        candidate = resolve_user_data_directory(
            system=system, environ=runtime_environ, home=home
        ) / "forwarder_dev.db"
    else:
        candidate = Path(configured_path).expanduser()
        if not candidate.is_absolute():
            raise RuntimeError("FORWARDER_LOCAL_DB_PATH must be an absolute path.")

    repository = Path(project_root or _PROJECT_ROOT)
    if _path_is_within(candidate, repository):
        raise RuntimeError("FORWARDER_LOCAL_DB_PATH must be outside the repository.")
    return candidate.resolve(strict=False)


def build_sqlite_database_uri(path: str | os.PathLike[str]) -> str:
    """Build a correctly escaped SQLAlchemy SQLite URL."""
    return str(URL.create("sqlite", database=str(path)))


def get_database_uri(*, testing: bool = False) -> str:
    """Return a database URI with explicit test/local/UAT/production behavior."""
    if testing:
        return os.getenv("TEST_DATABASE_URL") or _TEST_DATABASE_URI

    env = get_runtime_environment(testing=testing)
    database_url = os.getenv("DATABASE_URL")
    if is_production_environment(env):
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when APP_ENV/ENV/FLASK_ENV is production.")
        return database_url

    if database_url:
        if env == "uat" and make_url(database_url).get_backend_name() != "postgresql":
            raise RuntimeError("UAT DATABASE_URL must use PostgreSQL.")
        print("[startup]", format_database_url_diagnostics(database_url))
        return database_url

    if env == "uat":
        raise RuntimeError("DATABASE_URL is required and must use PostgreSQL when APP_ENV is uat.")
    if not is_development_environment(env):
        raise RuntimeError("DATABASE_URL is required outside local development and testing.")

    local_path = resolve_local_sqlite_path()
    print(
        "[startup] DATABASE_URL is not set. For local PostgreSQL, set DATABASE_URL "
        "in the process environment. Falling back to the user-local "
        "development-only SQLite database."
    )
    return str(build_sqlite_database_uri(local_path))


def get_secret_config(*, testing: bool = False) -> tuple[str, str]:
    """Return SECRET_KEY and JWT_SECRET_KEY for the current runtime."""
    if testing:
        return (
            os.getenv("SECRET_KEY") or _TEST_SECRET_KEY,
            os.getenv("JWT_SECRET_KEY") or _TEST_JWT_SECRET_KEY,
        )

    env = get_runtime_environment(testing=testing)
    secret_key = os.getenv("SECRET_KEY")
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")

    if is_production_environment(env):
        _require_non_placeholder_secret("SECRET_KEY", secret_key)
        _require_non_placeholder_secret("JWT_SECRET_KEY", jwt_secret_key)
        return secret_key or "", jwt_secret_key or ""

    if not secret_key:
        print("[startup] SECRET_KEY is not set; using development-only fallback secret.")
        secret_key = _DEV_SECRET_KEY
    if not jwt_secret_key:
        print("[startup] JWT_SECRET_KEY is not set; using development-only fallback JWT secret.")
        jwt_secret_key = _DEV_JWT_SECRET_KEY
    return secret_key, jwt_secret_key


def get_configured_cors_origins() -> list[str]:
    """Return explicit CORS origins with an unambiguous compatibility alias."""
    plural = _split_csv(os.getenv("CORS_ORIGINS"))
    singular = _split_csv(os.getenv("CORS_ORIGIN"))
    if plural and singular and set(plural) != set(singular):
        raise RuntimeError("CORS_ORIGINS and CORS_ORIGIN must not disagree.")
    return plural or singular


def validate_runtime_config(*, testing: bool, database_uri: str, secret_key: str, jwt_secret_key: str) -> None:
    """Fail fast for unsafe production runtime configuration."""
    env = get_runtime_environment(testing=testing)
    if not is_production_environment(env):
        return

    if not database_uri:
        raise RuntimeError("DATABASE_URL is required in production.")
    _require_non_placeholder_secret("SECRET_KEY", secret_key)
    _require_non_placeholder_secret("JWT_SECRET_KEY", jwt_secret_key)
    _validate_production_cors()


def _require_non_placeholder_secret(name: str, value: str | None) -> None:
    normalized = (value or "").strip()
    if not normalized:
        raise RuntimeError(f"{name} is required in production.")
    if normalized in _PLACEHOLDER_SECRET_VALUES:
        raise RuntimeError(f"{name} must be set to a deployment-specific production value.")
    if normalized.startswith("your-") or "change-this" in normalized.lower():
        raise RuntimeError(f"{name} must not use placeholder production values.")


def _validate_production_cors() -> None:
    origins = get_configured_cors_origins()
    allow_all = _bool_env("CORS_ALLOW_ALL_ORIGINS", False)
    if allow_all:
        raise RuntimeError("CORS_ALLOW_ALL_ORIGINS is not allowed in production.")
    if not origins:
        raise RuntimeError("CORS_ORIGINS is required in production.")
    if any(origin == "*" for origin in origins):
        raise RuntimeError("Wildcard CORS origins are not allowed in production.")
    invalid = [origin for origin in origins if _origin_is_placeholder(origin)]
    if invalid:
        raise RuntimeError("Production CORS origins must be real deployment origins, not placeholders or local hosts.")
    if CANONICAL_PRODUCTION_CORS_ORIGIN not in origins:
        raise RuntimeError("The canonical Production CORS origin is required.")
    if LEGACY_PRODUCTION_CORS_ORIGIN in origins:
        raise RuntimeError("The legacy Production CORS origin is not allowed.")


def _origin_is_placeholder(origin: str) -> bool:
    lowered = origin.lower()
    return any(fragment in lowered for fragment in _PLACEHOLDER_ORIGIN_FRAGMENTS)


def resolve_server_host(raw_host: str | None, *, environment: str | None = None) -> str:
    """Return a validated server bind address.

    UAT defaults to IPv4 loopback so a missing host cannot expose the readiness
    server. Other profiles retain the historical wildcard default, including
    production. An explicitly requested ``0.0.0.0`` remains supported.
    """
    runtime_environment = (
        environment if environment is not None else get_runtime_environment()
    ).strip().lower()
    if raw_host is None:
        return "127.0.0.1" if runtime_environment == "uat" else "0.0.0.0"

    host = raw_host.strip().lower()
    if not host:
        raise RuntimeError("HOST/FLASK_RUN_HOST must not be empty.")
    if host == "localhost":
        return "127.0.0.1"

    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not _HOSTNAME_PATTERN.fullmatch(host):
            raise RuntimeError(
                "HOST/FLASK_RUN_HOST must be an IP address or valid hostname."
            ) from None
    return host


# Server settings - single source of truth (default: no reload, fixed port 5001)
# Development and production retain the historical 0.0.0.0 default. UAT is
# loopback-only by default. Explicit loopback values are never widened.
_configured_host = os.getenv("HOST")
if _configured_host is None:
    _configured_host = os.getenv("FLASK_RUN_HOST")
HOST: str = resolve_server_host(_configured_host)
PORT: int = _int_env("PORT", 5001)
DEBUG: bool = _bool_env("FLASK_DEBUG", False)
USE_RELOAD: bool = _bool_env("FLASK_USE_RELOAD", False)

PROJECT_ROOT: str = _PROJECT_ROOT
