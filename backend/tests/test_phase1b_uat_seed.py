"""Focused safety and graph tests for the disposable Phase 1B UAT seed."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.engine import URL

from backend import create_app
from backend.auth import auth_manager
from backend.models import ExpertUser
from backend.operational_cli import _phase1b_seed_guard, seed_phase1b_uat
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalCheckpoint, OperationalMembership,
    OperationalOrganization, OperationalShipment, OperationalWorkItem,
    RouteDependency, RouteLeg, RoutePlan,
)
from backend.services.operational_service import OperationalError


@pytest.fixture()
def seed_app(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "phase1b-seed-test",
    })
    return app


def _counts():
    return {
        "organizations": OperationalOrganization.query.count(),
        "users": ExpertUser.query.filter(ExpertUser.username.like("phase1b_uat_%")).count(),
        "memberships": OperationalMembership.query.count(),
        "shipments": OperationalShipment.query.count(),
        "plans": RoutePlan.query.count(),
        "legs": RouteLeg.query.count(),
        "checkpoints": OperationalCheckpoint.query.count(),
        "dependencies": RouteDependency.query.count(),
        "milestones": Milestone.query.count(),
        "milestone_events": MilestoneEvent.query.count(),
        "work_items": OperationalWorkItem.query.count(),
    }


def test_seed_is_complete_tenant_scoped_and_idempotent(seed_app):
    with seed_app.app_context():
        first = seed_phase1b_uat(seed_app, "local-test-password")
        before = _counts()
        second = seed_phase1b_uat(seed_app, "local-test-password")

        assert first == second
        assert _counts() == before == {
            "organizations": 2, "users": 8, "memberships": 8,
            "shipments": 2, "plans": 2, "legs": 6, "checkpoints": 12,
            "dependencies": 12, "milestones": 36, "milestone_events": 12,
            "work_items": 2,
        }
        org_a = OperationalOrganization.query.filter_by(name="[PHASE1B-UAT] Organization A").one()
        org_b = OperationalOrganization.query.filter_by(name="[PHASE1B-UAT] Organization B").one()
        assert {row.organization_id for row in OperationalShipment.query.all()} == {org_a.id, org_b.id}
        assert OperationalMembership.query.filter_by(organization_id=org_a.id, is_active=False).count() == 1
        assert OperationalMembership.query.filter_by(organization_id=org_a.id, permissions=[]).count() == 1
        plan = (RoutePlan.query.join(OperationalShipment)
                .filter(OperationalShipment.organization_id == org_a.id).one())
        edges = {(row.predecessor_checkpoint_id, row.successor_checkpoint_id)
                 for row in RouteDependency.query.filter_by(route_plan_id=plan.id)}
        checkpoints = {row.sequence_number: row.id for row in
                       OperationalCheckpoint.query.filter_by(route_plan_id=plan.id)}
        assert (checkpoints[1], checkpoints[2]) in edges
        assert {(checkpoints[2], checkpoints[3]), (checkpoints[2], checkpoints[4])} <= edges
        assert {(checkpoints[3], checkpoints[5]), (checkpoints[4], checkpoints[5])} <= edges
        assert OperationalCheckpoint.query.filter_by(route_plan_id=plan.id, status="completed").count() == 2
        assert OperationalCheckpoint.query.filter_by(route_plan_id=plan.id, status="blocked").count() == 1
        assert MilestoneEvent.query.count() == 12
        assert MilestoneEvent.query.filter(MilestoneEvent.organization_id.is_(None)).count() == 0
        assert {row.event_type for row in MilestoneEvent.query.all()} == {"reported", "verified"}
        admin = ExpertUser.query.filter_by(username="phase1b_uat_admin").one()
        admin_membership = OperationalMembership.query.filter_by(user_id=admin.id).one()
        assert {
            "operational_execution.read",
            "operational_execution.manage",
            "operational_event.verify",
        }.issubset(set(admin_membership.permissions))
        assert {row.work_type for row in OperationalWorkItem.query.all()} == {
            "CHECKPOINT_OVERDUE", "ROUTE_DEPENDENCY_BLOCKED",
        }


def test_reporter_and_verifier_receive_only_required_detail_read_permissions(seed_app):
    with seed_app.app_context():
        seed_phase1b_uat(seed_app, "local-test-password")
        memberships = {
            user.username.removeprefix("phase1b_uat_"): set(
                OperationalMembership.query.filter_by(user_id=user.id).one().permissions
            )
            for user in ExpertUser.query.filter(ExpertUser.username.like("phase1b_uat_%")).all()
        }

    required_reads = {"operational_shipment.read", "route_plan.read", "checkpoint.read", "route_exception.read", "work_item.read"}
    assert required_reads <= memberships["reporter"]
    assert {"milestone_event.create", "checkpoint.report"} <= memberships["reporter"]
    assert required_reads <= memberships["verifier"]
    assert {"milestone.verify", "milestone.correct", "checkpoint.verify"} <= memberships["verifier"]
    assert not ({"milestone.verify", "checkpoint.verify", "route_plan.replan", "route_exception.manage"} & memberships["reporter"])
    assert not ({"route_plan.replan", "route_exception.manage"} & memberships["verifier"])


def test_reporter_detail_reads_and_report_are_allowed_but_privileged_actions_are_denied(seed_app):
    with seed_app.app_context():
        seed_phase1b_uat(seed_app, "local-test-password")
        reporter = ExpertUser.query.filter_by(username="phase1b_uat_reporter").one()
        token = auth_manager.generate_tokens(reporter.id)["access_token"]
        shipment = OperationalShipment.query.join(OperationalOrganization).filter(
            OperationalOrganization.name == "[PHASE1B-UAT] Organization A"
        ).one()
        plan = RoutePlan.query.filter_by(operational_shipment_id=shipment.id, is_active=True).one()
        checkpoint = OperationalCheckpoint.query.filter_by(route_plan_id=plan.id, sequence_number=3).one()
        milestone = Milestone.query.filter_by(checkpoint_id=checkpoint.id, milestone_type="checkpoint_arrival").one()
        exception = OperationalWorkItem.query.filter_by(operational_shipment_id=shipment.id, status="open").first()

    client = seed_app.test_client()
    headers = {"Authorization": f"Bearer {token}"}
    for path in (
        f"/api/operational-shipments/{shipment.id}",
        f"/api/operational-shipments/{shipment.id}/route-plans",
        f"/api/operational-shipments/{shipment.id}/route-plans/{plan.id}",
        f"/api/operational-shipments/{shipment.id}/route-exceptions",
    ):
        assert client.get(path, headers=headers).status_code == 200

    report = client.post(
        f"/api/operational-shipments/{shipment.id}/checkpoints/{checkpoint.id}/arrive",
        headers={**headers, "Idempotency-Key": "reporter-permission-boundary-arrive"},
        json={"occurred_at": "2030-01-03T12:00:00Z", "expected_version": checkpoint.version},
    )
    assert report.status_code == 200
    assert client.post(
        f"/api/operational-shipments/{shipment.id}/checkpoints/{checkpoint.id}/milestones/{milestone.id}/verify",
        headers={**headers, "Idempotency-Key": "reporter-permission-boundary-verify"},
        json={"expected_version": milestone.version + 1},
    ).status_code == 403
    assert client.post(
        f"/api/operational-shipments/{shipment.id}/route-plans/{plan.id}/replan",
        headers={**headers, "Idempotency-Key": "reporter-permission-boundary-replan"},
        json={"expected_version": plan.version, "reason": "must remain denied"},
    ).status_code == 403
    assert client.post(
        f"/api/operational-shipments/{shipment.id}/timeline/reconcile",
        headers={**headers, "Idempotency-Key": "reporter-permission-boundary-timeline"},
        json={"expected_route_plan_version": plan.version},
    ).status_code == 403
    assert client.post(
        f"/api/operational-shipments/{shipment.id}/route-exceptions/reconcile",
        headers={**headers, "Idempotency-Key": "reporter-permission-boundary-exceptions"},
        json={"expected_route_plan_version": plan.version},
    ).status_code == 403
    assert client.post(
        f"/api/operational-route-exceptions/{exception.id}/resolve",
        headers={**headers, "Idempotency-Key": "reporter-permission-boundary-resolve"},
        json={"expected_version": exception.version, "reason": "must remain denied"},
    ).status_code == 403


def test_seed_rolls_back_atomically_on_failure(seed_app, monkeypatch):
    import backend.operational_cli as cli

    original = cli._one_or_create
    calls = {"count": 0}

    def fail_after_writes(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 5:
            raise RuntimeError("injected seed failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(cli, "_one_or_create", fail_after_writes)
    with seed_app.app_context():
        with pytest.raises(RuntimeError, match="injected seed failure"):
            seed_phase1b_uat(seed_app, "local-test-password")
        assert _counts() == {key: 0 for key in _counts()}


@pytest.mark.parametrize(
    ("environment", "url"),
    [
        ("production", URL.create("postgresql", host="127.0.0.1", database="forwarder_phase1b_uat_x")),
        ("uat", URL.create("postgresql", host="db.example.invalid", database="forwarder_phase1b_uat_x")),
        ("uat", URL.create("postgresql", host="127.0.0.1", database="forwarder_live")),
        ("uat", URL.create("mysql", host="127.0.0.1", database="phase1b_uat_x")),
    ],
)
def test_guard_rejects_production_remote_wrong_name_and_wrong_engine(monkeypatch, environment, url):
    monkeypatch.setenv("APP_ENV", environment)
    fake_app = SimpleNamespace(config={"ENV": environment, "TESTING": False})
    with pytest.raises(OperationalError):
        _phase1b_seed_guard(fake_app, url)
