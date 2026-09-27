"""Versioned, deterministic Forwarder Reference Catalog V1 plan/apply."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.extensions import db
from backend.models import (
    CargoType,
    MASTER_DATA_DIMENSIONS,
    PackagingType,
    ReferenceDataSeedRun,
    ServiceType,
    TransportEquipmentType,
    TransportMeansType,
    TransportMethod,
    UnitOfMeasure,
)
from backend.request_transport_catalog import DEFAULT_TRANSPORT_METHODS

REFERENCE_DATA_DIR = Path(__file__).with_name("reference_data")
CATALOG_PATH = REFERENCE_DATA_DIR / "forwarder-reference-catalog-v1.json"
BASE_CATALOG_PATH = REFERENCE_DATA_DIR / "catalog-v1.0.0.json"
APPROVED_CATALOG_CHECKSUM = "sha256:13a0f6361eca01286422b9ca8df165c2e616c2bc2e73919391056ec7647da45a"
APPROVED_BASE_CHECKSUM = "sha256:f7fcfc54d624baa5ae993213fb70c8ca2b76432fb6ae9ae2167e1a11aa9ddaab"

RESOURCE_ORDER = (
    "cargo_types",
    "service_types",
    "units_of_measure",
    "packaging_types",
    "transport_means_types",
    "transport_equipment_types",
    "request_transport_methods",
)
CODE_PATTERNS = {
    "cargo_types": re.compile(r"^CARGO_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
    "service_types": re.compile(r"^SERVICE_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
    "units_of_measure": re.compile(r"^UOM_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
    "packaging_types": re.compile(r"^PACKAGING_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
    "transport_means_types": re.compile(r"^MEANS_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
    "transport_equipment_types": re.compile(r"^EQUIPMENT_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
}
MODELS = {
    "cargo_types": CargoType,
    "service_types": ServiceType,
    "units_of_measure": UnitOfMeasure,
    "packaging_types": PackagingType,
    "transport_means_types": TransportMeansType,
    "transport_equipment_types": TransportEquipmentType,
    "request_transport_methods": TransportMethod,
}
BASE_COMMON_KEYS = {
    "code", "fa_name", "en_name", "description", "display_order", "is_active"
}
ADDITION_COMMON_KEYS = {
    "code", "fa_name", "en_name", "description", "fa_description",
    "display_order", "status", "catalog_version", "family",
}
ADDITION_KEYS = {
    "units_of_measure": ADDITION_COMMON_KEYS | {"symbol", "measurement_dimension"},
    "packaging_types": ADDITION_COMMON_KEYS,
    "transport_means_types": ADDITION_COMMON_KEYS,
    "transport_equipment_types": ADDITION_COMMON_KEYS,
    "request_transport_methods": ADDITION_COMMON_KEYS,
}
TOP_LEVEL_KEYS = {
    "schema_version", "catalog_version", "catalog_name", "source_version",
    "base_catalog", "checksum", "fa_descriptions", "additions",
}


class CatalogValidationError(ValueError):
    pass


class CatalogApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Catalog:
    schema_version: str
    catalog_version: str
    catalog_name: str
    source_version: str
    checksum: str
    resources: dict[str, tuple[dict[str, Any], ...]]

    @property
    def planned_count(self) -> int:
        return sum(len(rows) for rows in self.resources.values())


@dataclass
class CatalogPlan:
    catalog_version: str
    catalog_name: str
    source_version: str
    checksum: str
    environment: str
    planned_count: int
    created_count: int = 0
    unchanged_count: int = 0
    conflict_count: int = 0
    rejected_count: int = 0
    conflicts: list[dict[str, str]] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "catalog_name": self.catalog_name,
            "source_version": self.source_version,
            "checksum": self.checksum,
            "environment": self.environment,
            "planned_count": self.planned_count,
            "created_count": self.created_count,
            "unchanged_count": self.unchanged_count,
            "conflict_count": self.conflict_count,
            "rejected_count": self.rejected_count,
            "conflicts": self.conflicts,
            "rejected": self.rejected,
        }


def _canonical_checksum(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "checksum"}
    encoded = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogValidationError("catalog is not readable strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise CatalogValidationError("catalog root must be an object")
    return payload


def _required_text(row: dict[str, Any], key: str, maximum: int) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogValidationError(f"{key} must be non-empty trimmed text")
    if len(value) > maximum:
        raise CatalogValidationError(f"{key} exceeds {maximum} characters")
    return value


def _normalized_title(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().casefold()


def _base_resources(payload: dict[str, Any], descriptions: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    if payload.get("checksum") != APPROVED_BASE_CHECKSUM or _canonical_checksum(payload) != APPROVED_BASE_CHECKSUM:
        raise CatalogValidationError("base catalog checksum is not approved")
    resources: dict[str, list[dict[str, Any]]] = {}
    for resource in ("cargo_types", "service_types", "units_of_measure"):
        rows = payload.get(resource)
        if not isinstance(rows, list) or not rows:
            raise CatalogValidationError(f"base {resource} must be a non-empty array")
        transformed = []
        for source in rows:
            code = source.get("code")
            if code not in descriptions:
                raise CatalogValidationError(f"missing Persian description for {code}")
            transformed.append({
                **source,
                "fa_description": descriptions[code],
                "family": resource,
                "catalog_version": "1",
                "status": "ACTIVE" if source.get("is_active") is True else "INACTIVE",
            })
        resources[resource] = transformed
    return resources


def _validate_rows(resources: dict[str, list[dict[str, Any]]]) -> None:
    request_codes = {item["name"] for item in DEFAULT_TRANSPORT_METHODS}
    for resource in RESOURCE_ORDER:
        rows = sorted(resources.get(resource, []), key=lambda row: (row["display_order"], row["code"]))
        if not rows:
            raise CatalogValidationError(f"{resource} must be a non-empty array")
        seen_codes: set[str] = set()
        seen_orders: set[int] = set()
        seen_titles: set[str] = set()
        for row in rows:
            code = _required_text(row, "code", 64)
            if resource == "request_transport_methods":
                if code not in request_codes:
                    raise CatalogValidationError(f"unsupported request transport method: {code}")
            elif not CODE_PATTERNS[resource].fullmatch(code) or not code.isascii():
                raise CatalogValidationError(f"invalid immutable code: {code}")
            if code in seen_codes:
                raise CatalogValidationError(f"duplicate immutable code: {code}")
            seen_codes.add(code)
            for key in ("fa_name", "en_name"):
                title = _required_text(row, key, 160)
                normalized = _normalized_title(title)
                if resource != "request_transport_methods" and normalized in seen_titles:
                    raise CatalogValidationError(f"duplicate title in {resource}: {title}")
                seen_titles.add(normalized)
            _required_text(row, "description", 4000)
            _required_text(row, "fa_description", 4000)
            if row.get("family") != resource or row.get("catalog_version") != "1":
                raise CatalogValidationError(f"family or catalog version mismatch for {code}")
            if row.get("status") != "ACTIVE" or row.get("is_active") is not True:
                raise CatalogValidationError(f"initial value must be active: {code}")
            order = row.get("display_order")
            if isinstance(order, bool) or not isinstance(order, int) or order < 0 or order in seen_orders:
                raise CatalogValidationError(f"invalid or duplicate display_order for {code}")
            seen_orders.add(order)
            if resource == "units_of_measure":
                _required_text(row, "symbol", 32)
                if row.get("measurement_dimension") not in MASTER_DATA_DIMENSIONS:
                    raise CatalogValidationError(f"invalid UOM dimension for {code}")
        resources[resource] = rows
    cargo_codes = {row["code"] for row in resources["cargo_types"]}
    for row in resources["cargo_types"]:
        parent = row.get("parent_code")
        if parent is not None and parent not in cargo_codes:
            raise CatalogValidationError(f"missing catalog parent for {row['code']}")


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    payload = _read_json(path)
    if set(payload) != TOP_LEVEL_KEYS:
        raise CatalogValidationError("catalog top-level schema is invalid")
    for key in ("schema_version", "catalog_version", "catalog_name", "source_version", "checksum"):
        _required_text(payload, key, 160)
    if payload["schema_version"] != "2" or payload["catalog_version"] != "1":
        raise CatalogValidationError("catalog schema or version is unsupported")
    if payload["catalog_name"] != "FORWARDER_REFERENCE_CATALOG_V1":
        raise CatalogValidationError("catalog name is not approved")
    expected = _canonical_checksum(payload)
    if payload["checksum"] != expected:
        raise CatalogValidationError("catalog checksum does not match content")
    if path == CATALOG_PATH and payload["checksum"] != APPROVED_CATALOG_CHECKSUM:
        raise CatalogValidationError("catalog checksum is not the approved Forwarder V1 checksum")
    base = payload.get("base_catalog")
    if base != {"path": BASE_CATALOG_PATH.name, "checksum": APPROVED_BASE_CHECKSUM}:
        raise CatalogValidationError("base catalog reference is invalid")
    descriptions = payload.get("fa_descriptions")
    additions = payload.get("additions")
    if not isinstance(descriptions, dict) or not isinstance(additions, dict) or set(additions) != set(ADDITION_KEYS):
        raise CatalogValidationError("catalog extension structure is invalid")
    resources = _base_resources(_read_json(BASE_CATALOG_PATH), descriptions)
    for resource, expected_keys in ADDITION_KEYS.items():
        rows = additions[resource]
        if not isinstance(rows, list) or not rows:
            raise CatalogValidationError(f"{resource} additions must be a non-empty array")
        transformed = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != expected_keys:
                raise CatalogValidationError(f"{resource} row schema is invalid")
            transformed.append({**row, "is_active": row["status"] == "ACTIVE"})
        resources.setdefault(resource, []).extend(transformed)
    _validate_rows(resources)
    return Catalog(
        schema_version=payload["schema_version"],
        catalog_version=payload["catalog_version"],
        catalog_name=payload["catalog_name"],
        source_version=payload["source_version"],
        checksum=payload["checksum"],
        resources={key: tuple(resources[key]) for key in RESOURCE_ORDER},
    )


def _row_code(resource: str, row: Any) -> str:
    return row.name if resource == "request_transport_methods" else row.immutable_code


def _existing_rows(resource: str) -> dict[str, Any]:
    return {_row_code(resource, row): row for row in MODELS[resource].query.all()}


def _persisted_expected(resource: str, entry: dict[str, Any]) -> dict[str, Any]:
    if resource == "request_transport_methods":
        return {
            "code": entry["code"],
            "fa_name": entry["fa_name"],
            "description": entry["description"],
            "is_active": True,
        }
    values = {
        "code": entry["code"],
        "fa_name": entry["fa_name"],
        "en_name": entry["en_name"],
        "description": entry["description"],
        "display_order": entry["display_order"],
        "is_active": True,
    }
    if resource == "cargo_types":
        values["parent_code"] = entry.get("parent_code")
    if resource == "units_of_measure":
        values.update(symbol=entry["symbol"], measurement_dimension=entry["measurement_dimension"])
    return values


def _governed_values(resource: str, row: Any) -> dict[str, Any]:
    if resource == "request_transport_methods":
        return {
            "code": row.name,
            "fa_name": row.name_fa,
            "description": row.description,
            "is_active": row.is_active,
        }
    values = {
        "code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "description": row.description,
        "display_order": row.display_order,
        "is_active": row.is_active,
    }
    if resource == "cargo_types":
        values["parent_code"] = row.parent.immutable_code if row.parent else None
    if resource == "units_of_measure":
        values.update(symbol=row.symbol, measurement_dimension=row.measurement_dimension)
    return values


def plan_catalog(catalog: Catalog, environment: str) -> CatalogPlan:
    plan = CatalogPlan(
        catalog_version=catalog.catalog_version,
        catalog_name=catalog.catalog_name,
        source_version=catalog.source_version,
        checksum=catalog.checksum,
        environment=environment,
        planned_count=catalog.planned_count,
    )
    for resource, entries in catalog.resources.items():
        existing = _existing_rows(resource)
        title_codes: dict[str, set[str]] = {}
        if resource != "request_transport_methods":
            for row in existing.values():
                for title in (row.fa_name, row.en_name):
                    title_codes.setdefault(_normalized_title(title), set()).add(_row_code(resource, row))
        for entry in entries:
            code = entry["code"]
            row = existing.get(code)
            duplicate_codes: set[str] = set()
            for title in (entry["fa_name"], entry["en_name"]):
                duplicate_codes.update(title_codes.get(_normalized_title(title), set()))
            duplicate_codes.discard(code)
            if duplicate_codes:
                plan.conflicts.append({
                    "resource": resource,
                    "code": code,
                    "reason": "same title exists under a different code",
                })
            elif row is None:
                plan.created_count += 1
            elif _governed_values(resource, row) == _persisted_expected(resource, entry):
                plan.unchanged_count += 1
            else:
                plan.conflicts.append({
                    "resource": resource,
                    "code": code,
                    "reason": "existing code is inactive" if not row.is_active else "governed values differ",
                })
    plan.conflict_count = len(plan.conflicts)
    return plan


def _new_row(resource: str, entry: dict[str, Any], parents: dict[str, CargoType]) -> Any:
    if resource == "request_transport_methods":
        return TransportMethod(
            name=entry["code"],
            name_fa=entry["fa_name"],
            description=entry["description"],
            is_active=True,
        )
    common = dict(
        immutable_code=entry["code"],
        fa_name=entry["fa_name"],
        en_name=entry["en_name"],
        description=entry["description"],
        display_order=entry["display_order"],
        is_active=True,
    )
    if resource == "cargo_types":
        parent_code = entry.get("parent_code")
        return CargoType(parent=parents.get(parent_code) if parent_code else None, **common)
    if resource == "units_of_measure":
        return UnitOfMeasure(
            symbol=entry["symbol"],
            measurement_dimension=entry["measurement_dimension"],
            **common,
        )
    return MODELS[resource](**common)


def apply_catalog(
    catalog: Catalog,
    *,
    environment: str,
    executed_by: str,
    approval_reference: str,
    expected_checksum: str,
    failure_hook: Any = None,
) -> tuple[CatalogPlan, ReferenceDataSeedRun]:
    if expected_checksum != catalog.checksum:
        raise CatalogApplyError("expected checksum does not match approved catalog")
    executed_by = executed_by.strip()
    approval_reference = approval_reference.strip()
    if not executed_by or len(executed_by) > 160:
        raise CatalogApplyError("a bounded named operator is required")
    if not approval_reference or len(approval_reference) > 200:
        raise CatalogApplyError("a bounded approval reference is required")
    plan = plan_catalog(catalog, environment)
    run = ReferenceDataSeedRun(
        catalog_version=catalog.catalog_version,
        catalog_family="FORWARDER_REFERENCE_CATALOG",
        catalog_name=catalog.catalog_name,
        schema_version=catalog.schema_version,
        source_bundle_version=catalog.source_version,
        checksum=catalog.checksum,
        environment=environment,
        mode="apply",
        planned_count=plan.planned_count,
        created_count=0,
        unchanged_count=plan.unchanged_count,
        conflict_count=plan.conflict_count,
        status="started",
        executed_by=executed_by,
        approval_reference=approval_reference,
    )
    db.session.add(run)
    db.session.commit()
    if plan.conflict_count or plan.rejected_count:
        run.status = "refused"
        run.completed_at = datetime.utcnow()
        run.error_summary = "Catalog conflicts or rejected rows detected; no catalog writes were made."
        db.session.commit()
        return plan, run
    try:
        parents = {row.immutable_code: row for row in CargoType.query.all()}
        for resource in RESOURCE_ORDER:
            existing = set(_existing_rows(resource))
            for entry in catalog.resources[resource]:
                if entry["code"] in existing:
                    continue
                row = _new_row(resource, entry, parents)
                db.session.add(row)
                if resource == "cargo_types":
                    db.session.flush()
                    parents[entry["code"]] = row
        if failure_hook is not None:
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
        persisted.error_summary = f"Catalog apply failed ({type(exc).__name__})."[:500]
        db.session.commit()
        raise CatalogApplyError("catalog apply failed; catalog writes were rolled back") from exc


def catalog_presentation_by_code(catalog: Catalog | None = None) -> dict[str, dict[str, str]]:
    """Persian Product copy kept in the versioned catalog, not tenant data."""
    selected = catalog or load_catalog()
    return {
        row["code"]: {
            "family": resource,
            "fa_description": row["fa_description"],
            "catalog_version": selected.catalog_version,
        }
        for resource, rows in selected.resources.items()
        for row in rows
    }


@lru_cache(maxsize=1)
def approved_catalog_presentation_by_code() -> dict[str, dict[str, str]]:
    return catalog_presentation_by_code(load_catalog())
