"""Tenant-safe ADR-041 organization adoption service."""
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from backend.extensions import db
from backend.global_logistics_point_models import (
    GlobalLogisticsPoint, GlobalLogisticsPointAlias, GlobalLogisticsPointCorridorTag,
    GlobalLogisticsPointMode, OrganizationGlobalLogisticsPointAdoption,
)
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country
from backend.operational_models import OperationalAudit
from backend.services.operational_service import OperationalError

METADATA_FIELDS = {"version", "organization_reference_code", "display_label", "notes"}


def _fail(code, message, status=400):
    raise OperationalError(code, message, status)


def _strict(payload, allowed):
    if not isinstance(payload, dict): _fail("VALIDATION_FAILED", "A JSON object is required.")
    unknown = sorted(set(payload) - allowed)
    if unknown: _fail("UNKNOWN_FIELDS", "Unknown fields are not allowed.")


def _uuid(value, message="Resource not found."):
    try: return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError): _fail("NOT_FOUND", message, 404)


def _text(payload, key, limit):
    value = payload.get(key)
    if value is None: return None
    if not isinstance(value, str): _fail("VALIDATION_FAILED", f"{key} is invalid.")
    value = value.strip()
    if len(value) > limit: _fail("VALIDATION_FAILED", f"{key} is too long.")
    return value or None


def _version(row, payload):
    if not isinstance(payload.get("version"), int): _fail("VALIDATION_FAILED", "version is required.")
    if payload["version"] != row.version: _fail("VERSION_CONFLICT", "Adoption version is stale.", 409)


def _audit(org_id, actor_id, action, row):
    db.session.add(OperationalAudit(organization_id=org_id, actor_user_id=actor_id,
        action=action, entity_type="OrganizationGlobalLogisticsPointAdoption", entity_id=row.id,
        metadata_json={"adoption_public_id": row.public_id, "global_point_public_id": row.global_point.public_id,
                       "version": row.version}))


def _commit():
    try: db.session.commit()
    except IntegrityError as exc:
        db.session.rollback(); raise OperationalError("ADOPTION_CONFLICT", "Global point is already adopted by this organization.", 409) from exc


def scoped_adoption(public_id, org_id):
    row = db.session.scalar(select(OrganizationGlobalLogisticsPointAdoption)
        .options(joinedload(OrganizationGlobalLogisticsPointAdoption.global_point))
        .where(OrganizationGlobalLogisticsPointAdoption.public_id == _uuid(public_id),
               OrganizationGlobalLogisticsPointAdoption.organization_id == org_id))
    if row is None: _fail("NOT_FOUND", "Adoption not found.", 404)
    return row


def _global(public_id):
    row = db.session.scalar(select(GlobalLogisticsPoint).where(GlobalLogisticsPoint.public_id == _uuid(public_id, "Global point not found.")))
    if row is None: _fail("NOT_FOUND", "Global point not found.", 404)
    return row


def adoption_projection(row):
    return {"public_id": row.public_id, "status": row.status,
        "organization_reference_code": row.organization_reference_code,
        "display_label": row.display_label, "notes": row.notes, "version": row.version,
        "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat(),
        "global_point_public_id": row.global_point.public_id,
        "platform_lifecycle_status": row.global_point.lifecycle_status}


def catalog_projection(point, adoption):
    if point.lifecycle_status == "DEPRECATED": state = "PLATFORM_DEPRECATED"
    elif adoption is None: state = "AVAILABLE"
    elif adoption.status == "ACTIVE": state = "ADOPTED"
    else: state = "INACTIVE_FOR_ORGANIZATION"
    return {"public_id": point.public_id, "immutable_code": point.immutable_code,
        "fa_name": point.fa_name, "en_name": point.en_name,
        "point_type": {"code": point.point_type.immutable_code, "fa_name": point.point_type.fa_name,
                       "en_name": point.point_type.en_name},
        "country": {"code": point.country.code, "fa_name": point.country.name_fa, "en_name": point.country.name_en},
        "geography": {"city": point.city_name, "region": point.region_name, "short_address": point.short_address},
        "supported_modes": sorted(x.mode_code for x in point.modes),
        "corridor_tags": sorted(x.tag_code for x in point.corridor_tags),
        "organization_state": state, "adoption": adoption_projection(adoption) if adoption else None}


def browse(args, org_id):
    adoption_join = (OrganizationGlobalLogisticsPointAdoption.global_logistics_point_id == GlobalLogisticsPoint.id) & (OrganizationGlobalLogisticsPointAdoption.organization_id == org_id)
    query = select(GlobalLogisticsPoint, OrganizationGlobalLogisticsPointAdoption).outerjoin(
        OrganizationGlobalLogisticsPointAdoption, adoption_join).where(or_(
            GlobalLogisticsPoint.lifecycle_status == "ACTIVE",
            (GlobalLogisticsPoint.lifecycle_status == "DEPRECATED") & (OrganizationGlobalLogisticsPointAdoption.id.is_not(None))))
    term = str(args.get("q", "")).strip()
    if len(term)>160: _fail("VALIDATION_FAILED", "q is too long.")
    if term:
        pattern=f"%{term}%"; query=query.where(or_(GlobalLogisticsPoint.immutable_code.ilike(pattern),
            GlobalLogisticsPoint.fa_name.ilike(pattern), GlobalLogisticsPoint.en_name.ilike(pattern),
            GlobalLogisticsPoint.aliases.any(GlobalLogisticsPointAlias.alias.ilike(pattern))))
    country=str(args.get("country","")).strip().upper()
    if country: query=query.join(GlobalLogisticsPoint.country).where(Country.code==country)
    kind=str(args.get("type","")).strip().upper()
    if kind: query=query.join(GlobalLogisticsPoint.point_type).where(LogisticsPointType.immutable_code==kind)
    mode=str(args.get("mode","")).strip().upper()
    if mode: query=query.where(GlobalLogisticsPoint.modes.any(GlobalLogisticsPointMode.mode_code==mode))
    corridor=str(args.get("corridor","")).strip().upper()
    if corridor:
        if len(corridor)>64: _fail("VALIDATION_FAILED", "corridor is invalid.")
        query=query.where(GlobalLogisticsPoint.corridor_tags.any(GlobalLogisticsPointCorridorTag.tag_code==corridor))
    state=str(args.get("adoption_state","")).strip().upper()
    if state:
        allowed={"AVAILABLE","ADOPTED","INACTIVE_FOR_ORGANIZATION","PLATFORM_DEPRECATED"}
        if state not in allowed: _fail("VALIDATION_FAILED", "adoption_state is invalid.")
        if state=="AVAILABLE": query=query.where(OrganizationGlobalLogisticsPointAdoption.id.is_(None))
        elif state=="ADOPTED": query=query.where(OrganizationGlobalLogisticsPointAdoption.status=="ACTIVE",GlobalLogisticsPoint.lifecycle_status=="ACTIVE")
        elif state=="INACTIVE_FOR_ORGANIZATION": query=query.where(OrganizationGlobalLogisticsPointAdoption.status=="INACTIVE",GlobalLogisticsPoint.lifecycle_status=="ACTIVE")
        else: query=query.where(GlobalLogisticsPoint.lifecycle_status=="DEPRECATED",OrganizationGlobalLogisticsPointAdoption.id.is_not(None))
    try: page=max(1,int(args.get("page",1))); per_page=min(100,max(1,int(args.get("per_page",20))))
    except (TypeError,ValueError): _fail("VALIDATION_FAILED", "pagination is invalid.")
    total=db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows=db.session.execute(query.order_by(GlobalLogisticsPoint.immutable_code).offset((page-1)*per_page)
        .limit(per_page).execution_options(populate_existing=True)).all()
    return {"items":[catalog_projection(p,a) for p,a in rows],"page":page,"per_page":per_page,
            "pages":((total+per_page-1)//per_page),"total":total}


def adopt(global_public_id, payload, org_id, actor_id):
    _strict(payload, {"organization_reference_code","display_label","notes"})
    point=_global(global_public_id)
    if point.lifecycle_status!="ACTIVE" or point.verification_status!="VERIFIED":
        _fail("GLOBAL_POINT_INELIGIBLE", "Only ACTIVE verified global points may be adopted.", 409)
    if db.session.scalar(select(OrganizationGlobalLogisticsPointAdoption.id).where(
        OrganizationGlobalLogisticsPointAdoption.organization_id==org_id,
        OrganizationGlobalLogisticsPointAdoption.global_logistics_point_id==point.id)):
        _fail("ADOPTION_CONFLICT", "Global point is already adopted by this organization.", 409)
    row=OrganizationGlobalLogisticsPointAdoption(organization_id=org_id,global_point=point,
        organization_reference_code=_text(payload,"organization_reference_code",64),
        display_label=_text(payload,"display_label",160),notes=_text(payload,"notes",1000),
        status="ACTIVE",created_by=actor_id,updated_by=actor_id)
    db.session.add(row); db.session.flush(); _audit(org_id,actor_id,"GLOBAL_POINT_ADOPTED",row); _commit()
    return scoped_adoption(row.public_id,org_id)


def update(public_id,payload,org_id,actor_id):
    _strict(payload,METADATA_FIELDS); row=scoped_adoption(public_id,org_id); _version(row,payload)
    for key,limit in (("organization_reference_code",64),("display_label",160),("notes",1000)):
        if key in payload: setattr(row,key,_text(payload,key,limit))
    row.updated_by=actor_id; row.version+=1; _audit(org_id,actor_id,"GLOBAL_POINT_ADOPTION_UPDATED",row); _commit()
    return scoped_adoption(row.public_id,org_id)


def transition(public_id,payload,org_id,actor_id,target):
    _strict(payload,{"version"}); row=scoped_adoption(public_id,org_id); _version(row,payload)
    if row.status==target: _fail("ILLEGAL_STATE_TRANSITION", f"Adoption is already {target}.",409)
    if target=="ACTIVE" and row.global_point.lifecycle_status!="ACTIVE":
        _fail("GLOBAL_POINT_INELIGIBLE", "A deprecated global point cannot be reactivated.",409)
    row.status=target; row.updated_by=actor_id; row.version+=1
    _audit(org_id,actor_id,"GLOBAL_POINT_ADOPTION_"+target,row); _commit()
    return scoped_adoption(row.public_id,org_id)
