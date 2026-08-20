"""Authorized admin definition and expert case-document APIs."""
from __future__ import annotations

from datetime import datetime

from flask import Blueprint, g, jsonify, request, send_file
from sqlalchemy.exc import IntegrityError

from backend.auth import get_current_user
from backend.extensions import db
from backend.models import CaseDocumentFile, CaseDocumentRequirement, DocumentDefinition, ShipmentRequest
from backend.security import require_auth
from backend.services import case_document_service as service
from backend.services.document_storage_service import DocumentStorageError, PrivateDocumentStorage
from backend.services.expert_request_detail_service import can_access_request_detail
from backend.quarantine import QuarantinedResource, is_quarantined
from backend.services.admin_authorization_service import require_organization_admin_context, require_platform_admin
from backend.services import organization_document_policy_service as organization_policy
from backend.services import document_catalog_service as catalog_service

document_bp = Blueprint("case_documents", __name__)


def _current():
    return get_current_user()


def _case_or_error(case_id: int):
    case = db.session.get(ShipmentRequest, case_id)
    if not case or is_quarantined("ShipmentRequest", case_id):
        return None, (jsonify({"error": "پرونده یافت نشد"}), 404)
    if not can_access_request_detail(case, _current()):
        return None, (jsonify({"error": "شما به این پرونده دسترسی ندارید"}), 403)
    return case, None


@document_bp.get("/api/admin/document-definitions")
@require_organization_admin_context()
def definitions_list():
    rows = DocumentDefinition.query.order_by(DocumentDefinition.sort_order, DocumentDefinition.id).all()
    return jsonify({"items": [service.serialize_definition(row) for row in rows]})


@document_bp.post("/api/admin/document-definitions")
@require_platform_admin()
def definitions_create():
    actor = _current()
    try:
        values = service.validate_definition(request.get_json(silent=True) or {})
        row = DocumentDefinition(**values, created_by=actor["id"], updated_by=actor["id"])
        db.session.add(row)
        db.session.flush()
        service.audit("document_definition_created", actor["id"], definition_id=row.id)
        db.session.commit()
        return jsonify(service.serialize_definition(row)), 201
    except service.DocumentError as exc:
        db.session.rollback()
        return jsonify({"error": exc.message}), exc.status
    except Exception as exc:
        db.session.rollback()
        if "unique" in str(exc).lower():
            return jsonify({"error": "کد داخلی تکراری است"}), 409
        raise


@document_bp.get("/api/admin/document-definitions/<int:definition_id>")
@require_organization_admin_context()
def definitions_read(definition_id: int):
    row = db.session.get(DocumentDefinition, definition_id)
    return (jsonify(service.serialize_definition(row)), 200) if row else (jsonify({"error": "تعریف یافت نشد"}), 404)


@document_bp.patch("/api/admin/document-definitions/<int:definition_id>")
@require_platform_admin()
def definitions_update(definition_id: int):
    row = db.session.get(DocumentDefinition, definition_id)
    if not row:
        return jsonify({"error": "تعریف یافت نشد"}), 404
    actor = _current()
    try:
        old = service.serialize_definition(row)
        values = service.validate_definition(request.get_json(silent=True) or {}, row)
        for key, value in values.items():
            setattr(row, key, value)
        row.revision += 1
        row.updated_by = actor["id"]
        service.audit("document_definition_updated", actor["id"], definition_id=row.id, details={"old": old, "new_revision": row.revision})
        db.session.commit()
        return jsonify(service.serialize_definition(row))
    except service.DocumentError as exc:
        db.session.rollback()
        return jsonify({"error": exc.message}), exc.status


@document_bp.post("/api/admin/document-definitions/<int:definition_id>/activation")
@require_platform_admin()
def definitions_activation(definition_id: int):
    row = db.session.get(DocumentDefinition, definition_id)
    if not row:
        return jsonify({"error": "تعریف یافت نشد"}), 404
    actor = _current()
    active = bool((request.get_json(silent=True) or {}).get("is_active"))
    if active and row.catalog_lifecycle_status != "ACTIVE":
        return jsonify({"error": "Use the governed catalog lifecycle API to activate this definition"}), 409
    row.is_active = active
    row.updated_by = actor["id"]
    service.audit("document_definition_activated" if active else "document_definition_deactivated", actor["id"], definition_id=row.id)
    db.session.commit()
    return jsonify(service.serialize_definition(row))


@document_bp.get("/api/platform/document-catalog")
@require_platform_admin()
def document_catalog_list():
    filters = {key: value for key, value in request.args.items() if key in {
        "q", "family_code", "catalog_lifecycle_status", "source_review_status",
        "jurisdiction", "mode", "stage", "business_scope", "is_active",
    }}
    return jsonify({"items": catalog_service.list_catalog(filters)})


@document_bp.get("/api/platform/document-catalog/<definition_public_id>")
@require_platform_admin()
def document_catalog_detail(definition_public_id: str):
    row = DocumentDefinition.query.filter_by(public_id=definition_public_id).one_or_none()
    return (jsonify(catalog_service.serialize(row)), 200) if row else (jsonify({"error": "Definition not found"}), 404)


@document_bp.patch("/api/platform/document-catalog/<definition_public_id>")
@require_platform_admin()
def document_catalog_update(definition_public_id: str):
    row = DocumentDefinition.query.filter_by(public_id=definition_public_id).with_for_update().one_or_none()
    if not row:
        return jsonify({"error": "Definition not found"}), 404
    try:
        result = catalog_service.update_metadata(
            row, request.get_json(silent=True) or {}, _current()["id"],
            request.headers.get("Idempotency-Key", "").strip(),
        )
        return jsonify(result)
    except catalog_service.CatalogError as exc:
        db.session.rollback()
        return jsonify({"error": exc.message}), exc.status
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Catalog metadata conflict"}), 409


@document_bp.post("/api/platform/document-catalog/<definition_public_id>/lifecycle")
@require_platform_admin()
def document_catalog_lifecycle(definition_public_id: str):
    row = DocumentDefinition.query.filter_by(public_id=definition_public_id).with_for_update().one_or_none()
    if not row:
        return jsonify({"error": "Definition not found"}), 404
    try:
        result = catalog_service.transition(
            row, request.get_json(silent=True) or {}, _current()["id"],
            request.headers.get("Idempotency-Key", "").strip(),
        )
        return jsonify(result)
    except catalog_service.CatalogError as exc:
        db.session.rollback()
        return jsonify({"error": exc.message}), exc.status


@document_bp.get("/api/admin/organization-document-policy")
@require_organization_admin_context(allow_platform=False)
def organization_document_policy_list():
    return jsonify(organization_policy.list_policy(g.organization_context.organization_id))


@document_bp.put("/api/admin/organization-document-policy/<definition_public_id>")
@require_organization_admin_context(allow_platform=False)
def organization_document_policy_upsert(definition_public_id: str):
    actor = _current()
    try:
        item = organization_policy.upsert(g.organization_context.organization_id,
            definition_public_id, request.get_json(silent=True) or {}, actor["id"])
        return jsonify(item)
    except organization_policy.PolicyError as exc:
        db.session.rollback()
        return jsonify({"error": exc.message}), exc.status


@document_bp.get("/api/expert/requests/<int:case_id>/documents")
@require_auth
def case_documents(case_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return error
    actor = _current()
    try:
        service.initialize_requirements(case, actor["id"])
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Document requirements were initialized concurrently; retry the request"}), 409
    return jsonify(service.case_payload(case))


@document_bp.post("/api/expert/requests/<int:case_id>/documents/initialize")
@require_auth
def case_documents_initialize(case_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return error
    try:
        created = service.initialize_requirements(case, _current()["id"])
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Document requirements were initialized concurrently; retry the request"}), 409
    return jsonify({"created_count": created, **service.case_payload(case)})


@document_bp.post("/api/expert/requests/<int:case_id>/document-requirements/<int:requirement_id>/files")
@require_auth
def requirement_upload(case_id: int, requirement_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return error
    requirement = db.session.get(CaseDocumentRequirement, requirement_id)
    upload_file = request.files.get("file")
    if not upload_file:
        return jsonify({"error": "انتخاب فایل الزامی است"}), 400
    try:
        row = service.upload(case, _current()["id"], upload_file, requirement=requirement, description=request.form.get("description"))
        return jsonify(service.serialize_file(row)), 201
    except (service.DocumentError, Exception) as exc:
        if isinstance(exc, service.DocumentError):
            return jsonify({"error": exc.message}), exc.status
        raise


@document_bp.post("/api/expert/requests/<int:case_id>/document-requirements/<int:requirement_id>/replace")
@require_auth
def requirement_replace(case_id: int, requirement_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return error
    requirement = db.session.get(CaseDocumentRequirement, requirement_id)
    if not requirement or requirement.shipment_request_id != case.id:
        return jsonify({"error": "نیازمندی سند معتبر نیست"}), 404
    previous = CaseDocumentFile.query.filter_by(case_requirement_id=requirement.id, status="active").order_by(CaseDocumentFile.version_number.desc()).first()
    if not previous:
        return jsonify({"error": "نسخه فعالی برای جایگزینی وجود ندارد"}), 409
    upload_file = request.files.get("file")
    if not upload_file:
        return jsonify({"error": "انتخاب فایل الزامی است"}), 400
    actor_id = _current()["id"]
    try:
        row = service.upload(case, actor_id, upload_file, requirement=requirement, description=request.form.get("description"), replacement=previous)
        return jsonify(service.serialize_file(row)), 201
    except service.DocumentError as exc:
        db.session.rollback()
        return jsonify({"error": exc.message}), exc.status


@document_bp.post("/api/expert/requests/<int:case_id>/documents/miscellaneous")
@require_auth
def miscellaneous_upload(case_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return error
    upload_file = request.files.get("file")
    if not upload_file:
        return jsonify({"error": "انتخاب فایل الزامی است"}), 400
    try:
        row = service.upload(case, _current()["id"], upload_file, miscellaneous=True, custom_title=request.form.get("title"), description=request.form.get("description"))
        return jsonify(service.serialize_file(row)), 201
    except service.DocumentError as exc:
        return jsonify({"error": exc.message}), exc.status


@document_bp.get("/api/expert/requests/<int:case_id>/documents/<int:file_id>/download")
@require_auth
def file_download(case_id: int, file_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return error
    row = db.session.get(CaseDocumentFile, file_id)
    if (not row or is_quarantined("CaseDocumentFile", file_id)
            or row.shipment_request_id != case.id or row.status == "deleted"):
        return jsonify({"error": "فایل یافت نشد"}), 404
    try:
        path = PrivateDocumentStorage().resolve_for_download(row, case=case)
    except (DocumentStorageError, QuarantinedResource):
        return jsonify({"error": "فایل یافت نشد"}), 404
    if not path.is_file():
        return jsonify({"error": "فایل ذخیره‌شده در دسترس نیست"}), 404
    service.audit("file_downloaded", _current()["id"], case_id=case.id, file_id=row.id)
    db.session.commit()
    return send_file(path, as_attachment=True, download_name=row.safe_download_filename, mimetype=row.detected_mime_type)


@document_bp.delete("/api/expert/requests/<int:case_id>/documents/<int:file_id>")
@require_auth
def file_delete(case_id: int, file_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return error
    row = db.session.get(CaseDocumentFile, file_id)
    if (not row or is_quarantined("CaseDocumentFile", file_id)
            or row.shipment_request_id != case.id or row.status == "deleted"):
        return jsonify({"error": "فایل یافت نشد"}), 404
    reason = str((request.get_json(silent=True) or {}).get("reason", "")).strip()
    if not reason:
        return jsonify({"error": "دلیل حذف الزامی است"}), 400
    row.status, row.deleted_at, row.deleted_by, row.deletion_reason = "deleted", datetime.utcnow(), _current()["id"], reason
    service.audit("file_logically_deleted", _current()["id"], case_id=case.id, file_id=row.id, details={"reason": reason})
    db.session.commit()
    return jsonify({"id": row.id, "status": row.status})
