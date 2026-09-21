"""Owned PostgreSQL migration, persistence, and concurrency proof for Quote communication."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
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
from backend.models import (
    CustomerGamification,
    ExpertConsoleLog,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.customer_gamification_service import record_quote_response
from backend.services.quote_service import create_quote_for_request


HEAD = "20260925_quote_communication"
REPOSITORY_HEAD = "20260926_fixed_shipment_responsible_expert"
PREVIOUS = "20260924_request_cargo_items"


def _url() -> str:
    url = os.environ.get("QUOTE_COMMUNICATION_DISPOSABLE_POSTGRES_URL")
    if not url:
        pytest.skip("owned disposable Quote communication PostgreSQL URL required")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.database == "forwarder_quote_communication_build"
    return url


def _reset(url: str, revision: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(url), revision)
    engine.dispose()


def _seed_current(app, suffix: str, *, expired: bool = False) -> dict[str, object]:
    with app.app_context():
        organization = OperationalOrganization(
            public_id=str(uuid4()), name=f"Quote proof {suffix}", is_active=True
        )
        expert = ExpertUser(
            username=f"quote_proof_{suffix}",
            password_hash="not-a-login-credential",
            full_name=f"Quote Expert {suffix}",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        customer = CustomerGamification(
            email=f"quote-proof-{suffix}@example.invalid",
            phone=f"0913{int(suffix[-6:], 16) % 10_000_000:07d}",
        )
        db.session.add_all([organization, expert, customer])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=organization.id,
                user_id=expert.id,
                is_active=True,
                permissions=[],
            )
        )
        request_row = ShipmentRequest(
            operational_organization_id=organization.id,
            ownership_scope="TENANT",
            tracking_code=f"QC-{suffix}",
            shipping_type="domestic",
            contact_phone=customer.phone,
            status_request_status="new",
            status="waiting_for_customer",
            assigned_to=expert.id,
            gamification_customer_id=customer.id,
            created_at=datetime.utcnow(),
            ready_at=datetime.utcnow(),
        )
        db.session.add(request_row)
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            operational_organization_id=organization.id,
            amount=1_250_000,
            currency="EUR",
            note="owned PostgreSQL proof",
            valid_until=(date.today() - timedelta(days=1)) if expired else (date.today() + timedelta(days=30)),
            created_by_expert_id=expert.id,
            created_at=datetime.utcnow(),
        )
        db.session.add(quote)
        db.session.commit()
        result = {
            "request_id": request_row.id,
            "tracking_code": request_row.tracking_code,
            "customer_id": customer.id,
            "quote_id": quote.id,
            "quote_public_id": quote.public_id,
            "expert_id": expert.id,
        }
        db.session.remove()
        return result


def _respond(app, barrier: Barrier, seed: dict[str, object], response: str, message: str | None = None):
    with app.app_context():
        barrier.wait(timeout=10)
        result = record_quote_response(
            str(seed["tracking_code"]),
            response,
            message=message,
            customer_id=seed["customer_id"],
            quote_public_id=str(seed["quote_public_id"]),
        )
        db.session.remove()
        return result


def _race_responses(app, seed, first, second):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_respond, app, barrier, seed, first[0], first[1]),
            pool.submit(_respond, app, barrier, seed, second[0], second[1]),
        ]
        return [future.result(timeout=20) for future in futures]


def test_quote_communication_owned_postgresql_migration_lifecycle():
    url = _url()
    _reset(url, PREVIOUS)
    config = alembic_config(url)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS
    assert revision_status(url).current == (PREVIOUS,)

    engine = create_engine(url)
    with engine.begin() as connection:
        organization_id = connection.execute(text("""
            INSERT INTO operational_organization (public_id, name, is_active, created_at)
            VALUES (:public_id, 'Historical Quote Org', true, now()) RETURNING id
        """), {"public_id": str(uuid4())}).scalar_one()
        customer_id = connection.execute(text("""
            INSERT INTO customer_gamification
                (email, phone, is_email_verified, created_at, total_requests,
                 completed_requests, loyalty_points, customer_level)
            VALUES ('historical-quote@example.invalid', '09120000999', false, now(), 0, 0, 0, 'bronze')
            RETURNING id
        """)).scalar_one()
        expert_id = connection.execute(text("""
            INSERT INTO expert_user
                (username, password_hash, full_name, role, authority, is_active,
                 can_handle_domestic, can_handle_international,
                 sla_response_work_minutes, created_at)
            VALUES ('historical_quote_expert', 'not-a-credential', 'Historical Expert',
                    'expert', 'EXPERT', true, true, true, 120, now())
            RETURNING id
        """)).scalar_one()
        request_id = connection.execute(text("""
            INSERT INTO shipment_request
                (operational_organization_id, ownership_scope, tracking_code,
                 shipping_type, contact_phone, created_at, ready_at,
                 status_request_status, status, assigned_to, gamification_customer_id)
            VALUES (:org, 'TENANT', 'QC-HISTORICAL', 'domestic', '09120000999',
                    now(), now(), 'new', 'waiting_for_customer', :expert, :customer)
            RETURNING id
        """), {"org": organization_id, "expert": expert_id, "customer": customer_id}).scalar_one()
        quote_id = connection.execute(text("""
            INSERT INTO expert_quote
                (shipment_request_id, operational_organization_id, amount, currency,
                 note, valid_until, created_by_expert_id, created_at,
                 customer_response, responded_at)
            VALUES (:request, :org, 975000, 'EUR', 'historical commercial evidence',
                    CURRENT_DATE + 30, :expert, now(), 'accepted', now())
            RETURNING id
        """), {"request": request_id, "org": organization_id, "expert": expert_id}).scalar_one()
        before = connection.execute(text("""
            SELECT amount, currency, note, customer_response, responded_at
            FROM expert_quote WHERE id=:id
        """), {"id": quote_id}).one()

    command.upgrade(config, HEAD)
    assert revision_status(url).current == (HEAD,)
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("expert_quote")}
    assert columns["public_id"]["nullable"] is False
    assert columns["customer_response_message"]["type"].length == 500
    assert {item["name"] for item in inspector.get_unique_constraints("expert_quote")} >= {
        "uq_expert_quote_public_id"
    }
    assert {item["name"] for item in inspector.get_check_constraints("expert_quote")} >= {
        "ck_expert_quote_customer_response",
        "ck_expert_quote_response_message",
    }
    assert {item["name"] for item in inspector.get_indexes("expert_quote")} >= {
        "ix_expert_quote_responded_by_customer_id"
    }
    assert any(
        item["name"] == "fk_expert_quote_responded_by_customer"
        and item["options"].get("ondelete") == "SET NULL"
        for item in inspector.get_foreign_keys("expert_quote")
    )

    with engine.connect() as connection:
        after = connection.execute(text("""
            SELECT amount, currency, note, customer_response, responded_at
            FROM expert_quote WHERE id=:id
        """), {"id": quote_id}).one()
        public_id = connection.execute(
            text("SELECT public_id FROM expert_quote WHERE id=:id"), {"id": quote_id}
        ).scalar_one()
        assert after == before
        assert len(public_id) == 36

    invalid = """
        UPDATE expert_quote
        SET customer_response=:response, customer_response_message=:message
        WHERE id=:id
    """
    for response, message in [("accepted", "forbidden"), ("discussion", None), ("unknown", None)]:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(invalid), {"response": response, "message": message, "id": quote_id})

    # An evidence-free downgrade is reversible and preserves legacy commercial evidence.
    command.downgrade(config, PREVIOUS)
    with engine.connect() as connection:
        assert connection.execute(text("""
            SELECT amount, currency, note, customer_response, responded_at
            FROM expert_quote WHERE id=:id
        """), {"id": quote_id}).one() == before
    command.upgrade(config, HEAD)

    with engine.begin() as connection:
        connection.execute(text("""
            UPDATE expert_quote
            SET customer_response='discussion',
                customer_response_message='preserved Customer evidence',
                responded_by_customer_id=:customer
            WHERE id=:id
        """), {"customer": customer_id, "id": quote_id})
    with pytest.raises(RuntimeError, match="Quote communication evidence exists"):
        command.downgrade(config, PREVIOUS)
    assert revision_status(url).current == (HEAD,)
    engine.dispose()


def test_quote_communication_owned_postgresql_response_races_and_revision_serialization():
    url = _url()
    _reset(url, HEAD)
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": url,
            "SECRET_KEY": "owned-disposable-quote-communication-proof",
        },
        skip_startup=True,
    )

    accepted_declined = _seed_current(app, uuid4().hex[:8])
    results = _race_responses(app, accepted_declined, ("accepted", None), ("declined", None))
    assert sorted(status for _payload, status in results) == [200, 409]

    accepted_discussion = _seed_current(app, uuid4().hex[:8])
    results = _race_responses(
        app,
        accepted_discussion,
        ("accepted", None),
        ("discussion", "هماهنگی شرایط پرداخت"),
    )
    assert sorted(status for _payload, status in results) == [200, 409]

    identical = _seed_current(app, uuid4().hex[:8])
    results = _race_responses(
        app,
        identical,
        ("discussion", "پیام یکسان برای بازپخش"),
        ("discussion", "پیام یکسان برای بازپخش"),
    )
    assert [status for _payload, status in results] == [200, 200]
    assert {payload["code"] for payload, _status in results} == {
        "QUOTE_RESPONSE_RECORDED",
        "QUOTE_RESPONSE_REPLAYED",
    }

    with app.app_context():
        for seed in (accepted_declined, accepted_discussion, identical):
            assert ExpertConsoleLog.query.filter_by(
                shipment_request_id=seed["request_id"],
                action="customer_quote_response",
            ).count() == 1
        db.session.remove()

    revision_seed = _seed_current(app, uuid4().hex[:8])
    barrier = Barrier(2)

    def revise():
        with app.app_context():
            barrier.wait(timeout=10)
            result = create_quote_for_request(
                int(revision_seed["request_id"]),
                {"amount": 1_500_000, "currency": "USD", "note": "official revision"},
                {"id": revision_seed["expert_id"], "role": "expert"},
            )
            db.session.remove()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        response_future = pool.submit(
            _respond,
            app,
            barrier,
            revision_seed,
            "discussion",
            "درخواست بازنگری رسمی",
        )
        revision_future = pool.submit(revise)
        response_payload, response_status = response_future.result(timeout=20)
        revision_result = revision_future.result(timeout=20)
    assert revision_result["quote"]["currency"] == "USD"
    assert response_status in {200, 409}
    if response_status == 409:
        assert response_payload["code"] == "QUOTE_SUPERSEDED"

    with app.app_context():
        quotes = (
            ExpertQuote.query.filter_by(shipment_request_id=revision_seed["request_id"])
            .order_by(ExpertQuote.created_at.asc(), ExpertQuote.id.asc())
            .all()
        )
        assert len(quotes) == 2
        assert quotes[0].amount == 1_250_000
        assert quotes[0].currency == "EUR"
        assert quotes[1].amount == 1_500_000
        assert quotes[1].currency == "USD"
        if response_status == 200:
            assert quotes[0].customer_response == "discussion"
            assert quotes[0].customer_response_message == "درخواست بازنگری رسمی"
        else:
            assert quotes[0].customer_response is None
        db.session.remove()

    expired = _seed_current(app, uuid4().hex[:8], expired=True)
    with app.app_context():
        payload, status = record_quote_response(
            str(expired["tracking_code"]),
            "accepted",
            customer_id=expired["customer_id"],
            quote_public_id=str(expired["quote_public_id"]),
        )
        assert status == 400
        assert payload["code"] == "QUOTE_EXPIRED"
        db.session.remove()
