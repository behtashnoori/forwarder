"""Direct PostgreSQL evidence for the P1B-UAT-003 permission boundary."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalAudit, OperationalCheckpoint,
    OperationalIdempotency, OperationalOrganization, OperationalOutbox,
    OperationalShipment, OperationalWorkItem, RoutePlan,
)


def _url() -> str:
    value = os.environ.get("FORWARDER_PHASE1B_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit disposable Phase 1B PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_phase1b_uat_")
    return value


def _headers(app, username: str) -> dict[str, str]:
    with app.app_context():
        user = ExpertUser.query.filter_by(username=username).one()
        token = auth_manager.generate_tokens(user.id)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _reportable_arrival(plan_id: int) -> tuple[OperationalCheckpoint, Milestone]:
    """Select by the reporting contract, never by a fixture row number."""
    candidates = db.session.execute(
        select(OperationalCheckpoint, Milestone)
        .join(Milestone, Milestone.checkpoint_id == OperationalCheckpoint.id)
        .where(
            OperationalCheckpoint.route_plan_id == plan_id,
            OperationalCheckpoint.status.in_(("planned", "approaching")),
            Milestone.route_plan_id == plan_id,
            Milestone.milestone_type == "checkpoint_arrival",
            Milestone.verification_state == "planned",
            ~select(MilestoneEvent.id).where(
                MilestoneEvent.milestone_id == Milestone.id,
                MilestoneEvent.event_type.in_(("reported", "corrected", "verified")),
            ).exists(),
        )
        .order_by(OperationalCheckpoint.sequence_number, Milestone.id)
    ).all()
    assert candidates, "UAT seed must expose an event-free reportable arrival milestone"
    return candidates[0]


def test_reporter_detail_lifecycle_and_least_privilege_boundary():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": _url(),
        "SECRET_KEY": "phase1b-reporter-permission-postgresql-test-only",
    }, skip_startup=True)
    client = app.test_client()
    reporter = _headers(app, "phase1b_uat_reporter")
    verifier = _headers(app, "phase1b_uat_verifier")
    readonly = _headers(app, "phase1b_uat_readonly")
    no_permission = _headers(app, "phase1b_uat_no_permission")
    inactive = _headers(app, "phase1b_uat_inactive")

    with app.app_context():
        org_a = OperationalOrganization.query.filter_by(name="[PHASE1B-UAT] Organization A").one()
        org_b = OperationalOrganization.query.filter_by(name="[PHASE1B-UAT] Organization B").one()
        shipment = OperationalShipment.query.filter_by(organization_id=org_a.id).one()
        other_shipment = OperationalShipment.query.filter_by(organization_id=org_b.id).one()
        plan = RoutePlan.query.filter_by(operational_shipment_id=shipment.id, is_active=True).one()
        checkpoint, milestone = _reportable_arrival(plan.id)
        exception = OperationalWorkItem.query.filter_by(
            operational_shipment_id=shipment.id, status="open"
        ).first()
        ids = {
            "shipment": shipment.public_id, "other_shipment": other_shipment.public_id,
            "plan": plan.id, "plan_version": plan.version,
            "checkpoint": checkpoint.id, "checkpoint_version": checkpoint.version,
            "milestone": milestone.id, "exception": exception.id,
            "exception_version": exception.version,
        }

    for path in (
        f"/api/operational-shipments/{ids['shipment']}",
        f"/api/operational-shipments/{ids['shipment']}/route-plans",
        f"/api/operational-shipments/{ids['shipment']}/route-plans/{ids['plan']}",
        f"/api/operational-shipments/{ids['shipment']}/timeline",
        f"/api/operational-shipments/{ids['shipment']}/route-exceptions",
    ):
        assert client.get(path, headers=reporter).status_code == 200
        assert client.get(path, headers=verifier).status_code == 200

    reported = client.post(
        f"/api/operational-shipments/{ids['shipment']}/checkpoints/{ids['checkpoint']}/arrive",
        headers={**reporter, "Idempotency-Key": "p1b-reporter-postgresql-arrive"},
        json={"occurred_at": "2030-01-03T12:00:00Z", "expected_version": ids["checkpoint_version"]},
    )
    assert reported.status_code == 200
    with app.app_context():
        milestone_version = db.session.get(Milestone, ids["milestone"]).version
        checkpoint_version = db.session.get(OperationalCheckpoint, ids["checkpoint"]).version
        first_report_effects = {
            "events": MilestoneEvent.query.filter_by(milestone_id=ids["milestone"]).count(),
            "audits": OperationalAudit.query.filter_by(
                action="checkpoint.arrived", entity_id=ids["checkpoint"],
            ).count(),
            "outbox": OperationalOutbox.query.filter_by(
                event_type="checkpoint.arrived", aggregate_id=ids["checkpoint"],
            ).count(),
        }
        assert first_report_effects == {"events": 1, "audits": 1, "outbox": 1}

    replayed = client.post(
        f"/api/operational-shipments/{ids['shipment']}/checkpoints/{ids['checkpoint']}/arrive",
        headers={**reporter, "Idempotency-Key": "p1b-reporter-postgresql-arrive"},
        json={"occurred_at": "2030-01-03T12:00:00Z", "expected_version": ids["checkpoint_version"]},
    )
    assert replayed.status_code == 200
    duplicate = client.post(
        f"/api/operational-shipments/{ids['shipment']}/checkpoints/{ids['checkpoint']}/arrive",
        headers={**reporter, "Idempotency-Key": "p1b-reporter-postgresql-arrive-distinct"},
        json={"occurred_at": "2030-01-03T12:01:00Z", "expected_version": checkpoint_version},
    )
    assert duplicate.status_code == 409
    assert duplicate.json["error"]["code"] == "INVALID_CHECKPOINT_TRANSITION"
    stale = client.post(
        f"/api/operational-shipments/{ids['shipment']}/checkpoints/{ids['checkpoint']}/arrive",
        headers={**reporter, "Idempotency-Key": "p1b-reporter-postgresql-arrive-stale"},
        json={"occurred_at": "2030-01-03T12:02:00Z", "expected_version": ids["checkpoint_version"]},
    )
    assert stale.status_code == 409
    assert stale.json["error"]["code"] == "STALE_MILESTONE_VERSION"
    with app.app_context():
        assert {
            "events": MilestoneEvent.query.filter_by(milestone_id=ids["milestone"]).count(),
            "audits": OperationalAudit.query.filter_by(
                action="checkpoint.arrived", entity_id=ids["checkpoint"],
            ).count(),
            "outbox": OperationalOutbox.query.filter_by(
                event_type="checkpoint.arrived", aggregate_id=ids["checkpoint"],
            ).count(),
        } == first_report_effects
        assert db.session.get(OperationalCheckpoint, ids["checkpoint"]).version == checkpoint_version

    verify_path = (
        f"/api/operational-shipments/{ids['shipment']}/checkpoints/{ids['checkpoint']}"
        f"/milestones/{ids['milestone']}/verify"
    )
    assert client.post(
        verify_path,
        headers={**reporter, "Idempotency-Key": "p1b-reporter-postgresql-self-verify"},
        json={"expected_version": milestone_version},
    ).status_code == 403
    assert client.post(
        verify_path,
        headers={**verifier, "Idempotency-Key": "p1b-verifier-postgresql-verify"},
        json={"expected_version": milestone_version},
    ).status_code == 200
    correction_path = (
        f"/api/operational-shipments/{ids['shipment']}/checkpoints/{ids['checkpoint']}"
        f"/milestones/{ids['milestone']}/correct"
    )
    with app.app_context():
        milestone = db.session.get(Milestone, ids["milestone"])
        checkpoint = db.session.get(OperationalCheckpoint, ids["checkpoint"])
        correction_version = milestone.version
        before = {
            "events": MilestoneEvent.query.count(),
            "corrected": MilestoneEvent.query.filter_by(event_type="corrected").count(),
            "audits": OperationalAudit.query.count(),
            "outbox": OperationalOutbox.query.count(),
            "version": milestone.version,
            "state": milestone.verification_state,
            "occurred_at": milestone.occurred_at,
            "actual": checkpoint.actual_arrival_at,
            "projected": checkpoint.projected_arrival_at,
        }
    correction_payload = {
        "expected_version": correction_version,
        "occurred_at": "2030-01-03T12:05:00Z",
        "reason": "PostgreSQL authorization evidence",
    }
    reporter_correction = client.post(
        correction_path,
        headers={**reporter, "Idempotency-Key": "p1b-reporter-postgresql-correct-denied"},
        json=correction_payload,
    )
    assert reporter_correction.status_code == 403
    assert reporter_correction.json["error"]["code"] == "FORBIDDEN_OPERATION"
    with app.app_context():
        milestone = db.session.get(Milestone, ids["milestone"])
        checkpoint = db.session.get(OperationalCheckpoint, ids["checkpoint"])
        after = {
            "events": MilestoneEvent.query.count(),
            "corrected": MilestoneEvent.query.filter_by(event_type="corrected").count(),
            "audits": OperationalAudit.query.count(),
            "outbox": OperationalOutbox.query.count(),
            "version": milestone.version,
            "state": milestone.verification_state,
            "occurred_at": milestone.occurred_at,
            "actual": checkpoint.actual_arrival_at,
            "projected": checkpoint.projected_arrival_at,
        }
        assert after == before
        assert OperationalIdempotency.query.filter_by(
            operation="checkpoint_milestone_correct",
            idempotency_key="p1b-reporter-postgresql-correct-denied",
        ).count() == 0
    authorised_correction = client.post(
        correction_path,
        headers={**verifier, "Idempotency-Key": "p1b-verifier-postgresql-correct"},
        json=correction_payload,
    )
    assert authorised_correction.status_code == 201
    with app.app_context():
        assert MilestoneEvent.query.filter_by(
            milestone_id=ids["milestone"], event_type="corrected",
        ).count() == 1
        assert OperationalAudit.query.filter_by(
            action="checkpoint.milestone_corrected", entity_id=ids["milestone"],
        ).count() == 1
        assert OperationalOutbox.query.filter_by(
            event_type="checkpoint.milestone_corrected", aggregate_id=ids["milestone"],
        ).count() == 1

    denied = (
        (f"/api/operational-shipments/{ids['shipment']}/route-plans/{ids['plan']}/replan",
         {"expected_version": ids["plan_version"], "reason": "denied"}),
        (f"/api/operational-shipments/{ids['shipment']}/timeline/reconcile",
         {"expected_route_plan_version": ids["plan_version"]}),
        (f"/api/operational-shipments/{ids['shipment']}/route-exceptions/reconcile",
         {"expected_route_plan_version": ids["plan_version"]}),
        (f"/api/operational-route-exceptions/{ids['exception']}/resolve",
         {"expected_version": ids["exception_version"], "reason": "denied"}),
    )
    for index, (path, payload) in enumerate(denied):
        assert client.post(
            path,
            headers={**reporter, "Idempotency-Key": f"p1b-reporter-postgresql-denied-{index}"},
            json=payload,
        ).status_code == 403

    assert client.get(f"/api/operational-shipments/{ids['shipment']}", headers=readonly).status_code == 200
    assert client.post(
        verify_path,
        headers={**readonly, "Idempotency-Key": "p1b-readonly-postgresql-denied"},
        json={"expected_version": milestone_version + 1},
    ).status_code == 403
    assert client.get(f"/api/operational-shipments/{ids['shipment']}", headers=no_permission).status_code == 403
    assert client.get(f"/api/operational-shipments/{ids['shipment']}", headers=inactive).status_code == 403
    assert client.get(f"/api/operational-shipments/{ids['other_shipment']}", headers=reporter).status_code == 404
