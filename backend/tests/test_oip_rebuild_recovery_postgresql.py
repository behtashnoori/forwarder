"""Fresh-disposable PostgreSQL recovery proof for OIP rebuildable projections."""
from datetime import datetime, timedelta, timezone

from backend.extensions import db
from backend.oip_models import OipAttentionProjection, OipFactReference, OipProjectionState, OipSignal, OipSituation, OipSituationHistory
from backend.services import oip_service as oip
from backend.tests.test_oip_races_postgresql import pg_app, _observe, _transition  # noqa: F401


def test_projection_rebuild_and_interrupted_reconciliation_preserve_human_history(pg_app):
    with pg_app.app_context():
        c=pg_app.config["race"]; created=_observe(pg_app);db.session.commit();pid=created["public_id"]
        _transition(pg_app,pid,"acknowledge","a",1)
        _transition(pg_app,pid,"claim","a",2)
        _transition(pg_app,pid,"snooze","a",3,{"reason":"awaiting source","until":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()})
        _transition(pg_app,pid,"resolve","a",4,{"reason":"human verified"})
        durable_before=(OipSituation.query.one().public_id,OipSituation.query.one().status,OipSituation.query.one().assignee_user_id,OipSituationHistory.query.count(),OipFactReference.query.count(),OipSignal.query.count())
        db.session.execute(db.delete(OipAttentionProjection));db.session.execute(db.delete(OipProjectionState));db.session.commit()
        rebuilt=oip.rebuild_attention_projections(c["a"])
        assert rebuilt["status"]=="FRESH" and rebuilt["projection_version"]==oip.PROJECTION_VERSION
        durable_after=(OipSituation.query.one().public_id,OipSituation.query.one().status,OipSituation.query.one().assignee_user_id,OipSituationHistory.query.count(),OipFactReference.query.count(),OipSignal.query.count())
        assert durable_after==durable_before and OipAttentionProjection.query.count()==1
        # Simulate a process dying after marking the projection rebuilding.
        state=OipProjectionState.query.one();state.status="REBUILDING";state.source_watermark="interrupted";db.session.flush();db.session.rollback()
        restarted=oip.rebuild_attention_projections(c["a"]);assert restarted["status"]=="FRESH" and OipAttentionProjection.query.count()==1
        assert _observe(pg_app,"w1")["status"]=="TERMINAL_PRESERVED";db.session.commit()
        assert OipSituation.query.one().status=="RESOLVED"
        assert _observe(pg_app,"w2",False)["status"]=="CLEARED";db.session.commit()
        assert _observe(pg_app,"w3",True)["status"]=="ACTIVE";db.session.commit()
        row=OipSituation.query.one();assert row.status=="OPEN" and row.occurrence_count==2 and row.assignee_user_id==c["a"]["id"]
