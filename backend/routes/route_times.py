"""Same-tenant reference administration and explicit route-plan consumption."""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import route_time_service as service
from backend.services.operational_service import OperationalError

route_times_bp = Blueprint("route_times", __name__)


@route_times_bp.after_request
def no_store(response):
    response.cache_control.no_store = True
    return response


def run(action, write=False):
    try:
        result = action()
        if write:
            row, created = result
            data = {"public_id": row.public_id, "created": created}
            db.session.commit()
            return jsonify({"data": data}), 201 if created else 200
        return jsonify({"data": result})
    except OperationalError as exc:
        db.session.rollback()
        return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": {"code": "ROUTE_TIME_CONFLICT", "message": "اطلاعات هم‌زمان تغییر کرده است؛ دوباره بخوانید."}}), 409


@route_times_bp.get("/api/organization/route-reference-times")
@require_auth
def listing():
    return run(lambda: service.listing(get_current_user(), request.args.get("page", 1)))


@route_times_bp.post("/api/admin/organization-route-reference-times")
@require_auth
def create():
    return run(lambda: service.save(get_current_user(), request.get_json(silent=True), request.headers.get("Idempotency-Key")), True)


@route_times_bp.post("/api/admin/organization-route-reference-times/<uuid:reference_id>/versions")
@require_auth
def version(reference_id):
    return run(lambda: service.save(get_current_user(), request.get_json(silent=True), request.headers.get("Idempotency-Key"), str(reference_id)), True)


@route_times_bp.get("/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/reference-times")
@require_auth
def plan_read(shipment_id, plan_id):
    return run(lambda: service.plan_read(str(shipment_id), plan_id, get_current_user()))


@route_times_bp.post("/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/legs/<int:leg_id>/reference-time")
@require_auth
def select_basis(shipment_id, plan_id, leg_id):
    return run(lambda: service.select_basis(str(shipment_id), plan_id, leg_id, get_current_user(), request.get_json(silent=True), request.headers.get("Idempotency-Key")), True)
