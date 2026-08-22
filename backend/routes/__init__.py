"""Application route registration."""
from flask import Flask

from .admin_panel import admin_bp
from .crm import crm_bp
from .customer_gamification import customer_gamification_bp
from .expert_console import expert_console_bp
from .tracking_locations import tracking_locations_bp
from .health import health_bp
from .locations import location_bp, provinces_bp
from .location_admin import location_admin_bp
from .shipment_request import shipment_request_bp
from .monitoring import monitoring_bp
from .user_management import user_management_bp
from .public_tracking import public_tracking_bp
from .site_settings import site_bp, admin_site_bp
from .customs import customs_bp
from .operations import operations_bp
from .operational_execution import operational_execution_bp
from .execution_units import execution_units_bp
from .case_documents import document_bp
from .master_data import master_data_bp
from .cargo import cargo_bp
from .logistics_network import logistics_network_bp
from .project_configuration import project_configuration_bp
from .document_readiness import document_readiness_bp
from .oip import oip_bp
from .economics import economics_bp
from .system import system_bp
from .global_logistics_points import global_logistics_points_bp
from .global_logistics_point_adoptions import global_logistics_point_adoptions_bp


def register_routes(app: Flask) -> None:
    """Register all application blueprints on the given Flask app."""
    app.register_blueprint(health_bp)
    app.register_blueprint(location_bp)
    app.register_blueprint(provinces_bp)
    app.register_blueprint(location_admin_bp)
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
    app.register_blueprint(operations_bp)
    app.register_blueprint(operational_execution_bp)
    app.register_blueprint(execution_units_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(master_data_bp)
    app.register_blueprint(cargo_bp)
    app.register_blueprint(logistics_network_bp)
    app.register_blueprint(project_configuration_bp)
    app.register_blueprint(document_readiness_bp)
    app.register_blueprint(oip_bp)
    app.register_blueprint(economics_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(global_logistics_points_bp)
    app.register_blueprint(global_logistics_point_adoptions_bp)
