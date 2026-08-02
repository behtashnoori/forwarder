"""Bounded Logistics Network application service."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType, ProjectLogisticsPoint, PROJECT_LOGISTICS_ROLES
from backend.models import City, Country, Province
from backend.operational_models import OperationalAudit, Project, utcnow
from backend.services.operational_service import OperationalError, organization_for_user, require_permission

TYPE_CODES = frozenset({"FACTORY","WAREHOUSE","DISTRIBUTION_CENTER","CUSTOMS","PORT","BORDER_CROSSING","AIRPORT","RAIL_TERMINAL","ROAD_TERMINAL","CUSTOMER_SITE","OTHER_GOVERNED"})
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationalError("VALIDATION_FAILED", "fa_name is required.")
    value = unicodedata.normalize("NFC", value).translate(str.maketrans({"ي":"ی", "ى":"ی", "ك":"ک"})).translate(_DIGITS)
    value = value.replace("\u200c", " ")
    return re.sub(r"\s+", " ", value).strip().casefold()


def _text(payload: dict, key: str, limit: int, *, required=False):
    value = payload.get(key)
    if value is None and not required: return None
    if not isinstance(value, str) or (required and not value.strip()): raise OperationalError("VALIDATION_FAILED", f"{key} is invalid.")
    value = value.strip()
    if len(value) > limit: raise OperationalError("VALIDATION_FAILED", f"{key} is too long.")
    return value or None


def _version(row, payload):
    if not isinstance(payload.get("version"), int) or payload["version"] != row.version:
        raise OperationalError("VERSION_CONFLICT", "version does not match the current resource.", 409)


def _audit(organization_id, user_id, action, entity_type, entity_id, metadata=None):
    db.session.add(OperationalAudit(organization_id=organization_id, actor_user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, metadata_json=metadata or {}))


def type_projection(row):
    return {"public_id":row.public_id,"immutable_code":row.immutable_code,"fa_name":row.fa_name,"en_name":row.en_name,"definition":row.definition,"display_order":row.display_order,"is_active":row.is_active,"version":row.version,"updated_at":row.updated_at.isoformat()}


def point_projection(row):
    return {"public_id":row.public_id,"immutable_code":row.immutable_code,"fa_name":row.fa_name,"en_name":row.en_name,"short_address":row.short_address,"is_active":row.is_active,"version":row.version,
        "point_type":type_projection(row.point_type),"country":{"code":row.country.code,"fa_name":row.country.name_fa,"en_name":row.country.name_en},
        "province":{"code":row.province.code,"name_fa":row.province.name_fa} if row.province else None,
        "city":{"code":row.city.code,"name_fa":row.city.name_fa} if row.city else None,"updated_at":row.updated_at.isoformat()}


def association_projection(row):
    return {"public_id":row.public_id,"project_role":row.project_role,"sequence_number":row.sequence_number,"display_label":row.display_label,"notes":row.notes,"is_active":row.is_active,"version":row.version,"logistics_point":point_projection(row.logistics_point)}


def list_types(args, *, admin=False):
    q=select(LogisticsPointType); active=str(args.get("active", "true" if not admin else "all"))
    if active in {"true","false"}: q=q.where(LogisticsPointType.is_active.is_(active=="true"))
    term=str(args.get("q", "")).strip()[:160]
    if term: q=q.where(or_(LogisticsPointType.immutable_code.ilike(f"%{term}%"),LogisticsPointType.fa_name.ilike(f"%{term}%"),LogisticsPointType.en_name.ilike(f"%{term}%")))
    rows=db.session.scalars(q.order_by(LogisticsPointType.display_order,LogisticsPointType.id)).all()
    return {"items":[type_projection(x) for x in rows]}


def create_type(payload,user):
    code=_text(payload,"immutable_code",64,required=True).upper()
    if code not in TYPE_CODES: raise OperationalError("VALIDATION_FAILED","immutable_code is not in the accepted catalog.")
    row=LogisticsPointType(immutable_code=code,fa_name=_text(payload,"fa_name",160,required=True),en_name=_text(payload,"en_name",160,required=True),definition=_text(payload,"definition",4000),display_order=int(payload.get("display_order",0)),created_by=user["id"],updated_by=user["id"])
    db.session.add(row);db.session.flush();return row


def update_type(row,payload,user):
    _version(row,payload)
    if "immutable_code" in payload and str(payload["immutable_code"]).upper()!=row.immutable_code: raise OperationalError("VALIDATION_FAILED","immutable_code cannot be changed.")
    for f,l,r in (("fa_name",160,True),("en_name",160,True),("definition",4000,False)):
        if f in payload:setattr(row,f,_text(payload,f,l,required=r))
    if "display_order" in payload: row.display_order=int(payload["display_order"])
    row.updated_by=user["id"];row.updated_at=utcnow();row.version+=1;return row


def _geography(payload):
    country=db.session.scalar(select(Country).where(Country.code==str(payload.get("country_code","")).upper(),Country.is_active.is_(True)))
    if not country: raise OperationalError("VALIDATION_FAILED","An active country_code is required.")
    province=None;city=None
    if payload.get("province_code"):
        province=db.session.scalar(select(Province).where(Province.code==str(payload["province_code"]),Province.country_id==country.id,Province.is_active.is_(True)))
        if not province: raise OperationalError("VALIDATION_FAILED","province_code is inconsistent with country.")
    if payload.get("city_code"):
        if not province: raise OperationalError("VALIDATION_FAILED","province_code is required when city_code is supplied.")
        city=db.session.scalar(select(City).where(City.code==str(payload["city_code"]),City.province_id==province.id,City.is_active.is_(True)))
        if not city: raise OperationalError("VALIDATION_FAILED","city_code is inconsistent with province.")
    key=f"{province.id if province else 0}:{city.id if city else 0}"
    return country,province,city,key


def probable_duplicates(org, normalized, type_id, country_id):
    return db.session.scalars(select(LogisticsPoint).where(LogisticsPoint.organization_id==org,LogisticsPoint.logistics_point_type_id==type_id,LogisticsPoint.country_id==country_id,LogisticsPoint.normalized_name==normalized)).all()


def create_point(payload,user):
    require_permission(user,"logistics_point.manage");org=organization_for_user(user["id"])
    point_type=db.session.scalar(select(LogisticsPointType).where(LogisticsPointType.public_id==payload.get("point_type_public_id"),LogisticsPointType.is_active.is_(True)))
    if not point_type: raise OperationalError("NOT_FOUND","Logistics point type not found.",404)
    country,province,city,key=_geography(payload); norm=normalize_name(payload.get("fa_name"))
    exact=db.session.scalar(select(LogisticsPoint).where(LogisticsPoint.organization_id==org,LogisticsPoint.normalized_name==norm,LogisticsPoint.logistics_point_type_id==point_type.id,LogisticsPoint.country_id==country.id,LogisticsPoint.geography_key==key))
    if exact: raise OperationalError("EXACT_DUPLICATE","An exact governed logistics point already exists.",409)
    probable=probable_duplicates(org,norm,point_type.id,country.id)
    if probable and payload.get("confirm_probable_duplicate") is not True: raise OperationalError("PROBABLE_DUPLICATE","Probable duplicate requires explicit confirmation.",409)
    row=LogisticsPoint(organization_id=org,immutable_code=_text(payload,"immutable_code",64,required=True).upper(),logistics_point_type_id=point_type.id,fa_name=_text(payload,"fa_name",160,required=True),normalized_name=norm,en_name=_text(payload,"en_name",160),country_id=country.id,province_id=province.id if province else None,city_id=city.id if city else None,geography_key=key,short_address=_text(payload,"short_address",500),created_by=user["id"],updated_by=user["id"])
    db.session.add(row);db.session.flush();_audit(org,user["id"],"logistics_point.created","logistics_point",row.id,{"public_id":row.public_id});return row


def scoped_point(public_id,user,permission="logistics_point.read",include_inactive=True):
    require_permission(user,permission);org=organization_for_user(user["id"])
    q=select(LogisticsPoint).where(LogisticsPoint.public_id==public_id,LogisticsPoint.organization_id==org)
    if not include_inactive:q=q.where(LogisticsPoint.is_active.is_(True))
    row=db.session.scalar(q)
    if not row: raise OperationalError("NOT_FOUND","Logistics point not found.",404)
    return row


def list_points(args,user,*,admin=False):
    require_permission(user,"logistics_point.read");org=organization_for_user(user["id"]);q=select(LogisticsPoint).where(LogisticsPoint.organization_id==org)
    active=str(args.get("active","all" if admin else "true"));
    if active in {"true","false"}:q=q.where(LogisticsPoint.is_active.is_(active=="true"))
    if args.get("type"):q=q.join(LogisticsPointType).where(LogisticsPointType.public_id==args["type"])
    if args.get("country"):q=q.join(Country).where(Country.code==str(args["country"]).upper())
    term=str(args.get("q","")).strip()[:160]
    if term:q=q.where(or_(LogisticsPoint.immutable_code.ilike(f"%{term}%"),LogisticsPoint.fa_name.ilike(f"%{term}%"),LogisticsPoint.en_name.ilike(f"%{term}%")))
    page=max(1,int(args.get("page",1)));per=min(100,max(1,int(args.get("per_page",20))));total=db.session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows=db.session.scalars(q.order_by(LogisticsPoint.immutable_code).offset((page-1)*per).limit(per)).all()
    return {"items":[point_projection(x) for x in rows],"page":page,"per_page":per,"total":total,"pages":((total+per-1)//per)}


def update_point(row,payload,user):
    _version(row,payload)
    if "immutable_code" in payload and str(payload["immutable_code"]).upper()!=row.immutable_code: raise OperationalError("VALIDATION_FAILED","immutable_code cannot be changed.")
    if any(k in payload for k in ("country_code","province_code","city_code")):
        country,province,city,key=_geography({"country_code":payload.get("country_code",row.country.code),"province_code":payload.get("province_code",row.province.code if row.province else None),"city_code":payload.get("city_code",row.city.code if row.city else None)})
        row.country_id,row.province_id,row.city_id,row.geography_key=country.id,province.id if province else None,city.id if city else None,key
    for f,l in (("fa_name",160),("en_name",160),("short_address",500)):
        if f in payload:setattr(row,f,_text(payload,f,l,required=f=="fa_name"))
    row.normalized_name=normalize_name(row.fa_name);row.updated_by=user["id"];row.updated_at=utcnow();row.version+=1;_audit(row.organization_id,user["id"],"logistics_point.updated","logistics_point",row.id);return row


def set_active(row,active,payload,user):
    _version(row,payload);row.is_active=active;row.updated_by=user["id"];row.updated_at=utcnow();row.version+=1
    organization_id=getattr(row,"organization_id",None)
    if organization_id:_audit(organization_id,user["id"],"logistics_network.activated" if active else "logistics_network.deactivated",row.__tablename__,row.id)
    return row


def scoped_project(public_id,user,permission="project_logistics_point.read"):
    require_permission(user,permission);org=organization_for_user(user["id"])
    row=db.session.scalar(select(Project).where(Project.public_id==public_id,Project.organization_id==org))
    if not row:raise OperationalError("NOT_FOUND","Project not found.",404)
    return row


def list_associations(project):
    rows=db.session.scalars(select(ProjectLogisticsPoint).where(ProjectLogisticsPoint.project_id==project.id).order_by(ProjectLogisticsPoint.is_active.desc(),ProjectLogisticsPoint.sequence_number)).all()
    return {"items":[association_projection(x) for x in rows]}


def create_association(project,payload,user):
    point=scoped_point(str(payload.get("logistics_point_public_id","")),user,include_inactive=False);role=str(payload.get("project_role","")).upper();seq=payload.get("sequence_number")
    if role not in PROJECT_LOGISTICS_ROLES or not isinstance(seq,int) or seq<1:raise OperationalError("VALIDATION_FAILED","A bounded role and positive sequence_number are required.")
    row=ProjectLogisticsPoint(organization_id=project.organization_id,project_id=project.id,logistics_point_id=point.id,project_role=role,sequence_number=seq,display_label=_text(payload,"display_label",160),notes=_text(payload,"notes",4000),created_by=user["id"],updated_by=user["id"])
    db.session.add(row);db.session.flush();_audit(project.organization_id,user["id"],"project_logistics_point.created","project_logistics_point",row.id,{"project_id":project.public_id});return row


def scoped_association(project,public_id):
    row=db.session.scalar(select(ProjectLogisticsPoint).where(ProjectLogisticsPoint.public_id==public_id,ProjectLogisticsPoint.project_id==project.id))
    if not row:raise OperationalError("NOT_FOUND","Project logistics point not found.",404)
    return row


def update_association(row,payload,user):
    _version(row,payload)
    if "project_role" in payload:
        role=str(payload["project_role"]).upper()
        if role not in PROJECT_LOGISTICS_ROLES:raise OperationalError("VALIDATION_FAILED","project_role is invalid.")
        row.project_role=role
    if "sequence_number" in payload:
        if not isinstance(payload["sequence_number"],int) or payload["sequence_number"]<1:raise OperationalError("VALIDATION_FAILED","sequence_number is invalid.")
        row.sequence_number=payload["sequence_number"]
    for f,l in (("display_label",160),("notes",4000)):
        if f in payload:setattr(row,f,_text(payload,f,l))
    row.updated_by=user["id"];row.updated_at=utcnow();row.version+=1;_audit(row.organization_id,user["id"],"project_logistics_point.updated","project_logistics_point",row.id);return row


def reorder(project,payload,user):
    items=payload.get("items")
    if not isinstance(items,list) or not items:raise OperationalError("VALIDATION_FAILED","items must be a non-empty array.")
    rows=db.session.scalars(select(ProjectLogisticsPoint).where(ProjectLogisticsPoint.project_id==project.id,ProjectLogisticsPoint.is_active.is_(True)).with_for_update()).all()
    by_id={x.public_id:x for x in rows}
    if {str(x.get("public_id")) for x in items}!=set(by_id):raise OperationalError("VALIDATION_FAILED","reorder must include every active association exactly once.")
    temporary_base = max((row.sequence_number for row in rows), default=0) + len(rows) + 1
    for index,item in enumerate(items,1):
        row=by_id[str(item["public_id"])]
        if item.get("version")!=row.version:raise OperationalError("VERSION_CONFLICT","Association version conflict.",409)
        row.sequence_number=temporary_base+index;row.updated_by=user["id"];row.version+=1
    db.session.flush()
    for index,item in enumerate(items,1):by_id[str(item["public_id"])].sequence_number=index
    _audit(project.organization_id,user["id"],"project_logistics_point.reordered","project",project.id,{"count":len(items)})
    return list(by_id.values())


def commit_or_error():
    try:db.session.commit()
    except IntegrityError as exc:
        db.session.rollback();raise OperationalError("CONFLICT","Logistics Network constraint conflict.",409) from exc
