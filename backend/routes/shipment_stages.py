"""Organization Shipment Stage configuration and execution API."""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import shipment_stage_service as service
from backend.services.operational_service import OperationalError


shipment_stages_bp = Blueprint("shipment_stages", __name__)


@shipment_stages_bp.after_request
def no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


def run(action, write=False):
    try:
        value = action()
        if write:
            row, created = value
            value = {"public_id": row.public_id, "created": created}
            db.session.commit()
        return jsonify({"data": value}), 201 if write and created else 200
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status
    except (IntegrityError, DBAPIError) as exc:
        db.session.rollback()
        if isinstance(exc, DBAPIError) and getattr(exc.orig, "sqlstate", getattr(exc.orig, "pgcode", None)) not in {"40001", "40P01", "23503", "23505", "23514"}:
            raise
        return jsonify({"error": {"code": "SHIPMENT_STAGE_CONFLICT", "message": "اطلاعات مراحل هم‌زمان تغییر کرد؛ دوباره بخوانید."}}), 409


@shipment_stages_bp.get("/api/admin/shipment-stage-configuration")
@require_auth
def configuration():
    return run(lambda: service.configuration(get_current_user()))


@shipment_stages_bp.post("/api/admin/shipment-stage-configuration/versions")
@require_auth
def save_configuration():
    return run(lambda: service.save_configuration(
        get_current_user(), request.get_json(silent=True), request.headers.get("Idempotency-Key"),
    ), True)


@shipment_stages_bp.get("/api/operational-shipments/<uuid:shipment_id>/operational-stages")
@require_auth
def stages(shipment_id):
    return run(lambda: service.read(str(shipment_id), get_current_user()))


@shipment_stages_bp.post("/api/operational-shipments/<uuid:shipment_id>/operational-stages/<uuid:definition_id>/events")
@require_auth
def event(shipment_id, definition_id):
    return run(lambda: service.record_event(
        str(shipment_id), str(definition_id), get_current_user(), request.get_json(silent=True),
        request.headers.get("Idempotency-Key"),
    ), True)

