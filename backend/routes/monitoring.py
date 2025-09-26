"""Monitoring and analytics API routes."""
from datetime import datetime, timedelta
from typing import Dict, Any

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError

from backend.monitoring import system_monitor, analytics_engine
from backend.auth import require_auth, admin_required
from backend.security import validate_input

monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/api/monitoring")


@monitoring_bp.get("/health")
def get_health_status():
    """Get system health status."""
    try:
        health_status = system_monitor.get_health_status()
        return jsonify(health_status)
    except Exception as e:
        current_app.logger.error(f"Health check error: {e}")
        return jsonify({"error": "Failed to get health status"}), 500


@monitoring_bp.get("/metrics")
@require_auth
def get_system_metrics():
    """Get system metrics (requires authentication)."""
    try:
        metrics = system_monitor.get_system_metrics()
        return jsonify(metrics)
    except Exception as e:
        current_app.logger.error(f"Metrics error: {e}")
        return jsonify({"error": "Failed to get system metrics"}), 500


@monitoring_bp.get("/database")
@require_auth
def get_database_metrics():
    """Get database performance metrics."""
    try:
        db_metrics = system_monitor.get_database_metrics()
        return jsonify(db_metrics)
    except Exception as e:
        current_app.logger.error(f"Database metrics error: {e}")
        return jsonify({"error": "Failed to get database metrics"}), 500


@monitoring_bp.get("/business")
@require_auth
def get_business_metrics():
    """Get business metrics."""
    try:
        business_metrics = system_monitor.get_business_metrics()
        return jsonify(business_metrics)
    except Exception as e:
        current_app.logger.error(f"Business metrics error: {e}")
        return jsonify({"error": "Failed to get business metrics"}), 500


@monitoring_bp.get("/analytics/customers")
@require_auth
def get_customer_analytics():
    """Get customer analytics."""
    try:
        days = request.args.get("days", 30, type=int)
        analytics = analytics_engine.get_customer_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Customer analytics error: {e}")
        return jsonify({"error": "Failed to get customer analytics"}), 500


@monitoring_bp.get("/analytics/sales")
@require_auth
def get_sales_analytics():
    """Get sales analytics."""
    try:
        days = request.args.get("days", 30, type=int)
        analytics = analytics_engine.get_sales_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Sales analytics error: {e}")
        return jsonify({"error": "Failed to get sales analytics"}), 500


@monitoring_bp.get("/analytics/performance")
@require_auth
def get_performance_analytics():
    """Get performance analytics."""
    try:
        days = request.args.get("days", 30, type=int)
        analytics = analytics_engine.get_performance_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Performance analytics error: {e}")
        return jsonify({"error": "Failed to get performance analytics"}), 500


@monitoring_bp.get("/dashboard")
@require_auth
def get_monitoring_dashboard():
    """Get comprehensive monitoring dashboard data."""
    try:
        # Get all metrics
        system_metrics = system_monitor.get_system_metrics()
        db_metrics = system_monitor.get_database_metrics()
        business_metrics = system_monitor.get_business_metrics()
        health_status = system_monitor.get_health_status()
        
        # Get analytics
        customer_analytics = analytics_engine.get_customer_analytics(30)
        sales_analytics = analytics_engine.get_sales_analytics(30)
        performance_analytics = analytics_engine.get_performance_analytics(30)
        
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "health": health_status,
            "system": system_metrics,
            "database": db_metrics,
            "business": business_metrics,
            "analytics": {
                "customers": customer_analytics,
                "sales": sales_analytics,
                "performance": performance_analytics
            }
        }
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}")
        return jsonify({"error": "Failed to get dashboard data"}), 500


@monitoring_bp.get("/alerts")
@require_auth
def get_system_alerts():
    """Get system alerts and warnings."""
    try:
        alerts = []
        
        # Get system metrics
        metrics = system_monitor.get_system_metrics()
        
        # Check memory usage
        memory_percent = metrics['system']['memory']['percent']
        if memory_percent > 90:
            alerts.append({
                "type": "critical",
                "category": "memory",
                "message": f"Memory usage is critically high: {memory_percent:.1f}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        elif memory_percent > 80:
            alerts.append({
                "type": "warning",
                "category": "memory",
                "message": f"Memory usage is high: {memory_percent:.1f}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check CPU usage
        cpu_percent = metrics['system']['cpu_percent']
        if cpu_percent > 90:
            alerts.append({
                "type": "critical",
                "category": "cpu",
                "message": f"CPU usage is critically high: {cpu_percent:.1f}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        elif cpu_percent > 80:
            alerts.append({
                "type": "warning",
                "category": "cpu",
                "message": f"CPU usage is high: {cpu_percent:.1f}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check error rate
        total_requests = metrics['application']['total_requests']
        total_errors = metrics['application']['total_errors']
        
        if total_requests > 0:
            error_rate = (total_errors / total_requests) * 100
            if error_rate > 10:
                alerts.append({
                    "type": "critical",
                    "category": "errors",
                    "message": f"Error rate is critically high: {error_rate:.1f}%",
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif error_rate > 5:
                alerts.append({
                    "type": "warning",
                    "category": "errors",
                    "message": f"Error rate is high: {error_rate:.1f}%",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Check response time
        avg_response_time = metrics['application']['avg_response_time']
        if avg_response_time > 5.0:  # 5 seconds
            alerts.append({
                "type": "warning",
                "category": "performance",
                "message": f"Average response time is slow: {avg_response_time:.2f}s",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return jsonify({
            "alerts": alerts,
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a['type'] == 'critical']),
            "warning_alerts": len([a for a in alerts if a['type'] == 'warning'])
        })
        
    except Exception as e:
        current_app.logger.error(f"Alerts error: {e}")
        return jsonify({"error": "Failed to get system alerts"}), 500


@monitoring_bp.post("/alerts/acknowledge")
@require_auth
def acknowledge_alert():
    """Acknowledge a system alert."""
    try:
        data = request.get_json()
        alert_id = data.get("alert_id")
        
        if not alert_id:
            return jsonify({"error": "Alert ID is required"}), 400
        
        # In a real implementation, you would store acknowledged alerts
        # For now, just return success
        return jsonify({
            "message": "Alert acknowledged",
            "alert_id": alert_id,
            "acknowledged_at": datetime.utcnow().isoformat()
        })
        
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
        
        # This would read from actual log files
        # For now, return mock data
        logs = {
            "application": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "Application started",
                    "module": "app"
                }
            ],
            "errors": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "ERROR",
                    "message": "Database connection failed",
                    "module": "database"
                }
            ],
            "security": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "WARNING",
                    "message": "Failed login attempt",
                    "module": "auth"
                }
            ]
        }
        
        if log_type == "all":
            return jsonify(logs)
        elif log_type in logs:
            return jsonify({log_type: logs[log_type]})
        else:
            return jsonify({"error": "Invalid log type"}), 400
            
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
