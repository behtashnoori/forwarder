"""P3-10 reference history, explicit plan use and fail-closed authority."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pathlib import Path
import re
import yaml
import pytest
from backend.extensions import db
from backend.models import ExpertUser, CustomerGamification
from backend.operational_models import RouteLeg, RoutePlan, OrganizationSlaRule, OperationalShipment
from backend.route_time_models import OrganizationRouteTime as Reference, OrganizationRouteTimeVersion as Version, RouteLegTimeBasis as Basis
from backend.services import route_time_service as svc, operational_service as operations, route_orchestration_service as routes
from backend.tests.test_operational_vertical_slice import operational_app, _user, _payload, _auth


def payload(app, **changes):
    ids = app.config["phase1a"]
    return {"origin": {"source_type": "province", "source_id": ids["origin"]},
        "destination": {"source_type": "province", "source_id": ids["destination"]}, "transport_mode": "road",
        "movement_min_minutes": 1200, "movement_max_minutes": 1440, "stop_min_minutes": 240, "stop_max_minutes": 480,
        "effective_from": (datetime.now(timezone.utc)-timedelta(days=1)).isoformat(), **changes}


def save(app, values=None, reference=None, key=None):
    row, created = svc.save(_user(app, "verifier"), values or payload(app), key or str(uuid4()), reference)
    db.session.commit()
    return row, created


def draft(app):
    source = _payload(app)
    shipment, _ = operations.create_from_accepted_quote(source, _user(app), str(uuid4()))
    plan = routes.create_plan(shipment.id, {}, _user(app))
    source.pop("accepted_quote_id")
    source["planned_departure"] = (datetime.now(timezone.utc)+timedelta(days=10)).isoformat()
    source["planned_arrival"] = (datetime.now(timezone.utc)+timedelta(days=12)).isoformat()
    leg = routes.add_leg(shipment.id, plan["id"], {**source, "sequence_number": 1}, _user(app))
    return shipment.public_id, plan["id"], leg


def select(app, shipment, plan, leg, version, revision=0, key=None):
    row, created = svc.select_basis(shipment, plan, leg["id"], _user(app), {
        "expected_version": leg["version"], "expected_selection_revision": revision,
        "reference_version_public_id": version.public_id}, key or str(uuid4()))
    db.session.commit()
    return row, created


def test_separate_ranges_future_version_and_old_new_plan_basis(operational_app):
    app = operational_app
    with app.app_context():
        first, _ = save(app)
        reference = db.session.get(Reference, first.reference_id)
        shipment, plan, leg = draft(app)
        before = (OrganizationSlaRule.query.count(), db.session.get(RouteLeg, leg["id"]).planned_arrival)
        selection, _ = select(app, shipment, plan, leg, first)
        second, _ = save(app, {key:value for key,value in payload(app, movement_min_minutes=1500,
            movement_max_minutes=1800, effective_from=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(), expected_version=1).items() if key not in svc.KEYS}, reference.public_id)
        view = svc.plan_read(shipment, plan, _user(app))["items"][0]
        assert view["selected"]["reference"]["public_id"] == first.public_id
        assert view["selected"]["reference"]["movement_min_minutes"] == 1200
        assert view["selected"]["reference"]["stop_max_minutes"] == 480
        assert view["applicable"]["public_id"] == second.public_id and view["selection_matches_leg"]
        assert view["selected"]["reference"]["effective_until"] == svc.aware(second.effective_from).isoformat()
        fresh_plan = routes.create_plan(shipment, {}, _user(app))
        location = payload(app)
        new_leg = routes.add_leg(shipment, fresh_plan["id"], {"origin":location["origin"], "destination":location["destination"],
            "transport_mode":"road", "sequence_number":1, "planned_departure":view["reference_at"]}, _user(app))
        new_selection, _ = select(app, shipment, fresh_plan["id"], new_leg, second)
        assert new_selection.reference_version_id == second.id and selection.reference_version_id == first.id
        listing = svc.listing(_user(app))["items"][0]
        assert listing["current"]["version"] == 1 and listing["latest_version"] == 2
        assert listing["versions"][1]["effective_until"] == listing["versions"][0]["effective_from"]
        assert before == (OrganizationSlaRule.query.count(), db.session.get(RouteLeg, leg["id"]).planned_arrival)
        assert all(row["actor_user_id"] == app.config["phase1a"]["verifier"] for row in listing["versions"])


@pytest.mark.parametrize("change", [
    {"movement_min_minutes":1441}, {"movement_min_minutes":True}, {"stop_max_minutes":None},
    {"movement_min_minutes":None, "movement_max_minutes":None, "stop_min_minutes":None, "stop_max_minutes":None},
    {"effective_from":"2026-10-01T12:00:00"}, {"transport_mode":"invented"}, {"organization_id":999},
])
def test_invalid_reference_never_creates_partial_configuration(operational_app, change):
    with operational_app.app_context():
        with pytest.raises(operations.OperationalError): save(operational_app, payload(operational_app, **change))
        db.session.rollback()
        assert Reference.query.count() == Version.query.count() == 0


def test_idempotent_versions_stale_updates_prospective_boundaries_and_immutability(operational_app):
    app = operational_app
    with app.app_context():
        values = payload(app); key = str(uuid4())
        first, _ = save(app, values, key=key)
        replay, created = save(app, values, key=key)
        assert replay.id == first.id and created is False
        reference = db.session.get(Reference, first.reference_id)
        with pytest.raises(operations.OperationalError): save(app, {**values,"stop_min_minutes":300}, key=key)
        db.session.rollback()
        for effective, expected in ((values["effective_from"],1), ((datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),0)):
            with pytest.raises(operations.OperationalError):
                save(app, {**{k:v for k,v in values.items() if k in svc.VALUES}, "effective_from":effective,"expected_version":expected}, reference.public_id)
            db.session.rollback()
        first.movement_min_minutes = 1
        with pytest.raises(ValueError): db.session.commit()
        db.session.rollback()
        assert Version.query.one().movement_min_minutes == 1200
        db.session.delete(reference)
        with pytest.raises(ValueError): db.session.flush()
        db.session.rollback()


def test_missing_reference_stale_leg_and_selection_are_explicit(operational_app):
    app = operational_app
    with app.app_context():
        shipment, plan, leg = draft(app)
        assert svc.plan_read(shipment,plan,_user(app))["items"][0]["applicable"] is None
        first, _ = save(app)
        selected, _ = select(app,shipment,plan,leg,first)
        changed = routes.update_leg(shipment,plan,leg["id"], {"expected_version":leg["version"],"transport_mode":"rail"},_user(app))
        view = svc.plan_read(shipment,plan,_user(app))["items"][0]
        assert view["applicable"] is None and not view["selection_matches_leg"]
        assert view["selected"]["public_id"] == selected.public_id and len(view["history"]) == 1
        with pytest.raises(operations.OperationalError): select(app,shipment,plan,changed,first,revision=1)
        db.session.rollback()
        assert Basis.query.count() == 1


def test_selection_replay_and_published_plan_cannot_be_rebound(operational_app):
    app=operational_app
    with app.app_context():
        version,_=save(app);shipment,plan,leg=draft(app);key=str(uuid4())
        first,_=select(app,shipment,plan,leg,version,key=key)
        replay,created=select(app,shipment,plan,leg,version,key=key)
        assert replay.id==first.id and created is False and Basis.query.count()==1
        with pytest.raises(operations.OperationalError,match="payload differs"):
            select(app,shipment,plan,leg,version,revision=1,key=key)
        db.session.rollback()
        current=db.session.get(RoutePlan,plan);current.status="active";db.session.commit()
        with pytest.raises(operations.OperationalError) as denied:
            select(app,shipment,plan,leg,version,revision=1)
        assert denied.value.code=="ROUTE_PLAN_NOT_DRAFT"
        db.session.rollback()
        view=svc.plan_read(shipment,plan,_user(app))["items"][0]
        assert not view["can_select"] and view["selected"]["reference"]["version"]==1


def test_explicit_zero_stop_is_distinct_from_undefined_movement(operational_app):
    with operational_app.app_context():
        version,_=save(operational_app,payload(operational_app,movement_min_minutes=None,movement_max_minutes=None,stop_min_minutes=0,stop_max_minutes=0))
        value=svc.project_version(version)
        assert value["movement_min_minutes"] is None and value["movement_max_minutes"] is None
        assert value["stop_min_minutes"]==value["stop_max_minutes"]==0


def test_live_role_tenant_and_parent_boundaries_for_http(operational_app):
    app = operational_app
    client = app.test_client()
    with app.app_context():
        first, _ = save(app); reference = db.session.get(Reference,first.reference_id).public_id
        shipment,plan,leg = draft(app)
        outsider = db.session.get(ExpertUser, app.config["phase1a"]["outsider"])
        outsider.authority="ORGANIZATION_ADMIN"; db.session.commit()
    assert client.get("/api/organization/route-reference-times").status_code == 401
    assert client.get("/api/organization/route-reference-times",headers=_auth(app,"outsider")).json["data"]["total"] == 0
    for actor in ("user","outsider"):
        result = client.post(f"/api/admin/organization-route-reference-times/{reference}/versions",headers={**_auth(app,actor),"Idempotency-Key":str(uuid4())},json={"expected_version":1})
        assert result.status_code == (403 if actor=="user" else 404)
    url=f"/api/operational-shipments/{shipment}/route-plans/{plan}/reference-times"
    assert client.get(url,headers=_auth(app,"outsider")).status_code == 404
    assert client.get(url,headers=_auth(app)).status_code == 200
    with app.app_context():
        admin = db.session.get(ExpertUser,app.config["phase1a"]["verifier"])
        admin.authority="PLATFORM_ADMIN"; db.session.commit()
    assert client.get("/api/organization/route-reference-times",headers=_auth(app,"verifier")).status_code == 403
    assert client.post("/api/admin/organization-route-reference-times",headers={**_auth(app,"verifier"),"Idempotency-Key":str(uuid4())},json=payload(app)).status_code == 403


def test_customer_session_and_disabled_membership_do_not_grant_reference_access(operational_app):
    from backend.tests.test_phase3_document_context import _as_customer
    from backend.operational_models import OperationalMembership
    app=operational_app
    client=app.test_client()
    with app.app_context():
        account=CustomerGamification(email="route-time@example.test",phone="09120000001",operational_organization_id=app.config["phase1a"]["org"])
        db.session.add(account);db.session.commit();account_id=account.id
    _as_customer(client,account_id)
    assert client.get("/api/organization/route-reference-times").status_code==401
    assert client.post("/api/admin/organization-route-reference-times",json=payload(app)).status_code==401
    with app.app_context():
        member=OperationalMembership.query.filter_by(user_id=app.config["phase1a"]["verifier"]).one()
        member.is_active=False;db.session.commit()
    assert client.get("/api/organization/route-reference-times",headers=_auth(app,"verifier")).status_code==403
    assert client.post("/api/admin/organization-route-reference-times",headers={**_auth(app,"verifier"),"Idempotency-Key":str(uuid4())},json=payload(app)).status_code==403


def test_openapi_exact_routes_and_recursive_response_allowlists(operational_app):
    app=operational_app
    document=yaml.safe_load((Path(__file__).resolve().parents[2]/"docs/openapi/openapi.yaml").read_text(encoding="utf-8"))
    actual={(re.sub(r"<(?:uuid|int):([^>]+)>",r"{\1}",rule.rule),method.lower()) for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith("route_times.") for method in rule.methods-{"HEAD","OPTIONS"}}
    declared={(path,method) for path,value in document["paths"].items() if "route-reference-times" in path or path.endswith("/reference-times") or path.endswith("/reference-time")
        for method in value if method in {"get","post","put","delete","patch"}}
    assert actual==declared
    def check(value,schema):
        if value is None: assert schema.get("nullable");return
        if "$ref" in schema:schema=document["components"]["schemas"][schema["$ref"].split("/")[-1]]
        if isinstance(value,dict):
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) <= set(value) <= set(schema["properties"])
            for key,item in value.items():check(item,schema["properties"][key])
        elif isinstance(value,list):
            for item in value:check(item,schema["items"])
    with app.app_context():
        first,_=save(app);shipment,plan,leg=draft(app)
        select(app,shipment,plan,leg,first)
        check(svc.listing(_user(app)),document["components"]["schemas"]["RouteTimeList"])
        check(svc.plan_read(shipment,plan,_user(app)),document["components"]["schemas"]["RoutePlanReferenceTimes"])
