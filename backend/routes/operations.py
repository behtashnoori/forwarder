"""Phase 1A operational shipment and work-queue HTTP API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
from sqlalchemy import exists, or_, select

from backend.auth import get_current_user
from backend.extensions import db
from backend.models import Customer
from backend.operational_models import (
    Milestone,
    OperationalCheckpoint,
    OperationalShipment,
    OperationalWorkItem,
    RouteLeg,
    RoutePlan,
)
from backend.security import require_auth
from backend.services import operational_service as service
from backend.services import operational_action_service as actions
from backend.services import organization_sla_service as organization_sla
from backend.services import operational_workspace_service as workspace
from backend.services import route_orchestration_service as routes
from backend.services import transport_execution_service as transport_executions
from backend.services import external_reference_service as external_references
from backend.services.shipment_request_identity_service import resolve_tenant_request_by_public_id
from backend.services.shipment_population_service import (
    OperationalWindow,
    operational_shipment_population,
    parse_transport_datetime,
)


operations_bp = Blueprint("operations", __name__)


def _reference_owner(kind: str, public_id: str, *, manage: bool = False):
    if kind == "shipment":
        owner = external_references.scoped_shipment(public_id, _user(), manage=manage)
        return owner, owner.organization_id
    return external_references.scoped_unit(public_id, _user(), manage=manage)


@operations_bp.get("/api/internal/external-reference-types/shipment-eligible")
@require_auth
def shipment_eligible_external_reference_types():
    try:
        service.require_permission(_user(), "operational_shipment.read")
        return jsonify({"data": external_references.eligible_types_for_shipment()})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get(
    "/api/internal/operational-shipments/<shipment_public_id>/external-references"
)
@require_auth
def shipment_external_references(shipment_public_id: str):
    try:
        owner, _ = _reference_owner("shipment", shipment_public_id)
        return jsonify(
            {
                "data": external_references.list_for_owner(
                    "shipment",
                    owner.id,
                    active_only=request.args.get("active_only") == "true",
                )
            }
        )
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post(
    "/api/internal/operational-shipments/<shipment_public_id>/external-references"
)
@require_auth
def create_shipment_external_reference(shipment_public_id: str):
    try:
        owner, org = _reference_owner("shipment", shipment_public_id, manage=True)
        row, created = external_references.create(
            "shipment",
            owner,
            org,
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify(
            {"data": external_references.serialize(row), "meta": {"created": created}}
        ), 201 if created else 200
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/internal/operational-shipments/<shipment_public_id>/external-references/<reference_public_id>/<action>"
)
@require_auth
def transition_shipment_external_reference(
    shipment_public_id: str, reference_public_id: str, action: str
):
    try:
        if action not in {"supersede", "cancel"}:
            raise service.OperationalError(
                "RESOURCE_NOT_FOUND", "Resource not found.", 404
            )
        owner, org = _reference_owner("shipment", shipment_public_id, manage=True)
        row = external_references.transition(
            "shipment",
            owner.id,
            org,
            reference_public_id,
            request.get_json(silent=True) or {},
            _user(),
            action,
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify({"data": external_references.serialize(row)})
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get("/api/internal/execution-units/<unit_public_id>/external-references")
@require_auth
def execution_unit_external_references(unit_public_id: str):
    try:
        owner, _ = _reference_owner("unit", unit_public_id)
        return jsonify(
            {
                "data": external_references.list_for_owner(
                    "unit",
                    owner.id,
                    active_only=request.args.get("active_only") == "true",
                )
            }
        )
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post(
    "/api/internal/execution-units/<unit_public_id>/external-references"
)
@require_auth
def create_execution_unit_external_reference(unit_public_id: str):
    try:
        owner, org = _reference_owner("unit", unit_public_id, manage=True)
        row, created = external_references.create(
            "unit",
            owner,
            org,
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify(
            {"data": external_references.serialize(row), "meta": {"created": created}}
        ), 201 if created else 200
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/internal/execution-units/<unit_public_id>/external-references/<reference_public_id>/<action>"
)
@require_auth
def transition_execution_unit_external_reference(
    unit_public_id: str, reference_public_id: str, action: str
):
    try:
        if action not in {"supersede", "cancel"}:
            raise service.OperationalError(
                "RESOURCE_NOT_FOUND", "Resource not found.", 404
            )
        owner, org = _reference_owner("unit", unit_public_id, manage=True)
        row = external_references.transition(
            "unit",
            owner.id,
            org,
            reference_public_id,
            request.get_json(silent=True) or {},
            _user(),
            action,
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify({"data": external_references.serialize(row)})
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get("/api/internal/external-references/search")
@require_auth
def search_external_references():
    try:
        return jsonify(external_references.search(request.args, _user()))
    except (service.OperationalError, ValueError) as exc:
        if isinstance(exc, service.OperationalError):
            return _error(exc)
        return _error(
            service.OperationalError("VALIDATION_FAILED", "Invalid search parameters.")
        )


def _error(exc: service.OperationalError):
    return jsonify(
        {"error": {"code": exc.code, "message": exc.message, "fields": []}}
    ), exc.status


def _user():
    user = get_current_user()
    if not user:
        raise service.OperationalError(
            "FORBIDDEN_OPERATION", "Authentication is required.", 401
        )
    return user


@operations_bp.get("/api/operational-context")
@require_auth
def context():
    try:
        return jsonify({"data": service.operational_context(_user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/operational-workspace")
@require_auth
def operational_workspace():
    try:
        return jsonify(workspace.snapshot(_user(), request.args.get("limit")))
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/organization-sla-rules")
@require_auth
def organization_sla_rules():
    try:
        return jsonify({"data": organization_sla.list_rules(_user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post("/api/organization-sla-rules")
@require_auth
def organization_sla_rule_create():
    try:
        return jsonify(
            {"data": organization_sla.create_rule(request.get_json(silent=True) or {}, _user())}
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.patch("/api/organization-sla-rules/<uuid:rule_id>")
@require_auth
def organization_sla_rule_update(rule_id):
    try:
        return jsonify(
            {
                "data": organization_sla.update_rule(
                    str(rule_id), request.get_json(silent=True) or {}, _user()
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get("/api/organization-sla-rules/<uuid:rule_id>/history")
@require_auth
def organization_sla_rule_history(rule_id):
    try:
        return jsonify({"data": organization_sla.rule_history(str(rule_id), _user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/operational-shipments/<uuid:shipment_id>/actions")
@require_auth
def operational_actions(shipment_id):
    try:
        return jsonify({"data": actions.list_actions(str(shipment_id), _user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post("/api/operational-shipments/<uuid:shipment_id>/actions")
@require_auth
def operational_action_create(shipment_id):
    try:
        return jsonify(
            {
                "data": actions.create_action(
                    str(shipment_id), request.get_json(silent=True) or {}, _user()
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/actions/<uuid:action_id>/follow-ups"
)
@require_auth
def operational_action_follow_up(shipment_id, action_id):
    try:
        return jsonify(
            {
                "data": actions.record_follow_up(
                    str(shipment_id),
                    str(action_id),
                    request.get_json(silent=True) or {},
                    _user(),
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/actions/<uuid:action_id>/resolve"
)
@require_auth
def operational_action_resolve(shipment_id, action_id):
    try:
        return jsonify(
            {
                "data": actions.resolve_action(
                    str(shipment_id),
                    str(action_id),
                    request.get_json(silent=True) or {},
                    _user(),
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get(
    "/api/operational-shipments/<uuid:shipment_id>/actions/<uuid:action_id>/history"
)
@require_auth
def operational_action_history(shipment_id, action_id):
    try:
        return jsonify(
            {
                "data": actions.action_history(
                    str(shipment_id), str(action_id), _user()
                )
            }
        )
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/operations/selectors/customers")
@require_auth
def selector_customers():
    try:
        return jsonify(service.customer_selector(request.args, _user()))
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/operations/selectors/projects")
@require_auth
def selector_projects():
    try:
        return jsonify(service.project_selector(request.args, _user()))
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/operations/selectors/accepted-quotes")
@require_auth
def selector_accepted_quotes():
    try:
        return jsonify(service.accepted_quote_selector(request.args, _user()))
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post("/api/operational-shipments/from-accepted-quote")
@require_auth
def create_from_quote():
    try:
        shipment, created = service.create_from_accepted_quote(
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify(
            {"data": service.shipment_graph(shipment), "meta": {"created": created}}
        ), 201 if created else 200
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post("/api/operational-shipments")
@require_auth
def create_direct():
    try:
        shipment, created = service.create_direct(
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify(
            {
                "data": service.shipment_graph(shipment),
                "meta": {"created": created, "replayed": not created},
            }
        ), 201 if created else 200
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get("/api/operational-shipments")
@require_auth
def list_shipments():
    try:
        user = _user()
        service.require_permission(user, "operational_shipment.read")
        org = service.organization_for_user(user["id"])
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
        window = OperationalWindow(
            from_=parse_transport_datetime(request.args.get("date_from"), "date_from"),
            to=parse_transport_datetime(request.args.get("date_to"), "date_to"),
        )
        query = operational_shipment_population(
            user, status=request.args.get("status") or None, window=window
        ).order_by(None)
        active = request.args.get("active")
        if active not in {None, "true", "false"}:
            raise service.OperationalError(
                "VALIDATION_FAILED", "active must be true or false.", 422
            )
        if active == "true":
            query = query.where(
                OperationalShipment.lifecycle_status.in_(("planned", "in_progress"))
            )
        elif active == "false":
            query = query.where(
                OperationalShipment.lifecycle_status.in_(("completed", "cancelled"))
            )
        customer = request.args.get("customer", "").strip()
        if customer:
            pattern = f"%{customer}%"
            query = query.join(
                Customer, Customer.id == OperationalShipment.customer_id
            ).where(
                or_(
                    Customer.company_name.ilike(pattern),
                    Customer.first_name.ilike(pattern),
                    Customer.last_name.ilike(pattern),
                    Customer.phone.ilike(pattern),
                    Customer.mobile.ilike(pattern),
                )
            )
        if request.args.get("customer_id", type=int):
            query = query.where(
                OperationalShipment.customer_id
                == request.args.get("customer_id", type=int)
            )
        if request.args.get("request_id", type=int):
            query = query.where(
                OperationalShipment.shipment_request_id
                == request.args.get("request_id", type=int)
            )
        request_public_id = request.args.get("request_public_id", "").strip()
        if request_public_id:
            parent = resolve_tenant_request_by_public_id(org, request_public_id)
            if not parent:
                return jsonify({"data": [], "meta": {"page": page, "has_more": False}})
            query = query.where(OperationalShipment.shipment_request_id == parent.id)
        if request.args.get("accepted_quote_id", type=int):
            query = query.where(
                OperationalShipment.accepted_quote_id
                == request.args.get("accepted_quote_id", type=int)
            )
        query = query.join(
            RoutePlan,
            (RoutePlan.operational_shipment_id == OperationalShipment.id)
            & RoutePlan.is_active.is_(True),
        ).join(RouteLeg, RouteLeg.route_plan_id == RoutePlan.id)
        if request.args.get("origin"):
            query = query.where(
                RouteLeg.origin_snapshot["display_name"].as_string().ilike(
                    f"%{request.args['origin'].strip()}%"
                )
            )
        if request.args.get("destination"):
            query = query.where(
                RouteLeg.destination_snapshot["display_name"].as_string().ilike(
                    f"%{request.args['destination'].strip()}%"
                )
            )
        if request.args.get("overdue") in {"true", "false"}:
            overdue = exists(
                select(Milestone.id).where(
                    Milestone.route_leg_id == RouteLeg.id,
                    Milestone.verification_state != "verified",
                    Milestone.planned_at < datetime.now(timezone.utc),
                )
            )
            query = query.where(
                overdue if request.args["overdue"] == "true" else ~overdue
            )
        query = query.distinct()
        rows = db.session.scalars(
            query.order_by(
                OperationalShipment.created_at.desc(),
                OperationalShipment.public_id.asc(),
            )
            .offset((page - 1) * per_page)
            .limit(per_page + 1)
        ).all()
        has_more = len(rows) > per_page
        return jsonify(
            {
                "data": [service.shipment_graph(row) for row in rows[:per_page]],
                "meta": {"page": page, "per_page": per_page, "has_more": has_more},
            }
        )
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/operational-shipments/<uuid:shipment_id>")
@require_auth
def shipment_detail(shipment_id: int):
    try:
        return jsonify(
            {
                "data": service.shipment_graph(
                    service.scoped_shipment(shipment_id, _user())
                )
            }
        )
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get("/api/operational-shipments/<uuid:shipment_id>/route-plans")
@require_auth
def route_plan_list(shipment_id):
    try:
        return jsonify({"data": routes.list_plans(shipment_id, _user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post("/api/operational-shipments/<uuid:shipment_id>/route-plans")
@require_auth
def route_plan_create(shipment_id):
    try:
        return jsonify(
            {
                "data": routes.create_plan(
                    shipment_id, request.get_json(silent=True) or {}, _user()
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>"
)
@require_auth
def route_plan_get(shipment_id, plan_id):
    try:
        return jsonify({"data": routes.get_plan(shipment_id, plan_id, _user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get(
    "/api/operational-shipments/<uuid:shipment_id>/transport-execution-options"
)
@require_auth
def transport_execution_options(shipment_id):
    try:
        return jsonify(
            {"data": transport_executions.options(str(shipment_id), _user())}
        )
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.get(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/transport-executions"
)
@require_auth
def route_transport_execution_list(shipment_id, plan_id):
    try:
        return jsonify(
            {
                "data": transport_executions.list_for_plan(
                    str(shipment_id), plan_id, _user()
                )
            }
        )
    except service.OperationalError as exc:
        return _error(exc)


def _execution_from_plan(payload: dict, execution_public_id: str) -> dict:
    for stage in payload["stages"]:
        for execution in stage["executions"]:
            if execution["execution_public_id"] == execution_public_id:
                return execution
    raise service.OperationalError(
        "TRANSPORT_EXECUTION_NOT_FOUND", "Transport execution was not found.", 404
    )


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/legs/<int:leg_id>/transport-executions"
)
@require_auth
def route_transport_execution_create(shipment_id, plan_id, leg_id):
    try:
        row, created = transport_executions.create(
            str(shipment_id),
            plan_id,
            leg_id,
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        execution_public_id = row.execution_unit.public_id
        db.session.commit()
        snapshot = transport_executions.list_for_plan(
            str(shipment_id), plan_id, _user()
        )
        return jsonify(
            {
                "data": _execution_from_plan(snapshot, execution_public_id),
                "meta": {"created": created},
            }
        ), 201 if created else 200
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/transport-executions/<uuid:execution_id>/revisions"
)
@require_auth
def route_transport_execution_revise(shipment_id, plan_id, execution_id):
    try:
        _, _, created = transport_executions.revise(
            str(shipment_id),
            plan_id,
            str(execution_id),
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        db.session.commit()
        snapshot = transport_executions.list_for_plan(
            str(shipment_id), plan_id, _user()
        )
        return jsonify(
            {
                "data": _execution_from_plan(snapshot, str(execution_id)),
                "meta": {"created": created},
            }
        ), 201 if created else 200
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/validate"
)
@require_auth
def route_plan_validate(shipment_id, plan_id):
    try:
        return jsonify({"data": routes.validate_plan(shipment_id, plan_id, _user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/activate"
)
@require_auth
def route_plan_activate(shipment_id, plan_id):
    try:
        return jsonify(
            {
                "data": routes.activate_plan(
                    shipment_id, plan_id, request.get_json(silent=True) or {}, _user()
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/replan"
)
@require_auth
def route_plan_replan(shipment_id, plan_id):
    try:
        return jsonify(
            {
                "data": routes.replan(
                    shipment_id,
                    plan_id,
                    request.get_json(silent=True) or {},
                    _user(),
                    request.headers.get("Idempotency-Key", ""),
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/legs"
)
@require_auth
def route_leg_create(shipment_id, plan_id):
    try:
        return jsonify(
            {
                "data": routes.add_leg(
                    shipment_id, plan_id, request.get_json(silent=True) or {}, _user()
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.patch(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/legs/<int:leg_id>"
)
@require_auth
def route_leg_update(shipment_id, plan_id, leg_id):
    try:
        return jsonify(
            {
                "data": routes.update_leg(
                    shipment_id,
                    plan_id,
                    leg_id,
                    request.get_json(silent=True) or {},
                    _user(),
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.delete(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/legs/<int:leg_id>"
)
@require_auth
def route_leg_delete(shipment_id, plan_id, leg_id):
    try:
        routes.delete_leg(shipment_id, plan_id, leg_id, _user())
        return "", 204
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.put(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/cargo-destinations/<uuid:cargo_public_id>"
)
@require_auth
def route_cargo_destination_put(shipment_id, plan_id, cargo_public_id):
    try:
        return jsonify(
            {
                "data": routes.assign_cargo_destination(
                    shipment_id,
                    plan_id,
                    cargo_public_id,
                    request.get_json(silent=True) or {},
                    _user(),
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/actual-route"
)
@require_auth
def route_actual_traversal_create(shipment_id, plan_id):
    try:
        return jsonify(
            {
                "data": routes.record_traversal(
                    shipment_id,
                    plan_id,
                    request.get_json(silent=True) or {},
                    _user(),
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/checkpoints"
)
@require_auth
def checkpoint_create(shipment_id, plan_id):
    try:
        return jsonify(
            {
                "data": routes.add_checkpoint(
                    shipment_id, plan_id, request.get_json(silent=True) or {}, _user()
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.patch(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/checkpoints/<int:checkpoint_id>"
)
@require_auth
def checkpoint_update(shipment_id, plan_id, checkpoint_id):
    try:
        return jsonify(
            {
                "data": routes.update_checkpoint(
                    shipment_id,
                    plan_id,
                    checkpoint_id,
                    request.get_json(silent=True) or {},
                    _user(),
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-plans/<int:plan_id>/dependencies"
)
@require_auth
def dependency_create(shipment_id, plan_id):
    try:
        return jsonify(
            {
                "data": routes.add_dependency(
                    shipment_id, plan_id, request.get_json(silent=True) or {}, _user()
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


def _checkpoint_action(shipment_id, checkpoint_id, action):
    try:
        return jsonify(
            {
                "data": routes.checkpoint_command(
                    shipment_id,
                    checkpoint_id,
                    request.get_json(silent=True) or {},
                    _user(),
                    request.headers.get("Idempotency-Key", ""),
                    action,
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/checkpoints/<int:checkpoint_id>/arrive"
)
@require_auth
def checkpoint_arrive(shipment_id, checkpoint_id):
    return _checkpoint_action(shipment_id, checkpoint_id, "arrive")


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/checkpoints/<int:checkpoint_id>/complete-processing"
)
@require_auth
def checkpoint_processing(shipment_id, checkpoint_id):
    return _checkpoint_action(shipment_id, checkpoint_id, "complete_processing")


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/checkpoints/<int:checkpoint_id>/depart"
)
@require_auth
def checkpoint_depart(shipment_id, checkpoint_id):
    return _checkpoint_action(shipment_id, checkpoint_id, "depart")


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/checkpoints/<int:checkpoint_id>/milestones/<int:milestone_id>/verify"
)
@require_auth
def checkpoint_milestone_verify(shipment_id, checkpoint_id, milestone_id):
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(
            {
                "data": routes.verify_checkpoint_milestone(
                    shipment_id,
                    checkpoint_id,
                    milestone_id,
                    payload.get("expected_version"),
                    _user(),
                    request.headers.get("Idempotency-Key", ""),
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/checkpoints/<int:checkpoint_id>/milestones/<int:milestone_id>/correct"
)
@require_auth
def checkpoint_milestone_correct(shipment_id, checkpoint_id, milestone_id):
    try:
        return jsonify(
            {
                "data": routes.correct_checkpoint_milestone(
                    shipment_id,
                    checkpoint_id,
                    milestone_id,
                    request.get_json(silent=True) or {},
                    _user(),
                    request.headers.get("Idempotency-Key", ""),
                )
            }
        ), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get("/api/operational-shipments/<uuid:shipment_id>/timeline")
@require_auth
def route_timeline(shipment_id):
    try:
        return jsonify({"data": routes.timeline(shipment_id, _user())})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post("/api/operational-shipments/<uuid:shipment_id>/timeline/reconcile")
@require_auth
def route_timeline_reconcile(shipment_id):
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(
            {
                "data": routes.recalculate_projected_timeline(
                    shipment_id,
                    _user(),
                    payload.get("expected_route_plan_version"),
                    request.headers.get("Idempotency-Key", ""),
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/route-exceptions/reconcile"
)
@require_auth
def route_exception_reconcile(shipment_id):
    payload = request.get_json(silent=True) or {}
    try:
        idempotency_key = request.headers.get("Idempotency-Key", "")
        service._require_idempotency_key(idempotency_key)
        return jsonify(
            {
                "data": routes.reconcile_route_exceptions(
                    shipment_id,
                    _user(),
                    payload.get("expected_route_plan_version"),
                    service._parse_utc(
                        payload.get("calculation_time"), "calculation_time"
                    )
                    if payload.get("calculation_time")
                    else None,
                    idempotency_key,
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get("/api/operational-route-exceptions")
@operations_bp.get("/api/operational-shipments/<uuid:shipment_id>/route-exceptions")
@require_auth
def route_exception_list(shipment_id=None):
    try:
        data = routes.list_route_exceptions(_user(), request.args.get("status", "open"))
        if shipment_id is not None:
            shipment = service.scoped_shipment(str(shipment_id), _user())
            data = [
                row for row in data if row["shipment_public_id"] == shipment.public_id
            ]
        return jsonify({"data": data})
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post("/api/operational-route-exceptions/<int:item_id>/resolve")
@operations_bp.post("/api/route-exceptions/<int:item_id>/resolve")
@require_auth
def route_exception_resolve(item_id):
    try:
        idempotency_key = request.headers.get("Idempotency-Key", "")
        service._require_idempotency_key(idempotency_key)
        return jsonify(
            {
                "data": routes._resolve_route_exception(
                    item_id,
                    request.get_json(silent=True) or {},
                    _user(),
                    idempotency_key,
                )
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/milestones/<int:milestone_id>/events"
)
@require_auth
def record_event(shipment_id: int, milestone_id: int):
    try:
        event = service.record_event(
            shipment_id,
            milestone_id,
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify({"data": {"id": event.id, "event_type": event.event_type}}), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/milestones/<int:milestone_id>/verify"
)
@require_auth
def verify(shipment_id: int, milestone_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        row = service.verify_milestone(
            shipment_id, milestone_id, payload.get("expected_version"), _user()
        )
        return jsonify(
            {
                "data": {
                    "id": row.id,
                    "version": row.version,
                    "verification_state": row.verification_state,
                }
            }
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.post(
    "/api/operational-shipments/<uuid:shipment_id>/milestones/<int:milestone_id>/correct"
)
@require_auth
def correct(shipment_id: int, milestone_id: int):
    try:
        event = service.correct_milestone(
            shipment_id,
            milestone_id,
            request.get_json(silent=True) or {},
            _user(),
            request.headers.get("Idempotency-Key", ""),
        )
        return jsonify({"data": {"id": event.id, "event_type": event.event_type}}), 201
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)


@operations_bp.get("/api/operational-work-items")
@require_auth
def work_queue():
    try:
        user = _user()
        service.require_permission(user, "work_item.read")
        org = service.organization_for_user(user["id"])
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
        status = request.args.get("status", "open")
        from backend.services.assigned_work_authorization import assigned_shipment_scope
        allowed_shipments = select(OperationalShipment.id).where(assigned_shipment_scope(user))
        query = select(OperationalWorkItem).where(
            OperationalWorkItem.organization_id == org,
            OperationalWorkItem.operational_shipment_id.in_(allowed_shipments),
        )
        if status:
            query = query.where(OperationalWorkItem.status == status)
        if request.args.get("work_type"):
            query = query.where(
                OperationalWorkItem.work_type == request.args["work_type"]
            )
        shipment_public_id = request.args.get("shipment_public_id", "").strip()
        if shipment_public_id:
            shipment = service.scoped_shipment(shipment_public_id, user)
            query = query.where(
                OperationalWorkItem.operational_shipment_id == shipment.id
            )
        rows = db.session.scalars(
            query.order_by(OperationalWorkItem.due_at.asc())
            .offset((page - 1) * per_page)
            .limit(per_page + 1)
        ).all()
        has_more = len(rows) > per_page
        data = []
        for r in rows[:per_page]:
            graph = service.shipment_graph(
                db.session.get(OperationalShipment, r.operational_shipment_id)
            )
            milestone = db.session.get(Milestone, r.milestone_id)
            checkpoint = (
                db.session.get(OperationalCheckpoint, r.checkpoint_id)
                if r.checkpoint_id
                else None
            )
            data.append(
                {
                    "id": r.id,
                    "public_id": r.public_id,
                    "shipment_public_id": graph["public_id"],
                    "milestone_id": r.milestone_id,
                    "checkpoint_id": r.checkpoint_id,
                    "type": r.work_type,
                    "status": r.status,
                    "due_at": r.due_at.isoformat(),
                    "planned_at": (
                        milestone.planned_at if milestone else r.due_at
                    ).isoformat(),
                    "milestone_type": milestone.milestone_type
                    if milestone
                    else checkpoint.checkpoint_type
                    if checkpoint
                    else r.work_type,
                    "overdue_seconds": max(
                        0,
                        int(
                            (
                                datetime.now(timezone.utc)
                                - r.due_at.replace(
                                    tzinfo=r.due_at.tzinfo or timezone.utc
                                )
                            ).total_seconds()
                        ),
                    ),
                    "customer": graph["customer"],
                    "route_leg": graph["route_leg"],
                    "reason": r.reason,
                    "assignee_user_id": r.assignee_user_id,
                    "action_context_type": r.action_context_type,
                    "process_type": r.process_type,
                    "expected_result": r.expected_result,
                    "latest_follow_up": r.latest_follow_up,
                    "latest_follow_up_at": r.latest_follow_up_at.isoformat()
                    if r.latest_follow_up_at
                    else None,
                    "version": r.version,
                }
            )
        return jsonify(
            {
                "data": data,
                "meta": {"page": page, "per_page": per_page, "has_more": has_more},
            }
        )
    except service.OperationalError as exc:
        return _error(exc)


@operations_bp.post("/api/operational-work-items/<int:item_id>/resolve")
@require_auth
def resolve_item(item_id: int):
    try:
        item = service.resolve_work_item(
            item_id,
            (request.get_json(silent=True) or {}).get("expected_version"),
            _user(),
        )
        return jsonify(
            {"data": {"id": item.id, "status": item.status, "version": item.version}}
        )
    except service.OperationalError as exc:
        db.session.rollback()
        return _error(exc)
