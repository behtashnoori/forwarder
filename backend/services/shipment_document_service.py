"""Owner-neutral shipment view over the existing CaseDocumentFile authority."""
from __future__ import annotations

import hashlib
import io
from datetime import datetime
from typing import Any
from werkzeug.datastructures import FileStorage
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.external_reference_models import OperationalShipmentExternalReference
from backend.mdpm_models import ArtifactAssociation, OperationalDocumentRequirement
from backend.models import CaseDocumentFile, CaseDocumentRequirement, ExpertUser
from backend.operational_models import OperationalAudit, OperationalIdempotency, OperationalShipment
from backend.services.case_document_service import DocumentError, FORMAT_CATALOG, _safe_original, detect_format
from backend.services.document_storage_service import PrivateDocumentStorage
from backend.services.assigned_work_authorization import authorize_document_management


def documents(shipment: OperationalShipment) -> list[dict]:
    predicates = [
        (CaseDocumentFile.owner_type == "SHIPMENT") & (CaseDocumentFile.operational_shipment_id == shipment.id)
    ]
    if shipment.shipment_request_id is not None:
        predicates.append(
            (CaseDocumentFile.owner_type == "REQUEST") &
            (CaseDocumentFile.shipment_request_id == shipment.shipment_request_id)
        )
    rows = db.session.scalars(select(CaseDocumentFile).where(or_(*predicates)).order_by(
        CaseDocumentFile.uploaded_at.desc(), CaseDocumentFile.id.desc()
    )).all()
    reference_rows = db.session.scalars(select(OperationalShipmentExternalReference).where(
        OperationalShipmentExternalReference.operational_shipment_id == shipment.id,
        OperationalShipmentExternalReference.organization_id == shipment.organization_id,
    )).all()
    reference_by_file = {}
    for ref in reference_rows:
        if ref.evidence_document_file_id:
            reference_by_file.setdefault(ref.evidence_document_file_id, []).append({
                "public_id": ref.public_id, "type": ref.reference_type.code,
                "display_value": ref.raw_value, "lifecycle_status": ref.lifecycle_status,
            })
    associations = db.session.scalars(select(ArtifactAssociation).join(
        OperationalDocumentRequirement, OperationalDocumentRequirement.id == ArtifactAssociation.requirement_id
    ).where(
        ArtifactAssociation.organization_id == shipment.organization_id,
        OperationalDocumentRequirement.operational_shipment_id == shipment.id,
    )).all()
    requirement_by_file = {}
    for association in associations:
        requirement = db.session.get(OperationalDocumentRequirement, association.requirement_id)
        requirement_by_file.setdefault(association.document_file_id, []).append({
            "public_id": requirement.public_id,
            "title": requirement.definition.name_fa or requirement.definition.title,
            "association_state": association.state,
        })
    result = []
    for row in rows:
        actor = db.session.get(ExpertUser, row.uploaded_by) if row.uploaded_by else None
        legacy_requirement = db.session.get(CaseDocumentRequirement, row.case_requirement_id) if row.case_requirement_id else None
        result.append({
            "public_id": row.public_id,
            "business_document_type": legacy_requirement.title if legacy_requirement else row.custom_title or "سند حمل",
            "filename": row.original_filename, "version": row.version_number,
            "recorded_at": row.uploaded_at.isoformat(),
            "actor": (actor.full_name or actor.username) if actor else None,
            "owner": row.owner_type, "lifecycle_state": row.status,
            "description": row.description, "references": reference_by_file.get(row.id, []),
            "requirements": requirement_by_file.get(row.id, []),
        })
    return result


def _actor_context(actor: dict[str, Any] | int) -> tuple[dict[str, Any], int]:
    if isinstance(actor, dict):
        return actor, int(actor["id"])
    actor_id = int(actor)
    return {"id": actor_id}, actor_id


def upload(shipment: OperationalShipment, actor: dict[str, Any] | int, file: FileStorage, title: str, description: str | None, key: str, replacement: CaseDocumentFile | None = None) -> CaseDocumentFile:
    actor_context, actor_id = _actor_context(actor)
    shipment = db.session.scalar(select(OperationalShipment).where(
        OperationalShipment.id == shipment.id
    ).with_for_update().execution_options(populate_existing=True))
    if shipment is None or not authorize_document_management(actor_context, shipment).allowed:
        raise DocumentError(
            "شما مجاز به مدیریت اسناد این محموله نیستید", 403,
            "DOCUMENT_MUTATION_FORBIDDEN",
        )
    title = str(title or "").strip()
    if not title:
        raise DocumentError("نوع یا عنوان تجاری سند الزامی است")
    if not key or len(key) > 100:
        raise DocumentError("شناسه امن تلاش بارگذاری الزامی است")
    original, extension = _safe_original(file.filename or "")
    data = file.stream.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        raise DocumentError("حجم فایل از سقف مجاز بیشتر است")
    detected = detect_format(data)
    if not detected:
        raise DocumentError("نوع محتوای فایل پشتیبانی نمی‌شود")
    format_id, mime = detected
    if extension not in FORMAT_CATALOG[format_id][0]:
        raise DocumentError("پسوند فایل با محتوای آن مطابقت ندارد")
    request_hash = hashlib.sha256((title + "\0" + (description or "") + "\0").encode() + data).hexdigest()
    replay = db.session.scalar(select(OperationalIdempotency).where(
        OperationalIdempotency.organization_id == shipment.organization_id,
        OperationalIdempotency.operation == "shipment_document.upload",
        OperationalIdempotency.resource_type == "shipment",
        OperationalIdempotency.command_resource_id == shipment.id,
        OperationalIdempotency.idempotency_key == key,
    ))
    if replay:
        if replay.request_hash != request_hash:
            raise DocumentError("این شناسه بارگذاری قبلاً برای فایل دیگری استفاده شده است", 409)
        return db.session.get(CaseDocumentFile, replay.result_resource_id)
    locked_replacement = None
    if replacement is not None:
        locked_replacement = db.session.scalar(select(CaseDocumentFile).where(
            CaseDocumentFile.id == replacement.id,
            CaseDocumentFile.owner_type == "SHIPMENT",
            CaseDocumentFile.operational_shipment_id == shipment.id,
            CaseDocumentFile.operational_organization_id == shipment.organization_id,
            CaseDocumentFile.status == "active",
        ).with_for_update().execution_options(populate_existing=True))
        if locked_replacement is None:
            raise DocumentError(
                "نسخه فعال انتخاب‌شده برای جایگزینی در دسترس نیست", 409,
                "REPLACEMENT_TARGET_CHANGED",
            )
    storage = PrivateDocumentStorage()
    storage_key = None
    try:
        storage_key, size, digest = storage.write(f"shipment-{shipment.id}", extension, io.BytesIO(data), 25 * 1024 * 1024)
        version = locked_replacement.version_number + 1 if locked_replacement is not None else 1
        row = CaseDocumentFile(owner_type="SHIPMENT", operational_shipment_id=shipment.id,
            shipment_request_id=shipment.shipment_request_id, operational_organization_id=shipment.organization_id,
            is_miscellaneous=True, custom_title=title, description=str(description or "").strip() or None,
            original_filename=original[:255], safe_download_filename=original[:255], storage_key=storage_key,
            canonical_extension=extension, detected_mime_type=mime, file_size_bytes=size,
            sha256_hash=digest, version_number=version, uploaded_by=actor_id)
        db.session.add(row); db.session.flush()
        if locked_replacement is not None:
            locked_replacement.status, locked_replacement.superseded_at, locked_replacement.superseded_by = "superseded", datetime.utcnow(), row.id
        db.session.add(OperationalIdempotency(organization_id=shipment.organization_id,
            operation="shipment_document.upload", resource_type="shipment", command_resource_id=shipment.id,
            idempotency_key=key, request_hash=request_hash, result_resource_id=row.id))
        db.session.add(OperationalAudit(organization_id=shipment.organization_id, actor_user_id=actor_id,
            action="shipment_document.uploaded", entity_type="CaseDocumentFile", entity_id=row.id,
            metadata_json={"shipment_id": shipment.id, "owner": "SHIPMENT", "version": version,
                           "supersedes_document_public_id": locked_replacement.public_id if locked_replacement else None}))
        db.session.commit()
        return row
    except IntegrityError as exc:
        db.session.rollback(); storage.remove_after_failed_transaction(storage_key)
        raise DocumentError("بارگذاری هم‌زمان تداخل داشت؛ دوباره تلاش کنید", 409) from exc
    except Exception:
        db.session.rollback(); storage.remove_after_failed_transaction(storage_key); raise


def remove(shipment: OperationalShipment, row: CaseDocumentFile, actor: dict[str, Any] | int, reason: str):
    actor_context, actor_id = _actor_context(actor)
    shipment = db.session.scalar(select(OperationalShipment).where(
        OperationalShipment.id == shipment.id
    ).with_for_update().execution_options(populate_existing=True))
    if shipment is None or not authorize_document_management(actor_context, shipment).allowed:
        raise DocumentError(
            "شما مجاز به مدیریت اسناد این محموله نیستید", 403,
            "DOCUMENT_MUTATION_FORBIDDEN",
        )
    row = db.session.scalar(select(CaseDocumentFile).where(
        CaseDocumentFile.id == row.id,
        CaseDocumentFile.owner_type == "SHIPMENT",
        CaseDocumentFile.operational_shipment_id == shipment.id,
        CaseDocumentFile.operational_organization_id == shipment.organization_id,
    ).with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise DocumentError("فایل یافت نشد", 404, "DOCUMENT_PARENT_NOT_FOUND")
    if row.status != "active":
        raise DocumentError("سند جاری در دسترس نیست", 409, "REPLACEMENT_TARGET_CHANGED")
    reason = str(reason or "").strip()
    if not reason:
        raise DocumentError("دلیل حذف الزامی است")
    row.status, row.deleted_at, row.deleted_by, row.deletion_reason = "deleted", datetime.utcnow(), actor_id, reason
    db.session.add(OperationalAudit(organization_id=shipment.organization_id, actor_user_id=actor_id,
        action="shipment_document.voided", entity_type="CaseDocumentFile", entity_id=row.id,
        metadata_json={"shipment_id": shipment.id, "reason": reason, "owner": row.owner_type}))
    db.session.commit()
