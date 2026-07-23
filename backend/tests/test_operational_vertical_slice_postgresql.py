"""Real PostgreSQL gates for the Phase 1A operational aggregate."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import Milestone, OperationalMembership, OperationalOrganization, OperationalOutbox, OperationalShipment, OperationalWorkItem, RouteLeg, RoutePlan
from backend.services import operational_service as service


def _url():
    value=os.environ.get("FORWARDER_PHASE1A_POSTGRES_URL","")
    if not value: pytest.skip("explicit Phase 1A disposable PostgreSQL URL not provided")
    parsed=make_url(value); assert parsed.host in {"127.0.0.1","localhost"}; assert parsed.database.startswith("forwarder_phase1a_test_")
    return value


def test_phase1a_postgresql_constraints_concurrency_and_triggers():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":_url(),"SECRET_KEY":"phase1a-postgresql"},skip_startup=True)
    permissions=["operational_shipment.read","operational_shipment.create","milestone_event.create","milestone.verify","milestone.correct","work_item.read","work_item.manage"]
    with app.app_context():
        org=OperationalOrganization(name="Phase1A PostgreSQL Org"); reporter=ExpertUser(username="phase1a-pg-reporter",password_hash="unused",full_name="PG Reporter",role="expert",is_active=True); verifier=ExpertUser(username="phase1a-pg-verifier",password_hash="unused",full_name="PG Verifier",role="manager",is_active=True)
        db.session.add_all([org,reporter,verifier]); db.session.flush(); db.session.add_all([OperationalMembership(organization_id=org.id,user_id=reporter.id,permissions=permissions),OperationalMembership(organization_id=org.id,user_id=verifier.id,permissions=permissions)])
        origin=Province(name_fa="PG Origin",code="P1APGO"); dest=Province(name_fa="PG Destination",code="P1APGD"); request=ShipmentRequest(contact_phone="09000000009",status="waiting_for_customer",status_request_status="new",assigned_to=reporter.id)
        db.session.add_all([origin,dest,request]); db.session.flush(); quote=ExpertQuote(shipment_request_id=request.id,amount=10,currency="IRR",created_by_expert_id=reporter.id,created_at=datetime.now(timezone.utc),customer_response="accepted",responded_at=datetime.now(timezone.utc),operational_organization_id=org.id); db.session.add(quote); db.session.commit()
        ids={"org":org.id,"reporter":reporter.id,"verifier":verifier.id,"quote":quote.id,"origin":origin.id,"dest":dest.id}
    payload={"accepted_quote_id":ids["quote"],"planned_departure":(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(),"planned_arrival":(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),"origin":{"source_type":"province","source_id":ids["origin"]},"destination":{"source_type":"province","source_id":ids["dest"]},"transport_mode":"road"}
    def create(key):
        with app.app_context(): return service.create_from_accepted_quote(payload,{"id":ids["reporter"],"role":"expert"},key)[0].id
    with ThreadPoolExecutor(max_workers=2) as pool: created=list(pool.map(create,["pg-create-1","pg-create-2"]))
    assert created[0] == created[1]
    with app.app_context():
        assert OperationalShipment.query.filter_by(accepted_quote_id=ids["quote"]).count() == 1
        shipment=OperationalShipment.query.filter_by(accepted_quote_id=ids["quote"]).one(); milestone=db.session.scalar(select(Milestone).join(RouteLeg,Milestone.route_leg_id==RouteLeg.id).join(RoutePlan,RouteLeg.route_plan_id==RoutePlan.id).where(RoutePlan.operational_shipment_id==shipment.id,Milestone.milestone_type=="departure"))
        event=service.record_event(shipment.id,milestone.id,{"occurred_at":datetime.now(timezone.utc).isoformat()},{"id":ids["reporter"],"role":"expert"},"pg-report")
        shipment_id, milestone_id, event_id, expected=shipment.id, milestone.id, event.id, milestone.version
    def verify():
        with app.app_context():
            try: service.verify_milestone(shipment_id,milestone_id,expected,{"id":ids["verifier"],"role":"manager"}); return "ok"
            except service.OperationalError as exc: return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(lambda _:verify(),range(2)))
    assert sorted(outcomes) == ["STALE_AGGREGATE_VERSION","ok"]
    with app.app_context():
        def reconcile():
            with app.app_context(): return service.reconcile_overdue(user_id=ids["reporter"])
        with ThreadPoolExecutor(max_workers=2) as pool: reconciled=list(pool.map(lambda _:reconcile(),range(2)))
        assert sum(reconciled) == 1
        assert OperationalWorkItem.query.filter_by(operational_shipment_id=shipment_id,status="open").count() == 1
        assert OperationalOutbox.query.filter_by(event_type="operational_shipment.created",aggregate_id=shipment_id).count() == 1
        with pytest.raises(DBAPIError): db.session.execute(text("update milestone_event set reason='tamper' where id=:id"),{"id":event_id}); db.session.commit()
        db.session.rollback()
        with pytest.raises(DBAPIError): db.session.execute(text("delete from milestone_event where id=:id"),{"id":event_id}); db.session.commit()
        db.session.rollback()
        with pytest.raises((IntegrityError,DBAPIError)):
            open_item=OperationalWorkItem.query.filter_by(status="open").one(); db.session.add(OperationalWorkItem(organization_id=open_item.organization_id,operational_shipment_id=open_item.operational_shipment_id,milestone_id=open_item.milestone_id,due_at=open_item.due_at,reason="duplicate")); db.session.commit()
        db.session.rollback()
