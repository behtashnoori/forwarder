"""Backend application factory."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from flask import Flask

from backend.extensions import db
from backend.routes import register_routes


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
            # Store the SQLite database in the Flask instance folder by default.
            f"sqlite:///{Path(app.instance_path) / 'forwarder.db'}",
        ),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    }

    app.config.from_mapping(default_config)
    if config is not None:
        app.config.from_mapping(config)

    # Ensure the instance path exists before any SQLite database is created.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    # Register all HTTP routes with the application.
    register_routes(app)

    @app.shell_context_processor
    def _make_shell_context() -> dict[str, Any]:
        """Expose database models in the interactive Flask shell."""

        from backend import models  # noqa: WPS433 (import for side effects)

        return {"db": db, **{name: getattr(models, name) for name in models.__all__}}

    return app


__all__ = ["create_app"]
