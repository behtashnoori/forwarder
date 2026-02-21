"""Health check and landing routes."""
from flask import Blueprint, jsonify

health_bp = Blueprint("health_bp", __name__)


@health_bp.get("/")
def landing_redirect():
    """Return a simple confirmation that the backend is running."""
    return "✅ Backend is running"


@health_bp.get("/api/health")
def health_root():
    """Return JSON health status for probes and frontend checks."""
    return jsonify({"status": "ok", "message": "API is running! Backend is healthy."})


@health_bp.get("/api/health/ping")
def health_ping():
    """Legacy ping endpoint; same JSON as /api/health for tests."""
    return jsonify({"status": "ok", "message": "API is running! Backend is healthy."})
