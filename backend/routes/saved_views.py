from flask import Blueprint, jsonify, request

from backend.auth import get_current_user
from backend.security import require_auth
from backend.services.operational_service import OperationalError
from backend.saved_view_validation import SavedViewValidationError
from backend import saved_view_service as service

saved_view_bp = Blueprint("saved_views", __name__)


def _user():
    user = get_current_user()
    if not user:
        raise OperationalError("UNAUTHENTICATED", "Authentication is required.", 401)
    return user


def _call(fn, *args, created=False):
    try:
        return jsonify({"data": fn(*args)}), 201 if created else 200
    except OperationalError as exc:
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status
    except SavedViewValidationError as exc:
        return jsonify({"error": {"code": exc.code, "message": str(exc)}}), 422


@saved_view_bp.get("/api/v2/saved-views")
@require_auth
def list_saved_views():
    return _call(service.list_, _user(), request.args.get("status") == "ARCHIVED")


@saved_view_bp.get("/api/v2/saved-views/<string:public_id>")
@require_auth
def get_saved_view(public_id):
    return _call(service.get, public_id, _user())


@saved_view_bp.post("/api/v2/saved-views")
@require_auth
def create_saved_view():
    return _call(service.create, request.get_json(silent=True) or {}, _user(), created=True)


@saved_view_bp.patch("/api/v2/saved-views/<string:public_id>")
@require_auth
def patch_saved_view(public_id):
    return _call(service.update, public_id, request.get_json(silent=True) or {}, _user())


@saved_view_bp.post("/api/v2/saved-views/<string:public_id>/archive")
@require_auth
def archive_saved_view(public_id):
    return _call(service.lifecycle, public_id, request.get_json(silent=True) or {}, _user(), "ARCHIVED")


@saved_view_bp.post("/api/v2/saved-views/<string:public_id>/restore")
@require_auth
def restore_saved_view(public_id):
    return _call(service.lifecycle, public_id, request.get_json(silent=True) or {}, _user(), "ACTIVE")
