"""Phase 1B multi-leg route orchestration contracts."""
from datetime import datetime, timedelta, timezone

import pytest

from backend.extensions import db
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalAudit, OperationalCheckpoint,
    OperationalIdempotency, OperationalMembership, OperationalOutbox,
    OperationalWorkItem, RouteDependency, RouteLeg, RoutePlan,
)
from backend.services import operational_service as base
from backend.services import route_orchestration_service as service
from backend.tests.test_operational_vertical_slice import _auth, _payload, _user, operational_app


def _leg(app, sequence, origin, destination, start):
    return {
        "sequence_number": sequence, "origin": {"source_type": "province", "source_id": origin},
        "destination": {"source_type": "province", "source_id": destination},
        "transport_mode": "road", "planned_departure": start.isoformat(),
        "planned_arrival": (start + timedelta(hours=2)).isoformat(),
    }


def test_create_validate_activate_and_replan(operational_app):
    with operational_app.app_context():
        shipment, _ = base.create_from_accepted_quote(_payload(operational_app), _user(operational_app), "phase1b-source")
        source = RoutePlan.query.filter_by(operational_shipment_id=shipment.id).one()
        ids = operational_app.config["phase1a"]; start = datetime.now(timezone.utc) + timedelta(days=1)
        draft = service.create_plan(shipment.id, {"legs": [_leg(operational_app, 1, ids["origin"], ids["destination"], start)]}, _user(operational_app))
        assert draft["status"] == "draft" and draft["revision_number"] == 2
        result = service.validate_plan(shipment.id, draft["id"], _user(operational_app))
        assert result == {"valid": True, "errors": []}
        activated = service.activate_plan(shipment.id, draft["id"], {"expected_version": 1}, _user(operational_app))
        assert activated["status"] == "active"
        assert db.session.get(RoutePlan, source.id).status == "superseded"
        replanned = service.replan(shipment.id, draft["id"], {"expected_version": 2, "reason": "Border closure"}, _user(operational_app), "replan-1")
        replay = service.replan(shipment.id, draft["id"], {"expected_version": 2, "reason": "Border closure"}, _user(operational_app), "replan-1")
        assert replanned["id"] == replay["id"] and replanned["revision_number"] == 3
        assert OperationalIdempotency.query.filter_by(operation="replan").count() == 1


def test_validation_reports_gap_and_continuity(operational_app):
    with operational_app.app_context():
        shipment, _ = base.create_from_accepted_quote(_payload(operational_app), _user(operational_app), "phase1b-invalid")
        ids = operational_app.config["phase1a"]; start = datetime.now(timezone.utc) + timedelta(days=1)
        draft = service.create_plan(shipment.id, {}, _user(operational_app))
        plan = db.session.get(RoutePlan, draft["id"])
        first = service._add_leg(plan, _leg(operational_app, 1, ids["origin"], ids["destination"], start))
        second_payload = _leg(operational_app, 3, ids["origin"], ids["destination"], start + timedelta(hours=3))
        service._add_leg(plan, second_payload); db.session.commit()
        result = service.validate_plan(shipment.id, plan.id, _user(operational_app))
        assert result["valid"] is False
        assert {"ROUTE_SEQUENCE_GAP", "ROUTE_LOCATION_DISCONTINUITY"} <= {row["code"] for row in result["errors"]}


def test_checkpoint_state_machine_idempotency_and_timeline(operational_app):
    with operational_app.app_context():
        shipment, _ = base.create_from_accepted_quote(_payload(operational_app), _user(operational_app), "phase1b-checkpoint")
        ids = operational_app.config["phase1a"]; start = datetime.now(timezone.utc) + timedelta(hours=1)
        plan = service.create_plan(shipment.id, {"legs": [_leg(operational_app, 1, ids["origin"], ids["destination"], start)]}, _user(operational_app))
        leg = RouteLeg.query.filter_by(route_plan_id=plan["id"]).one()
        checkpoint = service.add_checkpoint(shipment.id, plan["id"], {
            "route_leg_id": leg.id, "sequence_number": 1, "checkpoint_type": "export_customs",
            "canonical_location_id": leg.origin_location_id,
            "planned_arrival_at": start.isoformat(), "planned_departure_at": (start + timedelta(minutes=30)).isoformat(),
        }, _user(operational_app))
        occurred = datetime.now(timezone.utc).isoformat()
        arrived = service.checkpoint_command(shipment.id, checkpoint["id"], {"expected_version": 1, "occurred_at": occurred}, _user(operational_app), "arrive-1", "arrive")
        assert arrived["status"] == "arrived"
        replay = service.checkpoint_command(shipment.id, checkpoint["id"], {"expected_version": 1, "occurred_at": occurred}, _user(operational_app), "arrive-1", "arrive")
        assert replay["id"] == arrived["id"]
        with pytest.raises(base.OperationalError) as conflict:
            service.checkpoint_command(shipment.id, checkpoint["id"], {"expected_version": 2, "occurred_at": (datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()}, _user(operational_app), "arrive-1", "arrive")
        assert conflict.value.code == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"
        assert {"planned", "projected", "actual", "delays", "dependencies", "open_exceptions"} <= service.timeline(shipment.id, _user(operational_app)).keys()


def _draft_with_checkpoint(app, key="graph"):
    shipment, _ = base.create_from_accepted_quote(_payload(app), _user(app), f"{key}-source")
    ids=app.config["phase1a"]; start=datetime.now(timezone.utc)+timedelta(hours=1)
    plan=service.create_plan(shipment.id,{"legs":[_leg(app,1,ids["origin"],ids["destination"],start)]},_user(app))
    leg=RouteLeg.query.filter_by(route_plan_id=plan["id"]).one()
    checkpoint=service.add_checkpoint(shipment.id,plan["id"],{"route_leg_id":leg.id,"sequence_number":1,
        "checkpoint_type":"export_customs","canonical_location_id":leg.origin_location_id,
        "planned_arrival_at":start.isoformat(),"planned_departure_at":(start+timedelta(minutes=30)).isoformat()},_user(app))
    return shipment,db.session.get(RoutePlan,plan["id"]),leg,db.session.get(OperationalCheckpoint,checkpoint["id"])


def test_replan_clones_full_graph_with_provenance_and_remapped_dependency(operational_app):
    with operational_app.app_context():
        shipment,plan,leg,first=_draft_with_checkpoint(operational_app,"full-graph")
        second=service._add_checkpoint(plan,{"route_leg_id":leg.id,"sequence_number":2,"checkpoint_type":"final_delivery",
            "canonical_location_id":leg.destination_location_id,"planned_arrival_at":(first.planned_departure_at.replace(tzinfo=timezone.utc)+timedelta(hours=1)).isoformat()},_user(operational_app))
        dependency=RouteDependency(route_plan_id=plan.id,predecessor_checkpoint_id=first.id,successor_checkpoint_id=second.id,dependency_type="finish_to_start")
        db.session.add(dependency)
        old=RoutePlan.query.filter(RoutePlan.operational_shipment_id==shipment.id,RoutePlan.id!=plan.id).one();old.status="superseded";old.is_active=False
        db.session.flush(); plan.status="active";plan.is_active=True
        db.session.commit()
        result=service.replan(shipment.id,plan.id,{"expected_version":1,"reason":"Complete graph reroute"},_user(operational_app),"full-replan")
        target=db.session.get(RoutePlan,result["id"])
        assert target.is_active and target.status=="active" and target.created_from_plan_id==plan.id
        assert db.session.get(RoutePlan,plan.id).status=="superseded"
        cloned_legs=RouteLeg.query.filter_by(route_plan_id=target.id).all()
        cloned_checkpoints=OperationalCheckpoint.query.filter_by(route_plan_id=target.id).all()
        assert len(cloned_legs)==1 and cloned_legs[0].source_route_leg_id==leg.id
        assert {c.source_checkpoint_id for c in cloned_checkpoints}=={first.id,second.id}
        clone_dep=RouteDependency.query.filter_by(route_plan_id=target.id).one()
        assert {clone_dep.predecessor_checkpoint_id,clone_dep.successor_checkpoint_id}=={c.id for c in cloned_checkpoints}
        assert Milestone.query.filter_by(route_plan_id=target.id).count()==Milestone.query.filter_by(route_plan_id=plan.id).count()
        assert all(m.source_milestone_id for m in Milestone.query.filter_by(route_plan_id=target.id))
        assert MilestoneEvent.query.count()==0


@pytest.mark.parametrize("failure_point", [
    "target_create", "leg_clone", "checkpoint_clone", "dependency_clone",
    "milestone_clone", "source_supersede", "target_activation",
    "before_audit", "before_outbox", "before_commit",
])
def test_replan_failure_rolls_back_the_entire_graph(operational_app, failure_point):
    with operational_app.app_context():
        shipment,plan,_,checkpoint=_draft_with_checkpoint(
            operational_app, f"rollback-{failure_point}",
        )
        old=RoutePlan.query.filter(
            RoutePlan.operational_shipment_id==shipment.id,
            RoutePlan.id!=plan.id,
        ).one()
        old.status="superseded";old.is_active=False
        plan.status="active";plan.is_active=True
        item=OperationalWorkItem(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id, route_plan_id=plan.id,
            checkpoint_id=checkpoint.id, milestone_id=None,
            work_type="REPLAN_REQUIRED", status="open",
            due_at=datetime.now(timezone.utc), reason="Existing action",
        )
        db.session.add(item);db.session.commit()
        counts={
            "plans":RoutePlan.query.count(), "legs":RouteLeg.query.count(),
            "checkpoints":OperationalCheckpoint.query.count(),
            "milestones":Milestone.query.count(),
            "audits":OperationalAudit.query.count(),
            "outbox":OperationalOutbox.query.count(),
        }

        with pytest.raises(RuntimeError):
            service.replan(
                shipment.id, plan.id,
                {"expected_version":1,"reason":"Injected rollback"},
                _user(operational_app), f"rollback-{failure_point}",
                _fail_at=failure_point,
            )

        assert db.session.get(RoutePlan,plan.id).is_active
        assert db.session.get(RoutePlan,plan.id).status=="active"
        assert db.session.get(OperationalWorkItem,item.id).status=="open"
        assert RoutePlan.query.count()==counts["plans"]
        assert RouteLeg.query.count()==counts["legs"]
        assert OperationalCheckpoint.query.count()==counts["checkpoints"]
        assert Milestone.query.count()==counts["milestones"]
        assert OperationalAudit.query.count()==counts["audits"]
        assert OperationalOutbox.query.count()==counts["outbox"]
        assert OperationalIdempotency.query.filter_by(
            operation="replan",idempotency_key=f"rollback-{failure_point}",
        ).count()==0


def test_replan_resolves_only_source_plan_items_and_records_provenance(operational_app):
    with operational_app.app_context():
        shipment,plan,_,checkpoint=_draft_with_checkpoint(
            operational_app,"supersession",
        )
        old=RoutePlan.query.filter(
            RoutePlan.operational_shipment_id==shipment.id,
            RoutePlan.id!=plan.id,
        ).one()
        old.status="superseded";old.is_active=False
        plan.status="active";plan.is_active=True
        item=OperationalWorkItem(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id, route_plan_id=plan.id,
            checkpoint_id=checkpoint.id, milestone_id=None,
            work_type="REPLAN_REQUIRED", status="open",
            due_at=datetime.now(timezone.utc), reason="Existing action",
        )
        db.session.add(item);db.session.commit()

        result=service.replan(
            shipment.id,plan.id,
            {"expected_version":1,"reason":"Supersession consistency"},
            _user(operational_app),"supersession-replan",
        )

        resolved=db.session.get(OperationalWorkItem,item.id)
        assert resolved.status=="resolved"
        assert resolved.resolution_reason=="PLAN_SUPERSEDED"
        assert resolved.resolved_at and resolved.resolved_by_user_id
        assert OperationalWorkItem.query.filter_by(
            route_plan_id=result["id"],
        ).count()==0
        audit=OperationalAudit.query.filter_by(
            action="route_plan.replanned",entity_id=result["id"],
        ).one()
        assert audit.metadata_json["source_plan_id"]==plan.id
        assert audit.metadata_json["target_revision"]==result["revision_number"]
        outbox=OperationalOutbox.query.filter_by(
            event_type="route_plan.replanned",aggregate_id=result["id"],
        ).one()
        assert outbox.payload["source_plan_id"]==plan.id


def test_replan_stable_conflict_contract(operational_app):
    with operational_app.app_context():
        shipment,plan,_,_=_draft_with_checkpoint(operational_app,"conflicts")
        old=RoutePlan.query.filter(
            RoutePlan.operational_shipment_id==shipment.id,
            RoutePlan.id!=plan.id,
        ).one()
        old.status="superseded";old.is_active=False
        plan.status="active";plan.is_active=True
        db.session.commit()
        with pytest.raises(base.OperationalError) as stale:
            service.replan(
                shipment.id,plan.id,
                {"expected_version":99,"reason":"Stale"},
                _user(operational_app),"stale-replan",
            )
        assert stale.value.code=="STALE_ROUTE_PLAN_VERSION"
        service.replan(
            shipment.id,plan.id,
            {"expected_version":1,"reason":"Winner"},
            _user(operational_app),"winner-replan",
        )
        with pytest.raises(base.OperationalError) as inactive:
            service.replan(
                shipment.id,plan.id,
                {"expected_version":1,"reason":"Loser"},
                _user(operational_app),"loser-replan",
            )
        assert inactive.value.code=="ROUTE_PLAN_NOT_ACTIVE"


def test_replan_changes_future_graph_without_mutating_source(operational_app):
    with operational_app.app_context():
        shipment,plan,leg,checkpoint=_draft_with_checkpoint(
            operational_app,"future-change",
        )
        old=RoutePlan.query.filter(
            RoutePlan.operational_shipment_id==shipment.id,
            RoutePlan.id!=plan.id,
        ).one()
        old.status="superseded";old.is_active=False
        plan.status="active";plan.is_active=True
        db.session.commit()
        source_departure=leg.planned_departure
        source_note=checkpoint.notes
        changed_departure=source_departure.replace(
            tzinfo=source_departure.tzinfo or timezone.utc,
        )+timedelta(minutes=15)
        changed_arrival=leg.planned_arrival.replace(
            tzinfo=leg.planned_arrival.tzinfo or timezone.utc,
        )+timedelta(minutes=15)

        result=service.replan(
            shipment.id,plan.id,{
                "expected_version":1,"reason":"Future schedule change",
                "changes":{
                    "legs":[{
                        "source_route_leg_id":leg.id,
                        "planned_departure":changed_departure.isoformat(),
                        "planned_arrival":changed_arrival.isoformat(),
                        "carrier_reference":"NEW-REF",
                    }],
                    "checkpoints":[{
                        "source_checkpoint_id":checkpoint.id,
                        "notes":"Target-only update",
                    }],
                    "dependencies":[],
                },
            },_user(operational_app),"future-change-replan",
        )

        target_leg=RouteLeg.query.filter_by(route_plan_id=result["id"]).one()
        target_checkpoint=OperationalCheckpoint.query.filter_by(
            route_plan_id=result["id"],
        ).one()
        assert target_leg.planned_departure.replace(tzinfo=timezone.utc)==changed_departure
        assert target_leg.carrier_reference=="NEW-REF"
        assert target_checkpoint.notes=="Target-only update"
        assert db.session.get(RouteLeg,leg.id).planned_departure==source_departure
        assert db.session.get(OperationalCheckpoint,checkpoint.id).notes==source_note


def test_replan_rejects_completed_segment_change_atomically(operational_app):
    with operational_app.app_context():
        shipment,plan,leg,_=_draft_with_checkpoint(
            operational_app,"completed-change",
        )
        old=RoutePlan.query.filter(
            RoutePlan.operational_shipment_id==shipment.id,
            RoutePlan.id!=plan.id,
        ).one()
        old.status="superseded";old.is_active=False
        plan.status="active";plan.is_active=True
        leg.status="completed"
        db.session.commit()
        initial_plan_count=RoutePlan.query.count()

        with pytest.raises(base.OperationalError) as immutable:
            service.replan(
                shipment.id,plan.id,{
                    "expected_version":1,"reason":"Illegal history edit",
                    "changes":{"legs":[{
                        "source_route_leg_id":leg.id,
                        "carrier_reference":"ILLEGAL",
                    }]},
                },_user(operational_app),"completed-change-replan",
            )

        assert immutable.value.code=="COMPLETED_ROUTE_SEGMENT_IMMUTABLE"
        assert db.session.get(RoutePlan,plan.id).is_active
        assert RoutePlan.query.count()==initial_plan_count


def test_idempotency_is_resource_and_command_scoped(operational_app):
    with operational_app.app_context():
        shipment,plan,_,checkpoint=_draft_with_checkpoint(operational_app,"scope-one")
        occurred=datetime.now(timezone.utc).isoformat()
        service.checkpoint_command(shipment.id,checkpoint.id,{"expected_version":1,"occurred_at":occurred},_user(operational_app),"shared-key","arrive")
        second=service._add_checkpoint(plan,{"route_leg_id":checkpoint.route_leg_id,"sequence_number":2,"checkpoint_type":"final_delivery",
            "canonical_location_id":checkpoint.canonical_location_id,"planned_arrival_at":(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()},_user(operational_app));db.session.commit()
        service.checkpoint_command(shipment.id,second.id,{"expected_version":1,"occurred_at":occurred},_user(operational_app),"shared-key","arrive")
        assert OperationalIdempotency.query.filter_by(idempotency_key="shared-key").count()==2
        assert {row.command_resource_id for row in OperationalIdempotency.query.filter_by(idempotency_key="shared-key")}=={checkpoint.id,second.id}


def test_idempotency_hash_is_canonical_and_command_scoped(operational_app):
    assert base._hash({"expected_version": 1, "nested": {"b": 2, "a": 1}}) == base._hash(
        {"nested": {"a": 1, "b": 2}, "expected_version": 1}
    )
    with operational_app.app_context():
        shipment,_,_,checkpoint=_draft_with_checkpoint(operational_app,"command-scope")
        first_hash=base._hash({"expected_version":1})
        service._reserve_idempotency(
            shipment.organization_id, "checkpoint_arrive_report", "checkpoint",
            checkpoint.id, "command-shared", first_hash, checkpoint.id,
        )
        service._reserve_idempotency(
            shipment.organization_id, "checkpoint_depart_report", "checkpoint",
            checkpoint.id, "command-shared", first_hash, checkpoint.id,
        )
        db.session.commit()
        assert OperationalIdempotency.query.filter_by(idempotency_key="command-shared").count()==2


def test_cross_plan_service_validation_and_organization_isolation(operational_app):
    with operational_app.app_context():
        shipment,plan,leg,checkpoint=_draft_with_checkpoint(operational_app,"scope-validation")
        other=service.create_plan(shipment.id,{"legs":[]},_user(operational_app))
        other_plan=db.session.get(RoutePlan,other["id"])
        with pytest.raises(base.OperationalError) as checkpoint_error:
            service.add_checkpoint(shipment.id,other_plan.id,{
                "route_leg_id":leg.id,"sequence_number":1,"checkpoint_type":"final_delivery",
                "canonical_location_id":leg.destination_location_id,
                "planned_arrival_at":(datetime.now(timezone.utc)+timedelta(hours=4)).isoformat(),
            },_user(operational_app))
        assert checkpoint_error.value.code=="CROSS_PLAN_REFERENCE_NOT_ALLOWED"
        foreign=service._add_checkpoint(other_plan,{
            "sequence_number":1,"checkpoint_type":"final_delivery",
            "canonical_location_id":leg.destination_location_id,
            "planned_arrival_at":(datetime.now(timezone.utc)+timedelta(hours=4)).isoformat(),
        },_user(operational_app))
        db.session.commit()
        with pytest.raises(base.OperationalError) as dependency_error:
            service.add_dependency(shipment.id,plan.id,{
                "predecessor_checkpoint_id":checkpoint.id,
                "successor_checkpoint_id":foreign.id,
            },_user(operational_app))
        assert dependency_error.value.code=="CROSS_PLAN_REFERENCE_NOT_ALLOWED"
        with pytest.raises(base.OperationalError) as isolation_error:
            service.get_plan(shipment.id,plan.id,_user(operational_app,"outsider"))
        assert isolation_error.value.code=="RESOURCE_NOT_FOUND"


def test_http_cross_plan_and_direct_id_isolation_contract(operational_app):
    with operational_app.app_context():
        shipment,plan,leg,_=_draft_with_checkpoint(operational_app,"http-scope")
        other=service.create_plan(shipment.id,{"legs":[]},_user(operational_app))
        shipment_id,plan_id,other_plan_id,leg_id=shipment.public_id,plan.id,other["id"],leg.id
    client=operational_app.test_client()
    cross_plan=client.post(
        f"/api/operational-shipments/{shipment_id}/route-plans/{other_plan_id}/checkpoints",
        json={"route_leg_id":leg_id,"sequence_number":1,"checkpoint_type":"final_delivery",
              "canonical_location_id":operational_app.config["phase1a"]["destination"],
              "planned_arrival_at":(datetime.now(timezone.utc)+timedelta(hours=4)).isoformat()},
        headers=_auth(operational_app),
    )
    assert cross_plan.status_code == 409
    assert cross_plan.json["error"]["code"] == "CROSS_PLAN_REFERENCE_NOT_ALLOWED"
    assert cross_plan.json["error"]["fields"] == []
    assert isinstance(cross_plan.json["error"]["message"], str)
    assert "traceback" not in cross_plan.get_data(as_text=True).lower()
    assert "constraint" not in cross_plan.get_data(as_text=True).lower()
    hidden=client.get(
        f"/api/operational-shipments/{shipment_id}/route-plans/{plan_id}",
        headers=_auth(operational_app,"outsider"),
    )
    assert hidden.status_code == 404 and hidden.json["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_http_scoped_idempotency_and_membership_permission_contract(operational_app):
    with operational_app.app_context():
        shipment,plan,_,first=_draft_with_checkpoint(operational_app,"http-idempotency")
        second=service._add_checkpoint(plan,{"route_leg_id":first.route_leg_id,"sequence_number":2,
            "checkpoint_type":"final_delivery","canonical_location_id":first.canonical_location_id,
            "planned_arrival_at":(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()},
            _user(operational_app))
        db.session.commit()
        shipment_id,first_id,second_id=shipment.public_id,first.id,second.id
    client=operational_app.test_client()
    occurred=datetime.now(timezone.utc).isoformat()
    headers={**_auth(operational_app),"Idempotency-Key":"http-shared"}
    first_response=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{first_id}/arrive",
        json={"expected_version":1,"occurred_at":occurred},headers=headers,
    )
    independent=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{second_id}/arrive",
        json={"expected_version":1,"occurred_at":occurred},headers=headers,
    )
    assert first_response.status_code == 200 and independent.status_code == 200
    mismatch=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{first_id}/arrive",
        json={"expected_version":2,"occurred_at":(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()},
        headers=headers,
    )
    assert mismatch.status_code == 409
    assert mismatch.json["error"]["code"] == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"
    assert "traceback" not in mismatch.get_data(as_text=True).lower()
    with operational_app.app_context():
        membership=OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]).one()
        membership.permissions=["operational_shipment.read"]
        db.session.commit()
    forbidden=client.post(
        f"/api/operational-shipments/{shipment_id}/route-plans",
        json={},headers=_auth(operational_app),
    )
    assert forbidden.status_code == 403 and forbidden.json["error"]["code"] == "FORBIDDEN_OPERATION"
    with operational_app.app_context():
        membership=OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]).one()
        membership.is_active=False
        db.session.commit()
    inactive=client.get(
        f"/api/operational-shipments/{shipment_id}/route-plans",
        headers=_auth(operational_app),
    )
    assert inactive.status_code == 403 and inactive.json["error"]["code"] == "TENANT_SCOPE_VIOLATION"


def test_checkpoint_report_verify_correct_and_actual_derivation(operational_app):
    with operational_app.app_context():
        shipment,_,_,checkpoint=_draft_with_checkpoint(operational_app,"lifecycle")
        arrival=Milestone.query.filter_by(checkpoint_id=checkpoint.id,milestone_type="checkpoint_arrival").one()
        occurred=datetime.now(timezone.utc)-timedelta(minutes=5)
        service.checkpoint_command(shipment.id,checkpoint.id,{"expected_version":1,"occurred_at":occurred.isoformat()},_user(operational_app),"arrival-report","arrive")
        assert checkpoint.actual_arrival_at is None and arrival.verification_state=="reported"
        with pytest.raises(base.OperationalError) as separation:
            service.verify_checkpoint_milestone(
                shipment.id,checkpoint.id,arrival.id,arrival.version,_user(operational_app),"self-verify"
            )
        assert separation.value.code=="REPORTER_CANNOT_VERIFY_OWN_EVENT"
        verified=service.verify_checkpoint_milestone(
            shipment.id,checkpoint.id,arrival.id,arrival.version,_user(operational_app,"verifier"),"verify-arrival"
        )
        replay=service.verify_checkpoint_milestone(
            shipment.id,checkpoint.id,arrival.id,arrival.version-1,_user(operational_app,"verifier"),"verify-arrival"
        )
        assert replay["milestone"]["version"]==verified["milestone"]["version"]
        assert checkpoint.actual_arrival_at.replace(tzinfo=timezone.utc)==occurred and arrival.verification_state=="verified"
        old_actual=checkpoint.actual_arrival_at
        corrected=service.correct_checkpoint_milestone(shipment.id,checkpoint.id,arrival.id,{"expected_version":arrival.version,
            "occurred_at":(occurred+timedelta(minutes=1)).isoformat(),"reason":"Operator timestamp correction"},_user(operational_app),"arrival-correct")
        assert corrected["verification_state"]=="reported"
        event=MilestoneEvent.query.filter_by(milestone_id=arrival.id,event_type="corrected").one()
        assert event.supersedes_event_id and event.reason
        assert checkpoint.actual_arrival_at is None and old_actual != checkpoint.actual_arrival_at
        reverified=service.verify_checkpoint_milestone(
            shipment.id,checkpoint.id,arrival.id,arrival.version,_user(operational_app,"verifier"),"reverify-arrival"
        )
        assert reverified["milestone"]["verification_state"]=="verified"
        assert checkpoint.actual_arrival_at.replace(tzinfo=timezone.utc)==occurred+timedelta(minutes=1)
        assert [row.event_type for row in MilestoneEvent.query.filter_by(
            milestone_id=arrival.id).order_by(MilestoneEvent.id)]==[
                "reported","verified","corrected","verified",
            ]


def test_reporter_checkpoint_correction_is_forbidden_without_side_effects(operational_app):
    with operational_app.app_context():
        shipment,_,_,checkpoint=_draft_with_checkpoint(operational_app,"correction-auth")
        arrival=Milestone.query.filter_by(
            checkpoint_id=checkpoint.id,milestone_type="checkpoint_arrival",
        ).one()
        occurred=datetime.now(timezone.utc)-timedelta(minutes=5)
        service.checkpoint_command(
            shipment.id,checkpoint.id,
            {"expected_version":1,"occurred_at":occurred.isoformat()},
            _user(operational_app),"correction-auth-report","arrive",
        )
        service.verify_checkpoint_milestone(
            shipment.id,checkpoint.id,arrival.id,arrival.version,
            _user(operational_app,"verifier"),"correction-auth-verify",
        )
        membership=OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"],
        ).one()
        membership.permissions=[
            "operational_shipment.read","route_plan.read","checkpoint.read",
            "checkpoint.report",
        ]
        db.session.commit()
        shipment_id,checkpoint_id,milestone_id=shipment.public_id,checkpoint.id,arrival.id
        expected_version=arrival.version
        before={
            "events":MilestoneEvent.query.count(),
            "corrected":MilestoneEvent.query.filter_by(event_type="corrected").count(),
            "audits":OperationalAudit.query.count(),
            "outbox":OperationalOutbox.query.count(),
            "version":arrival.version,
            "state":arrival.verification_state,
            "occurred_at":arrival.occurred_at,
            "actual":checkpoint.actual_arrival_at,
            "projected":checkpoint.projected_arrival_at,
        }

    response=operational_app.test_client().post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/correct",
        json={
            "expected_version":expected_version,
            "occurred_at":(occurred+timedelta(minutes=1)).isoformat(),
            "reason":"Reporter must not be allowed",
        },
        headers={**_auth(operational_app),"Idempotency-Key":"correction-auth-denied"},
    )
    assert response.status_code==403
    assert response.json["error"]["code"]=="FORBIDDEN_OPERATION"

    with operational_app.app_context():
        arrival=db.session.get(Milestone,milestone_id)
        checkpoint=db.session.get(OperationalCheckpoint,checkpoint_id)
        after={
            "events":MilestoneEvent.query.count(),
            "corrected":MilestoneEvent.query.filter_by(event_type="corrected").count(),
            "audits":OperationalAudit.query.count(),
            "outbox":OperationalOutbox.query.count(),
            "version":arrival.version,
            "state":arrival.verification_state,
            "occurred_at":arrival.occurred_at,
            "actual":checkpoint.actual_arrival_at,
            "projected":checkpoint.projected_arrival_at,
        }
        assert after==before
        assert OperationalIdempotency.query.filter_by(
            operation="checkpoint_milestone_correct",
            idempotency_key="correction-auth-denied",
        ).count()==0

        corrected=service.correct_checkpoint_milestone(
            shipment_id,checkpoint_id,milestone_id,
            {
                "expected_version":expected_version,
                "occurred_at":(occurred+timedelta(minutes=1)).isoformat(),
                "reason":"Authorised correction",
            },
            _user(operational_app,"verifier"),"correction-auth-allowed",
        )
        assert corrected["verification_state"]=="reported"
        assert MilestoneEvent.query.filter_by(
            milestone_id=milestone_id,event_type="corrected",
        ).count()==1
        assert OperationalAudit.query.filter_by(
            action="checkpoint.milestone_corrected",entity_id=milestone_id,
        ).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="checkpoint.milestone_corrected",aggregate_id=milestone_id,
        ).count()==1


def test_http_checkpoint_lifecycle_correction_and_reverification(operational_app):
    with operational_app.app_context():
        shipment,_,_,checkpoint=_draft_with_checkpoint(operational_app,"http-lifecycle")
        arrival=Milestone.query.filter_by(
            checkpoint_id=checkpoint.id,milestone_type="checkpoint_arrival").one()
        shipment_id,checkpoint_id,milestone_id=shipment.public_id,checkpoint.id,arrival.id
    client=operational_app.test_client()
    occurred=datetime.now(timezone.utc)-timedelta(minutes=5)
    reported=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/arrive",
        json={"expected_version":1,"occurred_at":occurred.isoformat()},
        headers={**_auth(operational_app),"Idempotency-Key":"http-lifecycle-report"},
    )
    assert reported.status_code == 200
    self_verify=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/verify",
        json={"expected_version":2},
        headers={**_auth(operational_app),"Idempotency-Key":"http-lifecycle-self-verify"},
    )
    assert self_verify.status_code == 403
    assert self_verify.json["error"]["code"]=="REPORTER_CANNOT_VERIFY_OWN_EVENT"
    verified=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/verify",
        json={"expected_version":2},
        headers={**_auth(operational_app,"verifier"),"Idempotency-Key":"http-lifecycle-verify"},
    )
    assert verified.status_code == 200
    stale=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/verify",
        json={"expected_version":2},
        headers={**_auth(operational_app,"verifier"),"Idempotency-Key":"http-lifecycle-stale"},
    )
    assert stale.status_code == 409 and stale.json["error"]["code"]=="STALE_MILESTONE_VERSION"
    missing_reason=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/correct",
        json={"expected_version":3,"occurred_at":occurred.isoformat()},
        headers={**_auth(operational_app),"Idempotency-Key":"http-lifecycle-no-reason"},
    )
    assert missing_reason.status_code == 422
    assert missing_reason.json["error"]["code"]=="CORRECTION_REASON_REQUIRED"
    corrected_at=occurred+timedelta(minutes=2)
    corrected=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/correct",
        json={"expected_version":3,"occurred_at":corrected_at.isoformat(),"reason":"Corrected manifest time"},
        headers={**_auth(operational_app),"Idempotency-Key":"http-lifecycle-correct"},
    )
    assert corrected.status_code == 201
    with operational_app.app_context():
        assert db.session.get(OperationalCheckpoint,checkpoint_id).actual_arrival_at is None
    reverified=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/verify",
        json={"expected_version":4},
        headers={**_auth(operational_app,"verifier"),"Idempotency-Key":"http-lifecycle-reverify"},
    )
    assert reverified.status_code == 200
    replay=client.post(
        f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/verify",
        json={"expected_version":4},
        headers={**_auth(operational_app,"verifier"),"Idempotency-Key":"http-lifecycle-reverify"},
    )
    assert replay.status_code == 200 and replay.json==reverified.json
    with operational_app.app_context():
        row=db.session.get(OperationalCheckpoint,checkpoint_id)
        assert row.actual_arrival_at.replace(tzinfo=timezone.utc)==corrected_at
        assert MilestoneEvent.query.filter_by(milestone_id=milestone_id).count()==4


def test_http_checkpoint_verifier_authorization_and_tenant_isolation(operational_app):
    with operational_app.app_context():
        shipment,_,_,checkpoint=_draft_with_checkpoint(operational_app,"http-verifier-auth")
        arrival=Milestone.query.filter_by(
            checkpoint_id=checkpoint.id,milestone_type="checkpoint_arrival").one()
        service.checkpoint_command(
            shipment.id,checkpoint.id,
            {"expected_version":1,"occurred_at":datetime.now(timezone.utc).isoformat()},
            _user(operational_app),"verifier-auth-report","arrive",
        )
        shipment_id,checkpoint_id,milestone_id=shipment.public_id,checkpoint.id,arrival.id
        reporter_membership=OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]).one()
        reporter_membership.permissions=[
            permission for permission in reporter_membership.permissions
            if permission != "checkpoint.verify"
        ]
        db.session.commit()
    url=f"/api/operational-shipments/{shipment_id}/checkpoints/{checkpoint_id}/milestones/{milestone_id}/verify"
    client=operational_app.test_client()
    unauthorized=client.post(
        url,json={"expected_version":2},
        headers={**_auth(operational_app),"Idempotency-Key":"unauthorized-verify"},
    )
    assert unauthorized.status_code == 403 and unauthorized.json["error"]["code"]=="FORBIDDEN_OPERATION"
    with operational_app.app_context():
        verifier_membership=OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["verifier"]).one()
        verifier_membership.is_active=False
        db.session.commit()
    inactive=client.post(
        url,json={"expected_version":2},
        headers={**_auth(operational_app,"verifier"),"Idempotency-Key":"inactive-verify"},
    )
    assert inactive.status_code == 403 and inactive.json["error"]["code"]=="TENANT_SCOPE_VIOLATION"
    foreign=client.post(
        url,json={"expected_version":2},
        headers={**_auth(operational_app,"outsider"),"Idempotency-Key":"foreign-verify"},
    )
    assert foreign.status_code == 404 and foreign.json["error"]["code"]=="RESOURCE_NOT_FOUND"


def test_delay_reconciliation_is_idempotent_and_auto_resolves(operational_app):
    with operational_app.app_context():
        shipment,plan,_,checkpoint=_draft_with_checkpoint(operational_app,"delay")
        old=RoutePlan.query.filter(RoutePlan.operational_shipment_id==shipment.id,RoutePlan.id!=plan.id).one();old.status="superseded";old.is_active=False
        plan.status="active";plan.is_active=True
        checkpoint.planned_arrival_at=datetime.now(timezone.utc)-timedelta(hours=30)
        checkpoint.projected_arrival_at=checkpoint.planned_arrival_at;db.session.commit()
        first=service.reconcile_route_exceptions(shipment.id,_user(operational_app))
        second=service.reconcile_route_exceptions(shipment.id,_user(operational_app))
        assert first["opened"]==2 and second["opened"]==0
        assert OperationalWorkItem.query.filter_by(route_plan_id=plan.id,status="open").count()==2
        checkpoint.status="completed";db.session.commit()
        cleared=service.reconcile_route_exceptions(shipment.id,_user(operational_app))
        assert cleared["resolved"]==2 and OperationalWorkItem.query.filter_by(route_plan_id=plan.id,status="open").count()==0


def test_exception_manual_resolution_reopens_when_condition_persists(operational_app):
    with operational_app.app_context():
        shipment,plan,_,checkpoint=_draft_with_checkpoint(operational_app,"exception-reopen")
        old=RoutePlan.query.filter(RoutePlan.operational_shipment_id==shipment.id,RoutePlan.id!=plan.id).one()
        old.status="superseded";old.is_active=False;plan.status="active";plan.is_active=True
        checkpoint.planned_arrival_at=datetime.now(timezone.utc)-timedelta(hours=2)
        checkpoint.projected_arrival_at=checkpoint.planned_arrival_at;db.session.commit()
        service.reconcile_route_exceptions(shipment.id,_user(operational_app))
        item=OperationalWorkItem.query.filter_by(
            route_plan_id=plan.id,work_type="CHECKPOINT_OVERDUE",status="open",
        ).one()
        service.resolve_route_exception(
            item.id,{"expected_version":item.version,"reason":"Operator accepted risk"},_user(operational_app),
        )
        result=service.reconcile_route_exceptions(shipment.id,_user(operational_app))
        item=db.session.get(OperationalWorkItem,item.id)
        assert result["reopened"]==1
        assert item.status=="open" and item.occurrence_count==2 and item.resolution_source is None
        assert OperationalWorkItem.query.filter_by(
            route_plan_id=plan.id,checkpoint_id=checkpoint.id,
            work_type="CHECKPOINT_OVERDUE",status="open",
        ).count()==1


def test_exception_reconcile_command_replays_and_rejects_stale_plan(operational_app):
    with operational_app.app_context():
        shipment,plan,_,checkpoint=_draft_with_checkpoint(operational_app,"exception-command")
        old=RoutePlan.query.filter(RoutePlan.operational_shipment_id==shipment.id,RoutePlan.id!=plan.id).one()
        old.status="superseded";old.is_active=False;plan.status="active";plan.is_active=True
        checkpoint.planned_arrival_at=datetime.now(timezone.utc)-timedelta(hours=2)
        checkpoint.projected_arrival_at=checkpoint.planned_arrival_at;db.session.commit()
        calculation_time=datetime.now(timezone.utc)
        first=service.reconcile_route_exceptions(
            shipment.id,_user(operational_app),plan.version,calculation_time,"exception-command-key",
        )
        replay=service.reconcile_route_exceptions(
            shipment.id,_user(operational_app),plan.version,calculation_time,"exception-command-key",
        )
        assert first["opened"]==1 and replay["replayed"] is True
        assert OperationalAudit.query.filter_by(action="route_exceptions.reconciled").count()==1
        with pytest.raises(base.OperationalError) as stale:
            service.reconcile_route_exceptions(
                shipment.id,_user(operational_app),plan.version+1,calculation_time,"different-key",
            )
        assert stale.value.code=="STALE_ROUTE_PLAN_VERSION"


def test_exception_manual_resolution_is_idempotent_and_atomic(operational_app):
    with operational_app.app_context():
        shipment,plan,_,checkpoint=_draft_with_checkpoint(operational_app,"exception-resolve-command")
        old=RoutePlan.query.filter(RoutePlan.operational_shipment_id==shipment.id,RoutePlan.id!=plan.id).one()
        old.status="superseded";old.is_active=False;plan.status="active";plan.is_active=True
        checkpoint.planned_arrival_at=datetime.now(timezone.utc)-timedelta(hours=2)
        checkpoint.projected_arrival_at=checkpoint.planned_arrival_at;db.session.commit()
        service.reconcile_route_exceptions(shipment.id,_user(operational_app))
        item=OperationalWorkItem.query.filter_by(
            route_plan_id=plan.id,work_type="CHECKPOINT_OVERDUE",status="open",
        ).one()
        payload={"expected_version":item.version,"reason":"Operator accepted risk"}
        first=service._resolve_route_exception(
            item.id,payload,_user(operational_app),"manual-resolve-key",
        )
        replay=service._resolve_route_exception(
            item.id,payload,_user(operational_app),"manual-resolve-key",
        )
        assert first["replayed"] is False and replay["replayed"] is True
        assert OperationalAudit.query.filter_by(
            action="route_exception.manually_resolved",entity_id=item.id,
        ).count()==1
        assert OperationalOutbox.query.filter_by(
            event_type="route_exception.manually_resolved",aggregate_id=item.id,
        ).count()==1
        with pytest.raises(base.OperationalError) as mismatch:
            service._resolve_route_exception(
                item.id,{**payload,"reason":"Different reason"},_user(operational_app),
                "manual-resolve-key",
            )
        assert mismatch.value.code=="IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"


def _activate_for_timeline(shipment, plan):
    source = RoutePlan.query.filter(
        RoutePlan.operational_shipment_id == shipment.id, RoutePlan.id != plan.id,
    ).one()
    source.status = "superseded"
    source.is_active = False
    plan.status = "active"
    plan.is_active = True


def test_projected_timeline_chain_is_topological_and_synchronizes_entities(operational_app):
    with operational_app.app_context():
        shipment, plan, leg, first = _draft_with_checkpoint(operational_app, "timeline-chain")
        second = service._add_checkpoint(plan, {
            "route_leg_id": leg.id, "sequence_number": 3, "checkpoint_type": "unloading",
            "canonical_location_id": leg.destination_location_id,
            "planned_arrival_at": (first.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=1)).isoformat(),
            "planned_departure_at": (first.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=2)).isoformat(),
        }, _user(operational_app))
        third = service._add_checkpoint(plan, {
            "route_leg_id": leg.id, "sequence_number": 2, "checkpoint_type": "final_delivery",
            "canonical_location_id": leg.destination_location_id,
            "planned_arrival_at": (first.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=3)).isoformat(),
        }, _user(operational_app))
        # Sequence and insertion order deliberately disagree with dependency order.
        db.session.add_all([
            RouteDependency(route_plan_id=plan.id, predecessor_checkpoint_id=first.id,
                            successor_checkpoint_id=second.id, dependency_type="finish_to_start"),
            RouteDependency(route_plan_id=plan.id, predecessor_checkpoint_id=second.id,
                            successor_checkpoint_id=third.id, dependency_type="finish_to_start"),
        ])
        first.actual_arrival_at = first.planned_arrival_at.replace(tzinfo=timezone.utc) + timedelta(hours=4)
        first.actual_departure_at = first.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=4)
        _activate_for_timeline(shipment, plan)
        db.session.commit()
        before_planned = [(row.id, row.planned_arrival_at, row.planned_departure_at)
                          for row in (first, second, third)]

        result = service.recalculate_projected_timeline(
            shipment.id, _user(operational_app), plan.version, "timeline-chain-reconcile",
        )

        assert second.projected_arrival_at >= first.actual_departure_at + timedelta(hours=1)
        assert third.projected_arrival_at >= second.projected_departure_at + timedelta(hours=1)
        assert leg.projected_departure == first.projected_arrival_at
        assert leg.projected_arrival == third.projected_departure_at
        assert [(row.id, row.planned_arrival_at, row.planned_departure_at)
                for row in (first, second, third)] == before_planned
        assert all(m.projected_at for m in Milestone.query.filter(
            Milestone.checkpoint_id.in_([first.id, second.id, third.id])))
        replay = service.recalculate_projected_timeline(
            shipment.id, _user(operational_app), plan.version - 1, "timeline-chain-reconcile",
        )
        assert replay["replayed"] is True
        assert OperationalAudit.query.filter_by(action="route_plan.timeline_reconciled").count() == 1
        assert OperationalOutbox.query.filter_by(event_type="route_plan.timeline_reconciled").count() == 1
        assert result["actual_override_count"] == 2


def test_projected_timeline_fan_in_uses_latest_predecessor_and_cycle_is_atomic(operational_app):
    with operational_app.app_context():
        shipment, plan, leg, first = _draft_with_checkpoint(operational_app, "timeline-fanin")
        second = service._add_checkpoint(plan, {
            "route_leg_id": leg.id, "sequence_number": 2, "checkpoint_type": "unloading",
            "canonical_location_id": leg.destination_location_id,
            "planned_arrival_at": (first.planned_arrival_at.replace(tzinfo=timezone.utc) + timedelta(minutes=15)).isoformat(),
            "planned_departure_at": (first.planned_arrival_at.replace(tzinfo=timezone.utc) + timedelta(minutes=30)).isoformat(),
        }, _user(operational_app))
        successor = service._add_checkpoint(plan, {
            "route_leg_id": leg.id, "sequence_number": 3, "checkpoint_type": "final_delivery",
            "canonical_location_id": leg.destination_location_id,
            "planned_arrival_at": (first.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=2)).isoformat(),
        }, _user(operational_app))
        db.session.add_all([
            RouteDependency(route_plan_id=plan.id, predecessor_checkpoint_id=first.id,
                            successor_checkpoint_id=successor.id, dependency_type="finish_to_start"),
            RouteDependency(route_plan_id=plan.id, predecessor_checkpoint_id=second.id,
                            successor_checkpoint_id=successor.id, dependency_type="finish_to_start"),
        ])
        first.actual_arrival_at = first.planned_arrival_at.replace(tzinfo=timezone.utc) + timedelta(hours=1)
        first.actual_departure_at = first.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=1)
        second.actual_arrival_at = second.planned_arrival_at.replace(tzinfo=timezone.utc) + timedelta(hours=3)
        second.actual_departure_at = second.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=3)
        _activate_for_timeline(shipment, plan)
        db.session.commit()
        service.recalculate_projected_timeline(shipment.id, _user(operational_app), plan.version, "fanin")
        assert successor.projected_arrival_at >= second.actual_departure_at
        previous = successor.projected_arrival_at
        audits = OperationalAudit.query.count()
        db.session.add(RouteDependency(
            route_plan_id=plan.id, predecessor_checkpoint_id=successor.id,
            successor_checkpoint_id=first.id, dependency_type="finish_to_start",
        ))
        db.session.commit()
        with pytest.raises(base.OperationalError) as cycle:
            service.recalculate_projected_timeline(
                shipment.id, _user(operational_app), plan.version, "cycle",
            )
        db.session.rollback()
        assert cycle.value.code == "INVALID_ROUTE_GRAPH_CYCLE"
        assert db.session.get(OperationalCheckpoint, successor.id).projected_arrival_at == previous
        assert OperationalAudit.query.count() == audits


@pytest.mark.parametrize("failure_point", [
    "after_first_checkpoint", "middle_chain", "after_milestone_sync",
    "after_route_leg_sync", "before_audit", "before_outbox", "before_commit",
])
def test_projected_timeline_failure_injection_rolls_back_everything(operational_app, failure_point):
    with operational_app.app_context():
        shipment, plan, leg, checkpoint = _draft_with_checkpoint(
            operational_app, f"timeline-failure-{failure_point}",
        )
        _activate_for_timeline(shipment, plan)
        checkpoint.actual_arrival_at = checkpoint.planned_arrival_at.replace(tzinfo=timezone.utc) + timedelta(hours=2)
        checkpoint.actual_departure_at = checkpoint.planned_departure_at.replace(tzinfo=timezone.utc) + timedelta(hours=2)
        db.session.commit()
        projected_before = (checkpoint.projected_arrival_at, checkpoint.projected_departure_at)
        actual_before = (checkpoint.actual_arrival_at, checkpoint.actual_departure_at)
        event_count = MilestoneEvent.query.count()
        audit_count = OperationalAudit.query.count()
        outbox_count = OperationalOutbox.query.count()

        with pytest.raises(RuntimeError):
            service.recalculate_projected_timeline(
                shipment.id, _user(operational_app), plan.version,
                f"failure-{failure_point}", _failure_point=failure_point,
            )
        db.session.rollback()

        checkpoint = db.session.get(OperationalCheckpoint, checkpoint.id)
        leg = db.session.get(RouteLeg, leg.id)
        assert (checkpoint.projected_arrival_at, checkpoint.projected_departure_at) == projected_before
        assert (checkpoint.actual_arrival_at, checkpoint.actual_departure_at) == actual_before
        assert leg.projected_departure is None and leg.projected_arrival is None
        assert MilestoneEvent.query.count() == event_count
        assert OperationalAudit.query.count() == audit_count
        assert OperationalOutbox.query.count() == outbox_count
