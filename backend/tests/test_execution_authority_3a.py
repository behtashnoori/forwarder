"""Business occurrences own physical execution; decisions and signals do not."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy

import pytest

from backend.extensions import db
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalMembership, OperationalShipment,
    OperationalAudit, RoutePlan, RouteLeg,
)
from backend.services import operational_service as base
from backend.services import operational_execution_service as execution
from backend.services import occurrence_projection_service as projection
from backend.services import route_orchestration_service as routes
from backend.tests.test_operational_vertical_slice import operational_app, _payload, _user
from backend.tests.test_multileg_route_orchestration import _draft_with_checkpoint, _leg


def setup(app):
    shipment, _ = base.create_from_accepted_quote(_payload(app), _user(app), "3a")
    for member in OperationalMembership.query.all():
        member.permissions = list(member.permissions) + ["operational_event.create", "operational_event.correct",
            "operational_event.verify", "operational_execution.read", "operational_execution.manage"]
    db.session.commit()
    leg = RouteLeg.query.one()
    milestones = {row.milestone_type: row for row in Milestone.query.all()}
    return shipment, leg, milestones


def report(app, shipment, milestone, instant, key):
    return base.record_event(shipment.id, milestone.id, {"occurred_at": instant.isoformat()}, _user(app), key)


def snapshot(event):
    return deepcopy({c.name: getattr(event, c.name) for c in event.__table__.columns})


def test_report_verify_correct_idempotency_and_atomic_chronology(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        start = datetime.now(timezone.utc)-timedelta(hours=2)
        departure = report(operational_app, shipment, milestones["departure"], start, "dep")
        assert (leg.status, shipment.lifecycle_status) == ("in_progress", "in_progress")
        assert projection.aware(leg.actual_departure) == start
        assert report(operational_app, shipment, milestones["departure"], start, "dep").id == departure.id
        with pytest.raises(base.OperationalError, match="different"):
            report(operational_app, shipment, milestones["departure"], start+timedelta(minutes=1), "dep")
        before = snapshot(departure)
        base.verify_milestone(shipment.id, milestones["departure"].id, milestones["departure"].version,
                              _user(operational_app, "verifier"))
        assert snapshot(departure) == before
        assert MilestoneEvent.query.filter_by(event_type="verified").one().related_event_id == departure.id
        report(operational_app, shipment, milestones["arrival"], start+timedelta(hours=1), "arr")
        assert (leg.status, shipment.lifecycle_status) == ("completed", "completed")
        count = MilestoneEvent.query.count()
        with pytest.raises(base.OperationalError) as invalid:
            base.correct_milestone(shipment.id, milestones["departure"].id,
                {"expected_version": milestones["departure"].version, "occurred_at": (start+timedelta(hours=1, minutes=30)).isoformat(),
                 "reason": "bad chronology"}, _user(operational_app), "bad")
        assert invalid.value.code == "INVALID_ACTUAL_CHRONOLOGY"
        assert MilestoneEvent.query.count() == count
        assert projection.aware(leg.actual_departure) == start
        corrected = base.correct_milestone(shipment.id, milestones["departure"].id,
            {"expected_version": milestones["departure"].version, "occurred_at": (start+timedelta(minutes=5)).isoformat(),
             "reason": "clock correction"}, _user(operational_app), "good")
        assert corrected.supersedes_event_id == departure.id
        assert projection.effective_occurrence(milestones["departure"]).id == corrected.id
        assert projection.aware(leg.actual_departure) == start+timedelta(minutes=5)
        execution.verify_event(shipment.public_id, departure.public_id, {}, _user(operational_app, "verifier"))
        assert milestones["departure"].verification_state == "reported"
        assert snapshot(departure) == before


def test_departure_sequence_and_competing_roots(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        now = datetime.now(timezone.utc)
        with pytest.raises(base.OperationalError, match="requires an effective departure"):
            report(operational_app, shipment, milestones["arrival"], now, "arrival")
        report(operational_app, shipment, milestones["departure"], now-timedelta(hours=1), "departure")
        report(operational_app, shipment, milestones["arrival"], now, "arrival")
        assert leg.status == shipment.lifecycle_status == "completed"
        with pytest.raises(base.OperationalError) as conflict:
            report(operational_app, shipment, milestones["departure"], now-timedelta(minutes=50), "another")
        assert conflict.value.code == "OCCURRENCE_ALREADY_REPORTED"
        db.session.add(MilestoneEvent(organization_id=shipment.organization_id, milestone_id=milestones["departure"].id,
            event_type="reported", occurred_at=now, actor_user_id=_user(operational_app)["id"],
            idempotency_key="historical-conflict", request_hash="x"))
        db.session.flush()
        with pytest.raises(base.OperationalError) as ambiguous:
            projection.effective_occurrence(milestones["departure"])
        assert ambiguous.value.code == "AMBIGUOUS_OCCURRENCE"
        db.session.rollback()


@pytest.mark.parametrize("guard", ["blocked", "cancelled"])
def test_leg_guard_and_explicit_shipment_cancel(operational_app, guard):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        leg.status = guard
        shipment.lifecycle_status = "cancelled"
        db.session.commit()
        with pytest.raises(base.OperationalError) as rejected:
            report(operational_app, shipment, milestones["arrival"], datetime.now(timezone.utc), "arrival")
        assert rejected.value.code == "INVALID_LEG_TRANSITION"
        assert leg.status == guard and shipment.lifecycle_status == "cancelled"


def test_zero_multileg_and_cancelled_denominator(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        old = db.session.get(RoutePlan, leg.route_plan_id)
        old.is_active = False; old.status = "superseded"
        db.session.flush()
        empty = RoutePlan(operational_shipment_id=shipment.id, revision_number=2,
                          created_by_user_id=_user(operational_app)["id"])
        db.session.add(empty); db.session.flush()
        assert projection.project_shipment(shipment) == "EMPTY_EXECUTABLE_ROUTE"
        assert shipment.lifecycle_status == "planned"
        empty.is_active = False; empty.status = "superseded"; db.session.flush()
        old.is_active = True; old.status = "draft"
        ids = operational_app.config["phase1a"]
        second = routes._add_leg(old, _leg(operational_app, 2, ids["destination"], ids["origin"], datetime.now(timezone.utc)))
        projection.ensure_leg_milestones(second, shipment)
        old.status = "active"; db.session.commit()
        assert Milestone.query.filter_by(route_leg_id=second.id).count() == 2
        first_departure = datetime.now(timezone.utc)-timedelta(minutes=1)
        report(operational_app, shipment, milestones["departure"], first_departure, "first-departure")
        report(operational_app, shipment, milestones["arrival"], datetime.now(timezone.utc), "first-arrival")
        assert shipment.lifecycle_status == "in_progress"
        second.status = "cancelled"; projection.project_shipment(shipment)
        assert shipment.lifecycle_status == "completed"
        leg.status = "cancelled"; projection.project_shipment(shipment)
        assert shipment.lifecycle_status != "completed"


def test_checkpoint_actuals_without_verification_and_correction(operational_app):
    with operational_app.app_context():
        shipment, plan, leg, checkpoint = _draft_with_checkpoint(operational_app, "3a-checkpoint")
        now = datetime.now(timezone.utc)-timedelta(hours=1)
        for action, offset in (("arrive", 0), ("complete_processing", 10), ("depart", 20)):
            routes.checkpoint_command(shipment.id, checkpoint.id,
                {"expected_version": checkpoint.version, "occurred_at": (now+timedelta(minutes=offset)).isoformat()},
                _user(operational_app), action, action)
            if action == "complete_processing":
                assert checkpoint.actual_departure_at is None and checkpoint.status == "ready_to_depart"
        assert projection.aware(checkpoint.actual_arrival_at) == now
        departure = checkpoint.actual_departure_at
        arrival = Milestone.query.filter_by(checkpoint_id=checkpoint.id, milestone_type="checkpoint_arrival").one()
        routes.correct_checkpoint_milestone(shipment.id, checkpoint.id, arrival.id,
            {"expected_version": arrival.version, "occurred_at": (now+timedelta(minutes=2)).isoformat(), "reason": "clock"},
            _user(operational_app), "correction")
        assert checkpoint.actual_departure_at == departure and checkpoint.status == "completed"
        count = MilestoneEvent.query.count()
        with pytest.raises(base.OperationalError):
            routes.correct_checkpoint_milestone(shipment.id, checkpoint.id, arrival.id,
                {"expected_version": arrival.version, "occurred_at": (now+timedelta(minutes=30)).isoformat(), "reason": "invalid"},
                _user(operational_app), "invalid")
        assert MilestoneEvent.query.count() == count and checkpoint.actual_departure_at == departure


def test_generic_event_audit_replay_and_manual_route_guard(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        milestone = milestones["departure"]
        payload = {"expected_version": milestone.version, "effective_at": datetime.now(timezone.utc).isoformat(),
                   "idempotency_key": "explicit-key"}
        event = execution.create_event(shipment.public_id, milestone.public_id, payload, _user(operational_app))
        assert execution.create_event(shipment.public_id, milestone.public_id, payload, _user(operational_app)).id == event.id
        audit = OperationalAudit.query.filter_by(action="milestone_event.created").one()
        assert audit.entity_type == "MilestoneEvent" and audit.entity_id == event.id
        with pytest.raises(base.OperationalError):
            execution.transition(shipment.public_id, milestone.public_id,
                                 {"expected_version": milestone.version, "target_status": "COMPLETED"}, _user(operational_app))
        with pytest.raises(ValueError, match="append-only"):
            event.note = "mutation"; db.session.flush()
        db.session.rollback()


def test_tracking_and_execution_unit_delivered_do_not_advance_route(operational_app):
    from backend.operational_models import Project, ExecutionUnit
    from backend.services import multi_unit_tracking_service as tracking
    from backend.services import execution_unit_service as units
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        user = _user(operational_app)
        tracking.enable_tracking_for_shipment(shipment, user["id"])
        project = Project(organization_id=shipment.organization_id,
            primary_customer_id=operational_app.config["phase1a"]["customer"], project_code="3A-P",
            created_by_user_id=user["id"])
        db.session.add(project); db.session.flush()
        execution_unit = ExecutionUnit(project_id=project.id, operational_shipment_id=shipment.id,
            unit_code="3A-E", unit_type="road", created_by_user_id=user["id"])
        db.session.add(execution_unit); db.session.flush()
        units.create_event(execution_unit, {"expected_version": 1, "lifecycle_status": "delivered"}, user, "delivered")
        db.session.commit()
        assert execution_unit.lifecycle_status == "delivered"
        assert leg.status == shipment.lifecycle_status == "planned"
        assert leg.actual_arrival is None and MilestoneEvent.query.count() == 0


def test_invalid_decision_target_and_stale_correction(operational_app):
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        now = datetime.now(timezone.utc)-timedelta(hours=1)
        original = report(operational_app, shipment, milestones["departure"], now, "report")
        execution.verify_event(shipment.public_id, original.public_id, {}, _user(operational_app, "verifier"))
        decision = MilestoneEvent.query.filter_by(event_type="VERIFIED").one()
        with pytest.raises(base.OperationalError) as error:
            execution.verify_event(shipment.public_id, decision.public_id, {}, _user(operational_app, "verifier"))
        assert error.value.code == "INVALID_EVENT_TARGET"
        base.correct_milestone(shipment.id, milestones["departure"].id,
            {"expected_version": milestones["departure"].version, "occurred_at": (now+timedelta(minutes=1)).isoformat(),
             "reason": "correct"}, _user(operational_app), "correct")
        with pytest.raises(base.OperationalError) as error:
            execution.correct_event(shipment.public_id, original.public_id,
                {"expected_version": milestones["departure"].version, "effective_at": now.isoformat(), "reason": "stale"},
                _user(operational_app))
        assert error.value.code == "STALE_OCCURRENCE"


def test_checkpoint_departure_requires_reported_arrival(operational_app):
    with operational_app.app_context():
        shipment, plan, leg, checkpoint = _draft_with_checkpoint(operational_app, "3a-missing")
        checkpoint.status = "ready_to_depart"; db.session.commit()
        with pytest.raises(base.OperationalError) as error:
            routes.checkpoint_command(shipment.id, checkpoint.id,
                {"expected_version": checkpoint.version, "occurred_at": datetime.now(timezone.utc).isoformat()},
                _user(operational_app), "depart", "depart")
        assert error.value.code == "INVALID_ACTUAL_CHRONOLOGY"
        assert checkpoint.actual_departure_at is None and MilestoneEvent.query.count() == 0


def test_http_event_idempotency_header_is_respected(operational_app):
    from backend.tests.test_operational_vertical_slice import _auth
    with operational_app.app_context():
        shipment, leg, milestones = setup(operational_app)
        url = f"/api/v2/operational-shipments/{shipment.public_id}/execution/milestones/{milestones['departure'].public_id}/events"
    client = operational_app.test_client()
    headers = {**_auth(operational_app), "Idempotency-Key": "http-3a"}
    payload = {"expected_version": 1, "effective_at": datetime.now(timezone.utc).isoformat()}
    first = client.post(url, headers=headers, json=payload)
    replay = client.post(url, headers=headers, json=payload)
    assert first.status_code == replay.status_code == 201
    assert first.json["data"]["public_id"] == replay.json["data"]["public_id"]
    conflict = client.post(url, headers=headers, json={**payload, "note": "different"})
    assert conflict.status_code == 409
    assert conflict.json["error"]["code"] == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"
