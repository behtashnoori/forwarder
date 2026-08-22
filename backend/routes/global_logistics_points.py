"""Platform-only read API for the ADR-041 Phase 1 empty catalog."""

from flask import Blueprint, jsonify, request

from backend.extensions import db
from backend.services.admin_authorization_service import require_platform_admin
from backend.services import global_logistics_point_service as svc
from backend.services.operational_service import OperationalError


global_logistics_points_bp = Blueprint("global_logistics_points", __name__)


def _error(exc: OperationalError):
    db.session.rollback()
    return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status


@global_logistics_points_bp.get("/api/platform/global-logistics-points")
@require_platform_admin()
def list_global_logistics_points():
    try:
        return jsonify(svc.list_points(request.args))
    except OperationalError as exc:
        return _error(exc)


@global_logistics_points_bp.get("/api/platform/global-logistics-points/<public_id>")
@require_platform_admin()
def global_logistics_point_detail(public_id):
    try:
        return jsonify({"item": svc.projection(svc.detail(public_id))})
    except OperationalError as exc:
        return _error(exc)
