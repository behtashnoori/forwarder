"""Authorized admin definition and expert case-document APIs."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, g, jsonify, request, send_file
from sqlalchemy.exc import IntegrityError

from backend.auth import get_current_user
from backend.extensions import db
from backend.models import CaseDocumentFile, CaseDocumentRequirement, DocumentDefinition, ShipmentRequest
from backend.security import require_auth
from backend.services import case_document_service as service
from backend.services.document_storage_service import DocumentStorageError, PrivateDocumentStorage
from backend.services.expert_request_detail_service import can_access_request_detail
from backend.services.ownership_service import tenant_organization_for_user
from backend.services.shipment_request_identity_service import resolve_tenant_request_by_public_id
from backend.quarantine import QuarantinedResource, is_quarantined
from backend.services.admin_authorization_service import require_organization_admin_context, require_platform_admin
from backend.services import organization_document_policy_service as organization_policy
from backend.services import document_catalog_service as catalog_service
from backend.services import shipment_document_service as shipment_documents
from backend.services.assigned_work_authorization import authorize_document_management, authorize_work_action
from backend.operational_models import OperationalShipment

document_bp = Blueprint("case_documents", __name__)


def _resolve_opaque_case_route(handler):
    @wraps(handler)
    def resolved(*args, **kwargs):
        identity = kwargs.get("case_id")
        if isinstance(identity, str):
            try:
                organization_id = tenant_organization_for_user(get_current_user())
            except (TypeError, ValueError):
                kwargs["case_id"] = 0
            else:
                row = resolve_tenant_request_by_public_id(organization_id, identity)
                kwargs["case_id"] = row.id if row else 0
        return handler(*args, **kwargs)
    return resolved


def _current():
    return get_current_user()


def _case_or_error(case_id: int):
    case = db.session.get(ShipmentRequest, case_id)
    if not case or is_quarantined("ShipmentRequest", case_id):
        return None, (jsonify({"error": "پرونده یافت نشد"}), 404)
    if not can_access_request_detail(case, _current()):
        return None, (jsonify({"error": "شما به این پرونده دسترسی ندارید"}), 403)
    return case, None


def _case_manage_or_error(case_id: int):
    case, error = _case_or_error(case_id)
    if error:
        return None, error
    if not authorize_document_management(_current(), case).allowed:
        return None, (
            jsonify({
                "error": "شما مجاز به مدیریت اسناد این پرونده نیستید",
                "code": "DOCUMENT_MUTATION_FORBIDDEN",
            }),
            403,
        )
    return case, None


def _document_error(exc: service.DocumentError):
    return jsonify({"error": exc.message, "code": exc.code}), exc.status


def _requirement_for_selector(
    case: ShipmentRequest, definition_public_id: str, revision_value: str | None,
):
    try:
        revision = int(str(revision_value or ""))
    except ValueError:
        return None
    definition = DocumentDefinition.query.filter_by(public_id=definition_public_id).one_or_none()
    if definition is None:
        return None
    return CaseDocumentRequirement.query.filter_by(
        shipment_request_id=case.id,
        operational_organization_id=case.operational_organization_id,
        source_definition_id=definition.id,
        source_definition_revision=revision,
    ).one_or_none()


def _replacement_for_requirement(
    case: ShipmentRequest, requirement: CaseDocumentRequirement, public_id: str,
):
    return CaseDocumentFile.query.filter_by(
        public_id=public_id,
        owner_type="REQUEST",
        shipment_request_id=case.id,
        operational_organization_id=case.operational_organization_id,
        case_requirement_id=requirement.id,
    ).one_or_none()


def _upload_to_requirement(
    case: ShipmentRequest,
    requirement: CaseDocumentRequirement | None,
    *,
    replacement_required: bool = False,
    legacy_response: bool = False,
):
    if requirement is None or requirement.shipment_request_id != case.id:
        return jsonify({"error": "نیازمندی سند معتبر نیست", "code": "DOCUMENT_PARENT_NOT_FOUND"}), 404
    upload_file = request.files.get("file")
    if not upload_file:
        return jsonify({"error": "انتخاب فایل الزامی است", "code": "DOCUMENT_FILE_REQUIRED"}), 400
    replacement_public_id = request.form.get("replaces_file_public_id", "").strip()
    if replacement_required and not replacement_public_id:
        return jsonify({
            "error": "فایل جاری هدف برای جایگزینی الزامی است",
            "code": "REPLACEMENT_TARGET_REQUIRED",
        }), 422
    replacement = None
    if replacement_public_id:
        replacement = _replacement_for_requirement(case, requirement, replacement_public_id)
        if replacement is None:
            return jsonify({"error": "فایل یافت نشد", "code": "DOCUMENT_PARENT_NOT_FOUND"}), 404
        if replacement.status != "active":
            return jsonify({
                "error": "فایل انتخاب‌شده دیگر جاری نیست",
                "code": "REPLACEMENT_TARGET_CHANGED",
            }), 409
    try:
        row = service.upload(
            case, _current(), upload_file, requirement=requirement,
            description=request.form.get("description"), replacement=replacement,
        )
        return jsonify(service.serialize_file(row) if legacy_response else service.project_file(row)), 201
    except service.DocumentError as exc:
        return _document_error(exc)


def _shipment_or_error(public_id: str, action: str = "document.read"):
    row = OperationalShipment.query.filter_by(public_id=public_id).one_or_none()
    if row is None or not authorize_work_action(_current(), row, action).allowed:
        return None, (jsonify({"error": "محموله یا دسترسی سند یافت نشد"}), 404)
    return row, None


@document_bp.get("/api/internal/operational-shipments/<shipment_id>/documents")
@require_auth
def shipment_document_list(shipment_id: str):
    shipment, error = _shipment_or_error(shipment_id)
    return error if error else jsonify({
        "data": shipment_documents.documents(shipment),
        "can_manage_documents": authorize_document_management(_current(), shipment).allowed,
    })


@document_bp.post("/api/internal/operational-shipments/<shipment_id>/documents")
@require_auth
def shipment_document_upload(shipment_id: str):
    shipment, error = _shipment_or_error(shipment_id, "document.manage")
    if error:
        return error
    upload_file = request.files.get("file")
    if not upload_file:
        return jsonify({"error": "انتخاب فایل الزامی است"}), 400
    try:
        replacement_id = request.form.get("replaces_document_public_id", "").strip()
        replacement = CaseDocumentFile.query.filter_by(
            public_id=replacement_id,
            owner_type="SHIPMENT",
            operational_shipment_id=shipment.id,
            operational_organization_id=shipment.organization_id,
        ).one_or_none() if replacement_id else None
        if replacement_id and replacement is None:
            return jsonify({"error": "فایل یافت نشد", "code": "DOCUMENT_PARENT_NOT_FOUND"}), 404
        row = shipment_documents.upload(shipment, _current(), upload_file,
            request.form.get("title", ""), request.form.get("description"),
            request.headers.get("Idempotency-Key", "").strip(), replacement)
        item = next(item for item in shipment_documents.documents(shipment) if item["public_id"] == row.public_id)
        return jsonify({"data": item}), 201
    except service.DocumentError as exc:
        return jsonify({"error": exc.message}), exc.status


@document_bp.get("/api/internal/operational-shipments/<shipment_id>/documents/<document_id>/download")
@require_auth
def shipment_document_download(shipment_id: str, document_id: str):
    shipment, error = _shipment_or_error(shipment_id)
    if error:
        return error
    row = CaseDocumentFile.query.filter_by(public_id=document_id, operational_organization_id=shipment.organization_id).one_or_none()
    if row is None:
        return jsonify({"error": "فایل یافت نشد"}), 404
    try:
        path = PrivateDocumentStorage().resolve_for_shipment_download(row, shipment=shipment)
    except (DocumentStorageError, QuarantinedResource):
        return jsonify({"error": "فایل یافت نشد"}), 404
    return send_file(path, as_attachment=True, download_name=row.safe_download_filename, mimetype=row.detected_mime_type)


@document_bp.delete("/api/internal/operational-shipments/<shipment_id>/documents/<document_id>")
@require_auth
def shipment_document_delete(shipment_id: str, document_id: str):
    shipment, error = _shipment_or_error(shipment_id, "document.manage")
    if error:
        return error
    row = CaseDocumentFile.query.filter_by(
        public_id=document_id, owner_type="SHIPMENT",
        operational_shipment_id=shipment.id,
        operational_organization_id=shipment.organization_id,
    ).one_or_none()
    if row is None:
        return jsonify({"error": "فایل یافت نشد"}), 404
    try:
        shipment_documents.remove(shipment, row, _current(), (request.get_json(silent=True) or {}).get("reason"))
        return jsonify({"data": {"public_id": row.public_id, "lifecycle_state": row.status}})
    except service.DocumentError as exc:
        return jsonify({"error": exc.message}), exc.status


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
@document_bp.get("/api/expert/requests/<case_id>/documents")
@require_auth
@_resolve_opaque_case_route
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
    try:
        return jsonify(service.case_payload(
            case, can_manage=authorize_document_management(actor, case).allowed,
        ))
    except service.DocumentError as exc:
        return _document_error(exc)


@document_bp.post("/api/expert/requests/<int:case_id>/documents/initialize")
@document_bp.post("/api/expert/requests/<case_id>/documents/initialize")
@require_auth
@_resolve_opaque_case_route
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
    try:
        return jsonify({
            "created_count": created,
            **service.case_payload(
                case,
                can_manage=authorize_document_management(_current(), case).allowed,
            ),
        })
    except service.DocumentError as exc:
        return _document_error(exc)


@document_bp.post("/api/expert/requests/<int:case_id>/document-requirements/<int:requirement_id>/files")
@document_bp.post("/api/expert/requests/<case_id>/document-requirements/<int:requirement_id>/files")
@require_auth
@_resolve_opaque_case_route
def requirement_upload(case_id: int, requirement_id: int):
    case, error = _case_manage_or_error(case_id)
    if error:
        return error
    requirement = db.session.get(CaseDocumentRequirement, requirement_id)
    return _upload_to_requirement(case, requirement, legacy_response=True)


@document_bp.post("/api/expert/requests/<case_id>/document-requirements/<definition_public_id>/files")
@require_auth
@_resolve_opaque_case_route
def requirement_upload_opaque(case_id: int, definition_public_id: str):
    case, error = _case_manage_or_error(case_id)
    if error:
        return error
    requirement = _requirement_for_selector(
        case, definition_public_id, request.form.get("source_definition_revision"),
    )
    return _upload_to_requirement(case, requirement)


@document_bp.post("/api/expert/requests/<int:case_id>/document-requirements/<int:requirement_id>/replace")
@document_bp.post("/api/expert/requests/<case_id>/document-requirements/<int:requirement_id>/replace")
@require_auth
@_resolve_opaque_case_route
def requirement_replace(case_id: int, requirement_id: int):
    case, error = _case_manage_or_error(case_id)
    if error:
        return error
    requirement = db.session.get(CaseDocumentRequirement, requirement_id)
    return _upload_to_requirement(
        case, requirement, replacement_required=True, legacy_response=True,
    )


@document_bp.post("/api/expert/requests/<int:case_id>/documents/miscellaneous")
@document_bp.post("/api/expert/requests/<case_id>/documents/miscellaneous")
@require_auth
@_resolve_opaque_case_route
def miscellaneous_upload(case_id: int):
    case, error = _case_manage_or_error(case_id)
    if error:
        return error
    upload_file = request.files.get("file")
    if not upload_file:
        return jsonify({"error": "انتخاب فایل الزامی است"}), 400
    try:
        row = service.upload(case, _current(), upload_file, miscellaneous=True, custom_title=request.form.get("title"), description=request.form.get("description"))
        return jsonify(service.serialize_file(row)), 201
    except service.DocumentError as exc:
        return _document_error(exc)


def _file_for_case(case: ShipmentRequest, *, file_id: int | None = None, public_id: str | None = None):
    query = CaseDocumentFile.query.filter_by(
        owner_type="REQUEST",
        shipment_request_id=case.id,
        operational_organization_id=case.operational_organization_id,
    )
    return query.filter_by(id=file_id).one_or_none() if file_id is not None else query.filter_by(public_id=public_id).one_or_none()


def _download_case_file(case_id: int, *, file_id: int | None = None, public_id: str | None = None):
    case, error = _case_or_error(case_id)
    if error:
        return error
    row = _file_for_case(case, file_id=file_id, public_id=public_id)
    if (not row or is_quarantined("CaseDocumentFile", row.id) or row.status == "deleted"):
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


@document_bp.get("/api/expert/requests/<int:case_id>/documents/<int:file_id>/download")
@document_bp.get("/api/expert/requests/<case_id>/documents/<int:file_id>/download")
@require_auth
@_resolve_opaque_case_route
def file_download(case_id: int, file_id: int):
    return _download_case_file(case_id, file_id=file_id)


@document_bp.get("/api/expert/requests/<case_id>/documents/<file_public_id>/download")
@require_auth
@_resolve_opaque_case_route
def file_download_opaque(case_id: int, file_public_id: str):
    return _download_case_file(case_id, public_id=file_public_id)


def _delete_case_file(case_id: int, *, file_id: int | None = None, public_id: str | None = None):
    case, error = _case_manage_or_error(case_id)
    if error:
        return error
    row = _file_for_case(case, file_id=file_id, public_id=public_id)
    if not row or is_quarantined("CaseDocumentFile", row.id):
        return jsonify({"error": "فایل یافت نشد", "code": "DOCUMENT_PARENT_NOT_FOUND"}), 404
    try:
        row = service.deactivate(
            case, _current(), row,
            (request.get_json(silent=True) or {}).get("reason", ""),
        )
        return jsonify({"public_id": row.public_id, "status": row.status})
    except service.DocumentError as exc:
        return _document_error(exc)


@document_bp.delete("/api/expert/requests/<int:case_id>/documents/<int:file_id>")
@document_bp.delete("/api/expert/requests/<case_id>/documents/<int:file_id>")
@require_auth
@_resolve_opaque_case_route
def file_delete(case_id: int, file_id: int):
    return _delete_case_file(case_id, file_id=file_id)


@document_bp.delete("/api/expert/requests/<case_id>/documents/<file_public_id>")
@require_auth
@_resolve_opaque_case_route
def file_delete_opaque(case_id: int, file_public_id: str):
    return _delete_case_file(case_id, public_id=file_public_id)
