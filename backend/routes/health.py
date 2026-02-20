"""Health check and landing routes."""
from flask import Blueprint, jsonify, request, make_response

health_bp = Blueprint("health_bp", __name__)


@health_bp.get("/")
def landing_redirect():
    """Return a simple confirmation that the backend is running."""
    # The landing endpoint should not redirect to any external origin; it simply
    # returns a plain-text response indicating that the service is up.
    return "✅ Backend is running"


@health_bp.get("/api/health")
def health_root() -> str:
    """Return a simple health status message for probes."""
    return "✅ API is running! Backend is healthy."


@health_bp.route("/api/health/ping", methods=["GET", "OPTIONS"])
def health_ping():
    """JSON health ping for monitoring and tests. OPTIONS for CORS preflight."""
    if request.method == "OPTIONS":
        r = make_response("", 200)
        # CORS headers are added by after_request; ensure preflight gets 200
        return r
    return jsonify(message="OK", status="healthy")
