"""Security freeze for explicit Project access without Shipment propagation."""
import pytest

from backend import create_app
from backend.analytics import service as analytics
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import Customer, ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment, Project
from backend.services import operational_service
from backend.services.project_access_authorization import authorized_project_scope

PERMISSIONS = ["project_configuration.read", "project_configuration.manage", "execution_unit.read", "operational_shipment.create_direct", "operational_shipment.read"]


@pytest.fixture()
def access_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "project-access"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        oa, ob = OperationalOrganization(name="A"), OperationalOrganization(name="B")
        ea = ExpertUser(username="project-ea", password_hash="x", full_name="EA", authority="EXPERT", is_active=True)
        eb = ExpertUser(username="project-eb", password_hash="x", full_name="EB", authority="EXPERT", is_active=True)
        aa = ExpertUser(username="project-aa", password_hash="x", full_name="AA", authority="ORGANIZATION_ADMIN", is_active=True)
        ab = ExpertUser(username="project-ab", password_hash="x", full_name="AB", authority="ORGANIZATION_ADMIN", is_active=True)
        platform = ExpertUser(username="project-platform", password_hash="x", full_name="Platform", authority="PLATFORM_ADMIN", is_active=True)
        inactive = ExpertUser(username="project-inactive", password_hash="x", full_name="Inactive", authority="EXPERT", is_active=False)
        customer = Customer(first_name="Project", last_name="Customer")
        db.session.add_all([oa, ob, ea, eb, aa, ab, platform, inactive, customer]); db.session.flush()
        for user, org, active in ((ea, oa, True), (eb, oa, True), (aa, oa, True), (ab, ob, True), (platform, oa, True), (inactive, oa, False)):
            db.session.add(OperationalMembership(organization_id=org.id, user_id=user.id, is_active=active, permissions=PERMISSIONS))
        a1 = Project(organization_id=oa.id, primary_customer_id=customer.id, project_code="A1", created_by_user_id=aa.id)
        a2 = Project(organization_id=oa.id, primary_customer_id=customer.id, project_code="A2", created_by_user_id=aa.id)
        b1 = Project(organization_id=ob.id, primary_customer_id=customer.id, project_code="B1", created_by_user_id=ab.id)
        db.session.add_all([a1, a2, b1]); db.session.flush()
        shipment = OperationalShipment(public_id="00000000-0000-0000-0000-000000000011", organization_id=oa.id, project_id=a1.id, source_type="direct", customer_id=customer.id, lifecycle_status="planned", created_by_user_id=eb.id, primary_responsible_expert_id=eb.id)
        db.session.add(shipment); db.session.commit()
        users = {k: v for k, v in (("ea", ea), ("eb", eb), ("aa", aa), ("ab", ab), ("platform", platform), ("inactive", inactive))}
        def headers(key): return {"Authorization": f"Bearer {auth_manager.generate_tokens(users[key].id)['access_token']}"}
        yield app, {"users": users, "headers": headers, "a1": a1, "a2": a2, "b1": b1, "shipment": shipment}
        db.session.remove(); db.drop_all()


def _visible(user):
    return {row.public_id for row in db.session.scalars(db.select(Project).where(authorized_project_scope({"id": user.id}))).all()}


def test_assignment_management_scope_revocation_and_tenancy(access_app):
    app, x = access_app; client = app.test_client(); h = x["headers"]
    created = client.post(f"/api/v2/projects/{x['a1'].public_id}/access", headers=h("aa"), json={"username": x["users"]["ea"].username})
    assert created.status_code == 201
    assignment = created.json["data"]["public_id"]
    assert _visible(x["users"]["ea"]) == {x["a1"].public_id}
    assert client.post(f"/api/v2/projects/{x['b1'].public_id}/access", headers=h("aa"), json={"username": x["users"]["ea"].username}).status_code == 404
    assert client.post(f"/api/v2/projects/{x['a1'].public_id}/access", headers=h("aa"), json={"username": x["users"]["ab"].username}).status_code == 404
    assert client.post(f"/api/v2/projects/{x['a1'].public_id}/access", headers=h("aa"), json={"username": x["users"]["inactive"].username}).status_code == 404
    assert client.post(f"/api/v2/projects/{x['a1'].public_id}/access", headers=h("ea"), json={"username": x["users"]["ea"].username}).status_code == 403
    assert client.post(f"/api/v2/projects/{x['a1'].public_id}/access", headers=h("platform"), json={"username": x["users"]["ea"].username}).status_code == 403
    assert client.post(f"/api/v2/projects/{x['a1'].public_id}/access", headers=h("aa"), json={"username": x["users"]["ea"].username}).status_code == 409
    assert client.delete(f"/api/v2/projects/{x['a1'].public_id}/access/{assignment}", headers=h("aa")).status_code == 200
    assert _visible(x["users"]["ea"]) == set()


def test_actor_matrix_selector_detail_and_client_spoof(access_app):
    app, x = access_app; client = app.test_client(); h = x["headers"]
    for project, username in ((x["a1"], "project-ea"), (x["a2"], "project-eb")):
        assert client.post(f"/api/v2/projects/{project.public_id}/access", headers=h("aa"), json={"username": username}).status_code == 201
    assert _visible(x["users"]["ea"]) == {x["a1"].public_id}
    assert _visible(x["users"]["eb"]) == {x["a2"].public_id}
    assert _visible(x["users"]["aa"]) == {x["a1"].public_id, x["a2"].public_id}
    assert _visible(x["users"]["ab"]) == {x["b1"].public_id}
    assert _visible(x["users"]["platform"]) == set()
    selector = client.get("/api/operations/selectors/projects?organization_id=999&user_id=999", headers=h("ea"))
    assert [row["public_id"] for row in selector.json["items"]] == [x["a1"].public_id]
    assert client.get(f"/api/v2/projects/{x['a1'].public_id}/execution-units", headers=h("ea")).status_code == 200
    assert client.get(f"/api/v2/projects/{x['a2'].public_id}/execution-units", headers=h("ea")).status_code == 404
    assert client.get(f"/api/v2/projects/{x['b1'].public_id}/execution-units", headers=h("ea")).status_code == 404


def test_project_access_propagates_shipment_and_analytics_read_scope(access_app):
    app, x = access_app; client = app.test_client(); h = x["headers"]
    assert client.post(f"/api/v2/projects/{x['a1'].public_id}/access", headers=h("aa"), json={"username": "project-ea"}).status_code == 201
    assert client.get(f"/api/operational-shipments/{x['shipment'].public_id}", headers=h("ea")).status_code == 200
    result = analytics.query({"metrics": ["SHIPMENT_COUNT"], "filters": [{"dimension": "PROJECT", "value": x["a1"].public_id}]}, {"id": x["users"]["ea"].id})
    assert result["rows"][0]["SHIPMENT_COUNT"]["value"] == 1
    admin = analytics.query({"metrics": ["SHIPMENT_COUNT"]}, {"id": x["users"]["aa"].id})
    assert admin["rows"][0]["SHIPMENT_COUNT"]["value"] == 1
