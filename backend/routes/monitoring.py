"""Monitoring and analytics API routes."""
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

from backend.auth import admin_required
from backend.security import require_role
from backend.services import alert_service, monitoring_service

monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/api/monitoring")


@monitoring_bp.get("/health")
def get_health_status():
    """Get system health status."""
    try:
        health_status = monitoring_service.get_health_status()
        return jsonify(health_status)
    except Exception as e:
        current_app.logger.error(f"Health check error: {e}")
        return jsonify({"error": "Failed to get health status"}), 500


@monitoring_bp.get("/metrics")
@require_role("supervisor")
def get_system_metrics():
    """Get system metrics (requires authentication)."""
    try:
        metrics = monitoring_service.get_system_metrics()
        return jsonify(metrics)
    except Exception as e:
        current_app.logger.error(f"Metrics error: {e}")
        return jsonify({"error": "Failed to get system metrics"}), 500


@monitoring_bp.get("/database")
@require_role("supervisor")
def get_database_metrics():
    """Get database performance metrics."""
    try:
        db_metrics = monitoring_service.get_database_metrics()
        return jsonify(db_metrics)
    except Exception as e:
        current_app.logger.error(f"Database metrics error: {e}")
        return jsonify({"error": "Failed to get database metrics"}), 500


@monitoring_bp.get("/business")
@require_role("supervisor")
def get_business_metrics():
    """Get business metrics."""
    try:
        business_metrics = monitoring_service.get_business_metrics()
        return jsonify(business_metrics)
    except Exception as e:
        current_app.logger.error(f"Business metrics error: {e}")
        return jsonify({"error": "Failed to get business metrics"}), 500


@monitoring_bp.get("/analytics/customers")
@require_role("supervisor")
def get_customer_analytics():
    """Get customer analytics."""
    try:
        days = request.args.get("days", 30, type=int)
        analytics = monitoring_service.get_customer_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Customer analytics error: {e}")
        return jsonify({"error": "Failed to get customer analytics"}), 500


@monitoring_bp.get("/analytics/sales")
@require_role("supervisor")
def get_sales_analytics():
    """Get sales analytics."""
    try:
        days = request.args.get("days", 30, type=int)
        analytics = monitoring_service.get_sales_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Sales analytics error: {e}")
        return jsonify({"error": "Failed to get sales analytics"}), 500


@monitoring_bp.get("/analytics/performance")
@require_role("supervisor")
def get_performance_analytics():
    """Get performance analytics."""
    try:
        days = request.args.get("days", 30, type=int)
        analytics = monitoring_service.get_performance_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Performance analytics error: {e}")
        return jsonify({"error": "Failed to get performance analytics"}), 500


@monitoring_bp.get("/dashboard")
@require_role("supervisor")
def get_monitoring_dashboard():
    """Get comprehensive monitoring dashboard data."""
    try:
        dashboard_data = monitoring_service.get_dashboard_summary()
        return jsonify(dashboard_data)

    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}")
        return jsonify({"error": "Failed to get dashboard data"}), 500


@monitoring_bp.get("/alerts")
@require_role("supervisor")
def get_system_alerts():
    """Get system alerts and warnings."""
    try:
        alerts = alert_service.list_alerts()
        return jsonify(alerts)

    except Exception as e:
        current_app.logger.error(f"Alerts error: {e}")
        return jsonify({"error": "Failed to get system alerts"}), 500


@monitoring_bp.post("/alerts/acknowledge")
@require_role("supervisor")
def acknowledge_alert():
    """Acknowledge a system alert."""
    try:
        data = request.get_json()
        alert_id = data.get("alert_id")

        if not alert_id:
            return jsonify({"error": "Alert ID is required"}), 400

        acknowledgment = alert_service.acknowledge_alert(alert_id)
        return jsonify(acknowledgment)

    except Exception as e:
        current_app.logger.error(f"Alert acknowledgment error: {e}")
        return jsonify({"error": "Failed to acknowledge alert"}), 500


@monitoring_bp.get("/logs")
@admin_required
def get_system_logs():
    """Get system logs (admin only)."""
    try:
        log_type = request.args.get("type", "all")
        limit = min(request.args.get("limit", 100, type=int), 1000)

        logs = monitoring_service.get_system_logs(log_type, limit)
        if logs is None:
            return jsonify({"error": "Invalid log type"}), 400
        return jsonify(logs)

    except Exception as e:
        current_app.logger.error(f"Logs error: {e}")
        return jsonify({"error": "Failed to get system logs"}), 500


@monitoring_bp.get("/ping")
def ping():
    """Health check endpoint for monitoring."""
    return jsonify({
        "message": "Monitoring API is running",
        "timestamp": datetime.utcnow().isoformat()
    })
