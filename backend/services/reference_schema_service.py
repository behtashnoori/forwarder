"""Read-only reference-schema validation, readiness, and inventory helpers."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import func, inspect, or_

from backend.extensions import db
from backend.models import (
    City, Country, County, CustomsOffice, CustomsProvinceMapping, IranPort,
    PortCustomsOffice, PortLocation, PortProvinceMapping, Province,
)

PROVENANCE_FIELDS = ("source_organization", "source_reference", "source_version", "dataset_id")


class ReferenceValidationError(ValueError):
    """Controlled reference-data validation failure."""


def validate_effective_range(effective_from: date | None, effective_to: date | None) -> None:
    if effective_from is not None and effective_to is not None and effective_to < effective_from:
        raise ReferenceValidationError("effective_to must be on or after effective_from")


def validate_country_parent(country: Country | None) -> None:
    if country is None:
        raise ReferenceValidationError("country parent does not exist")


def validate_county_parent(county: County | None, province: Province | None) -> None:
    if county is None or province is None or county.province_id != province.id:
        raise ReferenceValidationError("county does not belong to the supplied province")


def validate_city_parent(city: City | None, county: County | None, province: Province | None = None) -> None:
    if city is None or county is None or city.county_id != county.id:
        raise ReferenceValidationError("city does not belong to the supplied county")
    if province is not None and (county.province_id != province.id or city.province_id != province.id):
        raise ReferenceValidationError("city hierarchy is inconsistent with the supplied province")


def validate_port_location_hierarchy(*, country=None, province=None, county=None, city=None) -> None:
    if province is not None and province.country_id is not None:
        if country is None or province.country_id != country.id:
            raise ReferenceValidationError("province does not belong to the supplied country")
    if county is not None:
        validate_county_parent(county, province)
    if city is not None:
        validate_city_parent(city, county, province)


def validate_customs_location_hierarchy(*, country=None, province=None, county=None, city=None) -> None:
    validate_country_parent(country)
    validate_port_location_hierarchy(country=country, province=province, county=county, city=city)


@dataclass(frozen=True)
class DomainReadiness:
    domain: str
    row_count: int
    null_code_count: int
    duplicate_code_count: int
    missing_parent_count: int
    invalid_effective_range_count: int
    missing_provenance_count: int
    status: str


def _invalid_range(model) -> int:
    return model.query.filter(model.effective_from.isnot(None), model.effective_to.isnot(None), model.effective_to < model.effective_from).count()


def _missing_provenance(model) -> int:
    return model.query.filter(or_(*(getattr(model, field).is_(None) for field in PROVENANCE_FIELDS))).count()


def _duplicate_codes(model, parent_field: str | None) -> int:
    columns = [getattr(model, parent_field)] if parent_field else []
    columns.append(model.code)
    return db.session.query(*columns).filter(model.code.isnot(None)).group_by(*columns).having(func.count(model.id) > 1).count()


def build_readiness_report() -> dict[str, Any]:
    inspector = inspect(db.engine)
    required = {"country", "province", "county", "city", "iran_port", "port_province_mapping", "customs_office", "port_customs_office", "port_location", "customs_province_mapping"}
    missing = sorted(required - set(inspector.get_table_names()))
    if missing:
        return {"status": "BLOCKED", "production_readiness": "NO-GO", "missing_tables": missing, "domains": []}
    configs = (
        ("country", Country, None, None),
        ("province", Province, "country_id", "country_id"),
        ("county", County, "province_id", None),
        ("city", City, "county_id", None),
        ("port", IranPort, "country_id", "country_id"),
        ("customs_office", CustomsOffice, None, None),
    )
    domains: list[DomainReadiness] = []
    conflict = False
    backfill = False
    for name, model, parent_scope, nullable_parent in configs:
        rows = model.query.count()
        null_codes = model.query.filter(model.code.is_(None)).count()
        duplicates = _duplicate_codes(model, parent_scope)
        missing_parent = model.query.filter(getattr(model, nullable_parent).is_(None)).count() if nullable_parent else 0
        invalid = _invalid_range(model)
        missing_provenance = _missing_provenance(model)
        has_conflict = bool(duplicates or invalid)
        needs_backfill = bool(null_codes or missing_parent or missing_provenance)
        conflict |= has_conflict
        backfill |= needs_backfill
        status = "CONFLICT" if has_conflict else ("BACKFILL_REQUIRED" if needs_backfill else "SCHEMA_READY")
        domains.append(DomainReadiness(name, rows, null_codes, duplicates, missing_parent, invalid, missing_provenance, status))

    coverage_duplicates = db.session.query(PortProvinceMapping.port_id, PortProvinceMapping.province_id).group_by(
        PortProvinceMapping.port_id, PortProvinceMapping.province_id).having(func.count(PortProvinceMapping.id) > 1).count()
    invalid_relations = sum(_invalid_range(model) for model in (PortProvinceMapping, PortCustomsOffice, PortLocation, CustomsProvinceMapping))
    conflict |= bool(coverage_duplicates or invalid_relations)
    result = "CONFLICT" if conflict else ("BACKFILL_REQUIRED" if backfill else "SCHEMA_READY")
    return {
        "status": result,
        "production_readiness": "NO-GO",
        "domains": [asdict(item) for item in domains],
        "port_coverage_duplicate_count": coverage_duplicates,
        "port_location_count": PortLocation.query.count(),
        "ports_without_location_count": IranPort.query.filter(~IranPort.id.in_(db.session.query(PortLocation.port_id).filter(PortLocation.is_active.is_(True)))).count(),
        "customs_coverage_count": CustomsProvinceMapping.query.count(),
        "invalid_relationship_effective_range_count": invalid_relations,
    }


def export_backfill_inventory(path: Path) -> int:
    """Write owner-review inventory only; every proposed code is intentionally blank."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for domain, model, parent_attr in (
        ("province", Province, "country_id"), ("county", County, "province_id"),
        ("city", City, "county_id"), ("port", IranPort, "country_id"),
    ):
        for record in model.query.order_by(model.id).all():
            rows.append({"domain": domain, "row_id_locator_only": record.id, "current_name": record.name_fa,
                         "parent_id_locator_only": getattr(record, parent_attr), "current_code": record.code or "",
                         "proposed_code_owner_must_supply": "", "conflict_status": "",
                         "provenance_status": "missing" if any(getattr(record, f) is None for f in PROVENANCE_FIELDS) else "present"})
    def safe_cell(value):
        text = "" if value is None else str(value)
        return "'" + text if text.startswith(("=", "+", "-", "@")) else text
    safe_rows = [{key: safe_cell(value) for key, value in row.items()} for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("# Numeric IDs are temporary reconciliation locators, never stable business keys. No code is generated.\n")
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["domain", "row_id_locator_only", "current_name", "parent_id_locator_only", "current_code", "proposed_code_owner_must_supply", "conflict_status", "provenance_status"])
        writer.writeheader(); writer.writerows(safe_rows)
    return len(rows)


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path = path.resolve(); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
