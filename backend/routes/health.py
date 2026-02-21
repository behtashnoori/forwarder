"""Health check and landing routes."""
import traceback

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from backend.extensions import db

health_bp = Blueprint("health_bp", __name__)


@health_bp.get("/")
def landing_redirect():
    """Return a simple confirmation that the backend is running."""
    return "✅ Backend is running"


@health_bp.get("/api/health")
def health_root():
    """Return JSON health status for probes and frontend. Only checks DB connection; returns 500 only if DB is down."""
    port = current_app.config.get("PORT")
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        current_app.logger.exception("Health check: database connection failed")
        traceback.print_exc()
        return (
            jsonify({
                "status": "error",
                "database": "not_ready",
                "message": str(e),
            }),
            500,
        )
    # Optional: check tables only when explicitly requested (e.g. GET /api/health?readiness=1)
    tables_ok = True
    if current_app.config.get("TESTING") or request.args.get("readiness"):
        for table in ("province", "transport_method"):
            try:
                db.session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            except Exception as e:
                current_app.logger.warning("Health readiness: table %s missing or inaccessible: %s", table, e)
                tables_ok = False
                break
    payload = {
        "status": "ok",
        "database": "connected",
        "port": port,
    }
    if request.args.get("readiness"):
        payload["tables_ready"] = tables_ok
    return jsonify(payload)


@health_bp.get("/api/health/ping")
def health_ping():
    """Legacy ping endpoint; lightweight ok without DB check for load balancers."""
    return jsonify({"status": "ok", "message": "API is running! Backend is healthy."})
