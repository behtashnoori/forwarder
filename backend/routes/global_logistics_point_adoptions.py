"""Organization Admin routes for tenant-owned global-point adoption."""
from flask import Blueprint, g, jsonify, request

from backend.extensions import db
from backend.services.admin_authorization_service import require_organization_admin_context
from backend.services import global_logistics_point_adoption_service as svc
from backend.services.operational_service import OperationalError

global_logistics_point_adoptions_bp = Blueprint("global_logistics_point_adoptions", __name__)


def _error(exc):
    db.session.rollback(); return jsonify({"error":{"code":exc.code,"message":exc.message}}),exc.status


def _context(): return int(g.organization_context.organization_id), int(g.current_user_id)


@global_logistics_point_adoptions_bp.get("/api/admin/global-logistics-points")
@require_organization_admin_context(allow_platform=False)
def browse():
    try: return jsonify(svc.browse(request.args,_context()[0]))
    except OperationalError as exc: return _error(exc)


@global_logistics_point_adoptions_bp.post("/api/admin/global-logistics-points/<public_id>/adopt")
@require_organization_admin_context(allow_platform=False)
def adopt(public_id):
    try:
        org,actor=_context(); return jsonify({"item":svc.adoption_projection(svc.adopt(public_id,request.get_json(silent=True),org,actor))}),201
    except OperationalError as exc: return _error(exc)


@global_logistics_point_adoptions_bp.get("/api/admin/global-logistics-point-adoptions/<public_id>")
@require_organization_admin_context(allow_platform=False)
def detail(public_id):
    try: return jsonify({"item":svc.adoption_projection(svc.scoped_adoption(public_id,_context()[0]))})
    except OperationalError as exc: return _error(exc)


@global_logistics_point_adoptions_bp.patch("/api/admin/global-logistics-point-adoptions/<public_id>")
@require_organization_admin_context(allow_platform=False)
def update(public_id):
    try:
        org,actor=_context(); return jsonify({"item":svc.adoption_projection(svc.update(public_id,request.get_json(silent=True),org,actor))})
    except OperationalError as exc: return _error(exc)


@global_logistics_point_adoptions_bp.post("/api/admin/global-logistics-point-adoptions/<public_id>/<action>")
@require_organization_admin_context(allow_platform=False)
def transition(public_id,action):
    if action not in {"activate","deactivate"}: return jsonify({"error":{"code":"NOT_FOUND","message":"Action not found."}}),404
    try:
        org,actor=_context(); target="ACTIVE" if action=="activate" else "INACTIVE"
        return jsonify({"item":svc.adoption_projection(svc.transition(public_id,request.get_json(silent=True),org,actor,target))})
    except OperationalError as exc: return _error(exc)
