"""Organization-scoped Project Configuration application service."""

from math import ceil
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from backend.extensions import db
from backend.models import DocumentDefinition, ServiceType
from backend.operational_models import Project, utcnow
from backend.logistics_network_models import ProjectLogisticsPoint
from backend.project_configuration_models import (
    DURATION_UNITS,
    REQUIREMENT_LEVELS,
    MilestoneType,
    ProjectDocumentRequirement,
    ProjectMilestoneDefinition,
    ProjectService,
)
from backend.services.operational_service import (
    OperationalError,
    organization_for_user,
    require_permission,
)

MILESTONE_CODES = frozenset(
    {
        "REQUEST_RECEIVED",
        "CARGO_READY",
        "PICKUP",
        "LOADING",
        "DEPARTURE",
        "BORDER_ARRIVAL",
        "CUSTOMS_START",
        "CUSTOMS_COMPLETE",
        "PORT_ARRIVAL",
        "DISCHARGE",
        "DELIVERY",
        "COMPLETION",
        "OTHER_GOVERNED",
    }
)


def project_permission(user):
    require_permission(user, "project_configuration.read")


def _text(p, key, limit):
    v = p.get(key)
    if v is None:
        return None
    if not isinstance(v, str) or len(v.strip()) > limit:
        raise OperationalError("VALIDATION_FAILED", f"{key} is invalid.")
    return v.strip() or None


def _version(row, p):
    if p.get("version") != row.version:
        raise OperationalError(
            "VERSION_CONFLICT", "version does not match the current resource.", 409
        )


def project(public_id, user, manage=False):
    require_permission(
        user, "project_configuration.manage" if manage else "project_configuration.read"
    )
    org = organization_for_user(user["id"])
    row = db.session.scalar(
        select(Project).where(
            Project.public_id == public_id, Project.organization_id == org
        )
    )
    if not row:
        raise OperationalError("NOT_FOUND", "Project not found.", 404)
    return row


def scoped(model, owner, public_id):
    row = db.session.scalar(
        select(model).where(model.project_id == owner.id, model.public_id == public_id)
    )
    if not row:
        raise OperationalError("NOT_FOUND", "Configuration resource not found.", 404)
    return row


def base(row):
    return {
        "public_id": row.public_id,
        "is_active": row.is_active,
        "version": row.version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def projection(row):
    out = base(row)
    if isinstance(row, ProjectService):
        out.update(
            service_type_public_id=row.service_type.public_id,
            is_primary=row.is_primary,
            is_required=row.is_required,
            display_order=row.display_order,
            display_label=row.display_label,
            notes=row.notes,
        )
    elif isinstance(row, ProjectDocumentRequirement):
        out.update(
            document_definition_public_id=row.document_definition.public_id,
            document_definition_code=row.document_definition.code,
            document_definition_title=row.document_definition.title,
            requirement_level=row.requirement_level,
            display_order=row.display_order,
            conditional_description=row.conditional_description,
            notes=row.notes,
        )
    else:
        out.update(
            milestone_type_public_id=row.milestone_type.public_id,
            milestone_type_code=row.milestone_type.immutable_code,
            sequence=row.sequence,
            is_required=row.is_required,
            project_logistics_point_public_id=row.project_logistics_point.public_id
            if row.project_logistics_point
            else None,
            display_label=row.display_label,
            target_duration_value=row.target_duration_value,
            warning_duration_value=row.warning_duration_value,
            duration_unit=row.duration_unit,
            notes=row.notes,
        )
    return out


def list_rows(model, owner, args):
    """Return an allowlisted, deterministic and bounded project list."""
    try:
        page = int(args.get("page", 1))
        per_page = int(args.get("per_page", 25))
    except (TypeError, ValueError):
        raise OperationalError("VALIDATION_FAILED", "page and per_page must be integers.", 400)
    if page < 1 or per_page < 1 or per_page > 100:
        raise OperationalError("VALIDATION_FAILED", "page must be positive and per_page must be between 1 and 100.", 400)
    active = args.get("active")
    if active not in (None, "true", "false"):
        raise OperationalError("VALIDATION_FAILED", "active must be true or false.", 400)
    sort_fields = {
        ProjectService: {"display_order": ProjectService.display_order, "created_at": ProjectService.created_at},
        ProjectDocumentRequirement: {"display_order": ProjectDocumentRequirement.display_order, "requirement_level": ProjectDocumentRequirement.requirement_level},
        ProjectMilestoneDefinition: {"sequence": ProjectMilestoneDefinition.sequence, "created_at": ProjectMilestoneDefinition.created_at},
    }[model]
    default_sort = "sequence" if model is ProjectMilestoneDefinition else "display_order"
    sort = args.get("sort", default_sort)
    direction = args.get("direction", "asc")
    if sort not in sort_fields or direction not in {"asc", "desc"}:
        raise OperationalError("VALIDATION_FAILED", "Unsupported sort field or direction.", 400)
    relationships = {
        ProjectService: (ProjectService.service_type,),
        ProjectDocumentRequirement: (ProjectDocumentRequirement.document_definition,),
        ProjectMilestoneDefinition: (
            ProjectMilestoneDefinition.milestone_type,
            ProjectMilestoneDefinition.project_logistics_point,
        ),
    }[model]
    query = select(model).where(model.project_id == owner.id).options(
        *(selectinload(relationship) for relationship in relationships)
    )
    if active is not None:
        query = query.where(model.is_active.is_(active == "true"))
    if model is ProjectService:
        if args.get("service_type_public_id"):
            query = query.join(ProjectService.service_type).where(ServiceType.public_id == args["service_type_public_id"])
        required = args.get("required")
        if required not in (None, "true", "false"):
            raise OperationalError("VALIDATION_FAILED", "required must be true or false.", 400)
        if required is not None:
            query = query.where(model.is_required.is_(required == "true"))
    elif model is ProjectDocumentRequirement and args.get("requirement_level"):
        level = args["requirement_level"].upper()
        if level not in REQUIREMENT_LEVELS:
            raise OperationalError("VALIDATION_FAILED", "requirement_level is invalid.", 400)
        query = query.where(model.requirement_level == level)
    elif model is ProjectMilestoneDefinition and args.get("milestone_type_public_id"):
        query = query.join(ProjectMilestoneDefinition.milestone_type).where(MilestoneType.public_id == args["milestone_type_public_id"])
    total = db.session.scalar(select(db.func.count()).select_from(query.order_by(None).subquery())) or 0
    column = sort_fields[sort]
    ordered = column.desc() if direction == "desc" else column.asc()
    rows = db.session.scalars(query.order_by(ordered, model.public_id).offset((page - 1) * per_page).limit(per_page)).all()
    return {"items": [projection(x) for x in rows], "page": page, "per_page": per_page, "total": total, "pages": ceil(total / per_page)}


def _common(row, p, user):
    for k, limit in (("display_label", 160), ("notes", 4000)):
        if k in p:
            setattr(row, k, _text(p, k, limit))
    row.updated_by = user["id"]
    row.updated_at = utcnow()


def create_service(owner, p, user):
    ref = db.session.scalar(
        select(ServiceType).where(
            ServiceType.public_id == p.get("service_type_public_id"),
            ServiceType.is_active.is_(True),
        )
    )
    if not ref:
        raise OperationalError("NOT_FOUND", "Active ServiceType not found.", 404)
    row = ProjectService(
        project_id=owner.id,
        service_type_id=ref.id,
        is_primary=p.get("is_primary") is True,
        is_required=p.get("is_required") is True,
        display_order=max(0, int(p.get("display_order", 0))),
        display_label=_text(p, "display_label", 160),
        notes=_text(p, "notes", 4000),
        created_by=user["id"],
        updated_by=user["id"],
    )
    db.session.add(row)
    return row


def create_document(owner, p, user):
    ref = db.session.scalar(
        select(DocumentDefinition).where(
            DocumentDefinition.public_id == p.get("document_definition_public_id"),
            DocumentDefinition.is_active.is_(True),
        )
    )
    if not ref:
        raise OperationalError("NOT_FOUND", "Active DocumentDefinition not found.", 404)
    level = str(p.get("requirement_level", "")).upper()
    if level not in REQUIREMENT_LEVELS:
        raise OperationalError("VALIDATION_FAILED", "requirement_level is invalid.")
    conditional = _text(p, "conditional_description", 4000)
    if level == "CONDITIONAL" and not conditional:
        raise OperationalError(
            "VALIDATION_FAILED", "conditional_description is required for CONDITIONAL."
        )
    row = ProjectDocumentRequirement(
        project_id=owner.id,
        document_definition_id=ref.id,
        requirement_level=level,
        display_order=max(0, int(p.get("display_order", 0))),
        conditional_description=conditional if level == "CONDITIONAL" else None,
        notes=_text(p, "notes", 4000),
        created_by=user["id"],
        updated_by=user["id"],
    )
    db.session.add(row)
    return row


def _durations(p):
    target = p.get("target_duration_value")
    warning = p.get("warning_duration_value")
    unit = p.get("duration_unit")
    if (target is not None or warning is not None) and unit not in DURATION_UNITS:
        raise OperationalError(
            "VALIDATION_FAILED", "A valid duration_unit is required."
        )
    if any(
        v is not None and (not isinstance(v, int) or v < 1) for v in (target, warning)
    ):
        raise OperationalError(
            "VALIDATION_FAILED", "Durations must be positive integers."
        )
    if target is not None and warning is not None and warning < target:
        raise OperationalError(
            "VALIDATION_FAILED",
            "warning duration must be greater than or equal to target.",
        )
    return target, warning, unit


def create_milestone(owner, p, user):
    ref = db.session.scalar(
        select(MilestoneType).where(
            MilestoneType.public_id == p.get("milestone_type_public_id"),
            MilestoneType.is_active.is_(True),
        )
    )
    if not ref:
        raise OperationalError("NOT_FOUND", "Active MilestoneType not found.", 404)
    seq = p.get("sequence")
    if not isinstance(seq, int) or seq < 1:
        raise OperationalError("VALIDATION_FAILED", "sequence must be positive.")
    point = None
    if p.get("project_logistics_point_public_id"):
        point = db.session.scalar(
            select(ProjectLogisticsPoint).where(
                ProjectLogisticsPoint.public_id
                == p["project_logistics_point_public_id"],
                ProjectLogisticsPoint.project_id == owner.id,
                ProjectLogisticsPoint.is_active.is_(True),
            )
        )
        if not point:
            raise OperationalError(
                "NOT_FOUND", "Project logistics point not found.", 404
            )
    t, w, u = _durations(p)
    row = ProjectMilestoneDefinition(
        project_id=owner.id,
        milestone_type_id=ref.id,
        sequence=seq,
        is_required=p.get("is_required") is True,
        project_logistics_point_id=point.id if point else None,
        display_label=_text(p, "display_label", 160),
        target_duration_value=t,
        warning_duration_value=w,
        duration_unit=u,
        notes=_text(p, "notes", 4000),
        created_by=user["id"],
        updated_by=user["id"],
    )
    db.session.add(row)
    return row


def update(row, p, user):
    _version(row, p)
    if isinstance(row, ProjectService):
        for k in ("is_primary", "is_required"):
            if k in p:
                setattr(row, k, p[k] is True)
        if "display_order" in p:
            row.display_order = max(0, int(p["display_order"]))
    elif isinstance(row, ProjectDocumentRequirement):
        level = str(p.get("requirement_level", row.requirement_level)).upper()
        if level not in REQUIREMENT_LEVELS:
            raise OperationalError("VALIDATION_FAILED", "requirement_level is invalid.")
        conditional = (
            _text(p, "conditional_description", 4000)
            if "conditional_description" in p
            else row.conditional_description
        )
        if level == "CONDITIONAL" and not conditional:
            raise OperationalError(
                "VALIDATION_FAILED",
                "conditional_description is required for CONDITIONAL.",
            )
        row.requirement_level = level
        row.conditional_description = conditional if level == "CONDITIONAL" else None
        if "display_order" in p:
            row.display_order = max(0, int(p["display_order"]))
    else:
        if "sequence" in p:
            if not isinstance(p["sequence"], int) or p["sequence"] < 1:
                raise OperationalError(
                    "VALIDATION_FAILED", "sequence must be positive."
                )
            row.sequence = p["sequence"]
        if "is_required" in p:
            row.is_required = p["is_required"] is True
        if "project_logistics_point_public_id" in p:
            point_public_id = p["project_logistics_point_public_id"]
            point = None
            if point_public_id:
                point = db.session.scalar(
                    select(ProjectLogisticsPoint).where(
                        ProjectLogisticsPoint.public_id == point_public_id,
                        ProjectLogisticsPoint.project_id == row.project_id,
                        ProjectLogisticsPoint.is_active.is_(True),
                    )
                )
                if not point:
                    raise OperationalError(
                        "NOT_FOUND", "Project logistics point not found.", 404
                    )
            row.project_logistics_point_id = point.id if point else None
        vals = {
            k: p.get(k, getattr(row, k))
            for k in (
                "target_duration_value",
                "warning_duration_value",
                "duration_unit",
            )
        }
        row.target_duration_value, row.warning_duration_value, row.duration_unit = (
            _durations(vals)
        )
    _common(row, p, user)
    row.version += 1
    return row


def active(row, value, p, user):
    _version(row, p)
    row.is_active = value
    row.version += 1
    _common(row, p, user)
    return row


def reorder(owner, p, user):
    items = p.get("items")
    rows = db.session.scalars(
        select(ProjectMilestoneDefinition).where(
            ProjectMilestoneDefinition.project_id == owner.id,
            ProjectMilestoneDefinition.is_active.is_(True),
        )
    ).all()
    by = {x.public_id: x for x in rows}
    if not isinstance(items, list) or {str(x.get("public_id")) for x in items} != set(
        by
    ):
        raise OperationalError(
            "VALIDATION_FAILED",
            "reorder must include every active definition exactly once.",
        )
    offset = max([x.sequence for x in rows], default=0) + len(rows) + 1
    for i, item in enumerate(items, 1):
        row = by[str(item["public_id"])]
        _version(row, item)
        row.sequence = offset + i
        row.version += 1
        row.updated_by = user["id"]
    db.session.flush()
    for i, item in enumerate(items, 1):
        by[str(item["public_id"])].sequence = i
    return list(by.values())


def reload_milestones(owner):
    """Reload reordered rows and only the relationships used by projection."""
    return db.session.scalars(
        select(ProjectMilestoneDefinition)
        .where(ProjectMilestoneDefinition.project_id == owner.id)
        .options(
            selectinload(ProjectMilestoneDefinition.milestone_type),
            selectinload(ProjectMilestoneDefinition.project_logistics_point),
        )
        .order_by(ProjectMilestoneDefinition.sequence)
    ).all()


def commit():
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise OperationalError(
            "CONFLICT", "Project Configuration constraint conflict.", 409
        ) from exc
