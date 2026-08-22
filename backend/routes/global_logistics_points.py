"""Platform-only governed API for the ADR-041 global catalog."""

from flask import Blueprint, g, jsonify, request

from backend.extensions import db
from backend.services.admin_authorization_service import require_platform_admin
from backend.services import global_logistics_point_service as svc
from backend.services.operational_service import OperationalError


global_logistics_points_bp = Blueprint("global_logistics_points", __name__)


def _error(exc: OperationalError):
    db.session.rollback()
    error = {"code": exc.code, "message": exc.message}
    if getattr(exc, "details", None) is not None:
        error["details"] = exc.details
    return jsonify({"error": error}), exc.status


def _payload():
    return request.get_json(silent=True)


def _actor():
    return int(g.current_user_id)


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


@global_logistics_points_bp.post("/api/platform/global-logistics-points")
@require_platform_admin()
def create_global_logistics_point():
    try:
        return jsonify({"item": svc.projection(svc.create(_payload(), _actor()))}), 201
    except OperationalError as exc:
        return _error(exc)


@global_logistics_points_bp.patch("/api/platform/global-logistics-points/<public_id>")
@require_platform_admin()
def update_global_logistics_point(public_id):
    try:
        return jsonify({"item": svc.projection(svc.update(public_id, _payload(), _actor()))})
    except OperationalError as exc:
        return _error(exc)


def _action(public_id, operation):
    try:
        return jsonify({"item": svc.projection(operation(public_id, _payload(), _actor()))})
    except OperationalError as exc:
        return _error(exc)


@global_logistics_points_bp.post("/api/platform/global-logistics-points/<public_id>/review")
@require_platform_admin()
def review_global_logistics_point(public_id):
    return _action(public_id, svc.review)


@global_logistics_points_bp.post("/api/platform/global-logistics-points/<public_id>/verify")
@require_platform_admin()
def verify_global_logistics_point(public_id):
    return _action(public_id, svc.verify)


@global_logistics_points_bp.post("/api/platform/global-logistics-points/<public_id>/activate")
@require_platform_admin()
def activate_global_logistics_point(public_id):
    return _action(public_id, svc.activate)


@global_logistics_points_bp.post("/api/platform/global-logistics-points/<public_id>/deprecate")
@require_platform_admin()
def deprecate_global_logistics_point(public_id):
    return _action(public_id, svc.deprecate)
