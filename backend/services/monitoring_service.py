"""Service helpers for monitoring and analytics orchestration."""
from datetime import datetime
from typing import Any, Dict, Optional

from backend.monitoring import analytics_engine, system_monitor


def get_health_status() -> Dict[str, Any]:
    """Return system health status."""
    return system_monitor.get_health_status()


def get_system_metrics() -> Dict[str, Any]:
    """Return system metrics."""
    return system_monitor.get_system_metrics()


def get_database_metrics() -> Dict[str, Any]:
    """Return database performance metrics."""
    return system_monitor.get_database_metrics()


def get_business_metrics() -> Dict[str, Any]:
    """Return business metrics."""
    return system_monitor.get_business_metrics()


def get_customer_analytics(days: int) -> Dict[str, Any]:
    """Return customer analytics for the requested period."""
    return analytics_engine.get_customer_analytics(days)


def get_sales_analytics(days: int) -> Dict[str, Any]:
    """Return sales analytics for the requested period."""
    return analytics_engine.get_sales_analytics(days)


def get_performance_analytics(days: int) -> Dict[str, Any]:
    """Return performance analytics for the requested period."""
    return analytics_engine.get_performance_analytics(days)


def get_dashboard_summary() -> Dict[str, Any]:
    """Return the comprehensive monitoring dashboard payload."""
    system_metrics = get_system_metrics()
    db_metrics = get_database_metrics()
    business_metrics = get_business_metrics()
    health_status = get_health_status()

    customer_analytics = get_customer_analytics(30)
    sales_analytics = get_sales_analytics(30)
    performance_analytics = get_performance_analytics(30)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "health": health_status,
        "system": system_metrics,
        "database": db_metrics,
        "business": business_metrics,
        "analytics": {
            "customers": customer_analytics,
            "sales": sales_analytics,
            "performance": performance_analytics,
        },
    }


def get_system_logs(log_type: str, limit: int) -> Optional[Dict[str, Any]]:
    """Return monitoring log payloads for a log type, preserving current mock behavior."""
    # The route has historically accepted a limit query parameter, but the
    # current mock payload is fixed-size. Keep the parameter in the service
    # signature to preserve the endpoint contract without changing behavior.
    _ = limit
    logs = {
        "application": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "Application started",
                "module": "app",
            }
        ],
        "errors": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Database connection failed",
                "module": "database",
            }
        ],
        "security": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "WARNING",
                "message": "Failed login attempt",
                "module": "auth",
            }
        ],
    }

    if log_type == "all":
        return logs
    if log_type in logs:
        return {log_type: logs[log_type]}
    return None
