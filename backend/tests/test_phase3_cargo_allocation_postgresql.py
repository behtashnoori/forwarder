"""Disposable PostgreSQL 18 proof for P3-05 migration and Cargo locking."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.cargo_models import CargoAllocationRevision, CargoAllocationTransfer, ShipmentCargoItem
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import CargoType, UnitOfMeasure
from backend.operational_models import OperationalMembership, OperationalShipment, RouteCargoDestination, RouteStageExecution
from backend.services import cargo_allocation_service as allocations
from backend.services import operational_service as operations
from backend.services import transport_execution_service as executions
from backend.tests.test_phase3_transport_execution_postgresql import _create_payload, _seed_runtime


POSTGRES_URL = os.environ.get("P3_CARGO_ALLOCATION_POSTGRES_URL", "")
PARENT = "20261003_phase3_transport_execution"
HEAD = "20261004_phase3_cargo_allocation_trace"
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="requires explicit owned P3_CARGO_ALLOCATION_POSTGRES_URL")


def _worker(app, context, barrier, key, quantity):
    with app.app_context():
        barrier.wait()
        try:
            row, replayed = allocations.set_allocation(
                context["shipment"], context["cargo"], context["first"],
                {"dimension": "ACTUAL", "quantity": quantity, "expected_version": 1},
                {"id": context["owner"]}, key,
            )
            db.session.commit()
            return "ok", replayed, row.version
        except operations.OperationalError as exc:
            db.session.rollback()
            return exc.code, None, None
        finally:
            db.session.remove()


def _transfer_worker(app, context, barrier, key):
    with app.app_context():
        barrier.wait()
        try:
            movement, replayed = allocations.transfer(
                context["shipment"], context["cargo"],
                {"source_stage_execution_public_id": context["first"],
                 "target_stage_execution_public_id": context["second"],
                 "quantity": "20", "expected_source_version": 2,
                 "expected_target_version": 0},
                {"id": context["owner"]}, key,
            )
            db.session.commit()
            return "ok", replayed, movement.id
        except operations.OperationalError as exc:
            db.session.rollback()
            return exc.code, None, None
        finally:
            db.session.remove()


def test_postgresql18_migration_locking_and_atomic_transfer():
    parsed = make_url(POSTGRES_URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_p3_05_cargo_allocation_")
    engine = sa.create_engine(POSTGRES_URL)
    with engine.connect() as connection:
        assert int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) >= 180000
    config = alembic_config(POSTGRES_URL)
    command.upgrade(config, PARENT)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": POSTGRES_URL, "SECRET_KEY": "p3-05-postgresql"}, skip_startup=True)
    with app.app_context():
        context = _seed_runtime(app)
        membership = OperationalMembership.query.filter_by(user_id=context["owner"]).one()
        membership.permissions = sorted(set(membership.permissions or []) | {"operational_shipment.create"})
        shipment = OperationalShipment.query.filter_by(public_id=context["shipment"]).one()
        cargo_type = CargoType(immutable_code="P305_PG_PARTS", fa_name="قطعات", en_name="Parts", is_active=True)
        uom = UnitOfMeasure(immutable_code="P305_PG_CARTON", fa_name="کارتن", en_name="Carton", symbol="ctn", measurement_dimension="COUNT", is_active=True)
        db.session.add_all([cargo_type, uom])
        db.session.flush()
        cargo = ShipmentCargoItem(
            operational_shipment_id=shipment.id, line_number=1,
            cargo_owner_customer_id=context["carrier"], cargo_type=cargo_type, uom=uom,
            quantity=Decimal("100"), planned_quantity=Decimal("100"), actual_quantity=Decimal("95"),
            display_name_snapshot="Parts", cargo_type_code_snapshot=cargo_type.immutable_code,
            cargo_type_fa_snapshot=cargo_type.fa_name, cargo_type_en_snapshot=cargo_type.en_name,
            uom_code_snapshot=uom.immutable_code, uom_symbol_snapshot=uom.symbol,
            created_by=context["owner"], updated_by=context["owner"],
        )
        db.session.add(cargo)
        db.session.flush()
        db.session.add(RouteCargoDestination(
            route_plan_id=context["plan"], operational_shipment_id=shipment.id,
            shipment_cargo_item_id=cargo.id, destination_route_leg_id=context["leg"],
            created_by_user_id=context["owner"],
        ))
        first, _ = executions.create(context["shipment"], context["plan"], context["leg"], _create_payload(context, "P305-1"), {"id": context["owner"]}, "p305-pg-first")
        second, _ = executions.create(context["shipment"], context["plan"], context["leg"], _create_payload(context, "P305-2"), {"id": context["owner"]}, "p305-pg-second")
        context.update(cargo=cargo.public_id, cargo_id=cargo.id, shipment_id=shipment.id, legacy_unit_id=first.execution_unit_id, first=first.public_id, second=second.public_id)
        db.session.commit()
        db.session.remove()
        db.engine.dispose()

    with engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO execution_unit_cargo_allocation (public_id, execution_unit_id, shipment_cargo_item_id, operational_shipment_id, allocated_quantity, created_at, updated_at, created_by, updated_by) VALUES ('90000000-0000-4000-8000-000000000305', :unit_id, :cargo_id, :shipment_id, 7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :owner_id, :owner_id)"), {"unit_id": context["legacy_unit_id"], "cargo_id": context["cargo_id"], "shipment_id": context["shipment_id"], "owner_id": context["owner"]})
    command.upgrade(config, HEAD)
    assert {"cargo_allocation_revision", "cargo_allocation_transfer"} <= set(sa.inspect(engine).get_table_names())
    with engine.connect() as connection:
        legacy = connection.execute(sa.text("SELECT route_stage_execution_id, dimension, is_current, version, allocated_quantity FROM execution_unit_cargo_allocation WHERE public_id='90000000-0000-4000-8000-000000000305'")).one()
        assert legacy.route_stage_execution_id is None and legacy.dimension is None
        assert legacy.is_current is True and legacy.version == 1 and legacy.allocated_quantity == 7
        assert connection.execute(sa.text("SELECT count(*) FROM cargo_allocation_revision")).scalar_one() == 0
    command.downgrade(config, PARENT)
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT allocated_quantity FROM execution_unit_cargo_allocation WHERE public_id='90000000-0000-4000-8000-000000000305'")).scalar_one() == 7

    with app.app_context():
        row, _ = allocations.set_allocation(context["shipment"], context["cargo"], context["first"], {"dimension": "ACTUAL", "quantity": "50", "expected_version": 0}, {"id": context["owner"]}, "p305-pg-initial")
        db.session.commit()
        assert row.version == 1

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda args: _worker(app, context, barrier, *args), [("p305-pg-correct-1", "48"), ("p305-pg-correct-2", "47")]))
    assert sorted(outcome[0] for outcome in outcomes) == ["VERSION_CONFLICT", "ok"]

    with app.app_context():
        source = allocations._current(ShipmentCargoItem.query.filter_by(public_id=context["cargo"]).one().id, RouteStageExecution.query.filter_by(public_id=context["first"]).one().id, "ACTUAL")
        assert source is not None and source.version == 2
        quantity_before = source.allocated_quantity
        with pytest.raises(operations.OperationalError, match="less recorded actual quantity"):
            allocations.transfer(context["shipment"], context["cargo"], {"source_stage_execution_public_id": context["first"], "target_stage_execution_public_id": context["second"], "quantity": "60", "expected_source_version": 2, "expected_target_version": 0}, {"id": context["owner"]}, "p305-pg-too-much")
        db.session.rollback()
        assert CargoAllocationTransfer.query.count() == 0
        assert source.allocated_quantity == quantity_before
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        transfers = list(pool.map(lambda key: _transfer_worker(app, context, barrier, key), ["p305-pg-transfer-1", "p305-pg-transfer-2"]))
    assert sorted(outcome[0] for outcome in transfers) == ["VERSION_CONFLICT", "ok"]
    with app.app_context():
        assert CargoAllocationRevision.query.count() == 4
        assert CargoAllocationTransfer.query.count() == 1
        db.session.remove()
        db.engine.dispose()
    with pytest.raises(RuntimeError, match="history exists"):
        command.downgrade(config, PARENT)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    engine.dispose()
