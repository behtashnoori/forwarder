"""MT-1C certification against an explicitly disposable PostgreSQL 18 DB."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest
from backend.quarantine import (
    OwnershipCertificationDecision,
    OwnershipCertificationScope,
)
from backend.services.tracking_service import get_public_tracking_payload


def test_mt1c_postgresql_runtime_and_rollback():
    url = os.getenv("MT1C_DISPOSABLE_DATABASE_URL", "")
    if not url:
        pytest.skip("explicit disposable MT-1C PostgreSQL URL not provided")
    assert "127.0.0.1" in url or "localhost" in url
    assert "/forwarder_mt1c_cert_" in url

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": url,
        "SECRET_KEY": "disposable-mt1c-only",
    }, skip_startup=True)
    with app.app_context():
        version = db.session.execute(text("SHOW server_version")).scalar_one()
        assert version.startswith("18.")
        db.drop_all()
        db.create_all()
        try:
            clear = ShipmentRequest(
                tracking_code="PG-MT1C-CLEAR", contact_phone="clear",
                shipping_type="domestic", status="new", status_request_status="new",
            )
            denied = ShipmentRequest(
                tracking_code="PG-MT1C-DENIED", contact_phone="denied",
                shipping_type="domestic", status="new", status_request_status="new",
            )
            missing = ShipmentRequest(
                tracking_code="PG-MT1C-MISSING", contact_phone="missing",
                shipping_type="domestic", status="new", status_request_status="new",
            )
            db.session.add_all([clear, denied, missing])
            db.session.flush()
            clear_id, denied_id, missing_id = clear.id, denied.id, missing.id
            denied_code = denied.tracking_code
            db.session.add(OwnershipCertificationScope(
                entity_type="ShipmentRequest", certified_through_id=missing_id,
                census_id="postgres-synthetic", decision_epoch=1,
            ))
            db.session.add_all([
                OwnershipCertificationDecision(
                    entity_type="ShipmentRequest", entity_id=clear_id,
                    classification="DETERMINISTIC", census_id="postgres-synthetic",
                    decision_id="pg-clear",
                ),
                OwnershipCertificationDecision(
                    entity_type="ShipmentRequest", entity_id=denied_id,
                    classification="INVALID_LINEAGE", census_id="postgres-synthetic",
                    decision_id="pg-invalid",
                ),
            ])
            db.session.commit()

            assert ShipmentRequest.query.count() == 1
            assert ShipmentRequest.query.one().id == clear_id
            assert get_public_tracking_payload(str(denied_id)) is None
            assert get_public_tracking_payload(denied_code) is None
            assert ShipmentRequest.query.filter_by(id=missing_id).first() is None

            # Prove rollback/cleanup semantics on the same PostgreSQL-backed flow.
            transient = ShipmentRequest(
                tracking_code="PG-MT1C-ROLLBACK", contact_phone="rollback",
                shipping_type="domestic", status="new", status_request_status="new",
            )
            db.session.add(transient)
            db.session.flush()
            transient_id = transient.id
            db.session.rollback()
            raw_count = db.session.execute(
                text("SELECT count(*) FROM shipment_request WHERE id=:id"),
                {"id": transient_id},
            ).scalar_one()
            assert raw_count == 0
        finally:
            db.session.rollback()
            db.drop_all()
