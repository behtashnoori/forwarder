"""PostgreSQL-only verification for tracking-location references and snapshots."""

from datetime import datetime, timedelta
import os
import re

import pytest
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest, TrackingLocationReference
from backend.services.multi_unit_tracking_service import (
    add_unit,
    add_update,
    build_internal_unit_tracking,
    enable_tracking,
)
from backend.services.tracking_location_bootstrap_service import ROWS, bootstrap


def test_tracking_locations_on_disposable_postgresql():
    url = os.environ.get("FORWARDER_TRACKING_LOCATION_POSTGRES_URL")
    if not url:
        pytest.skip("explicit disposable tracking-location PostgreSQL URL not provided")
    assert re.fullmatch(
        r"forwarder_tracking_location_migration_test_\d{14}[0-9a-f]{6}",
        url.rstrip("/").rsplit("/", 1)[-1],
    )

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": url,
            "SECRET_KEY": "synthetic-tracking-location-only",
        },
        skip_startup=True,
    )
    with app.app_context():
        request_id = 930003
        user_id = 930002
        old_request = db.session.get(ShipmentRequest, request_id)
        if old_request:
            db.session.delete(old_request)
        old_user = db.session.get(ExpertUser, user_id)
        if old_user:
            db.session.delete(old_user)
        db.session.commit()

        try:
            assert bootstrap() == {
                "inserted": 0,
                "updated": 0,
                "unchanged": len(ROWS),
                "total": len(ROWS),
                "applied": False,
            }
            assert TrackingLocationReference.query.count() == 64
            osh = TrackingLocationReference.query.filter_by(internal_key="KG-OSH").one()
            assert osh.country_code == "KG"
            assert set(osh.aliases) == {"Osh", "Ош", "اوش"}
            assert not TrackingLocationReference.query.filter(
                db.func.lower(TrackingLocationReference.name_en) == "ash"
            ).first()

            duplicate = TrackingLocationReference(
                internal_key="KG-OSH",
                name_fa="duplicate",
                country_code="KG",
                location_type="other",
            )
            db.session.add(duplicate)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

            actor = ExpertUser(
                id=user_id,
                username="postgres-tracking-location",
                password_hash="unused",
                full_name="PostgreSQL Tracking Location",
                role="expert",
                is_active=True,
            )
            request = ShipmentRequest(
                id=request_id,
                contact_phone="09000000003",
                status="won",
                status_request_status="new",
                tracking_code="POSTGRES-TRACKING-LOCATION",
                assigned_to=user_id,
            )
            db.session.add_all([actor, request])
            db.session.commit()
            unit = add_unit(
                enable_tracking(request, actor.id),
                actor.id,
                unit_code="POSTGRES-UNIT",
                unit_type="truck",
            )
            base = datetime(2026, 7, 17, 6, 0, 0)
            known = add_update(
                unit,
                actor.id,
                status="in_transit",
                location_reference_id=osh.id,
                occurred_at=base,
            )
            add_update(
                unit,
                actor.id,
                status="delayed",
                occurred_at=base + timedelta(minutes=1),
            )
            free_text = add_update(
                unit,
                actor.id,
                status="at_checkpoint",
                location_text="Ash",
                occurred_at=base + timedelta(minutes=2),
            )
            db.session.commit()

            assert known.location_name_snapshot == osh.name_fa
            assert known.country_code_snapshot == "KG"
            assert free_text.location_reference_id is None
            assert build_internal_unit_tracking(request)["units"][0]["latest_location"] == "Ash"
            assert TrackingLocationReference.query.count() == 64
        finally:
            db.session.rollback()
            row = db.session.get(ShipmentRequest, request_id)
            if row:
                db.session.delete(row)
            row = db.session.get(ExpertUser, user_id)
            if row:
                db.session.delete(row)
            db.session.commit()
