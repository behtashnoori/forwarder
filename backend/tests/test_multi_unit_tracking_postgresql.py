"""Explicit disposable-PostgreSQL verification for multi-unit tracking."""
from datetime import datetime, timedelta
import os

import pytest
from sqlalchemy import inspect

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.services.multi_unit_tracking_service import (
    TrackingValidationError,
    add_unit,
    add_update,
    build_public_unit_tracking,
    enable_tracking,
)


def test_disposable_postgresql_tracking_contract():
    url = os.environ.get("FORWARDER_POSTGRES_TRACKING_TEST_URL")
    if not url:
        pytest.skip("explicit disposable PostgreSQL URL not provided")
    database_name = url.rstrip("/").rsplit("/", 1)[-1]
    assert database_name in {
        "forwarder_security_test_20260718",
        "forwarder_session_test_20260719",
    }, "refusing to mutate a non-approved disposable database"

    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": url, "SECRET_KEY": "synthetic-only"},
        skip_startup=True,
    )
    now = datetime(2026, 7, 15, 12, 0, 0)
    with app.app_context():
        columns = {column["name"]: column for column in inspect(db.engine).get_columns("shipment_transport_unit")}
        assert columns["vehicle_reference"]["type"].length == 100
        assert columns["vehicle_reference"]["nullable"] is True

        admin = ExpertUser(id=910001, username="synthetic-admin", password_hash="unused", full_name="Synthetic Admin", role="admin", is_active=True)
        expert = ExpertUser(id=910002, username="synthetic-expert", password_hash="unused", full_name="Synthetic Expert", role="expert", is_active=True)
        first = ShipmentRequest(id=920001, contact_phone="09000000001", status="won", status_request_status="new", tracking_code="SYNTHETIC-TRACK-001", assigned_to=expert.id)
        second = ShipmentRequest(id=920002, contact_phone="09000000002", status="in_progress", status_request_status="new", tracking_code="SYNTHETIC-TRACK-002", assigned_to=expert.id)
        try:
            db.session.add_all([admin, expert, first, second])
            db.session.commit()
            with pytest.raises(TrackingValidationError, match="accepted"):
                enable_tracking(second, expert.id, now=now)
            tracking = enable_tracking(first, expert.id, now=now)
            assert enable_tracking(first, expert.id, now=now + timedelta(minutes=1)) is tracking
            assert first.status == "won"

            units = []
            kinds = ("truck", "container", "wagon", "other")
            for index in range(20):
                units.append(add_unit(tracking, expert.id, unit_code=f"UNIT-{index:02d}", unit_type=kinds[index % 4], vehicle_reference=f"REF-{index:02d}"))
            db.session.flush()
            assert all(unit.id is not None for unit in units)
            assert build_public_unit_tracking(first)["aggregate_status"] == "not_started"

            for index, unit in enumerate(units):
                status = "delivered" if index < 10 else "in_transit"
                add_update(unit, expert.id, status=status, occurred_at=now - timedelta(hours=2), now=now)
            tie = now - timedelta(hours=1)
            add_update(units[10], expert.id, status="delayed", occurred_at=tie, now=now)
            add_update(units[10], expert.id, status="delivered", occurred_at=tie, now=now)
            add_update(units[11], expert.id, status="cancelled", occurred_at=now - timedelta(minutes=30), now=now)
            add_update(units[12], expert.id, status="delayed", occurred_at=now - timedelta(hours=3), now=now)
            hidden = add_update(units[13], expert.id, status="delayed", occurred_at=now - timedelta(minutes=5), is_customer_visible=False, internal_note="private synthetic note", now=now)
            units[19].is_active = False
            db.session.commit()

            payload = build_public_unit_tracking(first)
            assert payload["aggregate_status"] == "attention_required"
            assert payload["summary"]["total_units"] == 19
            assert len(payload["units"]) == 19
            assert payload["units"][10]["latest_status"] == "delivered"
            assert payload["last_updated_at"] == (now - timedelta(minutes=30)).isoformat()
            rendered = repr(payload)
            assert "private synthetic note" not in rendered
            assert str(hidden.id) not in rendered
            assert all("id" not in unit for unit in payload["units"])
            assert {unit["unit_type"] for unit in payload["units"]} == set(kinds)
        finally:
            db.session.rollback()
            for request_id in (920001, 920002):
                row = db.session.get(ShipmentRequest, request_id)
                if row:
                    db.session.delete(row)
            for expert_id in (910001, 910002):
                row = db.session.get(ExpertUser, expert_id)
                if row:
                    db.session.delete(row)
            db.session.commit()
