"""Explicit customer-access configuration, exclusively same-tenant Org Admin."""
from flask import Blueprint, g, jsonify, request

from backend.extensions import db
from backend.services import customer_entitlement_service as service
from backend.services.admin_authorization_service import require_organization_admin_context
from backend.services.operational_service import OperationalError

customer_entitlements_bp = Blueprint("customer_entitlements", __name__, url_prefix="/api/admin/customer-entitlements")


@customer_entitlements_bp.after_request
def no_cache(response):
    response.cache_control.no_store = True
    return response


def _error(exc):
    db.session.rollback()
    return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status


@customer_entitlements_bp.get("")
@require_organization_admin_context(allow_platform=False)
def configuration():
    try:
        return jsonify(service.configuration(g.organization_context.organization_id, g.current_user_id))
    except OperationalError as exc:
        return _error(exc)


@customer_entitlements_bp.post("")
@require_organization_admin_context(allow_platform=False)
def grant():
    try:
        item, created = service.grant(g.organization_context.organization_id, g.current_user_id,
                                     request.get_json(silent=True), request.headers.get("Idempotency-Key"))
        return jsonify({"item": item}), 201 if created else 200
    except OperationalError as exc:
        return _error(exc)


@customer_entitlements_bp.post("/<public_id>/revoke")
@require_organization_admin_context(allow_platform=False)
def revoke(public_id):
    try:
        return jsonify({"item": service.revoke(g.organization_context.organization_id, g.current_user_id, public_id)})
    except OperationalError as exc:
        return _error(exc)
