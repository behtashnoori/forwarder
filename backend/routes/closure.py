"""Explicit closure configuration, current assessment and authorized commands."""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import DBAPIError
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import closure_service as service
from backend.services.operational_service import OperationalError

closure_bp = Blueprint("closure", __name__)


@closure_bp.after_request
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
    except DBAPIError as exc:
        db.session.rollback()
        if getattr(exc.orig, "sqlstate", getattr(exc.orig, "pgcode", None)) not in {"40001", "40P01", "23505", "23514"}:
            raise
        return jsonify({"error": {"code": "CLOSURE_CONFLICT", "message": "اطلاعات هم‌زمان تغییر کرد؛ دوباره بررسی کنید."}}), 409


@closure_bp.get("/api/admin/closure-policy")
@require_auth
def configuration():
    return run(lambda: service.configuration(get_current_user()))


@closure_bp.post("/api/admin/closure-policy/versions")
@require_auth
def version():
    return run(lambda: service.save_policy(get_current_user(), request.get_json(silent=True), request.headers.get("Idempotency-Key")), True)


@closure_bp.get("/api/operational-shipments/<uuid:shipment_id>/closure")
@require_auth
def assessment(shipment_id):
    return run(lambda: service.read(str(shipment_id), get_current_user()))


@closure_bp.post("/api/operational-shipments/<uuid:shipment_id>/close")
@require_auth
def close(shipment_id):
    return run(lambda: service.close(str(shipment_id), get_current_user(), request.get_json(silent=True), request.headers.get("Idempotency-Key")), True)
