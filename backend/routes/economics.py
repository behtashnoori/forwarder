"""Opaque tenant-first Shipment Economics API."""
from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import economics_service as service
from backend.services.operational_service import OperationalError

economics_bp=Blueprint("economics",__name__)
def _user():
    user=get_current_user()
    if not user: raise OperationalError("FORBIDDEN_OPERATION","Authentication is required.",401)
    return user
def _error(exc): db.session.rollback();return jsonify({"error":{"code":exc.code,"message":exc.message}}),exc.status

@economics_bp.get("/api/v2/operational-shipments/<shipment_id>/economics/lines")
@require_auth
def lines(shipment_id):
    try:return jsonify({"data":service.list_lines(shipment_id,_user())})
    except OperationalError as exc:return _error(exc)

@economics_bp.post("/api/v2/operational-shipments/<shipment_id>/economics/lines")
@require_auth
def create_line(shipment_id):
    try:return jsonify({"data":service.create_line(shipment_id,request.get_json(silent=True) or {},_user())}),201
    except OperationalError as exc:return _error(exc)

@economics_bp.post("/api/v2/operational-shipments/<shipment_id>/economics/lines/<line_id>/observations")
@require_auth
def append(shipment_id,line_id):
    try:return jsonify({"data":service.append_observation(shipment_id,line_id,request.get_json(silent=True) or {},_user())}),201
    except OperationalError as exc:return _error(exc)

@economics_bp.post("/api/v2/operational-shipments/<shipment_id>/economics/observations/<observation_id>/correct")
@require_auth
def correct(shipment_id,observation_id):
    try:return jsonify({"data":service.correct(shipment_id,observation_id,request.get_json(silent=True) or {},_user())}),201
    except OperationalError as exc:return _error(exc)

@economics_bp.get("/api/v2/operational-shipments/<shipment_id>/economics/projection")
@require_auth
def projection(shipment_id):
    try:return jsonify({"data":service.projection(shipment_id,_user(),request.args.get("reporting_currency"))})
    except OperationalError as exc:return _error(exc)

@economics_bp.get("/api/v2/operational-shipments/<shipment_id>/economics/commercial-materialization-preview")
@require_auth
def preview(shipment_id):
    try:return jsonify({"data":service.quote_preview(shipment_id,_user())})
    except OperationalError as exc:return _error(exc)

@economics_bp.post("/api/v2/operational-shipments/<shipment_id>/economics/commercial-materialize")
@require_auth
def confirm(shipment_id):
    try:return jsonify({"data":service.quote_confirm(shipment_id,request.get_json(silent=True) or {},_user())}),201
    except OperationalError as exc:return _error(exc)

@economics_bp.post("/api/v2/economics/fx-rates")
@require_auth
def fx():
    try:return jsonify({"data":service.create_fx(request.get_json(silent=True) or {},_user())}),201
    except OperationalError as exc:return _error(exc)

@economics_bp.get("/api/v2/projects/<project_id>/economics/projection")
@require_auth
def project(project_id):
    try:return jsonify({"data":service.project_projection(project_id,_user(),request.args.get("stage","COMMITMENT"),request.args.get("reporting_currency"))})
    except OperationalError as exc:return _error(exc)
