"""Opaque, tenant-first OIP-2 HTTP API."""
from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.security import require_auth
from backend.extensions import db
from backend.services import oip_service as service
from backend.services.operational_service import OperationalError

oip_bp=Blueprint("oip",__name__)
def _user():
    user=get_current_user()
    if not user: raise OperationalError("FORBIDDEN_OPERATION","Authentication is required.",401)
    return user
def _error(exc): return jsonify({"error":{"code":exc.code,"message":exc.message}}),exc.status

@oip_bp.get("/api/oip/policies")
@require_auth
def policies():
    try: service.require_permission(_user(),"oip.read");return jsonify({"data":service.policy_catalog()})
    except OperationalError as exc:return _error(exc)

@oip_bp.post("/api/oip/reconcile")
@require_auth
def reconcile():
    try:return jsonify({"data":service.reconcile(_user())})
    except OperationalError as exc:db.session.rollback();return _error(exc)

@oip_bp.post("/api/oip/projection/rebuild")
@require_auth
def rebuild():
    try:return jsonify({"data":service.rebuild_attention_projections(_user())})
    except OperationalError as exc:db.session.rollback();return _error(exc)

@oip_bp.get("/api/oip/projection/status")
@require_auth
def projection_status():
    try:return jsonify({"data":service.projection_health(_user())})
    except OperationalError as exc:db.session.rollback();return _error(exc)

@oip_bp.get("/api/oip/attention")
@require_auth
def attention():
    try:
        user=_user();return jsonify({"data":service.queue(user),"projection_health":service.projection_health(user)})
    except OperationalError as exc:return _error(exc)

@oip_bp.get("/api/oip/situations/<string:public_id>")
@require_auth
def detail(public_id):
    try:return jsonify({"data":service.detail(public_id,_user())})
    except OperationalError as exc:return _error(exc)

@oip_bp.get("/api/oip/situations/<string:public_id>/decision-context")
@require_auth
def context(public_id):
    try:return jsonify({"data":service.detail(public_id,_user())["decision_context"]})
    except OperationalError as exc:return _error(exc)

@oip_bp.post("/api/oip/situations/<string:public_id>/<string:action>")
@require_auth
def transition(public_id,action):
    try:return jsonify({"data":service.transition(public_id,action,request.get_json(silent=True) or {},_user())})
    except OperationalError as exc:db.session.rollback();return _error(exc)
