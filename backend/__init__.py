"""Backend application factory."""
from __future__ import annotations

import os
import sys
import traceback
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping, MutableMapping

import backend.config  # noqa: F401 - load .env once (single source of truth in backend.config)
from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.extensions import db, migrate
from backend.routes import register_routes
from backend.security import security
from backend.app_logging import logger
from backend.cors_config import get_cors_config, is_cors_origin_allowed, log_cors_info

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def create_app(config: Mapping[str, Any] | None = None, *, skip_startup: bool = False) -> Flask:
    """Create and configure the Flask application.

    Parameters
    ----------
    config:
        Optional mapping of configuration values that should override the defaults.
    skip_startup:
        Deprecated compatibility argument. Application construction never runs
        migrations, seeds, or database readiness checks. Runtime policy belongs
        to ``backend.runtime`` and migrations require an explicit CLI command.
    """

    app = Flask(__name__, instance_relative_config=True)

    # Default configuration keeps test/dev/prod behavior explicit. Tests never
    # fall back to developer/production DATABASE_URL, while production fails fast
    # unless sensitive runtime configuration is supplied by the environment.
    is_testing_config = bool(config and config.get("TESTING"))

    # PORT for health endpoint and startup logs (single source of truth: backend.config)
    import backend.config as _cfg  # noqa: E402

    database_uri = _cfg.get_database_uri(testing=is_testing_config)
    secret_key, jwt_secret_key = _cfg.get_secret_config(testing=is_testing_config)
    default_config: MutableMapping[str, Any] = {
        "SQLALCHEMY_DATABASE_URI": database_uri,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": secret_key,
        "JWT_SECRET_KEY": jwt_secret_key,
        "CORS_ORIGIN": os.getenv("CORS_ORIGIN", ""),
        "SLA_HOURS": int(os.getenv("SLA_HOURS", 2)),
        "PORT": _cfg.PORT,
        "APP_ENV": _cfg.get_runtime_environment(testing=is_testing_config),
        "AUTO_MIGRATE_ON_STARTUP": False,
        "JWT_ACCESS_TOKEN_EXPIRES": timedelta(
            seconds=int(os.getenv("ACCESS_TOKEN_LIFETIME_SECONDS", "3600"))
        ),
        "JWT_REFRESH_TOKEN_EXPIRES": timedelta(
            seconds=int(os.getenv("REFRESH_IDLE_LIFETIME_SECONDS", "2592000"))
        ),
        "SESSION_ABSOLUTE_LIFETIME": timedelta(
            seconds=int(os.getenv("SESSION_ABSOLUTE_LIFETIME_SECONDS", "7776000"))
        ),
        "JWT_CLOCK_SKEW_SECONDS": int(os.getenv("CLOCK_SKEW_SECONDS", "60")),
        "DOCUMENT_STORAGE_ROOT": os.getenv("DOCUMENT_STORAGE_ROOT"),
    }

    app.config.from_mapping(default_config)
    if config is not None:
        app.config.from_mapping(config)

    from backend.services.document_storage_service import validate_storage_root
    production = str(app.config["APP_ENV"]).lower() in {"production", "prod"}
    if not app.config.get("DOCUMENT_STORAGE_ROOT") and not production:
        app.config["DOCUMENT_STORAGE_ROOT"] = str(Path(app.instance_path) / "private-documents")
    app.config["DOCUMENT_STORAGE_ROOT"] = str(validate_storage_root(
        app.config.get("DOCUMENT_STORAGE_ROOT"),
        production=production,
        repository_root=PROJECT_ROOT,
    ))

    _cfg.validate_runtime_config(
        testing=bool(app.config.get("TESTING")),
        database_uri=app.config["SQLALCHEMY_DATABASE_URI"],
        secret_key=app.config["SECRET_KEY"],
        jwt_secret_key=app.config["JWT_SECRET_KEY"],
    )

    # File-backed SQLite needs its parent at application startup. Configuration
    # import and URI resolution remain side-effect free.
    from sqlalchemy.engine import make_url

    configured_url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if configured_url.get_backend_name() == "sqlite" and configured_url.database not in {None, "", ":memory:"}:
        Path(configured_url.database).parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize security
    security.init_app(app)
    
    # Initialize logging
    logger.init_app(app)

    # Configure CORS with dynamic origins
    cors_config = get_cors_config(testing=bool(app.config.get("TESTING")))
    CORS(app, **cors_config)
    print("[startup] CORS configured.")
    log_cors_info(testing=bool(app.config.get("TESTING")))
    
    def _is_cors_origin_allowed(origin: str | None) -> bool:
        """Return True if the given origin is allowed for CORS."""
        return is_cors_origin_allowed(
            origin,
            testing=bool(app.config.get("TESTING")),
            cors_config=cors_config,
        )

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

    # Test apps should be self-contained and must not depend on external schema
    # state, migrations, or developer databases. This is test-only and does not
    # affect production startup behavior.
    if app.config.get("TESTING") and not skip_startup:
        with app.app_context():
            db.create_all()

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
