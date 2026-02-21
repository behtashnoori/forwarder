"""Health check and landing routes."""
import traceback

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
    """Return JSON health status for probes and frontend. Checks DB; returns 500 if DB down."""
    port = current_app.config.get("PORT")
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "ok",
            "database": "connected",
            "port": port,
        })
    except Exception as e:
        current_app.logger.exception("Health check: database connection failed")
        traceback.print_exc()
        return (
            jsonify({
                "status": "error",
                "database": "disconnected",
                "message": str(e),
            }),
            500,
        )


@health_bp.get("/api/health/ping")
def health_ping():
    """Legacy ping endpoint; lightweight ok without DB check for load balancers."""
    return jsonify({"status": "ok", "message": "API is running! Backend is healthy."})
