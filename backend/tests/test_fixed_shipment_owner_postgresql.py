"""Owned PostgreSQL 18 proof for ADR-047 fixed Shipment ownership."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from alembic import command
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, revision_status
from backend.models import Customer, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
)
from backend.services.assigned_work_authorization import (
    authorize_document_management,
    authorize_work_action,
)
from backend.services.control_tower_scope import governed_summary_scope
from backend.services import operational_service


HEAD = "20260926_fixed_shipment_responsible_expert"
REPOSITORY_HEAD = "20260928_operational_workspace_phase2"
PREVIOUS = "20260925_quote_communication"


def _url() -> str:
    url = os.environ.get("FIXED_SHIPMENT_OWNER_DISPOSABLE_POSTGRES_URL")
    if not url:
        pytest.skip("owned disposable fixed-owner PostgreSQL URL required")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.database == "forwarder_fixed_shipment_owner_build"
    return url


def _reset(url: str, revision: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(url), revision)
    engine.dispose()


def _organization(connection, label: str) -> int:
    return connection.execute(
        text(
            "INSERT INTO operational_organization "
            "(public_id, name, is_active, created_at) "
            "VALUES (:public_id, :name, true, now()) RETURNING id"
        ),
        {"public_id": str(uuid4()), "name": label},
    ).scalar_one()


def _expert(connection, organization_id: int, label: str, *, authority="EXPERT") -> int:
    user_id = connection.execute(
        text(
            "INSERT INTO expert_user "
            "(username, password_hash, full_name, role, authority, is_active, "
            "can_handle_domestic, can_handle_international, "
            "sla_response_work_minutes, created_at) "
            "VALUES (:username, 'not-a-credential', :name, 'expert', :authority, "
            "true, true, true, 120, now()) RETURNING id"
        ),
        {
            "username": f"{label}-{uuid4().hex[:8]}",
            "name": label,
            "authority": authority,
        },
    ).scalar_one()
    connection.execute(
        text(
            "INSERT INTO operational_membership "
            "(organization_id, user_id, is_active, permissions, created_at) "
            "VALUES (:organization_id, :user_id, true, CAST('[]' AS json), now())"
        ),
        {"organization_id": organization_id, "user_id": user_id},
    )
    return int(user_id)


def _customer(connection, organization_id: int, label: str) -> int:
    return connection.execute(
        text(
            "INSERT INTO customer "
            "(operational_organization_id, ownership_scope, first_name, status, "
            "created_at, updated_at) "
            "VALUES (:organization_id, 'TENANT', :name, 'active', now(), now()) "
            "RETURNING id"
        ),
        {"organization_id": organization_id, "name": label},
    ).scalar_one()


def _request(connection, organization_id: int, customer_id: int, assignee_id: int, label: str) -> int:
    return connection.execute(
        text(
            "INSERT INTO shipment_request "
            "(operational_organization_id, ownership_scope, tracking_code, "
            "shipping_type, contact_phone, customer_id, created_at, ready_at, "
            "status_request_status, status, assigned_to) "
            "VALUES (:organization_id, 'TENANT', :tracking_code, 'domestic', "
            ":phone, :customer_id, now(), now(), 'new', 'waiting_for_customer', "
            ":assignee_id) RETURNING id"
        ),
        {
            "organization_id": organization_id,
            "tracking_code": f"A47-{label[:12]}-{uuid4().hex[:8]}",
            "phone": f"09{int(uuid4().hex[:9], 16) % 10_000_000_000:010d}",
            "customer_id": customer_id,
            "assignee_id": assignee_id,
        },
    ).scalar_one()


def _quote(
    connection,
    organization_id: int,
    request_id: int,
    issuer_id: int,
    *,
    response: str = "accepted",
) -> int:
    return connection.execute(
        text(
            "INSERT INTO expert_quote "
            "(public_id, shipment_request_id, operational_organization_id, "
            "amount, currency, created_by_expert_id, created_at, "
            "customer_response, responded_at) "
            "VALUES (:public_id, :request_id, :organization_id, 100, 'IRR', "
            ":issuer_id, now(), :response, now()) RETURNING id"
        ),
        {
            "public_id": str(uuid4()),
            "request_id": request_id,
            "organization_id": organization_id,
            "issuer_id": issuer_id,
            "response": response,
        },
    ).scalar_one()


def _accepted_shipment(
    connection,
    organization_id: int,
    request_id: int,
    quote_id: int,
    creator_id: int,
    owner_id: int | None,
) -> int:
    return connection.execute(
        text(
            "INSERT INTO operational_shipment "
            "(public_id, organization_id, source_type, shipment_request_id, "
            "accepted_quote_id, lifecycle_status, version, created_by_user_id, "
            "primary_responsible_expert_id, created_at, updated_at) "
            "VALUES (:public_id, :organization_id, 'accepted_quote', :request_id, "
            ":quote_id, 'planned', 1, :creator_id, :owner_id, now(), now()) "
            "RETURNING id"
        ),
        {
            "public_id": str(uuid4()),
            "organization_id": organization_id,
            "request_id": request_id,
            "quote_id": quote_id,
            "creator_id": creator_id,
            "owner_id": owner_id,
        },
    ).scalar_one()


def _direct_shipment(connection, organization_id: int, customer_id: int, owner_id: int) -> int:
    return connection.execute(
        text(
            "INSERT INTO operational_shipment "
            "(public_id, organization_id, source_type, customer_id, "
            "lifecycle_status, version, created_by_user_id, "
            "primary_responsible_expert_id, created_at, updated_at) "
            "VALUES (:public_id, :organization_id, 'direct', :customer_id, "
            "'planned', 1, :owner_id, :owner_id, now(), now()) RETURNING id"
        ),
        {
            "public_id": str(uuid4()),
            "organization_id": organization_id,
            "customer_id": customer_id,
            "owner_id": owner_id,
        },
    ).scalar_one()


def test_fixed_owner_migration_reconciles_only_exact_quote_lineage_and_is_reversible():
    url = _url()
    _reset(url, PREVIOUS)
    config = alembic_config(url)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS

    engine = create_engine(url)
    with engine.begin() as connection:
        org = _organization(connection, "ADR-047 historical")
        e1 = _expert(connection, org, "historical-e1")
        e2 = _expert(connection, org, "historical-e2")
        customer = _customer(connection, org, "Historical Customer")

        request_h1 = _request(connection, org, customer, e2, "h1-reassigned")
        quote_h1 = _quote(connection, org, request_h1, e1)
        h1 = _accepted_shipment(connection, org, request_h1, quote_h1, e2, None)

        h3 = _direct_shipment(connection, org, customer, e1)

        request_h4 = _request(connection, org, customer, e2, "h4-correct")
        quote_h4 = _quote(connection, org, request_h4, e1)
        h4 = _accepted_shipment(connection, org, request_h4, quote_h4, e2, e1)

    command.upgrade(config, HEAD)
    assert revision_status(url).current == (HEAD,)
    columns = {
        column["name"]: column
        for column in inspect(engine).get_columns("operational_shipment")
    }
    assert columns["primary_responsible_expert_id"]["nullable"] is False
    with engine.begin() as connection:
        owners = dict(
            connection.execute(
                text(
                    "SELECT id, primary_responsible_expert_id "
                    "FROM operational_shipment WHERE id IN (:h1, :h3, :h4)"
                ),
                {"h1": h1, "h3": h3, "h4": h4},
            ).all()
        )
        assert owners == {h1: e1, h3: e1, h4: e1}
        connection.execute(
            text(
                "UPDATE operational_shipment SET lifecycle_status='in_progress' "
                "WHERE id=:shipment_id"
            ),
            {"shipment_id": h1},
        )
    with pytest.raises(IntegrityError, match="responsible Expert is immutable"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE operational_shipment "
                    "SET primary_responsible_expert_id=:owner_id WHERE id=:shipment_id"
                ),
                {"owner_id": e2, "shipment_id": h1},
            )

    command.downgrade(config, PREVIOUS)
    assert revision_status(url).current == (PREVIOUS,)
    assert {
        column["name"]: column
        for column in inspect(engine).get_columns("operational_shipment")
    }["primary_responsible_expert_id"]["nullable"] is True
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT primary_responsible_expert_id FROM operational_shipment "
                "WHERE id=:shipment_id"
            ),
            {"shipment_id": h1},
        ).scalar_one() == e1
    engine.dispose()


@pytest.mark.parametrize(
    ("scenario", "reason"),
    [
        ("missing_accepted_lineage", "CONFLICTING_ACCEPTED_QUOTE_LINEAGE"),
        ("persisted_conflict", "PERSISTED_OWNER_CONFLICT"),
    ],
)
def test_fixed_owner_migration_refuses_ambiguous_or_conflicting_history(scenario, reason):
    url = _url()
    _reset(url, PREVIOUS)
    config = alembic_config(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        org = _organization(connection, f"ADR-047 {scenario}")
        e1 = _expert(connection, org, f"{scenario}-e1")
        e2 = _expert(connection, org, f"{scenario}-e2")
        customer = _customer(connection, org, f"{scenario} Customer")
        request_id = _request(connection, org, customer, e2, scenario)
        quote_id = _quote(
            connection,
            org,
            request_id,
            e1,
            response="declined" if scenario == "missing_accepted_lineage" else "accepted",
        )
        owner = e2 if scenario == "persisted_conflict" else None
        shipment_id = _accepted_shipment(
            connection, org, request_id, quote_id, e2, owner
        )

    with pytest.raises(RuntimeError, match=reason):
        command.upgrade(config, HEAD)
    assert revision_status(url).current == (PREVIOUS,)
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT primary_responsible_expert_id FROM operational_shipment "
                "WHERE id=:shipment_id"
            ),
            {"shipment_id": shipment_id},
        ).scalar_one_or_none() == owner
    engine.dispose()


def test_quote_creation_racing_request_reassignment_keeps_quote_issuer_owner():
    url = _url()
    _reset(url, HEAD)
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": url,
            "SECRET_KEY": "owned-fixed-owner-proof",
        },
        skip_startup=True,
    )
    with app.app_context():
        org = OperationalOrganization(name="ADR-047 race")
        e1 = ExpertUser(
            username=f"adr047-e1-{uuid4().hex[:8]}", password_hash="x",
            full_name="ADR-047 E1", authority="EXPERT", role="expert", is_active=True,
        )
        e2 = ExpertUser(
            username=f"adr047-e2-{uuid4().hex[:8]}", password_hash="x",
            full_name="ADR-047 E2", authority="EXPERT", role="expert", is_active=True,
        )
        admin = ExpertUser(
            username=f"adr047-admin-{uuid4().hex[:8]}", password_hash="x",
            full_name="ADR-047 Admin", authority="ORGANIZATION_ADMIN", role="admin",
            is_active=True,
        )
        customer = Customer(
            first_name="ADR-047", last_name="Customer", status="active",
            ownership_scope="TENANT",
        )
        origin = Province(name_fa="مبدأ ADR-047", code=f"A{uuid4().hex[:7]}")
        destination = Province(name_fa="مقصد ADR-047", code=f"B{uuid4().hex[:7]}")
        db.session.add_all([org, e1, e2, admin, origin, destination])
        db.session.flush()
        customer.operational_organization_id = org.id
        db.session.add(customer)
        db.session.flush()
        db.session.add_all([
            OperationalMembership(
                organization_id=org.id, user_id=e1.id, is_active=True,
                permissions=["operational_shipment.read"],
            ),
            OperationalMembership(
                organization_id=org.id, user_id=e2.id, is_active=True,
                permissions=["operational_shipment.read"],
            ),
            OperationalMembership(
                organization_id=org.id, user_id=admin.id, is_active=True,
                permissions=["request.read", "operational_shipment.read",
                             "operational_shipment.create"],
            ),
        ])
        request_row = ShipmentRequest(
            operational_organization_id=org.id, ownership_scope="TENANT",
            assigned_to=e1.id, customer_id=customer.id,
            contact_phone="09120000470", shipping_type="domestic",
            status="waiting_for_customer", status_request_status="new",
        )
        db.session.add(request_row)
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            operational_organization_id=org.id,
            amount=4700,
            currency="EUR",
            created_by_expert_id=e1.id,
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
        )
        db.session.add(quote)
        db.session.commit()
        ids = {
            "org": org.id,
            "e1": e1.id,
            "e2": e2.id,
            "admin": admin.id,
            "request": request_row.id,
            "quote": quote.id,
            "origin": origin.id,
            "destination": destination.id,
        }

    barrier = Barrier(2)

    def reassign_request():
        engine = create_engine(url)
        with engine.begin() as connection:
            barrier.wait(timeout=10)
            connection.execute(
                text("UPDATE shipment_request SET assigned_to=:e2 WHERE id=:request_id"),
                {"e2": ids["e2"], "request_id": ids["request"]},
            )
            connection.execute(text("SELECT pg_sleep(0.2)"))
        engine.dispose()

    def create_shipment():
        with app.app_context():
            barrier.wait(timeout=10)
            departure = datetime.now(timezone.utc) + timedelta(hours=1)
            shipment, created = operational_service.create_from_accepted_quote(
                {
                    "accepted_quote_id": ids["quote"],
                    "origin": {"source_type": "province", "source_id": ids["origin"]},
                    "destination": {
                        "source_type": "province",
                        "source_id": ids["destination"],
                    },
                    "transport_mode": "road",
                    "planned_departure": departure.isoformat(),
                    "planned_arrival": (departure + timedelta(hours=2)).isoformat(),
                },
                {"id": ids["admin"], "role": "admin"},
                "adr047-race",
            )
            result = (shipment.id, created)
            db.session.remove()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        reassignment = pool.submit(reassign_request)
        creation = pool.submit(create_shipment)
        shipment_id, created = creation.result(timeout=20)
        reassignment.result(timeout=20)
    assert created is True

    with app.app_context():
        request_row = db.session.get(ShipmentRequest, ids["request"])
        shipment = db.session.get(OperationalShipment, shipment_id)
        assert request_row.assigned_to == ids["e2"]
        assert shipment.primary_responsible_expert_id == ids["e1"]
        assert authorize_work_action({"id": ids["e1"]}, shipment, "shipment.read").allowed
        assert not authorize_work_action({"id": ids["e2"]}, shipment, "shipment.read").allowed
        assert authorize_document_management({"id": ids["e1"]}, shipment).allowed
        assert not authorize_document_management({"id": ids["e2"]}, shipment).allowed
        assert {row.shipment_id for row in governed_summary_scope({"id": ids["e1"]})} == {
            shipment.id
        }
        assert governed_summary_scope({"id": ids["e2"]}) == ()

        owner = db.session.get(ExpertUser, ids["e1"])
        owner.is_active = False
        db.session.commit()
        assert db.session.get(
            OperationalShipment, shipment.id
        ).primary_responsible_expert_id == ids["e1"]
        assert not authorize_work_action(
            {"id": ids["e1"]}, shipment, "shipment.read"
        ).allowed
        assert authorize_work_action(
            {"id": ids["admin"]}, shipment, "shipment.read"
        ).allowed
        assert not authorize_document_management({"id": ids["e1"]}, shipment).allowed
        db.session.remove()
