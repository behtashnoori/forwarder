"""Application route registration."""
from flask import Flask

from .admin_panel import admin_bp
from .expert_console import expert_console_bp
from .health import health_bp
from .locations import location_bp
from .shipment_request import shipment_request_bp


def register_routes(app: Flask) -> None:
    """Register all application blueprints on the given Flask app."""
    app.register_blueprint(health_bp)
    app.register_blueprint(location_bp)
    app.register_blueprint(shipment_request_bp)
    app.register_blueprint(expert_console_bp)
    app.register_blueprint(admin_bp)