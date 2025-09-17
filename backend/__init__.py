"""Backend application factory."""
from __future__ import annotations

import os
import re
from typing import Any, Mapping, MutableMapping

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from sqlalchemy import text

from backend.extensions import db
from backend.routes import register_routes

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
            "sqlite:///instance/forwarder.sqlite3",
        ),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "CORS_ORIGIN": os.getenv("CORS_ORIGIN", "http://localhost"),
        "SLA_HOURS": int(os.getenv("SLA_HOURS", 2)),
    }

    app.config.from_mapping(default_config)
    if config is not None:
        app.config.from_mapping(config)

    # Ensure the instance path exists before any SQLite database is created.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX")
    if cors_origin_regex:
        compiled_origin = re.compile(cors_origin_regex)
        CORS(app, resources={r"/api/*": {"origins": compiled_origin}})
    else:
        cors_origin = app.config.get("CORS_ORIGIN") or "*"
        CORS(app, resources={r"/api/*": {"origins": cors_origin}})

    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
            print("✅ Database connection successful.")
        except Exception as exc:  # pragma: no cover - startup diagnostic
            print("❌ Database connection failed:", exc)

    # Register all HTTP routes with the application.
    register_routes(app)

    @app.shell_context_processor
    def _make_shell_context() -> dict[str, Any]:
        """Expose database models in the interactive Flask shell."""

        from backend import models  # noqa: WPS433 (import for side effects)

        return {"db": db, **{name: getattr(models, name) for name in models.__all__}}

    return app


__all__ = ["create_app"]
