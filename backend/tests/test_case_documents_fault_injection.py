from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage

from backend import create_app
from backend.extensions import db
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    DocumentAuditEvent,
    DocumentDefinition,
    ExpertUser,
    ShipmentRequest,
)
from backend.services import case_document_service as service


PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


@pytest.fixture()
def fault_context(tmp_path):
    root = tmp_path / "private"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DOCUMENT_STORAGE_ROOT": str(root),
    })
    with app.app_context():
        actor = ExpertUser(
            username="fault-expert", password_hash="x", full_name="Fault Expert",
            role="expert", is_active=True,
        )
        case = ShipmentRequest(
            contact_phone="1", shipping_type="domestic", status="new",
            status_request_status="new",
        )
        definition = DocumentDefinition(
            code="fault_document", title="Fault document", is_required=True,
            allowed_formats='["pdf"]', max_file_size_bytes=1024 * 1024,
            max_active_file_count=1, sort_order=1, applicability_scope="all",
        )
        db.session.add_all([actor, case, definition])
        db.session.flush()
        case.assigned_to = actor.id
        requirement = CaseDocumentRequirement(
            shipment_request_id=case.id, source_definition_id=definition.id,
            source_definition_code=definition.code, source_definition_revision=1,
            title=definition.title, is_required=True, allowed_formats='["pdf"]',
            max_file_size_bytes=1024 * 1024, max_active_file_count=1,
            sort_order=1, applied_by=actor.id,
        )
        db.session.add(requirement)
        db.session.commit()
        yield app, root, case.id, actor.id, requirement.id


def _upload(case, actor_id, requirement=None, *, miscellaneous=False, replacement=None, suffix=b""):
    return service.upload(
        case, actor_id,
        FileStorage(stream=io.BytesIO(PDF + suffix), filename="evidence.pdf"),
        requirement=requirement, miscellaneous=miscellaneous,
        custom_title="Misc evidence" if miscellaneous else None,
        replacement=replacement,
    )


def _rows_and_files(root: Path):
    return (
        CaseDocumentFile.query.count(),
        DocumentAuditEvent.query.filter(
            DocumentAuditEvent.event_type.in_(["file_uploaded", "file_version_superseded"])
        ).count(),
        sorted(path for path in root.rglob("*") if path.is_file()),
    )


@pytest.mark.parametrize("miscellaneous", [False, True], ids=["requirement", "miscellaneous"])
def test_temporary_write_failure_leaves_no_database_audit_temp_or_final_file(
    fault_context, monkeypatch, miscellaneous,
):
    _, root, case_id, actor_id, requirement_id = fault_context
    case = db.session.get(ShipmentRequest, case_id)
    requirement = None if miscellaneous else db.session.get(CaseDocumentRequirement, requirement_id)
    original_open = Path.open

    def fail_temporary_open(path, *args, **kwargs):
        if path.name.endswith(".tmp"):
            raise OSError("injected temporary write failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_temporary_open)
    with pytest.raises(OSError, match="injected temporary write failure"):
        _upload(case, actor_id, requirement, miscellaneous=miscellaneous)
    assert _rows_and_files(root) == (0, 0, [])


@pytest.mark.parametrize("miscellaneous", [False, True], ids=["requirement", "miscellaneous"])
def test_atomic_finalize_failure_rolls_back_and_removes_temporary_file(
    fault_context, monkeypatch, miscellaneous,
):
    _, root, case_id, actor_id, requirement_id = fault_context
    case = db.session.get(ShipmentRequest, case_id)
    requirement = None if miscellaneous else db.session.get(CaseDocumentRequirement, requirement_id)

    def fail_replace(source, destination):
        assert Path(source).is_file()
        assert not Path(destination).exists()
        raise OSError("injected atomic rename failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected atomic rename failure"):
        _upload(case, actor_id, requirement, miscellaneous=miscellaneous)
    assert _rows_and_files(root) == (0, 0, [])


@pytest.mark.parametrize("failure_point", ["flush", "commit", "audit"])
@pytest.mark.parametrize("miscellaneous", [False, True], ids=["requirement", "miscellaneous"])
def test_database_or_audit_failure_rolls_back_and_removes_final_binary(
    fault_context, monkeypatch, failure_point, miscellaneous,
):
    _, root, case_id, actor_id, requirement_id = fault_context
    case = db.session.get(ShipmentRequest, case_id)
    requirement = None if miscellaneous else db.session.get(CaseDocumentRequirement, requirement_id)

    def injected_failure(*_args, **_kwargs):
        assert any(path.is_file() for path in root.rglob("*"))
        raise RuntimeError(f"injected {failure_point} failure")

    if failure_point == "audit":
        monkeypatch.setattr(service, "audit", injected_failure)
    else:
        monkeypatch.setattr(db.session, failure_point, injected_failure)
    with pytest.raises(RuntimeError, match=f"injected {failure_point} failure"):
        _upload(case, actor_id, requirement, miscellaneous=miscellaneous)
    db.session.rollback()
    assert _rows_and_files(root) == (0, 0, [])


@pytest.mark.parametrize("failure_point", ["flush", "commit", "audit"])
def test_replacement_failure_preserves_only_prior_active_version_and_binary(
    fault_context, monkeypatch, failure_point,
):
    _, root, case_id, actor_id, requirement_id = fault_context
    case = db.session.get(ShipmentRequest, case_id)
    requirement = db.session.get(CaseDocumentRequirement, requirement_id)
    previous = _upload(case, actor_id, requirement)
    previous_id, previous_key = previous.id, previous.storage_key
    baseline_audits = DocumentAuditEvent.query.count()

    call_count = 0
    original_audit = service.audit

    def injected_failure(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if failure_point != "audit" or call_count == 2:
            assert len([path for path in root.rglob("*") if path.is_file()]) == 2
            raise RuntimeError(f"injected replacement {failure_point} failure")
        return original_audit(*args, **kwargs)

    if failure_point == "audit":
        monkeypatch.setattr(service, "audit", injected_failure)
    else:
        monkeypatch.setattr(db.session, failure_point, injected_failure)
    with pytest.raises(RuntimeError, match=f"injected replacement {failure_point} failure"):
        _upload(case, actor_id, requirement, replacement=previous, suffix=b"\nreplacement")
    db.session.rollback()
    rows = CaseDocumentFile.query.filter_by(case_requirement_id=requirement_id).all()
    assert [(row.id, row.version_number, row.status) for row in rows] == [(previous_id, 1, "active")]
    assert DocumentAuditEvent.query.count() == baseline_audits
    files = [path for path in root.rglob("*") if path.is_file()]
    assert files == [root / previous_key]
