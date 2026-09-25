"""Owned PostgreSQL 18 delivery migration, immutable facts and real command races."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal
from uuid import uuid4
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.cargo_models import ShipmentCargoItem
from backend.models import CargoType, UnitOfMeasure, CaseDocumentFile
from backend.delivery_models import CargoDeliveryEvidence
from backend.document_context_models import OperationalDocumentContext
from backend.operational_models import OperationalShipment, OperationalMembership
from backend.services import delivery_service as deliveries, document_context_service as contexts
from backend.services.operational_service import OperationalError
from backend.services.case_document_service import DocumentError
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime

URL = os.environ.get("P3_CARGO_DELIVERY_POSTGRES_URL", "")
PARENT = "20261007_phase3_reported_facts"
HEAD = "20261008_phase3_cargo_delivery"
pytestmark = pytest.mark.skipif(not URL, reason="requires owned P3_CARGO_DELIVERY_POSTGRES_URL")


def test_postgresql18_delivery_migration_constraints_and_concurrent_commands():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_p3_08_delivery_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    config = alembic_config(URL)
    command.upgrade(config, PARENT)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL, "SECRET_KEY": "synthetic-p308"}, skip_startup=True)
    with app.app_context():
        ctx = _seed_runtime(app)
        membership = OperationalMembership.query.filter_by(user_id=ctx["owner"]).one()
        membership.permissions = [*membership.permissions, "operational_shipment.create"]
        shipment = OperationalShipment.query.filter_by(public_id=ctx["shipment"]).one()
        shipment.lifecycle_status = "completed"
        cargo_type = CargoType(immutable_code="PG308_PARTS", fa_name="قطعات", en_name="Parts", is_active=True)
        uom = UnitOfMeasure(immutable_code="PG308_CARTON", fa_name="کارتن", en_name="Carton", symbol="ctn", measurement_dimension="COUNT", is_active=True)
        wrong_uom = UnitOfMeasure(immutable_code="PG308_KG", fa_name="کیلوگرم", en_name="Kilogram", symbol="kg", measurement_dimension="WEIGHT", is_active=True)
        db.session.add_all([cargo_type, uom, wrong_uom]); db.session.flush()
        cargo = ShipmentCargoItem(operational_shipment_id=shipment.id, line_number=1,
            cargo_owner_customer_id=ctx["carrier"], cargo_type_id=cargo_type.id, uom_id=uom.id,
            quantity=100, planned_quantity=100, actual_quantity=100, display_name_snapshot="Cargo A",
            cargo_type_code_snapshot=cargo_type.immutable_code, cargo_type_fa_snapshot=cargo_type.fa_name,
            cargo_type_en_snapshot=cargo_type.en_name, uom_code_snapshot=uom.immutable_code,
            uom_symbol_snapshot=uom.symbol, created_by=ctx["owner"], updated_by=ctx["owner"])
        db.session.add(cargo); db.session.commit()
        ctx.update(cargo=cargo.public_id, uom=uom.public_id, wrong_uom=wrong_uom.id, shipment_id=shipment.id)
        db.session.remove(); db.engine.dispose()
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM cargo_delivery")).scalar_one() == 0
        assert connection.execute(sa.text("SELECT lifecycle_status FROM operational_shipment WHERE id=:id"), {"id": ctx["shipment_id"]}).scalar_one() == "completed"
    command.downgrade(config, PARENT)
    command.upgrade(config, HEAD)
    payload = {"cargo_public_id": ctx["cargo"], "quantity": "60", "uom_public_id": ctx["uom"],
        "destination_text": "انبار واقعی", "occurred_at": "2026-09-21T08:00:00Z", "expected_version": 0}
    barrier = Barrier(2)
    def worker(data, key):
        with app.app_context():
            barrier.wait(timeout=15)
            try:
                row, created = deliveries.create(ctx["shipment"], {"id": ctx["owner"]}, data, key)
                result = ("ok", created, row.public_id)
                db.session.commit(); return result
            except OperationalError as error:
                db.session.rollback(); return (error.code, False, None)
            finally: db.session.remove()
    def race(jobs):
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(worker, data, key) for data, key in jobs]
            return [job.result(timeout=30) for job in pending]
    results = race([(payload, "same-request")] * 2)
    assert sorted(x[1] for x in results) == [False, True] and results[0][2] == results[1][2]
    original = results[0][2]
    barrier = Barrier(2)
    correction = {**payload, "quantity": "58", "expected_version": 1, "corrects_public_id": original}
    results = race([(correction, f"correction-{i}") for i in range(2)])
    assert sorted(x[0] for x in results) == ["DELIVERY_VERSION_CONFLICT", "ok"]
    barrier = Barrier(2)
    results = race([({**payload, "quantity": "35"}, "separate-one"), ({**payload, "quantity": "9"}, "separate-two")])
    assert all(x[0] == "ok" and x[1] for x in results) and results[0][2] != results[1][2]
    with app.app_context():
        result = deliveries.listing(ctx["shipment"], {"id": ctx["owner"]})
        assert result["total"] == 4 and Decimal(result["cargo"][0]["delivered"]) == 102
        assert Decimal(result["cargo"][0]["excess"]) == 2
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        assert shipment.lifecycle_status == "completed"
        assert ShipmentCargoItem.query.one().actual_quantity == 100
        with pytest.raises(OperationalError) as denied:
            deliveries.create(ctx["shipment"], {"id": ctx["outsider"]}, payload, "foreign-owner")
        assert denied.value.status == 404
        db.session.rollback()
        # The same document transaction owns both context and evidence. Rollback removes both.
        document = CaseDocumentFile(owner_type="SHIPMENT", operational_shipment_id=shipment.id,
            operational_organization_id=shipment.organization_id, is_miscellaneous=True,
            custom_title="Evidence", original_filename="evidence.pdf", safe_download_filename="evidence.pdf",
            storage_key="synthetic/evidence.pdf", canonical_extension="pdf", detected_mime_type="application/pdf",
            file_size_bytes=10, sha256_hash="0" * 64, version_number=1, uploaded_by=ctx["owner"])
        db.session.add(document); db.session.flush()
        prepared = contexts.prepare(shipment, "DELIVERY", original, "CARGO_OWNER", [])
        contexts.attach(shipment, document, ctx["owner"], prepared)
        assert CargoDeliveryEvidence.query.count() == 1
        db.session.rollback()
        assert CargoDeliveryEvidence.query.count() == CaseDocumentFile.query.count() == 0
        # A replacement can commit after the route loaded a file. The context
        # command must reread the exact file after its shared Shipment lock.
        stale = CaseDocumentFile(owner_type="SHIPMENT", operational_shipment_id=shipment.id,
            operational_organization_id=shipment.organization_id, is_miscellaneous=True,
            custom_title="Stale evidence", original_filename="stale.pdf", safe_download_filename="stale.pdf",
            storage_key="synthetic/stale.pdf", canonical_extension="pdf", detected_mime_type="application/pdf",
            file_size_bytes=10, sha256_hash="1" * 64, version_number=1, uploaded_by=ctx["owner"])
        db.session.add(stale); db.session.flush()
        contexts.attach(shipment, stale, ctx["owner"], contexts.prepare(shipment, "CARGO", ctx["cargo"], "INTERNAL", []))
        db.session.commit()
        stale_id = stale.id
        assert stale.status == "active"
        with engine.begin() as connection:
            connection.execute(sa.text("UPDATE case_document_file SET status='superseded' WHERE id=:id"), {"id": stale_id})
        assert stale.status == "active"  # deliberately stale ORM identity, as in two requests
        with pytest.raises(DocumentError) as rejected:
            contexts.revise(shipment, stale, ctx["owner"], context_type="DELIVERY", target_public_id=original,
                            visibility="CARGO_OWNER", expected_version=1)
        assert rejected.value.status == 404
        db.session.rollback()
        assert CargoDeliveryEvidence.query.count() == 0
        retained_context = OperationalDocumentContext.query.filter_by(document_file_id=stale_id).one()
        assert retained_context.version == 1 and retained_context.context_type == "CARGO"
        db.session.remove(); db.engine.dispose()
    with engine.connect() as connection:
        original_pk = connection.execute(sa.text("SELECT id FROM cargo_delivery WHERE public_id=:id"), {"id": original}).scalar_one()
        foreign_org = connection.execute(sa.text("SELECT organization_id FROM operational_membership WHERE user_id=:id"), {"id": ctx["outsider"]}).scalar_one()
    for sql in ("UPDATE cargo_delivery SET quantity=1 WHERE id=:id", "DELETE FROM cargo_delivery WHERE id=:id"):
        with pytest.raises(sa.exc.DBAPIError, match="immutable"):
            with engine.begin() as connection: connection.execute(sa.text(sql), {"id": original_pk})
    for replacement, parameters in (("organization_id", {"wrong": foreign_org}), ("uom_id", {"wrong": ctx["wrong_uom"]})):
        columns = ["organization_id", "operational_shipment_id", "cargo_item_id", "quantity", "uom_id", "uom_code_snapshot", "uom_symbol_snapshot", "destination_text", "occurred_at", "recorded_at", "actor_user_id", "revision"]
        selected = [":wrong" if column == replacement else column for column in columns]
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(sa.text(f"INSERT INTO cargo_delivery (public_id,{','.join(columns)}) SELECT :public_id,{','.join(selected)} FROM cargo_delivery WHERE id=:id"), {**parameters, "public_id": str(uuid4()), "id": original_pk})
    with pytest.raises(RuntimeError, match="rollback would erase"):
        command.downgrade(config, PARENT)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        assert connection.execute(sa.text("SELECT count(*) FROM cargo_delivery")).scalar_one() == 4
    engine.dispose()
