"""Real PostgreSQL Phase 1B integrity and concurrency gates."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalCheckpoint, OperationalMembership,
    OperationalAudit, OperationalIdempotency, OperationalOrganization,
    OperationalOutbox, OperationalShipment, OperationalWorkItem,
    RouteDependency, RouteLeg, RoutePlan,
)
from backend.services import operational_service as base
from backend.services import route_orchestration_service as service


def _url():
    value=os.environ.get("FORWARDER_PHASE1B_POSTGRES_URL","")
    if not value: pytest.skip("explicit Phase 1B disposable PostgreSQL URL not provided")
    parsed=make_url(value)
    assert parsed.host in {"127.0.0.1","localhost"}
    assert parsed.database.startswith("forwarder_phase1b_uat_")
    return value


def test_phase1b_postgresql_integrity_lifecycle_and_concurrency():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":_url(),"SECRET_KEY":"phase1b-postgresql"},skip_startup=True)
    permissions=["operational_shipment.read","operational_shipment.create","route_plan.read","route_plan.create",
        "route_plan.activate","route_plan.replan","route_leg.manage","checkpoint.read","checkpoint.report","milestone.correct",
        "checkpoint.verify","route_exception.read","route_exception.manage"]
    suffix=os.urandom(4).hex()
    with app.app_context():
        org=OperationalOrganization(name=f"Phase1B PG {suffix}")
        reporter=ExpertUser(username=f"p1b-reporter-{suffix}",password_hash="unused",full_name="Reporter",role="expert",is_active=True)
        verifier=ExpertUser(username=f"p1b-verifier-{suffix}",password_hash="unused",full_name="Verifier",role="manager",is_active=True)
        db.session.add_all([org,reporter,verifier]);db.session.flush()
        db.session.add_all([OperationalMembership(organization_id=org.id,user_id=reporter.id,permissions=permissions),
            OperationalMembership(organization_id=org.id,user_id=verifier.id,permissions=permissions)])
        origin=Province(name_fa=f"Origin {suffix}",code=f"O{suffix[:5]}")
        destination=Province(name_fa=f"Destination {suffix}",code=f"D{suffix[:5]}")
        customer=Customer(first_name="Phase1B",last_name=f"Customer {suffix}",status="active")
        db.session.add_all([origin,destination,customer]);db.session.flush()
        request=ShipmentRequest(contact_phone=f"09{suffix[:8]}",status="waiting_for_customer",status_request_status="new",assigned_to=reporter.id,customer_id=customer.id)
        db.session.add(request);db.session.flush()
        quote=ExpertQuote(shipment_request_id=request.id,amount=100,currency="IRR",created_by_expert_id=reporter.id,
            created_at=datetime.now(timezone.utc),customer_response="accepted",responded_at=datetime.now(timezone.utc),
            operational_organization_id=org.id)
        db.session.add(quote);db.session.commit()
        ids={"org":org.id,"reporter":reporter.id,"verifier":verifier.id,"origin":origin.id,"destination":destination.id,"quote":quote.id}
        user={"id":reporter.id,"role":"expert"}; verifier_user={"id":verifier.id,"role":"manager"}
        start=datetime.now(timezone.utc)+timedelta(hours=1)
        payload={"accepted_quote_id":quote.id,"planned_departure":start.isoformat(),"planned_arrival":(start+timedelta(hours=4)).isoformat(),
            "origin":{"source_type":"province","source_id":origin.id},"destination":{"source_type":"province","source_id":destination.id},"transport_mode":"road"}
        shipment,_=base.create_from_accepted_quote(payload,user,f"p1b-create-{suffix}")
        active=RoutePlan.query.filter_by(operational_shipment_id=shipment.id,is_active=True).one()
        draft=service.create_plan(shipment.id,{"legs":[{"sequence_number":1,"origin":payload["origin"],"destination":payload["destination"],
            "transport_mode":"road","planned_departure":start.isoformat(),"planned_arrival":(start+timedelta(hours=4)).isoformat()}]},user)
        leg=RouteLeg.query.filter_by(route_plan_id=draft["id"]).one()
        first=service.add_checkpoint(shipment.id,draft["id"],{"route_leg_id":leg.id,"sequence_number":1,"checkpoint_type":"export_customs",
            "canonical_location_id":leg.origin_location_id,"planned_arrival_at":start.isoformat(),"planned_departure_at":(start+timedelta(minutes=30)).isoformat()},user)
        second=service.add_checkpoint(shipment.id,draft["id"],{"route_leg_id":leg.id,"sequence_number":2,"checkpoint_type":"unloading",
            "canonical_location_id":leg.destination_location_id,"planned_arrival_at":(start+timedelta(hours=3)).isoformat()},user)
        third=service.add_checkpoint(shipment.id,draft["id"],{"route_leg_id":leg.id,"sequence_number":3,"checkpoint_type":"final_delivery",
            "canonical_location_id":leg.destination_location_id,"planned_arrival_at":(start+timedelta(hours=4)).isoformat()},user)
        service.add_dependency(shipment.id,draft["id"],{"predecessor_checkpoint_id":first["id"],"successor_checkpoint_id":second["id"]},user)
        service.activate_plan(shipment.id,draft["id"],{"expected_version":1},user)
        plan_id=draft["id"]; shipment_id=shipment.id; second_id=second["id"]; third_id=third["id"]

        # Composite same-plan constraints reject cross-plan edges at the database.
        with pytest.raises(IntegrityError):
            db.session.add(OperationalCheckpoint(route_plan_id=active.id,route_leg_id=leg.id,sequence_number=9,
                checkpoint_type="final_delivery",canonical_location_id=leg.destination_location_id,
                status="planned",verification_state="planned",created_by_user_id=reporter.id))
            db.session.commit()
        db.session.rollback()
        checkpoint_count=OperationalCheckpoint.query.count()
        with pytest.raises(IntegrityError):
            db.session.execute(text(
                "UPDATE operational_checkpoint SET route_plan_id=:foreign_plan "
                "WHERE id=:checkpoint"
            ),{"foreign_plan":active.id,"checkpoint":first["id"]})
            db.session.commit()
        db.session.rollback()
        assert OperationalCheckpoint.query.count()==checkpoint_count
        foreign_checkpoint=OperationalCheckpoint.query.filter_by(route_plan_id=active.id).first()
        if foreign_checkpoint is None:
            # Phase 1A plan legitimately has no checkpoints; use a second draft graph.
            other=service.create_plan(shipment.id,{"legs":[]},user)
            other_plan=db.session.get(RoutePlan,other["id"])
            foreign_checkpoint=service._add_checkpoint(other_plan,{"sequence_number":1,"checkpoint_type":"final_delivery",
                "canonical_location_id":leg.destination_location_id,"planned_arrival_at":(start+timedelta(hours=5)).isoformat()},user)
            db.session.commit()
        with pytest.raises(IntegrityError):
            db.session.add(RouteDependency(route_plan_id=plan_id,predecessor_checkpoint_id=first["id"],
                successor_checkpoint_id=foreign_checkpoint.id,dependency_type="finish_to_start"));db.session.commit()
        db.session.rollback()
        with pytest.raises(IntegrityError):
            db.session.add(RouteDependency(route_plan_id=plan_id,predecessor_checkpoint_id=foreign_checkpoint.id,
                successor_checkpoint_id=second_id,dependency_type="finish_to_start"));db.session.commit()
        db.session.rollback()
        with pytest.raises(IntegrityError):
            db.session.add(Milestone(route_plan_id=plan_id,checkpoint_id=foreign_checkpoint.id,
                milestone_type="checkpoint_arrival",planned_at=start,projected_at=start))
            db.session.commit()
        db.session.rollback()
        with pytest.raises((DBAPIError,IntegrityError)):
            db.session.add(OperationalWorkItem(
                organization_id=org.id,operational_shipment_id=shipment_id,route_plan_id=plan_id,
                checkpoint_id=foreign_checkpoint.id,milestone_id=None,work_type="CHECKPOINT_OVERDUE",
                status="open",due_at=start,detected_at=start,severity="warning",reason="invalid scope",
            ))
            db.session.commit()
        db.session.rollback()

        arrival=Milestone.query.filter_by(checkpoint_id=first["id"],milestone_type="checkpoint_arrival").one()
        service.checkpoint_command(shipment.id,first["id"],{"expected_version":1,"occurred_at":datetime.now(timezone.utc).isoformat()},user,"pg-arrive","arrive")
        service.verify_checkpoint_milestone(
            shipment.id,first["id"],arrival.id,arrival.version,verifier_user,"pg-verify-arrival"
        )
        corrected_at=datetime.now(timezone.utc)+timedelta(minutes=2)
        service.correct_checkpoint_milestone(
            shipment.id,first["id"],arrival.id,
            {"expected_version":arrival.version,"occurred_at":corrected_at.isoformat(),"reason":"PG correction"},
            user,"pg-correct-arrival",
        )
        assert db.session.get(OperationalCheckpoint,first["id"]).actual_arrival_at is None
        service.verify_checkpoint_milestone(
            shipment.id,first["id"],arrival.id,arrival.version,verifier_user,"pg-reverify-arrival"
        )
        assert db.session.get(OperationalCheckpoint,first["id"]).actual_arrival_at==corrected_at
        assert [row.event_type for row in MilestoneEvent.query.filter_by(
            milestone_id=arrival.id).order_by(MilestoneEvent.id)]==[
                "reported","verified","corrected","verified",
            ]
        event_id=MilestoneEvent.query.filter_by(milestone_id=arrival.id,event_type="reported").one().id
        with pytest.raises(DBAPIError):
            db.session.execute(text("UPDATE milestone_event SET reason='tamper' WHERE id=:id"),{"id":event_id});db.session.commit()
        db.session.rollback()
        with pytest.raises(DBAPIError):
            db.session.execute(text("DELETE FROM milestone_event WHERE id=:id"),{"id":event_id});db.session.commit()
        db.session.rollback()

        # Real-PostgreSQL delay propagation preserves the ledger and synchronizes
        # checkpoint, milestone, and leg projections in one transaction.
        event_count_before=MilestoneEvent.query.filter(
            MilestoneEvent.milestone_id==arrival.id,
        ).count()
        plan_version=db.session.get(RoutePlan,plan_id).version
        reconciled=service.recalculate_projected_timeline(
            shipment_id,user,plan_version,"pg-delay-reconcile",
        )
        replay=service.recalculate_projected_timeline(
            shipment_id,user,plan_version,"pg-delay-reconcile",
        )
        assert reconciled["replayed"] is False and replay["replayed"] is True
        first_checkpoint=db.session.get(OperationalCheckpoint,first["id"])
        assert first_checkpoint.projected_arrival_at==first_checkpoint.actual_arrival_at
        assert Milestone.query.filter_by(
            checkpoint_id=first["id"],milestone_type="checkpoint_arrival",
        ).one().projected_at==first_checkpoint.actual_arrival_at
        assert db.session.get(RouteLeg,leg.id).projected_departure is not None
        assert MilestoneEvent.query.filter(
            MilestoneEvent.milestone_id==arrival.id,
        ).count()==event_count_before
        assert OperationalAudit.query.filter_by(
            action="route_plan.timeline_reconciled",entity_id=plan_id,
        ).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="route_plan.timeline_reconciled",aggregate_id=plan_id,
        ).count()==1
        second_checkpoint=db.session.get(OperationalCheckpoint,second_id)
        exception_time=datetime.now(timezone.utc)
        second_checkpoint.projected_arrival_at=exception_time-timedelta(hours=2)
        second_checkpoint.status="planned"
        exception_plan_version=db.session.get(RoutePlan,plan_id).version
        db.session.commit()

    def exception_reconcile(key):
        with app.app_context():
            result=service.reconcile_route_exceptions(
                shipment_id,user,exception_plan_version,exception_time,key,
            )
            return result["opened"],result["unchanged"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        exception_outcomes=list(pool.map(
            exception_reconcile,["pg-exception-race-a","pg-exception-race-b"],
        ))
    assert sorted(exception_outcomes)==[(0,1),(1,0)]
    with app.app_context():
        exception_item=OperationalWorkItem.query.filter_by(
            route_plan_id=plan_id,checkpoint_id=second_id,
            work_type="CHECKPOINT_OVERDUE",status="open",
        ).one()
        assert OperationalAudit.query.filter_by(
            action="route_exception.opened",entity_id=exception_item.id,
        ).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="route_exception.opened",aggregate_id=exception_item.id,
        ).count()==1
        db.session.add(OperationalWorkItem(
            organization_id=ids["org"],operational_shipment_id=shipment_id,
            route_plan_id=plan_id,checkpoint_id=second_id,milestone_id=None,
            work_type="CHECKPOINT_OVERDUE",status="open",due_at=exception_time,
            detected_at=exception_time,severity="warning",reason="duplicate",
        ))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    same_payload={"expected_version":1,"occurred_at":datetime.now(timezone.utc).isoformat()}
    def checkpoint_command(checkpoint_id,key,payload):
        with app.app_context():
            try:
                result=service.checkpoint_command(
                    shipment_id,checkpoint_id,payload,
                    {"id":ids["reporter"],"role":"expert"},key,"arrive",
                )
                return ("ok",result["id"])
            except base.OperationalError as exc:
                return ("error",exc.code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        same_outcomes=list(pool.map(
            lambda _:checkpoint_command(second_id,"pg-same-key",same_payload),range(2)
        ))
    assert same_outcomes==[("ok",second_id),("ok",second_id)]
    with app.app_context():
        second_milestone=Milestone.query.filter_by(
            checkpoint_id=second_id,milestone_type="checkpoint_arrival").one()
        second_milestone_id,second_version=second_milestone.id,second_milestone.version
        assert MilestoneEvent.query.filter_by(
            milestone_id=second_milestone_id,event_type="reported").count()==1
        assert OperationalIdempotency.query.filter_by(
            operation="checkpoint_arrive_report",command_resource_id=second_id,
            idempotency_key="pg-same-key").count()==1
        assert OperationalAudit.query.filter_by(
            action="checkpoint.arrived",entity_id=second_id).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="checkpoint.arrived",aggregate_id=second_id).count()==1

    def verify_milestone(key):
        with app.app_context():
            try:
                result=service.verify_checkpoint_milestone(
                    shipment_id,second_id,second_milestone_id,second_version,
                    {"id":ids["verifier"],"role":"manager"},key,
                )
                return ("ok",result["milestone"]["id"])
            except base.OperationalError as exc:
                return ("error",exc.code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        verify_outcomes=list(pool.map(lambda _ :verify_milestone("pg-verify-same-key"),range(2)))
    assert verify_outcomes==[("ok",second_milestone_id),("ok",second_milestone_id)]
    with app.app_context():
        assert MilestoneEvent.query.filter_by(
            milestone_id=second_milestone_id,event_type="verified").count()==1
        assert OperationalAudit.query.filter_by(
            action="checkpoint.milestone_verified",entity_id=second_milestone_id).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="checkpoint.milestone_verified",aggregate_id=second_milestone_id).count()==1
        corrected_expected=db.session.get(Milestone,second_milestone_id).version

    correction_payload={"expected_version":corrected_expected,
        "occurred_at":(datetime.now(timezone.utc)+timedelta(minutes=3)).isoformat(),
        "reason":"Concurrent PG correction"}
    def correct_milestone(key):
        with app.app_context():
            try:
                result=service.correct_checkpoint_milestone(
                    shipment_id,second_id,second_milestone_id,correction_payload,
                    {"id":ids["reporter"],"role":"expert"},key,
                )
                return ("ok",result["id"])
            except base.OperationalError as exc:
                return ("error",exc.code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        correction_outcomes=list(pool.map(lambda _ :correct_milestone("pg-correct-same-key"),range(2)))
    assert correction_outcomes==[("ok",second_milestone_id),("ok",second_milestone_id)]
    with app.app_context():
        assert MilestoneEvent.query.filter_by(
            milestone_id=second_milestone_id,event_type="corrected").count()==1
        assert OperationalAudit.query.filter_by(
            action="checkpoint.milestone_corrected",entity_id=second_milestone_id).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="checkpoint.milestone_corrected",aggregate_id=second_milestone_id).count()==1

    payload_a={"expected_version":1,"occurred_at":datetime.now(timezone.utc).isoformat()}
    payload_b={"expected_version":1,"occurred_at":(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()}
    with ThreadPoolExecutor(max_workers=2) as pool:
        different_outcomes=list(pool.map(
            lambda payload:checkpoint_command(third_id,"pg-different-payload",payload),
            [payload_a,payload_b],
        ))
    assert sum(outcome[0]=="ok" for outcome in different_outcomes)==1
    assert ("error","IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD") in different_outcomes
    with app.app_context():
        third_milestone=Milestone.query.filter_by(
            checkpoint_id=third_id,milestone_type="checkpoint_arrival").one()
        assert MilestoneEvent.query.filter_by(
            milestone_id=third_milestone.id,event_type="reported").count()==1
        assert OperationalAudit.query.filter_by(
            action="checkpoint.arrived",entity_id=third_id).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="checkpoint.arrived",aggregate_id=third_id).count()==1

        source_event_count=MilestoneEvent.query.join(Milestone).filter(
            Milestone.route_plan_id==plan_id,
        ).count()
        source_version=db.session.get(RoutePlan,plan_id).version
        first_checkpoint=db.session.get(OperationalCheckpoint,first["id"])
        superseded_item=OperationalWorkItem(
            organization_id=ids["org"], operational_shipment_id=shipment_id,
            route_plan_id=plan_id, checkpoint_id=first_checkpoint.id,
            milestone_id=None, work_type="REPLAN_REQUIRED", status="open",
            due_at=start, detected_at=start, severity="critical",
            reason="Existing source-plan action",
        )
        db.session.add(superseded_item);db.session.commit()
        superseded_item_id=superseded_item.id

    replan_payload={"expected_version":source_version,"reason":"Concurrent same-key replan"}
    def replan_command(source_id,key,payload):
        with app.app_context():
            try:
                result=service.replan(
                    shipment_id,source_id,payload,
                    {"id":ids["reporter"],"role":"expert"},key,
                )
                return ("ok",result["id"],result["revision_number"])
            except base.OperationalError as exc:
                return ("error",exc.code,None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        same_replan_outcomes=list(pool.map(
            lambda _:replan_command(
                plan_id,"pg-replan-same-key",replan_payload,
            ),range(2),
        ))
    assert same_replan_outcomes[0][0]=="ok"
    assert same_replan_outcomes[0]==same_replan_outcomes[1]
    target_id=same_replan_outcomes[0][1]
    with app.app_context():
        assert RoutePlan.query.filter_by(
            operational_shipment_id=shipment_id,is_active=True,
        ).one().id==target_id
        assert OperationalIdempotency.query.filter_by(
            operation="replan",command_resource_id=shipment_id,
            idempotency_key="pg-replan-same-key",
        ).count()==1
        assert OperationalAudit.query.filter_by(
            action="route_plan.replanned",entity_id=target_id,
        ).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="route_plan.replanned",aggregate_id=target_id,
        ).count()==1
        assert db.session.get(OperationalWorkItem,superseded_item_id).resolution_reason=="PLAN_SUPERSEDED"
        assert MilestoneEvent.query.join(Milestone).filter(
            Milestone.route_plan_id==plan_id,
        ).count()==source_event_count
        assert MilestoneEvent.query.join(Milestone).filter(
            Milestone.route_plan_id==target_id,
        ).count()==0
        target_version=db.session.get(RoutePlan,target_id).version

    competing_payload={"expected_version":target_version,"reason":"Competing replan"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        competing_outcomes=list(pool.map(
            lambda key:replan_command(target_id,key,competing_payload),
            ["pg-replan-winner-a","pg-replan-winner-b"],
        ))
    assert sum(outcome[0]=="ok" for outcome in competing_outcomes)==1
    assert ("error","ROUTE_PLAN_NOT_ACTIVE",None) in competing_outcomes
    with app.app_context():
        revisions=db.session.scalars(select(RoutePlan.revision_number).where(
            RoutePlan.operational_shipment_id==shipment_id,
        )).all()
        assert len(revisions)==len(set(revisions))
        assert RoutePlan.query.filter_by(
            operational_shipment_id=shipment_id,is_active=True,
        ).count()==1
