"""Shipment-scoped reported operational facts, with owner-only commands."""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services.operational_service import OperationalError
from backend.services import reported_fact_service as service

reported_facts_bp = Blueprint("reported_facts", __name__, url_prefix="/api/operational-shipments")


@reported_facts_bp.after_request
def no_store(response):
    response.cache_control.no_store = True
    return response


@reported_facts_bp.get("/<uuid:shipment_id>/reported-facts")
@require_auth
def listing(shipment_id):
    try:
        return jsonify({"data": service.listing(str(shipment_id), get_current_user(), request.args.get("page", 1))})
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status


@reported_facts_bp.post("/<uuid:shipment_id>/reported-facts")
@require_auth
def create(shipment_id):
    try:
        row, created = service.create(str(shipment_id), get_current_user(), request.get_json(silent=True),
                                      request.headers.get("Idempotency-Key"))
        public_id = row.event.public_id
        db.session.commit()
        return jsonify({"public_id": public_id, "created": created}), 201 if created else 200
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": {"code": "REPORT_CONFLICT", "message": "گزارش هم‌زمان تغییر کرده است؛ دوباره بخوانید."}}), 409
