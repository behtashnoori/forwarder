"""Direct PostgreSQL evidence for Phase 1B exception/replan races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (
    OperationalAudit,
    OperationalCheckpoint,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOrganization,
    OperationalOutbox,
    OperationalShipment,
    OperationalWorkItem,
    RouteLeg,
    RoutePlan,
)
from backend.services import operational_service as base
from backend.services import route_orchestration_service as service


ITERATIONS = 10


def _url():
    value = os.environ.get("FORWARDER_PHASE1B_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit Phase 1B disposable PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database.startswith("forwarder_phase1a_test_phase1b_")
    return value


@pytest.fixture(scope="module")
def app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": _url(),
            "SECRET_KEY": "phase1b-exception-race-postgresql",
        },
        skip_startup=True,
    )


def _seed(app, label):
    suffix = f"{label}-{os.urandom(4).hex()}"
    permissions = [
        "operational_shipment.read",
        "operational_shipment.create",
        "route_plan.read",
        "route_plan.create",
        "route_plan.activate",
        "route_plan.replan",
        "route_leg.manage",
        "checkpoint.read",
        "checkpoint.report",
        "checkpoint.verify",
        "route_exception.read",
        "route_exception.manage",
    ]
    with app.app_context():
        org = OperationalOrganization(name=f"Exception race {suffix}")
        actor = ExpertUser(
            username=f"race-{suffix}",
            password_hash="unused",
            full_name="Race Actor",
            role="manager",
            is_active=True,
        )
        db.session.add_all([org, actor])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=org.id,
                user_id=actor.id,
                permissions=permissions,
            )
        )
        origin = Province(name_fa=f"Race origin {suffix}", code=f"R{os.urandom(3).hex()}")
        destination = Province(
            name_fa=f"Race destination {suffix}", code=f"S{os.urandom(3).hex()}"
        )
        customer = Customer(first_name="Race", last_name=suffix, status="active")
        db.session.add_all([origin, destination, customer])
        db.session.flush()
        request = ShipmentRequest(
            contact_phone=f"09{os.urandom(5).hex()[:9]}",
            status="waiting_for_customer",
            status_request_status="new",
            assigned_to=actor.id,
            customer_id=customer.id,
        )
        db.session.add(request)
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request.id,
            amount=100,
            currency="IRR",
            created_by_expert_id=actor.id,
            created_at=datetime.now(timezone.utc),
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=org.id,
        )
        db.session.add(quote)
        db.session.commit()
        user = {"id": actor.id, "role": "manager"}
        start = datetime.now(timezone.utc) + timedelta(hours=1)
        shipment, _ = base.create_from_accepted_quote(
            {
                "accepted_quote_id": quote.id,
                "planned_departure": start.isoformat(),
                "planned_arrival": (start + timedelta(hours=4)).isoformat(),
                "origin": {"source_type": "province", "source_id": origin.id},
                "destination": {
                    "source_type": "province",
                    "source_id": destination.id,
                },
                "transport_mode": "road",
            },
            user,
            f"race-create-{suffix}",
        )
        draft = service.create_plan(
            shipment.id,
            {
                "legs": [
                    {
                        "sequence_number": 1,
                        "origin": {"source_type": "province", "source_id": origin.id},
                        "destination": {
                            "source_type": "province",
                            "source_id": destination.id,
                        },
                        "transport_mode": "road",
                        "planned_departure": start.isoformat(),
                        "planned_arrival": (start + timedelta(hours=4)).isoformat(),
                    }
                ]
            },
            user,
        )
        leg = RouteLeg.query.filter_by(route_plan_id=draft["id"]).one()
        checkpoints = []
        for sequence, checkpoint_type, offset in [
            (1, "export_customs", 1),
            (2, "unloading", 3),
            (3, "final_delivery", 4),
        ]:
            checkpoints.append(
                service.add_checkpoint(
                    shipment.id,
                    draft["id"],
                    {
                        "route_leg_id": leg.id,
                        "sequence_number": sequence,
                        "checkpoint_type": checkpoint_type,
                        "canonical_location_id": (
                            leg.origin_location_id
                            if sequence == 1
                            else leg.destination_location_id
                        ),
                        "planned_arrival_at": (
                            start + timedelta(hours=offset)
                        ).isoformat(),
                    },
                    user,
                )
            )
        service.activate_plan(shipment.id, draft["id"], {"expected_version": 1}, user)
        plan = db.session.get(RoutePlan, draft["id"])
        checkpoint = db.session.get(OperationalCheckpoint, checkpoints[1]["id"])
        calculation_time = datetime.now(timezone.utc)
        checkpoint.projected_arrival_at = calculation_time - timedelta(hours=2)
        db.session.commit()
        service.reconcile_route_exceptions(
            shipment.id,
            user,
            plan.version,
            calculation_time,
            f"race-open-{suffix}",
        )
        item = OperationalWorkItem.query.filter_by(
            route_plan_id=plan.id,
            checkpoint_id=checkpoint.id,
            work_type="CHECKPOINT_OVERDUE",
        ).one()
        return {
            "shipment_id": shipment.id,
            "plan_id": plan.id,
            "checkpoint_id": checkpoint.id,
            "item_id": item.id,
            "item_version": item.version,
            "plan_version": plan.version,
            "user": user,
            "calculation_time": calculation_time,
            "suffix": suffix,
        }


def _concurrent_pair(left, right):
    barrier = Barrier(2, timeout=10)

    def run(callback):
        barrier.wait()
        return callback()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, left), pool.submit(run, right)]
        return [future.result(timeout=30) for future in futures]


def _capture(app, callback):
    with app.app_context():
        try:
            return ("ok", callback())
        except base.OperationalError as exc:
            db.session.rollback()
            return ("error", exc.code)
        except (DBAPIError, IntegrityError) as exc:
            db.session.rollback()
            return ("raw-database-error", type(exc).__name__)


def _resolution_counts(item_id):
    manual_audit = OperationalAudit.query.filter_by(
        action="route_exception.manually_resolved", entity_id=item_id
    ).count()
    automatic_audit = OperationalAudit.query.filter_by(
        action="route_exception.resolved", entity_id=item_id
    ).count()
    manual_outbox = OperationalOutbox.query.filter_by(
        event_type="route_exception.manually_resolved", aggregate_id=item_id
    ).count()
    automatic_outbox = OperationalOutbox.query.filter_by(
        event_type="route_exception.resolved", aggregate_id=item_id
    ).count()
    return manual_audit + automatic_audit, manual_outbox + automatic_outbox


def test_manual_resolve_and_automatic_reconcile_repeated_races(app):
    stats = {
        "condition_cleared": 0,
        "condition_persists": 0,
        "stale_version": 0,
        "idempotent_retry": 0,
    }
    for iteration in range(ITERATIONS):
        seeded = _seed(app, f"clear-{iteration}")
        with app.app_context():
            checkpoint = db.session.get(
                OperationalCheckpoint, seeded["checkpoint_id"]
            )
            checkpoint.projected_arrival_at = seeded["calculation_time"] + timedelta(
                hours=2
            )
            db.session.commit()
        outcomes = _concurrent_pair(
            lambda: _capture(
                app,
                lambda: service._resolve_route_exception(
                    seeded["item_id"],
                    {
                        "expected_version": seeded["item_version"],
                        "reason": "Operator confirmed recovery",
                    },
                    seeded["user"],
                    f"manual-clear-{seeded['suffix']}",
                ),
            ),
            lambda: _capture(
                app,
                lambda: service.reconcile_route_exceptions(
                    seeded["shipment_id"],
                    seeded["user"],
                    seeded["plan_version"],
                    seeded["calculation_time"] + timedelta(minutes=1),
                    f"auto-clear-{seeded['suffix']}",
                ),
            ),
        )
        assert all(outcome[0] != "raw-database-error" for outcome in outcomes)
        with app.app_context():
            item = db.session.get(OperationalWorkItem, seeded["item_id"])
            assert item.status == "resolved"
            assert OperationalWorkItem.query.filter_by(
                route_plan_id=seeded["plan_id"],
                checkpoint_id=seeded["checkpoint_id"],
                work_type="CHECKPOINT_OVERDUE",
            ).count() == 1
            assert _resolution_counts(item.id) == (1, 1)
        stats["condition_cleared"] += 1

        seeded = _seed(app, f"persist-{iteration}")
        outcomes = _concurrent_pair(
            lambda: _capture(
                app,
                lambda: service._resolve_route_exception(
                    seeded["item_id"],
                    {
                        "expected_version": seeded["item_version"],
                        "reason": "Operator attempted resolution",
                    },
                    seeded["user"],
                    f"manual-persist-{seeded['suffix']}",
                ),
            ),
            lambda: _capture(
                app,
                lambda: service.reconcile_route_exceptions(
                    seeded["shipment_id"],
                    seeded["user"],
                    seeded["plan_version"],
                    seeded["calculation_time"] + timedelta(minutes=1),
                    f"auto-persist-{seeded['suffix']}",
                ),
            ),
        )
        assert all(outcome[0] != "raw-database-error" for outcome in outcomes)
        with app.app_context():
            rows = OperationalWorkItem.query.filter_by(
                route_plan_id=seeded["plan_id"],
                checkpoint_id=seeded["checkpoint_id"],
                work_type="CHECKPOINT_OVERDUE",
            ).all()
            assert len(rows) == 1
            item = rows[0]
            assert item.status in {"open", "resolved"}
            assert (item.status == "open") == (item.resolved_at is None)
        stats["condition_persists"] += 1

        seeded = _seed(app, f"stale-{iteration}")
        with app.app_context():
            checkpoint = db.session.get(
                OperationalCheckpoint, seeded["checkpoint_id"]
            )
            checkpoint.projected_arrival_at = seeded["calculation_time"] + timedelta(
                hours=2
            )
            db.session.commit()
            service.reconcile_route_exceptions(
                seeded["shipment_id"],
                seeded["user"],
                seeded["plan_version"],
                seeded["calculation_time"] + timedelta(minutes=1),
                f"stale-auto-winner-{seeded['suffix']}",
            )
        stale = _capture(
            app,
            lambda: service._resolve_route_exception(
                seeded["item_id"],
                {
                    "expected_version": seeded["item_version"],
                    "reason": "Stale operator command",
                },
                seeded["user"],
                f"stale-loser-{seeded['suffix']}",
            ),
        )
        assert stale == ("error", "ROUTE_EXCEPTION_ALREADY_RESOLVED")
        with app.app_context():
            assert _resolution_counts(seeded["item_id"]) == (1, 1)
        stats["stale_version"] += 1

        seeded = _seed(app, f"retry-{iteration}")
        key = f"manual-retry-{seeded['suffix']}"
        outcomes = _concurrent_pair(
            lambda: _capture(
                app,
                lambda: service._resolve_route_exception(
                    seeded["item_id"],
                    {
                        "expected_version": seeded["item_version"],
                        "reason": "Idempotent operator resolution",
                    },
                    seeded["user"],
                    key,
                ),
            ),
            lambda: _capture(
                app,
                lambda: service._resolve_route_exception(
                    seeded["item_id"],
                    {
                        "expected_version": seeded["item_version"],
                        "reason": "Idempotent operator resolution",
                    },
                    seeded["user"],
                    key,
                ),
            ),
        )
        assert outcomes[0][0] == outcomes[1][0] == "ok"
        with app.app_context():
            assert OperationalIdempotency.query.filter_by(
                operation="route_exception_resolve",
                command_resource_id=seeded["item_id"],
                idempotency_key=key,
            ).count() == 1
            assert _resolution_counts(seeded["item_id"]) == (1, 1)
        stats["idempotent_retry"] += 1
    assert stats == {name: ITERATIONS for name in stats}


def test_replan_and_exception_reconcile_repeated_race(app):
    winners = {"replan_observed_first": 0, "reconcile_observed_first": 0}
    for iteration in range(ITERATIONS):
        seeded = _seed(app, f"replan-reconcile-{iteration}")

        def replan():
            return _capture(
                app,
                lambda: service.replan(
                    seeded["shipment_id"],
                    seeded["plan_id"],
                    {
                        "expected_version": seeded["plan_version"],
                        "reason": "Concurrent exception-driven replan",
                    },
                    seeded["user"],
                    f"replan-race-{seeded['suffix']}",
                ),
            )

        def reconcile():
            return _capture(
                app,
                lambda: service.reconcile_route_exceptions(
                    seeded["shipment_id"],
                    seeded["user"],
                    seeded["plan_version"],
                    seeded["calculation_time"] + timedelta(minutes=1),
                    f"reconcile-race-{seeded['suffix']}",
                ),
            )

        outcomes = _concurrent_pair(replan, reconcile)
        assert all(outcome[0] != "raw-database-error" for outcome in outcomes)
        assert outcomes[0][0] == "ok"
        if outcomes[1][0] == "ok":
            winners["reconcile_observed_first"] += 1
        else:
            assert outcomes[1] in {
                ("error", "STALE_ROUTE_PLAN_VERSION"),
                ("error", "ROUTE_PLAN_NOT_ACTIVE"),
            }
            winners["replan_observed_first"] += 1
        with app.app_context():
            plans = RoutePlan.query.filter_by(
                operational_shipment_id=seeded["shipment_id"]
            ).all()
            active = [plan for plan in plans if plan.is_active]
            source = db.session.get(RoutePlan, seeded["plan_id"])
            assert len(active) == 1
            assert source.status == "superseded" and not source.is_active
            assert len({plan.revision_number for plan in plans}) == len(plans)
            source_items = OperationalWorkItem.query.filter_by(
                route_plan_id=source.id
            ).all()
            assert source_items and all(item.status == "resolved" for item in source_items)
            assert OperationalWorkItem.query.filter_by(
                route_plan_id=active[0].id
            ).count() == 0
            assert db.session.scalar(
                select(func.count()).select_from(OperationalCheckpoint).where(
                    OperationalCheckpoint.route_plan_id == active[0].id
                )
            ) == 3
    assert sum(winners.values()) == ITERATIONS
