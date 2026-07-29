from __future__ import annotations

import io
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    DocumentDefinition,
    ExpertUser,
    ShipmentRequest,
)
from backend.services import case_document_service as document_service


PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
POSTGRES_URL = os.environ.get("DMS_DISPOSABLE_POSTGRES_URL")
POSTGRES_ROOT = os.environ.get("DMS_DISPOSABLE_STORAGE_ROOT")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL or not POSTGRES_ROOT,
    reason="requires explicit DMS_DISPOSABLE_POSTGRES_URL and DMS_DISPOSABLE_STORAGE_ROOT",
)


@pytest.fixture(scope="module")
def postgres_app():
    assert POSTGRES_URL.startswith(("postgresql://", "postgresql+psycopg"))
    assert "dms1a_" in POSTGRES_URL
    root = (Path(POSTGRES_ROOT).resolve() / f"run-{uuid4().hex}").resolve()
    root.mkdir(parents=True, exist_ok=False)
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": POSTGRES_URL,
        "DOCUMENT_STORAGE_ROOT": str(root),
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
    })
    with app.app_context():
        version = db.session.execute(text("show server_version")).scalar_one()
        database = db.session.execute(text("select current_database()")).scalar_one()
        revision = db.session.execute(text("select version_num from alembic_version")).scalar_one()
        assert version.startswith("18.")
        assert database.startswith("dms1a_")
        assert revision == "20260804_case_documents"
        db.session.rollback()
    yield app, root
    with app.app_context():
        db.session.remove()
    shutil.rmtree(root)


def _seed(app, *, maximum=1, with_initial=False):
    token = uuid4().hex
    with app.app_context():
        expert = ExpertUser(
            username=f"dms-{token}", password_hash="x", full_name="DMS concurrent",
            role="expert", is_active=True,
        )
        case = ShipmentRequest(
            contact_phone=token[:20], shipping_type="domestic", status="new",
            status_request_status="new",
        )
        definition_code = f"dms_{token}"
        definition = DocumentDefinition(
            code=definition_code, title="Concurrent evidence", is_required=True,
            allowed_formats='["pdf"]', max_file_size_bytes=1024 * 1024,
            max_active_file_count=maximum, sort_order=1, applicability_scope="all",
        )
        db.session.add_all([expert, case, definition])
        db.session.flush()
        case.assigned_to = expert.id
        db.session.commit()
        access = auth_manager.generate_tokens(expert.id)["access_token"]
        ids = {"case": case.id, "definition": definition.id, "expert": expert.id}
    client = app.test_client()
    headers = {"Authorization": f"Bearer {access}"}
    initialized = client.post(
        f"/api/expert/requests/{ids['case']}/documents/initialize", headers=headers,
    )
    assert initialized.status_code == 200
    ids["requirement"] = next(
        item["id"] for item in initialized.get_json()["requirements"]
        if item["code"] == definition_code
    )
    if with_initial:
        uploaded = client.post(
            f"/api/expert/requests/{ids['case']}/document-requirements/{ids['requirement']}/files",
            headers=headers, data={"file": (io.BytesIO(PDF), "initial.pdf")},
        )
        assert uploaded.status_code == 201
        ids["initial_file"] = uploaded.get_json()["id"]
    return ids, headers


def _concurrent_requests(app, calls):
    barrier = threading.Barrier(len(calls))

    def invoke(call):
        client = app.test_client()
        barrier.wait(timeout=10)
        return call(client)

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(invoke, call) for call in calls]
        return [future.result(timeout=30) for future in futures]


def test_postgresql_concurrent_requirement_initialization_is_idempotent(postgres_app, monkeypatch):
    app, _ = postgres_app
    token = uuid4().hex
    with app.app_context():
        expert = ExpertUser(
            username=f"init-{token}", password_hash="x", full_name="Initializer",
            role="expert", is_active=True,
        )
        case = ShipmentRequest(
            contact_phone=token[:20], shipping_type="domestic", status="new",
            status_request_status="new",
        )
        definition = DocumentDefinition(
            code=f"init_{token}", title="Initialize race", is_required=True,
            allowed_formats='["pdf"]', max_file_size_bytes=1024,
            max_active_file_count=1, sort_order=1, applicability_scope="all",
        )
        db.session.add_all([expert, case, definition])
        db.session.flush()
        case.assigned_to = expert.id
        db.session.commit()
        case_id, definition_id = case.id, definition.id
        token_value = auth_manager.generate_tokens(expert.id)["access_token"]
    headers = {"Authorization": f"Bearer {token_value}"}
    path = f"/api/expert/requests/{case_id}/documents/initialize"
    insert_barrier = threading.Barrier(2)

    original_audit = document_service.audit

    def synchronize_before_commit(*args, **kwargs):
        if kwargs.get("case_id") == case_id:
            insert_barrier.wait(timeout=10)
        return original_audit(*args, **kwargs)

    monkeypatch.setattr(document_service, "audit", synchronize_before_commit)
    responses = _concurrent_requests(app, [
        lambda client: client.post(path, headers=headers),
        lambda client: client.post(path, headers=headers),
    ])
    assert sorted(response.status_code for response in responses) in ([200, 200], [200, 409])
    assert all(response.status_code < 500 for response in responses)
    with app.app_context():
        assert CaseDocumentRequirement.query.filter_by(
            shipment_request_id=case_id, source_definition_id=definition_id,
        ).count() == 1


def test_postgresql_concurrent_first_uploads_allocate_unique_versions(postgres_app):
    app, root = postgres_app
    ids, headers = _seed(app, maximum=2)
    path = f"/api/expert/requests/{ids['case']}/document-requirements/{ids['requirement']}/files"
    responses = _concurrent_requests(app, [
        lambda client, n=n: client.post(
            path, headers=headers,
            data={"file": (io.BytesIO(PDF + f"\n{n}".encode()), f"first-{n}.pdf")},
        ) for n in (1, 2)
    ])
    assert [response.status_code for response in responses].count(201) == 2, [
        response.get_json(silent=True) for response in responses
    ]
    with app.app_context():
        rows = CaseDocumentFile.query.filter_by(case_requirement_id=ids["requirement"]).all()
        assert sorted(row.version_number for row in rows) == [1, 2]
        assert sum(row.status == "active" for row in rows) == 2
        assert all((root / row.storage_key).is_file() for row in rows)


def test_postgresql_concurrent_replacement_serializes_and_has_safe_loser(postgres_app):
    app, root = postgres_app
    ids, headers = _seed(app, maximum=1, with_initial=True)
    path = f"/api/expert/requests/{ids['case']}/document-requirements/{ids['requirement']}/replace"
    responses = _concurrent_requests(app, [
        lambda client, n=n: client.post(
            path, headers=headers,
            data={"file": (io.BytesIO(PDF + f"\nreplacement-{n}".encode()), f"replacement-{n}.pdf")},
        ) for n in (1, 2)
    ])
    assert sorted(response.status_code for response in responses) == [201, 409]
    with app.app_context():
        rows = CaseDocumentFile.query.filter_by(case_requirement_id=ids["requirement"]).order_by(
            CaseDocumentFile.version_number
        ).all()
        assert [row.version_number for row in rows] == [1, 2]
        assert [row.status for row in rows] == ["superseded", "active"]
        assert rows[0].superseded_by == rows[1].id
        assert all((root / row.storage_key).is_file() for row in rows)


def test_postgresql_concurrent_max_count_allows_only_one_active_upload(postgres_app):
    app, root = postgres_app
    ids, headers = _seed(app, maximum=1)
    path = f"/api/expert/requests/{ids['case']}/document-requirements/{ids['requirement']}/files"
    responses = _concurrent_requests(app, [
        lambda client, n=n: client.post(
            path, headers=headers,
            data={"file": (io.BytesIO(PDF + f"\nlimit-{n}".encode()), f"limit-{n}.pdf")},
        ) for n in (1, 2)
    ])
    assert sorted(response.status_code for response in responses) == [201, 400]
    with app.app_context():
        rows = CaseDocumentFile.query.filter_by(case_requirement_id=ids["requirement"]).all()
        assert len(rows) == 1 and rows[0].status == "active"
        case_files = [path for path in (root / str(ids["case"])).rglob("*") if path.is_file()]
        assert case_files == [root / rows[0].storage_key]


def test_postgresql_concurrent_miscellaneous_uploads_are_independent(postgres_app):
    app, root = postgres_app
    ids, headers = _seed(app)
    path = f"/api/expert/requests/{ids['case']}/documents/miscellaneous"
    responses = _concurrent_requests(app, [
        lambda client, n=n: client.post(
            path, headers=headers,
            data={
                "title": f"Misc {n}",
                "file": (io.BytesIO(PDF + f"\nmisc-{n}".encode()), f"misc-{n}.pdf"),
            },
        ) for n in (1, 2)
    ])
    assert [response.status_code for response in responses].count(201) == 2
    with app.app_context():
        rows = CaseDocumentFile.query.filter_by(
            shipment_request_id=ids["case"], is_miscellaneous=True,
        ).all()
        assert len(rows) == 2
        assert {row.version_number for row in rows} == {1}
        assert len({row.storage_key for row in rows}) == 2
        assert all(row.status == "active" and row.superseded_by is None for row in rows)
        assert all((root / row.storage_key).is_file() for row in rows)
