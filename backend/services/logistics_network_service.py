"""Bounded Logistics Network application service."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import Text, case, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from backend.extensions import db
from backend.logistics_network_models import (
    LogisticsPoint,
    LogisticsPointType,
    ProjectLogisticsPoint,
    PROJECT_LOGISTICS_ROLES,
)
from backend.models import City, Country, Province
from backend.geonames_geography_catalog import DATASET_ID as GEONAMES_DATASET_ID, COUNTRY_SCOPE
from backend.services import geography_presentation as geo
from backend.operational_models import OperationalAudit, Project, utcnow
from backend.services.operational_service import (
    OperationalError,
    organization_for_user,
    require_any_permission,
    require_permission,
)

TYPE_CODES = frozenset(
    {
        "FACTORY",
        "WAREHOUSE",
        "DISTRIBUTION_CENTER",
        "CUSTOMS",
        "PORT",
        "BORDER_CROSSING",
        "AIRPORT",
        "RAIL_TERMINAL",
        "ROAD_TERMINAL",
        "CUSTOMER_SITE",
        "OTHER_GOVERNED",
    }
)
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationalError("VALIDATION_FAILED", "fa_name is required.")
    value = (
        unicodedata.normalize("NFC", value)
        .translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"}))
        .translate(_DIGITS)
    )
    value = value.replace("\u200c", " ")
    return re.sub(r"\s+", " ", value).strip().casefold()


def _text(payload: dict, key: str, limit: int, *, required=False):
    value = payload.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()):
        raise OperationalError("VALIDATION_FAILED", f"{key} is invalid.")
    value = value.strip()
    if len(value) > limit:
        raise OperationalError("VALIDATION_FAILED", f"{key} is too long.")
    return value or None


def _version(row, payload):
    if not isinstance(payload.get("version"), int) or payload["version"] != row.version:
        raise OperationalError(
            "VERSION_CONFLICT", "version does not match the current resource.", 409
        )


def _audit(organization_id, user_id, action, entity_type, entity_id, metadata=None):
    db.session.add(
        OperationalAudit(
            organization_id=organization_id,
            actor_user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
    )


def type_projection(row):
    return {
        "public_id": row.public_id,
        "immutable_code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "definition": row.definition,
        "display_order": row.display_order,
        "is_active": row.is_active,
        "version": row.version,
        "updated_at": row.updated_at.isoformat(),
    }


def point_projection(row):
    return {
        "public_id": row.public_id,
        "immutable_code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "short_address": row.short_address,
        "is_active": row.is_active,
        "global_source": ({
            "global_point_public_id": row.global_point.public_id,
            "adoption_public_id": row.global_adoption.public_id,
            "fa_name": row.global_point.fa_name,
            "en_name": row.global_point.en_name,
            "platform_lifecycle_status": row.global_point.lifecycle_status,
            "adoption_status": row.global_adoption.status,
        } if row.global_point is not None and row.global_adoption is not None else None),
        "version": row.version,
        "point_type": type_projection(row.point_type) if row.point_type else None,
        "country": {
            "code": row.country.code,
            "fa_name": row.country.name_fa,
            "en_name": row.country.name_en,
        },
        "province": {"code": row.province.code, "name_fa": geo.name_fa(row.province), "name_en": row.province.name_en, "geoname_id": row.province.geoname_id}
        if row.province
        else None,
        "city": {"code": row.city.code, "name_fa": geo.name_fa(row.city), "name_en": row.city.name_en, "geoname_id": row.city.geoname_id}
        if row.city
        else None,
        "latitude": str(row.latitude) if row.latitude is not None else None,
        "longitude": str(row.longitude) if row.longitude is not None else None,
        "description": row.description,
        "governance_state": row.governance_state,
        "duplicate_of_public_id": row.duplicate_of.public_id if row.duplicate_of else None,
        "updated_at": row.updated_at.isoformat(),
    }


def association_projection(row):
    return {
        "public_id": row.public_id,
        "project_role": row.project_role,
        "sequence_number": row.sequence_number,
        "display_label": row.display_label,
        "notes": row.notes,
        "is_active": row.is_active,
        "version": row.version,
        "logistics_point": point_projection(row.logistics_point),
    }


def list_types(args, *, admin=False):
    q = select(LogisticsPointType)
    active = str(args.get("active", "true" if not admin else "all"))
    if active in {"true", "false"}:
        q = q.where(LogisticsPointType.is_active.is_(active == "true"))
    term = str(args.get("q", "")).strip()[:160]
    if term:
        q = q.where(
            or_(
                LogisticsPointType.immutable_code.ilike(f"%{term}%"),
                LogisticsPointType.fa_name.ilike(f"%{term}%"),
                LogisticsPointType.en_name.ilike(f"%{term}%"),
            )
        )
    rows = db.session.scalars(
        q.order_by(LogisticsPointType.display_order, LogisticsPointType.id)
    ).all()
    return {"items": [type_projection(x) for x in rows]}


def create_type(payload, user):
    code = _text(payload, "immutable_code", 64, required=True).upper()
    if code not in TYPE_CODES:
        raise OperationalError(
            "VALIDATION_FAILED", "immutable_code is not in the accepted catalog."
        )
    row = LogisticsPointType(
        immutable_code=code,
        fa_name=_text(payload, "fa_name", 160, required=True),
        en_name=_text(payload, "en_name", 160, required=True),
        definition=_text(payload, "definition", 4000),
        display_order=int(payload.get("display_order", 0)),
        created_by=user["id"],
        updated_by=user["id"],
    )
    db.session.add(row)
    db.session.flush()
    return row


def update_type(row, payload, user):
    _version(row, payload)
    if (
        "immutable_code" in payload
        and str(payload["immutable_code"]).upper() != row.immutable_code
    ):
        raise OperationalError("VALIDATION_FAILED", "immutable_code cannot be changed.")
    for field, limit, required in (
        ("fa_name", 160, True),
        ("en_name", 160, True),
        ("definition", 4000, False),
    ):
        if field in payload:
            setattr(row, field, _text(payload, field, limit, required=required))
    if "display_order" in payload:
        row.display_order = int(payload["display_order"])
    row.updated_by = user["id"]
    row.updated_at = utcnow()
    row.version += 1
    return row


def _geography(payload):
    if payload.get("city_geoname_id") is not None:
        try:
            identity = int(payload["city_geoname_id"])
        except (TypeError, ValueError) as exc:
            raise OperationalError("VALIDATION_FAILED", "city_geoname_id is invalid.") from exc
        city = db.session.scalar(select(City).where(
            City.geoname_id == identity, City.dataset_id == GEONAMES_DATASET_ID, City.is_active.is_(True)
        ))
        if city is None:
            raise OperationalError("NOT_FOUND", "Canonical city not found.", 404)
        province = db.session.get(Province, city.province_id)
        country = db.session.get(Country, city.country_id)
        if province is None or country is None or province.country_id != country.id:
            raise OperationalError("VALIDATION_FAILED", "Canonical city ancestry is inconsistent.")
        return country, province, city, f"{province.id}:{city.id}"
    country = db.session.scalar(
        select(Country).where(
            Country.code == str(payload.get("country_code", "")).upper(),
            Country.is_active.is_(True),
        )
    )
    if not country:
        raise OperationalError(
            "VALIDATION_FAILED", "An active country_code is required."
        )
    province = None
    city = None
    if payload.get("province_code"):
        province = db.session.scalar(
            select(Province).where(
                Province.code == str(payload["province_code"]),
                Province.country_id == country.id,
                Province.is_active.is_(True),
            )
        )
        if not province:
            raise OperationalError(
                "VALIDATION_FAILED", "province_code is inconsistent with country."
            )
    if payload.get("city_code"):
        if not province:
            raise OperationalError(
                "VALIDATION_FAILED",
                "province_code is required when city_code is supplied.",
            )
        city = db.session.scalar(
            select(City).where(
                City.code == str(payload["city_code"]),
                City.province_id == province.id,
                City.is_active.is_(True),
            )
        )
        if not city:
            raise OperationalError(
                "VALIDATION_FAILED", "city_code is inconsistent with province."
            )
    key = f"{province.id if province else 0}:{city.id if city else 0}"
    return country, province, city, key


def probable_duplicates(org, normalized, type_id, country_id, city_id=None):
    query = select(LogisticsPoint).where(
            LogisticsPoint.organization_id == org,
            LogisticsPoint.country_id == country_id,
            LogisticsPoint.normalized_name == normalized,
        )
    query = query.where(LogisticsPoint.logistics_point_type_id == type_id) if type_id is not None else query.where(LogisticsPoint.logistics_point_type_id.is_(None))
    if city_id is not None:
        query = query.where(LogisticsPoint.city_id == city_id)
    return db.session.scalars(query).all()


def _coordinate(payload, key, lower, upper):
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise OperationalError("VALIDATION_FAILED", f"{key} is invalid.")
    if not parsed.is_finite() or parsed < lower or parsed > upper or parsed.as_tuple().exponent < -7:
        raise OperationalError("VALIDATION_FAILED", f"{key} is invalid.")
    return parsed


def create_expert_point(payload, user):
    require_any_permission(user, {
        "operational_shipment.create", "operational_shipment.create_direct",
        "operational_shipment.create_from_quote", "route_leg.manage", "execution_unit.update",
    })
    org = organization_for_user(user["id"])
    country, province, city, key = _geography(payload)
    name = payload.get("name", payload.get("fa_name"))
    norm = normalize_name(name)
    point_type = None
    if payload.get("point_type_public_id"):
        point_type = db.session.scalar(select(LogisticsPointType).where(
            LogisticsPointType.public_id == payload["point_type_public_id"], LogisticsPointType.is_active.is_(True)
        ))
        if point_type is None:
            raise OperationalError("NOT_FOUND", "Logistics point type not found.", 404)
    duplicates = probable_duplicates(org, norm, point_type.id if point_type else None, country.id, city.id)
    if duplicates and payload.get("confirm_probable_duplicate") is not True:
        raise OperationalError("PROBABLE_DUPLICATE", "Probable duplicate requires explicit confirmation.", 409)
    row = LogisticsPoint(
        organization_id=org, immutable_code=f"LOC-{city.geoname_id}-{uuid4().hex[:10].upper()}",
        logistics_point_type_id=point_type.id if point_type else None,
        fa_name=_text({"fa_name": name}, "fa_name", 160, required=True), normalized_name=norm,
        en_name=_text(payload, "en_name", 160), country_id=country.id, province_id=province.id,
        city_id=city.id, geography_key=key, short_address=_text(payload, "address", 500),
        latitude=_coordinate(payload, "latitude", Decimal("-90"), Decimal("90")),
        longitude=_coordinate(payload, "longitude", Decimal("-180"), Decimal("180")),
        description=_text(payload, "description", 4000), governance_state="PENDING_REVIEW",
        created_by=user["id"], updated_by=user["id"],
    )
    db.session.add(row); db.session.flush()
    _audit(org, user["id"], "logistics_point.expert_created", "logistics_point", row.id,
           {"public_id": row.public_id, "governance_state": row.governance_state})
    return row


def create_point(payload, user):
    require_permission(user, "logistics_point.manage")
    org = organization_for_user(user["id"])
    point_type = db.session.scalar(
        select(LogisticsPointType).where(
            LogisticsPointType.public_id == payload.get("point_type_public_id"),
            LogisticsPointType.is_active.is_(True),
        )
    )
    if not point_type:
        raise OperationalError("NOT_FOUND", "Logistics point type not found.", 404)
    country, province, city, key = _geography(payload)
    norm = normalize_name(payload.get("fa_name"))
    exact = db.session.scalar(
        select(LogisticsPoint).where(
            LogisticsPoint.organization_id == org,
            LogisticsPoint.normalized_name == norm,
            LogisticsPoint.logistics_point_type_id == point_type.id,
            LogisticsPoint.country_id == country.id,
            LogisticsPoint.geography_key == key,
        )
    )
    if exact:
        raise OperationalError(
            "EXACT_DUPLICATE", "An exact governed logistics point already exists.", 409
        )
    probable = probable_duplicates(org, norm, point_type.id, country.id, city.id if city else None)
    if probable and payload.get("confirm_probable_duplicate") is not True:
        raise OperationalError(
            "PROBABLE_DUPLICATE",
            "Probable duplicate requires explicit confirmation.",
            409,
        )
    row = LogisticsPoint(
        organization_id=org,
        immutable_code=_text(payload, "immutable_code", 64, required=True).upper(),
        logistics_point_type_id=point_type.id,
        fa_name=_text(payload, "fa_name", 160, required=True),
        normalized_name=norm,
        en_name=_text(payload, "en_name", 160),
        country_id=country.id,
        province_id=province.id if province else None,
        city_id=city.id if city else None,
        geography_key=key,
        short_address=_text(payload, "short_address", 500),
        governance_state="APPROVED",
        created_by=user["id"],
        updated_by=user["id"],
    )
    db.session.add(row)
    db.session.flush()
    _audit(
        org,
        user["id"],
        "logistics_point.created",
        "logistics_point",
        row.id,
        {"public_id": row.public_id},
    )
    return row


def scoped_point(
    public_id, user, permission="logistics_point.read", include_inactive=True
):
    require_permission(user, permission)
    org = organization_for_user(user["id"])
    q = select(LogisticsPoint).options(
        joinedload(LogisticsPoint.global_point), joinedload(LogisticsPoint.global_adoption)
    ).where(
        LogisticsPoint.public_id == public_id, LogisticsPoint.organization_id == org
    ).execution_options(populate_existing=True)
    if not include_inactive:
        q = q.outerjoin(LogisticsPointType).where(
            LogisticsPoint.is_active.is_(True),
            or_(LogisticsPoint.logistics_point_type_id.is_(None), LogisticsPointType.is_active.is_(True)),
        )
    row = db.session.scalar(q)
    if not row:
        raise OperationalError("NOT_FOUND", "Logistics point not found.", 404)
    return row


def list_points(args, user, *, admin=False):
    if admin:
        require_permission(user, "logistics_point.read")
    else:
        require_any_permission(user, {
            "logistics_point.read",
            "operational_shipment.create_direct",
            "operational_shipment.create_from_quote",
            "operational_shipment.create",
        })
    org = organization_for_user(user["id"])
    q = select(LogisticsPoint).options(
        joinedload(LogisticsPoint.global_point), joinedload(LogisticsPoint.global_adoption)
    ).where(LogisticsPoint.organization_id == org)
    if admin:
        active = str(args.get("active", "all"))
        if active in {"true", "false"}:
            q = q.where(LogisticsPoint.is_active.is_(active == "true"))
    else:
        q = q.outerjoin(LogisticsPointType).where(
            LogisticsPoint.is_active.is_(True),
            or_(LogisticsPoint.logistics_point_type_id.is_(None), LogisticsPointType.is_active.is_(True)),
        )
    if args.get("type"):
        q = q.join(LogisticsPointType).where(
            LogisticsPointType.public_id == args["type"]
        )
    if args.get("country"):
        q = q.join(Country).where(Country.code == str(args["country"]).upper())
    if args.get("city_geoname_id"):
        try:
            city_identity = int(args["city_geoname_id"])
        except (TypeError, ValueError) as exc:
            raise OperationalError("VALIDATION_FAILED", "city_geoname_id is invalid.") from exc
        q = q.join(City).where(City.geoname_id == city_identity)
    if args.get("governance_state"):
        q = q.where(LogisticsPoint.governance_state == str(args["governance_state"]).upper())
    term = str(args.get("q", "")).strip()[:160]
    if term:
        q = q.where(
            or_(
                LogisticsPoint.immutable_code.ilike(f"%{term}%"),
                LogisticsPoint.fa_name.ilike(f"%{term}%"),
                LogisticsPoint.en_name.ilike(f"%{term}%"),
            )
        )
    page = max(1, int(args.get("page", 1)))
    per = min(100, max(1, int(args.get("per_page", 20))))
    total = db.session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.session.scalars(
        q.order_by(LogisticsPoint.immutable_code).offset((page - 1) * per).limit(per)
        .execution_options(populate_existing=True)
    ).all()
    return {
        "items": [point_projection(x) for x in rows],
        "page": page,
        "per_page": per,
        "total": total,
        "pages": ((total + per - 1) // per),
    }


def tracking_selector(args, user):
    """Bounded active LogisticsPoint selector for the authenticated tenant."""
    # This projection is also the location picker for existing operational
    # commands that already accept a logistics-point identity.  Possessing one
    # of those write authorities must not require the broader logistics-network
    # read permission just to discover the safe selector label.
    require_any_permission(user, {
        "logistics_point.read",
        "operational_shipment.create_direct",
        "operational_shipment.create_from_quote",
        "operational_shipment.create",
        "route_plan.create",
        "route_leg.manage",
        "execution_unit.update",
    })
    org = organization_for_user(user["id"])
    q = (
        select(LogisticsPoint)
        .outerjoin(LogisticsPointType)
        .options(
            joinedload(LogisticsPoint.point_type),
            joinedload(LogisticsPoint.country),
            joinedload(LogisticsPoint.province),
            joinedload(LogisticsPoint.city),
            joinedload(LogisticsPoint.global_point),
            joinedload(LogisticsPoint.global_adoption),
        )
        .where(
            LogisticsPoint.organization_id == org,
            LogisticsPoint.is_active.is_(True),
            or_(LogisticsPoint.logistics_point_type_id.is_(None), LogisticsPointType.is_active.is_(True)),
        )
    )
    term = str(args.get("q", args.get("search", ""))).strip()
    if len(term) > 160:
        raise OperationalError("VALIDATION_FAILED", "q is too long.", 400)
    if term:
        q = q.where(or_(
            LogisticsPoint.fa_name.ilike(f"%{term}%"),
            LogisticsPoint.en_name.ilike(f"%{term}%"),
            LogisticsPoint.immutable_code.ilike(f"%{term}%"),
        ))
    country_code = str(args.get("country_code", "")).strip().upper()
    if country_code:
        if len(country_code) != 2:
            raise OperationalError("VALIDATION_FAILED", "country_code is invalid.", 400)
        q = q.join(Country).where(Country.code == country_code)
    if args.get("city_geoname_id"):
        try:
            city_identity = int(args["city_geoname_id"])
        except (TypeError, ValueError) as exc:
            raise OperationalError("VALIDATION_FAILED", "city_geoname_id is invalid.", 400) from exc
        q = q.join(City).where(City.geoname_id == city_identity)
    type_code = str(args.get("type_code", "")).strip().upper()
    if type_code:
        if len(type_code) > 64:
            raise OperationalError("VALIDATION_FAILED", "type_code is too long.", 400)
        q = q.where(LogisticsPointType.immutable_code == type_code)
    try:
        limit = min(100, max(1, int(args.get("limit", 20))))
        offset = max(0, int(args.get("offset", 0)))
    except (TypeError, ValueError) as exc:
        raise OperationalError("VALIDATION_FAILED", "pagination is invalid.", 400) from exc
    rows = db.session.scalars(
        q.order_by(LogisticsPoint.fa_name, LogisticsPoint.id)
        .offset(offset)
        .limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [
            {
                "public_id": row.public_id,
                "fa_name": row.fa_name,
                "en_name": row.en_name,
                "immutable_code": row.immutable_code,
                "selector_kind": (
                    "organization_reference"
                    if row.global_point is not None and row.global_adoption is not None
                    else "organization_private"
                ),
                "type": {
                    "code": row.point_type.immutable_code,
                    "label": row.point_type.fa_name,
                } if row.point_type else None,
                "country": {
                    "code": row.country.code,
                    "label": row.country.name_fa,
                },
                "province": row.province.name_fa if row.province else None,
                "city": row.city.name_fa if row.city else None,
                "governance_state": row.governance_state,
            }
            for row in rows
        ],
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }


def canonical_countries(args):
    term = str(args.get("q", "")).strip()[:160]
    q = select(Country).where(Country.is_active.is_(True))
    if term:
        q = q.where(or_(*(geo.searchable(field).like(geo.pattern(term), escape="!")
                         for field in (Country.name_fa, Country.name_en, Country.code))))
    rows = db.session.scalars(q.order_by(Country.name_fa, Country.code)).all()
    return {"items": [{"id": row.id, "code": row.code, "name_fa": row.name_fa,
                       "name_en": row.name_en, "geography_supported": row.code in COUNTRY_SCOPE} for row in rows]}


def canonical_admin1(args):
    code = str(args.get("country_code", "")).strip().upper()
    if len(code) != 2:
        raise OperationalError("VALIDATION_FAILED", "country_code is required.")
    term = str(args.get("q", "")).strip()[:160]
    q = select(Province).join(Country).where(
        Country.code == code, Country.is_active.is_(True),
        Province.dataset_id == GEONAMES_DATASET_ID, Province.is_active.is_(True))
    rows = db.session.scalars(q.order_by(Province.geoname_id)).all()
    items = [{"source_id": row.id, "geoname_id": row.geoname_id, "code": row.code,
              "name_fa": geo.name_fa(row), "name_en": row.name_en} for row in rows]
    if term:
        items = [row for row in items if any(geo.normalize(term) in geo.normalize(row[key] or "")
                                             for key in ("name_fa", "name_en", "code"))]
    return {"items": sorted(items, key=lambda row: (row["name_fa"], row["geoname_id"]))}


def canonical_cities(args):
    country_code = str(args.get("country_code", "")).strip().upper()
    raw_admin_identity = args.get("admin1_geoname_id")
    try:
        admin_identity = int(raw_admin_identity) if raw_admin_identity not in (None, "") else None
        offset = int(args.get("offset", 0))
        limit = int(args.get("limit", 200))
        if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
            raise ValueError()
    except (TypeError, ValueError) as exc:
        raise OperationalError("VALIDATION_FAILED", "Valid location paging parameters are required.") from exc
    if admin_identity is None and len(country_code) != 2:
        raise OperationalError("VALIDATION_FAILED", "country_code or admin1_geoname_id is required.")
    term = str(args.get("q", "")).strip()[:160]
    q = select(City).join(Province, City.province_id == Province.id).join(Country, City.country_id == Country.id).where(
        Province.dataset_id == GEONAMES_DATASET_ID,
        Province.is_active.is_(True), Country.is_active.is_(True), City.country_id == Province.country_id,
        City.dataset_id == GEONAMES_DATASET_ID, City.is_active.is_(True))
    if admin_identity is not None:
        q = q.where(Province.geoname_id == admin_identity)
    else:
        q = q.where(Country.code == country_code)
    if term:
        q = q.where(or_(*(geo.searchable(field).like(geo.pattern(term), escape="!")
                         for field in (City.name_fa, City.name_en, City.code, cast(City.aliases, Text)))))
        normalized = geo.normalize(term)
        exact_rank = case(
            (geo.searchable(City.name_fa) == normalized, 0),
            (geo.searchable(City.name_en) == normalized, 0),
            (geo.searchable(City.code) == normalized, 0),
            else_=1,
        )
        q = q.order_by(exact_rank)
    rows = db.session.scalars(q.order_by(City.name_fa, City.geoname_id).offset(offset).limit(limit + 1)).all()
    return {"items": [{"source_id": row.id, "geoname_id": row.geoname_id,
                        "name_fa": geo.name_fa(row), "name_en": row.name_en,
                        "province": {"source_id": row.province.id,
                                     "geoname_id": row.province.geoname_id,
                                     "name_fa": geo.name_fa(row.province),
                                     "name_en": row.province.name_en},
                        "latitude": str(row.latitude), "longitude": str(row.longitude)} for row in rows[:limit]],
            "has_more": len(rows) > limit, "offset": offset, "limit": limit}


def update_point(row, payload, user):
    _version(row, payload)
    if (
        "immutable_code" in payload
        and str(payload["immutable_code"]).upper() != row.immutable_code
    ):
        raise OperationalError("VALIDATION_FAILED", "immutable_code cannot be changed.")
    if any(k in payload for k in ("country_code", "province_code", "city_code")):
        country, province, city, key = _geography(
            {
                "country_code": payload.get("country_code", row.country.code),
                "province_code": payload.get(
                    "province_code", row.province.code if row.province else None
                ),
                "city_code": payload.get(
                    "city_code", row.city.code if row.city else None
                ),
            }
        )
        row.country_id, row.province_id, row.city_id, row.geography_key = (
            country.id,
            province.id if province else None,
            city.id if city else None,
            key,
        )
    if "point_type_public_id" in payload:
        point_type = None
        if payload.get("point_type_public_id"):
            point_type = db.session.scalar(select(LogisticsPointType).where(
                LogisticsPointType.public_id == payload["point_type_public_id"],
                LogisticsPointType.is_active.is_(True),
            ))
            if point_type is None:
                raise OperationalError("NOT_FOUND", "Logistics point type not found.", 404)
        row.logistics_point_type_id = point_type.id if point_type else None
    for field, limit in (("fa_name", 160), ("en_name", 160), ("short_address", 500), ("description", 4000)):
        if field in payload:
            setattr(
                row,
                field,
                _text(payload, field, limit, required=field == "fa_name"),
            )
    if "latitude" in payload:
        row.latitude = _coordinate(payload, "latitude", Decimal("-90"), Decimal("90"))
    if "longitude" in payload:
        row.longitude = _coordinate(payload, "longitude", Decimal("-180"), Decimal("180"))
    row.normalized_name = normalize_name(row.fa_name)
    row.updated_by = user["id"]
    row.updated_at = utcnow()
    row.version += 1
    _audit(
        row.organization_id,
        user["id"],
        "logistics_point.updated",
        "logistics_point",
        row.id,
    )
    return row


def review_point(row, action, payload, user):
    _version(row, payload)
    if action not in {"approve", "flag-duplicate", "deactivate"}:
        raise OperationalError("NOT_FOUND", "Action not found.", 404)
    if action == "flag-duplicate":
        duplicate = scoped_point(payload.get("duplicate_of_public_id"), user, "logistics_point.manage")
        if duplicate.id == row.id:
            raise OperationalError("VALIDATION_FAILED", "A location cannot duplicate itself.")
        row.duplicate_of_id = duplicate.id
        row.governance_state = "POTENTIAL_DUPLICATE"
    elif action == "approve":
        row.duplicate_of_id = None
        row.governance_state = "APPROVED"
    else:
        row.is_active = False
        row.governance_state = "DEACTIVATED"
    row.reviewed_at = utcnow(); row.reviewed_by = user["id"]
    row.updated_at = utcnow(); row.updated_by = user["id"]; row.version += 1
    _audit(row.organization_id, user["id"], f"logistics_point.{action}", "logistics_point", row.id)
    return row


def set_active(row, active, payload, user):
    _version(row, payload)
    row.is_active = active
    row.updated_by = user["id"]
    row.updated_at = utcnow()
    row.version += 1
    organization_id = getattr(row, "organization_id", None)
    if organization_id:
        _audit(
            organization_id,
            user["id"],
            "logistics_network.activated"
            if active
            else "logistics_network.deactivated",
            row.__tablename__,
            row.id,
        )
    return row


def scoped_project(public_id, user, permission="project_logistics_point.read"):
    require_permission(user, permission)
    from backend.services.project_access_authorization import scoped_project as authorized_project
    return authorized_project(public_id, user)


def list_associations(project):
    rows = db.session.scalars(
        select(ProjectLogisticsPoint)
        .where(ProjectLogisticsPoint.project_id == project.id)
        .order_by(
            ProjectLogisticsPoint.is_active.desc(),
            ProjectLogisticsPoint.sequence_number,
        )
    ).all()
    return {"items": [association_projection(x) for x in rows]}


def create_association(project, payload, user):
    point = scoped_point(
        str(payload.get("logistics_point_public_id", "")), user, include_inactive=False
    )
    role = str(payload.get("project_role", "")).upper()
    seq = payload.get("sequence_number")
    if role not in PROJECT_LOGISTICS_ROLES or not isinstance(seq, int) or seq < 1:
        raise OperationalError(
            "VALIDATION_FAILED",
            "A bounded role and positive sequence_number are required.",
        )
    row = ProjectLogisticsPoint(
        organization_id=project.organization_id,
        project_id=project.id,
        logistics_point_id=point.id,
        project_role=role,
        sequence_number=seq,
        display_label=_text(payload, "display_label", 160),
        notes=_text(payload, "notes", 4000),
        created_by=user["id"],
        updated_by=user["id"],
    )
    db.session.add(row)
    db.session.flush()
    _audit(
        project.organization_id,
        user["id"],
        "project_logistics_point.created",
        "project_logistics_point",
        row.id,
        {"project_id": project.public_id},
    )
    return row


def scoped_association(project, public_id):
    row = db.session.scalar(
        select(ProjectLogisticsPoint).where(
            ProjectLogisticsPoint.public_id == public_id,
            ProjectLogisticsPoint.project_id == project.id,
        )
    )
    if not row:
        raise OperationalError("NOT_FOUND", "Project logistics point not found.", 404)
    return row


def update_association(row, payload, user):
    _version(row, payload)
    if "project_role" in payload:
        role = str(payload["project_role"]).upper()
        if role not in PROJECT_LOGISTICS_ROLES:
            raise OperationalError("VALIDATION_FAILED", "project_role is invalid.")
        row.project_role = role
    if "sequence_number" in payload:
        if (
            not isinstance(payload["sequence_number"], int)
            or payload["sequence_number"] < 1
        ):
            raise OperationalError("VALIDATION_FAILED", "sequence_number is invalid.")
        row.sequence_number = payload["sequence_number"]
    for field, limit in (("display_label", 160), ("notes", 4000)):
        if field in payload:
            setattr(row, field, _text(payload, field, limit))
    row.updated_by = user["id"]
    row.updated_at = utcnow()
    row.version += 1
    _audit(
        row.organization_id,
        user["id"],
        "project_logistics_point.updated",
        "project_logistics_point",
        row.id,
    )
    return row


def reorder(project, payload, user):
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise OperationalError("VALIDATION_FAILED", "items must be a non-empty array.")
    rows = db.session.scalars(
        select(ProjectLogisticsPoint)
        .where(
            ProjectLogisticsPoint.project_id == project.id,
            ProjectLogisticsPoint.is_active.is_(True),
        )
        .with_for_update()
    ).all()
    by_id = {x.public_id: x for x in rows}
    if {str(x.get("public_id")) for x in items} != set(by_id):
        raise OperationalError(
            "VALIDATION_FAILED",
            "reorder must include every active association exactly once.",
        )
    temporary_base = (
        max((row.sequence_number for row in rows), default=0) + len(rows) + 1
    )
    for index, item in enumerate(items, 1):
        row = by_id[str(item["public_id"])]
        if item.get("version") != row.version:
            raise OperationalError(
                "VERSION_CONFLICT", "Association version conflict.", 409
            )
        row.sequence_number = temporary_base + index
        row.updated_by = user["id"]
        row.version += 1
    db.session.flush()
    for index, item in enumerate(items, 1):
        by_id[str(item["public_id"])].sequence_number = index
    _audit(
        project.organization_id,
        user["id"],
        "project_logistics_point.reordered",
        "project",
        project.id,
        {"count": len(items)},
    )
    return list(by_id.values())


def commit_or_error():
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise OperationalError(
            "CONFLICT", "Logistics Network constraint conflict.", 409
        ) from exc
