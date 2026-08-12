"""Internal Project Configuration API (opaque identifiers only)."""

from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth, require_role
from backend.services.admin_authorization_service import require_platform_admin
from backend.models import DocumentDefinition, ServiceType
from backend.logistics_network_models import ProjectLogisticsPoint
from backend.project_configuration_models import (
    MilestoneType,
    ProjectService,
    ProjectDocumentRequirement,
    ProjectMilestoneDefinition,
)
from backend.services import project_configuration_service as svc
from backend.services.operational_service import OperationalError

project_configuration_bp = Blueprint("project_configuration", __name__)


def user():
    value = get_current_user()
    if not value:
        raise OperationalError("UNAUTHENTICATED", "Authentication is required.", 401)
    return value


def failure(exc):
    db.session.rollback()
    return jsonify({"error": {"code": exc.code, "message": exc.message}}), exc.status


def owner(project_id, manage=False):
    return svc.project(project_id, user(), manage)


def paging():
    try:
        page, per_page = int(request.args.get("page", 1)), int(request.args.get("per_page", 25))
    except (TypeError, ValueError):
        raise OperationalError("VALIDATION_FAILED", "page and per_page must be integers.", 400)
    if page < 1 or per_page < 1 or per_page > 100:
        raise OperationalError("VALIDATION_FAILED", "page must be positive and per_page must be between 1 and 100.", 400)
    q = request.args.get("q", "").strip()
    if len(q) > 160:
        raise OperationalError("VALIDATION_FAILED", "q must not exceed 160 characters.", 400)
    return page, per_page, q


@project_configuration_bp.get("/api/internal/milestone-types")
@require_auth
def types_selector():
    try:
        svc.project_permission(user())
        page, per_page, q = paging()
        query = db.session.query(MilestoneType).filter_by(is_active=True)
        if q:
            query = query.filter(or_(MilestoneType.immutable_code.ilike(f"%{q}%"), MilestoneType.fa_name.ilike(f"%{q}%"), MilestoneType.en_name.ilike(f"%{q}%")))
        total = query.count()
        rows = query.order_by(MilestoneType.display_order, MilestoneType.public_id).offset((page-1)*per_page).limit(per_page).all()
    except OperationalError as exc:
        return failure(exc)
    return jsonify(
        {
            "items": [
                {
                    "public_id": x.public_id,
                    "immutable_code": x.immutable_code,
                    "fa_name": x.fa_name,
                    "en_name": x.en_name,
                }
                for x in rows
            ], "page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page
        }
    )


@project_configuration_bp.get("/api/internal/project-configuration/service-types")
@project_configuration_bp.get("/api/internal/project-configuration/document-definitions")
@require_auth
def reference_selector():
    try:
        svc.project_permission(user())
        page, per_page, q = paging()
        documents = request.path.endswith("document-definitions")
        model = DocumentDefinition if documents else ServiceType
        query = db.session.query(model).filter(model.is_active.is_(True))
        if q:
            columns = (model.code, model.title) if documents else (model.immutable_code, model.fa_name, model.en_name)
            query = query.filter(or_(*(column.ilike(f"%{q}%") for column in columns)))
        total = query.count()
        order = model.code if documents else model.immutable_code
        rows = query.order_by(order, model.public_id).offset((page-1)*per_page).limit(per_page).all()
        items = ([{"public_id": x.public_id, "code": x.code, "title": x.title} for x in rows] if documents else [{"public_id": x.public_id, "immutable_code": x.immutable_code, "fa_name": x.fa_name, "en_name": x.en_name} for x in rows])
        return jsonify({"items": items, "page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1)//per_page})
    except OperationalError as exc:
        return failure(exc)


@project_configuration_bp.get("/api/v2/projects/<project_id>/configuration/selectors/logistics-points")
@require_auth
def logistics_point_selector(project_id):
    try:
        own = owner(project_id)
        page, per_page, q = paging()
        query = db.session.query(ProjectLogisticsPoint).filter_by(project_id=own.id, is_active=True)
        if q:
            query = query.filter(ProjectLogisticsPoint.display_label.ilike(f"%{q}%"))
        total = query.count()
        rows = query.order_by(ProjectLogisticsPoint.sequence_number, ProjectLogisticsPoint.public_id).offset((page-1)*per_page).limit(per_page).all()
        return jsonify({"items": [{"public_id": x.public_id, "project_role": x.project_role, "sequence_number": x.sequence_number, "display_label": x.display_label} for x in rows], "page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1)//per_page})
    except OperationalError as exc:
        return failure(exc)


@project_configuration_bp.route("/api/admin/milestone-types", methods=["GET", "POST"])
@require_platform_admin()
def types_collection():
    try:
        if request.method == "GET":
            rows = (
                db.session.query(MilestoneType)
                .order_by(MilestoneType.display_order)
                .all()
            )
            return jsonify(
                {
                    "items": [
                        {
                            "public_id": x.public_id,
                            "immutable_code": x.immutable_code,
                            "fa_name": x.fa_name,
                            "en_name": x.en_name,
                            "definition": x.definition,
                            "display_order": x.display_order,
                            "is_active": x.is_active,
                            "version": x.version,
                        }
                        for x in rows
                    ]
                }
            )
        p = request.get_json(silent=True) or {}
        code = str(p.get("immutable_code", "")).upper()
        if code not in svc.MILESTONE_CODES:
            raise OperationalError(
                "VALIDATION_FAILED", "immutable_code is not approved."
            )
        u = user()
        row = MilestoneType(
            immutable_code=code,
            fa_name=svc._text(p, "fa_name", 160),
            en_name=svc._text(p, "en_name", 160),
            definition=svc._text(p, "definition", 4000),
            display_order=max(0, int(p.get("display_order", 0))),
            created_by=u["id"],
            updated_by=u["id"],
        )
        db.session.add(row)
        svc.commit()
        return jsonify({"public_id": row.public_id}), 201
    except OperationalError as exc:
        return failure(exc)


@project_configuration_bp.route(
    "/api/admin/milestone-types/<public_id>", methods=["PATCH"]
)
@project_configuration_bp.route(
    "/api/admin/milestone-types/<public_id>/<action>", methods=["POST"]
)
@require_platform_admin()
def type_item(public_id, action=None):
    try:
        row = db.session.query(MilestoneType).filter_by(public_id=public_id).first()
        if not row:
            raise OperationalError("NOT_FOUND", "MilestoneType not found.", 404)
        p = request.get_json(silent=True) or {}
        svc._version(row, p)
        if (
            "immutable_code" in p
            and str(p["immutable_code"]).upper() != row.immutable_code
        ):
            raise OperationalError(
                "VALIDATION_FAILED", "immutable_code cannot be changed."
            )
        if action:
            if action not in {"activate", "deactivate"}:
                raise OperationalError("NOT_FOUND", "Action not found.", 404)
            row.is_active = action == "activate"
        else:
            for k, limit in (("fa_name", 160), ("en_name", 160), ("definition", 4000)):
                if k in p:
                    setattr(row, k, svc._text(p, k, limit))
            if "display_order" in p:
                row.display_order = max(0, int(p["display_order"]))
        row.version += 1
        row.updated_by = user()["id"]
        svc.commit()
        return jsonify(
            {
                "public_id": row.public_id,
                "version": row.version,
                "is_active": row.is_active,
            }
        )
    except OperationalError as exc:
        return failure(exc)


RESOURCES = {
    "services": (ProjectService, svc.create_service),
    "document-requirements": (ProjectDocumentRequirement, svc.create_document),
    "milestone-definitions": (ProjectMilestoneDefinition, svc.create_milestone),
}


@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/services", defaults={"resource": "services"}, methods=["GET", "POST"])
@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/document-requirements", defaults={"resource": "document-requirements"}, methods=["GET", "POST"])
@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/milestone-definitions", defaults={"resource": "milestone-definitions"}, methods=["GET", "POST"])
@require_auth
def collection(project_id, resource):
    try:
        if resource not in RESOURCES:
            raise OperationalError("NOT_FOUND", "Resource not found.", 404)
        model, creator = RESOURCES[resource]
        own = owner(project_id, request.method == "POST")
        if request.method == "GET":
            return jsonify(svc.list_rows(model, own, request.args))
        row = creator(own, request.get_json(silent=True) or {}, user())
        svc.commit()
        return jsonify({"item": svc.projection(row)}), 201
    except OperationalError as exc:
        return failure(exc)


@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/services/<public_id>", defaults={"resource": "services"}, methods=["GET", "PATCH"])
@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/document-requirements/<public_id>", defaults={"resource": "document-requirements"}, methods=["GET", "PATCH"])
@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/milestone-definitions/<public_id>", defaults={"resource": "milestone-definitions"}, methods=["GET", "PATCH"])
@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/services/<public_id>/<action>", defaults={"resource": "services"}, methods=["POST"])
@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/document-requirements/<public_id>/<action>", defaults={"resource": "document-requirements"}, methods=["POST"])
@project_configuration_bp.route("/api/v2/projects/<project_id>/configuration/milestone-definitions/<public_id>/<action>", defaults={"resource": "milestone-definitions"}, methods=["POST"])
@require_auth
def item(project_id, resource, public_id, action=None):
    try:
        if resource not in RESOURCES:
            raise OperationalError("NOT_FOUND", "Resource not found.", 404)
        own = owner(project_id, request.method != "GET")
        row = svc.scoped(RESOURCES[resource][0], own, public_id)
        if request.method == "GET":
            return jsonify({"item": svc.projection(row)})
        p = request.get_json(silent=True) or {}
        if action:
            if action not in {"activate", "deactivate"}:
                raise OperationalError("NOT_FOUND", "Action not found.", 404)
            svc.active(row, action == "activate", p, user())
        else:
            svc.update(row, p, user())
        svc.commit()
        return jsonify({"item": svc.projection(row)})
    except OperationalError as exc:
        return failure(exc)


@project_configuration_bp.post(
    "/api/v2/projects/<project_id>/configuration/milestone-definitions/reorder"
)
@require_auth
def reorder(project_id):
    try:
        own = owner(project_id, True)
        rows = svc.reorder(
            own, request.get_json(silent=True) or {}, user()
        )
        svc.commit()
        rows = svc.reload_milestones(own)
        return jsonify(
            {
                "items": [
                    svc.projection(x) for x in sorted(rows, key=lambda x: x.sequence)
                ]
            }
        )
    except OperationalError as exc:
        return failure(exc)
