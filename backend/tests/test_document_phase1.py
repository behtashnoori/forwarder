"""The eight Phase 1 cases, with the same commands on SQLite and owned PG18."""
import io
import os
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import CaseDocumentFile, Customer, CustomerGamification, DocumentCatalogAuditEvent, DocumentDefinition, ExpertUser
from backend.operational_models import OperationalAudit, OperationalMembership, OperationalOrganization, OperationalShipment
from backend.services.auth_session_service import create_session_tokens
from backend.services.organization_document_policy_service import effective_definitions
from backend.tests.test_phase3_document_context import _as_customer

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
BASE = "/api/admin/organization-document-types"


@pytest.fixture()
def phase1(tmp_path):
    url = os.environ.get("DOCUMENT_PHASE1_POSTGRES_URL", "sqlite:///:memory:")
    if url != "sqlite:///:memory:":
        parsed = make_url(url)
        assert parsed.host == "127.0.0.1" and parsed.database.startswith("forwarder_document_phase1_")
        engine = sa.create_engine(url)
        with engine.connect() as connection:
            assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
        command.upgrade(alembic_config(url), "20261016_active_route_basis")
        # Preserve every pre-existing data column, including seeded generic types.
        # This disposable migration census must include protected rows as well;
        # use the existing read-only certification option on these SELECTs only.
        before = {}
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            for name in inspector.get_table_names():
                if name == "alembic_version":
                    continue
                table = sa.Table(name, sa.MetaData(), autoload_with=connection)
                statement = sa.select(table).execution_options(include_quarantined_for_certification=True)
                before[name] = (statement, sorted(repr(tuple(row)) for row in connection.execute(statement)))
        command.upgrade(alembic_config(url), "head")
        with engine.connect() as connection:
            for statement, records in before.values():
                assert sorted(repr(tuple(row)) for row in connection.execute(statement)) == records
        engine.dispose()
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": url,
                      "DOCUMENT_STORAGE_ROOT": str(tmp_path / "files"), "SECRET_KEY": "disposable-document-phase1"}, skip_startup=True)
    with app.app_context():
        if url == "sqlite:///:memory:":
            db.create_all()
        orgs = [OperationalOrganization(name=f"Document Phase1 {i}") for i in range(2)]
        db.session.add_all(orgs); db.session.flush()
        users = {}
        for name, authority, org in [("admin", "ORGANIZATION_ADMIN", 0), ("other_admin", "ORGANIZATION_ADMIN", 1),
                                     ("expert", "EXPERT", 0), ("other_expert", "EXPERT", 1), ("platform", "PLATFORM_ADMIN", 0)]:
            user = ExpertUser(username=f"phase1-{name}-{uuid4().hex[:8]}", full_name=name, password_hash="unused", authority=authority,
                              role="expert" if authority == "EXPERT" else "admin", is_active=True)
            db.session.add(user); db.session.flush()
            db.session.add(OperationalMembership(organization_id=orgs[org].id, user_id=user.id,
                permissions=["operational_shipment.read", "operational_shipment.close", "operational_shipment.create", "project_configuration.read"]))
            users[name] = user
        customer = Customer(company_name="Disposable", ownership_scope="TENANT", operational_organization_id=orgs[0].id)
        portal = CustomerGamification(email=f"{uuid4()}@example.test", phone="09120000001", operational_organization_id=orgs[0].id)
        db.session.add_all([customer, portal]); db.session.flush()
        shipment = OperationalShipment(organization_id=orgs[0].id, customer_id=customer.id, source_type="direct",
            lifecycle_status="planned", created_by_user_id=users["expert"].id, primary_responsible_expert_id=users["expert"].id)
        definition = DocumentDefinition(code=f"generic_{uuid4().hex}", title="Generic required", name_fa="مدرک پایه",
            allowed_formats='["pdf"]', max_file_size_bytes=1000, max_active_file_count=1, is_required=True)
        db.session.add_all([shipment, definition]); db.session.commit()
        state = {"shipment": shipment.public_id, "shipment_id": shipment.id, "org": orgs[0].id,
                 "foreign_org": orgs[1].id, "portal": portal.id, "expert_id": users["expert"].id,
                 "generic": definition.public_id,
                 "headers": {name: {"Authorization": f"Bearer {create_session_tokens(user.id)['access_token']}"} for name, user in users.items()}}
    yield app, state
    with app.app_context():
        db.session.remove(); db.engine.dispose()


def test_phase1_catalog_upload_persistence_deactivation_policy_closed_and_isolation(phase1):
    app, state = phase1; client = app.test_client(); headers = state["headers"]
    def mutate(path, body, actor="admin", method="post", key=None):
        return getattr(client, method)(path, json=body, headers={**headers[actor], "Idempotency-Key": key or str(uuid4())})
    with app.app_context():
        before = [(row.public_id, level) for row, level in effective_definitions(state["org"], "domestic")]
    key = str(uuid4()); payload = {"name_fa": "راهنامه CMR", "name_en": "CMR", "description": "نوع قابل تنظیم"}
    created = mutate(BASE, payload, key=key); assert created.status_code == 201, created.get_json()
    kind = created.get_json(); assert kind["ownership"] == "ORGANIZATION" and kind["is_active"]
    assert mutate(BASE, payload, key=key).get_json()["public_id"] == kind["public_id"]
    assert mutate(BASE, {**payload, "organization_id": state["foreign_org"]}).status_code == 400
    assert mutate(BASE, payload, actor="expert").status_code == 403
    assert mutate(BASE, payload, actor="platform").status_code == 403
    assert client.get(BASE, headers=headers["expert"]).status_code == 403
    _as_customer(client, state["portal"])
    assert client.post(BASE, json=payload).status_code in {401, 403}
    assert client.get(BASE).status_code in {401, 403}
    with app.app_context():
        assert [(row.public_id, level) for row, level in effective_definitions(state["org"], "domestic")] == before
        definition = DocumentDefinition.query.filter_by(public_id=kind["public_id"]).one()
        definition_id = definition.id
        assert DocumentCatalogAuditEvent.query.filter_by(definition_public_id=kind["public_id"]).count() == 1
    for path in (BASE, "/api/admin/organization-document-policy", "/api/admin/document-definitions", "/api/internal/project-configuration/document-definitions"):
        assert kind["public_id"] not in str(client.get(path, headers=headers["other_admin"]).get_json())
    assert client.get(f"/api/admin/document-definitions/{definition_id}", headers=headers["other_admin"]).status_code == 404
    assert mutate(f"{BASE}/{kind['public_id']}", {"is_active": False, "expected_revision": 1}, actor="other_admin", method="patch").status_code == 404
    assert client.put(f"/api/admin/organization-document-policy/{kind['public_id']}", json={"requirement_level": "REQUIRED"}, headers=headers["other_admin"]).status_code == 404
    assert mutate(f"{BASE}/{state['generic']}", {"is_active": False, "expected_revision": 1}, method="patch").status_code == 404
    path = f"/api/internal/operational-shipments/{state['shipment']}/documents"
    def upload(actor="expert", **extra):
        return client.post(path, headers={**headers[actor], "Idempotency-Key": str(uuid4())},
            data={"document_definition_public_id": kind["public_id"], "description": "یادداشت آزمایشی",
                  "file": (io.BytesIO(PDF), "cmr.pdf"), **extra})
    foreign_kind = mutate(BASE, payload, actor="other_admin").get_json()
    assert upload(document_definition_public_id=foreign_kind["public_id"]).status_code == 404
    assert any(row["public_id"] == kind["public_id"] for row in client.get(path, headers=headers["expert"]).get_json()["document_types"])
    uploaded = upload(); assert uploaded.status_code == 201, uploaded.get_json()
    doc = uploaded.get_json()["data"]
    assert doc["business_document_type"] == "راهنامه CMR"
    assert doc["filename"] == "cmr.pdf" and doc["actor"] == "expert" and doc["recorded_at"]
    assert doc["description"] == "یادداشت آزمایشی" and doc["document_definition_public_id"] == kind["public_id"]
    assert doc in client.get(path, headers=headers["expert"]).get_json()["data"]
    assert upload("other_expert").status_code == 404
    assert upload("admin").status_code == 404
    download = f"{path}/{doc['public_id']}/download"
    assert client.get(download, headers=headers["other_expert"]).status_code == 404
    assert client.get(f"/api/customer/documents/{doc['public_id']}/download").status_code == 404
    deactivated = mutate(f"{BASE}/{kind['public_id']}", {"is_active": False, "expected_revision": 1}, method="patch")
    assert deactivated.status_code == 200
    assert upload().status_code == 404
    listing = client.get(path, headers=headers["expert"]).get_json()
    assert kind["public_id"] not in str(listing["document_types"])
    assert listing["data"][0]["document_type_active"] is False
    assert client.get(download, headers=headers["expert"]).data == PDF
    with app.app_context():
        assert CaseDocumentFile.query.filter_by(operational_shipment_id=state["shipment_id"]).count() == 1
        event = OperationalAudit.query.filter_by(action="shipment_document.uploaded", entity_id=CaseDocumentFile.query.filter_by(public_id=doc["public_id"]).one().id).one()
        assert event.actor_user_id == state["expert_id"]
        assert event.metadata_json["document_definition_public_id"] == kind["public_id"]
    # Explicit policy alone controls required/optional semantics, after catalog creation.
    policy_path = f"/api/admin/organization-document-policy/{state['generic']}"
    for level in ("OPTIONAL", "REQUIRED"):
        assert client.put(policy_path, json={"requirement_level": level}, headers=headers["admin"]).status_code == 200
        with app.app_context():
            assert [(row.public_id, value) for row, value in effective_definitions(state["org"], "domestic")] == [(state["generic"], level)]


    # Close through the existing governed command, preserving its immutable decision.
    from backend.services import closure_service
    from backend.tests.test_phase3_closure import policy, command as close_command
    from backend.closure_models import ClosureDecision
    with app.app_context():
        app.config["phase1a"] = {"org": state["org"], "verifier": state["expert_id"]}
        policy(app)
        shipment = db.session.get(OperationalShipment, state["shipment_id"])
        shipment.lifecycle_status = "completed"; db.session.commit()
        decision, _ = closure_service.close(shipment.public_id, {"id": state["expert_id"], "role": "expert"}, close_command(shipment), str(uuid4()))
        db.session.commit(); frozen = decision.assessment
    assert mutate(f"{BASE}/{kind['public_id']}", {"is_active": True, "expected_revision": 2}, method="patch").status_code == 200
    denied = upload(); assert denied.status_code == 409 and denied.get_json()["code"] == "CLOSED_DOCUMENT_READONLY"
    repaired = upload(historical_repair="true"); assert repaired.status_code == 201, repaired.get_json()
    assert upload("admin", historical_repair="true").status_code == 404
    with app.app_context():
        assert ClosureDecision.query.filter_by(operational_shipment_id=state["shipment_id"]).one().assessment == frozen
        assert db.session.get(OperationalShipment, state["shipment_id"]).lifecycle_status == "closed"
    postgres_url = os.environ.get("DOCUMENT_PHASE1_POSTGRES_URL")
    if postgres_url:
        with pytest.raises(RuntimeError, match="ownership evidence exists"):
            command.downgrade(alembic_config(postgres_url), "20261016_active_route_basis")
