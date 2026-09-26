"""Owned PostgreSQL 18 only: ETA schema, immutable history, source races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from threading import Barrier
from uuid import uuid4

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import CargoType, UnitOfMeasure, ExpertUser, Province
from backend.cargo_models import ShipmentCargoItem as Cargo
from backend.eta_models import CargoEtaSnapshot as Snapshot, CargoEtaInput as Input
from backend.operational_models import OperationalShipment, OperationalMembership, RouteCargoDestination
from backend.services import eta_service as eta, reported_fact_service as reports, route_time_service as times
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime
from backend.tests.test_operational_vertical_slice import _auth

URL = os.environ.get("P3_ETA_POSTGRES_URL", "")
PREVIOUS = "20261009_phase3_route_time"
HEAD = "20261010_phase3_cargo_eta"
pytestmark = pytest.mark.skipif(not URL, reason="requires explicit owned P3_ETA_POSTGRES_URL")


def test_postgresql18_eta_upgrade_source_preservation_history_and_concurrent_ensure(monkeypatch):
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_p3_11_eta_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    config = alembic_config(URL)
    command.upgrade(config, PREVIOUS)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL, "SECRET_KEY": "synthetic-p311-owned"}, skip_startup=True)
    with app.app_context():
        ctx = _seed_runtime(app)
        membership = OperationalMembership.query.filter_by(user_id=ctx["owner"]).one()
        membership.permissions = [*membership.permissions, "operational_shipment.create"]
        shipment = OperationalShipment.query.filter_by(public_id=ctx["shipment"]).one()
        ctx.update(org=shipment.organization_id, shipment_id=shipment.id)
        admin = ExpertUser(username="p311-admin", password_hash="unused", full_name="Admin", role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        kind = CargoType(immutable_code="P311", fa_name="آزمایشی", en_name="Synthetic", is_active=True)
        uom = UnitOfMeasure(immutable_code="P311", fa_name="عدد", en_name="Each", symbol="ea", measurement_dimension="COUNT", is_active=True)
        db.session.add_all([admin, kind, uom, Province(id=800001, name_fa="مبدأ آزمایشی", code="P311-O"), Province(id=800002, name_fa="مقصد آزمایشی", code="P311-D")])
        db.session.flush()
        db.session.add(OperationalMembership(organization_id=ctx["org"], user_id=admin.id, permissions=[]))
        cargo = Cargo(operational_shipment_id=shipment.id, line_number=1, cargo_owner_customer_id=ctx["carrier"],
            cargo_type_id=kind.id, uom_id=uom.id, quantity=1, planned_quantity=1, actual_quantity=1,
            display_name_snapshot="Synthetic ETA", cargo_type_code_snapshot=kind.immutable_code,
            cargo_type_fa_snapshot=kind.fa_name, cargo_type_en_snapshot=kind.en_name,
            uom_code_snapshot=uom.immutable_code, uom_symbol_snapshot=uom.symbol, created_by=ctx["owner"], updated_by=ctx["owner"])
        db.session.add(cargo); db.session.flush()
        db.session.add(RouteCargoDestination(route_plan_id=ctx["plan"], operational_shipment_id=shipment.id,
            shipment_cargo_item_id=cargo.id, destination_route_leg_id=ctx["leg"], created_by_user_id=ctx["owner"]))
        db.session.commit()
        reference, _ = times.save({"id": admin.id}, {"origin": {"source_type": "province", "source_id": 800001},
            "destination": {"source_type": "province", "source_id": 800002}, "transport_mode": "road",
            "movement_min_minutes": 60, "movement_max_minutes": 120, "stop_min_minutes": 0, "stop_max_minutes": 0,
            "effective_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}, str(uuid4()))
        db.session.commit()
        ctx.update(cargo=cargo.public_id, cargo_id=cargo.id, reference=reference.id)
    tables = ("operational_shipment", "route_plan", "route_leg", "shipment_cargo_item", "organization_route_time_version")
    def source_rows():
        with engine.connect() as c:
            return {t: c.execute(sa.text(f"SELECT row_to_json(t)::text FROM {t} t ORDER BY id")).scalars().all() for t in tables}
    before = source_rows()
    command.upgrade(config, HEAD)
    assert source_rows() == before
    with engine.connect() as c:
        assert c.execute(sa.text("SELECT count(*) FROM cargo_eta_snapshot")).scalar_one() == 0
    command.downgrade(config, PREVIOUS); command.upgrade(config, HEAD)
    assert source_rows() == before

    app.config["phase1a"] = {"user": ctx["owner"], "outsider": ctx["outsider"]}
    headers = _auth(app)
    path = f"/api/operational-shipments/{ctx['shipment']}/cargo/{ctx['cargo']}/eta"
    barrier = Barrier(3)
    def ensure():
        barrier.wait()
        with app.test_client() as client:
            response = client.post(path + "/ensure", json={}, headers=headers)
            return response.status_code, response.get_json()
    with ThreadPoolExecutor(max_workers=3) as pool:
        values = list(pool.map(lambda _: ensure(), range(3)))
    assert [code for code, _ in values] == [200] * 3, values
    assert len({value["public_id"] for _, value in values}) == 1
    assert source_rows() == before
    with app.app_context():
        assert Snapshot.query.count() == 1
        assert Input.query.count() == 0  # missing progress is recorded honestly

    # A source appearing after calculation is read afresh before return. The
    # just-calculated result cannot masquerade as current after this race.
    original_project = eta.project
    created = []
    def raced_project(snapshot, **kwargs):
        value = original_project(snapshot, **kwargs)
        if not created:
            def add_report():
                with app.app_context():
                    from backend.operational_models import CanonicalLocation
                    location = CanonicalLocation.query.filter_by(source_type="province", source_id=800001).one()
                    row, _ = reports.create(ctx["shipment"], {"id": ctx["owner"]}, {"scope": "CARGO",
                        "target_public_id": ctx["cargo"], "kind": "LOCATION", "source": "DRIVER_REPORT",
                        "occurred_at": "2026-09-20T08:00:00Z", "location": {"canonical_location_public_id": location.public_id},
                        "impacted_cargo_public_ids": [ctx["cargo"]]}, str(uuid4()))
                    db.session.commit(); return row.event.public_id
            with ThreadPoolExecutor(max_workers=1) as pool:
                created.append(pool.submit(add_report).result(timeout=30))
        return value
    monkeypatch.setattr(eta, "project", raced_project)
    with app.test_client() as client:
        response = client.post(path + "/ensure", json={}, headers=headers)
        assert response.status_code == 200, response.get_json()
        assert response.get_json()["as_of"] == "2026-09-20T08:00:00+00:00"
        assert response.get_json()["next"]["available"]
        assert client.get(path + "/history", headers=_auth(app, "outsider")).status_code in {403, 404}
    after_report = source_rows()
    with app.test_client() as client:
        assert client.post(path + "/ensure", json={}, headers=headers).status_code == 200
        assert len(client.get(path + "/history", headers=headers).get_json()["items"]) == 2
    assert source_rows() == after_report

    for statement in (
        "UPDATE cargo_eta_snapshot SET source_basis='{}'", "DELETE FROM cargo_eta_snapshot",
        "UPDATE cargo_eta_input SET organization_id=organization_id", "DELETE FROM cargo_eta_input",
    ):
        with pytest.raises(sa.exc.DBAPIError), engine.begin() as c:
            c.execute(sa.text(statement))
    with engine.connect() as c:
        snap = c.execute(sa.text("SELECT id FROM cargo_eta_snapshot ORDER BY sequence DESC LIMIT 1")).scalar_one()
    with pytest.raises(sa.exc.DBAPIError), engine.begin() as c:
        c.execute(sa.text("INSERT INTO cargo_eta_input(snapshot_id,organization_id,reference_version_id) VALUES(:s,:org,:ref)"),
                  {"s": snap, "org": ctx["org"] + 1, "ref": ctx["reference"]})
    with pytest.raises(sa.exc.DBAPIError, match="sealed"), engine.begin() as c:
        c.execute(sa.text("INSERT INTO cargo_eta_input(snapshot_id,organization_id,reference_version_id) VALUES(:s,:org,:ref)"),
                  {"s": snap, "org": ctx["org"], "ref": ctx["reference"]})
    with pytest.raises(RuntimeError, match="history exists"):
        command.downgrade(config, PREVIOUS)
    with engine.connect() as c:
        assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    engine.dispose()
