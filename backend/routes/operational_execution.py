"""Internal opaque-ID Operational Execution API (Release 1.9.0)."""

from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import operational_execution_service as svc
from backend.services.operational_service import OperationalError

operational_execution_bp = Blueprint("operational_execution", __name__)


def user():
    row = get_current_user()
    if not row:
        raise OperationalError(
            "FORBIDDEN_OPERATION", "Authentication is required.", 401
        )
    return row


def error(exc):
    db.session.rollback()
    return jsonify(
        {"error": {"code": exc.code, "message": exc.message, "fields": getattr(exc, "fields", [])}}
    ), exc.status


@operational_execution_bp.get(
    "/api/v2/operational-shipments/<shipment_id>/execution/initialization-preview"
)
@require_auth
def preview(shipment_id):
    try:
        return jsonify({"data": svc.initialization_preview(shipment_id, user())})
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/initialize"
)
@require_auth
def initialize(shipment_id):
    try:
        rows, created = svc.initialize(
            shipment_id, request.get_json(silent=True) or {}, user()
        )
        return jsonify(
            {
                "data": [svc.milestone_projection(r) for r in rows],
                "meta": {"created": created},
            }
        ), 201 if created else 200
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.get(
    "/api/v2/operational-shipments/<shipment_id>/execution/milestones"
)
@require_auth
def milestones(shipment_id):
    try:
        return jsonify({"data": svc.list_milestones(shipment_id, user())})
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/milestones/<milestone_id>/transition"
)
@require_auth
def transition(shipment_id, milestone_id):
    try:
        return jsonify(
            {
                "data": svc.transition(
                    shipment_id,
                    milestone_id,
                    request.get_json(silent=True) or {},
                    user(),
                )
            }
        )
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/milestones/<milestone_id>/reopen"
)
@require_auth
def reopen(shipment_id, milestone_id):
    try:
        return jsonify(
            {
                "data": svc.reopen(
                    shipment_id,
                    milestone_id,
                    request.get_json(silent=True) or {},
                    user(),
                )
            }
        )
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.get(
    "/api/v2/operational-shipments/<shipment_id>/execution/events"
)
@require_auth
def events(shipment_id):
    try:
        return jsonify({"data": svc.events(shipment_id, user())})
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/milestones/<milestone_id>/events"
)
@require_auth
def create_event(shipment_id, milestone_id):
    try:
        row = svc.create_event(
            shipment_id, milestone_id, request.get_json(silent=True) or {}, user()
        )
        return jsonify({"data": {"public_id": row.public_id}}), 201
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/events/<event_id>/correct"
)
@require_auth
def correct_event(shipment_id, event_id):
    try:
        row = svc.correct_event(
            shipment_id, event_id, request.get_json(silent=True) or {}, user()
        )
        return jsonify({"data": {"public_id": row.public_id}}), 201
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/events/<event_id>/verify"
)
@require_auth
def verify(shipment_id, event_id):
    try:
        return jsonify(
            {
                "data": svc.verify_event(
                    shipment_id, event_id, request.get_json(silent=True) or {}, user()
                )
            }
        )
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.get(
    "/api/v2/operational-shipments/<shipment_id>/execution/progress"
)
@require_auth
def progress(shipment_id):
    try:
        return jsonify({"data": svc.progress(shipment_id, user())})
    except OperationalError as exc:
        return error(exc)


def condition(kind, shipment_id):
    try:
        return jsonify(
            {
                "data": svc.condition_collection(
                    kind,
                    shipment_id,
                    user(),
                    request.get_json(silent=True) or {}
                    if request.method == "POST"
                    else None,
                )
            }
        ), 201 if request.method == "POST" else 200
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.route(
    "/api/v2/operational-shipments/<shipment_id>/execution/delays",
    methods=["GET", "POST"],
)
@require_auth
def delays(shipment_id):
    return condition("delay", shipment_id)


@operational_execution_bp.route(
    "/api/v2/operational-shipments/<shipment_id>/execution/exceptions",
    methods=["GET", "POST"],
)
@require_auth
def exceptions(shipment_id):
    return condition("exception", shipment_id)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/delays/<public_id>/resolve"
)
@require_auth
def resolve_delay(shipment_id, public_id):
    try:
        return jsonify(
            {
                "data": svc.resolve_condition(
                    "delay",
                    shipment_id,
                    public_id,
                    request.get_json(silent=True) or {},
                    user(),
                )
            }
        )
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.post(
    "/api/v2/operational-shipments/<shipment_id>/execution/exceptions/<public_id>/resolve"
)
@require_auth
def resolve_exception(shipment_id, public_id):
    try:
        return jsonify(
            {
                "data": svc.resolve_condition(
                    "exception",
                    shipment_id,
                    public_id,
                    request.get_json(silent=True) or {},
                    user(),
                )
            }
        )
    except OperationalError as exc:
        return error(exc)


def reasons(kind, public_id=None):
    try:
        payload = (
            request.get_json(silent=True) or {} if request.method != "GET" else None
        )
        data = (
            svc.update_reason(kind, public_id, payload, user())
            if public_id
            else svc.reason_collection(kind, user(), payload)
        )
        return jsonify({"data": data}), 201 if request.method == "POST" else 200
    except OperationalError as exc:
        return error(exc)


@operational_execution_bp.route(
    "/api/v2/admin/reference-data/delay-reasons", methods=["GET", "POST"]
)
@require_auth
def delay_reasons():
    return reasons("delay")


@operational_execution_bp.patch(
    "/api/v2/admin/reference-data/delay-reasons/<public_id>"
)
@require_auth
def delay_reason(public_id):
    return reasons("delay", public_id)


@operational_execution_bp.route(
    "/api/v2/admin/reference-data/exception-reasons", methods=["GET", "POST"]
)
@require_auth
def exception_reasons():
    return reasons("exception")


@operational_execution_bp.patch(
    "/api/v2/admin/reference-data/exception-reasons/<public_id>"
)
@require_auth
def exception_reason(public_id):
    return reasons("exception", public_id)
