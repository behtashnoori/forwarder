"""Backend application factory."""
from __future__ import annotations

import os
import re
from typing import Any, Mapping, MutableMapping

from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS
from sqlalchemy import text

from backend.extensions import db, migrate
from backend.routes import register_routes
from backend.security import security
from backend.app_logging import logger
from backend.cors_config import get_cors_config, log_cors_info, is_ip_based_origin

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application.

    Parameters
    ----------
    config:
        Optional mapping of configuration values that should override the defaults.
    """

    app = Flask(__name__, instance_relative_config=True)

    # Default configuration makes it easy to run the backend locally while still
    # allowing full override via environment variables or a provided config mapping.
    default_config: MutableMapping[str, Any] = {
        "SQLALCHEMY_DATABASE_URI": os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:bagheri13@127.0.0.1:5432/forwarder_db",
        ),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "CORS_ORIGIN": os.getenv("CORS_ORIGIN", "*"),
        "SLA_HOURS": int(os.getenv("SLA_HOURS", 2)),
    }

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
    
    # Log CORS configuration for debugging
    log_cors_info()
    
    def _is_cors_origin_allowed(origin: str | None) -> bool:
        """Return True if the given origin is allowed for CORS."""
        if not origin:
            return False
        is_dev = os.getenv('FLASK_ENV', '').lower() in ('development', 'dev') or os.getenv('FLASK_DEBUG', '').lower() in ('true', '1', 'yes')
        allow_any = os.getenv('CORS_ALLOW_ALL_ORIGINS', '').lower() in ('1', 'true', 'yes')
        # Allow IP-based origins (e.g. http://130.185.77.25:8080) by default for deployment on VPS
        allow_ip_origins = os.getenv('CORS_ALLOW_IP_ORIGINS', '1').lower() in ('1', 'true', 'yes')
        if is_dev or allow_any:
            return True
        if allow_ip_origins and is_ip_based_origin(origin):
            return True
        origins_config = cors_config.get('origins')
        if callable(origins_config):
            return origins_config(origin)
        if isinstance(origins_config, list):
            return origin in origins_config
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
            print("Database connection successful.")
        except Exception as exc:  # pragma: no cover - startup diagnostic
            print("Database connection failed:", exc)

    # Register all HTTP routes with the application.
    register_routes(app)

    @app.shell_context_processor
    def _make_shell_context() -> dict[str, Any]:
        """Expose database models in the interactive Flask shell."""

        from backend import models  # noqa: WPS433 (import for side effects)

        return {"db": db, **{name: getattr(models, name) for name in models.__all__}}

    return app


__all__ = ["create_app"]
