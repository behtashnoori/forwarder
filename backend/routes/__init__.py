"""Application route registration."""
from flask import Flask

from .admin_panel import admin_bp
from .crm import crm_bp
from .customer_gamification import customer_gamification_bp
from .expert_console import expert_console_bp
from .tracking_locations import tracking_locations_bp
from .health import health_bp
from .locations import location_bp, provinces_bp
from .shipment_request import shipment_request_bp
from .monitoring import monitoring_bp
from .user_management import user_management_bp
from .public_tracking import public_tracking_bp
from .site_settings import site_bp, admin_site_bp
from .customs import customs_bp


def register_routes(app: Flask) -> None:
    """Register all application blueprints on the given Flask app."""
    app.register_blueprint(health_bp)
    app.register_blueprint(location_bp)
    app.register_blueprint(provinces_bp)
    app.register_blueprint(shipment_request_bp)
    app.register_blueprint(expert_console_bp)
    app.register_blueprint(tracking_locations_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(customer_gamification_bp)
    app.register_blueprint(user_management_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_tracking_bp)
    app.register_blueprint(site_bp)
    app.register_blueprint(admin_site_bp)
    app.register_blueprint(customs_bp)
