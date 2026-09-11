"""Opaque project/unit APIs for expert and customer Release 1.2.0 tracking."""
from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.extensions import db
from backend.operational_models import Project
from backend.security import require_auth
from backend.services import execution_unit_service as service
from backend.services import shared_transport_service as shared_transport
from backend.services.operational_service import OperationalError
from sqlalchemy import select

execution_units_bp=Blueprint("execution_units",__name__)

def _error(exc): return jsonify({"error":{"code":exc.code,"message":exc.message}}),exc.status
def _user():
    user=get_current_user()
    if not user: raise OperationalError("FORBIDDEN_OPERATION","Authentication is required.",401)
    return user

@execution_units_bp.get("/api/v2/projects/<project_id>/execution-units")
@require_auth
def expert_list(project_id):
    try: return jsonify(service.list_units(service.scoped_project(project_id,_user()),request.args))
    except OperationalError as exc: return _error(exc)

@execution_units_bp.post("/api/v2/projects/<project_id>/execution-units")
@require_auth
def expert_create(project_id):
    try:
        user=_user(); project=service.scoped_project(project_id,user,"execution_unit.create"); unit=service.create_unit(project,request.get_json(silent=True) or {},user); db.session.commit(); return jsonify({"data":service.unit_projection(unit)}),201
    except OperationalError as exc: db.session.rollback(); return _error(exc)

@execution_units_bp.get("/api/v2/projects/<project_id>/execution-units/<unit_id>")
@require_auth
def expert_detail(project_id,unit_id):
    try:
        project=service.scoped_project(project_id,_user()); return jsonify({"data":service.unit_projection(service.scoped_unit(project,unit_id))})
    except OperationalError as exc: return _error(exc)

@execution_units_bp.patch("/api/v2/projects/<project_id>/execution-units/<unit_id>")
@require_auth
def expert_update(project_id,unit_id):
    try:
        project=service.scoped_project(project_id,_user(),"execution_unit.update"); unit=service.update_unit(service.scoped_unit(project,unit_id),request.get_json(silent=True) or {}); db.session.commit(); return jsonify({"data":service.unit_projection(unit)})
    except OperationalError as exc: db.session.rollback(); return _error(exc)

@execution_units_bp.get("/api/v2/projects/<project_id>/execution-units/<unit_id>/timeline")
@require_auth
def expert_timeline(project_id,unit_id):
    try:
        project=service.scoped_project(project_id,_user()); return jsonify(service.timeline(service.scoped_unit(project,unit_id),request.args))
    except OperationalError as exc: return _error(exc)

@execution_units_bp.post("/api/v2/projects/<project_id>/execution-units/<unit_id>/events")
@require_auth
def expert_event(project_id,unit_id):
    try:
        user=_user(); project=service.scoped_project(project_id,user,"execution_unit.update"); unit=service.scoped_unit(project,unit_id); event,created=service.create_event(unit,request.get_json(silent=True) or {},user,request.headers.get("Idempotency-Key","")); db.session.commit(); return jsonify({"data":{"public_id":event.public_id},"meta":{"created":created}}),201 if created else 200
    except OperationalError as exc: db.session.rollback(); return _error(exc)


# ADR-046 commands remain nested under the existing authorized project route.
# The unit itself is tenant-owned; the project path is only the existing Expert
# entry point and is checked before the shared commands execute.
def _shared_unit(project_id, unit_id, permission="execution_unit.read"):
    user = _user()
    project = service.scoped_project(project_id, user, permission)
    unit = service.scoped_unit(project, unit_id)
    return user, unit


@execution_units_bp.get("/api/v2/projects/<project_id>/execution-units/<unit_id>/shared-transport")
@require_auth
def shared_transport_detail(project_id, unit_id):
    try:
        user, unit = _shared_unit(project_id, unit_id)
        result = shared_transport.allocations(execution_public_id=unit.public_id, user=user)
        carrier = unit.carrier_customer
        result["execution"] = {
            "public_id": unit.public_id, "unit_code": unit.unit_code,
            "carrier": {"id": carrier.id, "label": carrier.company_name or f"{carrier.first_name} {carrier.last_name}".strip()} if carrier else None,
        }
        return jsonify({"data": result})
    except OperationalError as exc: return _error(exc)


@execution_units_bp.get("/api/v2/projects/<project_id>/execution-units/<unit_id>/eligible-cargo")
@require_auth
def shared_transport_eligible_cargo(project_id, unit_id):
    try:
        user, unit = _shared_unit(project_id, unit_id, "execution_unit.update")
        return jsonify({"data": shared_transport.eligible_cargo(execution_public_id=unit.public_id, user=user)})
    except OperationalError as exc: return _error(exc)


@execution_units_bp.post("/api/v2/projects/<project_id>/execution-units/<unit_id>/allocations")
@require_auth
def shared_transport_allocate(project_id, unit_id):
    try:
        user, unit = _shared_unit(project_id, unit_id, "execution_unit.update")
        payload = request.get_json(silent=True) or {}
        cargo_public_id = payload.get("cargo_public_id")
        if not isinstance(cargo_public_id, str):
            raise OperationalError("VALIDATION_FAILED", "cargo_public_id is required.", 422)
        row = shared_transport.allocate(execution_public_id=unit.public_id, cargo_public_id=cargo_public_id, allocated_quantity=payload.get("allocated_quantity"), user=user)
        db.session.commit()
        return jsonify({"data": {"public_id": row.public_id}}), 201
    except OperationalError as exc: db.session.rollback(); return _error(exc)


@execution_units_bp.delete("/api/v2/projects/<project_id>/execution-units/<unit_id>/allocations/<allocation_id>")
@require_auth
def shared_transport_release(project_id, unit_id, allocation_id):
    try:
        user, unit = _shared_unit(project_id, unit_id, "execution_unit.update")
        shared_transport.release(execution_public_id=unit.public_id, allocation_public_id=allocation_id, user=user)
        db.session.commit()
        return "", 204
    except OperationalError as exc: db.session.rollback(); return _error(exc)


@execution_units_bp.patch("/api/v2/projects/<project_id>/execution-units/<unit_id>/carrier")
@require_auth
def shared_transport_carrier(project_id, unit_id):
    try:
        user, unit = _shared_unit(project_id, unit_id, "execution_unit.update")
        payload = request.get_json(silent=True) or {}
        # Customer has no public identity in this baseline.  This endpoint does
        # not list arbitrary customers; the ID is accepted only after the UI's
        # existing authorized master-data selection flow has chosen it.
        value = payload.get("carrier_customer_id")
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise OperationalError("VALIDATION_FAILED", "carrier_customer_id must be an integer or null.", 422)
        row = shared_transport.assign_carrier(execution_public_id=unit.public_id, carrier_customer_id=value, user=user)
        db.session.commit()
        return jsonify({"data": {"public_id": row.public_id, "carrier_assigned": row.carrier_customer_id is not None}})
    except OperationalError as exc: db.session.rollback(); return _error(exc)


@execution_units_bp.get("/api/v2/projects/<project_id>/execution-units/<unit_id>/carrier-options")
@require_auth
def shared_transport_carrier_options(project_id, unit_id):
    """Active carrier candidates, constrained to the active tenant."""
    try:
        user, unit = _shared_unit(project_id, unit_id, "execution_unit.update")
        return jsonify({"data": shared_transport.active_customers(execution_public_id=unit.public_id, user=user)})
    except OperationalError as exc: return _error(exc)

def _public_project(code):
    project=db.session.scalar(select(Project).where(Project.tracking_code==code))
    if project is None: raise OperationalError("NOT_FOUND","Project not found.",404)
    return project

@execution_units_bp.get("/api/public/v2/projects/<tracking_code>/summary")
def public_summary(tracking_code):
    try: return jsonify({"data":service.summary(_public_project(tracking_code))})
    except OperationalError as exc: return _error(exc)

@execution_units_bp.get("/api/public/v2/projects/<tracking_code>/execution-units")
def public_list(tracking_code):
    try: return jsonify(service.list_units(_public_project(tracking_code),request.args,customer=True))
    except OperationalError as exc: return _error(exc)

@execution_units_bp.get("/api/public/v2/projects/<tracking_code>/execution-units/<unit_id>")
def public_detail(tracking_code,unit_id):
    try:
        project=_public_project(tracking_code); unit=service.scoped_unit(project,unit_id)
        if not unit.is_active: raise OperationalError("NOT_FOUND","Execution unit not found.",404)
        return jsonify({"data":service.unit_projection(unit,customer=True)})
    except OperationalError as exc: return _error(exc)

@execution_units_bp.get("/api/public/v2/projects/<tracking_code>/execution-units/<unit_id>/timeline")
def public_timeline(tracking_code,unit_id):
    try:
        project=_public_project(tracking_code); unit=service.scoped_unit(project,unit_id)
        if not unit.is_active: raise OperationalError("NOT_FOUND","Execution unit not found.",404)
        return jsonify(service.timeline(unit,request.args,customer=True))
    except OperationalError as exc: return _error(exc)
