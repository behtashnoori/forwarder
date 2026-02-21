"""
Single source of truth for backend server configuration.
Load env from .env / .env.backend in exactly one place.
All runtime code must read host/port/debug/reload ONLY from this module.
"""
from __future__ import annotations

import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env() -> None:
    """Load .env and optionally .env.backend once. Idempotent. override=True so .env (PostgreSQL) always wins over stale shell env."""
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


# Server settings - single source of truth (default: no reload, fixed port 8000)
# Bind to 0.0.0.0 so the server is accessible from network; do not use 127.0.0.1
_raw_host = (os.getenv("HOST") or os.getenv("FLASK_RUN_HOST") or "0.0.0.0").strip().lower()
HOST: str = "0.0.0.0" if _raw_host in ("127.0.0.1", "localhost", "") else _raw_host
PORT: int = _int_env("PORT", 8000)
DEBUG: bool = _bool_env("FLASK_DEBUG", False)
USE_RELOAD: bool = _bool_env("FLASK_USE_RELOAD", False)

PROJECT_ROOT: str = _PROJECT_ROOT
