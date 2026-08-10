"""Focused contracts for the Forwarder 1.9.1 persistence foundation."""
from __future__ import annotations

import importlib

import pytest
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import (
    Country,
    Customer,
    ExpertQuote,
    ExpertUser,
    InternationalCity,
    ShipmentRequest,
)
from backend.operational_models import OperationalOrganization, OperationalShipment


MIGRATION = "backend.migrations.versions.20260819_v191_acceptance_corrections"


@pytest.fixture()
def persistence_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "v191-persistence-test",
        }
    )
    with app.app_context():
        customer = Customer(
            first_name="Canonical", last_name="Customer", status="active"
        )
        user = ExpertUser(
            username="v191-persistence-user",
            password_hash="unused",
            full_name="Persistence User",
            role="expert",
            is_active=True,
        )
        organization = OperationalOrganization(name="v1.9.1 Persistence Org")
        country = Country(name_en="Iran", name_fa="ایران", code="IR")
        db.session.add_all([customer, user, organization, country])
        db.session.flush()
        city = InternationalCity(
            name_en="Tehran",
            name_fa="تهران",
            country_id=country.id,
            city_type="city",
        )
        request_row = ShipmentRequest(
            contact_phone="09000000191",
            customer_id=customer.id,
            shipping_type="international",
            origin_country_id=country.id,
        )
        db.session.add_all([city, request_row])
        db.session.flush()
        request_row.origin_international_city_id = city.id
        request_row.dest_country_id = country.id
        request_row.dest_international_city_id = city.id
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            amount=100,
            currency="IRR",
            created_by_expert_id=user.id,
            customer_response="accepted",
            operational_organization_id=organization.id,
        )
        db.session.add(quote)
        db.session.commit()
        app.config["v191_ids"] = {
            "customer": customer.id,
            "user": user.id,
            "organization": organization.id,
            "request": request_row.id,
            "quote": quote.id,
            "country": country.id,
            "city": city.id,
        }
    return app


def _shipment(app, **overrides):
    ids = app.config["v191_ids"]
    values = {
        "organization_id": ids["organization"],
        "source_type": "accepted_quote",
        "customer_id": ids["customer"],
        "shipment_request_id": ids["request"],
        "accepted_quote_id": ids["quote"],
        "lifecycle_status": "planned",
        "created_by_user_id": ids["user"],
    }
    values.update(overrides)
    return OperationalShipment(**values)


def _assert_rejected(app, **overrides):
    with app.app_context():
        db.session.add(_shipment(app, **overrides))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_valid_accepted_quote_and_direct_states_and_customer_relationship(
    persistence_app,
):
    with persistence_app.app_context():
        accepted = _shipment(persistence_app)
        direct = _shipment(
            persistence_app,
            source_type="direct",
            shipment_request_id=None,
            accepted_quote_id=None,
        )
        db.session.add_all([accepted, direct])
        db.session.commit()

        assert accepted.customer.id == persistence_app.config["v191_ids"]["customer"]
        assert direct.customer.id == persistence_app.config["v191_ids"]["customer"]
        assert direct.shipment_request_id is None
        assert direct.accepted_quote_id is None


def test_legacy_accepted_quote_without_customer_remains_persistable(persistence_app):
    with persistence_app.app_context():
        row = _shipment(persistence_app, customer_id=None)
        db.session.add(row)
        db.session.commit()
        assert row.source_type == "accepted_quote"
        assert row.customer_id is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_type": "accepted_quote", "shipment_request_id": None},
        {"source_type": "accepted_quote", "accepted_quote_id": None},
        {"source_type": "direct", "shipment_request_id": "request"},
        {"source_type": "direct", "accepted_quote_id": "quote"},
        {
            "source_type": "direct",
            "shipment_request_id": "request",
            "accepted_quote_id": "quote",
        },
        {
            "source_type": "direct",
            "customer_id": None,
            "shipment_request_id": None,
            "accepted_quote_id": None,
        },
        {"source_type": "unknown"},
    ],
)
def test_source_shape_constraint_rejects_invalid_combinations(
    persistence_app, overrides
):
    ids = persistence_app.config["v191_ids"]
    normalized = {
        key: ids[value] if value in {"request", "quote"} else value
        for key, value in overrides.items()
    }
    _assert_rejected(persistence_app, **normalized)


def test_accepted_quote_remains_unique_while_direct_null_quotes_repeat(persistence_app):
    with persistence_app.app_context():
        db.session.add(_shipment(persistence_app))
        db.session.commit()
        db.session.add(_shipment(persistence_app))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add_all(
            [
                _shipment(
                    persistence_app,
                    source_type="direct",
                    shipment_request_id=None,
                    accepted_quote_id=None,
                ),
                _shipment(
                    persistence_app,
                    source_type="direct",
                    shipment_request_id=None,
                    accepted_quote_id=None,
                ),
            ]
        )
        db.session.commit()
        assert OperationalShipment.query.filter_by(source_type="direct").count() == 2


def test_canonical_international_location_relationships(persistence_app):
    ids = persistence_app.config["v191_ids"]
    with persistence_app.app_context():
        request_row = db.session.get(ShipmentRequest, ids["request"])
        assert request_row.origin_country_ref.id == ids["country"]
        assert request_row.origin_international_city_ref.id == ids["city"]
        assert request_row.dest_country_ref.id == ids["country"]
        assert request_row.dest_international_city_ref.id == ids["city"]
        assert request_row.origin_country is None
        assert request_row.origin_city_international is None


def test_migration_identity_shape_backfill_and_downgrade_contract_are_frozen():
    migration = importlib.import_module(MIGRATION)
    assert migration.revision == "20260819_v191_acceptance_corrections"
    assert migration.down_revision == "20260818_immutable_fx_provenance"
    assert "source_type = 'accepted_quote'" in migration.SOURCE_SHAPE
    assert "source_type = 'direct'" in migration.SOURCE_SHAPE
    assert "customer_id IS NOT NULL" in migration.SOURCE_SHAPE
