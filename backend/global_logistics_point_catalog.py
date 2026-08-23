"""Governed importer for the approved nine-point ADR-041 baseline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


from backend.extensions import db
from backend.global_logistics_point_models import (
    GLOBAL_POINT_BORDER_SIDES,
    GLOBAL_POINT_MODES,
    GlobalLogisticsPoint,
    GlobalLogisticsPointAlias,
    GlobalLogisticsPointCorridorTag,
    GlobalLogisticsPointExternalCode,
    GlobalLogisticsPointMode,
    GlobalLogisticsPointSource,
)
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country, ExpertUser, ReferenceDataSeedRun

CATALOG_PATH = (
    Path(__file__).with_name("reference_data")
    / "global-logistics-points-china-iran-v1.0.0-approved-baseline.json"
)
CATALOG_VERSION = "china-iran-global-logistics-points-1.0.0-approved-baseline"
APPROVED_CHECKSUM = (
    "sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c"
)
APPROVED_CODES = (
    "GLP-CN-ALASHANKOU",
    "GLP-CN-NINGBO-ZHOUSHAN",
    "GLP-IR-INCHEH-BORUN",
    "GLP-IR-SARAKHS",
    "GLP-KG-IRKESHTAM",
    "GLP-KZ-ALTYNKOL",
    "GLP-KZ-DOSTYK",
    "GLP-TM-FARAP",
    "GLP-TM-SERAKHS",
)
TOP_KEYS = {
    "approved_global_logistics_points",
    "approved_subset_count",
    "canonicalization",
    "catalog_version",
    "checksum",
    "owner_decision_reference",
    "parent_catalog_checksum",
    "parent_catalog_path",
    "parent_catalog_version",
    "production_seed_authorized",
    "schema_version",
}
ITEM_KEYS = {"review", "runtime_candidate"}
REVIEW_KEYS = {
    "classification",
    "evidence_class",
    "legacy_keys",
    "open_questions",
    "package_review_status",
    "sources",
    "tier",
}
SOURCE_KEYS = {
    "checked_date",
    "source_organization",
    "source_reference",
    "source_title",
    "source_type",
    "source_url",
    "source_version",
}
RUNTIME_KEYS = {
    "aliases",
    "border_pair_key",
    "border_side",
    "city_name",
    "corridor_tags",
    "country_code",
    "en_name",
    "external_codes",
    "fa_name",
    "facility_identity_key",
    "geography_key",
    "immutable_code",
    "latitude",
    "longitude",
    "normalized_name",
    "point_type_code",
    "proposed_lifecycle_status",
    "proposed_verification_status",
    "region_name",
    "short_address",
    "supported_modes",
    "timezone",
    "un_locode",
}


class GlobalCatalogValidationError(ValueError):
    pass


class GlobalCatalogApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class GlobalCatalog:
    payload: dict[str, Any]
    rows: tuple[dict[str, Any], ...]
    checksum: str
    catalog_version: str


@dataclass
class GlobalCatalogPlan:
    catalog_version: str
    checksum: str
    environment: str
    planned_count: int = 9
    created_count: int = 0
    unchanged_count: int = 0
    conflict_count: int = 0
    conflicts: list[dict[str, str]] = field(default_factory=list)
    candidate_codes: list[str] = field(default_factory=lambda: list(APPROVED_CODES))

    def as_dict(self) -> dict[str, Any]:
        return dict(
            catalog_version=self.catalog_version,
            checksum=self.checksum,
            environment=self.environment,
            planned_count=self.planned_count,
            created_count=self.created_count,
            unchanged_count=self.unchanged_count,
            conflict_count=self.conflict_count,
            conflicts=self.conflicts,
            candidate_codes=self.candidate_codes,
        )


def canonical_checksum(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "checksum"}
    encoded = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _text(value: Any, name: str, limit: int, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > limit
    ):
        raise GlobalCatalogValidationError(f"invalid {name}")
    return value


def load_catalog(path: Path = CATALOG_PATH) -> GlobalCatalog:
    try:
        raw = Path(path).read_bytes()
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GlobalCatalogValidationError("package is not strict UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != TOP_KEYS:
        raise GlobalCatalogValidationError("unexpected package fields")
    if (
        payload["schema_version"] != "1"
        or payload["catalog_version"] != CATALOG_VERSION
    ):
        raise GlobalCatalogValidationError(
            "package schema or catalog version is not approved"
        )
    if payload["production_seed_authorized"] is not False:
        raise GlobalCatalogValidationError(
            "package must not self-authorize Production seed"
        )
    if (
        payload["checksum"] != canonical_checksum(payload)
        or payload["checksum"] != APPROVED_CHECKSUM
    ):
        raise GlobalCatalogValidationError("package checksum is modified or unapproved")
    rows = payload.get("approved_global_logistics_points")
    if (
        payload.get("approved_subset_count") != 9
        or not isinstance(rows, list)
        or len(rows) != 9
    ):
        raise GlobalCatalogValidationError(
            "package must contain exactly nine approved rows"
        )
    seen_codes: set[str] = set()
    seen_facilities: set[tuple[str, str, str]] = set()
    for item in rows:
        if not isinstance(item, dict) or set(item) != ITEM_KEYS:
            raise GlobalCatalogValidationError("unexpected approved row fields")
        review, runtime = item["review"], item["runtime_candidate"]
        if not isinstance(review, dict) or set(review) != REVIEW_KEYS:
            raise GlobalCatalogValidationError("unexpected review fields")
        if (
            review["package_review_status"] != "READY_FOR_OWNER_APPROVAL"
            or review["open_questions"] != []
        ):
            raise GlobalCatalogValidationError(
                "package contains unresolved review state"
            )
        sources = review["sources"]
        if not isinstance(sources, list) or not sources:
            raise GlobalCatalogValidationError("required provenance is missing")
        for source in sources:
            if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
                raise GlobalCatalogValidationError("unexpected provenance fields")
            for key in (
                "source_organization",
                "source_reference",
                "source_version",
                "checked_date",
            ):
                _text(source.get(key), f"source.{key}", 500)
        if not isinstance(runtime, dict) or set(runtime) != RUNTIME_KEYS:
            raise GlobalCatalogValidationError("unexpected runtime candidate fields")
        code = _text(runtime.get("immutable_code"), "immutable_code", 64)
        country = _text(runtime.get("country_code"), "country_code", 3)
        point_type = _text(runtime.get("point_type_code"), "point_type_code", 64)
        facility = _text(
            runtime.get("facility_identity_key"), "facility_identity_key", 240
        )
        if (
            runtime["proposed_lifecycle_status"] != "DRAFT"
            or runtime["proposed_verification_status"] != "UNVERIFIED"
        ):
            raise GlobalCatalogValidationError(
                "approved lifecycle must be DRAFT/UNVERIFIED"
            )
        if runtime["border_side"] not in GLOBAL_POINT_BORDER_SIDES:
            raise GlobalCatalogValidationError(f"invalid border side for {code}")
        if point_type == "BORDER_CROSSING" and not runtime["border_pair_key"]:
            raise GlobalCatalogValidationError(f"border pair is required for {code}")
        modes = runtime["supported_modes"]
        if (
            not isinstance(modes, list)
            or not modes
            or len(modes) != len(set(modes))
            or not set(modes) <= GLOBAL_POINT_MODES
        ):
            raise GlobalCatalogValidationError(f"invalid modes for {code}")
        for key in ("aliases", "external_codes", "corridor_tags"):
            if not isinstance(runtime[key], list):
                raise GlobalCatalogValidationError(f"invalid {key} for {code}")
        if code in seen_codes:
            raise GlobalCatalogValidationError(f"duplicate immutable code: {code}")
        identity = (country, point_type, facility)
        if identity in seen_facilities:
            raise GlobalCatalogValidationError(f"duplicate facility identity: {code}")
        seen_codes.add(code)
        seen_facilities.add(identity)
    if tuple(sorted(seen_codes)) != APPROVED_CODES:
        raise GlobalCatalogValidationError(
            "package immutable-code set is not the approved nine-row set"
        )
    return GlobalCatalog(
        payload=payload,
        rows=tuple(rows),
        checksum=payload["checksum"],
        catalog_version=payload["catalog_version"],
    )


def _expected(entry: dict[str, Any]) -> dict[str, Any]:
    runtime, review = entry["runtime_candidate"], entry["review"]
    return {
        "immutable_code": runtime["immutable_code"],
        "country_code": runtime["country_code"],
        "point_type_code": runtime["point_type_code"],
        "fa_name": runtime["fa_name"],
        "en_name": runtime["en_name"],
        "normalized_name": runtime["normalized_name"],
        "geography_key": runtime["geography_key"],
        "facility_identity_key": runtime["facility_identity_key"],
        "region_name": runtime["region_name"],
        "city_name": runtime["city_name"],
        "short_address": runtime["short_address"],
        "latitude": runtime["latitude"],
        "longitude": runtime["longitude"],
        "timezone_name": runtime["timezone"],
        "un_locode": runtime["un_locode"],
        "border_pair_key": runtime["border_pair_key"],
        "border_side": runtime["border_side"],
        "lifecycle_status": "DRAFT",
        "verification_status": "UNVERIFIED",
        "aliases": sorted((x["value"], x["language_code"]) for x in runtime["aliases"]),
        "modes": sorted(runtime["supported_modes"]),
        "external_codes": sorted(
            (x["scheme"].upper(), x["value"], x["source_reference"])
            for x in runtime["external_codes"]
        ),
        "corridor_tags": sorted(runtime["corridor_tags"]),
        "sources": sorted(
            (
                x["source_organization"],
                x["source_reference"],
                x["source_version"],
                x["checked_date"],
            )
            for x in review["sources"]
        ),
    }


def _actual(row: GlobalLogisticsPoint) -> dict[str, Any]:
    def number(value):
        return None if value is None else float(value)

    return {
        "immutable_code": row.immutable_code,
        "country_code": row.country.code,
        "point_type_code": row.point_type.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "normalized_name": row.normalized_name,
        "geography_key": row.geography_key,
        "facility_identity_key": row.facility_identity_key,
        "region_name": row.region_name,
        "city_name": row.city_name,
        "short_address": row.short_address,
        "latitude": number(row.latitude),
        "longitude": number(row.longitude),
        "timezone_name": row.timezone_name,
        "un_locode": row.un_locode,
        "border_pair_key": row.border_pair_key,
        "border_side": row.border_side,
        "lifecycle_status": row.lifecycle_status,
        "verification_status": row.verification_status,
        "aliases": sorted((x.alias, x.language_code) for x in row.aliases),
        "modes": sorted(x.mode_code for x in row.modes),
        "external_codes": sorted(
            (x.scheme, x.value, x.source_reference) for x in row.external_codes
        ),
        "corridor_tags": sorted(x.tag_code for x in row.corridor_tags),
        "sources": sorted(
            (
                x.source_organization,
                x.source_reference,
                x.source_version,
                x.retrieved_at.date().isoformat() if x.retrieved_at else None,
            )
            for x in row.sources
        ),
    }


def plan_catalog(catalog: GlobalCatalog, environment: str) -> GlobalCatalogPlan:
    plan = GlobalCatalogPlan(catalog.catalog_version, catalog.checksum, environment)
    existing = {row.immutable_code: row for row in GlobalLogisticsPoint.query.all()}
    facility_map = {
        (
            row.country.code,
            row.point_type.immutable_code,
            row.facility_identity_key,
        ): row.immutable_code
        for row in existing.values()
    }
    countries = {
        row.code
        for row in Country.query.filter(
            Country.code.in_(
                {x["runtime_candidate"]["country_code"] for x in catalog.rows}
            )
        )
    }
    point_types = {
        row.immutable_code
        for row in LogisticsPointType.query.filter(
            LogisticsPointType.immutable_code.in_(
                {x["runtime_candidate"]["point_type_code"] for x in catalog.rows}
            )
        )
    }
    for entry in catalog.rows:
        expected = _expected(entry)
        code = expected["immutable_code"]
        if expected["country_code"] not in countries:
            plan.conflicts.append(
                {"code": code, "reason": "required country is absent"}
            )
            continue
        if expected["point_type_code"] not in point_types:
            plan.conflicts.append(
                {"code": code, "reason": "required LogisticsPointType is absent"}
            )
            continue
        row = existing.get(code)
        other = facility_map.get(
            (
                expected["country_code"],
                expected["point_type_code"],
                expected["facility_identity_key"],
            )
        )
        if other and other != code:
            plan.conflicts.append(
                {
                    "code": code,
                    "reason": "facility identity belongs to a different code",
                }
            )
        elif row is None:
            plan.created_count += 1
        elif _actual(row) == expected:
            plan.unchanged_count += 1
        else:
            plan.conflicts.append(
                {"code": code, "reason": "existing governed values differ"}
            )
    plan.conflict_count = len(plan.conflicts)
    return plan


def _new_point(
    entry: dict[str, Any],
    actor_id: int,
    countries: dict[str, Country],
    point_types: dict[str, LogisticsPointType],
) -> GlobalLogisticsPoint:
    runtime, review = entry["runtime_candidate"], entry["review"]
    row = GlobalLogisticsPoint(
        immutable_code=runtime["immutable_code"],
        point_type=point_types[runtime["point_type_code"]],
        country=countries[runtime["country_code"]],
        fa_name=runtime["fa_name"],
        en_name=runtime["en_name"],
        normalized_name=runtime["normalized_name"],
        geography_key=runtime["geography_key"],
        facility_identity_key=runtime["facility_identity_key"],
        region_name=runtime["region_name"],
        city_name=runtime["city_name"],
        short_address=runtime["short_address"],
        latitude=runtime["latitude"],
        longitude=runtime["longitude"],
        timezone_name=runtime["timezone"],
        un_locode=runtime["un_locode"],
        border_pair_key=runtime["border_pair_key"],
        border_side=runtime["border_side"],
        lifecycle_status="DRAFT",
        verification_status="UNVERIFIED",
        created_by=actor_id,
        updated_by=actor_id,
    )
    row.aliases = [
        GlobalLogisticsPointAlias(
            alias=x["value"],
            normalized_alias=x["value"].strip().casefold(),
            language_code=x["language_code"],
        )
        for x in runtime["aliases"]
    ]
    row.modes = [
        GlobalLogisticsPointMode(mode_code=x) for x in runtime["supported_modes"]
    ]
    row.external_codes = [
        GlobalLogisticsPointExternalCode(
            scheme=x["scheme"].upper(),
            value=x["value"],
            normalized_value=x["value"].strip().casefold(),
            source_reference=x["source_reference"],
        )
        for x in runtime["external_codes"]
    ]
    row.corridor_tags = [
        GlobalLogisticsPointCorridorTag(tag_code=x) for x in runtime["corridor_tags"]
    ]
    row.sources = [
        GlobalLogisticsPointSource(
            source_organization=x["source_organization"],
            source_reference=x["source_reference"],
            source_version=x["source_version"],
            retrieved_at=datetime.fromisoformat(x["checked_date"]),
            reviewed_by=actor_id,
        )
        for x in review["sources"]
    ]
    return row


def _run(
    catalog: GlobalCatalog,
    environment: str,
    operator: str,
    approval_reference: str,
    plan: GlobalCatalogPlan,
) -> ReferenceDataSeedRun:
    run = ReferenceDataSeedRun(
        catalog_version=catalog.catalog_version,
        catalog_family="GLOBAL_LOGISTICS_POINT",
        catalog_name="CHINA_IRAN_APPROVED_BASELINE",
        schema_version="1",
        checksum=catalog.checksum,
        environment=environment,
        mode="apply",
        planned_count=plan.planned_count,
        created_count=0,
        unchanged_count=plan.unchanged_count,
        conflict_count=plan.conflict_count,
        status="started",
        executed_by=operator,
        approval_reference=approval_reference,
    )
    db.session.add(run)
    db.session.commit()
    return run


def apply_catalog(
    catalog: GlobalCatalog,
    *,
    environment: str,
    operator: str,
    approval_reference: str,
    expected_checksum: str,
    user_id: int,
    failure_hook: Any = None,
) -> tuple[GlobalCatalogPlan, ReferenceDataSeedRun]:
    operator, approval_reference = (
        str(operator or "").strip(),
        str(approval_reference or "").strip(),
    )
    if expected_checksum != catalog.checksum:
        raise GlobalCatalogApplyError(
            "expected checksum does not match the approved package"
        )
    if not operator or len(operator) > 160:
        raise GlobalCatalogApplyError("a bounded explicit operator is required")
    if not approval_reference or len(approval_reference) > 200:
        raise GlobalCatalogApplyError(
            "a bounded explicit approval reference is required"
        )
    plan = plan_catalog(catalog, environment)
    run = _run(catalog, environment, operator, approval_reference, plan)
    actor = db.session.get(ExpertUser, user_id)
    if (
        actor is None
        or not actor.is_active
        or actor.authority != "PLATFORM_ADMIN"
        or actor.username != operator
    ):
        run.status = "refused"
        run.completed_at = datetime.utcnow()
        run.error_summary = "Apply refused: active PLATFORM_ADMIN identity did not match the named operator."
        db.session.commit()
        raise GlobalCatalogApplyError("active PLATFORM_ADMIN identity is required")
    if plan.conflict_count:
        run.status = "refused"
        run.completed_at = datetime.utcnow()
        run.error_summary = "Catalog conflicts detected; no catalog writes were made."
        db.session.commit()
        return plan, run
    try:
        countries = {x.code: x for x in Country.query.all()}
        point_types = {x.immutable_code: x for x in LogisticsPointType.query.all()}
        existing = {x.immutable_code for x in GlobalLogisticsPoint.query.all()}
        for entry in catalog.rows:
            if entry["runtime_candidate"]["immutable_code"] not in existing:
                db.session.add(_new_point(entry, actor.id, countries, point_types))
        if failure_hook:
            failure_hook()
        run.status = "succeeded"
        run.created_count = plan.created_count
        run.completed_at = datetime.utcnow()
        db.session.commit()
        return plan, run
    except Exception as exc:
        db.session.rollback()
        persisted = ReferenceDataSeedRun.query.filter_by(public_id=run.public_id).one()
        persisted.status = "failed"
        persisted.completed_at = datetime.utcnow()
        persisted.error_summary = f"Global catalog apply failed ({type(exc).__name__})."
        db.session.commit()
        raise GlobalCatalogApplyError("catalog apply rolled back") from exc
