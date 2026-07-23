"""Phase 1A domain, transaction, permission, and API contracts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalAudit, OperationalMembership,
    OperationalOrganization, OperationalOutbox, OperationalShipment,
    OperationalWorkItem, RouteLeg, RoutePlan,
)
from backend.services import operational_service as service
from backend.auth import auth_manager


@pytest.fixture()
def operational_app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"phase1a-test"})
    with app.app_context():
        org=OperationalOrganization(name="Synthetic Operations")
        other_org=OperationalOrganization(name="Other Synthetic Operations")
        user=ExpertUser(username="phase1a-operator",password_hash="unused",full_name="Phase1A Operator",role="expert",is_active=True)
        outsider=ExpertUser(username="phase1a-outsider",password_hash="unused",full_name="Phase1A Outsider",role="expert",is_active=True)
        verifier=ExpertUser(username="phase1a-verifier",password_hash="unused",full_name="Phase1A Verifier",role="manager",is_active=True)
        db.session.add_all([org,other_org,user,outsider,verifier]); db.session.flush()
        all_permissions=["operational_shipment.read","operational_shipment.create","milestone_event.create","milestone.verify","milestone.correct","work_item.read","work_item.manage"]
        db.session.add_all([OperationalMembership(organization_id=org.id,user_id=user.id,permissions=all_permissions),OperationalMembership(organization_id=org.id,user_id=verifier.id,permissions=all_permissions),OperationalMembership(organization_id=other_org.id,user_id=outsider.id,permissions=all_permissions)])
        origin=Province(name_fa="مبدأ",code="P1A-O"); destination=Province(name_fa="مقصد",code="P1A-D")
        request=ShipmentRequest(contact_phone="09000000000",status="waiting_for_customer",status_request_status="new",assigned_to=user.id)
        db.session.add_all([origin,destination,request]); db.session.flush()
        accepted=ExpertQuote(shipment_request_id=request.id,amount=1000,currency="IRR",created_by_expert_id=user.id,created_at=datetime.now(timezone.utc),customer_response="accepted",responded_at=datetime.now(timezone.utc),operational_organization_id=org.id)
        declined=ExpertQuote(shipment_request_id=request.id,amount=900,currency="IRR",created_by_expert_id=user.id,created_at=datetime.now(timezone.utc),customer_response="declined",responded_at=datetime.now(timezone.utc),operational_organization_id=org.id)
        db.session.add_all([accepted,declined]); db.session.commit()
        app.config["phase1a"]={"org":org.id,"other_org":other_org.id,"user":user.id,"verifier":verifier.id,"outsider":outsider.id,"accepted":accepted.id,"declined":declined.id,"origin":origin.id,"destination":destination.id}
    yield app


def _user(app, key="user"):
    ids=app.config["phase1a"]
    return {"id":ids[key],"role":"expert","username":key}


def _payload(app, quote="accepted", departure=None, arrival=None):
    ids=app.config["phase1a"]; departure=departure or datetime.now(timezone.utc)+timedelta(hours=1); arrival=arrival or departure+timedelta(hours=5)
    return {"accepted_quote_id":ids[quote],"planned_departure":departure.isoformat(),"planned_arrival":arrival.isoformat(),"origin":{"source_type":"province","source_id":ids["origin"]},"destination":{"source_type":"province","source_id":ids["destination"]},"transport_mode":"road"}


def _auth(app, key="user"):
    with app.app_context(): token=auth_manager.generate_tokens(app.config["phase1a"][key])["access_token"]
    return {"Authorization":f"Bearer {token}"}


def test_create_from_accepted_quote_is_complete_and_idempotent(operational_app):
    with operational_app.app_context():
        payload = _payload(operational_app)
        first,created=service.create_from_accepted_quote(payload,_user(operational_app),"create-1")
        replay,recreated=service.create_from_accepted_quote(payload,_user(operational_app),"create-1")
        assert created is True and recreated is False and replay.id == first.id
        assert OperationalShipment.query.count() == 1
        assert RoutePlan.query.count() == 1 and RouteLeg.query.count() == 1
        assert {m.milestone_type for m in Milestone.query.all()} == {"departure","arrival"}
        assert OperationalAudit.query.filter_by(action="operational_shipment.created").count() == 1
        assert OperationalOutbox.query.filter_by(event_type="operational_shipment.created").count() == 1


def test_create_guards_quote_timeline_location_and_tenant(operational_app):
    with operational_app.app_context():
        with pytest.raises(service.OperationalError) as rejected:
            service.create_from_accepted_quote(_payload(operational_app,"declined"),_user(operational_app),"declined")
        assert rejected.value.code == "QUOTE_NOT_ACCEPTED"
        bad=_payload(operational_app); bad["planned_arrival"]=bad["planned_departure"][:-6]
        with pytest.raises(service.OperationalError): service.create_from_accepted_quote(bad,_user(operational_app),"bad-time")
        same=_payload(operational_app); same["destination"]=same["origin"]
        with pytest.raises(service.OperationalError) as invalid: service.create_from_accepted_quote(same,_user(operational_app),"same")
        assert invalid.value.code == "INVALID_ROUTE_TIMELINE"
        with pytest.raises(service.OperationalError) as no_scope: service.create_from_accepted_quote(_payload(operational_app),{"id":999999,"role":"expert"},"none")
        assert no_scope.value.code == "TENANT_SCOPE_VIOLATION"


def test_report_verify_correct_and_work_item_lifecycle(operational_app):
    with operational_app.app_context():
        shipment,_=service.create_from_accepted_quote(_payload(operational_app),_user(operational_app),"events")
        milestone=Milestone.query.filter_by(milestone_type="departure").one()
        occurred=datetime.now(timezone.utc)-timedelta(minutes=10)
        event=service.record_event(shipment.id,milestone.id,{"occurred_at":occurred.isoformat()},_user(operational_app),"report-1")
        assert event.event_type == "reported" and milestone.verification_state == "reported"
        assert service.record_event(shipment.id,milestone.id,{"occurred_at":occurred.isoformat()},_user(operational_app),"report-1").id == event.id
        old_version=milestone.version
        service.verify_milestone(shipment.id,milestone.id,old_version,_user(operational_app,"verifier"))
        assert milestone.verification_state == "verified"
        with pytest.raises(service.OperationalError) as stale: service.verify_milestone(shipment.id,milestone.id,old_version,_user(operational_app))
        assert stale.value.code == "STALE_AGGREGATE_VERSION"
        corrected=service.correct_milestone(shipment.id,milestone.id,{"occurred_at":occurred.isoformat(),"reason":"Corrected operator timestamp","expected_version":milestone.version},_user(operational_app),"correct-1")
        assert corrected.event_type == "corrected" and corrected.supersedes_event_id
        assert MilestoneEvent.query.count() == 3


def test_reconcile_is_idempotent_and_verify_resolves_work(operational_app):
    with operational_app.app_context():
        past=datetime.now(timezone.utc)-timedelta(hours=3)
        shipment,_=service.create_from_accepted_quote(_payload(operational_app,departure=past,arrival=past+timedelta(hours=1)),_user(operational_app),"overdue")
        assert service.reconcile_overdue(user_id=_user(operational_app)["id"]) == 2
        assert service.reconcile_overdue(user_id=_user(operational_app)["id"]) == 0
        milestone=Milestone.query.filter_by(milestone_type="departure").one(); service.record_event(shipment.id,milestone.id,{"occurred_at":past.isoformat()},_user(operational_app),"late-report")
        service.verify_milestone(shipment.id,milestone.id,milestone.version,_user(operational_app,"verifier"))
        assert OperationalWorkItem.query.filter_by(milestone_id=milestone.id,status="resolved").count() == 1


def test_cross_tenant_detail_and_queue_are_hidden(operational_app):
    with operational_app.app_context():
        shipment,_=service.create_from_accepted_quote(_payload(operational_app),_user(operational_app),"tenant")
        with pytest.raises(service.OperationalError) as hidden: service.scoped_shipment(shipment.id,_user(operational_app,"outsider"))
        assert hidden.value.status == 404


def test_permission_denied_and_correction_reason_required(operational_app):
    with operational_app.app_context():
        membership=OperationalMembership.query.filter_by(user_id=operational_app.config["phase1a"]["user"]).one(); membership.permissions=["operational_shipment.read"]; db.session.commit()
        readonly={"id":operational_app.config["phase1a"]["user"],"role":"business_expert"}
        with pytest.raises(service.OperationalError) as forbidden: service.create_from_accepted_quote(_payload(operational_app),readonly,"forbidden")
        assert forbidden.value.code == "FORBIDDEN_OPERATION"
        membership.permissions=["operational_shipment.read","operational_shipment.create","milestone_event.create","milestone.verify","milestone.correct","work_item.read","work_item.manage"]; db.session.commit()
        shipment,_=service.create_from_accepted_quote(_payload(operational_app),_user(operational_app),"reason")
        milestone=Milestone.query.first()
        with pytest.raises(service.OperationalError) as reason: service.correct_milestone(shipment.id,milestone.id,{"occurred_at":datetime.now(timezone.utc).isoformat(),"expected_version":milestone.version},_user(operational_app),"correct")
        assert reason.value.code == "CORRECTION_REASON_REQUIRED"


def test_http_create_list_detail_and_error_envelopes(operational_app):
    client=operational_app.test_client(); headers={**_auth(operational_app),"Idempotency-Key":"http-create"}; payload=_payload(operational_app)
    created=client.post("/api/operational-shipments/from-accepted-quote",json=payload,headers=headers)
    assert created.status_code == 201 and created.json["meta"]["created"] is True
    replay=client.post("/api/operational-shipments/from-accepted-quote",json=payload,headers=headers)
    assert replay.status_code == 200 and replay.json["data"]["id"] == created.json["data"]["id"]
    listing=client.get("/api/operational-shipments?status=planned&customer=0900&page=1&per_page=5",headers=_auth(operational_app))
    assert listing.status_code == 200 and listing.json["meta"]["page"] == 1
    assert {"customer","current_milestone","overdue","open_work_item_count"} <= listing.json["data"][0].keys()
    detail=client.get(f"/api/operational-shipments/{created.json['data']['id']}",headers=_auth(operational_app))
    assert detail.status_code == 200 and "audit_summary" in detail.json["data"]
    missing=client.get("/api/operational-shipments/999999",headers=_auth(operational_app))
    assert missing.status_code == 404 and missing.json["error"]["code"] == "RESOURCE_NOT_FOUND"
    mismatch=dict(_payload(operational_app));mismatch["transport_mode"]="rail"
    conflict=client.post("/api/operational-shipments/from-accepted-quote",json=mismatch,headers=headers)
    assert conflict.status_code == 409 and conflict.json["error"]["code"] == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"


def test_http_permission_validation_transition_and_stale_conflicts(operational_app):
    with operational_app.app_context():
        membership=OperationalMembership.query.filter_by(user_id=operational_app.config["phase1a"]["user"]).one();membership.permissions=["operational_shipment.read"];db.session.commit()
    forbidden=operational_app.test_client().post("/api/operational-shipments/from-accepted-quote",json=_payload(operational_app),headers={**_auth(operational_app),"Idempotency-Key":"forbidden-http"})
    assert forbidden.status_code == 403 and forbidden.json["error"]["code"] == "FORBIDDEN_OPERATION"
    with operational_app.app_context(): membership=OperationalMembership.query.filter_by(user_id=operational_app.config["phase1a"]["user"]).one();membership.permissions=["operational_shipment.read","operational_shipment.create","milestone_event.create","milestone.verify","milestone.correct","work_item.read","work_item.manage"];db.session.commit()
    invalid=_payload(operational_app);invalid["planned_arrival"]="invalid"
    response=operational_app.test_client().post("/api/operational-shipments/from-accepted-quote",json=invalid,headers={**_auth(operational_app),"Idempotency-Key":"invalid-http"})
    assert response.status_code == 422 and response.json["error"]["code"] == "INVALID_ROUTE_TIMELINE" and "traceback" not in response.get_data(as_text=True).lower()
