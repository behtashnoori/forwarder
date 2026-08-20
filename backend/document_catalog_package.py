"""Strict ADR-036 Document Master Catalog package plan/apply engine."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

from backend.extensions import db
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    Country,
    DocumentCatalogAuditEvent,
    DocumentDefinition,
    DocumentDefinitionAlias,
    DocumentDefinitionBusinessScope,
    DocumentDefinitionJurisdiction,
    DocumentDefinitionMode,
    DocumentDefinitionProvenance,
    DocumentDefinitionStage,
    OrganizationDocumentRequirement,
    ReferenceDataSeedRun,
)
from backend.mdpm_models import ArtifactAssociation, OperationalDocumentRequirement
from backend.project_configuration_models import ProjectDocumentRequirement
from backend.services.document_catalog_service import (
    normalize_alias,
    validate_activation,
)

SCHEMA_PATH = (
    Path(__file__).with_name("reference_data") / "documents" / "schema-v1.json"
)
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
ALLOWED_ENVIRONMENTS = {
    "development",
    "dev",
    "local",
    "testing",
    "test",
    "uat",
    "staging",
    "production",
    "prod",
}
LIFECYCLE_ORDER = {
    "DRAFT": 0,
    "REVIEWED": 1,
    "SOURCE_CONFIRMED": 2,
    "ACTIVE": 3,
    "DEPRECATED": 4,
}
NULLABLE_METADATA = (
    "name_fa",
    "name_en",
    "description_fa",
    "description_en",
    "family_code",
    "reference_number_label_fa",
    "reference_number_label_en",
    "expiry_applicable",
)


class PackageValidationError(ValueError):
    pass


class PackageApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentCatalogPackage:
    payload: dict[str, Any]
    canonical_payload: dict[str, Any]
    checksum: str

    @property
    def definitions(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.canonical_payload["definitions"])


@dataclass
class DefinitionPlan:
    code: str
    action: str
    expected_revision: int | None = None
    metadata_changes: list[str] = field(default_factory=list)
    alias_additions: list[str] = field(default_factory=list)
    jurisdiction_additions: list[str] = field(default_factory=list)
    mode_additions: list[str] = field(default_factory=list)
    stage_additions: list[str] = field(default_factory=list)
    business_scope_additions: list[str] = field(default_factory=list)
    provenance_additions: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "action": self.action,
            "expected_revision": self.expected_revision,
            "metadata_changes": self.metadata_changes,
            "alias_additions": self.alias_additions,
            "jurisdiction_additions": self.jurisdiction_additions,
            "mode_additions": self.mode_additions,
            "stage_additions": self.stage_additions,
            "business_scope_additions": self.business_scope_additions,
            "provenance_additions": self.provenance_additions,
            "conflicts": self.conflicts[:20],
        }


@dataclass
class DocumentCatalogPlan:
    catalog_name: str
    catalog_version: str
    schema_version: str
    checksum: str
    environment: str
    database_fingerprint: str
    definitions: list[DefinitionPlan]

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
    for definition in result.get("definitions", []):
        definition["aliases"] = sorted(
            definition["aliases"],
            key=lambda item: (
                normalize_alias(item["display_value"]),
                item["locale"],
                item["alias_kind"],
            ),
        )
        definition["jurisdictions"] = sorted(
            definition["jurisdictions"], key=_jurisdiction_key
        )
        for key in ("transport_modes", "process_stages", "business_scopes"):
            definition[key] = sorted(definition[key])
        definition["provenance"] = sorted(definition["provenance"], key=_provenance_key)
        definition["compatibility"]["allowed_formats"] = sorted(
            definition["compatibility"]["allowed_formats"]
        )
    result["definitions"] = sorted(
        result.get("definitions", []), key=lambda item: item["code"]
    )
    return result


def checksum_for_payload(payload: dict[str, Any]) -> str:
    canonical = canonicalize_package(payload)
    encoded = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _walk_strings(value: Any, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, f"{path}.{key}")


def _jurisdiction_key(item: dict[str, Any]) -> str:
    return (
        f"COUNTRY:{item['country_code']}" if item["kind"] == "COUNTRY" else item["kind"]
    )


def _provenance_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        item["source_authority_code"],
        item["source_title"].casefold(),
        item.get("jurisdiction_key") or "",
    )


def _validate_semantics(payload: dict[str, Any]) -> None:
    for path, value in _walk_strings(payload):
        if value != value.strip():
            raise PackageValidationError(f"untrimmed text at {path}")
    codes: set[str] = set()
    aliases: dict[str, str] = {}
    for definition in payload["definitions"]:
        code = definition["code"]
        if code in codes:
            raise PackageValidationError(f"duplicate definition code: {code}")
        codes.add(code)
        local_aliases: set[str] = set()
        for alias in definition["aliases"]:
            normalized = normalize_alias(alias["display_value"])
            if normalized in local_aliases:
                raise PackageValidationError(f"duplicate alias for {code}")
            if normalized in aliases and aliases[normalized] != code:
                raise PackageValidationError("ambiguous alias in package")
            local_aliases.add(normalized)
            aliases[normalized] = code
        jurisdiction_keys = [
            _jurisdiction_key(item) for item in definition["jurisdictions"]
        ]
        if len(jurisdiction_keys) != len(set(jurisdiction_keys)):
            raise PackageValidationError(f"duplicate jurisdiction for {code}")
        provenance_keys = [_provenance_key(item) for item in definition["provenance"]]
        if len(provenance_keys) != len(set(provenance_keys)):
            raise PackageValidationError(f"duplicate provenance for {code}")
        for source in definition["provenance"]:
            if source.get("source_url"):
                try:
                    parsed = urlsplit(source["source_url"])
                    valid_url = parsed.scheme in {"http", "https"} and bool(
                        parsed.hostname
                    )
                except ValueError:
                    valid_url = False
                if not valid_url:
                    raise PackageValidationError(f"invalid source URL for {code}")
        target = definition["lifecycle_target"]
        if target in {"SOURCE_CONFIRMED", "ACTIVE"}:
            if definition["source_review_status"] not in {
                "VERIFIED",
                "SOURCE_CONFIRMED",
            }:
                raise PackageValidationError(f"confirmed review required for {code}")
            confirmed = {
                item.get("jurisdiction_key")
                for item in definition["provenance"]
                if item["review_status"] in {"VERIFIED", "SOURCE_CONFIRMED"}
            }
            if not definition["jurisdictions"] or not all(
                key in confirmed or "GLOBAL" in confirmed for key in jurisdiction_keys
            ):
                raise PackageValidationError(
                    f"confirmed provenance coverage required for {code}"
                )
        if target == "DEPRECATED":
            raise PackageValidationError(
                "new package deprecation commands are not supported in schema v1"
            )
    for alias, owner in aliases.items():
        if alias in codes and alias != owner:
            raise PackageValidationError("alias collides with another canonical code")


def load_package(path: Path) -> DocumentCatalogPackage:
    path = Path(path)
    if path.suffix.lower() != ".json" or not path.is_file():
        raise PackageValidationError("package must be an explicit local JSON file")
    if path.stat().st_size > MAX_PACKAGE_BYTES:
        raise PackageValidationError("package exceeds size limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError(
            "package is not readable strict UTF-8 JSON"
        ) from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            payload
        ),
        key=lambda item: list(item.path),
    )
    if errors:
        raise PackageValidationError(
            f"package schema is invalid at {'.'.join(map(str, errors[0].path)) or '$'}"
        )
    _validate_semantics(payload)
    checksum = checksum_for_payload(payload)
    if payload["checksum"] != checksum:
        raise PackageValidationError(
            "package checksum does not match canonical content"
        )
    return DocumentCatalogPackage(
        payload=payload,
        canonical_payload=canonicalize_package(payload),
        checksum=checksum,
    )


def _batch_state(package: DocumentCatalogPackage):
    codes = [item["code"] for item in package.definitions]
    rows = DocumentDefinition.query.filter(DocumentDefinition.code.in_(codes)).all()
    by_code = {row.code: row for row in rows}
    ids = [row.id for row in rows]

    def grouped(model):
        result: dict[int, list[Any]] = {}
        for item in (
            model.query.filter(model.document_definition_id.in_(ids)).all()
            if ids
            else []
        ):
            result.setdefault(item.document_definition_id, []).append(item)
        return result

    relations = {
        "aliases": grouped(DocumentDefinitionAlias),
        "jurisdictions": grouped(DocumentDefinitionJurisdiction),
        "modes": grouped(DocumentDefinitionMode),
        "stages": grouped(DocumentDefinitionStage),
        "scopes": grouped(DocumentDefinitionBusinessScope),
        "provenance": grouped(DocumentDefinitionProvenance),
    }
    return by_code, relations


def _existing_fingerprint(package: DocumentCatalogPackage, by_code, relations) -> str:
    state = []
    for definition in package.definitions:
        row = by_code.get(definition["code"])
        if not row:
            state.append({"code": definition["code"], "absent": True})
            continue
        state.append(
            {
                "code": row.code,
                "public_id": row.public_id,
                "revision": row.revision,
                "lifecycle": row.catalog_lifecycle_status,
                "review": row.source_review_status,
                "aliases": sorted(
                    (x.normalized_value, x.is_active)
                    for x in relations["aliases"].get(row.id, [])
                ),
                "jurisdictions": sorted(
                    x.applicability_key
                    for x in relations["jurisdictions"].get(row.id, [])
                ),
                "modes": sorted(
                    x.mode_code for x in relations["modes"].get(row.id, [])
                ),
                "stages": sorted(
                    x.stage_code for x in relations["stages"].get(row.id, [])
                ),
                "scopes": sorted(
                    x.scope_code for x in relations["scopes"].get(row.id, [])
                ),
                "provenance": sorted(
                    _db_provenance_key(x)
                    + (
                        x.review_status,
                        x.source_reference or "",
                        x.source_version or "",
                    )
                    for x in relations["provenance"].get(row.id, [])
                ),
            }
        )
    global_aliases = sorted(
        (x.normalized_value, x.document_definition_id)
        for x in DocumentDefinitionAlias.query.filter(
            DocumentDefinitionAlias.normalized_value.in_(
                [
                    normalize_alias(a["display_value"])
                    for d in package.definitions
                    for a in d["aliases"]
                ]
            )
        ).all()
    )
    encoded = json.dumps(
        {
            "checksum": package.checksum,
            "state": state,
            "global_aliases": global_aliases,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _db_provenance_key(item) -> tuple[str, str, str]:
    return (
        item.source_authority_code,
        item.source_title.casefold(),
        item.jurisdiction_key or "",
    )


def _plan_definition(
    definition, row, relations, global_alias_owners, available_country_codes
) -> DefinitionPlan:
    if row is None:
        plan = DefinitionPlan(code=definition["code"], action="CREATE")
        for alias in definition["aliases"]:
            normalized = normalize_alias(alias["display_value"])
            if normalized in global_alias_owners:
                plan.conflicts.append(f"alias collision: {normalized}")
        for item in definition["jurisdictions"]:
            if (
                item["kind"] == "COUNTRY"
                and item["country_code"] not in available_country_codes
            ):
                plan.conflicts.append(f"country is unavailable: {item['country_code']}")
        if plan.conflicts:
            plan.action = "CONFLICT"
        return plan
    plan = DefinitionPlan(
        code=row.code, action="NO_CHANGE", expected_revision=row.revision
    )
    compatibility = definition["compatibility"]
    actual_compatibility = {
        "title": row.title,
        "description": row.description,
        "applicability_scope": row.applicability_scope,
        "allowed_formats": sorted(json.loads(row.allowed_formats)),
        "max_file_size_bytes": row.max_file_size_bytes,
        "max_active_file_count": row.max_active_file_count,
        "sort_order": row.sort_order,
    }
    if actual_compatibility != compatibility:
        plan.conflicts.append("manual definition compatibility fields differ")
    package_metadata = {
        "name_fa": definition["name_fa"],
        "name_en": definition["name_en"],
        "description_fa": definition["description_fa"],
        "description_en": definition["description_en"],
        "family_code": definition["family"],
        "reference_number_label_fa": definition["reference_number_label_fa"],
        "reference_number_label_en": definition["reference_number_label_en"],
        "expiry_applicable": definition["expiry_applicable"],
    }
    for key, expected in package_metadata.items():
        actual = getattr(row, key)
        if actual is None and expected is not None:
            plan.metadata_changes.append(key)
        elif actual != expected:
            plan.conflicts.append(f"governed metadata differs: {key}")
    if row.organization_overridable != definition["organization_overridable"]:
        plan.conflicts.append("organization_overridable differs")
    if row.source_review_status != definition["source_review_status"]:
        if row.source_review_status in {
            "SOURCE_CONFIRMATION_REQUIRED",
            "DOMAIN_CONFIRMATION_REQUIRED",
        } and definition["source_review_status"] in {"SOURCE_CONFIRMED", "VERIFIED"}:
            plan.metadata_changes.append("source_review_status")
        else:
            plan.conflicts.append("unsafe source review change")
    target = definition["lifecycle_target"]
    if row.catalog_lifecycle_status != target:
        if (
            LIFECYCLE_ORDER[target] >= LIFECYCLE_ORDER[row.catalog_lifecycle_status]
            and row.catalog_lifecycle_status != "DEPRECATED"
        ):
            plan.metadata_changes.append("catalog_lifecycle_status")
        else:
            plan.conflicts.append("unsafe lifecycle change")
    existing_aliases = {
        x.normalized_value for x in relations["aliases"].get(row.id, [])
    }
    for alias in definition["aliases"]:
        normalized = normalize_alias(alias["display_value"])
        owner = global_alias_owners.get(normalized)
        if owner is not None and owner != row.id:
            plan.conflicts.append(f"alias collision: {normalized}")
        elif normalized not in existing_aliases:
            plan.alias_additions.append(normalized)
    expected_j = {_jurisdiction_key(item) for item in definition["jurisdictions"]}
    actual_j = {x.applicability_key for x in relations["jurisdictions"].get(row.id, [])}
    plan.jurisdiction_additions = sorted(expected_j - actual_j)
    for item in definition["jurisdictions"]:
        if (
            item["kind"] == "COUNTRY"
            and item["country_code"] not in available_country_codes
        ):
            plan.conflicts.append(f"country is unavailable: {item['country_code']}")
    for key, values, attr, target_list in (
        (
            "transport_modes",
            relations["modes"].get(row.id, []),
            "mode_code",
            plan.mode_additions,
        ),
        (
            "process_stages",
            relations["stages"].get(row.id, []),
            "stage_code",
            plan.stage_additions,
        ),
        (
            "business_scopes",
            relations["scopes"].get(row.id, []),
            "scope_code",
            plan.business_scope_additions,
        ),
    ):
        target_list.extend(
            sorted(set(definition[key]) - {getattr(x, attr) for x in values})
        )
    existing_sources = {
        _db_provenance_key(x): x for x in relations["provenance"].get(row.id, [])
    }
    for source in definition["provenance"]:
        key = _provenance_key(source)
        current = existing_sources.get(key)
        if not current:
            plan.provenance_additions.append("|".join(key))
        elif (
            current.review_status,
            current.source_reference,
            current.source_version,
            current.source_date.isoformat() if current.source_date else None,
            current.notes,
        ) != (
            source["review_status"],
            source.get("source_url") or source.get("source_reference"),
            source.get("source_version"),
            source.get("source_date"),
            source.get("notes"),
        ):
            plan.conflicts.append("provenance differs for " + "|".join(key))
    if plan.conflicts:
        plan.action = "CONFLICT"
    elif any(
        (
            plan.metadata_changes,
            plan.alias_additions,
            plan.jurisdiction_additions,
            plan.mode_additions,
            plan.stage_additions,
            plan.business_scope_additions,
            plan.provenance_additions,
        )
    ):
        plan.action = "UPDATE_COMPATIBLE"
    return plan


def plan_package(
    package: DocumentCatalogPackage, environment: str
) -> DocumentCatalogPlan:
    by_code, relations = _batch_state(package)
    normalized = [
        normalize_alias(alias["display_value"])
        for definition in package.definitions
        for alias in definition["aliases"]
    ]
    global_alias_owners = (
        {
            row.normalized_value: row.document_definition_id
            for row in DocumentDefinitionAlias.query.filter(
                DocumentDefinitionAlias.normalized_value.in_(normalized)
            ).all()
        }
        if normalized
        else {}
    )
    requested_country_codes = {
        item["country_code"]
        for definition in package.definitions
        for item in definition["jurisdictions"]
        if item["kind"] == "COUNTRY"
    }
    available_country_codes = (
        {
            row.code
            for row in Country.query.filter(Country.code.in_(requested_country_codes))
            .with_entities(Country.code)
            .all()
        }
        if requested_country_codes
        else set()
    )
    items = [
        _plan_definition(
            definition,
            by_code.get(definition["code"]),
            relations,
            global_alias_owners,
            available_country_codes,
        )
        for definition in package.definitions
    ]
    return DocumentCatalogPlan(
        package.canonical_payload["catalog_name"],
        package.canonical_payload["catalog_version"],
        package.canonical_payload["schema_version"],
        package.checksum,
        environment,
        _existing_fingerprint(package, by_code, relations),
        items,
    )


def _new_definition(definition, actor_id):
    compatibility = definition["compatibility"]
    return DocumentDefinition(
        code=definition["code"],
        title=compatibility["title"],
        description=compatibility["description"],
        name_fa=definition["name_fa"],
        name_en=definition["name_en"],
        description_fa=definition["description_fa"],
        description_en=definition["description_en"],
        family_code=definition["family"],
        reference_number_label_fa=definition["reference_number_label_fa"],
        reference_number_label_en=definition["reference_number_label_en"],
        expiry_applicable=definition["expiry_applicable"],
        organization_overridable=definition["organization_overridable"],
        catalog_lifecycle_status="DRAFT",
        source_review_status=definition["source_review_status"],
        is_required=False,
        allowed_formats=json.dumps(compatibility["allowed_formats"], sort_keys=True),
        max_file_size_bytes=compatibility["max_file_size_bytes"],
        max_active_file_count=compatibility["max_active_file_count"],
        sort_order=compatibility["sort_order"],
        is_active=False,
        applicability_scope=compatibility["applicability_scope"],
        created_by=actor_id,
        updated_by=actor_id,
    )


def _add_relations(row, definition, actor_id, country_by_code):
    aliases = {
        x.normalized_value
        for x in DocumentDefinitionAlias.query.filter_by(
            document_definition_id=row.id
        ).all()
    }
    for item in definition["aliases"]:
        normalized = normalize_alias(item["display_value"])
        if normalized not in aliases:
            db.session.add(
                DocumentDefinitionAlias(
                    document_definition_id=row.id,
                    locale=item["locale"],
                    display_value=item["display_value"],
                    normalized_value=normalized,
                    alias_kind=item["alias_kind"],
                    is_active=True,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
    jurisdictions = {
        x.applicability_key
        for x in DocumentDefinitionJurisdiction.query.filter_by(
            document_definition_id=row.id
        ).all()
    }
    for item in definition["jurisdictions"]:
        key = _jurisdiction_key(item)
        if key not in jurisdictions:
            country = country_by_code.get(item.get("country_code"))
            if item["kind"] == "COUNTRY" and not country:
                raise PackageApplyError(f"country is unavailable for {row.code}")
            db.session.add(
                DocumentDefinitionJurisdiction(
                    document_definition_id=row.id,
                    applicability_kind=item["kind"],
                    applicability_key=key,
                    country_id=country.id if country else None,
                )
            )
    for model, key, values in (
        (DocumentDefinitionMode, "mode_code", definition["transport_modes"]),
        (DocumentDefinitionStage, "stage_code", definition["process_stages"]),
        (DocumentDefinitionBusinessScope, "scope_code", definition["business_scopes"]),
    ):
        existing = {
            getattr(x, key)
            for x in model.query.filter_by(document_definition_id=row.id).all()
        }
        for value in values:
            if value not in existing:
                db.session.add(model(document_definition_id=row.id, **{key: value}))
    sources = {
        _db_provenance_key(x)
        for x in DocumentDefinitionProvenance.query.filter_by(
            document_definition_id=row.id
        ).all()
    }
    for item in definition["provenance"]:
        if _provenance_key(item) not in sources:
            db.session.add(
                DocumentDefinitionProvenance(
                    document_definition_id=row.id,
                    source_authority_code=item["source_authority_code"],
                    source_authority_name=item["source_authority_name"],
                    source_title=item["source_title"],
                    source_reference=item.get("source_url")
                    or item.get("source_reference"),
                    source_version=item.get("source_version"),
                    source_date=date.fromisoformat(item["source_date"])
                    if item.get("source_date")
                    else None,
                    jurisdiction_key=item.get("jurisdiction_key"),
                    review_status=item["review_status"],
                    reviewed_by=actor_id,
                    reviewed_at=datetime.now(timezone.utc),
                    notes=item.get("notes"),
                )
            )


def _apply_definition(definition, row, actor_id, run_id, country_by_code):
    created = row is None
    previous_lifecycle = None if created else row.catalog_lifecycle_status
    if created:
        row = _new_definition(definition, actor_id)
        db.session.add(row)
        db.session.flush()
    else:
        for key in NULLABLE_METADATA:
            expected = definition["family"] if key == "family_code" else definition[key]
            if getattr(row, key) is None and expected is not None:
                setattr(row, key, expected)
        if row.source_review_status != definition["source_review_status"]:
            row.source_review_status = definition["source_review_status"]
    _add_relations(row, definition, actor_id, country_by_code)
    db.session.flush()
    target = definition["lifecycle_target"]
    if target == "ACTIVE":
        validate_activation(row)
        row.is_active = True
    row.catalog_lifecycle_status = target
    if not created:
        row.revision += 1
    row.updated_by = actor_id
    db.session.add(
        DocumentCatalogAuditEvent(
            definition_public_id=row.public_id,
            definition_code=row.code,
            actor_id=actor_id,
            action="PACKAGE_CREATED" if created else "PACKAGE_ENRICHED",
            previous_revision=None if created else row.revision - 1,
            resulting_revision=row.revision,
            previous_lifecycle=previous_lifecycle,
            resulting_lifecycle=target,
            approval_reference=run_id,
            idempotency_key=f"{run_id}:{row.code}",
            request_hash=None,
            result="SUCCEEDED",
            details=json.dumps({"catalog_run_id": run_id}, sort_keys=True),
        )
    )


def apply_package(
    package: DocumentCatalogPackage,
    *,
    environment: str,
    operator: str,
    approval_reference: str,
    expected_checksum: str,
    expected_plan_fingerprint: str,
    idempotency_key: str,
    confirm: bool,
    confirm_production: bool = False,
    actor_id: int | None = None,
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
        raise PackageApplyError(
            "Production apply requires explicit production confirmation"
        )
    if not operator or len(operator) > 160:
        raise PackageApplyError("a bounded named operator is required")
    if not approval_reference or len(approval_reference) > 200:
        raise PackageApplyError("a bounded approval reference is required")
    if expected_checksum != package.checksum:
        raise PackageApplyError("expected checksum does not match package")
    if not idempotency_key or len(idempotency_key) > 128:
        raise PackageApplyError("a bounded idempotency key is required")
    request_hash = hashlib.sha256(
        json.dumps(
            {
                "checksum": package.checksum,
                "environment": environment,
                "operator": operator,
                "approval_reference": approval_reference,
                "plan": expected_plan_fingerprint,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    prior = ReferenceDataSeedRun.query.filter_by(
        idempotency_key=idempotency_key
    ).one_or_none()
    if prior:
        if prior.request_hash != request_hash:
            raise PackageApplyError(
                "idempotency key was already used with a different request"
            )
        return plan_package(package, environment), prior
    plan = plan_package(package, environment)
    if plan.database_fingerprint != expected_plan_fingerprint:
        raise PackageApplyError("reviewed plan fingerprint is stale")
    run = ReferenceDataSeedRun(
        catalog_family="DOCUMENT_MASTER",
        catalog_name=package.canonical_payload["catalog_name"],
        catalog_version=package.canonical_payload["catalog_version"],
        schema_version=package.canonical_payload["schema_version"],
        source_bundle_version=package.canonical_payload["source_bundle_version"],
        checksum=package.checksum,
        environment=environment,
        mode="apply",
        planned_count=len(plan.definitions),
        created_count=0,
        updated_count=0,
        unchanged_count=plan.unchanged_count,
        conflict_count=plan.conflict_count,
        status="started",
        executed_by=operator,
        approval_reference=approval_reference,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    db.session.add(run)
    db.session.commit()
    if plan.conflict_count:
        run.status = "refused"
        run.completed_at = datetime.now(timezone.utc)
        run.error_summary = (
            "Document catalog conflicts detected; no catalog writes were made."
        )
        db.session.commit()
        return plan, run
    try:
        codes = [item["code"] for item in package.definitions]
        locked = {
            row.code: row
            for row in DocumentDefinition.query.filter(
                DocumentDefinition.code.in_(codes)
            )
            .with_for_update()
            .all()
        }
        rebound = plan_package(package, environment)
        if rebound.database_fingerprint != expected_plan_fingerprint:
            raise PackageApplyError("reviewed plan became stale during apply")
        if rebound.conflict_count:
            raise PackageApplyError("catalog conflict appeared during apply")
        before = (
            OrganizationDocumentRequirement.query.count(),
            ProjectDocumentRequirement.query.count(),
            CaseDocumentRequirement.query.count(),
            OperationalDocumentRequirement.query.count(),
            ArtifactAssociation.query.count(),
            CaseDocumentFile.query.count(),
        )
        country_codes = {
            item["country_code"]
            for definition in package.definitions
            for item in definition["jurisdictions"]
            if item["kind"] == "COUNTRY"
        }
        country_by_code = (
            {
                row.code: row
                for row in Country.query.filter(Country.code.in_(country_codes)).all()
            }
            if country_codes
            else {}
        )
        for definition, item in zip(package.definitions, plan.definitions):
            if item.action in {"CREATE", "UPDATE_COMPATIBLE"}:
                _apply_definition(
                    definition,
                    locked.get(definition["code"]),
                    actor_id,
                    run.public_id,
                    country_by_code,
                )
        if failure_hook:
            failure_hook()
        after = (
            OrganizationDocumentRequirement.query.count(),
            ProjectDocumentRequirement.query.count(),
            CaseDocumentRequirement.query.count(),
            OperationalDocumentRequirement.query.count(),
            ArtifactAssociation.query.count(),
            CaseDocumentFile.query.count(),
        )
        if before != after:
            raise PackageApplyError(
                "catalog apply attempted a forbidden document-policy side effect"
            )
        run.status = "succeeded"
        run.created_count = plan.created_count
        run.updated_count = plan.updated_count
        run.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return plan, run
    except Exception as exc:
        db.session.rollback()
        persisted = ReferenceDataSeedRun.query.filter_by(public_id=run.public_id).one()
        persisted.status = "failed"
        persisted.completed_at = datetime.now(timezone.utc)
        persisted.error_summary = (
            f"Document catalog apply failed ({type(exc).__name__})."[:500]
        )
        db.session.commit()
        if isinstance(exc, PackageApplyError):
            raise
        raise PackageApplyError(
            "document catalog apply failed; catalog writes were rolled back"
        ) from exc
