"""Health check and landing routes."""
from flask import Blueprint, current_app, redirect

health_bp = Blueprint("health_bp", __name__)


@health_bp.get("/")
def landing_redirect():
    """Redirect visitors to the frontend landing page."""
    target = current_app.config.get("CORS_ORIGIN")
    if target:
        return redirect(target)
    # Fall back to a simple success message when no frontend URL is configured.
    return "✅ API is running! Backend is healthy."


@health_bp.get("/api/health")
def health_root() -> str:
    """Return a simple health status message for probes."""
    return "✅ API is running! Backend is healthy."
