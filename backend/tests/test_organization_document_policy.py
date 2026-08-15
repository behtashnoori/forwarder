"""Organization document policy isolation, precedence, and snapshot certification."""
import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (CaseDocumentRequirement, Customer, DocumentDefinition, ExpertUser,
                            OrganizationDocumentRequirement, ShipmentRequest)
from backend.operational_models import OperationalMembership, OperationalOrganization, Project
from backend.project_configuration_models import ProjectDocumentRequirement
from backend.services.auth_session_service import create_session_tokens
from backend.services.case_document_service import initialize_requirements
from backend.services.organization_document_policy_service import effective_definitions


@pytest.fixture()
def policy_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                      "SECRET_KEY": "policy-test-secret"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        password = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode()
        org_a = OperationalOrganization(public_id="samand-tarabar", name="Samand Tarabar", is_active=True)
        org_b = OperationalOrganization(public_id="company-b", name="Company B", is_active=True)
        db.session.add_all([org_a, org_b]); db.session.flush()
        platform = ExpertUser(username="policy-platform", password_hash=password, full_name="Platform",
                              role="admin", authority="PLATFORM_ADMIN", is_active=True)
        admin_a = ExpertUser(username="policy-a", password_hash=password, full_name="Admin A",
                             role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        admin_b = ExpertUser(username="policy-b", password_hash=password, full_name="Admin B",
                             role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        db.session.add_all([platform, admin_a, admin_b]); db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=org_a.id, user_id=admin_a.id, is_active=True, permissions=[]),
            OperationalMembership(organization_id=org_b.id, user_id=admin_b.id, is_active=True, permissions=[]),
        ])
        definitions = [DocumentDefinition(code=f"d{i}", title=f"D{i}", is_required=i == 1,
            allowed_formats='["pdf"]', max_file_size_bytes=1000, max_active_file_count=1,
            applicability_scope="all", created_by=platform.id, updated_by=platform.id) for i in range(1, 4)]
        db.session.add_all(definitions); db.session.commit()
        tokens = {"platform": create_session_tokens(platform.id)["access_token"],
                  "a": create_session_tokens(admin_a.id)["access_token"],
                  "b": create_session_tokens(admin_b.id)["access_token"]}
        state = {"org_a": org_a.id, "org_b": org_b.id, "admin_a": admin_a.id,
                 "definitions": [row.public_id for row in definitions], "tokens": tokens}
    return app, state


def headers(state, actor):
    return {"Authorization": f"Bearer {state['tokens'][actor]}"}


def put(client, state, actor, definition, level, **extra):
    return client.put(f"/api/admin/organization-document-policy/{definition}",
        headers=headers(state, actor), json={"requirement_level": level, "is_active": level != "DISABLED", **extra})


def test_two_organization_policy_isolation_and_global_boundary(policy_app):
    app, state = policy_app; client = app.test_client(); d1, d2, d3 = state["definitions"]
    for definition, level in zip((d1, d2, d3), ("REQUIRED", "OPTIONAL", "DISABLED")):
        assert put(client, state, "a", definition, level).status_code == 200
    for definition, level in zip((d1, d2, d3), ("OPTIONAL", "REQUIRED", "CONDITIONAL")):
        assert put(client, state, "b", definition, level).status_code == 200
    a = client.get("/api/admin/organization-document-policy", headers=headers(state, "a")).get_json()
    b = client.get("/api/admin/organization-document-policy", headers=headers(state, "b")).get_json()
    assert [row["requirement_level"] for row in a["items"]] == ["REQUIRED", "OPTIONAL", "DISABLED"]
    assert [row["requirement_level"] for row in b["items"]] == ["OPTIONAL", "REQUIRED", "CONDITIONAL"]
    assert put(client, state, "a", d1, "REQUIRED", organization_id=state["org_b"]).status_code == 400
    assert client.get("/api/admin/organization-document-policy", headers=headers(state, "platform")).status_code == 403
    assert client.post("/api/admin/document-definitions", headers=headers(state, "a"), json={}).status_code == 403


def test_explicit_mode_fallback_and_immutable_snapshots(policy_app):
    app, state = policy_app; d1, d2, _ = state["definitions"]
    with app.app_context():
        assert [(row.code, level) for row, level in effective_definitions(state["org_a"], "domestic")] == [
            ("d1", "REQUIRED"), ("d2", "OPTIONAL"), ("d3", "OPTIONAL")]
    client = app.test_client()
    assert put(client, state, "a", d1, "OPTIONAL").status_code == 200
    with app.app_context():
        assert [(row.code, level) for row, level in effective_definitions(state["org_a"], "domestic")] == [("d1", "OPTIONAL")]
        old_case = ShipmentRequest(contact_phone="1", shipping_type="domestic", status="new",
            status_request_status="new", operational_organization_id=state["org_a"], ownership_scope="TENANT")
        db.session.add(old_case); db.session.flush(); initialize_requirements(old_case, state["admin_a"]); db.session.commit()
        assert CaseDocumentRequirement.query.filter_by(shipment_request_id=old_case.id).one().is_required is False
        old_case_id = old_case.id
    assert put(client, state, "a", d1, "REQUIRED").status_code == 200
    assert put(client, state, "b", d2, "REQUIRED").status_code == 200
    with app.app_context():
        assert CaseDocumentRequirement.query.filter_by(shipment_request_id=old_case_id).one().is_required is False
        new_a = ShipmentRequest(contact_phone="2", shipping_type="domestic", status="new", status_request_status="new",
            operational_organization_id=state["org_a"], ownership_scope="TENANT")
        new_b = ShipmentRequest(contact_phone="3", shipping_type="domestic", status="new", status_request_status="new",
            operational_organization_id=state["org_b"], ownership_scope="TENANT")
        db.session.add_all([new_a, new_b]); db.session.flush()
        initialize_requirements(new_a, state["admin_a"]); initialize_requirements(new_b, state["admin_a"]); db.session.commit()
        assert [(r.source_definition_code, r.is_required) for r in CaseDocumentRequirement.query.filter_by(shipment_request_id=new_a.id)] == [("d1", True)]
        assert [(r.source_definition_code, r.is_required) for r in CaseDocumentRequirement.query.filter_by(shipment_request_id=new_b.id)] == [("d2", True)]


def test_database_uniqueness_is_tenant_safe(policy_app):
    app, state = policy_app
    with app.app_context():
        definition = DocumentDefinition.query.filter_by(public_id=state["definitions"][0]).one()
        first = OrganizationDocumentRequirement(operational_organization_id=state["org_a"],
            document_definition_id=definition.id, requirement_level="REQUIRED", created_by=state["admin_a"], updated_by=state["admin_a"])
        duplicate = OrganizationDocumentRequirement(operational_organization_id=state["org_a"],
            document_definition_id=definition.id, requirement_level="OPTIONAL", created_by=state["admin_a"], updated_by=state["admin_a"])
        db.session.add(first); db.session.commit(); db.session.add(duplicate)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()


def test_project_override_wins_and_cannot_cross_organization(policy_app):
    app, state = policy_app; client = app.test_client(); d1 = state["definitions"][0]
    assert put(client, state, "a", d1, "REQUIRED").status_code == 200
    with app.app_context():
        definition = DocumentDefinition.query.filter_by(public_id=d1).one()
        customer = Customer(first_name="Project", last_name="Customer")
        db.session.add(customer); db.session.flush()
        project_a = Project(organization_id=state["org_a"], primary_customer_id=customer.id,
            project_code="A-PROJECT", created_by_user_id=state["admin_a"])
        project_b = Project(organization_id=state["org_b"], primary_customer_id=customer.id,
            project_code="B-PROJECT", created_by_user_id=state["admin_a"])
        db.session.add_all([project_a, project_b]); db.session.flush()
        db.session.add(ProjectDocumentRequirement(project_id=project_a.id,
            document_definition_id=definition.id, requirement_level="OPTIONAL",
            created_by=state["admin_a"], updated_by=state["admin_a"]))
        db.session.commit()
        assert [(row.code, level) for row, level in effective_definitions(
            state["org_a"], "domestic", project_a.id)] == [("d1", "OPTIONAL")]
        assert [(row.code, level) for row, level in effective_definitions(
            state["org_a"], "domestic", project_b.id)] == [("d1", "REQUIRED")]
