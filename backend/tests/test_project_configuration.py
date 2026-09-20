from pathlib import Path
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.milestone_type_catalog import load_catalog, plan_catalog
from backend.models import CargoType, Customer, DocumentDefinition, ExpertUser, ServiceType, UnitOfMeasure
from backend.cargo_models import (
    CargoCatalogItem,
    CargoItemAlias,
    ProjectCargoCatalogItem,
    ShipmentCargoItem,
)
from backend.logistics_network_models import ProjectLogisticsPoint
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
    ProjectAccess,
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
            authority="ORGANIZATION_ADMIN",
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
            "operational_shipment.read",
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
        foreign_project = Project(
            organization_id=other.id,
            primary_customer_id=customer.id,
            project_code="CFG-OTHER",
            tracking_code="opaque-config-other",
            created_by_user_id=outsider.id,
        )
        cargo_type = CargoType(
            immutable_code="CFG_CARGO", fa_name="نوع کالا", en_name="Cargo type"
        )
        uom = UnitOfMeasure(
            immutable_code="CFG_EA",
            fa_name="عدد",
            en_name="Each",
            symbol="ea",
            measurement_dimension="COUNT",
        )
        db.session.add_all([project, foreign_project, service, document, milestone, cargo_type, uom])
        db.session.flush()
        db.session.add_all([ProjectAccess(organization_id=org.id, project_id=project.id, user_id=user.id, created_by_user_id=admin.id) for user in (manager, expert, readonly)])
        preferred_catalog = CargoCatalogItem(
            organization_id=org.id,
            immutable_code="Z-PREFERRED",
            fa_name="کالای ترجیحی",
            en_name="Preferred gearbox",
            cargo_type=cargo_type,
            default_uom=uom,
            part_number="PART-42",
            customer_item_code="CUSTOMER-42",
            hs_code="HS-4242",
            brand="AcmeBrand",
            model="Model-X",
            created_by=admin.id,
            updated_by=admin.id,
        )
        fallback_catalog = CargoCatalogItem(
            organization_id=org.id,
            immutable_code="A-FALLBACK",
            fa_name="کالای عمومی",
            en_name="Fallback cargo",
            cargo_type=cargo_type,
            default_uom=uom,
            created_by=admin.id,
            updated_by=admin.id,
        )
        inactive_catalog = CargoCatalogItem(
            organization_id=org.id,
            immutable_code="INACTIVE-CARGO",
            fa_name="کالای غیرفعال",
            en_name="Inactive cargo",
            cargo_type=cargo_type,
            default_uom=uom,
            is_active=False,
            created_by=admin.id,
            updated_by=admin.id,
        )
        foreign_catalog = CargoCatalogItem(
            organization_id=other.id,
            immutable_code="FOREIGN-CARGO",
            fa_name="کالای خارجی",
            en_name="Foreign cargo",
            cargo_type=cargo_type,
            default_uom=uom,
            created_by=outsider.id,
            updated_by=outsider.id,
        )
        db.session.add_all([preferred_catalog, fallback_catalog, inactive_catalog, foreign_catalog])
        db.session.flush()
        db.session.add(CargoItemAlias(
            catalog_item_id=preferred_catalog.id,
            alias_text="Special Gear",
            normalized_alias="special gear",
            language="en",
            alias_type="COMMON_NAME",
            created_by=admin.id,
            updated_by=admin.id,
        ))
        db.session.commit()
        yield (
            app,
            {
                "project": project.public_id,
                "service": service.public_id,
                "document": document.public_id,
                "milestone": milestone.public_id,
                "foreign_project": foreign_project.public_id,
                "preferred_catalog": preferred_catalog.public_id,
                "fallback_catalog": fallback_catalog.public_id,
                "inactive_catalog": inactive_catalog.public_id,
                "foreign_catalog": foreign_catalog.public_id,
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
        "20260922_notification_foundation"
    ]
    migration = (
        root / "migrations" / "versions" / "20260911_project_cargo_preference.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision = "20260910_route_leg_logistics_points"' in migration
    assert "fk_project_cargo_item_project_same_org" in migration
    assert "fk_project_cargo_item_catalog_same_org" in migration
    assert "uq_project_cargo_catalog_item_pair" in migration
    assert "op.execute" not in migration and "bulk_insert" not in migration


def test_project_commodity_crud_lifecycle_order_and_tenant_integrity(configured_app):
    app, ctx = configured_app
    client = app.test_client()
    base = f"/api/v2/projects/{ctx['project']}/configuration/commodities"

    created_response = client.post(
        base,
        headers=ctx["auth"],
        json={
            "cargo_catalog_item_public_id": ctx["preferred_catalog"],
            "display_order": 7,
        },
    )
    assert created_response.status_code == 201
    created = created_response.get_json()["item"]
    assert created["cargo_catalog_item_public_id"] == ctx["preferred_catalog"]
    assert created["display_order"] == 7 and created["is_active"] is True
    assert client.post(
        base,
        headers=ctx["auth"],
        json={"cargo_catalog_item_public_id": ctx["preferred_catalog"]},
    ).status_code == 409
    assert client.post(
        base,
        headers=ctx["auth"],
        json={"cargo_catalog_item_public_id": ctx["foreign_catalog"]},
    ).status_code == 404
    assert client.get(base, headers=ctx["other"]).status_code == 404

    changed = client.patch(
        f"{base}/{created['public_id']}",
        headers=ctx["auth"],
        json={"display_order": 2, "version": created["version"]},
    ).get_json()["item"]
    assert changed["display_order"] == 2
    inactive = client.post(
        f"{base}/{created['public_id']}/deactivate",
        headers=ctx["auth"],
        json={"version": changed["version"]},
    ).get_json()["item"]
    assert inactive["is_active"] is False
    active = client.post(
        f"{base}/{created['public_id']}/activate",
        headers=ctx["auth"],
        json={"version": inactive["version"]},
    ).get_json()["item"]
    assert active["is_active"] is True
    inactive_again = client.post(
        f"{base}/{created['public_id']}/deactivate",
        headers=ctx["auth"],
        json={"version": active["version"]},
    ).get_json()["item"]
    with app.app_context():
        catalog = CargoCatalogItem.query.filter_by(
            public_id=ctx["preferred_catalog"]
        ).one()
        catalog.is_active = False
        catalog.version += 1
        db.session.commit()
    assert client.post(
        f"{base}/{created['public_id']}/activate",
        headers=ctx["auth"],
        json={"version": inactive_again["version"]},
    ).status_code == 422

    constraints = {
        constraint.name: (
            tuple(column.name for column in constraint.columns),
            tuple(element.target_fullname for element in constraint.elements),
        )
        for constraint in ProjectCargoCatalogItem.__table__.foreign_key_constraints
    }
    assert constraints["fk_project_cargo_item_project_same_org"] == (
        ("project_id", "organization_id"),
        ("project.id", "project.organization_id"),
    )
    assert constraints["fk_project_cargo_item_catalog_same_org"] == (
        ("cargo_catalog_item_id", "organization_id"),
        ("cargo_catalog_item.id", "cargo_catalog_item.organization_id"),
    )


def test_operational_options_rank_fallback_filter_search_and_validate_project(configured_app):
    app, ctx = configured_app
    client = app.test_client()
    project_options = f"/api/internal/cargo-options?project_public_id={ctx['project']}"

    before = client.get(project_options, headers=ctx["auth"])
    assert before.status_code == 200
    assert client.get(project_options, headers=ctx["manager"]).status_code == 200
    baseline_codes = [x["code"] for x in before.get_json()["catalog"]]
    assert set(baseline_codes) == {"A-FALLBACK", "Z-PREFERRED"}
    assert not any(x["preferred"] for x in before.get_json()["catalog"])

    created = client.post(
        f"/api/v2/projects/{ctx['project']}/configuration/commodities",
        headers=ctx["auth"],
        json={
            "cargo_catalog_item_public_id": ctx["preferred_catalog"],
            "display_order": 1,
        },
    ).get_json()["item"]
    ranked = client.get(project_options, headers=ctx["auth"]).get_json()["catalog"]
    assert [x["code"] for x in ranked] == ["Z-PREFERRED", "A-FALLBACK"]
    assert ranked[0]["preferred"] is True and ranked[1]["preferred"] is False
    assert "INACTIVE-CARGO" not in {x["code"] for x in ranked}

    for query in (
        "Preferred", "Special Gear", "PART-42", "CUSTOMER-42",
        "HS-4242", "AcmeBrand", "Model-X",
    ):
        searched = client.get(
            project_options + f"&q={query}", headers=ctx["auth"]
        ).get_json()["catalog"]
        assert [x["code"] for x in searched] == ["Z-PREFERRED"]

    assert client.get(
        f"/api/internal/cargo-options?project_public_id={ctx['foreign_project']}",
        headers=ctx["auth"],
    ).status_code == 404
    no_project = client.get("/api/internal/cargo-options", headers=ctx["auth"])
    assert [x["code"] for x in no_project.get_json()["catalog"]] == baseline_codes

    deactivated = client.post(
        f"/api/v2/projects/{ctx['project']}/configuration/commodities/{created['public_id']}/deactivate",
        headers=ctx["auth"],
        json={"version": created["version"]},
    )
    assert deactivated.status_code == 200
    after = client.get(project_options, headers=ctx["auth"]).get_json()["catalog"]
    assert not any(x["preferred"] for x in after)
    assert [x["code"] for x in after] == baseline_codes


def test_preference_and_catalog_changes_do_not_rewrite_shipment_snapshot(configured_app):
    app, ctx = configured_app
    with app.app_context():
        project = Project.query.filter_by(public_id=ctx["project"]).one()
        catalog = CargoCatalogItem.query.filter_by(public_id=ctx["preferred_catalog"]).one()
        user = ExpertUser.query.filter_by(username="config-admin").one()
        customer = Customer.query.one()
        shipment = OperationalShipment(
            organization_id=project.organization_id,
            project_id=project.id,
            source_type="direct",
            customer_id=customer.id,
            created_by_user_id=user.id,
        )
        db.session.add(shipment)
        db.session.flush()
        line = ShipmentCargoItem(
            operational_shipment_id=shipment.id,
            line_number=1,
            catalog_item_id=catalog.id,
            cargo_type_id=catalog.cargo_type_id,
            quantity=1,
            uom_id=catalog.default_uom_id,
            display_name_snapshot=catalog.fa_name,
            cargo_type_code_snapshot=catalog.cargo_type.immutable_code,
            cargo_type_fa_snapshot=catalog.cargo_type.fa_name,
            cargo_type_en_snapshot=catalog.cargo_type.en_name,
            uom_code_snapshot=catalog.default_uom.immutable_code,
            uom_symbol_snapshot=catalog.default_uom.symbol,
            part_number_snapshot=catalog.part_number,
            created_by=user.id,
            updated_by=user.id,
        )
        association = ProjectCargoCatalogItem(
            organization_id=project.organization_id,
            project_id=project.id,
            cargo_catalog_item_id=catalog.id,
            created_by=user.id,
            updated_by=user.id,
        )
        db.session.add_all([line, association])
        db.session.commit()
        original = (line.catalog_item_id, line.display_name_snapshot, line.part_number_snapshot)
        association.is_active = False
        association.display_order = 99
        association.version += 1
        catalog.fa_name = "نام جدید کاتالوگ"
        catalog.part_number = "PART-NEW"
        catalog.is_active = False
        catalog.version += 1
        db.session.commit()
        assert (line.catalog_item_id, line.display_name_snapshot, line.part_number_snapshot) == original


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
