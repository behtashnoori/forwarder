"""Governed, tenant-neutral Document Master Catalog aggregate service."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import or_

from backend.extensions import db
from backend.models import (
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
    DOCUMENT_ALIAS_KINDS,
    DOCUMENT_BUSINESS_SCOPE_CODES,
    DOCUMENT_CATALOG_LIFECYCLES,
    DOCUMENT_FAMILIES,
    DOCUMENT_MODE_CODES,
    DOCUMENT_SOURCE_REVIEW_STATUSES,
    DOCUMENT_STAGE_CODES,
)


class CatalogError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def normalize_alias(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(normalized.split())


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _require_revision(row: DocumentDefinition, payload: dict[str, Any]) -> None:
    try:
        expected = int(payload["expected_revision"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogError("expected_revision is required", 400) from exc
    if expected != row.revision:
        raise CatalogError("Document definition revision conflict", 409)


def _check_idempotency(
    row: DocumentDefinition, payload: dict[str, Any], idempotency_key: str
) -> dict[str, Any] | None:
    prior = DocumentCatalogAuditEvent.query.filter_by(
        idempotency_key=idempotency_key
    ).one_or_none()
    if not prior:
        return None
    if prior.definition_public_id != row.public_id or prior.request_hash != _hash(
        payload
    ):
        raise CatalogError(
            "Idempotency key was already used with a different request", 409
        )
    return serialize(row)


def _audit(
    row: DocumentDefinition,
    actor_id: int,
    action: str,
    *,
    previous_revision: int,
    previous_lifecycle: str,
    payload: dict[str, Any],
    idempotency_key: str,
    approval_reference: str | None = None,
) -> None:
    request_hash = _hash(payload)
    db.session.add(
        DocumentCatalogAuditEvent(
            definition_public_id=row.public_id,
            definition_code=row.code,
            actor_id=actor_id,
            action=action,
            previous_revision=previous_revision,
            resulting_revision=row.revision,
            previous_lifecycle=previous_lifecycle,
            resulting_lifecycle=row.catalog_lifecycle_status,
            approval_reference=approval_reference,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result="SUCCEEDED",
            details=json.dumps(
                {
                    "changed_fields": sorted(
                        k for k in payload if k != "expected_revision"
                    )
                }
            ),
        )
    )


def _alias_item(row):
    return {
        "public_id": row.public_id,
        "locale": row.locale,
        "display_value": row.display_value,
        "normalized_value": row.normalized_value,
        "alias_kind": row.alias_kind,
        "is_active": row.is_active,
    }


def serialize(
    row: DocumentDefinition,
    related: dict[str, dict[int, list[Any]]] | None = None,
    countries: dict[int, Country] | None = None,
) -> dict[str, Any]:
    def rows(name, model, order):
        if related is not None:
            return related[name].get(row.id, [])
        return (
            model.query.filter_by(document_definition_id=row.id).order_by(order).all()
        )

    aliases = rows("aliases", DocumentDefinitionAlias, DocumentDefinitionAlias.id)
    jurisdictions = rows(
        "jurisdictions",
        DocumentDefinitionJurisdiction,
        DocumentDefinitionJurisdiction.applicability_key,
    )
    modes = rows("modes", DocumentDefinitionMode, DocumentDefinitionMode.mode_code)
    stages = rows("stages", DocumentDefinitionStage, DocumentDefinitionStage.stage_code)
    scopes = rows(
        "scopes",
        DocumentDefinitionBusinessScope,
        DocumentDefinitionBusinessScope.scope_code,
    )
    sources = rows(
        "sources", DocumentDefinitionProvenance, DocumentDefinitionProvenance.id
    )
    return {
        "public_id": row.public_id,
        "code": row.code,
        "title": row.title,
        "name_fa": row.name_fa,
        "name_en": row.name_en,
        "description": row.description,
        "description_fa": row.description_fa,
        "description_en": row.description_en,
        "family_code": row.family_code,
        "reference_number_label_fa": row.reference_number_label_fa,
        "reference_number_label_en": row.reference_number_label_en,
        "expiry_applicable": row.expiry_applicable,
        "organization_overridable": row.organization_overridable,
        "catalog_lifecycle_status": row.catalog_lifecycle_status,
        "source_review_status": row.source_review_status,
        "is_active": row.is_active,
        "is_required": row.is_required,
        "applicability_scope": row.applicability_scope,
        "revision": row.revision,
        "aliases": [_alias_item(x) for x in aliases],
        "jurisdictions": [
            {
                "public_id": x.public_id,
                "kind": x.applicability_kind,
                "key": x.applicability_key,
                "country_code": (
                    (countries or {}).get(x.country_id)
                    or db.session.get(Country, x.country_id)
                ).code
                if x.country_id
                else None,
            }
            for x in jurisdictions
        ],
        "modes": [x.mode_code for x in modes],
        "stages": [x.stage_code for x in stages],
        "business_scopes": [x.scope_code for x in scopes],
        "provenance": [
            {
                "public_id": x.public_id,
                "source_authority_code": x.source_authority_code,
                "source_authority_name": x.source_authority_name,
                "source_title": x.source_title,
                "source_reference": x.source_reference,
                "source_version": x.source_version,
                "source_date": x.source_date.isoformat() if x.source_date else None,
                "jurisdiction_key": x.jurisdiction_key,
                "review_status": x.review_status,
                "reviewed_at": x.reviewed_at.isoformat() if x.reviewed_at else None,
                "notes": x.notes,
            }
            for x in sources
        ],
    }


def list_catalog(filters: dict[str, str]) -> list[dict[str, Any]]:
    query = DocumentDefinition.query
    search = normalize_alias(filters.get("q", ""))
    if search:
        alias_ids = db.session.query(
            DocumentDefinitionAlias.document_definition_id
        ).filter(
            DocumentDefinitionAlias.is_active.is_(True),
            DocumentDefinitionAlias.normalized_value.contains(search),
        )
        query = query.filter(
            or_(
                DocumentDefinition.code.ilike(f"%{search}%"),
                DocumentDefinition.title.ilike(f"%{search}%"),
                DocumentDefinition.name_fa.ilike(f"%{search}%"),
                DocumentDefinition.name_en.ilike(f"%{search}%"),
                DocumentDefinition.id.in_(alias_ids),
            )
        )
    for key in ("family_code", "catalog_lifecycle_status", "source_review_status"):
        if filters.get(key):
            query = query.filter(
                getattr(DocumentDefinition, key) == filters[key].upper()
            )
    if filters.get("is_active") in {"true", "false"}:
        query = query.filter(
            DocumentDefinition.is_active.is_(filters["is_active"] == "true")
        )
    relation_filters = (
        ("mode", DocumentDefinitionMode, "mode_code"),
        ("stage", DocumentDefinitionStage, "stage_code"),
        ("business_scope", DocumentDefinitionBusinessScope, "scope_code"),
        ("jurisdiction", DocumentDefinitionJurisdiction, "applicability_key"),
    )
    for key, model, column in relation_filters:
        if filters.get(key):
            ids = db.session.query(model.document_definition_id).filter(
                getattr(model, column) == filters[key].upper()
            )
            query = query.filter(DocumentDefinition.id.in_(ids))
    definitions = (
        query.order_by(DocumentDefinition.sort_order, DocumentDefinition.code)
        .limit(200)
        .all()
    )
    definition_ids = [row.id for row in definitions]
    model_map = {
        "aliases": DocumentDefinitionAlias,
        "jurisdictions": DocumentDefinitionJurisdiction,
        "modes": DocumentDefinitionMode,
        "stages": DocumentDefinitionStage,
        "scopes": DocumentDefinitionBusinessScope,
        "sources": DocumentDefinitionProvenance,
    }
    related: dict[str, dict[int, list[Any]]] = {}
    for name, model in model_map.items():
        grouped: dict[int, list[Any]] = {}
        for item in (
            model.query.filter(model.document_definition_id.in_(definition_ids))
            .order_by(model.id)
            .all()
            if definition_ids
            else []
        ):
            grouped.setdefault(item.document_definition_id, []).append(item)
        related[name] = grouped
    country_ids = {
        item.country_id
        for items in related["jurisdictions"].values()
        for item in items
        if item.country_id
    }
    countries = (
        {
            item.id: item
            for item in Country.query.filter(Country.id.in_(country_ids)).all()
        }
        if country_ids
        else {}
    )
    return [serialize(row, related, countries) for row in definitions]


def _replace_simple(
    row, model, code_field: str, values: list[str], allowed: frozenset[str]
) -> None:
    normalized = {str(value).strip().upper() for value in values}
    if not normalized.issubset(allowed):
        raise CatalogError(f"Invalid {code_field}")
    model.query.filter_by(document_definition_id=row.id).delete(
        synchronize_session=False
    )
    for value in sorted(normalized):
        db.session.add(model(document_definition_id=row.id, **{code_field: value}))


def update_metadata(
    row: DocumentDefinition,
    payload: dict[str, Any],
    actor_id: int,
    idempotency_key: str,
) -> dict[str, Any]:
    if not idempotency_key:
        raise CatalogError("Idempotency-Key is required", 400)
    replay = _check_idempotency(row, payload, idempotency_key)
    if replay is not None:
        return replay
    _require_revision(row, payload)
    previous_revision, previous_lifecycle = row.revision, row.catalog_lifecycle_status
    for field in (
        "name_fa",
        "name_en",
        "description_fa",
        "description_en",
        "reference_number_label_fa",
        "reference_number_label_en",
    ):
        if field in payload:
            setattr(row, field, str(payload[field]).strip() or None)
    if "family_code" in payload:
        family = str(payload["family_code"]).upper() if payload["family_code"] else None
        if family and family not in DOCUMENT_FAMILIES:
            raise CatalogError("Invalid family_code")
        row.family_code = family
    for field in ("expiry_applicable", "organization_overridable"):
        if field in payload:
            if payload[field] is not None and not isinstance(payload[field], bool):
                raise CatalogError(f"{field} must be boolean")
            setattr(row, field, payload[field])
    if "source_review_status" in payload:
        value = str(payload["source_review_status"]).upper()
        if value not in DOCUMENT_SOURCE_REVIEW_STATUSES:
            raise CatalogError("Invalid source_review_status")
        if row.catalog_lifecycle_status == "ACTIVE" and value not in {
            "VERIFIED",
            "SOURCE_CONFIRMED",
        }:
            raise CatalogError(
                "Deprecate an active definition before reducing source confidence", 409
            )
        row.source_review_status = value
    if "aliases" in payload:
        DocumentDefinitionAlias.query.filter_by(document_definition_id=row.id).delete(
            synchronize_session=False
        )
        for item in payload["aliases"]:
            display = str(item.get("display_value", "")).strip()
            normalized = normalize_alias(display)
            kind = str(item.get("alias_kind", "COMMON_NAME")).upper()
            if not display or kind not in DOCUMENT_ALIAS_KINDS:
                raise CatalogError("Invalid alias")
            code_owner = DocumentDefinition.query.filter(
                DocumentDefinition.code == normalized, DocumentDefinition.id != row.id
            ).first()
            alias_owner = DocumentDefinitionAlias.query.filter(
                DocumentDefinitionAlias.normalized_value == normalized,
                DocumentDefinitionAlias.document_definition_id != row.id,
            ).first()
            if code_owner or alias_owner:
                raise CatalogError("Alias is ambiguous", 409)
            db.session.add(
                DocumentDefinitionAlias(
                    document_definition_id=row.id,
                    locale=item.get("locale"),
                    display_value=display,
                    normalized_value=normalized,
                    alias_kind=kind,
                    is_active=bool(item.get("is_active", True)),
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
    if "jurisdictions" in payload:
        DocumentDefinitionJurisdiction.query.filter_by(
            document_definition_id=row.id
        ).delete(synchronize_session=False)
        for item in payload["jurisdictions"]:
            kind = str(item.get("kind", "")).upper()
            country = None
            if kind == "COUNTRY":
                country = Country.query.filter_by(
                    code=str(item.get("country_code", "")).upper()
                ).one_or_none()
                if not country:
                    raise CatalogError("Unknown country_code")
                key = f"COUNTRY:{country.code}"
            elif kind in {"GLOBAL", "INTERNATIONAL"}:
                key = kind
            else:
                raise CatalogError("Invalid jurisdiction kind")
            db.session.add(
                DocumentDefinitionJurisdiction(
                    document_definition_id=row.id,
                    applicability_kind=kind,
                    applicability_key=key,
                    country_id=country.id if country else None,
                )
            )
    if "modes" in payload:
        _replace_simple(
            row,
            DocumentDefinitionMode,
            "mode_code",
            payload["modes"],
            DOCUMENT_MODE_CODES,
        )
    if "stages" in payload:
        _replace_simple(
            row,
            DocumentDefinitionStage,
            "stage_code",
            payload["stages"],
            DOCUMENT_STAGE_CODES,
        )
    if "business_scopes" in payload:
        _replace_simple(
            row,
            DocumentDefinitionBusinessScope,
            "scope_code",
            payload["business_scopes"],
            DOCUMENT_BUSINESS_SCOPE_CODES,
        )
    if "provenance" in payload:
        DocumentDefinitionProvenance.query.filter_by(
            document_definition_id=row.id
        ).delete(synchronize_session=False)
        for item in payload["provenance"]:
            review = str(
                item.get("review_status", "SOURCE_CONFIRMATION_REQUIRED")
            ).upper()
            if review not in DOCUMENT_SOURCE_REVIEW_STATUSES:
                raise CatalogError("Invalid provenance review_status")
            authority_code = str(item.get("source_authority_code", "")).strip().upper()
            authority_name = str(item.get("source_authority_name", "")).strip()
            title = str(item.get("source_title", "")).strip()
            if not authority_code or not authority_name or not title:
                raise CatalogError("Provenance authority and title are required")
            source_date = (
                date.fromisoformat(item["source_date"])
                if item.get("source_date")
                else None
            )
            db.session.add(
                DocumentDefinitionProvenance(
                    document_definition_id=row.id,
                    source_authority_code=authority_code,
                    source_authority_name=authority_name,
                    source_title=title,
                    source_reference=item.get("source_reference"),
                    source_version=item.get("source_version"),
                    source_date=source_date,
                    jurisdiction_key=item.get("jurisdiction_key"),
                    review_status=review,
                    reviewed_by=actor_id,
                    reviewed_at=datetime.now(timezone.utc),
                    notes=item.get("notes"),
                )
            )
    row.revision += 1
    row.updated_by = actor_id
    _audit(
        row,
        actor_id,
        "METADATA_UPDATED",
        previous_revision=previous_revision,
        previous_lifecycle=previous_lifecycle,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    db.session.commit()
    return serialize(row)


TRANSITIONS = {
    "DRAFT": {"REVIEWED"},
    "REVIEWED": {"DRAFT", "SOURCE_CONFIRMED"},
    "SOURCE_CONFIRMED": {"REVIEWED", "ACTIVE"},
    "ACTIVE": {"DEPRECATED"},
    "DEPRECATED": set(),
}


def transition(
    row: DocumentDefinition,
    payload: dict[str, Any],
    actor_id: int,
    idempotency_key: str,
) -> dict[str, Any]:
    if not idempotency_key:
        raise CatalogError("Idempotency-Key is required", 400)
    replay = _check_idempotency(row, payload, idempotency_key)
    if replay is not None:
        return replay
    _require_revision(row, payload)
    target = str(payload.get("target_status", "")).upper()
    if (
        target not in DOCUMENT_CATALOG_LIFECYCLES
        or target not in TRANSITIONS[row.catalog_lifecycle_status]
    ):
        raise CatalogError("Illegal catalog lifecycle transition", 409)
    if target in {"SOURCE_CONFIRMED", "ACTIVE"}:
        if row.source_review_status not in {"VERIFIED", "SOURCE_CONFIRMED"}:
            raise CatalogError("Confirmed source review is required", 409)
        sources = DocumentDefinitionProvenance.query.filter_by(
            document_definition_id=row.id
        ).all()
        confirmed_sources = [
            item
            for item in sources
            if item.review_status in {"VERIFIED", "SOURCE_CONFIRMED"}
        ]
        if not confirmed_sources:
            raise CatalogError("Confirmed provenance is required", 409)
    if target == "ACTIVE":
        if not row.name_fa or not row.name_en or not row.family_code:
            raise CatalogError("Bilingual names and family are required", 409)
        jurisdictions = DocumentDefinitionJurisdiction.query.filter_by(
            document_definition_id=row.id
        ).all()
        if not jurisdictions:
            raise CatalogError("Jurisdiction classification is required", 409)
        covered = {item.jurisdiction_key for item in confirmed_sources}
        if not all(
            item.applicability_key in covered or "GLOBAL" in covered
            for item in jurisdictions
        ):
            raise CatalogError(
                "Confirmed provenance is required for every jurisdiction", 409
            )
        if (
            row.organization_overridable is False
            and OrganizationDocumentRequirement.query.filter_by(
                document_definition_id=row.id
            ).first()
        ):
            raise CatalogError(
                "Existing organization policy conflicts must be resolved before activation",
                409,
            )
        row.is_active = True
    elif target == "DEPRECATED":
        row.is_active = False
    previous_revision, previous_lifecycle = row.revision, row.catalog_lifecycle_status
    row.catalog_lifecycle_status = target
    row.revision += 1
    row.updated_by = actor_id
    _audit(
        row,
        actor_id,
        "LIFECYCLE_TRANSITION",
        previous_revision=previous_revision,
        previous_lifecycle=previous_lifecycle,
        payload=payload,
        idempotency_key=idempotency_key,
        approval_reference=str(payload.get("approval_reference", "")).strip() or None,
    )
    db.session.commit()
    return serialize(row)
