"""Backend application factory."""
from __future__ import annotations

import os
import sys
import traceback
from typing import Any, Mapping, MutableMapping

import backend.config  # noqa: F401 - load .env once (single source of truth in backend.config)
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import text

from backend.extensions import db, migrate
from backend.routes import register_routes
from backend.security import security
from backend.app_logging import logger
from backend.cors_config import get_cors_config, log_cors_info, validate_origin

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def create_app(config: Mapping[str, Any] | None = None, *, skip_startup: bool = False) -> Flask:
    """Create and configure the Flask application.

    Parameters
    ----------
    config:
        Optional mapping of configuration values that should override the defaults.
    skip_startup:
        If True, do not run migrations/verify/seed inside create_app (caller will run them once, e.g. run.py).
        Use True in run.py to avoid running startup twice when reloader spawns a child process.
    """

    app = Flask(__name__, instance_relative_config=True)

    # Default configuration makes it easy to run the backend locally while still
    # allowing full override via environment variables or a provided config mapping.
    # In test mode, never fall back to a developer/production DATABASE_URL; tests
    # must use an isolated database unless they explicitly provide another URI.
    is_testing_config = bool(config and config.get("TESTING"))
    default_database_uri = (
        os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
        if is_testing_config
        else os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:bagheri13@127.0.0.1:5432/forwarder_db",
        )
    )
    default_config: MutableMapping[str, Any] = {
        "SQLALCHEMY_DATABASE_URI": default_database_uri,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "CORS_ORIGIN": os.getenv("CORS_ORIGIN", "*"),
        "SLA_HOURS": int(os.getenv("SLA_HOURS", 2)),
    }
    # PORT for health endpoint and startup logs (single source of truth: backend.config)
    import backend.config as _cfg  # noqa: E402
    default_config["PORT"] = _cfg.PORT

    app.config.from_mapping(default_config)
    if config is not None:
        app.config.from_mapping(config)

    # Ensure the instance path exists before any SQLite database is created.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize security
    security.init_app(app)
    
    # Initialize logging
    logger.init_app(app)

    # Configure CORS with dynamic origins
    cors_config = get_cors_config()
    CORS(app, **cors_config)
    print("[startup] CORS configured.")
    log_cors_info()
    
    def _is_cors_origin_allowed(origin: str | None) -> bool:
        """Return True if the given origin is allowed for CORS."""
        if not origin:
            return False
        is_dev = os.getenv('FLASK_ENV', '').lower() in ('development', 'dev') or os.getenv('FLASK_DEBUG', '').lower() in ('true', '1', 'yes')
        allow_any = os.getenv('CORS_ALLOW_ALL_ORIGINS', '').lower() in ('1', 'true', 'yes')
        if is_dev or allow_any:
            return True
        origins_config = cors_config.get('origins')
        if callable(origins_config):
            return origins_config(origin)
        if isinstance(origins_config, list):
            if origin in origins_config:
                return True
            if validate_origin(origin):
                return True
        return False

    def _add_cors_headers_to_response(response):
        """Add CORS headers to a response."""
        origin = request.headers.get('Origin')
        if origin and _is_cors_origin_allowed(origin):
            if 'Access-Control-Allow-Origin' not in response.headers:
                response.headers.add('Access-Control-Allow-Origin', origin)
            if 'Access-Control-Allow-Credentials' not in response.headers:
                response.headers.add('Access-Control-Allow-Credentials', 'true')
            if 'Access-Control-Allow-Methods' not in response.headers:
                response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
            if 'Access-Control-Allow-Headers' not in response.headers:
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token, X-Requested-With, Accept, Origin')
            if 'Access-Control-Max-Age' not in response.headers:
                response.headers.add('Access-Control-Max-Age', '3600')

    # Ensure CORS headers are always added (backup for Flask-CORS)
    @app.after_request
    def add_cors_headers(response):
        """Ensure CORS headers are always present."""
        _add_cors_headers_to_response(response)
        return response

    # Handle OPTIONS requests explicitly so preflight always gets CORS headers
    @app.before_request
    def handle_options():
        """Handle OPTIONS requests for CORS preflight."""
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin')
            # Always respond to OPTIONS with CORS headers when Origin is present
            if origin and _is_cors_origin_allowed(origin):
                from flask import jsonify
                response = jsonify({})
                response.headers.add('Access-Control-Allow-Origin', origin)
                response.headers.add('Access-Control-Allow-Credentials', 'true')
                response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token, X-Requested-With, Accept, Origin')
                response.headers.add('Access-Control-Max-Age', '3600')
                return response

    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
            print("[startup] Database connection OK.")
        except Exception as exc:  # pragma: no cover - startup diagnostic
            print("[startup] Database connection failed:", exc)
            traceback.print_exc()
            sys.exit(1)

    # Test apps should be self-contained and must not depend on external schema
    # state, migrations, or developer databases. This is test-only and does not
    # affect production startup behavior.
    if app.config.get("TESTING"):
        with app.app_context():
            db.create_all()
    # When not testing and not skip_startup: run migrations, verify tables, seed (gunicorn/wsgi; run.py runs them itself to avoid double run with reloader)
    elif not skip_startup:
        from backend.startup import run_migrations, verify_critical_tables
        from backend.startup_seed import run_startup_seed
        run_migrations(app)
        verify_critical_tables(app)
        run_startup_seed(app)

    # Register all HTTP routes with the application.
    try:
        register_routes(app)
        print("[startup] Routes registered.")
    except Exception as exc:
        print("[startup] Route registration failed:", exc)
        traceback.print_exc()
        sys.exit(1)

    # Global error handler: no silent 500; log full trace and return JSON (with details in dev)
    _MAX_BODY_LOG = 2000
    _is_dev = os.getenv("FLASK_ENV", "").lower() in ("development", "dev") or os.getenv("FLASK_DEBUG", "").lower() in ("true", "1", "yes")

    def _make_error_response(tb: str, path: str, method: str, body: str, err: Exception | None = None):
        app.logger.error(
            "Unhandled 500: path=%s method=%s\nTraceback:\n%s\nRequest body (safe): %s",
            path,
            method,
            tb,
            body or "<empty>",
        )
        payload = {"error": "Internal server error", "path": path}
        if _is_dev:
            payload["details"] = (str(err) if err else "") + "\n" + tb
        else:
            payload["message"] = "An unexpected error occurred."
        return jsonify(payload), 500

    @app.errorhandler(500)
    def _handle_500(err):
        tb = traceback.format_exc()
        path = request.path if request else "<no request>"
        method = request.method if request else "<no request>"
        body = ""
        if request and request.get_data:
            try:
                raw = request.get_data(as_text=True)
                if raw and len(raw) <= _MAX_BODY_LOG:
                    body = raw
                elif raw:
                    body = raw[: _MAX_BODY_LOG] + "... (truncated)"
            except Exception:
                body = "<non-text or unavailable>"
        return _make_error_response(tb, path, method, body or "<empty>", getattr(err, "original_exception", err))

    @app.errorhandler(Exception)
    def _handle_exception(err):
        from werkzeug.exceptions import HTTPException

        if isinstance(err, HTTPException) and err.code != 500:
            return jsonify(error=getattr(err, "description", str(err))), err.code
        tb = traceback.format_exc()
        path = request.path if request else "<no request>"
        method = request.method if request else "<no request>"
        body = ""
        if request and request.get_data:
            try:
                raw = request.get_data(as_text=True)
                if raw and len(raw) <= _MAX_BODY_LOG:
                    body = raw
                elif raw:
                    body = raw[: _MAX_BODY_LOG] + "... (truncated)"
            except Exception:
                body = "<non-text or unavailable>"
        return _make_error_response(tb, path, method, body or "<empty>", err)

    @app.shell_context_processor
    def _make_shell_context() -> dict[str, Any]:
        """Expose database models in the interactive Flask shell."""

        from backend import models  # noqa: WPS433 (import for side effects)

        return {"db": db, **{name: getattr(models, name) for name in models.__all__}}

    return app


__all__ = ["create_app"]
