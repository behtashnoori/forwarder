from datetime import datetime, timedelta, timezone

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertUser
from backend.operational_models import (
    ExecutionUnit,
    OperationalEvent,
    OperationalOrganization,
    OperationalShipment,
    Project,
)
from backend.services.tracking_projection_service import (
    project_execution_units,
    project_operational_shipments,
)


UTC = timezone.utc


@pytest.fixture()
def projection_app():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"},
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        user = ExpertUser(
            username="projection", password_hash="unused", full_name="Projection", role="admin"
        )
        org = OperationalOrganization(name="Projection Org")
        foreign_org = OperationalOrganization(name="Foreign Org")
        customer = Customer(first_name="Canonical", last_name="Tracking")
        db.session.add_all([user, org, foreign_org, customer])
        db.session.flush()
        project = Project(
            organization_id=org.id,
            primary_customer_id=customer.id,
            project_code="TRACKING",
            created_by_user_id=user.id,
        )
        foreign_project = Project(
            organization_id=foreign_org.id,
            primary_customer_id=customer.id,
            project_code="FOREIGN",
            created_by_user_id=user.id,
        )
        db.session.add_all([project, foreign_project])
        db.session.flush()
        shipment = OperationalShipment(
            organization_id=org.id,
            project_id=project.id,
            source_type="direct",
            customer_id=customer.id,
            lifecycle_status="in_progress",
            created_by_user_id=user.id,
        )
        foreign_shipment = OperationalShipment(
            organization_id=foreign_org.id,
            project_id=foreign_project.id,
            source_type="direct",
            customer_id=customer.id,
            lifecycle_status="planned",
            created_by_user_id=user.id,
        )
        db.session.add_all([shipment, foreign_shipment])
        db.session.flush()
        yield {
            "app": app,
            "user": user,
            "org": org,
            "project": project,
            "shipment": shipment,
            "foreign_project": foreign_project,
            "foreign_shipment": foreign_shipment,
        }
        db.session.remove()
        db.drop_all()


def _unit(ctx, code, *, shipment=None, checkpoint=None, event_at=None, active=True):
    row = ExecutionUnit(
        project_id=ctx["project"].id,
        operational_shipment_id=(shipment or ctx["shipment"]).id,
        unit_code=code,
        unit_type="truck",
        latest_checkpoint=checkpoint,
        last_event_at=event_at,
        is_active=active,
        created_by_user_id=ctx["user"].id,
    )
    db.session.add(row)
    db.session.flush()
    return row


def _event(ctx, unit, key, occurred_at, *, recorded_at=None, location=None, status=None, supersedes=None):
    row = OperationalEvent(
        project_id=unit.project_id,
        execution_unit_id=unit.id,
        event_type=key,
        lifecycle_status=status,
        checkpoint_text=location,
        occurred_at=occurred_at,
        recorded_at=recorded_at or occurred_at,
        actor_user_id=ctx["user"].id,
        idempotency_key=key,
        request_hash=key,
        supersedes_event_id=supersedes.id if supersedes else None,
    )
    db.session.add(row)
    db.session.flush()
    return row


def test_unit_projection_orders_effective_events_and_preserves_last_known_location(projection_app):
    ctx = projection_app
    with ctx["app"].app_context():
        t0 = datetime(2026, 8, 20, 8, tzinfo=UTC)
        unit = _unit(ctx, "U-1", checkpoint="Qom", event_at=t0 + timedelta(hours=2))
        _event(ctx, unit, "newer-inserted-first", t0 + timedelta(hours=2), location="Qom", status="in_progress")
        _event(ctx, unit, "late-history", t0, location="Tehran", status="ready")
        _event(ctx, unit, "status-only", t0 + timedelta(hours=3), status="arrived")
        db.session.commit()

        row = project_execution_units(ctx["org"].id, [unit.id])[unit.id]
        assert row["latest_event_type"] == "status-only"
        assert row["latest_event_at"] == "2026-08-20T11:00:00Z"
        assert row["current_location"] == "Qom"
        assert row["lifecycle_status"] == "arrived"
        assert row["reconciliation_health"] == "CACHE_STALE"
        assert row["source"] == "operational_event" and row["is_fallback"] is False


def test_same_time_tie_uses_recorded_at_then_public_id_and_corrections_supersede(projection_app):
    ctx = projection_app
    with ctx["app"].app_context():
        occurred = datetime(2026, 8, 20, 8, tzinfo=UTC)
        unit = _unit(ctx, "U-1")
        original = _event(ctx, unit, "original", occurred, recorded_at=occurred, location="Wrong")
        correction = _event(
            ctx,
            unit,
            "correction",
            occurred,
            recorded_at=occurred + timedelta(minutes=1),
            location="Correct",
            supersedes=original,
        )
        later_identity = _event(
            ctx,
            unit,
            "same-recorded-time",
            occurred,
            recorded_at=correction.recorded_at,
            location="Deterministic",
        )
        correction.public_id = "00000000-0000-0000-0000-000000000001"
        later_identity.public_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        db.session.commit()

        row = project_execution_units(ctx["org"].id, [unit.id])[unit.id]
        assert row["latest_event_type"] == "same-recorded-time"
        assert row["current_location"] == "Deterministic"
        assert row["reconciliation_health"] == "CACHE_MISSING"


def test_shipment_location_states_latest_event_inactive_units_and_tenant_fence(projection_app):
    ctx = projection_app
    with ctx["app"].app_context():
        t0 = datetime(2026, 8, 20, 8, tzinfo=UTC)
        one = _unit(ctx, "U-1", checkpoint="Qom", event_at=t0)
        _event(ctx, one, "one", t0, location="Qom")
        db.session.commit()
        projection = project_operational_shipments(ctx["org"].id, [ctx["shipment"].id])[ctx["shipment"].id]
        assert projection["location_state"] == "SINGLE"
        assert projection["current_location"] == "Qom"
        assert projection["reconciliation_health"] == "CONSISTENT"

        two = _unit(ctx, "U-2", checkpoint="Qom", event_at=t0 + timedelta(hours=1))
        _event(ctx, two, "two", t0 + timedelta(hours=1), location="Qom")
        _unit(ctx, "U-3")
        inactive = _unit(ctx, "U-4", checkpoint="Ignored", event_at=t0 + timedelta(hours=5), active=False)
        _event(ctx, inactive, "inactive", t0 + timedelta(hours=5), location="Ignored")
        db.session.commit()
        projection = project_operational_shipments(ctx["org"].id, [ctx["shipment"].id])[ctx["shipment"].id]
        assert projection["location_state"] == "COMMON"
        assert projection["known_location_unit_count"] == 2
        assert projection["unit_count"] == 3
        assert projection["latest_event_at"] == "2026-08-20T09:00:00Z"

        _event(ctx, two, "move", t0 + timedelta(hours=2), location="Tabriz")
        db.session.commit()
        projection = project_operational_shipments(ctx["org"].id, [ctx["shipment"].id])[ctx["shipment"].id]
        assert projection["location_state"] == "MULTIPLE"
        assert projection["current_location"] is None
        assert ctx["foreign_shipment"].id not in project_operational_shipments(
            ctx["org"].id, [ctx["foreign_shipment"].id]
        )


def test_zero_units_and_no_event_are_explicitly_unavailable(projection_app):
    ctx = projection_app
    with ctx["app"].app_context():
        empty = project_operational_shipments(ctx["org"].id, [ctx["shipment"].id])[ctx["shipment"].id]
        assert empty["location_state"] == "UNAVAILABLE"
        assert empty["source"] == "unavailable"
        assert empty["reconciliation_health"] == "NOT_APPLICABLE"
        unit = _unit(ctx, "U-1")
        db.session.commit()
        row = project_execution_units(ctx["org"].id, [unit.id])[unit.id]
        assert row["location_state"] == "UNAVAILABLE"
        assert row["latest_event_at"] is None
        assert row["lifecycle_status"] == "not_started"
