"""Project-to-Shipment visibility propagation is additive and read-only."""
from backend.auth import auth_manager
from backend.extensions import db
from backend.operational_models import OperationalShipment, ProjectAccess
from backend.analytics import service as analytics
from backend.services.assigned_work_authorization import assigned_shipment_scope, authorize_work_action
from backend.tests.test_project_access_foundation import access_app


def _ids(user):
    return {row.public_id for row in db.session.scalars(db.select(OperationalShipment).where(assigned_shipment_scope({"id": user.id}))).all()}


def test_project_visibility_union_and_immediate_revocation(access_app):
    _app, x = access_app
    ea, eb, admin = x["users"]["ea"], x["users"]["eb"], x["users"]["aa"]
    project = x["a1"]
    direct = OperationalShipment(public_id="direct-project-both", organization_id=project.organization_id, project_id=project.id, source_type="direct", customer_id=x["shipment"].customer_id, lifecycle_status="planned", created_by_user_id=ea.id, primary_responsible_expert_id=ea.id)
    project_only = x["shipment"]
    projectless = OperationalShipment(public_id="direct-projectless", organization_id=project.organization_id, source_type="direct", customer_id=x["shipment"].customer_id, lifecycle_status="planned", created_by_user_id=ea.id, primary_responsible_expert_id=ea.id)
    foreign = OperationalShipment(public_id="foreign-project-shipment", organization_id=x["b1"].organization_id, project_id=x["b1"].id, source_type="direct", customer_id=x["shipment"].customer_id, lifecycle_status="planned", created_by_user_id=eb.id, primary_responsible_expert_id=eb.id)
    db.session.add_all([direct, projectless, foreign]); db.session.flush()
    grant = ProjectAccess(organization_id=project.organization_id, project_id=project.id, user_id=ea.id, created_by_user_id=admin.id)
    db.session.add(grant); db.session.commit()
    future_project_shipment = OperationalShipment(public_id="future-project-shipment", organization_id=project.organization_id, project_id=project.id, source_type="direct", customer_id=x["shipment"].customer_id, lifecycle_status="planned", created_by_user_id=eb.id, primary_responsible_expert_id=eb.id)
    db.session.add(future_project_shipment); db.session.commit()
    assert {project_only.public_id, direct.public_id, projectless.public_id, future_project_shipment.public_id}.issubset(_ids(ea))
    assert foreign.public_id not in _ids(ea)
    assert authorize_work_action({"id": ea.id}, project_only, "shipment.read").allowed
    assert project_only.primary_responsible_expert_id == eb.id
    db.session.delete(grant); db.session.commit()
    visible = _ids(ea)
    assert {project_only.public_id, future_project_shipment.public_id, foreign.public_id}.isdisjoint(visible)
    assert {direct.public_id, projectless.public_id}.issubset(visible)
    assert not authorize_work_action({"id": ea.id}, project_only, "execution.read").allowed


def test_project_propagation_uses_operational_and_analytics_read_paths(access_app):
    app, x = access_app
    client = app.test_client()
    ea, admin, platform = x["users"]["ea"], x["users"]["aa"], x["users"]["platform"]
    db.session.add(ProjectAccess(organization_id=x["a1"].organization_id, project_id=x["a1"].id, user_id=ea.id, created_by_user_id=admin.id)); db.session.commit()
    query = analytics.query({"metrics": ["SHIPMENT_COUNT"]}, {"id": ea.id})
    detail = analytics.drilldown("SHIPMENT_COUNT", {"id": ea.id}, {})
    identities = {row["shipment_public_id"] for row in detail["items"]}
    assert x["shipment"].public_id in identities
    assert query["rows"][0]["SHIPMENT_COUNT"]["value"] == len(identities)
    headers = {"Authorization": f"Bearer {auth_manager.generate_tokens(ea.id)['access_token']}"}
    assert client.get(f"/api/operational-shipments/{x['shipment'].public_id}", headers=headers).status_code == 200
    get_response = client.get("/api/v2/analytics/drilldown/SHIPMENT_COUNT", headers=headers)
    post_response = client.post("/api/v2/analytics/drilldown/SHIPMENT_COUNT", json={"filters": [{"dimension": "PROJECT", "value": x["a1"].public_id}]}, headers=headers)
    for response in (get_response, post_response):
        assert response.status_code == 200
        assert {row["shipment_public_id"] for row in response.json["data"]["items"]} == identities
    assert x["shipment"].public_id in _ids(admin)
    assert _ids(platform) == set()
