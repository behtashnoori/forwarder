"""OIP-2's thirteen mandatory races on an explicit disposable PostgreSQL 18 database.

The suite uses READ COMMITTED (the application default), row locks for existing
Situations, and transaction-scoped advisory locks for logical identity creation.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from threading import Barrier
import uuid

import pytest
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.oip_models import OipAttentionProjection, OipFactReference, OipProjectionHealthHistory, OipProjectionState, OipSignal, OipSituation, OipSituationHistory
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services import oip_service as oip
from backend.services.operational_service import OperationalError


def _url():
    value=os.environ.get("OIP_POSTGRES_URL",""); parsed=make_url(value) if value else None
    if not value: pytest.skip("explicit disposable OIP PostgreSQL URL not provided")
    assert parsed.host in {"127.0.0.1","localhost"} and "oip2_gate" in (parsed.database or "")
    return value


@pytest.fixture()
def pg_app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":_url(),"SECRET_KEY":"oip-race"},skip_startup=True)
    with app.app_context():
        for model in (OipAttentionProjection,OipSituationHistory): db.session.query(model).delete()
        db.session.execute(db.delete(OipSituationHistory)); db.session.execute(db.delete(OipAttentionProjection))
        db.session.execute(db.delete(OipFactReference).where(False))
        # Evidence links must precede their durable parents.
        from backend.oip_models import OipSituationEvidence
        db.session.execute(db.delete(OipSituationEvidence)); db.session.execute(db.delete(OipSignal)); db.session.execute(db.delete(OipFactReference)); db.session.execute(db.delete(OipSituation)); db.session.execute(db.delete(OipProjectionHealthHistory)); db.session.execute(db.delete(OipProjectionState))
        org=OperationalOrganization(name=f"OIP race {uuid.uuid4()}"); other=OperationalOrganization(name=f"Other {uuid.uuid4()}")
        a=ExpertUser(username=f"oip-a-{uuid.uuid4()}",password_hash="unused",full_name="A",role="expert",is_active=True)
        b=ExpertUser(username=f"oip-b-{uuid.uuid4()}",password_hash="unused",full_name="B",role="expert",is_active=True)
        db.session.add_all([org,other,a,b]);db.session.flush();perms=["oip.read","oip.manage","oip.reconcile"]
        db.session.add_all([OperationalMembership(organization_id=org.id,user_id=a.id,permissions=perms),OperationalMembership(organization_id=org.id,user_id=b.id,permissions=perms)]);db.session.commit()
        app.config["race"]={"org":org.id,"a":{"id":a.id},"b":{"id":b.id},"other":other.id}
    yield app
    with app.app_context(): db.session.remove()


def _observe(app,watermark="w1",active=True,at=None,subject="subject",version=None):
    c=app.config["race"];now=at or datetime.now(timezone.utc)
    return oip.observe(organization_id=c["org"],situation_type="ACTIVE_DELAY_OR_EXCEPTION",subject_type="SHIPMENT",subject_public_id=subject,dimensions={"source":"race"},source_domain="OPERATIONAL_EXECUTION",source_type="RaceFact",source_public_id=subject,source_version=version or watermark,occurred_at=now-timedelta(hours=1),severity="HIGH",urgency="HIGH",active=active,source_watermark=watermark,calculated_at=now,evidence={"kind":"race"})


def _pair(app,left,right):
    barrier=Barrier(2)
    def run(fn):
        with app.app_context():
            barrier.wait()
            try: result=fn();db.session.commit();return ("ok",result)
            except OperationalError as exc: db.session.rollback();return (exc.code,None)
            finally: db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        return [future.result(timeout=20) for future in (pool.submit(run,left),pool.submit(run,right))]


def _seed(app):
    with app.app_context(): result=_observe(app);db.session.commit();return result["public_id"]
def _transition(app,public_id,action,user,version,payload=None):
    return oip.transition(public_id,action,{"expected_version":version,**(payload or {})},app.config["race"][user])
def _reason(): return {"reason":"race disposition"}


def test_race_01_same_signal_reconciled_concurrently(pg_app):
    results=_pair(pg_app,lambda:_observe(pg_app),lambda:_observe(pg_app))
    with pg_app.app_context(): assert OipSituation.query.count()==1 and OipSignal.query.count()==1 and len({x[1]["public_id"] for x in results})==1

def test_race_02_reconciliation_vs_acknowledgement(pg_app):
    pid=_seed(pg_app);_pair(pg_app,lambda:_observe(pg_app),lambda:_transition(pg_app,pid,"acknowledge","a",1))
    with pg_app.app_context(): assert OipSituation.query.one().status=="ACKNOWLEDGED"

def test_race_03_reconciliation_vs_resolution(pg_app):
    pid=_seed(pg_app);_pair(pg_app,lambda:_observe(pg_app),lambda:_transition(pg_app,pid,"resolve","a",1,_reason()))
    with pg_app.app_context(): assert OipSituation.query.one().status=="RESOLVED"

def test_race_04_resolution_vs_source_change_reopen(pg_app):
    pid=_seed(pg_app);_pair(pg_app,lambda:_observe(pg_app,"w2"),lambda:_transition(pg_app,pid,"resolve","a",1,_reason()))
    with pg_app.app_context(): assert OipSituation.query.one().status in {"OPEN","RESOLVED"} and OipSituation.query.one().occurrence_count<=2

def test_race_05_claim_vs_claim(pg_app):
    pid=_seed(pg_app);results=_pair(pg_app,lambda:_transition(pg_app,pid,"claim","a",1),lambda:_transition(pg_app,pid,"claim","b",1))
    assert sorted(x[0] for x in results)==["VERSION_CONFLICT","ok"]
    with pg_app.app_context(): assert OipSituation.query.one().assignee_user_id is not None

def test_race_06_claim_vs_reconciliation(pg_app):
    pid=_seed(pg_app);_pair(pg_app,lambda:_transition(pg_app,pid,"claim","a",1),lambda:_observe(pg_app))
    with pg_app.app_context(): assert OipSituation.query.one().assignee_user_id==pg_app.config["race"]["a"]["id"]

def test_race_07_snooze_vs_resolution(pg_app):
    pid=_seed(pg_app);payload={**_reason(),"until":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()};results=_pair(pg_app,lambda:_transition(pg_app,pid,"snooze","a",1,payload),lambda:_transition(pg_app,pid,"resolve","b",1,_reason()))
    assert sorted(x[0] for x in results)==["VERSION_CONFLICT","ok"]

def test_race_08_snooze_expiry_vs_reconciliation(pg_app):
    pid=_seed(pg_app)
    with pg_app.app_context(): _transition(pg_app,pid,"snooze","a",1,{**_reason(),"until":(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat()})
    _pair(pg_app,lambda:_observe(pg_app),lambda:oip.queue(pg_app.config["race"]["a"]))
    with pg_app.app_context(): assert OipSituation.query.one().status=="SNOOZED"

def test_race_09_source_correction_vs_reconciliation(pg_app):
    _seed(pg_app);new=datetime.now(timezone.utc);_pair(pg_app,lambda:_observe(pg_app,"w2",False,new),lambda:_observe(pg_app,"w1",True,new-timedelta(seconds=1)))
    with pg_app.app_context(): assert OipSituation.query.one().status=="RESOLVED"

def test_race_10_policy_version_change_vs_reconciliation(pg_app):
    _seed(pg_app);_pair(pg_app,lambda:_observe(pg_app,"policy-2",True,version="2"),lambda:_observe(pg_app,"policy-1",True,version="1"))
    with pg_app.app_context(): assert OipSituation.query.count()==1 and OipSignal.query.count()==3

def test_race_11_stale_lifecycle_writer_vs_newer_write(pg_app):
    pid=_seed(pg_app);results=_pair(pg_app,lambda:_transition(pg_app,pid,"acknowledge","a",1),lambda:_transition(pg_app,pid,"start","b",1))
    assert sorted(x[0] for x in results)==["VERSION_CONFLICT","ok"]

def test_race_12_situation_dedup_under_projection_workers(pg_app):
    _pair(pg_app,lambda:_observe(pg_app,"worker-a"),lambda:_observe(pg_app,"worker-b"))
    with pg_app.app_context(): assert OipSituation.query.count()==1 and OipSituation.query.one().occurrence_count==1

def test_race_13_rebuild_while_human_interaction_changes(pg_app):
    pid=_seed(pg_app);results=_pair(pg_app,lambda:oip.rebuild_attention_projections(pg_app.config["race"]["a"]),lambda:_transition(pg_app,pid,"claim","b",1))
    assert all(x[0]=="ok" for x in results)
    with pg_app.app_context():
        row=OipSituation.query.one();assert row.assignee_user_id==pg_app.config["race"]["b"]["id"] and OipAttentionProjection.query.count()==1
