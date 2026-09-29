"""Human-walkthrough gap: exact structured progress qualifies ETA, text never does."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.cargo_models import ExecutionUnitCargoAllocation, ShipmentCargoItem
from backend.extensions import db
from backend.eta_models import CargoEtaSnapshot
from backend.operational_models import ExecutionUnit, OperationalShipment, RoutePlan, RouteStageExecution
from backend.reported_fact_models import OperationalEventRouteProgress
from backend.services import eta_service as eta, reported_fact_service as reports
from backend.services import route_orchestration_service as routes
from backend.tests.test_operational_vertical_slice import _user, operational_app
from backend.tests.test_phase3_eta import setup
from backend.tests.test_phase3_document_context import _as_customer


def _fixture(app, *, planned_distance_km="100.000"):
    ctx = setup(app, planned_distance_km=planned_distance_km)
    shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
    cargo = db.session.scalar(db.select(ShipmentCargoItem).where(ShipmentCargoItem.public_id == ctx["cargo"]))
    cargo.actual_quantity = Decimal("1")
    unit = ExecutionUnit(
        organization_id=shipment.organization_id, project_id=shipment.project_id,
        operational_shipment_id=shipment.id, unit_code=f"ETA-{uuid4().hex[:10]}",
        unit_type="road", display_name="کامیون آزمون ETA", lifecycle_status="in_progress",
        created_by_user_id=app.config["phase1a"]["user"],
    )
    db.session.add(unit); db.session.flush()
    stage = RouteStageExecution(
        organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
        route_plan_id=ctx["plan"], route_leg_id=ctx["root"], execution_unit_id=unit.id,
        idempotency_key=f"eta-stage-{uuid4()}", request_hash="a" * 64,
        created_by_user_id=app.config["phase1a"]["user"],
    )
    db.session.add(stage); db.session.flush()
    db.session.add(ExecutionUnitCargoAllocation(
        execution_unit_id=unit.id, shipment_cargo_item_id=cargo.id,
        operational_shipment_id=shipment.id, project_id=shipment.project_id,
        route_stage_execution_id=stage.id, dimension="ACTUAL", allocated_quantity=Decimal("1"),
        created_by=app.config["phase1a"]["user"], updated_by=app.config["phase1a"]["user"],
    ))
    db.session.commit()
    plan = db.session.get(RoutePlan, ctx["plan"])
    ctx.update(unit=unit.public_id, stage=stage.public_id,
               occurred_at=eta.stamp(plan.effective_at))
    return ctx


def _progress(app, ctx, remaining, *, location="نزدیک مرز"):
    row, _ = reports.create(ctx["shipment"], _user(app), {
        "scope": "EXECUTION_UNIT", "target_public_id": ctx["unit"],
        "kind": "PROGRESS", "source": "DRIVER_REPORT", "occurred_at": ctx["occurred_at"],
        "location": {"location_text": location} if location else None,
        "route_progress": {"stage_execution_public_id": ctx["stage"],
                           "distance_remaining_km": str(remaining)},
        "impacted_cargo_public_ids": [ctx["cargo"]],
    }, str(uuid4()))
    db.session.commit()
    return row


def test_no_progress_and_free_text_only_never_qualify_eta(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        first = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], user=_user(operational_app))
        assert first.result["next"]["reason"] == "PROGRESS_UNDEFINED"
        reports.create(ctx["shipment"], _user(operational_app), {
            "scope": "EXECUTION_UNIT", "target_public_id": ctx["unit"],
            "kind": "LOCATION", "source": "DRIVER_REPORT", "occurred_at": ctx["occurred_at"],
            "location": {"location_text": "نزدیک مرز"},
            "impacted_cargo_public_ids": [ctx["cargo"]],
        }, str(uuid4()))
        db.session.commit()
        second = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], user=_user(operational_app))
        assert second.result["next"]["reason"] in {"PROGRESS_UNDEFINED", "PROGRESS_AMBIGUOUS"}
        assert OperationalEventRouteProgress.query.count() == 0


def test_exact_remaining_distance_prorates_only_the_active_leg(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        row = _progress(operational_app, ctx, "50.000")
        observed = eta.times.instant(ctx["occurred_at"])
        snapshot = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], user=_user(operational_app))
        db.session.commit()
        progress = db.session.get(OperationalEventRouteProgress, row.operational_event_id)
        assert progress.route_plan_id == ctx["plan"] and progress.route_leg_id == ctx["root"]
        assert progress.route_leg_time_basis_id is not None
        assert snapshot.ruleset == "ETA_RULESET_V2"
        assert snapshot.result["planned_distance"] == "100.000"
        assert snapshot.result["basis_label"] == "پیشرفت ساختاریافته مسیر"
        assert eta.times.instant(snapshot.result["next"]["earliest"]) == observed + timedelta(minutes=30)
        assert eta.times.instant(snapshot.result["next"]["latest"]) == observed + timedelta(minutes=60)
        assert eta.times.instant(snapshot.result["final"]["earliest"]) == observed + timedelta(minutes=90)
        assert eta.times.instant(snapshot.result["final"]["latest"]) == observed + timedelta(minutes=180)
        assert "نزدیک مرز" not in str(snapshot.source_basis)


def test_customer_receives_safe_eta_without_distance_or_private_progress_provenance(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        _progress(operational_app, ctx, "50.000", location="PRIVATE DRIVER POSITION")
        account_id = ctx["accounts"][0]
    client = operational_app.test_client()
    _as_customer(client, account_id)
    path = f"/api/customer/shipments/{ctx['shipment']}/cargo/{ctx['cargo']}/eta/ensure"
    response = client.post(path, json={})
    assert response.status_code == 200, response.get_json()
    value = response.get_json()
    assert value["next"]["available"] and value["planned_distance"] is None
    assert value["basis_label"] == "گزارش موقعیت عملیاتی"
    assert "provenance" not in value and "source_fingerprint" not in value
    assert "PRIVATE" not in str(value) and "100.000" not in str(value)


def test_progress_without_pinned_distance_stays_baseline_undefined(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app, planned_distance_km=None)
        row = _progress(operational_app, ctx, "50")
        progress = db.session.get(OperationalEventRouteProgress, row.operational_event_id)
        assert progress.route_leg_time_basis_id is None and progress.planned_distance_km is None
        result = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], user=_user(operational_app)).result
        assert result["next"]["reason"] == "ROUTE_BASELINE_UNDEFINED"
        assert result["final"]["reason"] == "ROUTE_BASELINE_UNDEFINED"


def test_replan_keeps_old_progress_and_snapshot_bound_and_refuses_old_stage(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        row = _progress(operational_app, ctx, "25")
        old_snapshot = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], user=_user(operational_app))
        db.session.commit()
        old_result = dict(old_snapshot.result)
        source = db.session.get(RoutePlan, ctx["plan"])
        replacement = routes.replan(ctx["shipment_id"], source.id, {
            "expected_version": source.version, "reason": "qualification replan", "changes": {},
        }, _user(operational_app), str(uuid4()))
        db.session.commit()
        assert replacement["status"] == "active" and replacement["id"] != ctx["plan"]
        with pytest.raises(eta.base.OperationalError) as exc:
            _progress(operational_app, ctx, "20")
        assert exc.value.code == "REPORT_PROGRESS_PLAN_INACTIVE"
        db.session.rollback()
        progress = db.session.get(OperationalEventRouteProgress, row.operational_event_id)
        assert progress.route_plan_id == ctx["plan"]
        assert db.session.get(CargoEtaSnapshot, old_snapshot.id).result == old_result


def test_invalid_stage_identity_and_distance_outside_baseline_fail_closed(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        with pytest.raises(eta.base.OperationalError) as missing:
            reports.create(ctx["shipment"], _user(operational_app), {
                "scope": "EXECUTION_UNIT", "target_public_id": ctx["unit"], "kind": "PROGRESS",
                "source": "DRIVER_REPORT", "occurred_at": ctx["occurred_at"],
                "route_progress": {"stage_execution_public_id": str(uuid4()), "distance_remaining_km": "10"},
                "impacted_cargo_public_ids": [ctx["cargo"]],
            }, str(uuid4()))
        assert missing.value.code == "REPORT_PROGRESS_STAGE_NOT_FOUND"
        with pytest.raises(eta.base.OperationalError):
            _progress(operational_app, ctx, "100.001")
        db.session.rollback()
        assert OperationalEventRouteProgress.query.count() == 0
