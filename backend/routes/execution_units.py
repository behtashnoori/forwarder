"""Opaque project/unit APIs for expert and customer Release 1.2.0 tracking."""
from flask import Blueprint, jsonify, request
from backend.auth import get_current_user
from backend.extensions import db
from backend.operational_models import Project
from backend.security import require_auth
from backend.services import execution_unit_service as service
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
