"""Tenant-fenced services for ADR-039 external operational references."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sqlalchemy import select

from backend.extensions import db
from backend.external_reference_models import (
    ExecutionUnitExternalReference,
    ExternalReferenceType,
    OperationalShipmentExternalReference,
    TYPE_CODES,
)
from backend.models import CaseDocumentFile, CaseDocumentRequirement
from backend.operational_models import (
    ExecutionUnit,
    OperationalAudit,
    OperationalIdempotency,
    OperationalShipment,
    Project,
    utcnow,
)
from backend.services.operational_service import (
    OperationalError,
    organization_for_user,
    require_permission,
)

TYPE_DOCUMENT_CODES = {
    "BILL_OF_LADING_NUMBER": {
        "BILL_OF_LADING",
        "HOUSE_BILL_OF_LADING",
        "MASTER_BILL_OF_LADING",
    },
    "AIR_WAYBILL_NUMBER": {"AIR_WAYBILL", "HOUSE_AIR_WAYBILL", "MASTER_AIR_WAYBILL"},
    "CMR_NUMBER": {"CMR_CONSIGNMENT_NOTE"},
}


def normalize(value: Any) -> tuple[str, str]:
    raw = str(value or "").strip()
    if not raw or len(raw) > 255 or any(ord(char) < 32 for char in raw):
        raise OperationalError(
            "INVALID_REFERENCE_VALUE",
            "Reference value is required and must not exceed 255 characters.",
        )
    normalized = re.sub(r"\s+", " ", raw).upper()
    return raw, normalized


def _hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _type(code: str, owner_kind: str) -> ExternalReferenceType:
    if code not in TYPE_CODES:
        raise OperationalError(
            "REFERENCE_TYPE_NOT_FOUND", "Reference type is unavailable.", 404
        )
    row = db.session.scalar(
        select(ExternalReferenceType).where(
            ExternalReferenceType.code == code,
            ExternalReferenceType.lifecycle_status == "ACTIVE",
        )
    )
    allowed = row and (
        row.allows_operational_shipment
        if owner_kind == "shipment"
        else row.allows_execution_unit
    )
    if not allowed:
        raise OperationalError(
            "REFERENCE_TYPE_NOT_APPLICABLE",
            "Reference type is unavailable for this owner.",
            422,
        )
    return row


def scoped_shipment(
    public_id: str, user: dict, *, manage: bool = False
) -> OperationalShipment:
    require_permission(
        user, "operational_shipment.create" if manage else "operational_shipment.read"
    )
    org = organization_for_user(int(user["id"]))
    row = db.session.scalar(
        select(OperationalShipment).where(
            OperationalShipment.public_id == public_id,
            OperationalShipment.organization_id == org,
        )
    )
    if row is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
    return row


def scoped_unit(
    public_id: str, user: dict, *, manage: bool = False
) -> tuple[ExecutionUnit, int]:
    require_permission(
        user, "execution_unit.manage" if manage else "execution_unit.read"
    )
    org = organization_for_user(int(user["id"]))
    row = db.session.scalar(
        select(ExecutionUnit)
        .join(Project, Project.id == ExecutionUnit.project_id)
        .where(ExecutionUnit.public_id == public_id, Project.organization_id == org)
    )
    if row is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
    return row, org


def _evidence(
    payload: dict, shipment: OperationalShipment, type_row: ExternalReferenceType
) -> tuple[int | None, int | None]:
    public_id = payload.get("evidence_document_public_id")
    if not public_id:
        return None, None
    if shipment.shipment_request_id is None:
        raise OperationalError(
            "EVIDENCE_LINEAGE_MISMATCH", "Evidence is unavailable for this owner.", 422
        )
    file = db.session.scalar(
        select(CaseDocumentFile).where(
            CaseDocumentFile.public_id == str(public_id),
            CaseDocumentFile.operational_organization_id == shipment.organization_id,
            CaseDocumentFile.shipment_request_id == shipment.shipment_request_id,
        )
    )
    if file is None or file.case_requirement_id is None:
        raise OperationalError("EVIDENCE_NOT_FOUND", "Evidence is unavailable.", 404)
    definition_code = db.session.scalar(
        select(CaseDocumentRequirement.source_definition_code).where(
            CaseDocumentRequirement.id == file.case_requirement_id
        )
    )
    if definition_code not in TYPE_DOCUMENT_CODES[type_row.code]:
        raise OperationalError(
            "EVIDENCE_TYPE_MISMATCH", "Evidence document type is incompatible.", 422
        )
    expected = payload.get("evidence_version")
    if expected is not None and expected != file.version_number:
        raise OperationalError(
            "EVIDENCE_VERSION_MISMATCH",
            "Evidence version does not match the exact file version.",
            409,
        )
    return file.id, file.version_number


def _owner_config(owner_kind: str, owner: Any):
    if owner_kind == "shipment":
        return (
            OperationalShipmentExternalReference,
            "operational_shipment_id",
            owner.id,
            owner,
        )
    shipment = (
        db.session.get(OperationalShipment, owner.operational_shipment_id)
        if owner.operational_shipment_id
        else None
    )
    return ExecutionUnitExternalReference, "execution_unit_id", owner.id, shipment


def _check_unique(
    type_row: ExternalReferenceType,
    model,
    owner_field: str,
    owner_id: int,
    org: int,
    normalized: str,
    issuer: str | None,
):
    scope = type_row.uniqueness_scope
    if scope == "NONE":
        return
    if scope == "OWNER":
        exists = db.session.scalar(
            select(model.id)
            .where(
                model.external_reference_type_id == type_row.id,
                model.normalized_value == normalized,
                model.lifecycle_status == "ACTIVE",
                getattr(model, owner_field) == owner_id,
            )
            .limit(1)
        )
        if exists is not None:
            raise OperationalError(
                "REFERENCE_ALREADY_EXISTS",
                "An active reference already exists in this uniqueness scope.",
                409,
            )
        return
    if scope == "ISSUER":
        if not issuer:
            raise OperationalError(
                "ISSUER_REQUIRED", "issuer_key is required for issuer uniqueness."
            )
    for candidate in (
        OperationalShipmentExternalReference,
        ExecutionUnitExternalReference,
    ):
        predicates = [
            candidate.organization_id == org,
            candidate.external_reference_type_id == type_row.id,
            candidate.normalized_value == normalized,
            candidate.lifecycle_status == "ACTIVE",
        ]
        if scope == "ISSUER":
            predicates.append(candidate.issuer_key == issuer)
        if (
            db.session.scalar(select(candidate.id).where(*predicates).limit(1))
            is not None
        ):
            raise OperationalError(
                "REFERENCE_ALREADY_EXISTS",
                "An active reference already exists in this uniqueness scope.",
                409,
            )


def serialize(row) -> dict:
    return {
        "public_id": row.public_id,
        "type": row.reference_type.code,
        "display_value": row.raw_value,
        "lifecycle_status": row.lifecycle_status,
        "issuer_key": row.issuer_key,
        "source_system": row.source_system,
        "issued_at": row.issued_at.isoformat().replace("+00:00", "Z")
        if row.issued_at
        else None,
        "evidence": {
            "document_public_id": db.session.get(
                CaseDocumentFile, row.evidence_document_file_id
            ).public_id,
            "version": row.evidence_version,
        }
        if row.evidence_document_file_id
        else None,
        "revision": row.revision,
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
    }


def create(
    owner_kind: str, owner, org: int, payload: dict, user: dict, key: str
) -> tuple[Any, bool]:
    if not key or len(key) > 100:
        raise OperationalError(
            "IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key is required."
        )
    type_row = _type(str(payload.get("type", "")), owner_kind)
    db.session.execute(
        select(ExternalReferenceType.id)
        .where(ExternalReferenceType.id == type_row.id)
        .with_for_update()
    )
    raw, normalized = normalize(payload.get("value"))
    model, owner_field, owner_id, shipment = _owner_config(owner_kind, owner)
    if shipment is None and payload.get("evidence_document_public_id"):
        raise OperationalError(
            "EVIDENCE_LINEAGE_MISMATCH", "Evidence is unavailable for this owner."
        )
    request_hash = _hash(payload)
    operation = f"external_reference.{owner_kind}.create"
    replay = db.session.scalar(
        select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == org,
            OperationalIdempotency.operation == operation,
            OperationalIdempotency.resource_type == owner_kind,
            OperationalIdempotency.command_resource_id == owner_id,
            OperationalIdempotency.idempotency_key == key,
        )
    )
    if replay:
        if replay.request_hash != request_hash:
            raise OperationalError(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key was reused with another payload.",
                409,
            )
        return db.session.get(model, replay.result_resource_id), False
    issuer = str(payload.get("issuer_key") or "").strip() or None
    _check_unique(type_row, model, owner_field, owner_id, org, normalized, issuer)
    evidence_id, evidence_version = (
        _evidence(payload, shipment, type_row) if shipment else (None, None)
    )
    row = model(
        organization_id=org,
        external_reference_type_id=type_row.id,
        raw_value=raw,
        normalized_value=normalized,
        issuer_key=issuer,
        source_system=str(payload.get("source_system") or "").strip() or None,
        evidence_document_file_id=evidence_id,
        evidence_version=evidence_version,
        created_by_user_id=int(user["id"]),
        updated_by_user_id=int(user["id"]),
        **{owner_field: owner_id},
    )
    db.session.add(row)
    db.session.flush()
    db.session.add(
        OperationalIdempotency(
            organization_id=org,
            operation=operation,
            resource_type=owner_kind,
            command_resource_id=owner_id,
            idempotency_key=key,
            request_hash=request_hash,
            result_resource_id=row.id,
        )
    )
    db.session.add(
        OperationalAudit(
            organization_id=org,
            actor_user_id=int(user["id"]),
            action="external_reference.created",
            entity_type=f"{owner_kind}_external_reference",
            entity_id=row.id,
            metadata_json={"type": type_row.code, "owner_id": owner_id},
        )
    )
    db.session.commit()
    return row, True


def list_for_owner(
    owner_kind: str, owner_id: int, *, active_only: bool = False
) -> list[dict]:
    model, field = (
        (OperationalShipmentExternalReference, "operational_shipment_id")
        if owner_kind == "shipment"
        else (ExecutionUnitExternalReference, "execution_unit_id")
    )
    query = select(model).where(getattr(model, field) == owner_id)
    if active_only:
        query = query.where(model.lifecycle_status == "ACTIVE")
    return [
        serialize(row)
        for row in db.session.scalars(
            query.order_by(model.created_at.desc(), model.id.desc())
        ).all()
    ]


def transition(
    owner_kind: str,
    owner_id: int,
    org: int,
    reference_public_id: str,
    payload: dict,
    user: dict,
    action: str,
    key: str,
):
    if not key or len(key) > 100:
        raise OperationalError(
            "IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key is required."
        )
    model, field = (
        (OperationalShipmentExternalReference, "operational_shipment_id")
        if owner_kind == "shipment"
        else (ExecutionUnitExternalReference, "execution_unit_id")
    )
    operation = f"external_reference.{owner_kind}.{action}"
    request_hash = _hash(payload)
    replay = db.session.scalar(
        select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == org,
            OperationalIdempotency.operation == operation,
            OperationalIdempotency.resource_type == owner_kind,
            OperationalIdempotency.command_resource_id == owner_id,
            OperationalIdempotency.idempotency_key == key,
        )
    )
    if replay:
        if replay.request_hash != request_hash:
            raise OperationalError(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key was reused with another payload.",
                409,
            )
        return db.session.get(model, replay.result_resource_id)
    old = db.session.scalar(
        select(model)
        .where(
            model.public_id == reference_public_id,
            model.organization_id == org,
            getattr(model, field) == owner_id,
        )
        .with_for_update()
    )
    if old is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
    if (
        old.lifecycle_status != "ACTIVE"
        or payload.get("expected_revision") != old.revision
    ):
        raise OperationalError(
            "VERSION_CONFLICT", "Reference is not active at the expected revision.", 409
        )
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise OperationalError("REASON_REQUIRED", "A reason is required.")
    if action == "cancel":
        old.lifecycle_status = "CANCELLED"
        old.reason = reason
        old.revision += 1
        old.updated_by_user_id = int(user["id"])
        old.updated_at = utcnow()
        result = old
    else:
        type_row = old.reference_type
        db.session.execute(
            select(ExternalReferenceType.id)
            .where(ExternalReferenceType.id == type_row.id)
            .with_for_update()
        )
        raw, normalized = normalize(payload.get("value"))
        issuer = str(payload.get("issuer_key") or old.issuer_key or "").strip() or None
        _check_unique(type_row, model, field, owner_id, org, normalized, issuer)
        values = dict(
            organization_id=org,
            external_reference_type_id=old.external_reference_type_id,
            raw_value=raw,
            normalized_value=normalized,
            issuer_key=issuer,
            source_system=str(
                payload.get("source_system") or old.source_system or ""
            ).strip()
            or None,
            supersedes_reference_id=old.id,
            evidence_document_file_id=old.evidence_document_file_id,
            evidence_version=old.evidence_version,
            reason=reason,
            created_by_user_id=int(user["id"]),
            updated_by_user_id=int(user["id"]),
            **{field: owner_id},
        )
        result = model(**values)
        db.session.add(result)
        db.session.flush()
        old.lifecycle_status = "SUPERSEDED"
        old.reason = reason
        old.revision += 1
        old.updated_by_user_id = int(user["id"])
    db.session.add(
        OperationalAudit(
            organization_id=org,
            actor_user_id=int(user["id"]),
            action=f"external_reference.{action}d",
            entity_type=f"{owner_kind}_external_reference",
            entity_id=result.id,
            metadata_json={
                "type": old.reference_type.code,
                "predecessor_id": old.id if action == "supersede" else None,
            },
        )
    )
    db.session.add(
        OperationalIdempotency(
            organization_id=org,
            operation=operation,
            resource_type=owner_kind,
            command_resource_id=owner_id,
            idempotency_key=key,
            request_hash=request_hash,
            result_resource_id=result.id,
        )
    )
    db.session.commit()
    return result


def search(args: dict, user: dict) -> dict:
    require_permission(user, "operational_shipment.read")
    org = organization_for_user(int(user["id"]))
    code = str(args.get("type") or "")
    type_row = _type(code, "shipment")
    mode = str(args.get("mode") or "exact").lower()
    _, term = normalize(args.get("value"))
    if mode == "prefix" and (type_row.search_policy != "PREFIX" or len(term) < 3):
        raise OperationalError(
            "PREFIX_SEARCH_NOT_ALLOWED", "Prefix search is unavailable."
        )
    if mode not in {"exact", "prefix"}:
        raise OperationalError("VALIDATION_FAILED", "mode must be exact or prefix.")
    limit = min(50, max(1, int(args.get("limit", 20))))
    rows = []
    for model, field, label in (
        (
            OperationalShipmentExternalReference,
            "operational_shipment_id",
            "OPERATIONAL_SHIPMENT",
        ),
        (ExecutionUnitExternalReference, "execution_unit_id", "EXECUTION_UNIT"),
    ):
        value_filter = (
            model.normalized_value.like(f"{term}%")
            if mode == "prefix"
            else model.normalized_value == term
        )
        query = (
            select(model)
            .where(
                model.organization_id == org,
                model.external_reference_type_id == type_row.id,
                model.lifecycle_status == "ACTIVE",
                value_filter,
            )
            .limit(limit)
        )
        for row in db.session.scalars(query).all():
            owner = db.session.get(
                OperationalShipment
                if label == "OPERATIONAL_SHIPMENT"
                else ExecutionUnit,
                getattr(row, field),
            )
            rows.append(
                {
                    "reference": serialize(row),
                    "owner_type": label,
                    "owner_public_id": owner.public_id,
                }
            )
    return {"data": rows[:limit], "meta": {"limit": limit, "mode": mode}}
