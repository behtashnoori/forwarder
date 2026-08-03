"""Internal/admin Logistics Network HTTP contract."""

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from backend.auth import get_current_user
from backend.extensions import db
from backend.logistics_network_models import LogisticsPointType
from backend.security import require_auth, require_role
from backend.services import logistics_network_service as svc
from backend.services.operational_service import OperationalError

logistics_network_bp = Blueprint("logistics_network", __name__)


def _user():
    user = get_current_user()
    if not user:
        raise OperationalError("UNAUTHENTICATED", "Authentication is required.", 401)
    return user


def _error(exc):
    db.session.rollback()
    return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status


def _type(public_id):
    row = db.session.scalar(
        select(LogisticsPointType).where(LogisticsPointType.public_id == public_id)
    )
    if not row:
        raise OperationalError("NOT_FOUND", "Logistics point type not found.", 404)
    return row


@logistics_network_bp.get("/api/admin/logistics-point-types")
@require_role("admin")
def type_list():
    return jsonify(svc.list_types(request.args, admin=True))


@logistics_network_bp.post("/api/admin/logistics-point-types")
@require_role("admin")
def type_create():
    try:
        row = svc.create_type(request.get_json(silent=True) or {}, _user())
        svc.commit_or_error()
        return jsonify({"item": svc.type_projection(row)}), 201
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.get("/api/admin/logistics-point-types/<public_id>")
@require_role("admin")
def type_detail(public_id):
    try:
        return jsonify({"item": svc.type_projection(_type(public_id))})
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.patch("/api/admin/logistics-point-types/<public_id>")
@require_role("admin")
def type_update(public_id):
    try:
        row = svc.update_type(
            _type(public_id), request.get_json(silent=True) or {}, _user()
        )
        svc.commit_or_error()
        return jsonify({"item": svc.type_projection(row)})
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.post("/api/admin/logistics-point-types/<public_id>/<action>")
@require_role("admin")
def type_active(public_id, action):
    try:
        if action not in {"activate", "deactivate"}:
            raise OperationalError("NOT_FOUND", "Action not found.", 404)
        row = svc.set_active(
            _type(public_id),
            action == "activate",
            request.get_json(silent=True) or {},
            _user(),
        )
        svc.commit_or_error()
        return jsonify({"item": svc.type_projection(row)})
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.get("/api/admin/logistics-points")
@require_role("admin")
def admin_point_list():
    try:
        return jsonify(svc.list_points(request.args, _user(), admin=True))
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.post("/api/admin/logistics-points")
@require_role("admin")
def point_create():
    try:
        row = svc.create_point(request.get_json(silent=True) or {}, _user())
        svc.commit_or_error()
        return jsonify({"item": svc.point_projection(row)}), 201
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.get("/api/admin/logistics-points/<public_id>")
@require_role("admin")
def point_detail(public_id):
    try:
        return jsonify(
            {"item": svc.point_projection(svc.scoped_point(public_id, _user()))}
        )
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.patch("/api/admin/logistics-points/<public_id>")
@require_role("admin")
def point_update(public_id):
    try:
        user = _user()
        row = svc.update_point(
            svc.scoped_point(public_id, user, "logistics_point.manage"),
            request.get_json(silent=True) or {},
            user,
        )
        svc.commit_or_error()
        return jsonify({"item": svc.point_projection(row)})
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.post("/api/admin/logistics-points/<public_id>/<action>")
@require_role("admin")
def point_active(public_id, action):
    try:
        if action not in {"activate", "deactivate"}:
            raise OperationalError("NOT_FOUND", "Action not found.", 404)
        user = _user()
        row = svc.set_active(
            svc.scoped_point(public_id, user, "logistics_point.manage"),
            action == "activate",
            request.get_json(silent=True) or {},
            user,
        )
        svc.commit_or_error()
        return jsonify({"item": svc.point_projection(row)})
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.get("/api/internal/logistics-point-types")
@require_auth
def internal_types():
    return jsonify(svc.list_types(request.args))


@logistics_network_bp.get("/api/internal/logistics-points")
@require_auth
def internal_points():
    try:
        return jsonify(svc.list_points(request.args, _user()))
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.get("/api/v2/projects/<project_id>/logistics-points")
@require_auth
def project_list(project_id):
    try:
        return jsonify(svc.list_associations(svc.scoped_project(project_id, _user())))
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.post("/api/v2/projects/<project_id>/logistics-points")
@require_auth
def project_create(project_id):
    try:
        user = _user()
        project = svc.scoped_project(project_id, user, "project_logistics_point.manage")
        row = svc.create_association(project, request.get_json(silent=True) or {}, user)
        svc.commit_or_error()
        return jsonify({"item": svc.association_projection(row)}), 201
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.get(
    "/api/v2/projects/<project_id>/logistics-points/<association_id>"
)
@require_auth
def project_detail(project_id, association_id):
    try:
        project = svc.scoped_project(project_id, _user())
        return jsonify(
            {
                "item": svc.association_projection(
                    svc.scoped_association(project, association_id)
                )
            }
        )
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.patch(
    "/api/v2/projects/<project_id>/logistics-points/<association_id>"
)
@require_auth
def project_update(project_id, association_id):
    try:
        user = _user()
        project = svc.scoped_project(project_id, user, "project_logistics_point.manage")
        row = svc.update_association(
            svc.scoped_association(project, association_id),
            request.get_json(silent=True) or {},
            user,
        )
        svc.commit_or_error()
        return jsonify({"item": svc.association_projection(row)})
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.post(
    "/api/v2/projects/<project_id>/logistics-points/<association_id>/<action>"
)
@require_auth
def project_active(project_id, association_id, action):
    try:
        if action not in {"activate", "deactivate"}:
            raise OperationalError("NOT_FOUND", "Action not found.", 404)
        user = _user()
        project = svc.scoped_project(project_id, user, "project_logistics_point.manage")
        row = svc.scoped_association(project, association_id)
        if action == "activate" and not row.logistics_point.is_active:
            raise OperationalError(
                "VALIDATION_FAILED", "Inactive point cannot be selected."
            )
        svc.set_active(
            row, action == "activate", request.get_json(silent=True) or {}, user
        )
        svc.commit_or_error()
        return jsonify({"item": svc.association_projection(row)})
    except OperationalError as exc:
        return _error(exc)


@logistics_network_bp.post("/api/v2/projects/<project_id>/logistics-points/reorder")
@require_auth
def project_reorder(project_id):
    try:
        user = _user()
        project = svc.scoped_project(project_id, user, "project_logistics_point.manage")
        rows = svc.reorder(project, request.get_json(silent=True) or {}, user)
        svc.commit_or_error()
        return jsonify(
            {
                "items": [
                    svc.association_projection(x)
                    for x in sorted(rows, key=lambda r: r.sequence_number)
                ]
            }
        )
    except OperationalError as exc:
        return _error(exc)
