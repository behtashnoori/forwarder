"""Authenticated, sanitized system identity routes."""
from flask import Blueprint, jsonify

from backend.auth import get_current_user
from backend.security import require_auth
from backend.services.release_identity_service import release_identity

system_bp = Blueprint("system", __name__)


@system_bp.get("/api/system/release-identity")
@require_auth
def get_release_identity():
    user = get_current_user() or {}
    support = user.get("role") in {"admin", "support"}
    return jsonify({"data": release_identity(support=support), "projection": "support" if support else "normal"})
