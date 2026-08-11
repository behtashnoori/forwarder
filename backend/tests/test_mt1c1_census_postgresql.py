"""PostgreSQL 18 concurrency certification for the MT-1C.1 census fence."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from hashlib import sha256
import os
from threading import Event

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, select, text, update
from sqlalchemy.orm import Session

from backend import create_app
from backend.census_context import ensure_census_context
from backend.extensions import db
from backend.models import Customer, ExpertUser, ShipmentRequest, ShipmentRequestLog
from backend.operational_models import (
    OperationalOrganization,
    OperationalOutbox,
    Project,
    project_party_relationship,
)
from backend.ownership_census import (
    CensusDecisionInput,
    CensusPublication,
    internal_publisher_authority,
    publish_census,
)
from backend.resource_identity import project_party_identity, scalar_identity
from backend.quarantine import assert_session_materializable


FP = sha256(b"mt1c1-postgresql-certification").hexdigest()
TOKEN = "mt1c1-postgresql-publisher-token"


def _url():
    url = os.getenv("MT1C1_DISPOSABLE_DATABASE_URL", "")
    if not url:
        pytest.skip("explicit disposable MT-1C.1 PostgreSQL URL not provided")
    assert "127.0.0.1" in url or "localhost" in url
    assert "/forwarder_mt1c1_cert_" in url
    return url


def _decision(identity, *, clear=True, root=None):
    return CensusDecisionInput(
        identity,
        "DETERMINISTIC" if clear else "CONFLICT",
        "CLEAR" if clear else "QUARANTINED",
        FP,
        root,
    )


def _publication(census_id, order, decisions, previous=None):
    counts = {}
    for item in decisions:
        counts[item.identity.resource_type] = counts.get(item.identity.resource_type, 0) + 1
    return CensusPublication(
        census_id,
        "mt1c1-pg-v1",
        order,
        previous,
        FP,
        "pytest-publisher",
        tuple(decisions),
        counts,
        {name: FP for name in counts},
    )


def test_mt1c1_postgresql_pinned_reader_side_effect_and_core_fence(monkeypatch):
    url = _url()
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_TOKEN", TOKEN)
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_DATABASE_ROLES", "postgres")
    config = Config("backend/migrations/alembic.ini")
    config.set_main_option("script_location", "backend/migrations")
    config.set_main_option("sqlalchemy.url", url)
    bootstrap_engine = create_engine(url)
    with bootstrap_engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(255) NOT NULL PRIMARY KEY)"
        ))
    bootstrap_engine.dispose()
    command.upgrade(config, "head")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": url,
            "SECRET_KEY": "mt1c1-pg-test",
        },
        skip_startup=True,
    )
    authority = internal_publisher_authority(TOKEN)
    with app.app_context():
        user = ExpertUser(
            username="mt1c1-pg",
            password_hash="x",
            full_name="MT1C1 PG",
            email="mt1c1-pg@example.test",
            role="admin",
            is_active=True,
        )
        organization = OperationalOrganization(name="MT1C1 PG")
        customer = Customer(company_name="MT1C1 PG", first_name="MT1C1", last_name="PG")
        request_row = ShipmentRequest(
            tracking_code="MT1C1-PG",
            contact_phone="before",
            shipping_type="domestic",
            status="new",
            status_request_status="new",
        )
        db.session.add_all([user, organization, customer, request_row])
        db.session.flush()
        project = Project(
            organization_id=organization.id,
            primary_customer_id=customer.id,
            project_code="MT1C1-PG",
            created_by_user_id=user.id,
        )
        db.session.add(project)
        db.session.flush()
        request_log = ShipmentRequestLog(
            shipment_request_id=request_row.id,
            created_at=datetime.utcnow(),
            note="lazy relationship certification",
        )
        db.session.add(request_log)
        db.session.flush()
        request_id, project_id, customer_id, organization_id = (
            request_row.id,
            project.id,
            customer.id,
            organization.id,
        )
        request_log_id = request_log.id
        db.session.execute(project_party_relationship.insert().values(
            project_id=project_id,
            customer_id=customer_id,
            party_role="payer",
            source="certification",
        ))
        db.session.commit()

        request_identity = scalar_identity("ShipmentRequest", request_id)
        customer_identity = scalar_identity("Customer", customer_id)
        project_identity = scalar_identity("Project", project_id)
        party_identity = project_party_identity(project_id, customer_id, "payer")
        request_log_identity = scalar_identity("ShipmentRequestLog", request_log_id)
        n1_decisions = [
            _decision(request_identity),
            _decision(request_log_identity, root=request_identity),
            _decision(customer_identity),
            _decision(project_identity),
            _decision(party_identity, root=project_identity),
        ]
        with Session(db.engine) as publisher:
            n1 = publish_census(
                publisher,
                _publication("mt1c1-pg-n1", 1, n1_decisions),
                authority=authority,
            )
        db.session.rollback()
        engine = db.engine

        reader_pinned = Event()
        release_reader = Event()
        publisher_done = Event()

        def reader():
            with Session(engine) as session, session.begin():
                context = ensure_census_context(session)
                held = session.get(ShipmentRequest, request_id)
                count = session.query(ShipmentRequest).count()
                page = session.execute(
                    select(ShipmentRequest).order_by(ShipmentRequest.id).limit(10)
                ).scalars().all()
                association = session.execute(select(project_party_relationship)).all()
                assert context.census_id == "mt1c1-pg-n1"
                assert context.token == (n1.cache_version, n1.cache_token)
                assert count == len(page) == len(association) == 1
                reader_pinned.set()
                assert release_reader.wait(10)
                # Held mutation and all final queries still use immutable N.
                held.contact_phone = "committed-under-n1"
                assert len(held.logs) == 1
                session.add(OperationalOutbox(
                    organization_id=organization_id,
                    event_type="mt1c1.certified",
                    aggregate_type="ShipmentRequest",
                    aggregate_id=request_id,
                    payload={"_ownership_census": {
                        "census_id": context.census_id,
                        "cache_version": context.cache_version,
                        "cache_token": context.cache_token,
                    }},
                ))
                assert session.query(ShipmentRequest).count() == count
                assert ensure_census_context(session) == context
                assert_session_materializable(session)

        def publisher():
            assert reader_pinned.wait(10)
            n2_decisions = [
                _decision(request_identity, clear=False),
                _decision(request_log_identity, root=request_identity),
                _decision(customer_identity),
                _decision(project_identity),
                _decision(party_identity, clear=False, root=project_identity),
            ]
            with Session(engine) as session:
                publish_census(
                    session,
                    _publication("mt1c1-pg-n2", 2, n2_decisions, "mt1c1-pg-n1"),
                    authority=authority,
                )
            publisher_done.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            reader_future = pool.submit(reader)
            publisher_future = pool.submit(publisher)
            assert reader_pinned.wait(10)
            assert not publisher_done.wait(0.5), "publisher bypassed the shared transaction fence"
            release_reader.set()
            reader_future.result(timeout=15)
            publisher_future.result(timeout=15)
        assert publisher_done.is_set()

        with Session(db.engine) as session, session.begin():
            context = ensure_census_context(session)
            assert context.census_id == "mt1c1-pg-n2"
            assert session.get(ShipmentRequest, request_id) is None
            assert session.execute(select(project_party_relationship)).all() == []
            assert session.execute(
                update(project_party_relationship)
                .where(project_party_relationship.c.project_id == project_id)
                .values(source="must-not-update")
            ).rowcount == 0
            assert session.execute(
                delete(project_party_relationship).where(
                    project_party_relationship.c.project_id == project_id
                )
            ).rowcount == 0

        with Session(db.engine) as session:
            stored_phone = session.execute(
                select(ShipmentRequest.contact_phone)
                .where(ShipmentRequest.id == request_id)
                .execution_options(include_quarantined_for_certification=True)
            ).scalar_one()
            assert stored_phone == "committed-under-n1"
            outbox = session.execute(
                select(OperationalOutbox).where(
                    OperationalOutbox.event_type == "mt1c1.certified"
                )
            ).scalar_one()
            assert outbox.payload["_ownership_census"]["census_id"] == "mt1c1-pg-n1"
