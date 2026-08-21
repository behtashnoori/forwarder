"""Real PostgreSQL gates for the Phase 1A operational aggregate."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os

import pytest
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.models import Customer, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (
    Milestone,
    OperationalMembership,
    OperationalOrganization,
    OperationalOutbox,
    OperationalShipment,
    OperationalWorkItem,
    RouteLeg,
    RoutePlan,
)
from backend.services import operational_service as service


def _url():
    value = os.environ.get("FORWARDER_PHASE1A_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit Phase 1A disposable PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database.startswith("forwarder_phase1a_test_")
    return value


def test_phase1a_postgresql_constraints_concurrency_and_triggers(monkeypatch):
    database_url = _url()
    config = alembic_config(database_url)
    prepare_version_table_for_upgrade(database_url, config)
    command.upgrade(config, "head")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_url,
            "SECRET_KEY": "phase1a-postgresql",
        },
        skip_startup=True,
    )
    permissions = [
        "operational_shipment.read",
        "operational_shipment.create",
        "operational_shipment.create_direct",
        "milestone_event.create",
        "milestone.verify",
        "milestone.correct",
        "work_item.read",
        "work_item.manage",
    ]
    with app.app_context():
        org = OperationalOrganization(name="Phase1A PostgreSQL Org")
        reporter = ExpertUser(
            username="phase1a-pg-reporter",
            password_hash="unused",
            full_name="PG Reporter",
            role="expert",
            is_active=True,
        )
        verifier = ExpertUser(
            username="phase1a-pg-verifier",
            password_hash="unused",
            full_name="PG Verifier",
            role="manager",
            is_active=True,
        )
        db.session.add_all([org, reporter, verifier])
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id, user_id=reporter.id, permissions=permissions
                ),
                OperationalMembership(
                    organization_id=org.id, user_id=verifier.id, permissions=permissions
                ),
            ]
        )
        origin = Province(name_fa="PG Origin", code="P1APGO")
        dest = Province(name_fa="PG Destination", code="P1APGD")
        customer = Customer(first_name="PG", last_name="Customer", status="active",
                            ownership_scope="TENANT", operational_organization_id=org.id)
        db.session.add_all([origin, dest, customer])
        db.session.flush()
        request = ShipmentRequest(
            contact_phone="09000000009",
            status="waiting_for_customer",
            status_request_status="new",
            assigned_to=reporter.id,
            customer_id=customer.id,
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        db.session.add(request)
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request.id,
            amount=10,
            currency="IRR",
            created_by_expert_id=reporter.id,
            created_at=datetime.now(timezone.utc),
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=org.id,
        )
        db.session.add(quote)
        db.session.commit()
        ids = {
            "org": org.id,
            "reporter": reporter.id,
            "verifier": verifier.id,
            "quote": quote.id,
            "origin": origin.id,
            "dest": dest.id,
            "customer": customer.id,
        }
    payload = {
        "accepted_quote_id": ids["quote"],
        "planned_departure": (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat(),
        "planned_arrival": (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat(),
        "origin": {"source_type": "province", "source_id": ids["origin"]},
        "destination": {"source_type": "province", "source_id": ids["dest"]},
        "transport_mode": "road",
    }

    def create_quote(key):
        with app.app_context():
            try:
                return service.create_from_accepted_quote(
                    payload, {"id": ids["reporter"], "role": "expert"}, key
                )[0].id
            except service.OperationalError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        created = list(pool.map(create_quote, ["pg-create-1", "pg-create-2"]))
    assert created.count("OPERATIONAL_SHIPMENT_ALREADY_EXISTS") == 1
    assert sum(isinstance(value, int) for value in created) == 1
    with app.app_context():
        assert (
            OperationalShipment.query.filter_by(accepted_quote_id=ids["quote"]).count()
            == 1
        )
        shipment = OperationalShipment.query.filter_by(
            accepted_quote_id=ids["quote"]
        ).one()
        milestone = db.session.scalar(
            select(Milestone)
            .join(RouteLeg, Milestone.route_leg_id == RouteLeg.id)
            .join(RoutePlan, RouteLeg.route_plan_id == RoutePlan.id)
            .where(
                RoutePlan.operational_shipment_id == shipment.id,
                Milestone.milestone_type == "departure",
            )
        )
        event = service.record_event(
            shipment.id,
            milestone.id,
            {"occurred_at": datetime.now(timezone.utc).isoformat()},
            {"id": ids["reporter"], "role": "expert"},
            "pg-report",
        )
        shipment_id, milestone_id, event_id, expected = (
            shipment.id,
            milestone.id,
            event.id,
            milestone.version,
        )

    def verify():
        with app.app_context():
            try:
                service.verify_milestone(
                    shipment_id,
                    milestone_id,
                    expected,
                    {"id": ids["verifier"], "role": "manager"},
                )
                return "ok"
            except service.OperationalError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: verify(), range(2)))
    assert sorted(outcomes) == ["STALE_AGGREGATE_VERSION", "ok"]
    with app.app_context():

        def reconcile():
            with app.app_context():
                return service.reconcile_overdue(user_id=ids["reporter"])

        with ThreadPoolExecutor(max_workers=2) as pool:
            reconciled = list(pool.map(lambda _: reconcile(), range(2)))
        assert sum(reconciled) == 1
        assert (
            OperationalWorkItem.query.filter_by(
                operational_shipment_id=shipment_id, status="open"
            ).count()
            == 1
        )
        assert (
            OperationalOutbox.query.filter_by(
                event_type="operational_shipment.created", aggregate_id=shipment_id
            ).count()
            == 1
        )
        with pytest.raises(DBAPIError):
            db.session.execute(
                text("update milestone_event set reason='tamper' where id=:id"),
                {"id": event_id},
            )
            db.session.commit()
        db.session.rollback()
        with pytest.raises(DBAPIError):
            db.session.execute(
                text("delete from milestone_event where id=:id"), {"id": event_id}
            )
            db.session.commit()
        db.session.rollback()
        with pytest.raises((IntegrityError, DBAPIError)):
            open_item = OperationalWorkItem.query.filter_by(status="open").one()
            db.session.add(
                OperationalWorkItem(
                    organization_id=open_item.organization_id,
                    operational_shipment_id=open_item.operational_shipment_id,
                    milestone_id=open_item.milestone_id,
                    due_at=open_item.due_at,
                    reason="duplicate",
                )
            )
            db.session.commit()
        db.session.rollback()

    direct_payload = {
        "source_type": "direct",
        "customer_id": ids["customer"],
        "project_public_id": None,
        "route": {
            "planned_departure": datetime.now(timezone.utc).isoformat(),
            "planned_arrival": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat(),
            "origin": {"source_type": "province", "source_id": ids["origin"]},
            "destination": {"source_type": "province", "source_id": ids["dest"]},
            "transport_mode": "road",
        },
    }

    def create_direct():
        with app.app_context():
            shipment, _ = service.create_direct(
                direct_payload,
                {"id": ids["reporter"], "role": "expert"},
                "pg-direct-same-key",
            )
            return shipment.id

    with ThreadPoolExecutor(max_workers=2) as pool:
        direct_ids = list(pool.map(lambda _: create_direct(), range(2)))
    assert direct_ids[0] == direct_ids[1]
    with app.app_context():
        direct = OperationalShipment.query.filter_by(source_type="direct").one()
        assert direct.shipment_request_id is None and direct.accepted_quote_id is None
        changed = {
            **direct_payload,
            "route": {**direct_payload["route"], "transport_mode": "rail"},
        }
        with pytest.raises(
            service.OperationalError, match="different payload"
        ) as conflict:
            service.create_direct(
                changed, {"id": ids["reporter"], "role": "expert"}, "pg-direct-same-key"
            )
        assert conflict.value.code == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"
        counts = (
            OperationalShipment.query.count(),
            RoutePlan.query.count(),
            RouteLeg.query.count(),
            Milestone.query.count(),
            OperationalOutbox.query.count(),
        )
        original_outbox = service._outbox
        monkeypatch.setattr(
            service,
            "_outbox",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("rollback injection")
            ),
        )
        with pytest.raises(RuntimeError, match="rollback injection"):
            service.create_direct(
                direct_payload,
                {"id": ids["reporter"], "role": "expert"},
                "pg-direct-rollback",
            )
        db.session.rollback()
        monkeypatch.setattr(service, "_outbox", original_outbox)
        assert counts == (
            OperationalShipment.query.count(),
            RoutePlan.query.count(),
            RouteLeg.query.count(),
            Milestone.query.count(),
            OperationalOutbox.query.count(),
        )
