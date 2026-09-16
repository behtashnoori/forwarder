"""Run only through the owned disposable PostgreSQL cluster launcher."""

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest, ShipmentTransportUnitUpdate
from backend.operational_models import OperationalIdempotency, OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens
from backend.services.multi_unit_tracking_service import add_unit, add_update, enable_tracking
from backend.services.tracking_time import manual, offset


def test_owned_postgres_upgrade_roundtrip_and_safe_downgrade():
    url = os.environ.get("FWD05_DISPOSABLE_DATABASE_URL")
    own_data = os.environ.get("FWD05_OWN_CLUSTER_DATA")
    if not url or not own_data:
        pytest.skip("owned disposable PostgreSQL cluster required")
    assert Path(own_data).resolve().name == "data"
    assert "forwarder_fwd05_qualification" in url
    config = Config("backend/migrations/alembic.ini")
    predecessor = "20260916_fwd05_quote_response"
    command.upgrade(config, predecessor)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": url, "SECRET_KEY": "synthetic-fwd06"}, skip_startup=True)
    with app.app_context():
        assert "occurred_at_utc" not in {x["name"] for x in inspect(db.engine).get_columns("shipment_transport_unit_update")}
        legacy_actor = ExpertUser(username="synthetic-legacy-m1", password_hash="unused", full_name="Synthetic Legacy", role="expert", is_active=True)
        legacy_org = OperationalOrganization(name="Synthetic Legacy M1 Organization")
        db.session.add_all([legacy_actor, legacy_org])
        db.session.flush()
        legacy_request = ShipmentRequest(ownership_scope="TENANT", operational_organization_id=legacy_org.id,
                                         contact_phone="09000000012", status="won", status_request_status="new",
                                         tracking_code="SYNTHETIC-LEGACY-M1", assigned_to=legacy_actor.id)
        db.session.add(legacy_request)
        db.session.flush()
        legacy_unit = add_unit(enable_tracking(legacy_request, legacy_actor.id), legacy_actor.id,
                               unit_code="LEGACY-M1", unit_type="truck")
        db.session.flush()
        legacy_id = db.session.execute(text("""
            INSERT INTO shipment_transport_unit_update
            (unit_id, operational_organization_id, ownership_scope, status,
             occurred_at, created_at, is_customer_visible)
            VALUES (:unit, :org, 'TENANT', 'loading',
             '2026-07-14 09:00:00', '2026-07-14 10:00:00', true)
            RETURNING id
        """), {"unit": legacy_unit.id, "org": legacy_org.id}).scalar_one()
        db.session.commit()
        legacy_before = db.session.execute(text("""
            SELECT unit_id, operational_organization_id, ownership_scope, status,
                   occurred_at, created_at, is_customer_visible
            FROM shipment_transport_unit_update WHERE id=:id
        """), {"id": legacy_id}).one()
        db.session.commit()
    command.upgrade(config, "head")
    with app.app_context():
        columns = {x["name"]: x for x in inspect(db.engine).get_columns("shipment_transport_unit_update")}
        assert {"occurred_at_utc", "time_input_wall", "time_input_basis", "time_input_source", "time_input_policy"} <= columns.keys()
        assert all(columns[name]["nullable"] for name in ("occurred_at_utc", "time_input_wall", "time_input_basis", "time_input_source", "time_input_policy"))
        legacy_after = db.session.execute(text("""
            SELECT unit_id, operational_organization_id, ownership_scope, status,
                   occurred_at, created_at, is_customer_visible
            FROM shipment_transport_unit_update WHERE id=:id
        """), {"id": legacy_id}).one()
        assert legacy_after == legacy_before
        historical = db.session.get(ShipmentTransportUnitUpdate, legacy_id)
        assert all(getattr(historical, name) is None for name in
                   ("occurred_at_utc", "time_input_wall", "time_input_basis", "time_input_source", "time_input_policy"))
        db.session.commit()
    command.downgrade(config, predecessor)
    with app.app_context():
        assert "occurred_at_utc" not in {x["name"] for x in inspect(db.engine).get_columns("shipment_transport_unit_update")}
    command.upgrade(config, "head")
    with app.app_context():
        actor = ExpertUser(username="synthetic-m1", password_hash="unused", full_name="Synthetic M1", role="expert", is_active=True)
        org = OperationalOrganization(name="Synthetic M1 Organization")
        db.session.add_all([actor, org])
        db.session.flush()
        request = ShipmentRequest(ownership_scope="TENANT", operational_organization_id=org.id,
                                  contact_phone="09000000011", status="won", status_request_status="new",
                                  tracking_code="SYNTHETIC-M1-TRACK", assigned_to=actor.id)
        db.session.add(request)
        db.session.flush()
        tracking = enable_tracking(request, actor.id)
        unit = add_unit(tracking, actor.id, unit_code="M1-1", unit_type="truck")
        snapshot = manual("2026-07-15T12:00", "tracking.manual-iran.v1")
        row = add_update(unit, actor.id, status="in_transit", occurred_at=snapshot[0], time_snapshot=snapshot)
        machine_snapshot = offset("2026-07-15T13:00:00+04:00")
        machine_row = add_update(unit, actor.id, status="at_checkpoint", occurred_at=machine_snapshot[0], time_snapshot=machine_snapshot)
        db.session.commit()
        row_id = row.id
        machine_id = machine_row.id
        db.session.expire_all()
        row = db.session.get(ShipmentTransportUnitUpdate, row_id)
        assert row.occurred_at_utc.astimezone(timezone.utc) == datetime(2026, 7, 15, 8, 30, tzinfo=timezone.utc)
        assert row.occurred_at == datetime(2026, 7, 15, 8, 30)
        assert row.time_input_basis == "Asia/Tehran"
        machine_row = db.session.get(ShipmentTransportUnitUpdate, machine_id)
        assert machine_row.time_input_wall == "2026-07-15T13:00:00"
        assert machine_row.time_input_basis == "+04:00"
        assert machine_row.time_input_policy is None
        assert machine_row.occurred_at == datetime(2026, 7, 15, 9, 0)
        membership = OperationalMembership(organization_id=org.id, user_id=actor.id, permissions=[])
        db.session.add(membership)
        db.session.commit()
        membership_id = membership.id
        token = create_session_tokens(actor.id)["access_token"]
        path = f"/api/expert/requests/{request.public_id}/tracking/units/{unit.id}/updates"
        # A DB-level incomplete envelope is rejected independently of the route.
        with pytest.raises(Exception):
            db.session.execute(text("UPDATE shipment_transport_unit_update SET time_input_policy = NULL WHERE id = :id"), {"id": row_id})
            db.session.commit()
        db.session.rollback()
        for wall, basis, source, policy in (
            ("2026-07-15T12:00", None, "manual", "tracking.manual-iran.v1"),
            ("2026-07-15 12:00", "Asia/Tehran", "manual", "tracking.manual-iran.v1"),
            ("2026-07-15T12:00:00.1234567", "+03:30", "offset", None),
            ("2026-07-15T12:00:00", "Asia/Tehran", "offset", None),
        ):
            with pytest.raises(Exception):
                db.session.execute(text("""
                    INSERT INTO shipment_transport_unit_update
                    (unit_id, operational_organization_id, ownership_scope, status,
                     occurred_at, occurred_at_utc, time_input_wall, time_input_basis,
                     time_input_source, time_input_policy, is_customer_visible, created_at)
                    VALUES (:unit, :org, 'TENANT', 'loading',
                     '2026-07-15 08:30:00', '2026-07-15 08:30:00+00',
                     :wall, :basis, :source, :policy, true, now())
                """), {"unit": unit.id, "org": org.id, "wall": wall,
                       "basis": basis, "source": source, "policy": policy})
                db.session.commit()
            db.session.rollback()
        with pytest.raises(Exception):
            db.session.execute(text("""
                INSERT INTO shipment_transport_unit_update
                (unit_id, operational_organization_id, ownership_scope, status,
                 occurred_at, occurred_at_utc, time_input_wall, time_input_basis,
                 time_input_source, time_input_policy, is_customer_visible, created_at)
                VALUES (:unit_id, :org_id, 'TENANT', 'loading',
                 '2026-07-15 07:00:00', '2026-07-15 07:00:00+00',
                 '2026-07-15T12:00:00', '+04:00', 'offset', NULL, true, now())
            """), {"unit_id": unit.id, "org_id": org.id})
            db.session.commit()
        db.session.rollback()
        with pytest.raises(Exception):
            db.session.execute(text("UPDATE shipment_transport_unit_update SET occurred_at = '2026-07-15 10:00:00' WHERE id = :id"), {"id": row_id})
            db.session.commit()
        db.session.rollback()
    headers = {"Authorization": "Bearer " + token, "Idempotency-Key": "m1-race"}
    payload = {"status": "delayed", "time_input_wall": "2026-07-16T12:00",
               "time_input_policy": "tracking.manual-iran.v1"}

    def post_once():
        return app.test_client().post(path, headers=headers, json=payload)

    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(lambda _: post_once(), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 201]
    assert app.test_client().post(path, headers=headers, json={**payload, "status": "loading"}).status_code == 409
    restarted = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": url,
                            "SECRET_KEY": "synthetic-fwd06"}, skip_startup=True)
    assert restarted.test_client().post(path, headers=headers, json=payload).status_code == 200
    with restarted.app_context():
        persisted = db.session.get(ShipmentTransportUnitUpdate, row_id)
        assert persisted.occurred_at == datetime(2026, 7, 15, 8, 30)
        assert persisted.time_input_wall == "2026-07-15T12:00"
    with app.app_context():
        assert db.session.query(ShipmentTransportUnitUpdate).count() == 4
        member = db.session.get(OperationalMembership, membership_id)
        member.is_active = False
        db.session.commit()
    assert app.test_client().post(path, headers=headers, json=payload).status_code in (403, 404)
    with pytest.raises(RuntimeError, match="downgrade refused before DDL"):
        command.downgrade(config, predecessor)
    with app.app_context():
        assert "occurred_at_utc" in {x["name"] for x in inspect(db.engine).get_columns("shipment_transport_unit_update")}
        assert db.session.get(ShipmentTransportUnitUpdate, row_id).time_input_policy == "tracking.manual-iran.v1"
        assert db.session.query(OperationalIdempotency).filter_by(operation="tracking.update.append", idempotency_key="m1-race").count() == 1
        db.session.get(OperationalMembership, membership_id).is_active = True
        db.session.commit()
    assert app.test_client().post(path, headers=headers, json=payload).status_code == 200
    # Exercise the actual pre-M1 application against retained schema. Rollback
    # mode is database read-only: old writes cannot create provenance-free events.
    with tempfile.TemporaryDirectory(prefix="forwarder-fwd06-old-app-") as previous:
        archive = Path(previous) / "baseline.zip"
        subprocess.run(["git", "archive", "--format=zip", "--output", str(archive),
                        "0e14d3df7d8d2b704eb7f37138dd09850d9fc9a9", "backend"], check=True)
        with zipfile.ZipFile(archive) as packaged:
            packaged.extractall(previous)
        script = """
import os
from sqlalchemy import text
from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest, ShipmentTransportUnitUpdate
from backend.services.multi_unit_tracking_service import build_internal_unit_tracking
from backend.operational_models import OperationalIdempotency
app = create_app({'TESTING': True, 'SECRET_KEY': 'synthetic-fwd06',
    'SQLALCHEMY_DATABASE_URI': os.environ['FWD05_DISPOSABLE_DATABASE_URL'],
    'SQLALCHEMY_ENGINE_OPTIONS': {'connect_args': {'options': '-c default_transaction_read_only=on'}}}, skip_startup=True)
with app.app_context():
    request = db.session.query(ShipmentRequest).filter_by(tracking_code='SYNTHETIC-M1-TRACK').one()
    assert build_internal_unit_tracking(request)['units']
    assert db.session.query(ShipmentTransportUnitUpdate).count() == 4
    assert db.session.query(OperationalIdempotency).filter_by(idempotency_key='m1-race').count() == 1
    assert db.session.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
    try:
        db.session.execute(text("UPDATE shipment_transport_unit_update SET status='loading'"))
    except Exception:
        db.session.rollback()
    else:
        raise AssertionError('old application writes must be stopped')
"""
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=previous,
                                capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stderr[-2000:]
    assert app.test_client().post(path, headers=headers, json=payload).status_code == 200
