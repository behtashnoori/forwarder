"""Separate liveness, health, and deployment-readiness probes."""

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from backend.extensions import db

health_bp = Blueprint("health_bp", __name__)


@health_bp.get("/")
def landing_redirect():
    """Return a simple confirmation that the backend is running."""
    return "✅ Backend is running"


@health_bp.get("/api/health")
def health_root():
    """Compatibility health endpoint; never exposes database exceptions."""
    port = current_app.config.get("PORT")
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        current_app.logger.error("Health check: database connection failed")
        return (
            jsonify({
                "status": "error",
                "database": "not_ready",
            }),
            503,
        )
    payload = {
        "status": "ok",
        "database": "connected",
        "port": port,
    }
    return jsonify(payload)


@health_bp.get("/api/health/ready")
def health_ready():
    """Return 200 only when DB, Alembic revision, and critical tables are ready."""
    from backend.runtime import readiness_report

    report = readiness_report(current_app._get_current_object())
    status_code = 200 if report["ready"] else 503
    return jsonify(report), status_code


@health_bp.get("/api/health/ping")
def health_ping():
    """Legacy ping endpoint; lightweight ok without DB check for load balancers."""
    return jsonify({"status": "ok", "message": "API is running! Backend is healthy."})
