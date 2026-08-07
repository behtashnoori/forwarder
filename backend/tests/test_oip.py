"""OIP-2 seven-policy, dedup, lifecycle, evidence, security and abstention contracts."""
from datetime import datetime, timedelta, timezone
import pytest
from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import ExpertUser
from backend.oip_models import OipFactReference, OipSignal, OipSituation, OipSituationHistory
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services import oip_service as oip

@pytest.fixture()
def app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"oip-test"})
    with app.app_context():
        org=OperationalOrganization(name="OIP Synthetic");other=OperationalOrganization(name="Other")
        user=ExpertUser(username="oip",password_hash="unused",full_name="OIP Operator",role="expert",is_active=True)
        outsider=ExpertUser(username="outside",password_hash="unused",full_name="Outside",role="expert",is_active=True)
        db.session.add_all([org,other,user,outsider]);db.session.flush();permissions=["oip.read","oip.manage","oip.reconcile"]
        db.session.add_all([OperationalMembership(organization_id=org.id,user_id=user.id,permissions=permissions),OperationalMembership(organization_id=other.id,user_id=outsider.id,permissions=permissions)]);db.session.commit()
        app.config["oip_ids"]={"org":org.id,"user":user.id,"outsider":outsider.id}
    return app

def observation(app,typ,active=True,watermark="w1"):
    now=datetime.now(timezone.utc);ids=app.config["oip_ids"]
    return oip.observe(organization_id=ids["org"],situation_type=typ,subject_type="SHIPMENT",subject_public_id="shipment-opaque",dimensions={"bounded":"dimension"},source_domain="OPERATIONAL_EXECUTION",source_type="SyntheticAuthoritativeAdapter",source_public_id="source-opaque",source_version=watermark,occurred_at=now-timedelta(hours=2),due_at=now-timedelta(hours=1),severity="HIGH",urgency="HIGH",active=active,source_watermark=watermark,calculated_at=now,evidence={"kind":"test-authoritative-reference","public_id":"source-opaque"})

def test_exact_seven_catalog_and_threshold_gaps(app):
    with app.app_context():
        catalog=oip.policy_catalog();assert len(catalog)==7
        assert {x["situation_type"] for x in catalog}==set(oip.POLICIES)
        gaps={x["situation_type"] for x in catalog if not x["configured"]}
        assert gaps=={"NEXT_MILESTONE_OVERDUE","EXECUTION_UNIT_STALE"}
        assert observation(app,"NEXT_MILESTONE_OVERDUE")["status"]=="INACTIVE_UNCONFIGURED"
        assert observation(app,"EXECUTION_UNIT_STALE")["status"]=="INACTIVE_UNCONFIGURED"
        assert OipSituation.query.count()==0

@pytest.mark.parametrize("typ",["CHECKPOINT_OVERDUE","ROUTE_DEPENDENCY_BLOCKED","REPLAN_REQUIRED","DOCUMENT_READINESS_BLOCKED","ACTIVE_DELAY_OR_EXCEPTION"])
def test_configured_policy_detects_deduplicates_explains_and_traces(app,typ):
    with app.app_context():
        first=observation(app,typ);db.session.commit();second=observation(app,typ);db.session.commit()
        assert first["public_id"]==second["public_id"] and OipSituation.query.count()==1
        row=OipSituation.query.one();assert row.priority=="HIGH" and row.priority_explanation["policy"]=="lexicographic-v1"
        assert OipFactReference.query.count()==1 and OipSignal.query.count()==1
        detail=oip.detail(row.public_id,{"id":app.config["oip_ids"]["user"]})
        assert detail["evidence"] and detail["recommendation"]["automatic_execution"] is False
        assert detail["decision_context"]["read_only"] is True

def test_clear_reopen_preserves_history_and_occurrence(app):
    with app.app_context():
        observation(app,"ACTIVE_DELAY_OR_EXCEPTION");db.session.commit();observation(app,"ACTIVE_DELAY_OR_EXCEPTION",False,"w2");db.session.commit()
        row=OipSituation.query.one();assert row.status=="RESOLVED"
        observation(app,"ACTIVE_DELAY_OR_EXCEPTION",True,"w3");db.session.commit();assert row.status=="OPEN" and row.occurrence_count==2
        assert [h.event_type for h in OipSituationHistory.query.order_by(OipSituationHistory.id)]==["DETECTED","AUTO_RESOLVED","REOPENED"]

def test_lifecycle_version_reason_and_snooze_contract(app):
    with app.app_context():
        observation(app,"ACTIVE_DELAY_OR_EXCEPTION");db.session.commit();row=OipSituation.query.one();user={"id":app.config["oip_ids"]["user"]}
        oip.transition(row.public_id,"acknowledge",{"expected_version":1},user);assert row.status=="ACKNOWLEDGED"
        with pytest.raises(oip.OperationalError) as stale:oip.transition(row.public_id,"start",{"expected_version":1},user)
        assert stale.value.code=="VERSION_CONFLICT"
        with pytest.raises(oip.OperationalError):oip.transition(row.public_id,"dismiss",{"expected_version":2},user)
        oip.transition(row.public_id,"snooze",{"expected_version":2,"reason":"awaiting governed review","until":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()},user);assert row.status=="SNOOZED"

def test_tenant_isolation_and_impossible_intelligence(app):
    with app.app_context():
        observation(app,"ACTIVE_DELAY_OR_EXCEPTION");db.session.commit();row=OipSituation.query.one()
        with pytest.raises(oip.OperationalError) as hidden:oip.detail(row.public_id,{"id":app.config["oip_ids"]["outsider"]})
        assert hidden.value.code=="SITUATION_NOT_FOUND"
        dumped=str(oip.serialize(row)).lower()
        for forbidden in ("financial exposure","carrier reliability","compliance score","predictive risk","customer criticality"):assert forbidden not in dumped

def test_unknown_signal_is_rejected(app):
    with app.app_context():
        with pytest.raises(oip.OperationalError) as exc:observation(app,"PREDICTIVE_RISK")
        assert exc.value.code=="UNSUPPORTED_SITUATION_TYPE"
