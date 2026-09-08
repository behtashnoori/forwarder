"""P0 freeze: Semantic Analytics never exceeds canonical Shipment access."""
from datetime import datetime, timedelta, timezone

import pytest

from backend import dashboard_service, saved_view_service
from backend.analytics import service as analytics
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalShipment, Project
from backend.services import operational_service
from backend.services.operational_service import OperationalError
from backend.tests.test_operational_vertical_slice import (
    _direct_payload,
    _payload,
    _user,
    operational_app,
)


def _value(result, metric="SHIPMENT_COUNT"):
    return sum((row.get(metric, {}).get("value") or 0) for row in result["rows"])


def _query(user, **extra):
    return analytics.query({"metrics": ["SHIPMENT_COUNT"], **extra}, user)


def _saved_view_definition():
    return {
        "schema_version": "saved-view-definition-v1",
        "semantic_version": "analytics-semantic-v1",
        "surface": "OPERATIONAL_SHIPMENTS",
        "query_definition": {
            "metric_keys": ["SHIPMENT_COUNT"], "dimension_keys": [],
            "filters": [{"dimension": "SHIPMENT_STATUS", "value": "planned"}],
            "time_dimension": "created", "limit": 20,
        },
        "presentation": {
            "columns": ["CUSTOMER"],
            "sort": {"field": "PLANNED_DEPARTURE", "direction": "ASC"},
            "display_type": "LIST", "limit": 20,
        },
    }


@pytest.fixture()
def security_population(operational_app):
    with operational_app.app_context():
        ids = operational_app.config["phase1a"]
        peer = ExpertUser(username="analytics-peer", password_hash="x", full_name="Peer", authority="EXPERT", is_active=True)
        platform = ExpertUser(username="analytics-platform", password_hash="x", full_name="Platform", authority="PLATFORM_ADMIN", is_active=True)
        no_permission = ExpertUser(username="analytics-no-permission", password_hash="x", full_name="No Permission", authority="EXPERT", is_active=True)
        db.session.add_all([peer, platform, no_permission]); db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=ids["org"], user_id=peer.id, permissions=["operational_shipment.read"]),
            OperationalMembership(organization_id=ids["org"], user_id=platform.id, permissions=["operational_shipment.read"]),
            OperationalMembership(organization_id=ids["org"], user_id=no_permission.id, permissions=[]),
        ])
        request_shipment, _ = operational_service.create_from_accepted_quote(_payload(operational_app), _user(operational_app), "analytics-request")
        direct_shipment, _ = operational_service.create_direct(_direct_payload(operational_app), _user(operational_app), "analytics-direct")
        peer_shipment = OperationalShipment(
            public_id="analytics-peer-shipment", organization_id=ids["org"], source_type="direct",
            customer_id=ids["customer"], lifecycle_status="planned", created_by_user_id=peer.id,
            primary_responsible_expert_id=peer.id,
        )
        foreign_shipment = OperationalShipment(
            public_id="analytics-foreign-shipment", organization_id=ids["other_org"], source_type="direct",
            customer_id=ids["customer"], lifecycle_status="planned", created_by_user_id=ids["outsider"],
            primary_responsible_expert_id=ids["outsider"],
        )
        project = Project(
            organization_id=ids["org"], primary_customer_id=ids["customer"], project_code="ANALYTICS-P0",
            created_by_user_id=ids["user"],
        )
        db.session.add_all([peer_shipment, foreign_shipment, project]); db.session.flush()
        request_shipment.project_id = direct_shipment.project_id = peer_shipment.project_id = project.id
        db.session.commit()
        yield {
            "expert": {"id": ids["user"]}, "peer": {"id": peer.id},
            "admin": {"id": ids["verifier"]}, "platform": {"id": platform.id},
            "no_permission": {"id": no_permission.id}, "project": project.public_id,
            "expert_ids": {request_shipment.public_id, direct_shipment.public_id},
            "peer_id": peer_shipment.public_id, "foreign_id": foreign_shipment.public_id,
        }


def test_cross_assignment_aggregate_filters_dimensions_and_parity(security_population):
    p = security_population
    for actor, expected in ((p["expert"], p["expert_ids"]), (p["peer"], {p["peer_id"]}), (p["admin"], p["expert_ids"] | {p["peer_id"]})):
        result = _query(actor, dimensions=["SHIPMENT_STATUS"])
        detail = analytics.drilldown("SHIPMENT_COUNT", actor, {})
        identities = {item["shipment_public_id"] for item in detail["items"]}
        assert _value(result) == len(expected) == len(identities)
        assert identities == expected
        assert p["foreign_id"] not in identities

    status = _query(p["expert"], filters=[{"dimension": "SHIPMENT_STATUS", "value": "planned"}])
    project = _query(p["expert"], filters=[{"dimension": "PROJECT", "value": p["project"]}])
    now = datetime.now(timezone.utc)
    time = _query(p["expert"], filters=[{"dimension": "TIME", "value": {"from": (now - timedelta(days=1)).isoformat(), "to": (now + timedelta(days=1)).isoformat()}}])
    assert _value(status) == _value(project) == _value(time) == 2


def test_platform_permission_and_client_authority_are_fail_closed(security_population):
    p = security_population
    assert _value(_query(p["platform"])) == 0
    with pytest.raises(OperationalError) as denied:
        _query(p["no_permission"])
    assert denied.value.status == 403
    spoofed = analytics.query({"metrics": ["SHIPMENT_COUNT"], "organization_id": 999, "user_id": p["peer"]["id"]}, p["expert"])
    assert _value(spoofed) == 2


def test_get_and_post_drilldown_use_authenticated_business_scope(operational_app, security_population):
    p = security_population
    with operational_app.app_context():
        token = auth_manager.generate_tokens(p["expert"]["id"])["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client = operational_app.test_client()
    get_response = client.get("/api/v2/analytics/drilldown/SHIPMENT_COUNT?organization_id=999&user_id=999", headers=headers)
    post_response = client.post("/api/v2/analytics/drilldown/SHIPMENT_COUNT", json={"metrics": ["SHIPMENT_COUNT"], "organization_id": 999, "user_id": p["peer"]["id"]}, headers=headers)
    expected = p["expert_ids"]
    for response in (get_response, post_response):
        assert response.status_code == 200
        assert {item["shipment_public_id"] for item in response.json["data"]["items"]} == expected


def test_dashboard_and_saved_view_runtime_cannot_expand_scope(security_population):
    p = security_population
    membership = OperationalMembership.query.filter_by(user_id=p["expert"]["id"]).one()
    membership.permissions = sorted(set(membership.permissions or []) | {"personal_dashboard.read", "personal_dashboard.manage"})
    db.session.commit()
    dashboard_service.clone("operations-control-tower", p["expert"])
    assert _value(_query(p["expert"])) == 2
    saved = saved_view_service.create({"name": "P0", "definition": _saved_view_definition()}, p["expert"])
    query = saved["definition"]["query_definition"]
    result = analytics.query({
        "metrics": query["metric_keys"], "dimensions": query["dimension_keys"],
        "filters": query["filters"], "time_dimension": query["time_dimension"], "limit": query["limit"],
    }, p["expert"])
    assert _value(result) == 2
