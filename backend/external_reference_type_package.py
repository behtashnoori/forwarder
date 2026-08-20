"""Strict ADR-039 ExternalReferenceType package plan/apply adapter."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from backend.extensions import db
from backend.external_reference_models import (
    ExecutionUnitExternalReference,
    ExternalReferenceType,
    OperationalShipmentExternalReference,
    SEARCH_POLICIES,
    TYPE_CODES,
    TYPE_LIFECYCLES,
    UNIQUENESS_SCOPES,
)
from backend.mdpm_models import ArtifactAssociation, OperationalDocumentRequirement
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    OrganizationDocumentRequirement,
    ReferenceDataSeedRun,
    ShipmentRequest,
)
from backend.operational_models import ExecutionUnit, OperationalShipment
from backend.project_configuration_models import ProjectDocumentRequirement


SCHEMA_PATH = (
    Path(__file__).with_name("reference_data")
    / "external_references"
    / "schema-v1.json"
)
MAX_PACKAGE_BYTES = 256 * 1024
ALLOWED_ENVIRONMENTS = {
    "development", "dev", "local", "testing", "test", "uat", "staging",
    "production", "prod",
}
FORBIDDEN_CODES = frozenset({
    "COTAGE_NUMBER", "WAREHOUSE_RECEIPT_ID", "REGISTRATION_ORDER_NUMBER",
    "BARFARABARAN_REFERENCE",
})
EXPECTED_CODES = TYPE_CODES
PROTECTED_MODELS = (
    OrganizationDocumentRequirement,
    ProjectDocumentRequirement,
    OperationalDocumentRequirement,
    CaseDocumentRequirement,
    CaseDocumentFile,
    ArtifactAssociation,
    ShipmentRequest,
    OperationalShipment,
    ExecutionUnit,
    OperationalShipmentExternalReference,
    ExecutionUnitExternalReference,
)


class PackageValidationError(ValueError):
    pass


class PackageApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExternalReferenceTypePackage:
    payload: dict[str, Any]
    canonical_payload: dict[str, Any]
    checksum: str

    @property
    def definitions(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.canonical_payload["definitions"])


@dataclass(frozen=True)
class DefinitionPlan:
    code: str
    action: str
    conflicts: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "action": self.action, "conflicts": list(self.conflicts)}


@dataclass(frozen=True)
class ExternalReferenceTypePlan:
    catalog_name: str
    catalog_version: str
    schema_version: str
    checksum: str
    environment: str
    database_fingerprint: str
    definitions: tuple[DefinitionPlan, ...]

    @property
    def created_count(self) -> int:
        return sum(item.action == "CREATE" for item in self.definitions)

    @property
    def updated_count(self) -> int:
        return sum(item.action == "UPDATE_COMPATIBLE" for item in self.definitions)

    @property
    def unchanged_count(self) -> int:
        return sum(item.action == "NO_CHANGE" for item in self.definitions)

    @property
    def conflict_count(self) -> int:
        return sum(item.action == "CONFLICT" for item in self.definitions)

    def as_dict(self) -> dict[str, Any]:
        return {
            "catalog_name": self.catalog_name,
            "catalog_version": self.catalog_version,
            "schema_version": self.schema_version,
            "checksum": self.checksum,
            "environment": self.environment,
            "database_fingerprint": self.database_fingerprint,
            "planned_count": len(self.definitions),
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "conflict_count": self.conflict_count,
            "definitions": [item.as_dict() for item in self.definitions],
        }


def _nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(item) for item in value]
    if isinstance(value, dict):
        return {key: _nfc(value[key]) for key in sorted(value)}
    return value


def canonicalize_package(payload: dict[str, Any]) -> dict[str, Any]:
    result = _nfc({key: value for key, value in payload.items() if key != "checksum"})
    result["definitions"] = sorted(result.get("definitions", []), key=lambda x: x["code"])
    for definition in result["definitions"]:
        definition["owner_applicability"] = sorted(definition["owner_applicability"])
    return result


def checksum_for_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        canonicalize_package(payload), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_semantics(payload: dict[str, Any]) -> None:
    definitions = payload["definitions"]
    codes = [item["code"] for item in definitions]
    if len(definitions) != 3 or set(codes) != EXPECTED_CODES:
        raise PackageValidationError(
            "package must contain exactly the three ADR-039 V1 type codes"
        )
    if set(codes) & FORBIDDEN_CODES:
        raise PackageValidationError("package contains a forbidden type code")
    if len(codes) != len(set(codes)):
        raise PackageValidationError("duplicate type code")
    for item in definitions:
        for key, value in item.items():
            if isinstance(value, str) and value != value.strip():
                raise PackageValidationError(f"untrimmed text at {item['code']}.{key}")
        if item["lifecycle"] not in TYPE_LIFECYCLES:
            raise PackageValidationError(f"invalid lifecycle for {item['code']}")
        if item["normalization_policy"] != "TRIM_UPPERCASE_V1":
            raise PackageValidationError(f"invalid normalization policy for {item['code']}")
        if item["search_policy"] not in SEARCH_POLICIES:
            raise PackageValidationError(f"invalid search policy for {item['code']}")
        if item["uniqueness_scope"] not in UNIQUENESS_SCOPES:
            raise PackageValidationError(f"invalid uniqueness policy for {item['code']}")
        owners = set(item["owner_applicability"])
        if not owners or not owners <= {"OPERATIONAL_SHIPMENT", "EXECUTION_UNIT"}:
            raise PackageValidationError(f"invalid owner applicability for {item['code']}")
        provenance = item["provenance"]
        if item["lifecycle"] == "ACTIVE" and (
            provenance["status"] not in {"VERIFIED", "SOURCE_CONFIRMED"}
            or not provenance["source_authority"]
            or not provenance["source_title"]
            or not provenance["source_reference"]
        ):
            raise PackageValidationError(f"active provenance is insufficient for {item['code']}")


def load_package(path: str | Path) -> ExternalReferenceTypePackage:
    path = Path(path)
    if path.stat().st_size > MAX_PACKAGE_BYTES:
        raise PackageValidationError("package exceeds the size limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError("package is not valid UTF-8 JSON") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        error = errors[0]
        location = ".".join(str(x) for x in error.path) or "$"
        raise PackageValidationError(f"schema validation failed at {location}: {error.message}")
    _validate_semantics(payload)
    checksum = checksum_for_payload(payload)
    if payload["checksum"] != checksum:
        raise PackageValidationError("package checksum is invalid")
    return ExternalReferenceTypePackage(payload, canonicalize_package(payload), checksum)


def _expected_row(item: dict[str, Any]) -> dict[str, Any]:
    provenance = item["provenance"]
    return {
        "code": item["code"],
        "name_fa": item["name_fa"],
        "name_en": item["name_en"],
        "lifecycle_status": item["lifecycle"],
        "normalization_policy": item["normalization_policy"],
        "search_policy": item["search_policy"],
        "uniqueness_scope": item["uniqueness_scope"],
        "masking_policy": item["masking_policy"],
        "source_authority": provenance["source_authority"],
        "provenance_reference": provenance["source_reference"],
        "allows_operational_shipment": "OPERATIONAL_SHIPMENT" in item["owner_applicability"],
        "allows_execution_unit": "EXECUTION_UNIT" in item["owner_applicability"],
    }


def _row_state(row: ExternalReferenceType) -> dict[str, Any]:
    return {key: getattr(row, key) for key in _expected_row({
        "code": row.code, "name_fa": row.name_fa, "name_en": row.name_en,
        "lifecycle": row.lifecycle_status,
        "normalization_policy": row.normalization_policy,
        "search_policy": row.search_policy, "uniqueness_scope": row.uniqueness_scope,
        "masking_policy": row.masking_policy,
        "owner_applicability": ["OPERATIONAL_SHIPMENT"],
        "provenance": {"source_authority": row.source_authority, "source_reference": row.provenance_reference},
    })}


def _database_fingerprint(package: ExternalReferenceTypePackage, by_code: dict[str, ExternalReferenceType]) -> str:
    state = []
    for item in package.definitions:
        row = by_code.get(item["code"])
        state.append({"code": item["code"], "state": None if row is None else _row_state(row)})
    encoded = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def plan_package(package: ExternalReferenceTypePackage, environment: str) -> ExternalReferenceTypePlan:
    environment = environment.strip().lower()
    codes = [item["code"] for item in package.definitions]
    by_code = {row.code: row for row in ExternalReferenceType.query.filter(ExternalReferenceType.code.in_(codes)).all()}
    plans = []
    for item in package.definitions:
        row = by_code.get(item["code"])
        if row is None:
            plans.append(DefinitionPlan(item["code"], "CREATE"))
            continue
        expected = _expected_row(item)
        conflicts = tuple(key for key, value in expected.items() if getattr(row, key) != value)
        plans.append(DefinitionPlan(item["code"], "CONFLICT" if conflicts else "NO_CHANGE", conflicts))
    return ExternalReferenceTypePlan(
        package.canonical_payload["catalog_name"],
        package.canonical_payload["catalog_version"],
        package.canonical_payload["schema_version"], package.checksum, environment,
        _database_fingerprint(package, by_code), tuple(plans),
    )


def apply_package(
    package: ExternalReferenceTypePackage, *, environment: str, operator: str,
    approval_reference: str, expected_checksum: str,
    expected_plan_fingerprint: str, idempotency_key: str, confirm: bool,
    confirm_production: bool = False, actor_id: int | None = None,
    failure_hook=None,
):
    environment = environment.strip().lower()
    operator = operator.strip()
    approval_reference = approval_reference.strip()
    idempotency_key = idempotency_key.strip()
    if not confirm:
        raise PackageApplyError("apply requires explicit confirmation")
    if environment not in ALLOWED_ENVIRONMENTS:
        raise PackageApplyError("apply requires a recognized explicit environment")
    if environment in {"production", "prod"} and not confirm_production:
        raise PackageApplyError("Production apply requires explicit production confirmation")
    if not operator or len(operator) > 160:
        raise PackageApplyError("a bounded named operator is required")
    if not approval_reference or len(approval_reference) > 200:
        raise PackageApplyError("a bounded approval reference is required")
    if expected_checksum != package.checksum:
        raise PackageApplyError("expected checksum does not match package")
    if not idempotency_key or len(idempotency_key) > 128:
        raise PackageApplyError("a bounded idempotency key is required")
    if actor_id is None:
        raise PackageApplyError("an authorized actor is required")
    request_hash = hashlib.sha256(json.dumps({
        "checksum": package.checksum, "environment": environment,
        "operator": operator, "approval_reference": approval_reference,
        "plan": expected_plan_fingerprint,
    }, sort_keys=True).encode()).hexdigest()
    prior = ReferenceDataSeedRun.query.filter_by(idempotency_key=idempotency_key).one_or_none()
    if prior:
        if prior.request_hash != request_hash:
            raise PackageApplyError("idempotency key was already used with a different request")
        return plan_package(package, environment), prior
    plan = plan_package(package, environment)
    if plan.database_fingerprint != expected_plan_fingerprint:
        raise PackageApplyError("reviewed plan fingerprint is stale")
    run = ReferenceDataSeedRun(
        catalog_family="EXTERNAL_REFERENCE_TYPE", catalog_name=plan.catalog_name,
        catalog_version=plan.catalog_version, schema_version=plan.schema_version,
        source_bundle_version=package.canonical_payload["source_bundle_version"],
        checksum=package.checksum, environment=environment, mode="apply",
        planned_count=len(plan.definitions), created_count=0, updated_count=0,
        unchanged_count=plan.unchanged_count, conflict_count=plan.conflict_count,
        status="started", executed_by=operator, approval_reference=approval_reference,
        idempotency_key=idempotency_key, request_hash=request_hash,
    )
    db.session.add(run)
    db.session.commit()
    if plan.conflict_count:
        run.status = "refused"
        run.completed_at = datetime.now(timezone.utc)
        run.error_summary = "External reference type conflicts detected; no catalog writes were made."
        db.session.commit()
        return plan, run
    try:
        codes = [item["code"] for item in package.definitions]
        locked = {row.code: row for row in ExternalReferenceType.query.filter(ExternalReferenceType.code.in_(codes)).with_for_update().all()}
        rebound = plan_package(package, environment)
        if rebound.database_fingerprint != expected_plan_fingerprint:
            raise PackageApplyError("reviewed plan became stale during apply")
        before = tuple(model.query.count() for model in PROTECTED_MODELS)
        for item in package.definitions:
            if item["code"] not in locked:
                db.session.add(ExternalReferenceType(
                    **_expected_row(item), revision=1,
                    created_by_user_id=actor_id, updated_by_user_id=actor_id,
                ))
        db.session.flush()
        if failure_hook:
            failure_hook()
        after = tuple(model.query.count() for model in PROTECTED_MODELS)
        if before != after:
            raise PackageApplyError("catalog apply attempted a forbidden tenant/policy side effect")
        run.status = "succeeded"
        run.created_count = plan.created_count
        run.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return plan, run
    except Exception as exc:
        db.session.rollback()
        persisted = ReferenceDataSeedRun.query.filter_by(public_id=run.public_id).one()
        persisted.status = "failed"
        persisted.completed_at = datetime.now(timezone.utc)
        persisted.error_summary = f"External reference type apply failed ({type(exc).__name__})."[:500]
        db.session.commit()
        if isinstance(exc, PackageApplyError):
            raise
        raise PackageApplyError("external reference type apply failed; catalog writes were rolled back") from exc
