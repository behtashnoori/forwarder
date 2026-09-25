"""Organization Admin API for tenant-owned reference availability."""

from flask import Blueprint, g, jsonify, request

from backend.extensions import db
from backend.services import organization_reference_catalog_service as svc
from backend.services.admin_authorization_service import (
    require_organization_admin_context,
)
from backend.services.operational_service import OperationalError


organization_reference_catalog_bp = Blueprint(
    "organization_reference_catalog",
    __name__,
    url_prefix="/api/admin/organization-reference-catalog",
)


def _context():
    return int(g.organization_context.organization_id), int(g.current_user_id)


def _error(exc):
    db.session.rollback()
    return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status


@organization_reference_catalog_bp.get("/<resource>")
@require_organization_admin_context(allow_platform=False)
def list_resource(resource):
    try:
        organization_id, _actor_id = _context()
        return jsonify(svc.list_rows(resource, organization_id, request.args))
    except OperationalError as exc:
        return _error(exc)


@organization_reference_catalog_bp.post(
    "/<resource>/<definition_public_id>/<action>"
)
@require_organization_admin_context(allow_platform=False)
def transition_resource(resource, definition_public_id, action):
    if action not in {"activate", "deactivate"}:
        return jsonify(
            {
                "error": {
                    "code": "REFERENCE_ACTION_NOT_FOUND",
                    "message": "عملیات مرجع یافت نشد.",
                }
            }
        ), 404
    try:
        organization_id, actor_id = _context()
        payload = request.get_json(silent=True)
        if payload is None:
            payload = {}
        item, created = svc.transition(
            resource,
            definition_public_id,
            "ACTIVE" if action == "activate" else "INACTIVE",
            payload,
            organization_id,
            actor_id,
        )
        return jsonify({"item": item}), 201 if created else 200
    except OperationalError as exc:
        return _error(exc)
