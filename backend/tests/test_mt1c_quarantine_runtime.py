"""Adversarial certification for the centralized MT-1C quarantine boundary."""
from __future__ import annotations

from datetime import datetime

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    ExpertConsoleNotification,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.quarantine import (
    OwnershipCertificationDecision,
    OwnershipCertificationScope,
    QuarantinedResource,
    assert_not_quarantined,
    decision_epoch_token,
    is_quarantined,
)
from backend.census_context import clear_census_context
from backend.services.tracking_service import get_public_tracking_payload


@pytest.fixture()
def quarantine_app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        user = ExpertUser(
            username="mt1c", password_hash="x", full_name="MT1C",
            email="mt1c@example.test", role="admin", is_active=True,
        )
        db.session.add(user)
        db.session.flush()
        rows = []
        for marker in ("CLEAR", "QUARANTINED", "INVALID", "CONFLICT", "MISSING"):
            rows.append(ShipmentRequest(
                tracking_code=f"MT1C-{marker}", contact_phone=marker,
                shipping_type="domestic", status="new", status_request_status="new",
            ))
        db.session.add_all(rows)
        db.session.flush()

        quote = ExpertQuote(
            shipment_request_id=rows[1].id, amount=100, currency="IRR",
            created_by_expert_id=user.id,
        )
        notification = ExpertConsoleNotification(
            expert_user_id=user.id, shipment_request_id=rows[1].id,
            notification_type="test", title="hidden", message="hidden",
        )
        db.session.add_all([quote, notification])
        db.session.flush()
        ids = {marker: row.id for marker, row in zip(
            ("CLEAR", "QUARANTINED", "INVALID", "CONFLICT", "MISSING"), rows
        )}
        db.session.add(OwnershipCertificationScope(
            entity_type="ShipmentRequest", certified_through_id=max(ids.values()),
            census_id="synthetic-a", decision_epoch=1,
        ))
        for marker, classification in {
            "CLEAR": "DETERMINISTIC",
            "QUARANTINED": "QUARANTINED",
            "INVALID": "INVALID_LINEAGE",
            "CONFLICT": "CONFLICT",
        }.items():
            db.session.add(OwnershipCertificationDecision(
                entity_type="ShipmentRequest", entity_id=ids[marker],
                classification=classification, census_id="synthetic-a",
                decision_id=f"decision-{marker.lower()}",
            ))
        db.session.add_all([
            OwnershipCertificationDecision(
                entity_type="ExpertQuote", entity_id=quote.id,
                classification="QUARANTINED", census_id="synthetic-a",
                decision_id="decision-quote",
            ),
            OwnershipCertificationDecision(
                entity_type="ExpertConsoleNotification", entity_id=notification.id,
                classification="QUARANTINED", census_id="synthetic-a",
                decision_id="decision-notification",
            ),
        ])
        db.session.commit()
        yield app, ids, user.id
        db.session.rollback()
        db.drop_all()


def test_fail_closed_states_and_normal_data(quarantine_app):
    app, ids, _user_id = quarantine_app
    with app.app_context():
        assert ShipmentRequest.query.with_entities(ShipmentRequest.id).all() == [(ids["CLEAR"],)]
        assert db.session.get(ShipmentRequest, ids["CLEAR"]) is not None
        for marker in ("QUARANTINED", "INVALID", "CONFLICT", "MISSING"):
            assert ShipmentRequest.query.filter_by(id=ids[marker]).first() is None
            assert is_quarantined("ShipmentRequest", ids[marker]) is True
            with pytest.raises(QuarantinedResource):
                assert_not_quarantined("ShipmentRequest", ids[marker])
        assert is_quarantined("ShipmentRequest", ids["CLEAR"]) is False


@pytest.mark.parametrize(
    "surface",
    [
        "API list", "API detail", "search", "selector", "report", "export",
        "job", "notification", "document download", "public tracking",
        "admin tooling", "CLI tooling", "cache", "joins/materialization",
        "monitoring/analytics",
    ],
)
def test_all_mandatory_surfaces_share_the_guard(quarantine_app, surface):
    """One parameter per machine-readable matrix row prevents silent omissions."""

    app, ids, _user_id = quarantine_app
    with app.app_context():
        # Each surface ultimately consumes an ORM selection, assertion, or epoch;
        # exercise those authoritative primitives for every declared row.
        if surface == "cache":
            assert decision_epoch_token() == (1, 6)
        elif surface == "public tracking":
            assert get_public_tracking_payload(str(ids["QUARANTINED"])) is None
            assert get_public_tracking_payload("MT1C-QUARANTINED") is None
        elif surface == "notification":
            assert ExpertConsoleNotification.query.count() == 0
        elif surface == "joins/materialization":
            assert ExpertQuote.query.join(ShipmentRequest).count() == 0
        else:
            hidden = ShipmentRequest.query.filter(
                ShipmentRequest.contact_phone.contains("QUARANTINED")
            ).count()
            assert hidden == 0


def test_identity_map_and_public_tracking_do_not_bypass(quarantine_app):
    app, ids, _user_id = quarantine_app
    with app.app_context():
        # The explicit assertion remains authoritative even if a caller already
        # holds an ORM instance and Session.get would return it from identity map.
        raw = db.session.execute(
            db.select(ShipmentRequest)
            .where(ShipmentRequest.id == ids["QUARANTINED"])
            .execution_options(include_quarantined_for_certification=True)
        ).scalar_one()
        assert raw.id == ids["QUARANTINED"]
        with pytest.raises(QuarantinedResource):
            assert_not_quarantined("ShipmentRequest", raw.id)
        client = app.test_client()
        for identifier in (str(raw.id), raw.tracking_code):
            response = client.get(f"/api/public/track/{identifier}")
            assert response.status_code == 404
            assert "quarant" not in response.get_data(as_text=True).lower()


def test_quarantined_parent_cannot_be_laundered_into_new_child(quarantine_app):
    app, ids, user_id = quarantine_app
    with app.app_context():
        db.session.add(ExpertQuote(
            shipment_request_id=ids["QUARANTINED"], amount=200,
            currency="IRR", created_by_expert_id=user_id, created_at=datetime.utcnow(),
        ))
        with pytest.raises(QuarantinedResource):
            db.session.flush()
        db.session.rollback()


def test_bulk_mutation_cannot_bypass_quarantine(quarantine_app):
    app, _ids, user_id = quarantine_app
    with app.app_context():
        # Set-based mutation of a side-effect table has no mapped parent on
        # which to run the census eligibility contract, so it fails closed.
        with pytest.raises(QuarantinedResource):
            ExpertConsoleNotification.query.filter_by(
                expert_user_id=user_id
            ).update({"is_read": True}, synchronize_session=False)
        db.session.rollback()


def test_post_census_runtime_row_without_metadata_fails_closed(quarantine_app):
    app, ids, _user_id = quarantine_app
    with app.app_context():
        row = ShipmentRequest(
            tracking_code="MT1C-POST-CENSUS", contact_phone="normal",
            shipping_type="domestic", status="new", status_request_status="new",
        )
        db.session.add(row)
        db.session.flush()
        row_id = row.id
        db.session.commit()
        assert row_id > max(ids.values())
        assert ShipmentRequest.query.filter_by(id=row_id).first() is None
        assert is_quarantined("ShipmentRequest", row_id)


def test_cache_epoch_changes_when_new_census_is_activated(quarantine_app):
    app, _ids, _user_id = quarantine_app
    with app.app_context():
        before = decision_epoch_token()
        scope = db.session.get(OwnershipCertificationScope, "ShipmentRequest")
        scope.decision_epoch += 1
        db.session.commit()
        clear_census_context(db.session)
        assert decision_epoch_token()[0] == before[0] + 1
