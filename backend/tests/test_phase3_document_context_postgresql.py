"""Disposable PostgreSQL 18 proof for P3-06 legacy-safe migration."""
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import CaseDocumentFile
from backend.document_context_models import OperationalDocumentContext
from backend.operational_models import OperationalShipment
from backend.services import document_context_service as contexts
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime


POSTGRES_URL = os.environ.get("P3_DOCUMENT_CONTEXT_POSTGRES_URL", "")
PARENT = "20261004_phase3_cargo_allocation_trace"
HEAD = "20261005_phase3_contextual_documents"
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="requires owned P3_DOCUMENT_CONTEXT_POSTGRES_URL")


def test_postgresql18_legacy_document_upgrade_downgrade_guard():
    parsed = make_url(POSTGRES_URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_p3_06_documents_")
    engine = sa.create_engine(POSTGRES_URL)
    with engine.connect() as connection:
        assert int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) >= 180000
    config = alembic_config(POSTGRES_URL)
    command.upgrade(config, PARENT)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": POSTGRES_URL,
                      "SECRET_KEY": "p3-06-disposable-postgresql"}, skip_startup=True)
    with app.app_context():
        fixture = _seed_runtime(app)
        shipment = OperationalShipment.query.filter_by(public_id=fixture["shipment"]).one()
        legacy = CaseDocumentFile(
            owner_type="SHIPMENT", operational_shipment_id=shipment.id,
            operational_organization_id=shipment.organization_id,
            is_miscellaneous=True, custom_title="Legacy internal",
            original_filename="legacy.pdf", safe_download_filename="legacy.pdf",
            storage_key=f"shipment-{shipment.id}/legacy/legacy.pdf",
            canonical_extension="pdf", detected_mime_type="application/pdf",
            file_size_bytes=10, sha256_hash="0" * 64, version_number=1,
            uploaded_by=fixture["owner"],
        )
        db.session.add(legacy)
        db.session.commit()
        legacy_id = legacy.id
        db.session.remove()
        db.engine.dispose()

    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM operational_document_context")).scalar_one() == 0
        assert connection.execute(sa.text(
            "SELECT original_filename FROM case_document_file WHERE id=:id"
        ), {"id": legacy_id}).scalar_one() == "legacy.pdf"
    command.downgrade(config, PARENT)
    command.upgrade(config, HEAD)
    with app.app_context():
        shipment = OperationalShipment.query.filter_by(public_id=fixture["shipment"]).one()
        legacy = db.session.get(CaseDocumentFile, legacy_id)
        prepared = contexts.prepare(shipment, "SHIPMENT", shipment.public_id, "INTERNAL", [])
        contexts.attach(shipment, legacy, fixture["owner"], prepared)
        db.session.commit()
        assert OperationalDocumentContext.query.count() == 1
        db.session.remove()
        db.engine.dispose()
    with pytest.raises(RuntimeError, match="P3-06 document facts exist"):
        command.downgrade(config, PARENT)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    engine.dispose()
