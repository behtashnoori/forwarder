"""
Single source of truth for backend server and runtime configuration.
Load env from .env / .env.backend in exactly one place.
All runtime code must read host/port/debug/reload ONLY from this module.
"""
from __future__ import annotations

import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEV_DATABASE_URI = "sqlite:///forwarder_dev.db"
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
_PLACEHOLDER_ORIGIN_FRAGMENTS = ("yourdomain.com", "example.com", "localhost", "127.0.0.1")


def _load_env() -> None:
    """Load .env and optionally .env.backend once."""
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"), override=True)
    load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env.backend"), override=True)
    if os.path.isfile(os.path.join(_PROJECT_ROOT, ".env")):
        print("[startup] Loaded env from", os.path.join(_PROJECT_ROOT, ".env"))
    else:
        print("[startup] No .env file - using process env only")


# Load once at import so any code using os.getenv (e.g. create_app) sees env
_load_env()


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


def get_database_uri(*, testing: bool = False) -> str:
    """Return a database URI with explicit test/dev/prod behavior."""
    if testing:
        return os.getenv("TEST_DATABASE_URL") or _TEST_DATABASE_URI

    env = get_runtime_environment(testing=testing)
    database_url = os.getenv("DATABASE_URL")
    if is_production_environment(env):
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when APP_ENV/ENV/FLASK_ENV is production.")
        return database_url

    if database_url:
        return database_url

    print("[startup] DATABASE_URL is not set; using development-only local SQLite database.")
    return os.getenv("DEV_DATABASE_URL") or _DEV_DATABASE_URI


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
    """Return explicit CORS origins from current environment variables."""
    return _split_csv(os.getenv("CORS_ORIGINS") or os.getenv("CORS_ORIGIN"))


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


def _origin_is_placeholder(origin: str) -> bool:
    lowered = origin.lower()
    return any(fragment in lowered for fragment in _PLACEHOLDER_ORIGIN_FRAGMENTS)


# Server settings - single source of truth (default: no reload, fixed port 8000)
# Bind to 0.0.0.0 so the server is accessible from network; do not use 127.0.0.1
_raw_host = (os.getenv("HOST") or os.getenv("FLASK_RUN_HOST") or "0.0.0.0").strip().lower()
HOST: str = "0.0.0.0" if _raw_host in ("127.0.0.1", "localhost", "") else _raw_host
PORT: int = _int_env("PORT", 8000)
DEBUG: bool = _bool_env("FLASK_DEBUG", False)
USE_RELOAD: bool = _bool_env("FLASK_USE_RELOAD", False)

PROJECT_ROOT: str = _PROJECT_ROOT
