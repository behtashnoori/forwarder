"""Analytics v1 contracts: registry governance and Step 3-safe aggregation."""
from datetime import datetime, timedelta, timezone
import pytest
from backend.extensions import db
from backend.analytics import service
from backend.analytics.registry import DIMENSIONS, METRICS
from backend.operational_models import MilestoneEvent, OperationalMembership, RoutePlan
from backend.services import route_orchestration_service as routes
from backend.tests.test_execution_authority_3a import setup, report
from backend.tests.test_operational_vertical_slice import operational_app, _user, _auth

def query(app, metrics, dimensions=(), filters=()):
    return service.query({"metrics": list(metrics), "dimensions": list(dimensions), "filters": list(filters)}, _user(app))

def value(result, key):
    return sum((row.get(key, {}).get("value") or 0) for row in result["rows"])

def test_registry_is_versioned_unique_and_rejects_undefined_metrics(operational_app):
    with operational_app.app_context():
        registry = service.semantic_registry(_user(operational_app))
        assert registry["semantic_version"] == "analytics-semantic-v1"
        assert len(METRICS) == len(set(METRICS)) and len(DIMENSIONS) == len(set(DIMENSIONS))
        assert METRICS["LEAD_TIME"]["readiness"] == "BUSINESS_DEFINITION_REQUIRED"
        with pytest.raises(Exception, match="not executable"):
            query(operational_app, ["LEAD_TIME"])

def test_dashboard_only_user_can_discover_registry_but_cannot_query(operational_app):
    with operational_app.app_context():
        actor = _user(operational_app)
        membership = OperationalMembership.query.filter_by(user_id=actor["id"]).one()
        membership.permissions = ["personal_dashboard.read", "personal_dashboard.manage"]
        db.session.commit()
        assert service.semantic_registry(actor)["semantic_version"] == "analytics-semantic-v1"
        with pytest.raises(service.OperationalError) as denied:
            service.query({"metrics": ["SHIPMENT_COUNT"]}, actor)
        assert denied.value.status == 403

def test_counts_correction_verification_and_replan_are_lineage_safe(operational_app):
    from backend.services import operational_execution_service as execution
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        occurred = datetime.now(timezone.utc) - timedelta(hours=2)
        original = report(operational_app, shipment, milestones["departure"], occurred, "dep")
        execution.verify_event(shipment.public_id, original.public_id, {}, _user(operational_app, "verifier"))
        active = db.session.get(RoutePlan, leg.route_plan_id)
        routes.replan(shipment.id, active.id, {"expected_version": active.version, "reason": "retain"}, _user(operational_app), "analytics-replan")
        corrected = execution.correct_event(shipment.public_id, original.public_id, {"expected_version": milestones["departure"].version, "effective_at": (occurred + timedelta(minutes=3)).isoformat(), "reason": "clock"}, _user(operational_app))
        result = query(operational_app, ["RAW_EVENT_COUNT", "EFFECTIVE_BUSINESS_OCCURRENCE_COUNT", "REPLAN_COUNT"])
        assert value(result, "RAW_EVENT_COUNT") == 3
        assert value(result, "EFFECTIVE_BUSINESS_OCCURRENCE_COUNT") == 1
        assert value(result, "REPLAN_COUNT") == 1
        assert corrected.supersedes_event_id == original.id

def test_active_leg_metrics_and_null_duration_are_distinct(operational_app):
    with operational_app.app_context():
        shipment, _leg, _milestones = setup(operational_app)
        result = query(operational_app, ["SHIPMENT_COUNT", "ROUTE_LEG_COUNT", "LEG_TRANSIT_TIME"])
        assert value(result, "SHIPMENT_COUNT") == 1 and value(result, "ROUTE_LEG_COUNT") == 1
        unknown = [r for r in result["rows"] if r.get("LEG_TRANSIT_TIME", {}).get("state") == "NULL_UNKNOWN"]
        assert unknown
        coverage = {r["coverage_key"]: r for r in result["coverage"]}
        assert coverage["COMPLETED_LEGS_WITH_ACTUAL_TIMES_COVERAGE"]["state"] == "NOT_APPLICABLE"

def test_tenant_scope_project_filter_and_unsupported_semantic_join(operational_app):
    with operational_app.app_context():
        shipment, _leg, _milestones = setup(operational_app)
        assert value(query(operational_app, ["SHIPMENT_COUNT"], filters=[{"dimension": "SHIPMENT_STATUS", "value": "planned"}]), "SHIPMENT_COUNT") == 1
        with pytest.raises(Exception, match="cannot be combined"):
            query(operational_app, ["ROUTE_LEG_COUNT"], ["COMMODITY"])
        with pytest.raises(Exception, match="outside the analytics tenant"):
            query(operational_app, ["SHIPMENT_COUNT"], filters=[{"dimension": "PROJECT", "value": "foreign-project"}])

def test_read_only_http_contract_exposes_registry_and_hides_sql(operational_app):
    with operational_app.app_context():
        setup(operational_app)
    client = operational_app.test_client()
    registry = client.get("/api/v2/analytics/semantic-registry", headers=_auth(operational_app, "user"))
    assert registry.status_code == 200 and registry.json["data"]["semantic_version"] == "analytics-semantic-v1"
    response = client.post("/api/v2/analytics/query", json={"metrics": ["SHIPMENT_COUNT"]}, headers=_auth(operational_app, "user"))
    assert response.status_code == 200 and "sql" not in str(response.json).lower()

def test_registry_contract_is_enforced_for_filters_and_time_grain(operational_app):
    with operational_app.app_context():
        setup(operational_app)
        result = service.query({"metrics": ["SHIPMENT_COUNT"], "dimensions": ["TIME"], "time_grain": "month"}, _user(operational_app))
        assert result["rows"] and result["normalized_query"]["time_grain"] == "month"
        with pytest.raises(Exception, match="cannot be filtered"):
            service.query({"metrics": ["SHIPMENT_COUNT"], "filters": [{"dimension": "TRANSPORT_MODE", "value": "road"}]}, _user(operational_app))
        with pytest.raises(Exception, match="Unsupported time grain"):
            service.query({"metrics": ["SHIPMENT_COUNT"], "dimensions": ["TIME"], "time_grain": "century"}, _user(operational_app))

def test_drilldown_reuses_metric_population_and_is_bounded(operational_app):
    with operational_app.app_context():
        shipment, _leg, _milestones = setup(operational_app)
        detail = service.drilldown("PLANNED_SHIPMENT_COUNT", _user(operational_app), {}, 1)
        assert detail["items"] == [{"shipment_public_id": shipment.public_id}]
        assert detail["pagination"]["limit"] == 1

def test_post_drilldown_carries_normalized_filters_and_segment(operational_app):
    with operational_app.app_context():
        shipment, leg, _milestones = setup(operational_app)
        client = operational_app.test_client()
        response = client.post(
            "/api/v2/analytics/drilldown/SHIPMENT_COUNT",
            json={"metrics": ["SHIPMENT_COUNT"], "dimensions": ["SHIPMENT_STATUS"], "filters": [], "segment": {"dimension": "SHIPMENT_STATUS", "value": "planned"}, "limit": 1},
            headers=_auth(operational_app, "user"),
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["items"] == [{"shipment_public_id": shipment.public_id}]
        assert data["normalized_query"]["filters"] == [{"dimension": "SHIPMENT_STATUS", "value": "planned"}]

        legs = client.post(
            "/api/v2/analytics/drilldown/ROUTE_LEG_COUNT",
            json={"metrics": ["ROUTE_LEG_COUNT"], "dimensions": ["LEG_STATUS"], "segment": {"dimension": "LEG_STATUS", "value": leg.status}},
            headers=_auth(operational_app, "user"),
        )
        assert legs.status_code == 200
        assert legs.json["data"]["items"] == [{"route_leg_id": leg.id, "shipment_public_id": shipment.public_id}]

def test_legacy_get_ignores_a_json_body(operational_app):
    with operational_app.app_context():
        setup(operational_app)
    response = operational_app.test_client().get(
        "/api/v2/analytics/drilldown/SHIPMENT_COUNT",
        json={"filters": [{"dimension": "SHIPMENT_STATUS", "value": "cancelled"}]},
        headers=_auth(operational_app, "user"),
    )
    assert response.status_code == 200
    assert response.json["data"]["normalized_query"]["filters"] == []
