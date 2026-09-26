"""Current authorized owner history and one explicitly authenticated transfer."""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import DBAPIError
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import owner_transfer_service as service
from backend.services.operational_service import OperationalError

owner_transfer_bp = Blueprint("owner_transfer", __name__)


@owner_transfer_bp.after_request
def no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


def run(action, write=False):
    try:
        value = action()
        if write:
            row,created = value
            value = {"public_id":row.public_id,"created":created}
            db.session.commit()
        return jsonify({"data":value}), 201 if write and created else 200
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error":{"code":exc.code,"message":exc.message}}), exc.status
    except DBAPIError as exc:
        db.session.rollback()
        if getattr(exc.orig,"sqlstate",getattr(exc.orig,"pgcode",None)) not in {"40001","40P01","23505","23514"}:
            raise
        return jsonify({"error":{"code":"OWNER_TRANSFER_CONFLICT","message":"اطلاعات هم‌زمان تغییر کرد؛ دوباره بررسی کنید."}}), 409


@owner_transfer_bp.get("/api/operational-shipments/<uuid:shipment_id>/owner-transfers")
@require_auth
def history(shipment_id):
    return run(lambda: service.read(str(shipment_id),get_current_user(),request.args.get("page",1)))


@owner_transfer_bp.get("/api/operational-shipments/<uuid:shipment_id>/owner-transfer-candidates")
@require_auth
def candidates(shipment_id):
    return run(lambda: service.candidates(str(shipment_id),get_current_user(),request.args.get("search",""),request.args.get("page",1)))


@owner_transfer_bp.post("/api/operational-shipments/<uuid:shipment_id>/owner-transfers")
@require_auth
def transfer(shipment_id):
    return run(lambda: service.transfer(str(shipment_id),get_current_user(),request.get_json(silent=True),request.headers.get("Idempotency-Key")),True)
