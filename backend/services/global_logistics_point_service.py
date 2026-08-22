"""Read-only Platform API projection for ADR-041 Phase 1."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from backend.extensions import db
from backend.global_logistics_point_models import (
    GLOBAL_POINT_LIFECYCLES,
    GLOBAL_POINT_MODES,
    GLOBAL_POINT_VERIFICATION_STATES,
    GlobalLogisticsPoint,
    GlobalLogisticsPointAlias,
    GlobalLogisticsPointCorridorTag,
    GlobalLogisticsPointMode,
)
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country
from backend.services.operational_service import OperationalError


def _opaque_id(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise OperationalError("NOT_FOUND", "Global logistics point not found.", 404) from exc


def _options():
    return (
        selectinload(GlobalLogisticsPoint.aliases),
        selectinload(GlobalLogisticsPoint.modes),
        selectinload(GlobalLogisticsPoint.external_codes),
        selectinload(GlobalLogisticsPoint.corridor_tags),
        selectinload(GlobalLogisticsPoint.sources),
        selectinload(GlobalLogisticsPoint.point_type),
        selectinload(GlobalLogisticsPoint.country),
        selectinload(GlobalLogisticsPoint.province),
        selectinload(GlobalLogisticsPoint.city),
        selectinload(GlobalLogisticsPoint.international_city),
    )


def projection(row: GlobalLogisticsPoint) -> dict:
    return {
        "public_id": row.public_id,
        "immutable_code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "point_type": {
            "public_id": row.point_type.public_id,
            "code": row.point_type.immutable_code,
            "fa_name": row.point_type.fa_name,
            "en_name": row.point_type.en_name,
        },
        "country": {
            "code": row.country.code,
            "fa_name": row.country.name_fa,
            "en_name": row.country.name_en,
        },
        "geography": {
            "province": row.province.name_fa if row.province else row.region_name,
            "city": (
                row.city.name_fa
                if row.city
                else row.international_city.name_fa
                if row.international_city
                else row.city_name
            ),
            "short_address": row.short_address,
            "latitude": float(row.latitude) if row.latitude is not None else None,
            "longitude": float(row.longitude) if row.longitude is not None else None,
            "timezone": row.timezone_name,
            "un_locode": row.un_locode,
            "border_pair_key": row.border_pair_key,
            "border_side": row.border_side,
        },
        "aliases": [
            {"value": item.alias, "language_code": item.language_code}
            for item in sorted(row.aliases, key=lambda item: item.normalized_alias)
        ],
        "supported_modes": sorted(item.mode_code for item in row.modes),
        "corridor_tags": sorted(item.tag_code for item in row.corridor_tags),
        "external_codes": [
            {"scheme": item.scheme, "value": item.value}
            for item in sorted(
                row.external_codes, key=lambda item: (item.scheme, item.normalized_value)
            )
        ],
        "lifecycle_status": row.lifecycle_status,
        "verification_status": row.verification_status,
        "version": row.version,
    }


def list_points(args) -> dict:
    query = select(GlobalLogisticsPoint).options(*_options())
    term = str(args.get("q", "")).strip()
    if len(term) > 160:
        raise OperationalError("VALIDATION_FAILED", "q is too long.", 400)
    if term:
        pattern = f"%{term}%"
        query = query.where(
            or_(
                GlobalLogisticsPoint.immutable_code.ilike(pattern),
                GlobalLogisticsPoint.fa_name.ilike(pattern),
                GlobalLogisticsPoint.en_name.ilike(pattern),
                GlobalLogisticsPoint.aliases.any(
                    GlobalLogisticsPointAlias.alias.ilike(pattern)
                ),
            )
        )
    country = str(args.get("country", "")).strip().upper()
    if country:
        if len(country) not in {2, 3}:
            raise OperationalError("VALIDATION_FAILED", "country is invalid.", 400)
        query = query.join(GlobalLogisticsPoint.country).where(Country.code == country)
    type_code = str(args.get("type", "")).strip().upper()
    if type_code:
        query = query.join(GlobalLogisticsPoint.point_type).where(
            LogisticsPointType.immutable_code == type_code
        )
    status = str(args.get("status", "ACTIVE")).strip().upper()
    if status != "ALL":
        if status not in GLOBAL_POINT_LIFECYCLES:
            raise OperationalError("VALIDATION_FAILED", "status is invalid.", 400)
        query = query.where(GlobalLogisticsPoint.lifecycle_status == status)
    verification = str(args.get("verification", "")).strip().upper()
    if verification:
        if verification not in GLOBAL_POINT_VERIFICATION_STATES:
            raise OperationalError("VALIDATION_FAILED", "verification is invalid.", 400)
        query = query.where(GlobalLogisticsPoint.verification_status == verification)
    mode = str(args.get("mode", "")).strip().upper()
    if mode:
        if mode not in GLOBAL_POINT_MODES:
            raise OperationalError("VALIDATION_FAILED", "mode is invalid.", 400)
        query = query.where(
            GlobalLogisticsPoint.modes.any(GlobalLogisticsPointMode.mode_code == mode)
        )
    corridor = str(args.get("corridor", "")).strip().upper()
    if corridor:
        if len(corridor) > 64:
            raise OperationalError("VALIDATION_FAILED", "corridor is invalid.", 400)
        query = query.where(
            GlobalLogisticsPoint.corridor_tags.any(
                GlobalLogisticsPointCorridorTag.tag_code == corridor
            )
        )
    try:
        page = max(1, int(args.get("page", 1)))
        per_page = min(100, max(1, int(args.get("per_page", 20))))
    except (TypeError, ValueError) as exc:
        raise OperationalError("VALIDATION_FAILED", "pagination is invalid.", 400) from exc
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.session.scalar(count_query) or 0
    rows = db.session.scalars(
        query.order_by(GlobalLogisticsPoint.immutable_code, GlobalLogisticsPoint.public_id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return {
        "items": [projection(row) for row in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    }


def detail(public_id: str) -> GlobalLogisticsPoint:
    normalized = _opaque_id(public_id)
    row = db.session.scalar(
        select(GlobalLogisticsPoint)
        .options(*_options())
        .where(GlobalLogisticsPoint.public_id == normalized)
    )
    if row is None:
        raise OperationalError("NOT_FOUND", "Global logistics point not found.", 404)
    return row
