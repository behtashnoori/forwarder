"""Document definitions, case snapshots, validation, versioning and audit."""
from __future__ import annotations

import json
import re
import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.extensions import db
from backend.models import CaseDocumentFile, CaseDocumentRequirement, DocumentAuditEvent, DocumentDefinition, ShipmentRequest
from backend.services.document_storage_service import DocumentStorageError, PrivateDocumentStorage

FORMAT_CATALOG = {
    "jpeg": ({"jpg", "jpeg"}, {"image/jpeg"}),
    "png": ({"png"}, {"image/png"}),
    "webp": ({"webp"}, {"image/webp"}),
    "pdf": ({"pdf"}, {"application/pdf"}),
    "docx": ({"docx"}, {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
    "xlsx": ({"xlsx"}, {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
}
SCOPES = {"all", "domestic", "international"}
CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class DocumentError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def audit(event_type: str, actor_id: int | None, *, case_id=None, definition_id=None, file_id=None, details=None):
    db.session.add(DocumentAuditEvent(
        event_type=event_type, actor_id=actor_id, shipment_request_id=case_id,
        definition_id=definition_id, document_file_id=file_id,
        details=_json(details) if details else None,
    ))


def validate_definition(payload: dict[str, Any], existing: DocumentDefinition | None = None) -> dict[str, Any]:
    code = str(payload.get("code", existing.code if existing else "")).strip().lower()
    if existing and code != existing.code:
        raise DocumentError("کد داخلی پس از ایجاد قابل تغییر نیست")
    if not CODE_RE.fullmatch(code):
        raise DocumentError("کد داخلی باید با حرف انگلیسی آغاز شود و فقط شامل حروف کوچک، عدد و زیرخط باشد")
    title = str(payload.get("title", existing.title if existing else "")).strip()
    if not title:
        raise DocumentError("عنوان الزامی است")
    formats = payload.get("allowed_formats", json.loads(existing.allowed_formats) if existing else [])
    if not isinstance(formats, list) or not formats or any(item not in FORMAT_CATALOG for item in formats):
        raise DocumentError("فرمت فایل نامعتبر است")
    size = int(payload.get("max_file_size_bytes", existing.max_file_size_bytes if existing else 0))
    count = int(payload.get("max_active_file_count", existing.max_active_file_count if existing else 0))
    if size <= 0 or size > 100 * 1024 * 1024:
        raise DocumentError("حداکثر حجم باید بین ۱ بایت و ۱۰۰ مگابایت باشد")
    if count <= 0 or count > 100:
        raise DocumentError("حداکثر تعداد فایل باید بین ۱ و ۱۰۰ باشد")
    scope = payload.get("applicability_scope", existing.applicability_scope if existing else "all")
    if scope not in SCOPES:
        raise DocumentError("دامنه کاربرد نامعتبر است")
    return {
        "code": code, "title": title, "description": str(payload.get("description", existing.description if existing else "")).strip() or None,
        "is_required": bool(payload.get("is_required", existing.is_required if existing else False)),
        "allowed_formats": _json(sorted(set(formats))), "max_file_size_bytes": size,
        "max_active_file_count": count, "sort_order": int(payload.get("sort_order", existing.sort_order if existing else 0)),
        "applicability_scope": scope,
    }


def serialize_definition(row: DocumentDefinition) -> dict[str, Any]:
    return {
        "id": row.id, "code": row.code, "title": row.title, "description": row.description,
        "is_required": row.is_required, "allowed_formats": json.loads(row.allowed_formats),
        "max_file_size_bytes": row.max_file_size_bytes, "max_active_file_count": row.max_active_file_count,
        "sort_order": row.sort_order, "is_active": row.is_active,
        "applicability_scope": row.applicability_scope, "revision": row.revision,
        "usage_count": CaseDocumentRequirement.query.filter_by(source_definition_id=row.id).count(),
        "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat(),
    }


def initialize_requirements(case: ShipmentRequest, actor_id: int | None) -> int:
    definitions = DocumentDefinition.query.filter(
        DocumentDefinition.is_active.is_(True),
        DocumentDefinition.applicability_scope.in_(["all", case.shipping_type]),
    ).order_by(DocumentDefinition.sort_order, DocumentDefinition.id).all()
    created = 0
    for definition in definitions:
        # Once a definition has been snapshotted for a case, later definition
        # revisions are intentionally not applied by this idempotent initializer.
        exists = CaseDocumentRequirement.query.filter_by(
            shipment_request_id=case.id, source_definition_id=definition.id,
        ).first()
        if exists:
            continue
        db.session.add(CaseDocumentRequirement(
            shipment_request_id=case.id, source_definition_id=definition.id,
            source_definition_code=definition.code, source_definition_revision=definition.revision,
            title=definition.title, description=definition.description, is_required=definition.is_required,
            allowed_formats=definition.allowed_formats, max_file_size_bytes=definition.max_file_size_bytes,
            max_active_file_count=definition.max_active_file_count, sort_order=definition.sort_order,
            applied_by=actor_id,
        ))
        created += 1
    if created:
        audit("case_requirement_snapshot_initialized", actor_id, case_id=case.id, details={"created_count": created})
    return created


def detect_format(data: bytes) -> tuple[str, str] | None:
    if len(data) >= 4 and data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"): return "jpeg", "image/jpeg"
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n") and b"IHDR" in data[:32] and data.endswith(b"IEND\xaeB`\x82"): return "png", "image/png"
    if len(data) >= 16 and data.startswith(b"RIFF") and data[8:12] == b"WEBP" and int.from_bytes(data[4:8], "little") + 8 <= len(data): return "webp", "image/webp"
    if len(data) >= 12 and data.startswith(b"%PDF-") and b"%%EOF" in data[-1024:]: return "pdf", "application/pdf"
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as package:
                infos = package.infolist()
                if len(infos) > 10_000 or any(i.file_size > 100 * 1024 * 1024 for i in infos): return None
                names = {i.filename.replace("\\", "/") for i in infos}
                if "[Content_Types].xml" not in names or "_rels/.rels" not in names: return None
                content_types = package.read("[Content_Types].xml")
                if len(content_types) > 2 * 1024 * 1024: return None
                if "word/document.xml" in names and b"wordprocessingml.document.main+xml" in content_types:
                    return "docx", next(iter(FORMAT_CATALOG["docx"][1]))
                if "xl/workbook.xml" in names and b"spreadsheetml.sheet.main+xml" in content_types:
                    return "xlsx", next(iter(FORMAT_CATALOG["xlsx"][1]))
        except (OSError, KeyError, RuntimeError, zipfile.BadZipFile):
            return None
    return None


def _safe_original(name: str) -> tuple[str, str]:
    normalized = secure_filename(Path(name or "").name)
    parts = normalized.lower().split(".")
    if len(parts) != 2 or not parts[0] or parts[1] not in {e for v in FORMAT_CATALOG.values() for e in v[0]}:
        raise DocumentError("نام فایل یا پسوند آن امن نیست")
    return normalized[:255], parts[1]


def upload(case: ShipmentRequest, actor_id: int, upload_file: FileStorage, *, requirement=None, miscellaneous=False, custom_title=None, description=None, replacement=None):
    if miscellaneous and not str(custom_title or "").strip():
        raise DocumentError("عنوان سند متفرقه الزامی است")
    if not miscellaneous and (not requirement or requirement.shipment_request_id != case.id):
        raise DocumentError("نیازمندی سند معتبر نیست", 404)
    original, extension = _safe_original(upload_file.filename or "")
    maximum = 25 * 1024 * 1024 if miscellaneous else requirement.max_file_size_bytes
    data = upload_file.stream.read(maximum + 1)
    if len(data) > maximum:
        raise DocumentError("File is larger than the configured limit")
    detected = detect_format(data)
    if not detected:
        raise DocumentError("نوع محتوای فایل پشتیبانی نمی‌شود")
    format_id, mime = detected
    if extension not in FORMAT_CATALOG[format_id][0]:
        raise DocumentError("پسوند فایل با محتوای آن مطابقت ندارد")
    allowed = list(FORMAT_CATALOG) if miscellaneous else json.loads(requirement.allowed_formats)
    if format_id not in allowed:
        raise DocumentError("این فرمت برای سند انتخاب‌شده مجاز نیست")
    if requirement is not None:
        requirement = db.session.query(CaseDocumentRequirement).filter_by(
            id=requirement.id, shipment_request_id=case.id,
        ).with_for_update().one_or_none()
        if requirement is None:
            raise DocumentError("Document requirement was not found", 404)
    query = CaseDocumentFile.query.filter_by(shipment_request_id=case.id, status="active")
    if miscellaneous:
        active_count = query.filter_by(is_miscellaneous=True).count()
        version = 1
    else:
        active_count = query.filter_by(case_requirement_id=requirement.id).count()
        version = (db.session.query(func.max(CaseDocumentFile.version_number)).filter_by(case_requirement_id=requirement.id).scalar() or 0) + 1
        if replacement is None and active_count >= requirement.max_active_file_count:
            raise DocumentError("حداکثر تعداد فایل فعال این سند تکمیل شده است")
    storage = PrivateDocumentStorage()
    key = None
    try:
        key, size, digest = storage.write(case.id, extension, io.BytesIO(data), maximum)
        title = str(custom_title).strip() if miscellaneous else requirement.title
        safe_download = secure_filename(f"{title}-{case.tracking_code or case.id}-v{version}.{extension}") or f"document-{case.id}-v{version}.{extension}"
        row = CaseDocumentFile(
            shipment_request_id=case.id, case_requirement_id=requirement.id if requirement else None,
            is_miscellaneous=miscellaneous, custom_title=str(custom_title).strip() if miscellaneous else None,
            description=str(description or "").strip() or None, original_filename=original,
            safe_download_filename=safe_download, storage_key=key, canonical_extension=extension,
            detected_mime_type=mime, file_size_bytes=size, sha256_hash=digest, version_number=version,
            uploaded_by=actor_id,
        )
        db.session.add(row)
        db.session.flush()
        if replacement is not None:
            previous = db.session.query(CaseDocumentFile).filter_by(
                id=replacement.id, case_requirement_id=requirement.id, status="active",
            ).with_for_update().one_or_none()
            if previous is None:
                raise DocumentError("Active version is no longer available for replacement", 409)
            previous.status = "superseded"
            previous.superseded_at = datetime.utcnow()
            previous.superseded_by = row.id
        audit("file_uploaded", actor_id, case_id=case.id, file_id=row.id, details={"format": format_id, "size": size, "version": version})
        if replacement is not None:
            audit("file_version_superseded", actor_id, case_id=case.id, file_id=previous.id, details={"replacement_id": row.id})
        db.session.commit()
        return row
    except DocumentStorageError as exc:
        db.session.rollback()
        storage.remove_after_failed_transaction(key)
        raise DocumentError(str(exc)) from exc
    except DocumentError:
        db.session.rollback()
        storage.remove_after_failed_transaction(key)
        raise
    except IntegrityError as exc:
        db.session.rollback()
        storage.remove_after_failed_transaction(key)
        raise DocumentError("A concurrent document change conflicted; retry the request", 409) from exc
    except Exception:
        db.session.rollback()
        storage.remove_after_failed_transaction(key)
        raise


def serialize_file(row: CaseDocumentFile) -> dict[str, Any]:
    return {
        "id": row.id, "requirement_id": row.case_requirement_id, "is_miscellaneous": row.is_miscellaneous,
        "custom_title": row.custom_title, "description": row.description, "original_filename": row.original_filename,
        "canonical_extension": row.canonical_extension, "detected_mime_type": row.detected_mime_type,
        "file_size_bytes": row.file_size_bytes, "sha256_hash": row.sha256_hash,
        "version_number": row.version_number, "status": row.status,
        "uploaded_at": row.uploaded_at.isoformat(),
    }


def case_payload(case: ShipmentRequest) -> dict[str, Any]:
    requirements = CaseDocumentRequirement.query.filter_by(shipment_request_id=case.id).order_by(CaseDocumentRequirement.sort_order).all()
    files = CaseDocumentFile.query.filter_by(shipment_request_id=case.id).order_by(CaseDocumentFile.uploaded_at.desc()).all()
    result = []
    for requirement in requirements:
        active = [serialize_file(f) for f in files if f.case_requirement_id == requirement.id and f.status == "active"]
        versions = [serialize_file(f) for f in files if f.case_requirement_id == requirement.id]
        result.append({
            "id": requirement.id, "code": requirement.source_definition_code, "title": requirement.title,
            "description": requirement.description, "is_required": requirement.is_required,
            "allowed_formats": json.loads(requirement.allowed_formats), "max_file_size_bytes": requirement.max_file_size_bytes,
            "max_active_file_count": requirement.max_active_file_count, "complete": bool(active),
            "active_files": active, "versions": versions,
        })
    misc = [serialize_file(f) for f in files if f.is_miscellaneous and f.status == "active"]
    return {
        "requirements": result, "miscellaneous": misc,
        "summary": {
            "total_requirements": len(result), "required_requirements": sum(r["is_required"] for r in result),
            "uploaded_requirements": sum(r["complete"] for r in result),
            "missing_required_requirements": sum(r["is_required"] and not r["complete"] for r in result),
            "miscellaneous_file_count": len(misc),
        },
    }
