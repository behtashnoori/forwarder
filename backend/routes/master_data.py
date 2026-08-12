"""Admin-only API for governed canonical master data."""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.security import require_role
from backend.services import master_data_service as svc
from backend.services.admin_authorization_service import require_organization_admin_context, require_platform_admin

master_data_bp = Blueprint("master_data", __name__, url_prefix="/api/admin/master-data")


def _resource(resource):
    model = svc.model_for(resource)
    return model, None if model else (jsonify({"error": "unknown resource"}), 404)


def _row(model, public_id):
    row = model.query.filter_by(public_id=public_id).first()
    return row, None if row else (jsonify({"error": "not found"}), 404)


def _failure(exc):
    db.session.rollback()
    status = 409 if isinstance(exc, (svc.VersionConflictError, IntegrityError)) else 400
    return jsonify({"error": str(exc) if not isinstance(exc, IntegrityError) else "conflicting master data"}), status


@master_data_bp.get("/<resource>")
@require_organization_admin_context()
def list_resource(resource):
    model, error = _resource(resource)
    if error:
        return error
    try:
        active_arg = request.args.get("active")
        active = None if active_arg in (None, "all") else active_arg == "true"
        result = svc.list_rows(
            resource, search=request.args.get("q", ""), active=active,
            dimension=request.args.get("measurement_dimension"), sort=request.args.get("sort", "display_order"),
            direction=request.args.get("direction", "asc"), page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 20, type=int),
        )
        return jsonify({"items": [svc.serialize(row) for row in result.items], "page": result.page, "per_page": result.per_page, "total": result.total, "pages": result.pages})
    except svc.MasterDataValidationError as exc:
        return _failure(exc)


@master_data_bp.get("/<resource>/<public_id>")
@require_organization_admin_context()
def detail_resource(resource, public_id):
    model, error = _resource(resource)
    if error: return error
    row, error = _row(model, public_id)
    return error or jsonify({"item": svc.serialize(row)})


@master_data_bp.post("/<resource>")
@require_platform_admin()
def create_resource(resource):
    if svc.model_for(resource) is None:
        return jsonify({"error": "unknown resource"}), 404
    try:
        return jsonify({"item": svc.serialize(svc.create(resource, request.get_json(silent=True) or {}))}), 201
    except (svc.MasterDataValidationError, IntegrityError) as exc:
        return _failure(exc)


@master_data_bp.patch("/<resource>/<public_id>")
@require_platform_admin()
def update_resource(resource, public_id):
    model, error = _resource(resource)
    if error: return error
    row, error = _row(model, public_id)
    if error: return error
    try:
        return jsonify({"item": svc.serialize(svc.update(row, request.get_json(silent=True) or {}))})
    except (svc.MasterDataValidationError, svc.VersionConflictError, IntegrityError) as exc:
        return _failure(exc)


@master_data_bp.post("/<resource>/<public_id>/<action>")
@require_platform_admin()
def activation_resource(resource, public_id, action):
    if action not in {"activate", "deactivate"}:
        return jsonify({"error": "unknown action"}), 404
    model, error = _resource(resource)
    if error: return error
    row, error = _row(model, public_id)
    if error: return error
    try:
        data = request.get_json(silent=True) or {}
        return jsonify({"item": svc.serialize(svc.set_active(row, action == "activate", data.get("version")))})
    except (svc.MasterDataValidationError, svc.VersionConflictError) as exc:
        return _failure(exc)
