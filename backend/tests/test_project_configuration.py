from pathlib import Path
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.milestone_type_catalog import load_catalog, plan_catalog
from backend.models import Customer, DocumentDefinition, ExpertUser, ServiceType
from backend.logistics_network_models import ProjectLogisticsPoint
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    Project,
)
from backend.project_configuration_models import (
    MilestoneType,
    ProjectMilestoneDefinition,
    ProjectService,
)


@pytest.fixture()
def configured_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "config-test",
        }
    )
    with app.app_context():
        org = OperationalOrganization(name="Config Org")
        other = OperationalOrganization(name="Other Org")
        admin = ExpertUser(
            username="config-admin",
            password_hash="x",
            full_name="Admin",
            role="admin",
            is_active=True,
        )
        outsider = ExpertUser(
            username="config-other",
            password_hash="x",
            full_name="Other",
            role="admin",
            is_active=True,
        )
        manager = ExpertUser(username="config-manager", password_hash="x", full_name="Manager", role="admin", is_active=True)
        expert = ExpertUser(username="config-expert", password_hash="x", full_name="Expert", role="expert", is_active=True)
        readonly = ExpertUser(username="config-readonly", password_hash="x", full_name="Read only", role="expert", is_active=True)
        denied = ExpertUser(username="config-denied", password_hash="x", full_name="Denied", role="expert", is_active=True)
        customer = Customer(first_name="Config", last_name="Customer")
        db.session.add_all([org, other, admin, outsider, manager, expert, readonly, denied, customer])
        db.session.flush()
        permissions = [
            "project_configuration.read",
            "project_configuration.manage",
            "milestone_type.read",
            "milestone_type.manage",
        ]
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id, user_id=admin.id, permissions=permissions
                ),
                OperationalMembership(
                    organization_id=other.id,
                    user_id=outsider.id,
                    permissions=permissions,
                ),
                OperationalMembership(organization_id=org.id, user_id=manager.id, permissions=["project_configuration.read", "project_configuration.manage"]),
                OperationalMembership(organization_id=org.id, user_id=expert.id, permissions=["project_configuration.read", "project_configuration.manage"]),
                OperationalMembership(organization_id=org.id, user_id=readonly.id, permissions=["project_configuration.read"]),
                OperationalMembership(organization_id=org.id, user_id=denied.id, permissions=[]),
            ]
        )
        project = Project(
            organization_id=org.id,
            primary_customer_id=customer.id,
            project_code="CFG-1",
            tracking_code="opaque-config",
            created_by_user_id=admin.id,
        )
        service = ServiceType(
            immutable_code="FREIGHT", fa_name="حمل", en_name="Freight"
        )
        document = DocumentDefinition(
            code="BOL",
            title="بارنامه",
            allowed_formats='["pdf"]',
            max_file_size_bytes=1000,
        )
        milestone = MilestoneType(
            immutable_code="PICKUP",
            fa_name="جمع‌آوری",
            en_name="Pickup",
            display_order=1,
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.session.add_all([project, service, document, milestone])
        db.session.commit()
        yield (
            app,
            {
                "project": project.public_id,
                "service": service.public_id,
                "document": document.public_id,
                "milestone": milestone.public_id,
                "auth": {
                    "Authorization": f"Bearer {auth_manager.generate_tokens(admin.id)['access_token']}"
                },
                "other": {
                    "Authorization": f"Bearer {auth_manager.generate_tokens(outsider.id)['access_token']}"
                },
                "manager": {"Authorization": f"Bearer {auth_manager.generate_tokens(manager.id)['access_token']}"},
                "expert": {"Authorization": f"Bearer {auth_manager.generate_tokens(expert.id)['access_token']}"},
                "readonly": {"Authorization": f"Bearer {auth_manager.generate_tokens(readonly.id)['access_token']}"},
                "denied": {"Authorization": f"Bearer {auth_manager.generate_tokens(denied.id)['access_token']}"},
            },
        )
        db.session.remove()
        db.drop_all()


def test_identity_catalog_and_single_head(configured_app):
    app, ctx = configured_app
    with app.app_context():
        assert len(DocumentDefinition.query.one().public_id) == 36
        payload = load_catalog()
        assert len(payload["milestone_types"]) == 13
        assert plan_catalog(payload, "test")["created_count"] == 12
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    assert ScriptDirectory.from_config(config).get_heads() == [
        "20260831_document_catalog_metadata"
    ]


def test_same_project_point_constraint_metadata_matches_migration(configured_app):
    parent_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in ProjectLogisticsPoint.__table__.constraints
    }
    assert parent_constraints["uq_project_logistics_point_project_id_id"] == (
        "project_id",
        "id",
    )

    child_fks = {
        constraint.name: (
            tuple(column.name for column in constraint.columns),
            tuple(element.target_fullname for element in constraint.elements),
        )
        for constraint in ProjectMilestoneDefinition.__table__.foreign_key_constraints
    }
    assert child_fks["fk_project_milestone_definition_project_point"] == (
        ("project_id", "project_logistics_point_id"),
        ("project_logistics_point.project_id", "project_logistics_point.id"),
    )
    assert not any(
        targets == ("project_logistics_point.id",)
        for _, targets in child_fks.values()
    )


def test_opaque_crud_validation_and_tenant_isolation(configured_app):
    app, ctx = configured_app
    client = app.test_client()
    base = f"/api/v2/projects/{ctx['project']}/configuration"
    assert client.get(base + "/services").status_code == 401
    assert client.get(base + "/services", headers=ctx["other"]).status_code == 404
    created = client.post(
        base + "/services",
        headers=ctx["auth"],
        json={"service_type_public_id": ctx["service"], "is_primary": True},
    ).get_json()["item"]
    assert "id" not in created and created["service_type_public_id"] == ctx["service"]
    assert (
        client.post(
            base + "/services",
            headers=ctx["auth"],
            json={"service_type_public_id": ctx["service"]},
        ).status_code
        == 409
    )
    doc = client.post(
        base + "/document-requirements",
        headers=ctx["auth"],
        json={
            "document_definition_public_id": ctx["document"],
            "requirement_level": "CONDITIONAL",
        },
    )
    assert doc.status_code == 422
    doc = client.post(
        base + "/document-requirements",
        headers=ctx["auth"],
        json={
            "document_definition_public_id": ctx["document"],
            "requirement_level": "REQUIRED",
        },
    )
    assert (
        doc.status_code == 201
        and "document_definition_id" not in doc.get_json()["item"]
    )
    milestone = client.post(
        base + "/milestone-definitions",
        headers=ctx["auth"],
        json={
            "milestone_type_public_id": ctx["milestone"],
            "sequence": 1,
            "target_duration_value": 5,
            "warning_duration_value": 4,
            "duration_unit": "HOUR",
        },
    )
    assert milestone.status_code == 422
    milestone = client.post(
        base + "/milestone-definitions",
        headers=ctx["auth"],
        json={
            "milestone_type_public_id": ctx["milestone"],
            "sequence": 1,
            "target_duration_value": 5,
            "warning_duration_value": 6,
            "duration_unit": "HOUR",
        },
    )
    assert milestone.status_code == 201
    listed = client.get(base + "/milestone-definitions", headers=ctx["auth"])
    assert listed.status_code == 200
    assert len(listed.get_json()["items"]) == 1
    assert ProjectService.query.count() == 1


def test_bounded_lists_filters_sorts_and_selectors(configured_app):
    app, ctx = configured_app
    client = app.test_client()
    base = f"/api/v2/projects/{ctx['project']}/configuration/services"
    client.post(base, headers=ctx["auth"], json={"service_type_public_id": ctx["service"], "is_required": True})

    listed = client.get(base + "?page=1&per_page=1&required=true&sort=display_order&direction=desc", headers=ctx["auth"])
    assert listed.status_code == 200
    assert listed.get_json() | {"page": 1, "per_page": 1, "total": 1, "pages": 1} == listed.get_json()
    for query in ("?page=0", "?per_page=101", "?page=nope", "?active=maybe", "?sort=id", "?direction=sideways", "?required=maybe"):
        response = client.get(base + query, headers=ctx["auth"])
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "VALIDATION_FAILED"
    assert client.get(base + "?page=1&per_page=1", headers=ctx["other"]).status_code == 404

    for path in (
        "/api/internal/project-configuration/service-types",
        "/api/internal/project-configuration/document-definitions",
        "/api/internal/milestone-types",
        f"/api/v2/projects/{ctx['project']}/configuration/selectors/logistics-points",
    ):
        response = client.get(path + "?page=1&per_page=1", headers=ctx["auth"])
        assert response.status_code == 200
        body = response.get_json()
        assert {"items", "page", "per_page", "total", "pages"} <= set(body)
        assert all("id" not in item for item in body["items"])
    assert client.get("/api/internal/project-configuration/service-types?per_page=101", headers=ctx["auth"]).status_code == 400
    assert client.get(f"/api/v2/projects/{ctx['project']}/configuration/selectors/logistics-points", headers=ctx["other"]).status_code == 404


def test_selector_role_tenant_and_identity_matrix(configured_app):
    app, ctx = configured_app
    client = app.test_client()
    selectors = (
        "/api/internal/project-configuration/service-types",
        "/api/internal/project-configuration/document-definitions",
        "/api/internal/milestone-types",
        f"/api/v2/projects/{ctx['project']}/configuration/selectors/logistics-points",
    )
    for identity in ("auth", "manager", "expert", "readonly"):
        for path in selectors:
            response = client.get(path + "?page=1&per_page=25&q=", headers=ctx[identity])
            assert response.status_code == 200, (identity, path, response.get_json())
            body = response.get_json()
            assert {"items", "page", "per_page", "total", "pages"} <= body.keys()
            assert all("id" not in item and "public_id" in item for item in body["items"])
    for path in selectors:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=ctx["denied"]).status_code == 403
        for query in ("?page=0", "?per_page=101", "?page=bad", "?q=" + "x" * 161):
            response = client.get(path + query, headers=ctx["auth"])
            assert response.status_code == 400
            assert response.get_json()["error"]["code"] == "VALIDATION_FAILED"

    # Governed global selectors contain active catalog rows only; inactive rows
    # and internal numeric identities never leak through list or bounded search.
    with app.app_context():
        ServiceType.query.filter_by(public_id=ctx["service"]).one().is_active = False
        DocumentDefinition.query.filter_by(public_id=ctx["document"]).one().is_active = False
        MilestoneType.query.filter_by(public_id=ctx["milestone"]).one().is_active = False
        db.session.commit()
    for path, query in (
        (selectors[0], "FREIGHT"), (selectors[1], "BOL"), (selectors[2], "PICKUP")
    ):
        body = client.get(path + f"?q={query}", headers=ctx["auth"]).get_json()
        assert body["items"] == []

    # A foreign organization may read the shared governed catalogs with its own
    # permission, but a foreign Project selector is deliberately non-disclosing.
    for path in selectors[:3]:
        assert client.get(path, headers=ctx["other"]).status_code == 200
    assert client.get(selectors[3], headers=ctx["other"]).status_code == 404
