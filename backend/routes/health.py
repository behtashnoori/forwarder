"""Health check endpoints."""
from flask import Blueprint

health_bp = Blueprint("health_bp", __name__)


@health_bp.get("/")
def health_root() -> str:
    """Return a simple health status message."""
    return "✅ API is running! Backend is healthy."
