"""Current-integrated-head DMS compatibility contract.

This complements, and does not replace, the immutable revision-pinned DMS race
evidence in ``test_case_documents_postgresql.py``.
"""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import (DocumentAuditEvent, CaseDocumentFile,
                            DocumentDefinition, ExpertUser, ShipmentRequest)


PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


def _settings(tmp_path: Path):
    url = os.environ.get("INTEGRATED_RC_POSTGRES_URL", "")
    if not url:
        pytest.skip("explicit disposable Integrated RC PostgreSQL URL not provided")
    parsed = make_url(url)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_rc_")
    return url, tmp_path / "integrated-dms"


def _head() -> str:
    config = Config("backend/migrations/alembic.ini")
    config.set_main_option("script_location", "backend/migrations")
    return ScriptDirectory.from_config(config).get_current_head()


def _user(name: str, role: str = "expert") -> ExpertUser:
    return ExpertUser(username=f"{name}-{uuid4().hex}", password_hash="unused",
                      full_name=name, role=role, is_active=True)


def test_integrated_head_dms_identity_version_integrity_audit_and_tenant_boundary(tmp_path):
    url, root = _settings(tmp_path)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": url,
                      "DOCUMENT_STORAGE_ROOT": str(root), "SECRET_KEY": "integrated-dms"},
                     skip_startup=True)
    with app.app_context():
        assert db.session.execute(text("select version_num from alembic_version")).scalar_one() == _head()
        owner, outsider = _user("dms-owner"), _user("dms-outsider")
        case = ShipmentRequest(contact_phone=uuid4().hex[:20], shipping_type="domestic",
                               status="new", status_request_status="new")
        definition = DocumentDefinition(code=f"integrated_{uuid4().hex}", title="Synthetic evidence",
            is_required=True, allowed_formats='["pdf"]', max_file_size_bytes=1024 * 1024,
            max_active_file_count=1, sort_order=1, applicability_scope="all")
        db.session.add_all([owner, outsider, case, definition]); db.session.flush()
        case.assigned_to = owner.id; db.session.commit()
        owner_token = auth_manager.generate_tokens(owner.id)["access_token"]
        outsider_token = auth_manager.generate_tokens(outsider.id)["access_token"]
        case_id, code = case.id, definition.code

    client = app.test_client()
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    initialized = client.post(f"/api/expert/requests/{case_id}/documents/initialize", headers=owner_headers)
    assert initialized.status_code == 200
    requirement = next(x for x in initialized.get_json()["requirements"] if x["code"] == code)
    path = f"/api/expert/requests/{case_id}/document-requirements/{requirement['id']}"
    first = client.post(path + "/files", headers=owner_headers,
                        data={"file": (io.BytesIO(PDF + b"-v1"), "evidence-v1.pdf")})
    assert first.status_code == 201
    replacement = client.post(path + "/replace", headers=owner_headers,
        data={"file": (io.BytesIO(PDF + b"-v2"), "evidence-v2.pdf")})
    assert replacement.status_code == 201
    assert client.get(f"/api/expert/requests/{case_id}/documents", headers=outsider_headers).status_code in {403, 404}

    with app.app_context():
        rows = CaseDocumentFile.query.filter_by(case_requirement_id=requirement["id"]).order_by(
            CaseDocumentFile.version_number).all()
        assert [row.version_number for row in rows] == [1, 2]
        assert [row.status for row in rows] == ["superseded", "active"]
        assert rows[0].superseded_by == rows[1].id
        assert len({row.public_id for row in rows}) == 2
        for row, payload in zip(rows, (PDF + b"-v1", PDF + b"-v2")):
            stored = root / row.storage_key
            assert stored.is_file()
            assert hashlib.sha256(stored.read_bytes()).hexdigest() == hashlib.sha256(payload).hexdigest()
        assert DocumentAuditEvent.query.filter_by(shipment_request_id=case_id).count() >= 3
