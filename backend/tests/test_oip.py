"""OIP-2 seven-policy, dedup, lifecycle, evidence, security and abstention contracts."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import ExpertUser
from backend.oip_models import OipFactReference, OipProjectionHealthHistory, OipProjectionState, OipSignal, OipSituation, OipSituationHistory, OipThresholdPolicy
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

def observation(app,typ,active=True,watermark="w1",calculated_at=None):
    now=calculated_at or datetime.now(timezone.utc);ids=app.config["oip_ids"]
    return oip.observe(organization_id=ids["org"],situation_type=typ,subject_type="SHIPMENT",subject_public_id="shipment-opaque",dimensions={"bounded":"dimension"},source_domain="OPERATIONAL_EXECUTION",source_type="SyntheticAuthoritativeAdapter",source_public_id="source-opaque",source_version=watermark,occurred_at=now-timedelta(hours=2),due_at=now-timedelta(hours=1),severity="HIGH",urgency="HIGH",active=active,source_watermark=watermark,calculated_at=now,evidence={"kind":"test-authoritative-reference","public_id":"source-opaque"})

def threshold(app, signal_type, *, scope_type="ENTERPRISE", scope_public_id="ENTERPRISE", value=1, unit="HOUR", version=1, active=True, effective_from=None, effective_to=None):
    ids=app.config["oip_ids"];now=datetime.now(timezone.utc)
    row=OipThresholdPolicy(organization_id=ids["org"],signal_type=signal_type,scope_type=scope_type,scope_public_id=scope_public_id,value=value,unit=unit,authority="OIP-POL-001 approved governance",source="test governed policy",version=version,is_active=active,effective_from=effective_from or now-timedelta(days=1),effective_to=effective_to,created_by_user_id=ids["user"],updated_by_user_id=ids["user"])
    db.session.add(row);db.session.flush();return row

def test_exact_seven_catalog_and_threshold_gaps(app):
    with app.app_context():
        catalog=oip.policy_catalog();assert len(catalog)==7
        assert {x["situation_type"] for x in catalog}==set(oip.POLICIES)
        governed={x["situation_type"] for x in catalog if x["configured"]=="GOVERNED"}
        assert governed=={"NEXT_MILESTONE_OVERDUE","EXECUTION_UNIT_STALE"}
        assert observation(app,"NEXT_MILESTONE_OVERDUE")["status"]=="INACTIVE_UNCONFIGURED"
        assert observation(app,"EXECUTION_UNIT_STALE")["status"]=="INACTIVE_UNCONFIGURED"
        assert OipSituation.query.count()==0

def test_projection_health_exact_watermark_stale_rebuild_degraded_and_recovery(app):
    with app.app_context():
        user={"id":app.config["oip_ids"]["user"]}
        initial=oip.projection_health(user)
        assert initial["health_state"]=="STALE" and initial["processed_watermark"] is None
        rebuilt=oip.rebuild_attention_projections(user)
        assert rebuilt["health_state"]=="FRESH"
        state=db.session.get(OipProjectionState,app.config["oip_ids"]["org"])
        assert state.source_watermark==state.processed_watermark and state.last_success_at
        # A real authoritative-source version change produces exact controlled lag.
        org=OperationalOrganization.query.get(app.config["oip_ids"]["org"]);org.name="OIP Synthetic renamed"
        # Organization metadata is not an OIP source, so it cannot manufacture STALE.
        db.session.commit();assert oip.projection_health(user)["health_state"]=="FRESH"
        with pytest.raises(oip.OperationalError) as failure:
            oip.rebuild_attention_projections(user,_failure_point="after_delete")
        assert failure.value.code=="REBUILD_FAILED"
        degraded=oip.projection_health(user)
        assert degraded["health_state"]=="DEGRADED" and degraded["reason_code"]=="REBUILD_FAILED"
        assert "controlled" not in (degraded["reason"] or "")
        assert oip.rebuild_attention_projections(user)["health_state"]=="FRESH"
        assert {h.to_state for h in OipProjectionHealthHistory.query.all()} >= {"STALE","REBUILDING","DEGRADED","FRESH"}

def test_threshold_precedence_effectivity_and_abstention(app):
    with app.app_context():
        ids=app.config["oip_ids"];now=datetime.now(timezone.utc)
        assert oip.resolve_threshold(organization_id=ids["org"],signal_type="NEXT_MILESTONE_OVERDUE",project_public_id="project",at=now)["status"]=="INACTIVE_UNCONFIGURED"
        threshold(app,"NEXT_MILESTONE_OVERDUE",value=9)
        threshold(app,"NEXT_MILESTONE_OVERDUE",scope_type="SERVICE_MODE",scope_public_id="mode",value=5)
        threshold(app,"NEXT_MILESTONE_OVERDUE",scope_type="PROJECT",scope_public_id="project",value=2,version=1)
        threshold(app,"NEXT_MILESTONE_OVERDUE",scope_type="PROJECT",scope_public_id="project",value=1,version=2,active=False)
        threshold(app,"NEXT_MILESTONE_OVERDUE",scope_type="PROJECT",scope_public_id="project",value=1,version=3,effective_from=now+timedelta(days=1))
        db.session.commit()
        resolved=oip.resolve_threshold(organization_id=ids["org"],signal_type="NEXT_MILESTONE_OVERDUE",project_public_id="project",service_mode_public_ids=["mode"],at=now)
        assert (resolved["scope"],resolved["value"],resolved["policy_version"])==("PROJECT",2,1)
        service=oip.resolve_threshold(organization_id=ids["org"],signal_type="NEXT_MILESTONE_OVERDUE",project_public_id="other",service_mode_public_ids=["mode"],at=now)
        assert (service["scope"],service["value"])==("SERVICE_MODE",5)
        enterprise=oip.resolve_threshold(organization_id=ids["org"],signal_type="NEXT_MILESTONE_OVERDUE",project_public_id="other",at=now)
        assert (enterprise["scope"],enterprise["value"])==("ENTERPRISE",9)

def test_overdue_boundaries_terminal_due_and_policy_explanation(app):
    with app.app_context():
        ids=app.config["oip_ids"];now=datetime.now(timezone.utc);threshold(app,"NEXT_MILESTONE_OVERDUE");db.session.commit()
        base=dict(organization_id=ids["org"],project_public_id="project",subject_public_id="shipment",dimensions={"milestone_public_id":"milestone"},source_public_id="milestone",source_version=1,occurred_at=now-timedelta(hours=2),lifecycle_status="PENDING",calculated_at=now)
        assert oip.evaluate_next_milestone_overdue(**base,due_at=now)["status"]=="CLEARED"
        assert oip.evaluate_next_milestone_overdue(**{**base,"source_version":2},due_at=now-timedelta(minutes=30))["status"]=="CLEARED"
        active=oip.evaluate_next_milestone_overdue(**{**base,"source_version":3},due_at=now-timedelta(hours=2));db.session.commit()
        assert active["status"]=="ACTIVE"
        row=OipSituation.query.one();assert row.priority_explanation["evaluation"]["scope"]=="ENTERPRISE"
        assert oip.evaluate_next_milestone_overdue(**{**base,"source_version":4,"lifecycle_status":"COMPLETED"},due_at=now-timedelta(hours=2))["status"]=="CLEARED"
        assert oip.evaluate_next_milestone_overdue(**{**base,"source_version":5},due_at=None)["reason"]=="NO_AUTHORITATIVE_DUE_TIME"

def test_execution_unit_stale_operational_time_lifecycle_clear_reopen_and_policy_change(app):
    with app.app_context():
        ids=app.config["oip_ids"];now=datetime.now(timezone.utc)
        unit=SimpleNamespace(public_id="unit-opaque",version=1,is_active=True,lifecycle_status="in_progress",last_event_at=now-timedelta(hours=3),created_at=now-timedelta(days=1),updated_at=now)
        assert oip.evaluate_execution_unit_stale(organization_id=ids["org"],project_public_id="project",unit=unit,calculated_at=now)["status"]=="INACTIVE_UNCONFIGURED"
        threshold(app,"EXECUTION_UNIT_STALE",value=2);db.session.commit()
        active=oip.evaluate_execution_unit_stale(organization_id=ids["org"],project_public_id="project",unit=unit,calculated_at=now);db.session.commit()
        assert active["status"]=="ACTIVE"
        row=OipSituation.query.one();assert row.priority_explanation["evaluation"]["time_source"]=="LATEST_OPERATIONAL_EVENT_OCCURRED_AT"
        # A late-recorded event remains old by canonical occurred_at and therefore stays stale.
        unit.version=2;unit.updated_at=now;unit.last_event_at=now-timedelta(hours=3)
        assert oip.evaluate_execution_unit_stale(organization_id=ids["org"],project_public_id="project",unit=unit,calculated_at=now)["status"]=="ACTIVE"
        unit.version=3;unit.last_event_at=now-timedelta(minutes=5)
        assert oip.evaluate_execution_unit_stale(organization_id=ids["org"],project_public_id="project",unit=unit,calculated_at=now)["status"]=="CLEARED";db.session.commit()
        assert row.status=="RESOLVED"
        unit.version=4;unit.last_event_at=now-timedelta(hours=3)
        assert oip.evaluate_execution_unit_stale(organization_id=ids["org"],project_public_id="project",unit=unit,calculated_at=now)["status"]=="ACTIVE";db.session.commit()
        assert row.status=="OPEN" and row.occurrence_count==2
        unit.version=5;unit.lifecycle_status="delivered"
        assert oip.evaluate_execution_unit_stale(organization_id=ids["org"],project_public_id="project",unit=unit,calculated_at=now)["status"]=="CLEARED"
        threshold(app,"EXECUTION_UNIT_STALE",scope_type="PROJECT",scope_public_id="project",value=1,version=2);db.session.commit()
        unit.version=6;unit.lifecycle_status="in_progress"
        assert oip.evaluate_execution_unit_stale(organization_id=ids["org"],project_public_id="project",unit=unit,calculated_at=now)["status"]=="ACTIVE";db.session.commit()
        assert row.policy_version=="2" and OipSituation.query.count()==1

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

def test_snooze_expiry_reconciliation_returns_same_situation_to_attention(app):
    with app.app_context():
        observation(app,"ACTIVE_DELAY_OR_EXCEPTION");db.session.commit();row=OipSituation.query.one();user={"id":app.config["oip_ids"]["user"]}
        until=datetime.now(timezone.utc)+timedelta(seconds=1)
        oip.transition(row.public_id,"snooze",{"expected_version":1,"reason":"short controlled expiry","until":until.isoformat()},user)
        public_id=row.public_id
        observation(app,"ACTIVE_DELAY_OR_EXCEPTION",True,"w2",calculated_at=until+timedelta(seconds=1));db.session.commit()
        assert row.public_id==public_id and row.status=="OPEN" and row.occurrence_count==1
        assert oip.serialize(row)["snoozed_until"].startswith(until.replace(tzinfo=None).isoformat())
        assert [h.event_type for h in OipSituationHistory.query.order_by(OipSituationHistory.id)]==["DETECTED","SNOOZE","RETURNED_TO_ATTENTION"]

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
