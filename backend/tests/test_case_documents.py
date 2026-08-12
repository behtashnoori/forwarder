from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import CaseDocumentFile, CaseDocumentRequirement, DocumentAuditEvent, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.case_document_service import detect_format
from backend.services.document_storage_service import validate_storage_root


@pytest.fixture()
def document_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DOCUMENT_STORAGE_ROOT": str(tmp_path / "private"),
    })
    with app.app_context():
        admin = ExpertUser(username="doc-admin", password_hash="x", full_name="Admin", role="admin", authority="PLATFORM_ADMIN", is_active=True)
        expert = ExpertUser(username="doc-expert", password_hash="x", full_name="Expert", role="expert", is_active=True)
        outsider = ExpertUser(username="doc-other", password_hash="x", full_name="Other", role="expert", is_active=True)
        organization = OperationalOrganization(name="Case Documents Organization")
        db.session.add_all([admin, expert, outsider, organization])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=organization.id, user_id=user.id, permissions=[])
            for user in (admin, expert, outsider)
        ])
        case = ShipmentRequest(contact_phone="1", shipping_type="domestic", status="new", status_request_status="new", assigned_to=expert.id, ownership_scope="TENANT", operational_organization_id=organization.id)
        other_case = ShipmentRequest(contact_phone="2", shipping_type="domestic", status="new", status_request_status="new", assigned_to=outsider.id, ownership_scope="TENANT", operational_organization_id=organization.id)
        db.session.add_all([case, other_case])
        db.session.commit()
        values = {
            "admin": auth_manager.generate_tokens(admin.id)["access_token"],
            "expert": auth_manager.generate_tokens(expert.id)["access_token"],
            "outsider": auth_manager.generate_tokens(outsider.id)["access_token"],
            "case_id": case.id,
            "other_case_id": other_case.id,
            "root": tmp_path / "private",
        }
    return app, values


def headers(token): return {"Authorization": f"Bearer {token}"}


def definition_payload(**changes):
    value = {
        "code": "bill_of_lading", "title": "بارنامه", "description": "نسخه خوانا",
        "is_required": True, "allowed_formats": ["pdf", "jpeg"],
        "max_file_size_bytes": 1024 * 1024, "max_active_file_count": 1,
        "sort_order": 1, "applicability_scope": "all",
    }
    value.update(changes)
    return value


def pdf_bytes(): return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


def ooxml_bytes(kind: str) -> bytes:
    target = io.BytesIO()
    main = "word/document.xml" if kind == "docx" else "xl/workbook.xml"
    content_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        if kind == "docx" else
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
    )
    with zipfile.ZipFile(target, "w") as package:
        package.writestr("[Content_Types].xml", f'<Types><Override PartName="/{main}" ContentType="{content_type}"/></Types>')
        package.writestr("_rels/.rels", "<Relationships/>")
        package.writestr(main, "<root/>")
    return target.getvalue()


def test_storage_root_policy(tmp_path):
    repository = tmp_path / "release"
    repository.mkdir()
    durable = tmp_path / "durable" / "documents"
    assert validate_storage_root(durable, production=True, repository_root=repository) == durable.resolve()
    with pytest.raises(RuntimeError):
        validate_storage_root(None, production=True, repository_root=repository)
    with pytest.raises(RuntimeError):
        validate_storage_root("relative/documents", production=True, repository_root=repository)
    with pytest.raises(RuntimeError):
        validate_storage_root(repository / "instance" / "documents", production=True, repository_root=repository)
    unusable = tmp_path / "file"
    unusable.write_text("not a directory")
    with pytest.raises(RuntimeError):
        validate_storage_root(unusable, production=True, repository_root=repository)


def test_format_detection_rejects_spoofs_and_truncation():
    assert detect_format(pdf_bytes()) == ("pdf", "application/pdf")
    assert detect_format(b"%PDF-1.7") is None
    assert detect_format(b"\x89PNG\r\n\x1a\n") is None
    assert detect_format(b"\xff\xd8\xff") is None
    assert detect_format(ooxml_bytes("docx"))[0] == "docx"
    assert detect_format(ooxml_bytes("xlsx"))[0] == "xlsx"
    arbitrary = io.BytesIO()
    with zipfile.ZipFile(arbitrary, "w") as package:
        package.writestr("word/document.xml", "<script/>")
    assert detect_format(arbitrary.getvalue()) is None


def test_admin_definition_validation_authorization_and_deactivation(document_app):
    app, state = document_app; client = app.test_client()
    assert client.post("/api/admin/document-definitions", headers=headers(state["expert"]), json=definition_payload()).status_code == 403
    created = client.post("/api/admin/document-definitions", headers=headers(state["admin"]), json=definition_payload())
    assert created.status_code == 201
    definition_id = created.get_json()["id"]
    assert client.post("/api/admin/document-definitions", headers=headers(state["admin"]), json=definition_payload()).status_code == 409
    assert client.post("/api/admin/document-definitions", headers=headers(state["admin"]), json=definition_payload(code="bad-code")).status_code == 400
    assert client.post("/api/admin/document-definitions", headers=headers(state["admin"]), json=definition_payload(code="bad_format", allowed_formats=["exe"])).status_code == 400
    assert client.patch(f"/api/admin/document-definitions/{definition_id}", headers=headers(state["admin"]), json={"title": "بارنامه جدید"}).get_json()["revision"] == 2
    response = client.post(f"/api/admin/document-definitions/{definition_id}/activation", headers=headers(state["admin"]), json={"is_active": False})
    assert response.get_json()["is_active"] is False


def test_snapshot_is_idempotent_and_immutable(document_app):
    app, state = document_app; client = app.test_client()
    created = client.post("/api/admin/document-definitions", headers=headers(state["admin"]), json=definition_payload()).get_json()
    first = client.get(f"/api/expert/requests/{state['case_id']}/documents", headers=headers(state["expert"]))
    second = client.post(f"/api/expert/requests/{state['case_id']}/documents/initialize", headers=headers(state["expert"]))
    assert first.get_json()["summary"]["total_requirements"] == 1
    assert second.get_json()["created_count"] == 0
    client.patch(f"/api/admin/document-definitions/{created['id']}", headers=headers(state["admin"]), json={"title": "عنوان جدید"})
    unchanged = client.get(f"/api/expert/requests/{state['case_id']}/documents", headers=headers(state["expert"])).get_json()
    assert unchanged["requirements"][0]["title"] == "بارنامه"
    with app.app_context():
        assert CaseDocumentRequirement.query.count() == 1


def test_upload_download_delete_security_and_miscellaneous(document_app):
    app, state = document_app; client = app.test_client()
    client.post("/api/admin/document-definitions", headers=headers(state["admin"]), json=definition_payload())
    requirement = client.get(f"/api/expert/requests/{state['case_id']}/documents", headers=headers(state["expert"])).get_json()["requirements"][0]
    path = f"/api/expert/requests/{state['case_id']}/document-requirements/{requirement['id']}/files"
    assert client.post(path, headers=headers(state["expert"]), data={"file": (io.BytesIO(b""), "empty.pdf")}).status_code == 400
    assert client.post(path, headers=headers(state["expert"]), data={"file": (io.BytesIO(pdf_bytes()), "payload.exe")}).status_code == 400
    assert client.post(path, headers=headers(state["expert"]), data={"file": (io.BytesIO(pdf_bytes()), "photo.jpg")}).status_code == 400
    uploaded = client.post(path, headers=headers(state["expert"]), data={"file": (io.BytesIO(pdf_bytes()), "../../invoice.pdf")})
    assert uploaded.status_code == 201
    row = uploaded.get_json()
    assert row["sha256_hash"] and row["file_size_bytes"] == len(pdf_bytes())
    assert client.get(f"/api/expert/requests/{state['case_id']}/documents/{row['id']}/download", headers=headers(state["outsider"])).status_code == 403
    download = client.get(f"/api/expert/requests/{state['case_id']}/documents/{row['id']}/download", headers=headers(state["expert"]))
    assert download.status_code == 200 and "attachment" in download.headers["Content-Disposition"]
    assert client.delete(f"/api/expert/requests/{state['case_id']}/documents/{row['id']}", headers=headers(state["expert"]), json={}).status_code == 400
    assert client.delete(f"/api/expert/requests/{state['case_id']}/documents/{row['id']}", headers=headers(state["expert"]), json={"reason": "نسخه اشتباه"}).status_code == 200
    assert client.get(f"/api/expert/requests/{state['case_id']}/documents/{row['id']}/download", headers=headers(state["expert"])).status_code == 404
    misc_path = f"/api/expert/requests/{state['case_id']}/documents/miscellaneous"
    assert client.post(misc_path, headers=headers(state["expert"]), data={"file": (io.BytesIO(pdf_bytes()), "misc.pdf")}).status_code == 400
    assert client.post(misc_path, headers=headers(state["expert"]), data={"title": "سند تکمیلی", "file": (io.BytesIO(pdf_bytes()), "misc.pdf")}).status_code == 201
    with app.app_context():
        file_row = db.session.get(CaseDocumentFile, row["id"])
        assert file_row.status == "deleted"
        assert (state["root"] / file_row.storage_key).exists()
        assert Path(file_row.storage_key).name != "invoice.pdf"
        assert DocumentAuditEvent.query.filter_by(event_type="file_downloaded").count() == 1


def test_replacement_retains_binary_and_versions(document_app):
    app, state = document_app; client = app.test_client()
    client.post("/api/admin/document-definitions", headers=headers(state["admin"]), json=definition_payload())
    requirement = client.get(f"/api/expert/requests/{state['case_id']}/documents", headers=headers(state["expert"])).get_json()["requirements"][0]
    base = f"/api/expert/requests/{state['case_id']}/document-requirements/{requirement['id']}"
    first = client.post(base + "/files", headers=headers(state["expert"]), data={"file": (io.BytesIO(pdf_bytes()), "one.pdf")}).get_json()
    second = client.post(base + "/replace", headers=headers(state["expert"]), data={"file": (io.BytesIO(pdf_bytes()+b"\n2"), "two.pdf")})
    assert second.status_code == 201 and second.get_json()["version_number"] == 2
    with app.app_context():
        old = db.session.get(CaseDocumentFile, first["id"])
        assert old.status == "superseded"
        assert (state["root"] / old.storage_key).exists()


@pytest.fixture()
def cross_case_documents(document_app):
    app, state = document_app
    client = app.test_client()
    client.post(
        "/api/admin/document-definitions",
        headers=headers(state["admin"]),
        json=definition_payload(),
    )
    case_a = client.get(
        f"/api/expert/requests/{state['case_id']}/documents",
        headers=headers(state["expert"]),
    ).get_json()
    case_b = client.get(
        f"/api/expert/requests/{state['other_case_id']}/documents",
        headers=headers(state["admin"]),
    ).get_json()
    requirement_a = case_a["requirements"][0]["id"]
    requirement_b = case_b["requirements"][0]["id"]
    first_a = client.post(
        f"/api/expert/requests/{state['case_id']}/document-requirements/{requirement_a}/files",
        headers=headers(state["expert"]),
        data={"file": (io.BytesIO(pdf_bytes()), "case-a-v1.pdf")},
    ).get_json()
    active_a = client.post(
        f"/api/expert/requests/{state['case_id']}/document-requirements/{requirement_a}/replace",
        headers=headers(state["expert"]),
        data={"file": (io.BytesIO(pdf_bytes() + b"\n2"), "case-a-v2.pdf")},
    ).get_json()
    active_b = client.post(
        f"/api/expert/requests/{state['other_case_id']}/document-requirements/{requirement_b}/files",
        headers=headers(state["admin"]),
        data={"file": (io.BytesIO(pdf_bytes()), "case-b.pdf")},
    ).get_json()
    misc_a = client.post(
        f"/api/expert/requests/{state['case_id']}/documents/miscellaneous",
        headers=headers(state["expert"]),
        data={"title": "Case A misc", "file": (io.BytesIO(pdf_bytes()), "misc-a.pdf")},
    ).get_json()
    state.update({
        "requirement_a": requirement_a,
        "requirement_b": requirement_b,
        "superseded_a": first_a["id"],
        "active_a": active_a["id"],
        "active_b": active_b["id"],
        "misc_a": misc_a["id"],
    })
    return app, state


def _document_state(app, root):
    with app.app_context():
        rows = [
            (row.id, row.shipment_request_id, row.status, row.storage_key)
            for row in CaseDocumentFile.query.order_by(CaseDocumentFile.id)
        ]
        audits = DocumentAuditEvent.query.count()
        requirements = CaseDocumentRequirement.query.count()
    files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    return rows, audits, requirements, files


def _assert_denied_without_side_effect(cross_case_documents, method, path, **kwargs):
    app, state = cross_case_documents
    client = app.test_client()
    before = _document_state(app, state["root"])
    response = getattr(client, method)(path, headers=headers(state["expert"]), **kwargs)
    assert response.status_code in {403, 404}
    assert _document_state(app, state["root"]) == before


def test_expert_a_cannot_upload_using_case_b_requirement_id(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "post",
        f"/api/expert/requests/{state['case_id']}/document-requirements/{state['requirement_b']}/files",
        data={"file": (io.BytesIO(pdf_bytes()), "guess.pdf")},
    )


def test_expert_a_cannot_upload_replacement_for_case_b_file(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "post",
        f"/api/expert/requests/{state['other_case_id']}/document-requirements/{state['requirement_b']}/replace",
        data={"file": (io.BytesIO(pdf_bytes()), "replace.pdf")},
    )


def test_expert_a_cannot_download_case_b_active_file(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "get",
        f"/api/expert/requests/{state['other_case_id']}/documents/{state['active_b']}/download",
    )


def test_expert_a_cannot_download_case_b_superseded_version(cross_case_documents):
    app, state = cross_case_documents
    client = app.test_client()
    old_b = client.post(
        f"/api/expert/requests/{state['other_case_id']}/document-requirements/{state['requirement_b']}/replace",
        headers=headers(state["admin"]),
        data={"file": (io.BytesIO(pdf_bytes() + b"\nnew"), "case-b-new.pdf")},
    )
    assert old_b.status_code == 201
    _assert_denied_without_side_effect(
        cross_case_documents, "get",
        f"/api/expert/requests/{state['other_case_id']}/documents/{state['active_b']}/download",
    )


def test_expert_a_cannot_list_case_b_version_history(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "get",
        f"/api/expert/requests/{state['other_case_id']}/documents",
    )


def test_expert_a_cannot_logically_delete_case_b_file(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "delete",
        f"/api/expert/requests/{state['other_case_id']}/documents/{state['active_b']}",
        json={"reason": "unauthorized"},
    )


def test_expert_a_cannot_use_case_a_route_with_case_b_file_id(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "get",
        f"/api/expert/requests/{state['case_id']}/documents/{state['active_b']}/download",
    )


def test_expert_a_cannot_use_case_b_route_with_case_a_requirement_id(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "post",
        f"/api/expert/requests/{state['other_case_id']}/document-requirements/{state['requirement_a']}/files",
        data={"file": (io.BytesIO(pdf_bytes()), "cross-case.pdf")},
    )


@pytest.mark.parametrize("operation", ["initialize", "list"])
def test_unassigned_expert_cannot_initialize_or_list_case_documents(cross_case_documents, operation):
    app, state = cross_case_documents
    client = app.test_client()
    before = _document_state(app, state["root"])
    suffix = "/documents/initialize" if operation == "initialize" else "/documents"
    response = getattr(client, "post" if operation == "initialize" else "get")(
        f"/api/expert/requests/{state['case_id']}{suffix}",
        headers=headers(state["outsider"]),
    )
    assert response.status_code == 403
    assert _document_state(app, state["root"]) == before


def test_miscellaneous_upload_enforces_case_authorization(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "post",
        f"/api/expert/requests/{state['other_case_id']}/documents/miscellaneous",
        data={"title": "guess", "file": (io.BytesIO(pdf_bytes()), "guess.pdf")},
    )


def test_miscellaneous_download_enforces_case_authorization(cross_case_documents):
    _, state = cross_case_documents
    _assert_denied_without_side_effect(
        cross_case_documents, "get",
        f"/api/expert/requests/{state['other_case_id']}/documents/{state['misc_a']}/download",
    )


@pytest.mark.parametrize("file_key", ["active_a", "superseded_a", "misc_a"])
def test_guessing_document_id_alone_never_grants_access(cross_case_documents, file_key):
    app, state = cross_case_documents
    client = app.test_client()
    before = _document_state(app, state["root"])
    response = client.get(
        f"/api/expert/requests/{state['case_id']}/documents/{state[file_key]}/download",
        headers=headers(state["outsider"]),
    )
    assert response.status_code == 403
    assert _document_state(app, state["root"]) == before


def test_admin_can_access_both_cases_under_existing_policy(cross_case_documents):
    app, state = cross_case_documents
    client = app.test_client()
    assert client.get(
        f"/api/expert/requests/{state['case_id']}/documents",
        headers=headers(state["admin"]),
    ).status_code == 200
    assert client.get(
        f"/api/expert/requests/{state['other_case_id']}/documents/{state['active_b']}/download",
        headers=headers(state["admin"]),
    ).status_code == 200


def test_unauthenticated_document_access_is_rejected_without_side_effect(cross_case_documents):
    app, state = cross_case_documents
    client = app.test_client()
    before = _document_state(app, state["root"])
    response = client.get(f"/api/expert/requests/{state['case_id']}/documents")
    assert response.status_code == 401
    assert _document_state(app, state["root"]) == before


def test_download_audit_commit_failure_fails_closed_without_mutation(
    cross_case_documents, monkeypatch,
):
    app, state = cross_case_documents
    client = app.test_client()
    app.config["PROPAGATE_EXCEPTIONS"] = False
    before = _document_state(app, state["root"])

    def fail_commit():
        raise RuntimeError("injected download audit persistence failure")

    monkeypatch.setattr(db.session, "commit", fail_commit)
    response = client.get(
        f"/api/expert/requests/{state['case_id']}/documents/{state['active_a']}/download",
        headers=headers(state["expert"]),
    )
    assert response.status_code == 500
    assert response.data != pdf_bytes() + b"\n2"
    assert _document_state(app, state["root"]) == before


@pytest.mark.parametrize("file_key", ["active_a", "superseded_a"])
def test_successful_active_and_superseded_download_each_create_exactly_one_audit(
    cross_case_documents, file_key,
):
    app, state = cross_case_documents
    client = app.test_client()
    with app.app_context():
        before = DocumentAuditEvent.query.filter_by(
            event_type="file_downloaded", document_file_id=state[file_key],
        ).count()
    response = client.get(
        f"/api/expert/requests/{state['case_id']}/documents/{state[file_key]}/download",
        headers=headers(state["expert"]),
    )
    assert response.status_code == 200
    with app.app_context():
        after = DocumentAuditEvent.query.filter_by(
            event_type="file_downloaded", document_file_id=state[file_key],
        ).count()
    assert after == before + 1
