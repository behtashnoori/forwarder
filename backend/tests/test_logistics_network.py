from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.logistics_network_models import (
    LogisticsPointType,
    ProjectLogisticsPoint,
)
from backend.logistics_point_catalog import ALLOWED_CODES, load_catalog, plan_catalog
from backend.models import Country, Customer, ExpertUser
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    Project,
)
from backend.services.logistics_network_service import normalize_name


@pytest.fixture()
def network_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "network-test",
        }
    )
    with app.app_context():
        db.create_all()
        org = OperationalOrganization(name="Network Org")
        other = OperationalOrganization(name="Other Org")
        admin = ExpertUser(
            username="network-admin",
            password_hash="x",
            full_name="Admin",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        outsider = ExpertUser(
            username="network-other",
            password_hash="x",
            full_name="Other",
            role="admin",
            is_active=True,
        )
        customer = Customer(first_name="Project", last_name="Customer")
        country = Country(code="IR", name_en="Iran", name_fa="ایران")
        db.session.add_all([org, other, admin, outsider, customer, country])
        db.session.flush()
        permissions = [
            "logistics_point.read",
            "logistics_point.manage",
            "project_logistics_point.read",
            "project_logistics_point.manage",
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
            ]
        )
        project = Project(
            organization_id=org.id,
            primary_customer_id=customer.id,
            project_code="NET-1",
            tracking_code="opaque-network",
            created_by_user_id=admin.id,
        )
        point_type = LogisticsPointType(
            immutable_code="WAREHOUSE",
            fa_name="انبار",
            en_name="Warehouse",
            display_order=1,
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.session.add_all([project, point_type])
        db.session.commit()
        yield (
            app,
            {
                "project": project.public_id,
                "type": point_type.public_id,
                "auth": {
                    "Authorization": f"Bearer {auth_manager.generate_tokens(admin.id)['access_token']}"
                },
                "other_auth": {
                    "Authorization": f"Bearer {auth_manager.generate_tokens(outsider.id)['access_token']}"
                },
            },
        )
        db.session.remove()
        db.drop_all()


def _point(client, ctx, code, name, *, confirm=False, en_name=None):
    return client.post(
        "/api/admin/logistics-points",
        headers=ctx["auth"],
        json={
            "immutable_code": code,
            "point_type_public_id": ctx["type"],
            "fa_name": name,
            "en_name": en_name,
            "country_code": "IR",
            "short_address": "Tehran",
            "confirm_probable_duplicate": confirm,
        },
    )


def test_normalization_catalog_and_projections_are_bounded(network_app):
    assert normalize_name("  بندر\u200c  ۱۲ كیش ") == "بندر 12 کیش"
    payload = load_catalog()
    assert {row["code"] for row in payload["logistics_point_types"]} == ALLOWED_CODES
    with network_app[0].app_context():
        plan = plan_catalog(payload, "test")
        assert plan["created_count"] == 10 and plan["conflict_count"] == 1


def test_exact_duplicate_org_boundary_and_no_public_surface(network_app):
    app, ctx = network_app
    with app.test_client() as client:
        point_type = client.post(
            "/api/admin/logistics-point-types",
            headers=ctx["auth"],
            json={
                "immutable_code": "FACTORY",
                "fa_name": "کارخانه",
                "en_name": "Factory",
                "display_order": 2,
            },
        )
        assert (
            point_type.status_code == 201
            and point_type.get_json()["item"]["immutable_code"] == "FACTORY"
        )
        created = _point(client, ctx, "LP-001", "انبار مرکزی")
        assert created.status_code == 201
        item = created.get_json()["item"]
        assert "id" not in item and "organization_id" not in item
        duplicate = _point(client, ctx, "LP-002", "انبار\u200cمرکزی")
        assert (
            duplicate.status_code == 409
            and duplicate.get_json()["error"]["code"] == "EXACT_DUPLICATE"
        )
        assert (
            client.get(
                f"/api/admin/logistics-points/{item['public_id']}",
                headers=ctx["other_auth"],
            ).status_code
            == 404
        )
        assert client.get("/api/public/v2/logistics-points").status_code == 404


def test_tracking_selector_is_active_tenant_scoped_and_bounded(network_app):
    app, ctx = network_app
    with app.test_client() as client:
        same = _point(client, ctx, "TEH-WH-1", "انبار تهران", en_name="Tehran Warehouse").get_json()["item"]
        other = client.post(
            "/api/admin/logistics-points", headers=ctx["other_auth"],
            json={
                "immutable_code": "OTHER-WH-1", "point_type_public_id": ctx["type"],
                "fa_name": "انبار سازمان دیگر", "en_name": "Other Tenant Warehouse",
                "country_code": "IR",
            },
        )
        assert other.status_code == 201
        endpoint = "/api/internal/logistics-points/tracking-selector"
        result = client.get(endpoint, headers=ctx["auth"])
        assert result.status_code == 200
        assert [row["public_id"] for row in result.get_json()["items"]] == [same["public_id"]]
        assert client.get(endpoint + "?q=تهران", headers=ctx["auth"]).get_json()["items"]
        assert client.get(endpoint + "?q=Warehouse", headers=ctx["auth"]).get_json()["items"]
        assert client.get(endpoint + "?q=TEH-WH", headers=ctx["auth"]).get_json()["items"]
        assert client.get(endpoint + "?country_code=IR&type_code=WAREHOUSE&limit=1&offset=0", headers=ctx["auth"]).get_json()["items"]
        assert client.get(endpoint + "?organization_id=1", headers=ctx["auth"]).status_code == 403
        client.post(
            f"/api/admin/logistics-points/{same['public_id']}/deactivate",
            headers=ctx["auth"], json={"version": same["version"]},
        )
        assert client.get(endpoint, headers=ctx["auth"]).get_json()["items"] == []


def test_project_association_role_uniqueness_reorder_and_deactivation(network_app):
    app, ctx = network_app
    with app.test_client() as client:
        first = _point(client, ctx, "LP-101", "انبار اول").get_json()["item"]
        second = _point(client, ctx, "LP-102", "انبار دوم").get_json()["item"]
        url = f"/api/v2/projects/{ctx['project']}/logistics-points"
        a = client.post(
            url,
            headers=ctx["auth"],
            json={
                "logistics_point_public_id": first["public_id"],
                "project_role": "ORIGIN",
                "sequence_number": 1,
            },
        ).get_json()["item"]
        b = client.post(
            url,
            headers=ctx["auth"],
            json={
                "logistics_point_public_id": second["public_id"],
                "project_role": "DESTINATION",
                "sequence_number": 2,
            },
        ).get_json()["item"]
        reordered = client.post(
            url + "/reorder",
            headers=ctx["auth"],
            json={
                "items": [
                    {"public_id": b["public_id"], "version": b["version"]},
                    {"public_id": a["public_id"], "version": a["version"]},
                ]
            },
        )
        assert reordered.status_code == 200
        assert [row["sequence_number"] for row in reordered.get_json()["items"]] == [
            1,
            2,
        ]
        current_a = next(
            row
            for row in reordered.get_json()["items"]
            if row["public_id"] == a["public_id"]
        )
        removed = client.post(
            f"{url}/{a['public_id']}/deactivate",
            headers=ctx["auth"],
            json={"version": current_a["version"]},
        )
        assert (
            removed.status_code == 200
            and removed.get_json()["item"]["is_active"] is False
        )
        assert ProjectLogisticsPoint.query.count() == 2


def test_cross_tenant_and_unauthenticated_commands_are_non_disclosing(network_app):
    app, ctx = network_app
    with app.test_client() as client:
        point = _point(client, ctx, "LP-IDOR", "نقطه محرمانه").get_json()["item"]
        project_url = f"/api/v2/projects/{ctx['project']}/logistics-points"
        association = client.post(
            project_url,
            headers=ctx["auth"],
            json={
                "logistics_point_public_id": point["public_id"],
                "project_role": "ORIGIN",
                "sequence_number": 1,
            },
        ).get_json()["item"]

        detail_url = f"/api/admin/logistics-points/{point['public_id']}"
        lifecycle_url = detail_url + "/deactivate"
        association_url = f"{project_url}/{association['public_id']}"
        attempts = [
            client.get(detail_url, headers=ctx["other_auth"]),
            client.patch(
                detail_url,
                headers=ctx["other_auth"],
                json={"version": point["version"], "fa_name": "leak"},
            ),
            client.post(
                lifecycle_url,
                headers=ctx["other_auth"],
                json={"version": point["version"]},
            ),
            client.post(
                project_url,
                headers=ctx["other_auth"],
                json={
                    "logistics_point_public_id": point["public_id"],
                    "project_role": "DESTINATION",
                    "sequence_number": 2,
                },
            ),
            client.patch(
                association_url,
                headers=ctx["other_auth"],
                json={"version": association["version"], "sequence_number": 2},
            ),
            client.post(
                association_url + "/deactivate",
                headers=ctx["other_auth"],
                json={"version": association["version"]},
            ),
            client.post(
                association_url + "/activate",
                headers=ctx["other_auth"],
                json={"version": association["version"]},
            ),
        ]
        assert {response.status_code for response in attempts} == {404}
        assert {response.get_json()["error"]["code"] for response in attempts} == {
            "NOT_FOUND"
        }
        assert all(
            "organization" not in response.get_data(as_text=True).lower()
            for response in attempts
        )

        unauthenticated = client.get(detail_url)
        assert unauthenticated.status_code == 401
        assert point["public_id"] not in unauthenticated.get_data(as_text=True)


def test_logistics_migration_is_the_single_head():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260904_global_logistics_point_foundation"]
    assert (
        script.get_revision("20260810_logistics_network").down_revision
        == "20260809_cargo_catalog_items"
    )
