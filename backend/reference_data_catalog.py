"""Validated, deterministic initial reference-data catalog operations."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.extensions import db
from backend.models import (
    CargoType,
    MASTER_DATA_DIMENSIONS,
    ReferenceDataSeedRun,
    ServiceType,
    UnitOfMeasure,
)

CATALOG_PATH = Path(__file__).with_name("reference_data") / "catalog-v1.0.0.json"
APPROVED_CATALOG_CHECKSUM = "sha256:f7fcfc54d624baa5ae993213fb70c8ca2b76432fb6ae9ae2167e1a11aa9ddaab"
CODE_PATTERNS = {
    "cargo_types": re.compile(r"^CARGO_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
    "service_types": re.compile(r"^SERVICE_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
    "units_of_measure": re.compile(r"^UOM_[A-Z0-9]+(?:_[A-Z0-9]+)*$"),
}
MODELS = {
    "cargo_types": CargoType,
    "service_types": ServiceType,
    "units_of_measure": UnitOfMeasure,
}
COMMON_KEYS = {"code", "fa_name", "en_name", "description", "display_order", "is_active"}
RESOURCE_KEYS = {
    "cargo_types": COMMON_KEYS | {"parent_code"},
    "service_types": COMMON_KEYS,
    "units_of_measure": COMMON_KEYS | {"symbol", "measurement_dimension"},
}
TOP_LEVEL_KEYS = {
    "schema_version", "catalog_version", "source_version", "checksum",
    "cargo_types", "service_types", "units_of_measure",
}


class CatalogValidationError(ValueError):
    pass


class CatalogApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Catalog:
    schema_version: str
    catalog_version: str
    source_version: str
    checksum: str
    resources: dict[str, tuple[dict[str, Any], ...]]

    @property
    def planned_count(self) -> int:
        return sum(len(rows) for rows in self.resources.values())


@dataclass
class CatalogPlan:
    catalog_version: str
    source_version: str
    checksum: str
    environment: str
    planned_count: int
    created_count: int = 0
    unchanged_count: int = 0
    conflict_count: int = 0
    conflicts: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "source_version": self.source_version,
            "checksum": self.checksum,
            "environment": self.environment,
            "planned_count": self.planned_count,
            "created_count": self.created_count,
            "unchanged_count": self.unchanged_count,
            "conflict_count": self.conflict_count,
            "conflicts": self.conflicts,
        }


def _canonical_checksum(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "checksum"}
    encoded = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _required_text(row: dict[str, Any], key: str, maximum: int) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogValidationError(f"{key} must be non-empty trimmed text")
    if len(value) > maximum:
        raise CatalogValidationError(f"{key} exceeds {maximum} characters")
    return value


def _normalized_title(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().casefold()


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogValidationError("catalog is not readable strict UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != TOP_LEVEL_KEYS:
        raise CatalogValidationError("catalog top-level schema is invalid")
    for key in ("schema_version", "catalog_version", "source_version", "checksum"):
        _required_text(payload, key, 160)
    if payload["schema_version"] != "1":
        raise CatalogValidationError("catalog schema_version is unsupported")
    expected = _canonical_checksum(payload)
    if payload["checksum"] != expected:
        raise CatalogValidationError("catalog checksum does not match content")

    resources: dict[str, tuple[dict[str, Any], ...]] = {}
    all_titles: dict[tuple[str, str], str] = {}
    for resource, pattern in CODE_PATTERNS.items():
        rows = payload.get(resource)
        if not isinstance(rows, list) or not rows:
            raise CatalogValidationError(f"{resource} must be a non-empty array")
        seen_codes: set[str] = set()
        seen_orders: set[int] = set()
        previous_order = -1
        validated: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != RESOURCE_KEYS[resource]:
                raise CatalogValidationError(f"{resource} row schema is invalid")
            code = _required_text(row, "code", 64)
            if not pattern.fullmatch(code) or not code.isascii():
                raise CatalogValidationError(f"invalid immutable code: {code}")
            if code in seen_codes:
                raise CatalogValidationError(f"duplicate immutable code: {code}")
            seen_codes.add(code)
            for label_key in ("fa_name", "en_name"):
                label = _required_text(row, label_key, 160)
                title_key = (resource, _normalized_title(label))
                if title_key in all_titles:
                    raise CatalogValidationError(
                        f"duplicate title in {resource}: {code} and {all_titles[title_key]}"
                    )
                all_titles[title_key] = code
            description = _required_text(row, "description", 4000)
            order = row.get("display_order")
            if isinstance(order, bool) or not isinstance(order, int) or order < 0:
                raise CatalogValidationError(f"invalid display_order for {code}")
            if order in seen_orders:
                raise CatalogValidationError(f"duplicate display_order in {resource}: {order}")
            if order <= previous_order:
                raise CatalogValidationError(f"non-deterministic row ordering in {resource}")
            previous_order = order
            seen_orders.add(order)
            if row.get("is_active") is not True:
                raise CatalogValidationError(f"initial value must be active: {code}")
            if resource == "cargo_types":
                parent = row["parent_code"]
                if parent is not None and (not isinstance(parent, str) or not pattern.fullmatch(parent)):
                    raise CatalogValidationError(f"invalid parent_code for {code}")
            if resource == "units_of_measure":
                _required_text(row, "symbol", 32)
                if row["measurement_dimension"] not in MASTER_DATA_DIMENSIONS:
                    raise CatalogValidationError(f"invalid UOM dimension for {code}")
            validated.append({**row, "description": description})
        if resource == "cargo_types":
            codes = {row["code"] for row in validated}
            for row in validated:
                parent = row["parent_code"]
                if parent is not None and parent not in codes:
                    raise CatalogValidationError(f"missing catalog parent for {row['code']}")
        resources[resource] = tuple(validated)
    if payload["checksum"] != APPROVED_CATALOG_CHECKSUM:
        raise CatalogValidationError("catalog checksum is not the approved Release 1.5.0 checksum")
    return Catalog(
        schema_version=payload["schema_version"],
        catalog_version=payload["catalog_version"],
        source_version=payload["source_version"],
        checksum=payload["checksum"],
        resources=resources,
    )


def _governed_values(resource: str, row: Any, parent_code: str | None = None) -> dict[str, Any]:
    values = {
        "code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "description": row.description,
        "display_order": row.display_order,
        "is_active": row.is_active,
    }
    if resource == "cargo_types":
        values["parent_code"] = parent_code if parent_code is not None else (
            row.parent.immutable_code if row.parent else None
        )
    if resource == "units_of_measure":
        values.update(symbol=row.symbol, measurement_dimension=row.measurement_dimension)
    return values


def plan_catalog(catalog: Catalog, environment: str) -> CatalogPlan:
    plan = CatalogPlan(
        catalog_version=catalog.catalog_version,
        source_version=catalog.source_version,
        checksum=catalog.checksum,
        environment=environment,
        planned_count=catalog.planned_count,
    )
    for resource, entries in catalog.resources.items():
        model = MODELS[resource]
        existing = {row.immutable_code: row for row in model.query.all()}
        title_codes: dict[str, set[str]] = {}
        for row in existing.values():
            for title in (row.fa_name, row.en_name):
                title_codes.setdefault(_normalized_title(title), set()).add(row.immutable_code)
        for entry in entries:
            code = entry["code"]
            row = existing.get(code)
            duplicate_codes = set()
            for title in (entry["fa_name"], entry["en_name"]):
                duplicate_codes.update(title_codes.get(_normalized_title(title), set()))
            duplicate_codes.discard(code)
            if duplicate_codes:
                plan.conflicts.append({
                    "resource": resource,
                    "code": code,
                    "reason": "same title exists under a different code",
                })
                continue
            if row is None:
                plan.created_count += 1
                continue
            actual = _governed_values(resource, row)
            expected = dict(entry)
            if actual == expected:
                plan.unchanged_count += 1
            else:
                reason = "existing code is inactive" if not row.is_active else "governed values differ"
                plan.conflicts.append({"resource": resource, "code": code, "reason": reason})
    plan.conflict_count = len(plan.conflicts)
    return plan


def _new_row(resource: str, entry: dict[str, Any], parents: dict[str, CargoType]) -> Any:
    common = dict(
        immutable_code=entry["code"],
        fa_name=entry["fa_name"],
        en_name=entry["en_name"],
        description=entry["description"],
        display_order=entry["display_order"],
        is_active=True,
    )
    if resource == "cargo_types":
        parent_code = entry["parent_code"]
        return CargoType(parent=parents.get(parent_code) if parent_code else None, **common)
    if resource == "units_of_measure":
        return UnitOfMeasure(
            symbol=entry["symbol"],
            measurement_dimension=entry["measurement_dimension"],
            **common,
        )
    return ServiceType(**common)


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
    if not executed_by or len(executed_by) > 160:
        raise CatalogApplyError("a bounded named operator is required")
    approval_reference = approval_reference.strip()
    if not approval_reference or len(approval_reference) > 200:
        raise CatalogApplyError("a bounded approval reference is required")
    plan = plan_catalog(catalog, environment)
    run = ReferenceDataSeedRun(
        catalog_version=catalog.catalog_version,
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
    if plan.conflict_count:
        run.status = "refused"
        run.completed_at = datetime.utcnow()
        run.error_summary = "Catalog conflicts detected; no catalog writes were made."
        db.session.commit()
        return plan, run
    try:
        parents = {row.immutable_code: row for row in CargoType.query.all()}
        for resource in ("cargo_types", "service_types", "units_of_measure"):
            model = MODELS[resource]
            existing = {row.immutable_code for row in model.query.all()}
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
