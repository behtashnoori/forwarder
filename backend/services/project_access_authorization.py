"""Canonical Project business access and Organization Admin management."""
from sqlalchemy import false, select
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, Project, ProjectAccess
from backend.services.operational_service import OperationalError, organization_for_user, require_permission


def _context(user):
    uid = int(user["id"]); org = organization_for_user(uid)
    actor = db.session.get(ExpertUser, uid)
    if not actor or not actor.is_active:
        raise OperationalError("FORBIDDEN_OPERATION", "Active user is required.", 403)
    return actor, org, uid


def authorized_project_scope(user):
    actor, org, uid = _context(user)
    tenant = Project.organization_id == org
    authority = (actor.authority or "EXPERT").upper()
    if authority == "ORGANIZATION_ADMIN":
        return tenant
    if authority != "EXPERT":
        return false()
    assigned = select(ProjectAccess.project_id).where(ProjectAccess.organization_id == org, ProjectAccess.user_id == uid)
    return tenant & Project.id.in_(assigned)


def scoped_project(public_id, user):
    row = db.session.scalar(select(Project).where(Project.public_id == public_id, authorized_project_scope(user)))
    if not row:
        raise OperationalError("NOT_FOUND", "Project not found.", 404)
    return row


def _admin_project(public_id, user):
    require_permission(user, "project_configuration.manage")
    actor, org, uid = _context(user)
    if (actor.authority or "EXPERT").upper() != "ORGANIZATION_ADMIN":
        raise OperationalError("FORBIDDEN_OPERATION", "Organization administrator authority is required.", 403)
    row = db.session.scalar(select(Project).where(Project.public_id == public_id, Project.organization_id == org))
    if not row:
        raise OperationalError("NOT_FOUND", "Project not found.", 404)
    return row, org, uid


def serialize(row):
    user = db.session.get(ExpertUser, row.user_id)
    return {"public_id": row.public_id, "username": user.username, "full_name": user.full_name, "email": user.email, "created_at": row.created_at.isoformat()}


def list_assignments(project_public_id, user):
    project, org, _ = _admin_project(project_public_id, user)
    rows = db.session.scalars(select(ProjectAccess).where(ProjectAccess.project_id == project.id, ProjectAccess.organization_id == org).order_by(ProjectAccess.created_at, ProjectAccess.public_id)).all()
    return [serialize(row) for row in rows]


def add_assignment(project_public_id, payload, user):
    if set(payload) != {"username"} or not isinstance(payload.get("username"), str):
        raise OperationalError("VALIDATION_FAILED", "username is required.", 422)
    project, org, actor_id = _admin_project(project_public_id, user)
    target = db.session.scalar(select(ExpertUser).join(OperationalMembership, OperationalMembership.user_id == ExpertUser.id).where(ExpertUser.username == payload["username"], ExpertUser.is_active.is_(True), OperationalMembership.organization_id == org, OperationalMembership.is_active.is_(True)))
    if not target:
        raise OperationalError("NOT_FOUND", "Eligible organization user not found.", 404)
    row = ProjectAccess(organization_id=org, project_id=project.id, user_id=target.id, created_by_user_id=actor_id)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise OperationalError("PROJECT_ACCESS_ALREADY_EXISTS", "Project access already exists.", 409)
    return serialize(row)


def revoke_assignment(project_public_id, assignment_public_id, user):
    project, org, _ = _admin_project(project_public_id, user)
    row = db.session.scalar(select(ProjectAccess).where(ProjectAccess.public_id == assignment_public_id, ProjectAccess.project_id == project.id, ProjectAccess.organization_id == org))
    if not row:
        raise OperationalError("NOT_FOUND", "Project access not found.", 404)
    db.session.delete(row); db.session.commit()
    return {"public_id": assignment_public_id, "revoked": True}
