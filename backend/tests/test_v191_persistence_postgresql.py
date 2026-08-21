"""Disposable PostgreSQL replay for the Forwarder 1.9.1 persistence revision."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from uuid import uuid4

from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
import pytest

from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade


BASELINE = "20260818_immutable_fx_provenance"
HEAD = "20260819_v191_acceptance_corrections"


def _url() -> str:
    value = os.environ.get("FORWARDER_V191_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit disposable v1.9.1 PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_v191_slice2_test_")
    return value


def _seed_v190(connection):
    now = datetime.now(timezone.utc)
    connection.execute(
        text(
            "INSERT INTO operational_organization "
            "(id, public_id, name, is_active, created_at) "
            "VALUES (9101, :public_id, 'v191 org', true, :now)"
        ),
        {"public_id": str(uuid4()), "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO expert_user "
            "(id, username, password_hash, full_name, role, is_active, "
            "can_handle_domestic, can_handle_international, "
            "sla_response_work_minutes, created_at) VALUES "
            "(9101, 'v191-pg-user', 'unused', 'v191 pg user', 'expert', true, "
            "true, true, 120, :now)"
        ),
        {"now": now},
    )
    connection.execute(
        text(
            "INSERT INTO customer "
            "(id, first_name, last_name, status, customer_type, created_at, updated_at) "
            "VALUES (9101, 'Canonical', 'Customer', 'active', 'customer', :now, :now)"
        ),
        {"now": now},
    )
    for request_id, customer_id, phone in (
        (9101, 9101, "09000001911"),
        (9102, None, "09000001912"),
    ):
        connection.execute(
            text(
                "INSERT INTO shipment_request "
                "(id, shipping_type, contact_phone, customer_id, created_at, "
                "ready_at, status_request_status, status) VALUES "
                "(:id, 'international', :phone, :customer_id, :now, :now, 'new', 'new')"
            ),
            {
                "id": request_id,
                "phone": phone,
                "customer_id": customer_id,
                "now": now,
            },
        )
    for quote_id, request_id in ((9101, 9101), (9102, 9102)):
        connection.execute(
            text(
                "INSERT INTO expert_quote "
                "(id, shipment_request_id, amount, currency, created_by_expert_id, "
                "created_at, customer_response, operational_organization_id) VALUES "
                "(:id, :request_id, 100, 'IRR', 9101, :now, 'accepted', 9101)"
            ),
            {"id": quote_id, "request_id": request_id, "now": now},
        )
    for shipment_id, request_id, quote_id in (
        (9101, 9101, 9101),
        (9102, 9102, 9102),
    ):
        connection.execute(
            text(
                "INSERT INTO operational_shipment "
                "(id, public_id, organization_id, shipment_request_id, accepted_quote_id, "
                "lifecycle_status, version, created_by_user_id, created_at, updated_at) "
                "VALUES (:id, :public_id, 9101, :request_id, :quote_id, "
                "'planned', 1, 9101, :now, :now)"
            ),
            {
                "id": shipment_id,
                "public_id": str(uuid4()),
                "request_id": request_id,
                "quote_id": quote_id,
                "now": now,
            },
        )
    connection.execute(
        text(
            "INSERT INTO country "
            "(id, name_en, name_fa, code, is_active, created_at) "
            "VALUES (9101, 'Iran v191', 'Iran v191', 'V19', true, :now)"
        ),
        {"now": now.replace(tzinfo=None)},
    )
    connection.execute(
        text(
            "INSERT INTO international_city "
            "(id, name_en, name_fa, country_id, city_type, is_active, created_at) "
            "VALUES (9101, 'City v191', 'City v191', 9101, 'city', true, :now)"
        ),
        {"now": now.replace(tzinfo=None)},
    )


def _direct_insert(connection, shipment_id: int):
    now = datetime.now(timezone.utc)
    connection.execute(
        text(
            "INSERT INTO operational_shipment "
            "(id, public_id, organization_id, source_type, customer_id, "
            "shipment_request_id, accepted_quote_id, lifecycle_status, version, "
            "created_by_user_id, created_at, updated_at) VALUES "
            "(:id, :public_id, 9101, 'direct', 9101, NULL, NULL, 'planned', 1, "
            "9101, :now, :now)"
        ),
        {"id": shipment_id, "public_id": str(uuid4()), "now": now},
    )


def test_v191_upgrade_constraints_backfill_and_guarded_downgrade_postgresql():
    url = _url()
    config = alembic_config(url)
    prepare_version_table_for_upgrade(url, config)
    command.upgrade(config, BASELINE)
    engine = create_engine(url)
    with engine.begin() as connection:
        _seed_v190(connection)

    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == HEAD
        )
        rows = connection.execute(
            text(
                "SELECT id, source_type, customer_id, shipment_request_id, accepted_quote_id "
                "FROM operational_shipment WHERE id IN (9101, 9102) ORDER BY id"
            )
        ).all()
        assert rows == [
            (9101, "accepted_quote", 9101, 9101, 9101),
            (9102, "accepted_quote", None, 9102, 9102),
        ]
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='shipment_request' AND column_name IN "
                    "('origin_country_id','origin_international_city_id',"
                    "'dest_country_id','dest_international_city_id')"
                )
            )
        }
        assert columns == {
            "origin_country_id",
            "origin_international_city_id",
            "dest_country_id",
            "dest_international_city_id",
        }

    with engine.begin() as connection:
        _direct_insert(connection, 9201)
        _direct_insert(connection, 9202)

    with pytest.raises((IntegrityError, DBAPIError)):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO operational_shipment "
                    "(id, public_id, organization_id, source_type, customer_id, "
                    "shipment_request_id, accepted_quote_id, lifecycle_status, version, "
                    "created_by_user_id, created_at, updated_at) SELECT "
                    "9203, :public_id, organization_id, 'direct', 999999, NULL, NULL, "
                    "lifecycle_status, version, created_by_user_id, created_at, updated_at "
                    "FROM operational_shipment WHERE id=9101"
                ),
                {"public_id": str(uuid4())},
            )

    with pytest.raises((IntegrityError, DBAPIError)):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO operational_shipment "
                    "(id, public_id, organization_id, source_type, customer_id, "
                    "shipment_request_id, accepted_quote_id, lifecycle_status, version, "
                    "created_by_user_id, created_at, updated_at) SELECT "
                    "9204, :public_id, organization_id, 'accepted_quote', customer_id, "
                    "NULL, NULL, lifecycle_status, version, created_by_user_id, created_at, updated_at "
                    "FROM operational_shipment WHERE id=9101"
                ),
                {"public_id": str(uuid4())},
            )

    with pytest.raises((IntegrityError, DBAPIError)):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO operational_shipment "
                    "(id, public_id, organization_id, source_type, customer_id, "
                    "shipment_request_id, accepted_quote_id, lifecycle_status, version, "
                    "created_by_user_id, created_at, updated_at) SELECT "
                    "9205, :public_id, organization_id, source_type, customer_id, "
                    "shipment_request_id, accepted_quote_id, lifecycle_status, version, "
                    "created_by_user_id, created_at, updated_at "
                    "FROM operational_shipment WHERE id=9101"
                ),
                {"public_id": str(uuid4())},
            )

    with pytest.raises((IntegrityError, DBAPIError)):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO operational_shipment "
                    "(id, public_id, organization_id, source_type, customer_id, "
                    "shipment_request_id, accepted_quote_id, lifecycle_status, version, "
                    "created_by_user_id, created_at, updated_at) SELECT "
                    "9301, :public_id, organization_id, 'direct', customer_id, "
                    "shipment_request_id, NULL, lifecycle_status, version, "
                    "created_by_user_id, created_at, updated_at "
                    "FROM operational_shipment WHERE id=9101"
                ),
                {"public_id": str(uuid4())},
            )

    with pytest.raises(RuntimeError, match="direct OperationalShipment"):
        command.downgrade(config, BASELINE)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM operational_shipment WHERE id IN (9201,9202)")
        )
        connection.execute(
            text(
                "UPDATE shipment_request SET origin_country_id=9101, "
                "origin_international_city_id=9101 WHERE id=9101"
            )
        )
    with pytest.raises(RuntimeError, match="location data would be lost"):
        command.downgrade(config, BASELINE)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE shipment_request SET origin_country_id=NULL, "
                "origin_international_city_id=NULL WHERE id=9101"
            )
        )
    command.downgrade(config, BASELINE)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == BASELINE
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_name='operational_shipment' AND column_name='source_type'"
                )
            ).scalar_one()
            == 0
        )
    engine.dispose()
