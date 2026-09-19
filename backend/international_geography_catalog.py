"""Explicit, additive reconciliation for the governed worldwide geography catalog.

The catalog is never applied during application startup.  Operators first inspect
``plan_catalog`` and then invoke ``apply_catalog`` with the pinned checksum and a
named approval.  Existing identities, labels, provenance, and lifecycle state are
read-only to this reconciler.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from backend.extensions import db
from backend.models import Country, InternationalCity, ReferenceDataSeedRun


CATALOG_PATH = (
    Path(__file__).with_name("reference_data")
    / "international-geography-v2-fwd02.json"
)
CATALOG_DATASET_ID = "forwarder-international-geography-v2-fwd02"
CATALOG_VERSION = "2025-1"
CATALOG_SHA256 = "b3e71f12f7c9cc8a9c5061a9df0ed67f085636bc84bd7120400694adab2d48ca"
CATALOG_CHECKSUM = f"sha256:{CATALOG_SHA256}"
SOURCE_ARCHIVE_SHA256 = "ad409fc7149b10f98d61190c34d9daf78b78bb8b31464cc66de1a89d09b01b5d"
EXPECTED_COUNTRY_COUNT = 249
EXPECTED_LOCATION_COUNT = 115_208
EXPECTED_IRAN_LOCATION_COUNT = 154
EXPECTED_TYPE_COUNTS = {"airport": 5_252, "city": 102_894, "port": 7_062}
ALLOWED_LOCATION_TYPES = frozenset(EXPECTED_TYPE_COUNTS)
ALLOWED_SOURCE_STATUSES = frozenset(
    {"AA", "AC", "AF", "AI", "AS", "AM", "AQ", "RN", "RL"}
)
_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")
_UNLOCODE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}$")


class GeographyCatalogError(ValueError):
    """The checked-in catalog or an apply request is not safe to use."""


@dataclass(frozen=True)
class GeographyCatalog:
    payload: dict[str, Any]
    checksum: str
    country_count: int
    location_count: int
    iran_location_count: int
    location_type_counts: dict[str, int]
    duplicate_count: int
    invalid_record_count: int

    @property
    def dataset_id(self) -> str:
        return self.payload["dataset_id"]

    @property
    def snapshot_version(self) -> str:
        return self.payload["snapshot_version"]


@dataclass
class GeographyCatalogPlan:
    dataset_id: str
    catalog_version: str
    checksum: str
    country_count: int
    location_count: int
    iran_location_count: int
    location_type_counts: dict[str, int]
    created_country_count: int = 0
    created_location_count: int = 0
    unchanged_country_count: int = 0
    unchanged_location_count: int = 0
    conflicts: list[dict[str, str]] = field(default_factory=list)
    country_creates: list[dict[str, Any]] = field(default_factory=list, repr=False)
    location_creates: list[tuple[str, dict[str, Any]]] = field(
        default_factory=list, repr=False
    )

    @property
    def created_count(self) -> int:
        return self.created_country_count + self.created_location_count

    @property
    def unchanged_count(self) -> int:
        return self.unchanged_country_count + self.unchanged_location_count

    @property
    def skipped_count(self) -> int:
        return len(self.conflicts)

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    @property
    def planned_count(self) -> int:
        return self.country_count + self.location_count

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "catalog_version": self.catalog_version,
            "checksum": self.checksum,
            "country_count": self.country_count,
            "location_count": self.location_count,
            "iran_location_count": self.iran_location_count,
            "location_type_counts": dict(sorted(self.location_type_counts.items())),
            "italy_present": self._country_present("IT"),
            "norway_present": self._country_present("NO"),
            "created_country_count": self.created_country_count,
            "created_location_count": self.created_location_count,
            "created_count": self.created_count,
            "updated_count": 0,
            "unchanged_country_count": self.unchanged_country_count,
            "unchanged_location_count": self.unchanged_location_count,
            "unchanged_count": self.unchanged_count,
            "skipped_count": self.skipped_count,
            "conflict_count": self.conflict_count,
            "conflicts": self.conflicts,
        }

    def _country_present(self, code: str) -> bool:
        return any(
            item.get("code") == code for item in self.country_creates
        ) or self.country_count == EXPECTED_COUNTRY_COUNT


def _required_text(value: Any, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise GeographyCatalogError(f"{field_name} must be non-empty trimmed text")
    if len(value) > maximum:
        raise GeographyCatalogError(f"{field_name} exceeds {maximum} characters")
    return value


def _catalog_locations(payload: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    defaults = payload.get("location_defaults", {})
    for record in payload.get("records", []):
        code = record["country"]["code"]
        for item in record.get("locations", []):
            yield code, {**defaults, **item}


def load_catalog(path: Path = CATALOG_PATH) -> GeographyCatalog:
    """Load and fully validate the exact approved bytes without network access."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise GeographyCatalogError("geography catalog is not readable") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CATALOG_SHA256:
        raise GeographyCatalogError("geography catalog checksum mismatch")
    try:
        payload = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GeographyCatalogError("geography catalog is not strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise GeographyCatalogError("geography catalog root must be an object")
    if payload.get("dataset_id") != CATALOG_DATASET_ID:
        raise GeographyCatalogError("geography catalog identity mismatch")
    if payload.get("snapshot_version") != CATALOG_VERSION:
        raise GeographyCatalogError("geography catalog version mismatch")
    if payload.get("country_authority") != "ISO 3166-1 alpha-2":
        raise GeographyCatalogError("country authority mismatch")
    if payload.get("international_location_authority") != "UNECE UN/LOCODE":
        raise GeographyCatalogError("international location authority mismatch")
    if payload.get("source_archive_sha256") != SOURCE_ARCHIVE_SHA256:
        raise GeographyCatalogError("source archive identity mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
        raise GeographyCatalogError("records must be an array")

    seen_countries: set[str] = set()
    seen_locations: set[str] = set()
    duplicate_count = 0
    invalid_count = 0
    iran_count = 0
    type_counts = {kind: 0 for kind in ALLOWED_LOCATION_TYPES}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("country"), dict):
            invalid_count += 1
            continue
        country = record["country"]
        code = country.get("code")
        if not isinstance(code, str) or not _COUNTRY_CODE.fullmatch(code):
            invalid_count += 1
            continue
        if code in seen_countries:
            duplicate_count += 1
        seen_countries.add(code)
        try:
            _required_text(country.get("name_en"), f"{code}.name_en", 100)
            _required_text(country.get("name_fa"), f"{code}.name_fa", 100)
        except GeographyCatalogError:
            invalid_count += 1
        locations = record.get("locations")
        if not isinstance(locations, list) or not locations:
            invalid_count += 1
            continue
        for location in locations:
            if not isinstance(location, dict):
                invalid_count += 1
                continue
            locode = location.get("un_locode")
            location_type = location.get("city_type")
            valid = (
                isinstance(locode, str)
                and bool(_UNLOCODE.fullmatch(locode))
                and locode.startswith(code)
                and location_type in ALLOWED_LOCATION_TYPES
                and isinstance(location.get("is_major_port"), bool)
                and isinstance(location.get("is_major_airport"), bool)
                and location.get("source_status") in ALLOWED_SOURCE_STATUSES | {None}
            )
            try:
                _required_text(location.get("name_en"), f"{locode}.name_en", 100)
                _required_text(location.get("name_fa"), f"{locode}.name_fa", 100)
            except GeographyCatalogError:
                valid = False
            if not valid:
                invalid_count += 1
                continue
            if locode in seen_locations:
                duplicate_count += 1
            seen_locations.add(locode)
            type_counts[location_type] += 1
            if code == "IR":
                iran_count += 1

    if invalid_count or duplicate_count:
        raise GeographyCatalogError(
            f"catalog contains {invalid_count} invalid and {duplicate_count} duplicate records"
        )
    if len(records) != EXPECTED_COUNTRY_COUNT or len(seen_locations) != EXPECTED_LOCATION_COUNT:
        raise GeographyCatalogError("catalog coverage counts do not match the approved input")
    if iran_count != EXPECTED_IRAN_LOCATION_COUNT or type_counts != EXPECTED_TYPE_COUNTS:
        raise GeographyCatalogError("catalog geography/type counts do not match the approved input")
    if not {"IT", "NO", "IR"}.issubset(seen_countries):
        raise GeographyCatalogError("required country coverage is missing")
    return GeographyCatalog(
        payload=payload,
        checksum=CATALOG_CHECKSUM,
        country_count=len(records),
        location_count=len(seen_locations),
        iran_location_count=iran_count,
        location_type_counts=type_counts,
        duplicate_count=duplicate_count,
        invalid_record_count=invalid_count,
    )


def plan_catalog(catalog: GeographyCatalog | None = None) -> GeographyCatalogPlan:
    """Compare catalog identities without writing or mutating tracked rows."""
    catalog = catalog or load_catalog()
    plan = GeographyCatalogPlan(
        dataset_id=catalog.dataset_id,
        catalog_version=catalog.snapshot_version,
        checksum=catalog.checksum,
        country_count=catalog.country_count,
        location_count=catalog.location_count,
        iran_location_count=catalog.iran_location_count,
        location_type_counts=catalog.location_type_counts,
    )
    countries = {row.code: row for row in Country.query.all()}
    coded_locations: dict[str, list[int]] = {}
    unbound_names: set[tuple[int, str]] = set()
    location_rows = db.session.query(
        InternationalCity.country_id,
        InternationalCity.un_locode,
        InternationalCity.name_en,
    ).yield_per(5_000)
    for country_id, un_locode, name_en in location_rows:
        if un_locode:
            coded_locations.setdefault(un_locode, []).append(country_id)
        else:
            unbound_names.add((country_id, name_en.casefold()))

    for record in catalog.payload["records"]:
        source_country = record["country"]
        country_code = source_country["code"]
        country = countries.get(country_code)
        if country is None:
            plan.created_country_count += 1
            plan.country_creates.append(source_country)
        else:
            plan.unchanged_country_count += 1
        for source_location in record["locations"]:
            locode = source_location["un_locode"]
            matches = coded_locations.get(locode, [])
            if matches:
                if (
                    len(matches) != 1
                    or country is None
                    or matches[0] != country.id
                ):
                    plan.conflicts.append(
                        {
                            "kind": "location",
                            "stable_key": locode,
                            "reason": "stable key is already attached to a different country or duplicate row",
                        }
                    )
                else:
                    plan.unchanged_location_count += 1
                continue
            if country is not None and (
                country.id,
                source_location["name_en"].casefold(),
            ) in unbound_names:
                plan.conflicts.append(
                    {
                        "kind": "location",
                        "stable_key": locode,
                        "reason": "same-country legacy name requires reviewed identity mapping",
                    }
                )
                continue
            plan.created_location_count += 1
            plan.location_creates.append((country_code, source_location))
    return plan


def _validate_apply_text(value: str, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise GeographyCatalogError(f"bounded {field_name} is required")
    return value.strip()


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def apply_catalog(
    *,
    expected_checksum: str,
    executed_by: str,
    approval_reference: str,
    environment: str,
    catalog: GeographyCatalog | None = None,
) -> tuple[GeographyCatalogPlan, ReferenceDataSeedRun]:
    """Apply only missing identities in one data transaction with an audit run."""
    catalog = catalog or load_catalog()
    if expected_checksum not in {CATALOG_SHA256, CATALOG_CHECKSUM}:
        raise GeographyCatalogError("expected checksum does not match approved geography input")
    executed_by = _validate_apply_text(executed_by, "operator", 160)
    approval_reference = _validate_apply_text(
        approval_reference, "approval reference", 200
    )
    environment = _validate_apply_text(environment, "environment", 32).lower()
    if db.session.new or db.session.dirty or db.session.deleted:
        raise GeographyCatalogError("geography apply requires a clean unit of work")

    plan = plan_catalog(catalog)
    run = ReferenceDataSeedRun(
        catalog_version=CATALOG_DATASET_ID,
        catalog_family="GEOGRAPHY",
        catalog_name="Governed international geography",
        schema_version="2",
        source_bundle_version=CATALOG_VERSION,
        checksum=CATALOG_CHECKSUM,
        environment=environment,
        mode="apply",
        planned_count=plan.planned_count,
        created_count=0,
        updated_count=0,
        unchanged_count=plan.unchanged_count,
        conflict_count=plan.conflict_count,
        status="refused" if plan.conflicts else "started",
        executed_by=executed_by,
        approval_reference=approval_reference,
    )
    db.session.add(run)
    db.session.commit()
    run_public_id = run.public_id
    if plan.conflicts:
        run.completed_at = _utc_naive_now()
        run.error_summary = "Geography conflicts detected; no catalog rows were written."
        db.session.commit()
        return plan, run

    try:
        countries = {row.code: row for row in Country.query.all()}
        created_at = _utc_naive_now()
        for source in plan.country_creates:
            row = Country(
                code=source["code"],
                name_en=source["name_en"],
                name_fa=source["name_fa"],
                is_active=True,
                source_organization=source["source_organization"],
                source_reference=source["source_reference"],
                source_version=source["source_version"],
                dataset_id=CATALOG_DATASET_ID,
                created_at=created_at,
            )
            db.session.add(row)
            countries[row.code] = row
        db.session.flush()

        defaults = catalog.payload["location_defaults"]
        batch: list[dict[str, Any]] = []
        for country_code, source in plan.location_creates:
            item = {**defaults, **source}
            batch.append(
                {
                    "country_id": countries[country_code].id,
                    "un_locode": item["un_locode"],
                    "name_en": item["name_en"],
                    "name_fa": item["name_fa"],
                    "city_type": item["city_type"],
                    "is_major_port": item["is_major_port"],
                    "is_major_airport": item["is_major_airport"],
                    "is_active": True,
                    "source_organization": item["source_organization"],
                    "source_reference": item["source_reference"],
                    "source_version": item["source_version"],
                    "dataset_id": CATALOG_DATASET_ID,
                    "created_at": created_at,
                }
            )
            if len(batch) == 5_000:
                db.session.bulk_insert_mappings(InternationalCity, batch)
                batch.clear()
        if batch:
            db.session.bulk_insert_mappings(InternationalCity, batch)

        run.status = "succeeded"
        run.created_count = plan.created_count
        run.completed_at = _utc_naive_now()
        db.session.commit()
        return plan, run
    except Exception as exc:
        db.session.rollback()
        persisted = ReferenceDataSeedRun.query.filter_by(public_id=run_public_id).one()
        persisted.status = "failed"
        persisted.completed_at = _utc_naive_now()
        persisted.error_summary = (
            f"Geography apply rolled back ({type(exc).__name__}); inspect operator diagnostics."
        )[:500]
        db.session.commit()
        raise GeographyCatalogError("geography catalog apply failed and rolled back") from exc
