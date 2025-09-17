"""Application route registration."""
from flask import Flask

from .admin_panel import admin_bp
from .locations import location_bp
from .shipment_request import shipment_request_bp


def register_routes(app: Flask) -> None:
    """Register all application blueprints on the given Flask app."""
    app.register_blueprint(location_bp)
    app.register_blueprint(shipment_request_bp)
    app.register_blueprint(admin_bp)
