"""Revision-aware history, inherited evidence, and typed audit isolation."""
from datetime import datetime, timedelta, timezone
import pytest
from backend.extensions import db
from backend.operational_models import Milestone, MilestoneEvent, RoutePlan, RouteLeg, OperationalAudit
from backend.services import operational_read_service as reads
from backend.services import occurrence_projection_service as authority
from backend.services import operational_service as base
from backend.services import route_orchestration_service as routes
from backend.tests.test_execution_authority_3a import setup, report
from backend.tests.test_operational_vertical_slice import operational_app, _user, _auth
from backend.tests.test_multileg_route_orchestration import _leg


def test_replan_retains_evidence_snapshots_and_future_times(operational_app):
    with operational_app.app_context():
        shipment, first, milestones = setup(operational_app)
        plan = db.session.get(RoutePlan, first.route_plan_id)
        ids = operational_app.config["phase1a"]
        plan.status = "draft"
        second = routes._add_leg(plan, _leg(operational_app, 2, ids["destination"], ids["origin"],
                                            datetime.now(timezone.utc)+timedelta(days=1)))
        plan.status = "active"; db.session.commit()
        arrival = milestones["arrival"]
        arrival.milestone_type_snapshot = {"name": "Arrival then"}
        arrival.expected_point_snapshot = {"label": "Historical facility"}
        arrival.target_metadata = {"note": "Historical instruction"}
        db.session.commit()
        occurred = datetime.now(timezone.utc)-timedelta(hours=2)
        report(operational_app, shipment, milestones["departure"], occurred-timedelta(minutes=30), "departure")
        event = report(operational_app, shipment, arrival, occurred, "arrival")
        base.verify_milestone(shipment.id, arrival.id, arrival.version, _user(operational_app, "verifier"))
        assert reads.current_route(shipment)["route_revision"] == 1
        event_count = MilestoneEvent.query.count()
        future = datetime.now(timezone.utc)+timedelta(days=2)
        result = routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "New schedule",
            "changes": {"legs": [{"source_route_leg_id": second.id, "planned_departure": future.isoformat(),
                                   "planned_arrival": (future+timedelta(hours=3)).isoformat()}]}}, _user(operational_app), "replan")
        clone = RouteLeg.query.filter_by(route_plan_id=result["id"], source_route_leg_id=first.id).one()
        copied = Milestone.query.filter_by(route_leg_id=clone.id, milestone_type="arrival").one()
        assert clone.status == "completed" and authority.aware(clone.actual_arrival) == occurred
        assert copied.lifecycle_status == "COMPLETED" and copied.verification_state == "verified"
        assert copied.source_milestone_id == arrival.id
        assert copied.milestone_type_snapshot == arrival.milestone_type_snapshot
        assert copied.expected_point_snapshot == arrival.expected_point_snapshot
        assert copied.target_metadata == arrival.target_metadata
        assert clone.origin_snapshot == first.origin_snapshot
        assert clone.destination_snapshot == first.destination_snapshot
        assert clone.origin_logistics_point_id == first.origin_logistics_point_id
        assert clone.destination_logistics_point_id == first.destination_logistics_point_id
        assert MilestoneEvent.query.count() == event_count
        future_clone = RouteLeg.query.filter_by(route_plan_id=result["id"], source_route_leg_id=second.id).one()
        times = {m.milestone_type: authority.aware(m.planned_at) for m in Milestone.query.filter_by(route_leg_id=future_clone.id)}
        assert times == {"departure": future, "arrival": future+timedelta(hours=3)}
        current = routes.timeline(shipment.id, _user(operational_app))
        assert current["scope"] == "current_route" and current["route_revision"] == 2
        proof = current["milestone_evidence"][copied.id]
        assert proof["inherited"] and proof["effective_event_public_id"] == event.public_id
        assert proof["source_route_revision"] == 1
        history = reads.history(shipment)
        physical = [i for i in history["items"] if i["classification"] == "PHYSICAL_OCCURRENCE"]
        assert len(physical) == 2 and all(i["route_revision"] == 1 and not i["is_active"] for i in physical)
        decision = next(i for i in history["items"] if i["classification"] == "VERIFICATION_DECISION")
        assert decision["related_event_public_id"] == event.public_id
        assert len([i for i in history["items"] if i["classification"] == "REPLAN_REVISION"]) == 2


def test_graph_reported_not_overdue_and_correction_provenance(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        now = datetime.now(timezone.utc)-timedelta(hours=1)
        milestones["departure"].planned_at = now-timedelta(hours=1)
        milestones["arrival"].planned_at = None
        db.session.commit()
        assert reads.current_route(shipment)["shipment_status_reason"] == "NO_ACTIVE_EXECUTION"
        original = report(operational_app, shipment, milestones["departure"], now, "dep")
        graph = base.shipment_graph(shipment)
        assert not graph["overdue"] and graph["current_milestone"] == "arrival"
        assert graph["status"] == "in_progress"
        assert graph["operational_provenance"]["shipment_status_reason"] == "ACTIVE_LEGS_IN_PROGRESS"
        replacement = base.correct_milestone(shipment.id, milestones["departure"].id,
            {"expected_version": milestones["departure"].version, "reason": "clock",
             "occurred_at": (now+timedelta(minutes=1)).isoformat()}, _user(operational_app), "correct")
        view = reads.current_route(shipment)["route_legs"][0]
        assert view["departure"]["time_source"] == "actual"
        assert view["occurrence_sources"]["departure"]["effective_event_public_id"] == replacement.public_id
        item = reads.event_view(replacement, shipment)
        assert item["supersedes_event_public_id"] == original.public_id and item["classification"] == "CORRECTION"
        report(operational_app, shipment, milestones["arrival"], now+timedelta(minutes=30), "arr")
        assert reads.current_route(shipment)["shipment_status_reason"] == "ALL_REQUIRED_ACTIVE_LEGS_COMPLETED"


def test_absent_empty_and_cancelled_routes(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        plan = db.session.get(RoutePlan, leg.route_plan_id)
        plan.is_active = False; plan.status = "superseded"; db.session.commit()
        graph = base.shipment_graph(shipment)
        assert graph["route_plan"] is None and graph["route_leg"] is None and graph["route_legs"] == []
        assert graph["operational_provenance"]["shipment_status_reason"] == "EMPTY_ROUTE"
        plan.is_active = True; plan.status = "active"; leg.status = "cancelled"; db.session.commit()
        assert reads.current_route(shipment)["status"] == "planned"
        assert reads.current_route(shipment)["shipment_status_reason"] == "UNRESOLVED_ROUTE_STATE"


def test_audit_typed_scope_event_identity_and_tenant(operational_app):
    from backend.services import operational_execution_service as execution
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        event = execution.create_event(shipment.public_id, milestones["departure"].public_id,
            {"expected_version": 1, "effective_at": datetime.now(timezone.utc).isoformat()}, _user(operational_app))
        actor = _user(operational_app)["id"]
        for kind, entity, org, action in [("UnrelatedEntity", shipment.id, shipment.organization_id, "collision"),
            ("MilestoneEvent", event.id, shipment.organization_id+100, "other-tenant"),
            ("RouteLeg", leg.id+1000, shipment.organization_id, "unrelated-leg")]:
            db.session.add(OperationalAudit(entity_type=kind, entity_id=entity, organization_id=org,
                actor_user_id=actor, action=action, metadata_json={}))
        db.session.flush()
        rows = db.session.scalars(reads.audit_query(shipment)).all()
        assert not {"collision", "other-tenant", "unrelated-leg"}.intersection(r.action for r in rows)
        created = next(r for r in rows if r.action == "milestone_event.created")
        assert created.entity_type == "MilestoneEvent" and created.entity_id == event.id
        assert any(i["id"] == created.id for i in base.shipment_graph(shipment)["audit_summary"])
        db.session.rollback()


def test_legacy_unresolved_and_bounded_history(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        event = MilestoneEvent(organization_id=shipment.organization_id, milestone_id=milestones["departure"].id,
            event_type="verified", occurred_at=datetime.now(timezone.utc), actor_user_id=_user(operational_app)["id"],
            idempotency_key="legacy", request_hash="legacy")
        db.session.add(event); db.session.commit()
        view = reads.event_view(event, shipment)
        assert view["relationship_status"] == "UNRESOLVED" and view["related_event_public_id"] is None
        first, second = reads.history(shipment, 1, 1), reads.history(shipment, 2, 1)
        assert first["has_more"] and len(first["items"]) == len(second["items"]) == 1
        with pytest.raises(base.OperationalError):
            reads.history(shipment, 1, 101)
        public_id = shipment.public_id
    client = operational_app.test_client()
    result = client.get(f"/api/v2/operational-shipments/{public_id}/history?per_page=1", headers=_auth(operational_app))
    assert result.status_code == 200 and result.json["data"]["scope"] == "shipment_history"
    assert result.json["data"]["per_page"] == 1
    assert result.json["data"]["items"][0]["history_id"]
    assert result.json["data"]["items"][0]["category"]


def test_activation_rejects_occurrence_without_cached_actual(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        report(operational_app, shipment, milestones["departure"], datetime.now(timezone.utc), "dep")
        leg.actual_departure = None; leg.status = "planned"; db.session.commit()
        ids = operational_app.config["phase1a"]
        draft = routes.create_plan(shipment.id, {"legs": [_leg(operational_app, 1, ids["origin"], ids["destination"],
            datetime.now(timezone.utc)+timedelta(days=1))]}, _user(operational_app))
        with pytest.raises(base.OperationalError) as error:
            routes.activate_plan(shipment.id, draft["id"], {"expected_version": draft["version"]}, _user(operational_app))
        assert error.value.code == "EXECUTED_ROUTE_REQUIRES_REPLAN"


def test_time_source_and_read_does_not_mutate(operational_app):
    assert reads.time_value(None, None, None)["time_source"] == "unavailable"
    now = datetime.now(timezone.utc)
    assert reads.time_value(now, None, None)["time_source"] == "planned"
    assert reads.time_value(now, now, None)["time_source"] == "projected"
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        reads.current_route(shipment); reads.history(shipment); base.shipment_graph(shipment)
        assert not db.session.dirty and not db.session.new


def test_in_progress_replan_preserves_source_and_blocks_future_edit(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        event = report(operational_app, shipment, milestones["departure"], datetime.now(timezone.utc)-timedelta(hours=1), "dep")
        plan = db.session.get(RoutePlan, leg.route_plan_id)
        with pytest.raises(base.OperationalError) as error:
            routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "Edit executed",
                "changes": {"legs": [{"source_route_leg_id": leg.id, "planned_departure": datetime.now(timezone.utc).isoformat()}]}},
                _user(operational_app), "invalid-edit")
        assert error.value.code == "COMPLETED_ROUTE_SEGMENT_IMMUTABLE"
        result = routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "Retain execution"},
                               _user(operational_app), "preserve")
        current = reads.current_route(shipment)
        assert current["route_plan_id"] == result["id"] and current["status"] == "in_progress"
        assert current["route_legs"][0]["occurrence_sources"]["departure"]["effective_event_public_id"] == event.public_id
        assert MilestoneEvent.query.count() == 1


def test_event_pagination_resolves_decision_target_off_page(operational_app):
    from backend.services import operational_execution_service as execution
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        event = report(operational_app, shipment, milestones["departure"], datetime.now(timezone.utc), "dep")
        execution.verify_event(shipment.public_id, event.public_id, {}, _user(operational_app, "verifier"))
        first = execution.events(shipment.public_id, _user(operational_app), 1, 1)[0]
        second = execution.events(shipment.public_id, _user(operational_app), 2, 1)[0]
        assert first["classification"] == "VERIFICATION_DECISION"
        assert first["related_event_public_id"] == event.public_id
        assert second["verification_state"] == "verified"
        assert second["route_revision"] == 1


def test_history_api_rejects_other_organization(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        public_id = shipment.public_id
    response = operational_app.test_client().get(f"/api/v2/operational-shipments/{public_id}/history",
                                                headers=_auth(operational_app, "outsider"))
    assert response.status_code in {403, 404}


def test_source_correction_after_replan_updates_current_actual(operational_app):
    """Inherited evidence and the active leg actual must describe the same fact."""
    from backend.services import operational_execution_service as execution
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        occurred = datetime.now(timezone.utc) - timedelta(hours=2)
        original = report(operational_app, shipment, milestones["departure"], occurred, "dep")
        plan = db.session.get(RoutePlan, leg.route_plan_id)
        routes.replan(shipment.id, plan.id,
            {"expected_version": plan.version, "reason": "Retain execution"},
            _user(operational_app), "preserve-for-correction")
        corrected_at = occurred + timedelta(minutes=10)
        corrected = execution.correct_event(shipment.public_id, original.public_id,
            {"expected_version": milestones["departure"].version,
             "effective_at": corrected_at.isoformat(), "reason": "Correct source clock"},
            _user(operational_app))
        db.session.expire_all()
        current = reads.current_route(shipment)["route_legs"][0]
        proof = current["occurrence_sources"]["departure"]
        assert proof["effective_event_public_id"] == corrected.public_id
        assert proof["effective_occurred_at"] == corrected_at.isoformat()
        assert current["departure"]["actual_at"] == corrected_at.isoformat()


@pytest.mark.parametrize("replans,kind,completed", [(1, "departure", False), (2, "departure", False),
    (2, "arrival", True), (1, "departure", True)])
def test_correction_rebuilds_all_retained_descendants(operational_app, replans, kind, completed):
    from backend.tests.test_execution_authority_3a import snapshot
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        now = datetime.now(timezone.utc) - timedelta(hours=3)
        departure = report(operational_app, shipment, milestones["departure"], now, "dep")
        original = departure
        if completed:
            arrival = report(operational_app, shipment, milestones["arrival"], now+timedelta(hours=1), "arr")
            if kind == "arrival":
                original = arrival
        before_event = snapshot(original)
        source = milestones[kind]
        base.verify_milestone(shipment.id, source.id, source.version, _user(operational_app, "verifier"))
        for index in range(replans):
            plan = authority.active_plan(shipment)
            routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "Preserve"},
                          _user(operational_app), f"preserve-{index}")
        before_plan = {p.id: (p.revision_number, p.is_active) for p in RoutePlan.query.all()}
        before_leg = {l.id: (l.planned_departure, l.planned_arrival, l.origin_snapshot, l.destination_snapshot)
                      for l in RouteLeg.query.all()}
        count = MilestoneEvent.query.count()
        replacement_time = authority.aware(original.occurred_at) + timedelta(minutes=5)
        replacement = _correct_retained_source(shipment.id, source.id,
            {"expected_version": source.version, "occurred_at": replacement_time.isoformat(), "reason": "Clock"},
            _user(operational_app), "source-correction")
        db.session.expire_all()
        assert snapshot(original) == before_event
        assert MilestoneEvent.query.count() == count+1
        assert replacement.milestone_id == source.id
        for row in Milestone.query.filter_by(milestone_type=kind):
            assert authority.aware(row.occurred_at) == replacement_time
            assert row.verification_state == "reported" and row.lifecycle_status == "COMPLETED"
            assert authority.aware(row.completed_at) == replacement_time
            if row.id != source.id:
                assert MilestoneEvent.query.filter_by(milestone_id=row.id).count() == 0
        for row in RouteLeg.query.all():
            assert authority.aware(getattr(row, "actual_"+kind)) == replacement_time
            assert row.status == ("completed" if completed else "in_progress")
            assert before_leg[row.id] == (row.planned_departure, row.planned_arrival, row.origin_snapshot, row.destination_snapshot)
        assert before_plan == {p.id: (p.revision_number, p.is_active) for p in RoutePlan.query.all()}
        current = reads.current_route(shipment)
        proof = current["route_legs"][0]["occurrence_sources"][kind]
        assert proof["effective_event_public_id"] == replacement.public_id
        assert proof["source_route_revision"] == 1 and proof["route_revision"] == replans+1
        assert current["route_legs"][0][kind]["actual_at"] == replacement_time.isoformat()
        assert current["status"] == shipment.lifecycle_status == ("completed" if completed else "in_progress")
        history = reads.history(shipment)["items"]
        assert sum(i.get("public_id") == original.public_id for i in history) == 1
        assert sum(i.get("public_id") == replacement.public_id for i in history) == 1


def test_descendant_chronology_failure_rolls_back_source_and_event(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        now = datetime.now(timezone.utc)-timedelta(hours=3)
        report(operational_app, shipment, milestones["departure"], now, "dep")
        plan = authority.active_plan(shipment)
        routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "Preserve"},
                      _user(operational_app), "preserve")
        active = authority.active_plan(shipment)
        arrival = Milestone.query.filter_by(route_plan_id=active.id, milestone_type="arrival").one()
        report(operational_app, shipment, arrival, now+timedelta(hours=1), "active-arrival")
        def state():
            return ([(m.id, m.occurred_at, m.verification_state, m.version) for m in Milestone.query.order_by(Milestone.id)],
                    [(l.id, l.actual_departure, l.actual_arrival, l.status, l.version) for l in RouteLeg.query.order_by(RouteLeg.id)],
                    shipment.lifecycle_status, shipment.version, MilestoneEvent.query.count(), OperationalAudit.query.count())
        before = state()
        with pytest.raises(base.OperationalError) as error:
            _correct_retained_source(shipment.id, milestones["departure"].id,
                {"expected_version": milestones["departure"].version, "occurred_at": (now+timedelta(hours=2)).isoformat(),
                 "reason": "Invalid only in descendant"}, _user(operational_app), "invalid-descendant")
        assert error.value.code == "INVALID_ACTUAL_CHRONOLOGY"
        db.session.expire_all()
        assert state() == before


def test_verification_after_replan_does_not_change_actuals(operational_app):
    from backend.services import operational_execution_service as execution
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        original = report(operational_app, shipment, milestones["departure"], datetime.now(timezone.utc), "dep")
        plan = authority.active_plan(shipment)
        routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "Preserve"},
                      _user(operational_app), "preserve")
        before = [(l.id, l.actual_departure, l.actual_arrival, l.status) for l in RouteLeg.query.all()]
        execution.verify_event(shipment.public_id, original.public_id, {}, _user(operational_app, "verifier"))
        assert before == [(l.id, l.actual_departure, l.actual_arrival, l.status) for l in RouteLeg.query.all()]
        assert MilestoneEvent.query.filter_by(event_type="VERIFIED").one().related_event_id == original.id


@pytest.mark.parametrize("kind", ["checkpoint_arrival", "checkpoint_departure"])
def test_checkpoint_correction_reaches_inherited_checkpoint(operational_app, kind):
    from backend.tests.test_multileg_route_orchestration import _draft_with_checkpoint
    from backend.operational_models import OperationalCheckpoint
    with operational_app.app_context():
        shipment, plan, leg, checkpoint = _draft_with_checkpoint(operational_app, "lineage-checkpoint")
        active = authority.active_plan(shipment)
        active.is_active = False; active.status = "superseded"; db.session.flush()
        plan.is_active = True; plan.status = "active"; db.session.commit()
        now = datetime.now(timezone.utc)-timedelta(hours=3)
        for action, minutes in (("arrive", 0), ("complete_processing", 10), ("depart", 20)):
            routes.checkpoint_command(shipment.id, checkpoint.id,
                {"expected_version": checkpoint.version, "occurred_at": (now+timedelta(minutes=minutes)).isoformat()},
                _user(operational_app), action, action)
        source = Milestone.query.filter_by(checkpoint_id=checkpoint.id, milestone_type=kind).one()
        count = MilestoneEvent.query.count()
        for index in range(2):
            active = authority.active_plan(shipment)
            routes.replan(shipment.id, active.id, {"expected_version": active.version, "reason": "Preserve"},
                          _user(operational_app), f"checkpoint-replan-{index}")
        corrected_at = authority.aware(source.occurred_at)+timedelta(minutes=2)
        routes.correct_checkpoint_milestone(shipment.id, checkpoint.id, source.id,
            {"expected_version": source.version, "occurred_at": corrected_at.isoformat(), "reason": "Clock"},
            _user(operational_app), "checkpoint-correct")
        db.session.expire_all()
        assert MilestoneEvent.query.count() == count+1
        field = "actual_arrival_at" if kind == "checkpoint_arrival" else "actual_departure_at"
        for row in OperationalCheckpoint.query.all():
            assert authority.aware(getattr(row, field)) == corrected_at
            assert row.status == "completed"
        for row in Milestone.query.filter_by(milestone_type=kind):
            assert authority.aware(row.occurred_at) == corrected_at
            if row.id != source.id:
                assert MilestoneEvent.query.filter_by(milestone_id=row.id).count() == 0


@pytest.mark.parametrize("case", ["independent", "malformed", "other_tenant", "invalid_owner"])
def test_lineage_divergence_and_scope_guards(operational_app, case):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        now = datetime.now(timezone.utc)-timedelta(hours=2)
        report(operational_app, shipment, milestones["departure"], now, "dep")
        plan = authority.active_plan(shipment)
        routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "Preserve"},
                      _user(operational_app), "preserve")
        child = Milestone.query.filter_by(source_milestone_id=milestones["departure"].id).one()
        owner = db.session.get(RouteLeg, child.route_leg_id)
        if case in {"independent", "malformed"}:
            # Imported local lineage fixture; report commands do not create competing roots.
            db.session.add(MilestoneEvent(organization_id=shipment.organization_id, milestone_id=child.id,
                event_type="reported" if case == "independent" else "corrected", occurred_at=now+timedelta(minutes=1),
                actor_user_id=_user(operational_app)["id"], idempotency_key="local", request_hash="local",
                reason="Imported malformed link" if case == "malformed" else None,
                supersedes_event_id=authority.effective_occurrence(milestones["departure"]).id if case == "malformed" else None))
            if case == "independent":
                authority.project(child)
        elif case == "other_tenant":
            child.organization_id += 100
        else:
            owner.source_route_leg_id = None
        db.session.commit()
        before = (child.occurred_at, child.version, owner.actual_departure, owner.version)
        count = MilestoneEvent.query.count()
        def correct():
            return _correct_retained_source(shipment.id, milestones["departure"].id,
                {"expected_version": milestones["departure"].version, "occurred_at": (now+timedelta(minutes=5)).isoformat(),
                 "reason": "Clock"}, _user(operational_app), "source-correct")
        if case in {"malformed", "invalid_owner"}:
            with pytest.raises(base.OperationalError):
                correct()
            assert MilestoneEvent.query.count() == count
        else:
            correct()
            assert MilestoneEvent.query.count() == count+1
        db.session.expire_all()
        assert before == (child.occurred_at, child.version, owner.actual_departure, owner.version)
        if case == "other_tenant":
            with pytest.raises(base.OperationalError, match="scope"):
                authority.effective_occurrence(child)


def _correct_retained_source(shipment_id, milestone_id, payload, user, key):
    from backend.services import operational_execution_service as execution
    from backend.operational_models import OperationalShipment
    shipment = db.session.get(OperationalShipment, shipment_id)
    source = db.session.get(Milestone, milestone_id)
    event = authority.effective_occurrence(source)
    return execution.correct_event(shipment.public_id, event.public_id,
        {"expected_version": payload["expected_version"], "effective_at": payload["occurred_at"],
         "reason": payload["reason"], "idempotency_key": key}, user)


@pytest.mark.parametrize("guard", ["blocked", "cancelled"])
def test_correction_leaves_unrelated_routes_and_guarded_status_unchanged(operational_app, guard):
    with operational_app.app_context():
        shipment, first, milestones = setup(operational_app)
        plan = authority.active_plan(shipment)
        ids = operational_app.config["phase1a"]
        future = datetime.now(timezone.utc)+timedelta(days=1)
        plan.status = "draft"
        second = routes._add_leg(plan, _leg(operational_app, 2, ids["destination"], ids["origin"], future))
        plan.status = "active"; db.session.commit()
        original = report(operational_app, shipment, milestones["departure"], future-timedelta(days=2), "dep")
        routes.replan(shipment.id, plan.id, {"expected_version": plan.version, "reason": "Preserve"},
                      _user(operational_app), "preserve")
        draft = routes.create_plan(shipment.id, {"legs": [_leg(operational_app, 1, ids["origin"], ids["destination"], future)]},
                                   _user(operational_app))
        inherited = RouteLeg.query.filter_by(source_route_leg_id=first.id).one()
        inherited.status = guard; db.session.commit()
        unaffected = [l for l in RouteLeg.query.all() if l.id not in {first.id, inherited.id}]
        before = [(l.id, l.actual_departure, l.actual_arrival, l.status, l.version) for l in unaffected]
        _correct_retained_source(shipment.id, milestones["departure"].id,
            {"expected_version": milestones["departure"].version, "occurred_at": (authority.aware(original.occurred_at)+timedelta(minutes=5)).isoformat(),
             "reason": "Clock"}, _user(operational_app), "guard-correction")
        assert inherited.status == guard
        assert before == [(l.id, l.actual_departure, l.actual_arrival, l.status, l.version) for l in unaffected]
        assert not db.session.get(RoutePlan, draft["id"]).is_active
