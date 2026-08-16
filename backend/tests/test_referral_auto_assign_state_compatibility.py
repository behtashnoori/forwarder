from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend import create_app
from backend.extensions import db
from backend.models import ReferralAutoAssignState
from backend.operational_models import OperationalOrganization
from backend.referral_engine import ReferralEngine


@pytest.fixture()
def state_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "referral-state-compatibility-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        legacy = ReferralAutoAssignState(id=1, last_index=2)
        org_a = OperationalOrganization(public_id="state-org-a", name="State Org A")
        org_b = OperationalOrganization(public_id="state-org-b", name="State Org B")
        db.session.add_all([legacy, org_a, org_b])
        db.session.commit()
        yield app, org_a.id, org_b.id
        db.session.remove()
        db.drop_all()


def test_legacy_null_state_is_preserved_and_tenant_states_are_isolated(state_app):
    _, org_a_id, org_b_id = state_app
    engine = ReferralEngine(db.session)

    state_a = engine._get_or_create_auto_assign_state(org_a_id)
    state_b = engine._get_or_create_auto_assign_state(org_b_id)
    db.session.flush()

    legacy = db.session.get(ReferralAutoAssignState, 1)
    assert legacy.operational_organization_id is None
    assert legacy.last_index == 2
    assert state_a.id != legacy.id
    assert state_b.id not in {legacy.id, state_a.id}
    assert state_a.operational_organization_id == org_a_id
    assert state_b.operational_organization_id == org_b_id


def test_existing_tenant_state_is_reused(state_app):
    _, org_a_id, _ = state_app
    engine = ReferralEngine(db.session)
    first = engine._get_or_create_auto_assign_state(org_a_id)
    db.session.flush()
    second = engine._get_or_create_auto_assign_state(org_a_id)
    assert second.id == first.id
    assert ReferralAutoAssignState.query.filter_by(
        operational_organization_id=org_a_id
    ).count() == 1


POSTGRES_URL = os.environ.get("V1951_POSTGRES_URL")
pytestmark_postgres = pytest.mark.skipif(
    not POSTGRES_URL, reason="V1951_POSTGRES_URL is required"
)


def _postgres_url():
    url = make_url(POSTGRES_URL)
    assert url.get_backend_name() == "postgresql"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    return url


def _sync_sequence(connection):
    connection.execute(text(
        "SELECT setval("
        "pg_get_serial_sequence('referral_auto_assign_state', 'id'), "
        "GREATEST(COALESCE((SELECT MAX(id) FROM referral_auto_assign_state), 1), "
        "(SELECT last_value FROM referral_auto_assign_state_id_seq)), "
        "CASE WHEN EXISTS (SELECT 1 FROM referral_auto_assign_state) THEN true "
        "ELSE (SELECT is_called FROM referral_auto_assign_state_id_seq) END)"
    ))


@pytestmark_postgres
def test_postgresql_sequence_repairs_empty_legacy_multiple_and_correct_states():
    engine = create_engine(_postgres_url())
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM referral_auto_assign_state"))
        connection.execute(text(
            "SELECT setval('referral_auto_assign_state_id_seq', 1, false)"
        ))
        _sync_sequence(connection)
        assert connection.execute(text(
            "SELECT nextval('referral_auto_assign_state_id_seq')"
        )).scalar_one() == 1

        connection.execute(text("DELETE FROM referral_auto_assign_state"))
        connection.execute(text(
            "INSERT INTO referral_auto_assign_state "
            "(id, last_index, updated_at, operational_organization_id) "
            "VALUES (1, 2, NOW(), NULL)"
        ))
        connection.execute(text(
            "SELECT setval('referral_auto_assign_state_id_seq', 1, true)"
        ))
        _sync_sequence(connection)
        assert connection.execute(text(
            "SELECT nextval('referral_auto_assign_state_id_seq')"
        )).scalar_one() == 2

        connection.execute(text(
            "INSERT INTO referral_auto_assign_state "
            "(id, last_index, updated_at, operational_organization_id) "
            "VALUES (5, 0, NOW(), NULL)"
        ))
        connection.execute(text(
            "SELECT setval('referral_auto_assign_state_id_seq', 1, true)"
        ))
        _sync_sequence(connection)
        assert connection.execute(text(
            "SELECT nextval('referral_auto_assign_state_id_seq')"
        )).scalar_one() == 6

        connection.execute(text(
            "SELECT setval('referral_auto_assign_state_id_seq', 20, true)"
        ))
        _sync_sequence(connection)
        assert connection.execute(text(
            "SELECT nextval('referral_auto_assign_state_id_seq')"
        )).scalar_one() == 21
        _sync_sequence(connection)
        assert connection.execute(text(
            "SELECT nextval('referral_auto_assign_state_id_seq')"
        )).scalar_one() == 22
    engine.dispose()


def _concurrent_state(organization_id: int, barrier: threading.Barrier) -> int:
    engine = create_engine(_postgres_url())
    try:
        with Session(engine) as session:
            barrier.wait()
            state = ReferralEngine(session)._get_or_create_auto_assign_state(
                organization_id
            )
            state_id = state.id
            session.commit()
            return state_id
    finally:
        engine.dispose()


@pytestmark_postgres
def test_postgresql_concurrent_first_use_same_organization_converges():
    engine = create_engine(_postgres_url())
    with engine.begin() as connection:
        organization_id = connection.execute(text(
            "INSERT INTO operational_organization (public_id, name, is_active, created_at) "
            "VALUES ('concurrent-same-org', 'Concurrent Same Org', true, NOW()) "
            "RETURNING id"
        )).scalar_one()
    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: _concurrent_state(organization_id, barrier), range(2)))
    assert len(set(ids)) == 1
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM referral_auto_assign_state "
            "WHERE operational_organization_id=:organization_id"
        ), {"organization_id": organization_id}).scalar_one() == 1
    engine.dispose()


@pytestmark_postgres
def test_postgresql_concurrent_first_use_different_organizations_stays_isolated():
    engine = create_engine(_postgres_url())
    with engine.begin() as connection:
        organization_ids = [
            connection.execute(text(
                "INSERT INTO operational_organization "
                "(public_id, name, is_active, created_at) "
                "VALUES (:public_id, :name, true, NOW()) RETURNING id"
            ), {"public_id": f"concurrent-org-{suffix}", "name": f"Concurrent Org {suffix}"}).scalar_one()
            for suffix in ("a", "b")
        ]
    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda org_id: _concurrent_state(org_id, barrier), organization_ids))
    assert len(set(ids)) == 2
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT operational_organization_id FROM referral_auto_assign_state "
            "WHERE operational_organization_id = ANY(:organization_ids)"
        ), {"organization_ids": organization_ids}).scalars().all()
        assert set(rows) == set(organization_ids)
    engine.dispose()
