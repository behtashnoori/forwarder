"""Read-only semantic analytics HTTP contract."""
from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.analytics import service
from backend.services.operational_service import OperationalError

analytics_bp = Blueprint("analytics", __name__)

def _user():
    row = get_current_user()
    if not row: raise OperationalError("UNAUTHENTICATED", "Authentication is required.", 401)
    return row

def _call(fn, *args):
    try: return jsonify({"data": fn(*args)})
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status

@analytics_bp.get("/api/v2/analytics/semantic-registry")
@require_auth
def registry(): return _call(service.semantic_registry, _user())

@analytics_bp.post("/api/v2/analytics/query")
@require_auth
def query(): return _call(service.query, request.get_json(silent=True) or {}, _user())

@analytics_bp.get("/api/v2/analytics/drilldown/<string:metric>")
@require_auth
def drilldown(metric): return _call(service.drilldown, metric, _user(), request.get_json(silent=True) or {}, request.args.get("limit", 100))
