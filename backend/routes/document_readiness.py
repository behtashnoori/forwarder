"""Opaque-ID MDPM-1 document readiness API."""
from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import document_readiness_service as svc
from backend.services.operational_service import OperationalError

document_readiness_bp = Blueprint("document_readiness", __name__)

def _user():
    row = get_current_user()
    if not row: raise OperationalError("UNAUTHENTICATED", "Authentication is required.", 401)
    return row

def _call(fn, *args, created=False):
    try: return jsonify({"data": fn(*args)}), 201 if created else 200
    except OperationalError as exc:
        db.session.rollback(); return jsonify({"error":{"code":exc.code,"message":exc.message,"fields":getattr(exc,"fields",[])}}), exc.status

@document_readiness_bp.get("/api/v2/operational-shipments/<shipment_id>/document-readiness/materialization-preview")
@require_auth
def preview(shipment_id): return _call(svc.materialization_preview, shipment_id, _user())

@document_readiness_bp.post("/api/v2/operational-shipments/<shipment_id>/document-readiness/materialize")
@require_auth
def materialize(shipment_id):
    try:
        rows, created = svc.materialize(shipment_id, request.get_json(silent=True) or {}, _user())
        return jsonify({"data":[svc._requirement_projection(r) for r in rows],"meta":{"created":created}}), 201 if created else 200
    except OperationalError as exc:
        db.session.rollback(); return jsonify({"error":{"code":exc.code,"message":exc.message,"fields":[]}}), exc.status

@document_readiness_bp.get("/api/v2/operational-shipments/<shipment_id>/document-readiness/requirements")
@require_auth
def requirements(shipment_id): return _call(svc.list_requirements, shipment_id, _user())

@document_readiness_bp.post("/api/v2/operational-shipments/<shipment_id>/document-readiness/requirements/<requirement_id>/artifacts")
@require_auth
def associate(shipment_id, requirement_id): return _call(svc.associate, shipment_id, requirement_id, request.get_json(silent=True) or {}, _user())

@document_readiness_bp.post("/api/v2/operational-shipments/<shipment_id>/document-readiness/requirements/<requirement_id>/assessments")
@require_auth
def assess(shipment_id, requirement_id): return _call(svc.assess, shipment_id, requirement_id, request.get_json(silent=True) or {}, _user(), created=True)

@document_readiness_bp.post("/api/v2/operational-shipments/<shipment_id>/document-readiness/requirements/<requirement_id>/applicability")
@require_auth
def applicability(shipment_id, requirement_id): return _call(svc.resolve_applicability, shipment_id, requirement_id, request.get_json(silent=True) or {}, _user(), created=True)

@document_readiness_bp.get("/api/v2/operational-shipments/<shipment_id>/document-readiness/milestones/<milestone_id>/readiness")
@require_auth
def readiness(shipment_id, milestone_id): return _call(svc.readiness, shipment_id, milestone_id, request.args.get("target_status", ""), _user())

@document_readiness_bp.get("/api/v2/operational-shipments/<shipment_id>/document-readiness/next-action")
@require_auth
def next_action(shipment_id): return _call(svc.next_readiness, shipment_id, _user())

@document_readiness_bp.post("/api/v2/operational-shipments/<shipment_id>/document-readiness/requirements/<requirement_id>/overrides")
@require_auth
def create_override(shipment_id, requirement_id): return _call(svc.create_override, shipment_id, requirement_id, request.get_json(silent=True) or {}, _user(), created=True)

@document_readiness_bp.post("/api/v2/operational-shipments/<shipment_id>/document-readiness/overrides/<override_id>/revoke")
@require_auth
def revoke_override(shipment_id, override_id): return _call(svc.revoke_override, shipment_id, override_id, _user())
