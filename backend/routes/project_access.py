from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.security import require_auth
from backend.services import project_access_authorization as service
from backend.services.operational_service import OperationalError

project_access_bp = Blueprint("project_access", __name__)

def _call(fn, *args, created=False):
    try: return jsonify({"data": fn(*args)}), 201 if created else 200
    except OperationalError as exc: return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status

@project_access_bp.get("/api/v2/projects/<project_id>/access")
@require_auth
def list_access(project_id): return _call(service.list_assignments, project_id, get_current_user())

@project_access_bp.post("/api/v2/projects/<project_id>/access")
@require_auth
def add_access(project_id): return _call(service.add_assignment, project_id, request.get_json(silent=True) or {}, get_current_user(), created=True)

@project_access_bp.delete("/api/v2/projects/<project_id>/access/<assignment_id>")
@require_auth
def revoke_access(project_id, assignment_id): return _call(service.revoke_assignment, project_id, assignment_id, get_current_user())
