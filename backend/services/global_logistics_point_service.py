"""Governed Platform Admin operations for the ADR-041 global catalog."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.extensions import db
from backend.global_logistics_point_models import (
    GLOBAL_POINT_BORDER_SIDES, GLOBAL_POINT_LIFECYCLES, GLOBAL_POINT_MODES,
    GLOBAL_POINT_VERIFICATION_STATES, GlobalLogisticsPoint,
    GlobalLogisticsPointAlias, GlobalLogisticsPointCorridorTag,
    GlobalLogisticsPointExternalCode, GlobalLogisticsPointMode,
    GlobalLogisticsPointSource,
)
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country
from backend.services.operational_service import OperationalError

CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,63}$")
TAG_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,63}$")
LANG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
LIMITS = {"aliases": 50, "supported_modes": 5, "external_codes": 30,
          "corridor_tags": 30, "sources": 30}
CREATE_FIELDS = {"immutable_code", "point_type_public_id", "country_code",
    "fa_name", "en_name", "facility_identity_key", "region_name", "city_name",
    "short_address", "latitude", "longitude", "timezone", "un_locode",
    "border_pair_key", "border_side", "confirm_probable_duplicate",
    "duplicate_review_reason", *LIMITS}
PATCH_FIELDS = {"expected_version", "point_type_public_id", "fa_name", "en_name",
    "region_name", "city_name", "short_address", "latitude", "longitude", "timezone",
    "un_locode", "border_pair_key", "border_side", *LIMITS}


def _fail(code, message, status=400, details=None):
    exc = OperationalError(code, message, status)
    exc.details = details
    raise exc


def _strict(payload, allowed):
    if not isinstance(payload, dict):
        _fail("VALIDATION_FAILED", "A JSON object is required.")
    unknown = sorted(set(payload) - allowed)
    if unknown:
        _fail("UNKNOWN_FIELDS", "Unknown fields are not allowed.", details={"fields": unknown})


def _opaque_id(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise OperationalError("NOT_FOUND", "Global logistics point not found.", 404) from exc


def _options():
    return (selectinload(GlobalLogisticsPoint.aliases), selectinload(GlobalLogisticsPoint.modes),
        selectinload(GlobalLogisticsPoint.external_codes), selectinload(GlobalLogisticsPoint.corridor_tags),
        selectinload(GlobalLogisticsPoint.sources), selectinload(GlobalLogisticsPoint.point_type),
        selectinload(GlobalLogisticsPoint.country), selectinload(GlobalLogisticsPoint.province),
        selectinload(GlobalLogisticsPoint.city), selectinload(GlobalLogisticsPoint.international_city))


def _norm(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().casefold().split())


def _text(payload, key, limit, required=False):
    value = str(payload.get(key) or "").strip()
    if required and not value:
        _fail("VALIDATION_FAILED", f"{key} is required.")
    if len(value) > limit:
        _fail("VALIDATION_FAILED", f"{key} is too long.")
    return value or None


def _version(row, payload):
    expected = payload.get("expected_version")
    if not isinstance(expected, int) or isinstance(expected, bool):
        _fail("VALIDATION_FAILED", "expected_version is required and must be an integer.")
    if expected != row.version:
        _fail("VERSION_CONFLICT", "Global logistics point version is stale.", 409,
              {"current_version": row.version})


def _type(value):
    try:
        value = str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        _fail("VALIDATION_FAILED", "point_type_public_id is invalid.")
    row = db.session.scalar(select(LogisticsPointType).where(LogisticsPointType.public_id == value))
    if row is None:
        _fail("VALIDATION_FAILED", "point_type_public_id is invalid.")
    return row


def _country(value):
    value = str(value or "").strip().upper()
    if len(value) not in {2, 3}:
        _fail("VALIDATION_FAILED", "country_code is invalid.")
    row = db.session.scalar(select(Country).where(Country.code == value))
    if row is None:
        _fail("VALIDATION_FAILED", "country_code is invalid.")
    return row


def _coords(payload):
    lat, lon = payload.get("latitude"), payload.get("longitude")
    if (lat is None) != (lon is None):
        _fail("VALIDATION_FAILED", "latitude and longitude must be supplied together.")
    if lat is None:
        return None, None
    try:
        lat, lon = Decimal(str(lat)), Decimal(str(lon))
    except (InvalidOperation, ValueError):
        _fail("VALIDATION_FAILED", "coordinates are invalid.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        _fail("VALIDATION_FAILED", "coordinates are out of range.")
    return lat, lon


def _timezone(value):
    value = str(value or "").strip() or None
    if value:
        if len(value) > 64:
            _fail("VALIDATION_FAILED", "timezone is too long.")
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            _fail("VALIDATION_FAILED", "timezone must be a valid IANA timezone.")
    return value


def _items(payload, key):
    value = payload.get(key, [])
    if not isinstance(value, list) or len(value) > LIMITS[key]:
        _fail("VALIDATION_FAILED", f"{key} must be a bounded list (maximum {LIMITS[key]}).")
    return value


def _build_children(payload, actor_id):
    result = {}
    seen = set(); result["aliases"] = []
    for item in _items(payload, "aliases"):
        if not isinstance(item, dict) or set(item) - {"value", "language_code"}:
            _fail("VALIDATION_FAILED", "aliases contain an invalid item.")
        value = _text(item, "value", 160, True); normalized = _norm(value)
        language = str(item.get("language_code") or "").strip() or None
        if language and not LANG_RE.fullmatch(language):
            _fail("VALIDATION_FAILED", "alias language_code is invalid.")
        if normalized in seen: _fail("DUPLICATE_CHILD", "Duplicate alias.", 409)
        seen.add(normalized); result["aliases"].append(GlobalLogisticsPointAlias(
            alias=value, normalized_alias=normalized, language_code=language))
    seen = set(); result["supported_modes"] = []
    for raw in _items(payload, "supported_modes"):
        value = str(raw).strip().upper()
        if value not in GLOBAL_POINT_MODES: _fail("VALIDATION_FAILED", "Invalid supported mode.")
        if value in seen: _fail("DUPLICATE_CHILD", "Duplicate supported mode.", 409)
        seen.add(value); result["supported_modes"].append(GlobalLogisticsPointMode(mode_code=value))
    seen = set(); result["external_codes"] = []
    for item in _items(payload, "external_codes"):
        if not isinstance(item, dict) or set(item) - {"scheme", "value", "source_reference"}:
            _fail("VALIDATION_FAILED", "external_codes contain an invalid item.")
        scheme = str(_text(item, "scheme", 64, True)).upper()
        value = _text(item, "value", 160, True); normalized = _norm(value)
        key = (scheme, normalized)
        if key in seen: _fail("DUPLICATE_CHILD", "Duplicate external code.", 409)
        seen.add(key); result["external_codes"].append(GlobalLogisticsPointExternalCode(
            scheme=scheme, value=value, normalized_value=normalized,
            source_reference=_text(item, "source_reference", 500)))
    seen = set(); result["corridor_tags"] = []
    for raw in _items(payload, "corridor_tags"):
        value = str(raw).strip().upper()
        if not TAG_RE.fullmatch(value): _fail("VALIDATION_FAILED", "Invalid corridor tag.")
        if value in seen: _fail("DUPLICATE_CHILD", "Duplicate corridor tag.", 409)
        seen.add(value); result["corridor_tags"].append(GlobalLogisticsPointCorridorTag(tag_code=value))
    seen = set(); result["sources"] = []
    for item in _items(payload, "sources"):
        if not isinstance(item, dict) or set(item) - {"organization", "reference", "version", "retrieved_at"}:
            _fail("VALIDATION_FAILED", "sources contain an invalid item.")
        org = _text(item, "organization", 160, True); ref = _text(item, "reference", 500, True)
        version = _text(item, "version", 100) or "unspecified"; retrieved = item.get("retrieved_at")
        if retrieved:
            try: retrieved = datetime.fromisoformat(str(retrieved).replace("Z", "+00:00"))
            except ValueError: _fail("VALIDATION_FAILED", "source retrieved_at is invalid.")
        key = (_norm(org), _norm(ref), _norm(version))
        if key in seen: _fail("DUPLICATE_CHILD", "Duplicate source.", 409)
        seen.add(key); result["sources"].append(GlobalLogisticsPointSource(
            source_organization=org, source_reference=ref, source_version=version,
            retrieved_at=retrieved, reviewed_by=actor_id))
    return result


def _apply(row, payload, actor_id, creating=False):
    if creating or "point_type_public_id" in payload: row.point_type = _type(payload.get("point_type_public_id"))
    for key, limit, required in (("fa_name",160,True),("en_name",160,True),
        ("region_name",160,False),("city_name",160,False),("short_address",500,False),
        ("un_locode",5,False),("border_pair_key",100,False)):
        if creating or key in payload: setattr(row, key, _text(payload, key, limit, required))
    if creating or "latitude" in payload or "longitude" in payload: row.latitude, row.longitude = _coords(payload)
    if creating or "timezone" in payload: row.timezone_name = _timezone(payload.get("timezone"))
    if creating or "border_side" in payload:
        side = str(payload.get("border_side") or "").strip().upper() or None
        if side and side not in GLOBAL_POINT_BORDER_SIDES: _fail("VALIDATION_FAILED", "border_side is invalid.")
        row.border_side = side
    row.normalized_name = _norm(row.en_name)
    row.geography_key = ":".join(filter(None, [row.country.code, _norm(row.region_name), _norm(row.city_name)]))
    if creating or any(key in payload for key in LIMITS):
        current = {
            "aliases": [{"value": x.alias, "language_code": x.language_code} for x in row.aliases],
            "supported_modes": [x.mode_code for x in row.modes],
            "external_codes": [{"scheme": x.scheme, "value": x.value,
                "source_reference": x.source_reference} for x in row.external_codes],
            "corridor_tags": [x.tag_code for x in row.corridor_tags],
            "sources": [{"organization": x.source_organization, "reference": x.source_reference,
                "version": x.source_version, "retrieved_at": x.retrieved_at.isoformat() if x.retrieved_at else None}
                for x in row.sources],
        }
        built = _build_children({key: payload.get(key, current[key]) for key in LIMITS}, actor_id)
        if not creating:
            for key, attr in (("aliases","aliases"),("supported_modes","modes"),
                ("external_codes","external_codes"),("corridor_tags","corridor_tags"),("sources","sources")):
                if key in payload:
                    setattr(row, attr, [])
            db.session.flush()
        for key, attr in (("aliases","aliases"),("supported_modes","modes"),
            ("external_codes","external_codes"),("corridor_tags","corridor_tags"),("sources","sources")):
            if creating or key in payload: setattr(row, attr, built[key])
    row.updated_by = actor_id


def _commit():
    try: db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise OperationalError("DUPLICATE_CONFLICT", "A governed identity already exists.", 409) from exc


def _external_conflict(row):
    for code in row.external_codes:
        collision = db.session.scalar(select(GlobalLogisticsPointExternalCode.id).where(
            GlobalLogisticsPointExternalCode.global_logistics_point_id != (row.id or 0),
            GlobalLogisticsPointExternalCode.scheme == code.scheme,
            func.lower(GlobalLogisticsPointExternalCode.normalized_value) == code.normalized_value.lower()))
        if collision:
            _fail("DUPLICATE_CONFLICT", "An external code already belongs to another governed point.", 409)


def projection(row):
    return {"public_id":row.public_id, "immutable_code":row.immutable_code,
        "fa_name":row.fa_name, "en_name":row.en_name,
        "point_type":{"public_id":row.point_type.public_id,"code":row.point_type.immutable_code,
            "fa_name":row.point_type.fa_name,"en_name":row.point_type.en_name},
        "country":{"code":row.country.code,"fa_name":row.country.name_fa,"en_name":row.country.name_en},
        "facility_identity_key":row.facility_identity_key,
        "geography":{"province":row.province.name_fa if row.province else row.region_name,
            "city":row.city.name_fa if row.city else row.international_city.name_fa if row.international_city else row.city_name,
            "short_address":row.short_address,"latitude":float(row.latitude) if row.latitude is not None else None,
            "longitude":float(row.longitude) if row.longitude is not None else None,"timezone":row.timezone_name,
            "un_locode":row.un_locode,"border_pair_key":row.border_pair_key,"border_side":row.border_side},
        "aliases":[{"value":x.alias,"language_code":x.language_code} for x in sorted(row.aliases,key=lambda x:x.normalized_alias)],
        "supported_modes":sorted(x.mode_code for x in row.modes),
        "corridor_tags":sorted(x.tag_code for x in row.corridor_tags),
        "external_codes":[{"scheme":x.scheme,"value":x.value} for x in sorted(row.external_codes,key=lambda x:(x.scheme,x.normalized_value))],
        "sources":[{"organization":x.source_organization,"reference":x.source_reference,
            "version":x.source_version,"retrieved_at":x.retrieved_at.isoformat() if x.retrieved_at else None} for x in row.sources],
        "lifecycle_status":row.lifecycle_status,"verification_status":row.verification_status,
        "version":row.version,"created_at":row.created_at.isoformat(),"updated_at":row.updated_at.isoformat()}


def list_points(args):
    query = select(GlobalLogisticsPoint).options(*_options())
    term = str(args.get("q", "")).strip()
    if len(term)>160: _fail("VALIDATION_FAILED", "q is too long.")
    if term:
        pattern=f"%{term}%"; query=query.where(or_(GlobalLogisticsPoint.immutable_code.ilike(pattern),
            GlobalLogisticsPoint.fa_name.ilike(pattern),GlobalLogisticsPoint.en_name.ilike(pattern),
            GlobalLogisticsPoint.aliases.any(GlobalLogisticsPointAlias.alias.ilike(pattern))))
    country=str(args.get("country","")).strip().upper()
    if country: query=query.join(GlobalLogisticsPoint.country).where(Country.code==country)
    type_code=str(args.get("type","")).strip().upper()
    if type_code: query=query.join(GlobalLogisticsPoint.point_type).where(LogisticsPointType.immutable_code==type_code)
    status=str(args.get("status","ACTIVE")).strip().upper()
    if status!="ALL":
        if status not in GLOBAL_POINT_LIFECYCLES: _fail("VALIDATION_FAILED","status is invalid.")
        query=query.where(GlobalLogisticsPoint.lifecycle_status==status)
    verification=str(args.get("verification","")).strip().upper()
    if verification:
        if verification not in GLOBAL_POINT_VERIFICATION_STATES: _fail("VALIDATION_FAILED","verification is invalid.")
        query=query.where(GlobalLogisticsPoint.verification_status==verification)
    mode=str(args.get("mode","")).strip().upper()
    if mode:
        if mode not in GLOBAL_POINT_MODES: _fail("VALIDATION_FAILED","mode is invalid.")
        query=query.where(GlobalLogisticsPoint.modes.any(GlobalLogisticsPointMode.mode_code==mode))
    corridor=str(args.get("corridor","")).strip().upper()
    if corridor:
        if not TAG_RE.fullmatch(corridor): _fail("VALIDATION_FAILED","corridor is invalid.")
        query=query.where(GlobalLogisticsPoint.corridor_tags.any(GlobalLogisticsPointCorridorTag.tag_code==corridor))
    try: page=max(1,int(args.get("page",1))); per_page=min(100,max(1,int(args.get("per_page",20))))
    except (TypeError,ValueError): _fail("VALIDATION_FAILED","pagination is invalid.")
    total=db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows=db.session.scalars(query.order_by(GlobalLogisticsPoint.immutable_code,GlobalLogisticsPoint.public_id)
        .offset((page-1)*per_page).limit(per_page)).all()
    return {"items":[projection(x) for x in rows],"page":page,"per_page":per_page,
        "total":total,"pages":((total+per_page-1)//per_page)}


def detail(public_id):
    row=db.session.scalar(select(GlobalLogisticsPoint).options(*_options()).where(
        GlobalLogisticsPoint.public_id==_opaque_id(public_id)))
    if row is None: _fail("NOT_FOUND","Global logistics point not found.",404)
    return row


def create(payload, actor_id):
    _strict(payload, CREATE_FIELDS)
    code=str(payload.get("immutable_code") or "").strip().upper()
    if not CODE_RE.fullmatch(code): _fail("VALIDATION_FAILED","immutable_code is invalid.")
    country=_country(payload.get("country_code")); point_type=_type(payload.get("point_type_public_id"))
    facility=_norm(_text(payload,"facility_identity_key",240,True))
    conflict=db.session.scalar(select(GlobalLogisticsPoint.id).where(or_(
        GlobalLogisticsPoint.immutable_code==code,
        (GlobalLogisticsPoint.country_id==country.id)&(GlobalLogisticsPoint.logistics_point_type_id==point_type.id)&(GlobalLogisticsPoint.facility_identity_key==facility))))
    if conflict: _fail("DUPLICATE_CONFLICT","A governed identity already exists.",409)
    probable = db.session.scalars(select(GlobalLogisticsPoint).where(
        GlobalLogisticsPoint.country_id == country.id,
        GlobalLogisticsPoint.logistics_point_type_id == point_type.id,
        or_(GlobalLogisticsPoint.normalized_name == _norm(payload.get("en_name")),
            GlobalLogisticsPoint.city_name == str(payload.get("city_name") or "").strip()))).all()
    if probable and payload.get("confirm_probable_duplicate") is not True:
        _fail("PROBABLE_DUPLICATE_REVIEW_REQUIRED", "Probable duplicates require explicit reviewed confirmation.",
              409, {"candidates": [{"public_id": x.public_id, "immutable_code": x.immutable_code} for x in probable]})
    review_reason = None
    if payload.get("confirm_probable_duplicate") is True:
        review_reason = _text(payload, "duplicate_review_reason", 500, True)
    row=GlobalLogisticsPoint(immutable_code=code,country=country,point_type=point_type,
        facility_identity_key=facility,geography_key=country.code,fa_name="pending",en_name="pending",
        normalized_name="pending",lifecycle_status="DRAFT",verification_status="UNVERIFIED",
        created_by=actor_id,updated_by=actor_id)
    _apply(row,payload,actor_id,True)
    if review_reason:
        row.sources.append(GlobalLogisticsPointSource(source_organization="Forwarder Platform Governance",
            source_reference=review_reason, source_version="PROBABLE_DUPLICATE_OVERRIDE:v1", reviewed_by=actor_id))
    _external_conflict(row); db.session.add(row); _commit(); return detail(row.public_id)


def update(public_id,payload,actor_id):
    _strict(payload,PATCH_FIELDS); row=detail(public_id); _version(row,payload)
    if row.lifecycle_status=="DEPRECATED": _fail("ILLEGAL_STATE_TRANSITION","Deprecated points cannot be edited.",409)
    if "sources" in payload and row.verification_status != "UNVERIFIED":
        _fail("PROVENANCE_IMMUTABLE", "Reviewed provenance cannot be replaced by ordinary metadata update.", 409)
    if row.lifecycle_status=="ACTIVE" and payload.get("sources") == []:
        _fail("PROVENANCE_REQUIRED", "Provenance cannot be removed from an active point.", 409)
    _apply(row,payload,actor_id); _external_conflict(row); row.version+=1; _commit(); return detail(row.public_id)


def _verification(public_id,payload,actor_id,current,target):
    _strict(payload,{"expected_version","evidence_reference"}); row=detail(public_id); _version(row,payload)
    if row.lifecycle_status!="DRAFT" or row.verification_status!=current:
        _fail("ILLEGAL_STATE_TRANSITION",f"Only DRAFT {current} points may transition to {target}.",409)
    evidence = _text(payload,"evidence_reference",500,True)
    if not row.sources: _fail("VALIDATION_FAILED","At least one provenance source is required.")
    row.sources.append(GlobalLogisticsPointSource(source_organization="Forwarder Platform Governance",
        source_reference=evidence, source_version=f"{target}:v{row.version + 1}", reviewed_by=actor_id))
    row.verification_status=target; row.updated_by=actor_id; row.version+=1; _commit(); return detail(row.public_id)


def review(public_id,payload,actor_id): return _verification(public_id,payload,actor_id,"UNVERIFIED","REVIEWED")
def verify(public_id,payload,actor_id): return _verification(public_id,payload,actor_id,"REVIEWED","VERIFIED")


def activation_failures(row):
    failures=[]
    def add(code,field,message): failures.append({"code":code,"field":field,"message":message})
    if not CODE_RE.fullmatch(row.immutable_code or ""): add("INVALID_IMMUTABLE_CODE","immutable_code","Immutable code is invalid.")
    if not row.point_type or not row.point_type.is_active: add("INVALID_POINT_TYPE","point_type","Point type must be active.")
    if not row.country: add("INVALID_COUNTRY","country","Country is required.")
    if not row.fa_name.strip() or not row.en_name.strip(): add("MISSING_NAMES","names","Canonical names are required.")
    if not row.facility_identity_key: add("INVALID_FACILITY_IDENTITY","facility_identity_key","Facility identity is required.")
    if not row.modes: add("MISSING_MODES","supported_modes","At least one supported mode is required.")
    if not row.sources: add("MISSING_PROVENANCE","sources","At least one provenance source is required.")
    if row.verification_status!="VERIFIED": add("VERIFICATION_REQUIRED","verification_status","VERIFIED status is required.")
    if row.timezone_name:
        try: ZoneInfo(row.timezone_name)
        except ZoneInfoNotFoundError: add("INVALID_TIMEZONE","timezone","Timezone is invalid.")
    is_border = bool(row.point_type and row.point_type.immutable_code=="BORDER_CROSSING")
    if is_border and (not row.border_pair_key or row.border_side not in {"ENTRY","EXIT","BIDIRECTIONAL"}):
        add("INVALID_BORDER_SEMANTICS","border","Border crossings require pair key and applicable side.")
    if not is_border and row.border_side and row.border_side!="NOT_APPLICABLE":
        add("INVALID_BORDER_SEMANTICS","border_side","Non-border points must use NOT_APPLICABLE.")
    for code in row.external_codes:
        collision=db.session.scalar(select(GlobalLogisticsPointExternalCode.id).where(
            GlobalLogisticsPointExternalCode.global_logistics_point_id!=row.id,
            GlobalLogisticsPointExternalCode.scheme==code.scheme,
            func.lower(GlobalLogisticsPointExternalCode.normalized_value)==code.normalized_value.lower()))
        if collision: add("EXTERNAL_CODE_CONFLICT","external_codes",f"{code.scheme} code already belongs to another point.")
    return failures


def activate(public_id,payload,actor_id):
    _strict(payload,{"expected_version"}); row=detail(public_id); _version(row,payload)
    if row.lifecycle_status!="DRAFT": _fail("ILLEGAL_STATE_TRANSITION","Only DRAFT points may be activated.",409)
    failures=activation_failures(row)
    if failures: _fail("ACTIVATION_GATE_FAILED","Activation requirements are not satisfied.",422,{"failures":failures})
    row.lifecycle_status="ACTIVE"; row.updated_by=actor_id; row.version+=1; _commit(); return detail(row.public_id)


def deprecate(public_id,payload,actor_id):
    _strict(payload,{"expected_version","reason"}); row=detail(public_id); _version(row,payload)
    if row.lifecycle_status!="ACTIVE": _fail("ILLEGAL_STATE_TRANSITION","Only ACTIVE points may be deprecated.",409)
    reason = _text(payload,"reason",500,True)
    row.sources.append(GlobalLogisticsPointSource(source_organization="Forwarder Platform Governance",
        source_reference=reason, source_version=f"DEPRECATED:v{row.version + 1}", reviewed_by=actor_id))
    row.lifecycle_status="DEPRECATED"; row.updated_by=actor_id
    row.version+=1; _commit(); return detail(row.public_id)
