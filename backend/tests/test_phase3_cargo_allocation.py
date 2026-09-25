"""P3-05 stage distribution, warnings, history and atomic transfer."""

from decimal import Decimal
from uuid import uuid4

import pytest

from backend.cargo_models import CargoAllocationRevision, CargoAllocationTransfer, ExecutionUnitCargoAllocation, ShipmentCargoItem
from backend.extensions import db
from backend.models import CargoType, UnitOfMeasure
from backend.operational_models import RouteCargoDestination, RouteLeg
from backend.services import cargo_allocation_service as allocations
from backend.services import operational_service
from backend.services import shared_transport_service
from backend.services import transport_execution_service as executions
from backend.tests.test_operational_vertical_slice import _auth, _user, operational_app
from backend.tests.test_phase3_transport_execution import _payload_for, _setup


def _fixture(app, *, second_stage=False):
    ctx = _setup(app)
    ids = app.config["phase1a"]
    cargo_type = CargoType(immutable_code="P305_ENGINE", fa_name="قطعات موتور", en_name="Engine parts", is_active=True)
    uom = UnitOfMeasure(immutable_code="P305_CARTON", fa_name="کارتن", en_name="Carton", symbol="ctn", measurement_dimension="COUNT", is_active=True)
    db.session.add_all([cargo_type, uom])
    db.session.flush()
    cargo = ShipmentCargoItem(
        operational_shipment_id=ctx["shipment_id"], line_number=1,
        cargo_owner_customer_id=ids["customer"], cargo_type=cargo_type, uom=uom,
        quantity=Decimal("100"), planned_quantity=Decimal("100"), actual_quantity=Decimal("95"),
        display_name_snapshot="Engine parts", cargo_type_code_snapshot=cargo_type.immutable_code,
        cargo_type_fa_snapshot=cargo_type.fa_name, cargo_type_en_snapshot=cargo_type.en_name,
        uom_code_snapshot=uom.immutable_code, uom_symbol_snapshot=uom.symbol,
        created_by=ids["user"], updated_by=ids["user"],
    )
    db.session.add(cargo)
    db.session.flush()
    first_leg = db.session.get(RouteLeg, ctx["leg"])
    terminal = first_leg
    if second_stage:
        terminal = RouteLeg(
            route_plan_id=ctx["plan"], sequence_number=2,
            parent_route_leg_id=first_leg.id,
            origin_location_id=first_leg.destination_location_id,
            destination_location_id=first_leg.origin_location_id,
            origin_snapshot=first_leg.destination_snapshot,
            destination_snapshot=first_leg.origin_snapshot,
            status="planned",
        )
        db.session.add(terminal)
        db.session.flush()
    db.session.add(RouteCargoDestination(
        route_plan_id=ctx["plan"], operational_shipment_id=ctx["shipment_id"],
        shipment_cargo_item_id=cargo.id, destination_route_leg_id=terminal.id,
        created_by_user_id=ids["user"],
    ))
    first, _ = executions.create(ctx["shipment"], ctx["plan"], ctx["leg"], _payload_for(ctx, identifier="TRUCK-12"), _user(app), "p305-first")
    second, _ = executions.create(ctx["shipment"], ctx["plan"], ctx["leg"], _payload_for(ctx, identifier="TRUCK-18"), _user(app), "p305-second")
    ctx.update(cargo=cargo.public_id, first=first.public_id, second=second.public_id)
    if second_stage:
        third, _ = executions.create(ctx["shipment"], ctx["plan"], terminal.id, _payload_for(ctx, identifier="TRUCK-30"), _user(app), "p305-third")
        ctx["third"] = third.public_id
    db.session.commit()
    return ctx


def _set(app, ctx, stage, dimension, quantity, version, key, **extra):
    return allocations.set_allocation(ctx["shipment"], ctx["cargo"], stage, {
        "dimension": dimension, "quantity": str(quantity), "expected_version": version, **extra,
    }, _user(app), key)


def test_planned_actual_split_warnings_revisions_and_cargo_total(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app, second_stage=True)
        planned_a, _ = _set(operational_app, ctx, ctx["first"], "PLANNED", 60, 0, "plan-a")
        _set(operational_app, ctx, ctx["second"], "PLANNED", 30, 0, "plan-b")
        actual_a, _ = _set(operational_app, ctx, ctx["first"], "ACTUAL", 55, 0, "actual-a")
        _set(operational_app, ctx, ctx["second"], "ACTUAL", 40, 0, "actual-b")
        db.session.commit()
        trace = allocations.trace(ctx["shipment"], ctx["cargo"], _user(operational_app))
        first_stage = trace["stages"][0]
        assert first_stage["planned_total"] == "90.000000"
        assert first_stage["actual_total"] == "95.000000"
        assert {warning["code"] for warning in first_stage["warnings"]} == {"PLAN_UNDER", "ACTUAL_VS_PLAN"}
        assert trace["cargo"]["actual_quantity"] == "95.000000"
        assert shared_transport_service.classification(actual_a.execution_unit_id) == "single_cargo"
        assert CargoAllocationTransfer.query.count() == 0

        revised, _ = _set(operational_app, ctx, ctx["first"], "PLANNED", 70, planned_a.version, "plan-revise", reason="New loading plan")
        corrected, _ = _set(operational_app, ctx, ctx["first"], "ACTUAL", 48, actual_a.version, "actual-correct", reason="Verified count")
        db.session.commit()
        assert revised.version == corrected.version == 2
        assert [(r.before_quantity, r.after_quantity) for r in CargoAllocationRevision.query.filter_by(allocation_id=planned_a.id).order_by(CargoAllocationRevision.id)] == [(Decimal("0"), Decimal("60")), (Decimal("60"), Decimal("70"))]
        assert [(r.before_quantity, r.after_quantity) for r in CargoAllocationRevision.query.filter_by(allocation_id=actual_a.id).order_by(CargoAllocationRevision.id)] == [(Decimal("0"), Decimal("55")), (Decimal("55"), Decimal("48"))]
        assert allocations.trace(ctx["shipment"], ctx["cargo"], _user(operational_app))["cargo"]["actual_quantity"] == "95.000000"

        stage2, _ = _set(operational_app, ctx, ctx["third"], "ACTUAL", 115, 0, "stage2-over")
        db.session.commit()
        trace = allocations.trace(ctx["shipment"], ctx["cargo"], _user(operational_app))
        assert trace["stages"][1]["actual_total"] == "115.000000"
        assert any(w["code"] == "ACTUAL_VS_KNOWN" and w["difference"] == "20.000000" for w in trace["stages"][1]["warnings"])
        assert stage2.dimension == "ACTUAL"


def test_atomic_same_stage_transfer_cross_stage_handoff_replay_and_denial(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app, second_stage=True)
        source, _ = _set(operational_app, ctx, ctx["first"], "ACTUAL", 50, 0, "source")
        db.session.commit()
        payload = {"source_stage_execution_public_id": ctx["first"], "target_stage_execution_public_id": ctx["second"], "quantity": "20", "expected_source_version": 1, "expected_target_version": 0, "context": "Khorgos"}
        movement, replay = allocations.transfer(ctx["shipment"], ctx["cargo"], payload, _user(operational_app), "transfer-1")
        db.session.commit()
        assert replay is False and movement.quantity == Decimal("20")
        assert allocations.transfer(ctx["shipment"], ctx["cargo"], payload, _user(operational_app), "transfer-1")[1] is True
        trace = allocations.trace(ctx["shipment"], ctx["cargo"], _user(operational_app))
        assert trace["stages"][0]["actual_total"] == "50.000000"
        assert source.allocated_quantity == Decimal("30")
        assert len(trace["transfers"]) == 1
        assert {r.action for r in CargoAllocationRevision.query.filter_by(transfer_id=movement.id)} == {"TRANSFER_IN", "TRANSFER_OUT"}

        target_stage = ctx["third"]
        handoff, _ = allocations.transfer(ctx["shipment"], ctx["cargo"], {"source_stage_execution_public_id": ctx["first"], "target_stage_execution_public_id": target_stage, "quantity": "30", "expected_source_version": 2, "expected_target_version": 0}, _user(operational_app), "handoff")
        db.session.commit()
        assert handoff.id and source.allocated_quantity == Decimal("30")
        trace = allocations.trace(ctx["shipment"], ctx["cargo"], _user(operational_app))
        assert trace["stages"][0]["actual_total"] == "50.000000"
        assert trace["stages"][1]["actual_total"] == "30.000000"
        assert any(w["code"] == "STAGE_CONTINUITY" for w in trace["stages"][1]["warnings"])
        assert CargoAllocationTransfer.query.count() == 2

        with pytest.raises(operational_service.OperationalError) as denied:
            allocations.set_allocation(ctx["shipment"], ctx["cargo"], ctx["first"], {"dimension": "PLANNED", "quantity": "10", "expected_version": 0}, _user(operational_app, "verifier"), "denied")
        assert denied.value.status in (403, 404)
        db.session.rollback()


def test_invalid_quantity_version_and_failed_transfer_leave_state_unchanged(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        source, _ = _set(operational_app, ctx, ctx["first"], "ACTUAL", 50, 0, "source")
        db.session.commit()
        for value in ("-1", "1.0000001", "NaN", "Infinity"):
            with pytest.raises(operational_service.OperationalError):
                _set(operational_app, ctx, ctx["second"], "ACTUAL", value, 0, f"invalid-{value}")
            db.session.rollback()
        with pytest.raises(operational_service.OperationalError) as conflict:
            _set(operational_app, ctx, ctx["first"], "ACTUAL", 48, 0, "stale")
        assert conflict.value.code == "VERSION_CONFLICT"
        db.session.rollback()
        with pytest.raises(operational_service.OperationalError) as failed:
            allocations.transfer(ctx["shipment"], ctx["cargo"], {"source_stage_execution_public_id": ctx["first"], "target_stage_execution_public_id": ctx["second"], "quantity": "60", "expected_source_version": 1, "expected_target_version": 0}, _user(operational_app), "too-much")
        assert failed.value.code == "TRANSFER_SOURCE_INSUFFICIENT"
        db.session.rollback()
        assert source.allocated_quantity == Decimal("50")
        assert CargoAllocationTransfer.query.count() == 0


def test_cargo_cannot_be_allocated_to_an_unselected_route_branch(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        first_leg = db.session.get(RouteLeg, ctx["leg"])
        sibling = RouteLeg(
            route_plan_id=ctx["plan"], sequence_number=3,
            parent_route_leg_id=first_leg.id,
            origin_location_id=first_leg.destination_location_id,
            destination_location_id=first_leg.origin_location_id,
            origin_snapshot=first_leg.destination_snapshot,
            destination_snapshot=first_leg.origin_snapshot,
            status="planned",
        )
        db.session.add(sibling)
        db.session.flush()
        wrong_stage, _ = executions.create(ctx["shipment"], ctx["plan"], sibling.id, _payload_for(ctx, identifier="WRONG-BRANCH"), _user(operational_app), "p305-wrong-branch")
        db.session.commit()
        with pytest.raises(operational_service.OperationalError) as rejected:
            _set(operational_app, ctx, wrong_stage.public_id, "PLANNED", 20, 0, "wrong-branch-allocation")
        assert rejected.value.code == "CARGO_STAGE_MISMATCH"
        db.session.rollback()
        assert CargoAllocationRevision.query.count() == 0


def test_http_stage_allocation_reopen_replay_and_fail_closed(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
    client = operational_app.test_client()
    root = f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items/{ctx['cargo']}"
    url = f"{root}/stage-executions/{ctx['first']}/allocation"
    payload = {"dimension": "PLANNED", "quantity": "60", "expected_version": 0}
    headers = {**_auth(operational_app), "Idempotency-Key": "p305-http-plan"}
    first = client.put(url, json=payload, headers=headers)
    assert first.status_code == 201, first.get_json()
    assert first.get_json()["allocation"]["quantity"] == "60.000000"
    replay = client.put(url, json=payload, headers=headers)
    assert replay.status_code == 200 and replay.get_json()["replayed"] is True
    trace = client.get(f"{root}/allocation-trace", headers=_auth(operational_app))
    assert trace.status_code == 200, trace.get_json()
    assert trace.get_json()["trace"]["stages"][0]["planned_total"] == "60.000000"
    assert any(w["code"] == "PLAN_UNDER" for w in trace.get_json()["trace"]["stages"][0]["warnings"])

    conflict = client.put(url, json={**payload, "quantity": "70"}, headers=headers)
    assert conflict.status_code == 409
    denied = client.put(url, json=payload, headers={**_auth(operational_app, "verifier"), "Idempotency-Key": "p305-denied"})
    assert denied.status_code in (403, 404)
    guessed = client.put(f"{root}/stage-executions/{uuid4()}/allocation", json=payload, headers={**_auth(operational_app), "Idempotency-Key": "p305-guessed"})
    assert guessed.status_code == 404
    foreign_cargo = client.get(f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items/{uuid4()}/allocation-trace", headers=_auth(operational_app))
    assert foreign_cargo.status_code == 404
    with operational_app.app_context():
        assert CargoAllocationRevision.query.count() == 1


def test_http_transfer_atomic_replay_and_history(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
    client = operational_app.test_client()
    root = f"/api/internal/operational-shipments/{ctx['shipment']}/cargo-items/{ctx['cargo']}"
    allocation_url = f"{root}/stage-executions/{ctx['first']}/allocation"
    created = client.put(allocation_url, json={"dimension": "ACTUAL", "quantity": "50", "expected_version": 0}, headers={**_auth(operational_app), "Idempotency-Key": "p305-http-actual"})
    assert created.status_code == 201, created.get_json()
    payload = {"source_stage_execution_public_id": ctx["first"], "target_stage_execution_public_id": ctx["second"], "quantity": "20", "expected_source_version": 1, "expected_target_version": 0, "context": "Khorgos"}
    headers = {**_auth(operational_app), "Idempotency-Key": "p305-http-transfer"}
    transferred = client.post(f"{root}/allocation-transfers", json=payload, headers=headers)
    assert transferred.status_code == 201, transferred.get_json()
    replayed = client.post(f"{root}/allocation-transfers", json=payload, headers=headers)
    assert replayed.status_code == 200 and replayed.get_json()["replayed"] is True
    trace = client.get(f"{root}/allocation-trace", headers=_auth(operational_app)).get_json()["trace"]
    quantities = sorted(row["quantity"] for unit in trace["stages"][0]["executions"] for row in unit["allocations"] if row["dimension"] == "ACTUAL")
    assert quantities == ["20.000000", "30.000000"]
    assert len(trace["transfers"]) == 1
    assert {row["action"] for row in trace["history"]} == {"CREATE", "TRANSFER_OUT", "TRANSFER_IN"}


def test_legacy_adapter_release_retains_provable_history(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        unit = allocations._stage(operational_service.scoped_shipment(ctx["shipment"], _user(operational_app)), ctx["first"]).execution_unit
        row = shared_transport_service.allocate(execution_public_id=unit.public_id, cargo_public_id=ctx["cargo"], allocated_quantity="20", user=_user(operational_app))
        db.session.commit()
        public_id = row.public_id
        shared_transport_service.release(execution_public_id=unit.public_id, allocation_public_id=public_id, user=_user(operational_app))
        db.session.commit()
        retained = ExecutionUnitCargoAllocation.query.filter_by(public_id=public_id).one()
        assert retained.is_current is False
        assert retained.route_stage_execution_id is None and retained.dimension is None
        assert [(revision.action, revision.before_quantity, revision.after_quantity) for revision in CargoAllocationRevision.query.filter_by(allocation_id=retained.id).order_by(CargoAllocationRevision.revision_number)] == [("LEGACY_RECORD", Decimal("0"), Decimal("20")), ("LEGACY_RELEASE", Decimal("20"), Decimal("0"))]
