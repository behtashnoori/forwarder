from datetime import datetime, timedelta

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.services.multi_unit_tracking_service import (
    TrackingValidationError,
    add_unit,
    add_update,
    build_public_unit_tracking,
    disable_tracking,
    enable_tracking,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed_request(status="won", tracking_code="trk-production-safe"):
    actor = ExpertUser(
        username="tracker",
        password_hash="not-used",
        full_name="Tracking Operator",
        role="expert",
    )
    req = ShipmentRequest(
        contact_phone="09120000000",
        status=status,
        status_request_status="new",
        tracking_code=tracking_code,
    )
    db.session.add_all([actor, req])
    db.session.commit()
    return actor, req


def test_enablement_requires_accepted_request_and_tracking_code(app):
    with app.app_context():
        actor, req = _seed_request(status="in_progress")
        with pytest.raises(TrackingValidationError, match="accepted"):
            enable_tracking(req, actor.id)

        req.status = "won"
        req.tracking_code = None
        with pytest.raises(TrackingValidationError, match="tracking code"):
            enable_tracking(req, actor.id)


def test_public_projection_aggregates_partial_delivery_and_hides_private_data(app):
    with app.app_context():
        actor, req = _seed_request()
        now = datetime(2026, 7, 15, 12, 0, 0)
        tracking = enable_tracking(req, actor.id, now=now - timedelta(hours=3))
        truck = add_unit(
            tracking,
            actor.id,
            unit_code="TRUCK-01",
            unit_type="truck",
            display_name="Truck 1",
        )
        container = add_unit(
            tracking,
            actor.id,
            unit_code="CONT-02",
            unit_type="container",
            display_name="Container 2",
            sort_order=1,
        )
        add_update(
            truck,
            actor.id,
            status="delivered",
            location="Tehran",
            customer_message="Delivered safely",
            internal_note="private operations detail",
            occurred_at=now - timedelta(hours=1),
            now=now,
        )
        add_update(
            container,
            actor.id,
            status="in_transit",
            location="Qom",
            customer_message="On route",
            occurred_at=now - timedelta(hours=2),
            now=now,
        )
        add_update(
            container,
            actor.id,
            status="exception",
            location="Private depot",
            internal_note="not for customer",
            is_customer_visible=False,
            occurred_at=now - timedelta(minutes=30),
            now=now,
        )
        db.session.commit()

        payload = build_public_unit_tracking(req)
        assert payload["aggregate_status"] == "partially_delivered"
        assert payload["unit_count"] == 2
        assert payload["delivered_unit_count"] == 1
        assert payload["is_partially_delivered"] is True
        assert payload["latest_update_at"] == (now - timedelta(hours=1)).isoformat()
        assert payload["units"][1]["latest_status"] == "in_transit"
        assert "internal_note" not in str(payload)
        assert "Private depot" not in str(payload)


def test_disable_tracking_retains_history_but_removes_public_projection(app):
    with app.app_context():
        actor, req = _seed_request()
        tracking = enable_tracking(req, actor.id)
        unit = add_unit(tracking, actor.id, unit_code="W-1", unit_type="wagon")
        add_update(
            unit,
            actor.id,
            status="arrived",
            location="Rail terminal",
            occurred_at=datetime.utcnow() - timedelta(minutes=1),
        )
        db.session.commit()

        disable_tracking(tracking, actor.id)
        db.session.commit()

        assert build_public_unit_tracking(req) is None
        assert len(tracking.units[0].updates) == 1
