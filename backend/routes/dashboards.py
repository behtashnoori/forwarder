from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.security import require_auth
from backend.services.operational_service import OperationalError
from backend import dashboard_service as service
from backend.dashboard_validation import DashboardValidationError
dashboard_bp=Blueprint("dashboards",__name__)
def call(fn,*args):
    try:return jsonify({"data":fn(*args)})
    except OperationalError as e:return jsonify({"error":{"code":e.code,"message":e.message}}),e.status
    except DashboardValidationError as e:return jsonify({"error":{"code":e.code,"message":str(e)}}),422
    except ValueError as e:return jsonify({"error":{"code":"INVALID_DASHBOARD_DEFINITION","message":str(e)}}),422
def user():
    row=get_current_user()
    if not row: raise OperationalError("UNAUTHENTICATED","Authentication is required.",401)
    return row
@dashboard_bp.get("/api/v2/dashboards")
@require_auth
def list_dashboards(): return call(service.list_,user())
@dashboard_bp.get("/api/v2/dashboards/<string:public_id>")
@require_auth
def get_dashboard(public_id): return call(service.get,public_id,user())
@dashboard_bp.post("/api/v2/dashboards/system/<string:system_id>/clone")
@require_auth
def clone_dashboard(system_id): return call(service.clone,system_id,user(),(request.get_json(silent=True) or {}).get("name"))
@dashboard_bp.patch("/api/v2/dashboards/<string:public_id>")
@require_auth
def patch_dashboard(public_id): return call(service.update,public_id,request.get_json(silent=True) or {},user())
@dashboard_bp.post("/api/v2/dashboards/<string:public_id>/archive")
@require_auth
def archive_dashboard(public_id): return call(service.lifecycle,public_id,user(),"ARCHIVED")
@dashboard_bp.post("/api/v2/dashboards/<string:public_id>/restore")
@require_auth
def restore_dashboard(public_id): return call(service.lifecycle,public_id,user(),"ACTIVE")
