"""Owner-only delivery commands and existing authorized Shipment reads."""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import delivery_service as service
from backend.services.operational_service import OperationalError

deliveries_bp = Blueprint("deliveries", __name__, url_prefix="/api/operational-shipments")


@deliveries_bp.after_request
def no_store(response):
    response.cache_control.no_store = True
    return response


@deliveries_bp.get("/<uuid:shipment_id>/deliveries")
@require_auth
def listing(shipment_id):
    try:
        return jsonify({"data": service.listing(str(shipment_id), get_current_user(), request.args.get("page", 1))})
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status


@deliveries_bp.post("/<uuid:shipment_id>/deliveries")
@require_auth
def create(shipment_id):
    try:
        row, created = service.create(str(shipment_id), get_current_user(), request.get_json(silent=True), request.headers.get("Idempotency-Key"))
        result = {"public_id": row.public_id, "revision": row.revision, "created": created}
        db.session.commit()
        return jsonify(result), 201 if created else 200
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": {"code": "DELIVERY_CONFLICT", "message": "تحویل هم‌زمان تغییر کرده است؛ دوباره بخوانید."}}), 409
