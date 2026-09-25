"""Owned PostgreSQL 18 migration preservation and report/correction races."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timezone
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.operational_models import OperationalEvent, OperationalMembership
from backend.services import reported_fact_service as reports, transport_execution_service as executions
from backend.services.operational_service import OperationalError
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime, _create_payload

URL = os.environ.get("P3_REPORTED_FACTS_POSTGRES_URL", "")
PARENT = "20261006_customer_entitlement"
HEAD = "20261007_phase3_reported_facts"
pytestmark = pytest.mark.skipif(not URL, reason="requires owned P3_REPORTED_FACTS_POSTGRES_URL")


def test_postgresql18_report_history_constraints_migration_and_races():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_p3_07_reports_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    config = alembic_config(URL)
    command.upgrade(config, PARENT)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL, "SECRET_KEY": "synthetic-p307"}, skip_startup=True)
    with app.app_context():
        ctx = _seed_runtime(app)
        membership = OperationalMembership.query.filter_by(user_id=ctx["owner"]).one()
        membership.permissions = [*membership.permissions, "operational_shipment.create"]
        stage, _ = executions.create(ctx["shipment"], ctx["plan"], ctx["leg"], _create_payload(ctx, "PG-REPORT"), {"id": ctx["owner"]}, "report-unit")
        unit_pk, unit_id = stage.execution_unit_id, stage.execution_unit.public_id
        db.session.commit()
        db.session.remove(); db.engine.dispose()
    with engine.begin() as connection:
        legacy_id = connection.execute(sa.text("""INSERT INTO operational_event
            (public_id, execution_unit_id, event_type, source, occurred_at, recorded_at, actor_user_id,
             internal_note, visibility, idempotency_key, request_hash, attention_required, delayed)
            VALUES ('70000000-0000-4000-8000-000000000007', :unit, 'legacy_report', 'expert',
             '2025-01-01T00:00:00Z', CURRENT_TIMESTAMP, :actor, 'Retain legacy evidence', 'internal',
             'legacy-report', 'synthetic', false, false) RETURNING id"""), {"unit": unit_pk, "actor": ctx["owner"]}).scalar_one()
    with engine.begin() as connection:
        connection.execute(sa.text("UPDATE operational_event SET event_type='phase3_reported_fact' WHERE id=:id"), {"id": legacy_id})
    with pytest.raises(RuntimeError, match="collides with legacy data"):
        command.upgrade(config, HEAD)
    # Restore only this test-created legacy marker to exercise preservation.
    with engine.begin() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == PARENT
        connection.execute(sa.text("UPDATE operational_event SET event_type='legacy_report' WHERE id=:id"), {"id": legacy_id})
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM operational_event_report_context")).scalar_one() == 0
        assert connection.execute(sa.text("SELECT internal_note FROM operational_event WHERE id=:id"), {"id": legacy_id}).scalar_one() == "Retain legacy evidence"
    command.downgrade(config, PARENT)
    command.upgrade(config, HEAD)
    payload = {"scope": "EXECUTION_UNIT", "target_public_id": unit_id, "kind": "LOCATION",
        "source": "DRIVER_REPORT", "occurred_at": "2026-09-20T07:00:00Z", "location": {"location_text": "Reported border"}}
    barrier = Barrier(2)
    def worker(data, key):
        with app.app_context():
            barrier.wait(timeout=15)
            try:
                row, created = reports.create(ctx["shipment"], {"id": ctx["owner"]}, data, key)
                result = ("ok", created, row.event.public_id)
                db.session.commit()
                return result
            except OperationalError as error:
                db.session.rollback()
                return (error.code, False, None)
            finally: db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(worker, payload, "concurrent-same") for _ in range(2)]
        results = [job.result(timeout=30) for job in jobs]
    assert sorted(x[1] for x in results) == [False, True]
    assert results[0][2] == results[1][2]
    original = results[0][2]
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(worker, {**payload, "corrects_public_id": original, "reason": f"Correction {i}"}, f"correction-{i}") for i in range(2)]
        results = [job.result(timeout=30) for job in jobs]
    assert sorted(x[0] for x in results) == ["REPORT_ALREADY_CORRECTED", "ok"]
    with engine.connect() as connection:
        report_id = connection.execute(sa.text("SELECT id FROM operational_event WHERE public_id=:id"), {"id": original}).scalar_one()
        foreign_org = connection.execute(sa.text("SELECT organization_id FROM operational_membership WHERE user_id=:id"), {"id": ctx["outsider"]}).scalar_one()
    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as connection:
            connection.execute(sa.text("""INSERT INTO operational_event
                (public_id, organization_id, execution_unit_id, event_type, source, occurred_at, recorded_at,
                 actor_user_id, visibility, idempotency_key, request_hash, attention_required, delayed)
                VALUES ('70000000-0000-4000-8000-000000000099', :org, :unit, 'legacy', 'expert',
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :actor, 'internal', 'cross-tenant-event', 'test', false, false)"""),
                {"org": foreign_org, "unit": unit_pk, "actor": ctx["owner"]})
    for sql in (
        "UPDATE operational_event SET internal_note='rewrite' WHERE id=:id",
        "UPDATE operational_event SET event_type='legacy' WHERE id=:id",
        "DELETE FROM operational_event_report_context WHERE operational_event_id=:id",
    ):
        with pytest.raises(sa.exc.DBAPIError, match="immutable"):
            with engine.begin() as connection: connection.execute(sa.text(sql), {"id": report_id})
    with app.app_context():
        listing = reports.listing(ctx["shipment"], {"id": ctx["owner"]})
        assert len(listing["items"]) == 2 and len(listing["reported_locations"]) == 1
        assert {x["status"] for x in listing["items"]} == {"CURRENT", "SUPERSEDED"}
        with pytest.raises(OperationalError) as denied:
            reports.listing(ctx["shipment"], {"id": ctx["outsider"]})
        assert denied.value.status == 404
        db.session.remove(); db.engine.dispose()
    with pytest.raises(RuntimeError, match="rollback would erase"):
        command.downgrade(config, PARENT)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    engine.dispose()
