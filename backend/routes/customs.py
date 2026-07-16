"""Authenticated customs master-data API."""
from flask import Blueprint, jsonify, request
from backend.extensions import db
from backend.models import CustomsOffice, PortCustomsOffice
from backend.security import require_role
from backend.services import customs_service
from sqlalchemy.exc import IntegrityError

customs_bp = Blueprint("customs", __name__, url_prefix="/api/customs")


def _error(error):
    db.session.rollback()
    return jsonify({"error": str(error)}), 400


def _conflict():
    db.session.rollback()
    return jsonify({"error": "conflicting customs master data"}), 409


@customs_bp.get("/offices")
@require_role("admin")
def list_offices():
    return jsonify({"customs_offices": [customs_service.serialize_office(x) for x in CustomsOffice.query.order_by(CustomsOffice.code).all()]})


@customs_bp.post("/offices")
@require_role("admin")
def create_office():
    try:
        office = customs_service.create_office(request.get_json(silent=True) or {})
        return jsonify({"customs_office": customs_service.serialize_office(office)}), 201
    except customs_service.CustomsValidationError as exc: return _error(exc)
    except IntegrityError: return _conflict()


@customs_bp.get("/offices/<int:office_id>")
@require_role("admin")
def read_office(office_id):
    office = db.session.get(CustomsOffice, office_id)
    return (jsonify({"customs_office": customs_service.serialize_office(office)}) if office else (jsonify({"error": "not found"}), 404))


@customs_bp.put("/offices/<int:office_id>")
@require_role("admin")
def update_office(office_id):
    office = db.session.get(CustomsOffice, office_id)
    if office is None: return jsonify({"error": "not found"}), 404
    try: return jsonify({"customs_office": customs_service.serialize_office(customs_service.update_office(office, request.get_json(silent=True) or {}))})
    except customs_service.CustomsValidationError as exc: return _error(exc)
    except IntegrityError: return _conflict()


@customs_bp.get("/relationships")
@require_role("admin")
def list_relationships():
    return jsonify({"relationships": [{"id": x.id, "port_id": x.port_id, "customs_office_id": x.customs_office_id, "relationship_type": x.relationship_type, "is_primary": x.is_primary, "is_active": x.is_active} for x in PortCustomsOffice.query.order_by(PortCustomsOffice.id).all()]})


@customs_bp.post("/relationships")
@require_role("admin")
def create_relationship():
    try:
        x = customs_service.create_relationship(request.get_json(silent=True) or {})
        return jsonify({"relationship": {"id": x.id, "port_id": x.port_id, "customs_office_id": x.customs_office_id, "relationship_type": x.relationship_type}}), 201
    except customs_service.CustomsValidationError as exc: return _error(exc)
    except IntegrityError: return _conflict()


@customs_bp.delete("/relationships/<int:relationship_id>")
@require_role("admin")
def deactivate_relationship(relationship_id):
    relation = db.session.get(PortCustomsOffice, relationship_id)
    if relation is None: return jsonify({"error": "not found"}), 404
    relation.is_active = False; db.session.commit(); return jsonify({"status": "deactivated"})
