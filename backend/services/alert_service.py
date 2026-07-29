"""Service helpers for monitoring alert orchestration."""
from typing import Any, Dict, List

from backend.services.monitoring_service import get_system_metrics
from backend.services.utc_timestamp import current_utc_timestamp


def list_alerts() -> Dict[str, Any]:
    """Build the current system alerts payload from monitoring metrics."""
    alerts: List[Dict[str, str]] = []
    metrics = get_system_metrics()

    memory_percent = metrics["system"]["memory"]["percent"]
    if memory_percent > 90:
        alerts.append({
            "type": "critical",
            "category": "memory",
            "message": f"Memory usage is critically high: {memory_percent:.1f}%",
            "timestamp": current_utc_timestamp(),
        })
    elif memory_percent > 80:
        alerts.append({
            "type": "warning",
            "category": "memory",
            "message": f"Memory usage is high: {memory_percent:.1f}%",
            "timestamp": current_utc_timestamp(),
        })

    cpu_percent = metrics["system"]["cpu_percent"]
    if cpu_percent > 90:
        alerts.append({
            "type": "critical",
            "category": "cpu",
            "message": f"CPU usage is critically high: {cpu_percent:.1f}%",
            "timestamp": current_utc_timestamp(),
        })
    elif cpu_percent > 80:
        alerts.append({
            "type": "warning",
            "category": "cpu",
            "message": f"CPU usage is high: {cpu_percent:.1f}%",
            "timestamp": current_utc_timestamp(),
        })

    total_requests = metrics["application"]["total_requests"]
    total_errors = metrics["application"]["total_errors"]

    if total_requests > 0:
        error_rate = (total_errors / total_requests) * 100
        if error_rate > 10:
            alerts.append({
                "type": "critical",
                "category": "errors",
                "message": f"Error rate is critically high: {error_rate:.1f}%",
                "timestamp": current_utc_timestamp(),
            })
        elif error_rate > 5:
            alerts.append({
                "type": "warning",
                "category": "errors",
                "message": f"Error rate is high: {error_rate:.1f}%",
                "timestamp": current_utc_timestamp(),
            })

    avg_response_time = metrics["application"]["avg_response_time"]
    if avg_response_time > 5.0:
        alerts.append({
            "type": "warning",
            "category": "performance",
            "message": f"Average response time is slow: {avg_response_time:.2f}s",
            "timestamp": current_utc_timestamp(),
        })

    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["type"] == "critical"]),
        "warning_alerts": len([a for a in alerts if a["type"] == "warning"]),
    }


def acknowledge_alert(alert_id: Any) -> Dict[str, Any]:
    """Return the current acknowledgement payload for an alert id."""
    return {
        "message": "Alert acknowledged",
        "alert_id": alert_id,
        "acknowledged_at": current_utc_timestamp(),
    }
