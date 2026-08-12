"""Legacy MT-1C PostgreSQL smoke test using the current census contract."""
from __future__ import annotations

from hashlib import sha256
import os

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest
from backend.ownership_census import (
    CensusDecisionInput,
    CensusPublication,
    internal_publisher_authority,
    publish_census,
)
from backend.resource_identity import scalar_identity
from backend.services.tracking_service import get_public_tracking_payload


FP = sha256(b"mt1c-legacy-postgresql-smoke").hexdigest()
TOKEN = "mt1c-legacy-postgresql-publisher"


def _url() -> str:
    url = os.getenv("MT1C_DISPOSABLE_DATABASE_URL", "")
    if not url:
        pytest.skip("explicit disposable MT-1C PostgreSQL URL not provided")
    assert "127.0.0.1" in url or "localhost" in url
    assert "/forwarder_mt1c_cert_" in url
    return url


def test_mt1c_postgresql_runtime_and_rollback(monkeypatch):
    url = _url()
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_TOKEN", TOKEN)
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_DATABASE_ROLES", "postgres")
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": url,
        "SECRET_KEY": "disposable-mt1c-only",
    }, skip_startup=True)
    with app.app_context():
        assert db.session.execute(text("SHOW server_version")).scalar_one().startswith("18.")
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
            db.session.add_all([clear, denied])
            db.session.flush()
            clear_id = clear.id
            denied_id = denied.id
            denied_code = denied.tracking_code
            db.session.commit()
            identities = [
                scalar_identity("ShipmentRequest", clear_id),
                scalar_identity("ShipmentRequest", denied_id),
            ]
            publication = CensusPublication(
                "mt1c-legacy-current", "mt1d-v1", 1, None, FP, "pytest-publisher",
                (
                    CensusDecisionInput(identities[0], "DETERMINISTIC", "CLEAR", FP),
                    CensusDecisionInput(identities[1], "CONFLICT", "QUARANTINED", FP),
                ),
                {"ShipmentRequest": 2}, {"ShipmentRequest": FP},
            )
            with Session(db.engine) as publisher:
                publish_census(
                    publisher, publication,
                    authority=internal_publisher_authority(TOKEN),
                )

            # A new reader pins the publication; no certification metadata is
            # mutated inside that reader's unit of work.
            db.session.remove()
            assert ShipmentRequest.query.with_entities(ShipmentRequest.id).all() == [(clear_id,)]
            assert get_public_tracking_payload(str(denied_id)) is None
            assert get_public_tracking_payload(denied_code) is None

            transient = ShipmentRequest(
                tracking_code="PG-MT1C-ROLLBACK", contact_phone="rollback",
                shipping_type="domestic", status="new", status_request_status="new",
            )
            db.session.add(transient)
            db.session.flush()
            transient_id = transient.id
            db.session.rollback()
            with Session(db.engine) as reader:
                assert reader.execute(
                    select(ShipmentRequest.id)
                    .where(ShipmentRequest.id == transient_id)
                    .execution_options(include_quarantined_for_certification=True)
                ).first() is None
        finally:
            db.session.rollback()
            db.drop_all()
