"""MT-1D atomic publisher certification on an explicit disposable PostgreSQL 18 DB."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import os
from pathlib import Path
from threading import Barrier, Event

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.ownership_census import (
    CensusDecisionInput,
    CensusIntegrityError,
    CensusPublication,
    OwnershipActiveCensus,
    OwnershipCensus,
    OwnershipCensusScope,
    OwnershipDecision,
    StaleCensusPublication,
    UnauthorizedCensusPublisher,
    internal_publisher_authority,
    publish_census,
)
from backend.operational_models import (
    OperationalOrganization,
    Project,
    project_party_relationship,
)
from backend.quarantine import (
    QuarantinedResource,
    assert_instance_current,
    is_quarantined_identity,
)
from backend.resource_identity import (
    composite_identity,
    project_party_identity,
    scalar_identity,
)


FP = sha256(b"mt1d-postgresql-certification").hexdigest()
PUBLISH_TOKEN = "mt1d-postgresql-publisher-token-not-for-production"


def _authority():
    return internal_publisher_authority(PUBLISH_TOKEN)


def _authorize(monkeypatch, url):
    from sqlalchemy.engine import make_url

    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_TOKEN", PUBLISH_TOKEN)
    monkeypatch.setenv(
        "MT1D_CENSUS_PUBLISHER_DATABASE_ROLES", make_url(url).username
    )


def _decision(identity, classification="DETERMINISTIC", enforcement="CLEAR", root=None):
    return CensusDecisionInput(identity, classification, enforcement, FP, root)


def _publication(census_id, order, decisions, previous=None):
    counts = {}
    for item in decisions:
        counts[item.identity.resource_type] = counts.get(item.identity.resource_type, 0) + 1
    return CensusPublication(
        census_id, "mt1d-pg-v1", order, previous, FP, "pytest-publisher",
        tuple(decisions), counts, {name: FP for name in counts},
    )


def _url():
    url = os.getenv("MT1D_DISPOSABLE_DATABASE_URL", "")
    if not url:
        pytest.skip("explicit disposable MT-1D PostgreSQL URL not provided")
    assert "127.0.0.1" in url or "localhost" in url
    assert "/forwarder_mt1d_cert_" in url
    return url


def test_mt1d_postgresql_atomic_rollback_concurrency_and_lineage(monkeypatch):
    url = _url()
    _authorize(monkeypatch, url)
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": url,
        "SECRET_KEY": "disposable-mt1d-only",
    }, skip_startup=True)
    with app.app_context():
        assert db.session.execute(text("SHOW server_version")).scalar_one().startswith("18.")
        db.drop_all()
        db.create_all()
        engine = db.engine
        user = ExpertUser(
            username="mt1d-pg",
            password_hash="x",
            full_name="MT1D PG",
            email="mt1d-pg@example.test",
            role="admin",
            is_active=True,
        )
        organization = OperationalOrganization(name="MT1D PG")
        customer = Customer(
            company_name="MT1D PG", first_name="MT1D", last_name="PG"
        )
        db.session.add_all([user, organization])
        db.session.flush()
        db.session.add(customer)
        db.session.flush()
        project = Project(
            organization_id=organization.id,
            primary_customer_id=customer.id,
            project_code="MT1D-PG",
            created_by_user_id=user.id,
        )
        request = ShipmentRequest(
            tracking_code="MT1D-PG-REQUEST",
            contact_phone="pg",
            shipping_type="domestic",
            status="new",
            status_request_status="new",
        )
        db.session.add_all([project, request])
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request.id,
            amount=10,
            currency="IRR",
            created_by_expert_id=user.id,
        )
        db.session.add(quote)
        db.session.flush()
        db.session.execute(project_party_relationship.insert().values(
            project_id=project.id,
            customer_id=customer.id,
            party_role="payer",
            source="mt1d-certification",
        ))
        db.session.commit()
        root = scalar_identity("ShipmentRequest", request.id)
        child = scalar_identity("ExpertQuote", quote.id)
        project_root = scalar_identity("Project", project.id)
        customer_root = scalar_identity("Customer", customer.id)
        composite = project_party_identity(project.id, customer.id, "payer")
        string_identity = scalar_identity(
            "SyntheticStringResource", "00123", kind="STRING"
        )
        collision_left = composite_identity(
            "SyntheticComposite", (("A", "INTEGER", 1), ("B", "INTEGER", 23))
        )
        collision_right = composite_identity(
            "SyntheticComposite", (("A", "INTEGER", 12), ("B", "INTEGER", 3))
        )
        stable_decisions = [
            _decision(customer_root),
            _decision(project_root),
            _decision(composite, root=project_root),
            _decision(string_identity),
            _decision(collision_left),
            _decision(collision_right),
        ]

        # N: a persisted certification scope without an active pointer fails
        # closed. This simulates damaged/missing authority before publication.
        with Session(engine) as session, session.begin():
            session.add(OwnershipCensus(
                census_id="pg-missing-active",
                analysis_version="mt1d-pg-v1",
                publication_order=99,
                manifest_fingerprint="1" * 64,
                source_fingerprint=FP,
                publisher="damage-simulation",
            ))
            session.add(OwnershipCensusScope(
                census_id="pg-missing-active",
                resource_type="ShipmentRequest",
                expected_decision_count=1,
                evidence_fingerprint=FP,
            ))
        db.session.rollback()
        assert is_quarantined_identity(root) is True
        with Session(engine) as session, session.begin():
            session.execute(OwnershipCensusScope.__table__.delete())
            session.execute(OwnershipCensus.__table__.delete())

        initial = _publication(
            "pg-census-1", 1,
            [
                _decision(root),
                _decision(child, root=root),
                *stable_decisions,
            ],
        )
        try:
            monkeypatch.setenv(
                "MT1D_CENSUS_PUBLISHER_DATABASE_ROLES", "not_the_current_role"
            )
            with Session(engine) as session, pytest.raises(
                UnauthorizedCensusPublisher, match="database role"
            ):
                publish_census(session, initial, authority=_authority())
            _authorize(monkeypatch, url)
            with Session(engine) as session:
                first = publish_census(
                    session, initial, authority=_authority()
                )
            with Session(engine) as session:
                replay = publish_census(session, initial, authority=_authority())
                assert replay.replayed is True
                assert replay.cache_token == first.cache_token
            db.session.rollback()
            assert is_quarantined_identity(child) is False
            assert is_quarantined_identity(composite) is False
            assert string_identity.key_hash != scalar_identity(
                "SyntheticStringResource", 123
            ).key_hash
            assert collision_left.key_hash != collision_right.key_hash
            held = db.session.get(ExpertQuote, quote.id)
            db.session().expire_on_commit = False
            assert_instance_current(held)
            db.session.commit()

            invalid_state = _publication(
                "pg-invalid-state",
                2,
                [
                    _decision(root, "UNRESOLVED", "CLEAR"),
                    _decision(child, root=root),
                    *stable_decisions,
                ],
                "pg-census-1",
            )
            with Session(engine) as session, pytest.raises(CensusIntegrityError):
                publish_census(session, invalid_state, authority=_authority())

            failed = _publication(
                "pg-census-rollback", 2,
                [
                    _decision(root, "CONFLICT", "QUARANTINED"),
                    _decision(child, root=root),
                    *stable_decisions,
                ],
                "pg-census-1",
            )
            with Session(engine) as session, pytest.raises(RuntimeError, match="rollback"):
                publish_census(
                    session,
                    failed,
                    authority=_authority(),
                    failure_hook=lambda: (_ for _ in ()).throw(RuntimeError("rollback")),
                )
            with Session(engine) as session:
                assert session.get(OwnershipCensus, "pg-census-rollback") is None
                assert session.get(OwnershipActiveCensus, 1).census_id == "pg-census-1"

            transition = _publication(
                "pg-census-2", 2,
                [
                    _decision(root, "CONFLICT", "QUARANTINED"),
                    _decision(child, root=root),
                    *stable_decisions,
                ],
                "pg-census-1",
            )
            staged = Event()
            release = Event()

            def publish_transition():
                with Session(engine) as session:
                    return publish_census(
                        session,
                        transition,
                        authority=_authority(),
                        failure_hook=lambda: (staged.set(), release.wait(10)),
                    )

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(publish_transition)
                assert staged.wait(10)
                # The new rows exist only in the publisher's uncommitted
                # transaction; an independent reader still sees the old set.
                with Session(engine) as reader:
                    active_id = reader.get(OwnershipActiveCensus, 1).census_id
                    assert active_id == "pg-census-1"
                    assert {
                        row.enforcement_state
                        for row in reader.execute(
                            select(OwnershipDecision).where(
                                OwnershipDecision.census_id == active_id
                            )
                        ).scalars()
                    } == {"CLEAR"}
                release.set()
                transitioned = future.result(timeout=10)
            assert transitioned.cache_version == first.cache_version + 1
            with pytest.raises(QuarantinedResource):
                assert_instance_current(held)

            start = Barrier(2)
            candidates = [
                _publication(
                    f"pg-concurrent-{suffix}", 3,
                    [
                        _decision(root, "CONFLICT", "QUARANTINED"),
                        _decision(child, root=root),
                        *stable_decisions,
                    ],
                    "pg-census-2",
                )
                for suffix in ("a", "b")
            ]

            def attempt(publication):
                start.wait()
                with Session(engine) as session:
                    try:
                        return publish_census(
                            session,
                            publication,
                            authority=_authority(),
                        )
                    except StaleCensusPublication:
                        return "stale"

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(attempt, candidates))
            assert sum(outcome == "stale" for outcome in outcomes) == 1
            winner = next(outcome for outcome in outcomes if outcome != "stale")
            assert winner.cache_version == first.cache_version + 2
            assert winner.cache_token != first.cache_token

            db.session.rollback()
            assert is_quarantined_identity(root) is True
            assert is_quarantined_identity(child) is True
            assert is_quarantined_identity(composite) is False
            with Session(engine) as session:
                active_id = session.get(OwnershipActiveCensus, 1).census_id
                rows = session.execute(
                    select(OwnershipDecision).where(OwnershipDecision.census_id == active_id)
                ).scalars().all()
                assert len(rows) == 8
                assert {row.decision_version for row in rows} == {3}
            with Session(engine) as session, pytest.raises(StaleCensusPublication):
                publish_census(session, initial, authority=_authority())

            # K/M: every classification/enforcement transition rotates the
            # token, including a classification change under the same hold.
            transition_states = [
                ("DETERMINISTIC", "QUARANTINED"),
                ("DETERMINISTIC", "CLEAR"),
                ("UNRESOLVED", "QUARANTINED"),
                ("DETERMINISTIC", "CLEAR"),
            ]
            tokens = {(winner.cache_version, winner.cache_token)}
            previous = active_id
            for order, (classification, enforcement) in enumerate(
                transition_states, 4
            ):
                publication = _publication(
                    f"pg-transition-{order}",
                    order,
                    [
                        _decision(root, classification, enforcement),
                        _decision(child, root=root),
                        *stable_decisions,
                    ],
                    previous,
                )
                with Session(engine) as session:
                    result = publish_census(
                        session, publication, authority=_authority()
                    )
                tokens.add((result.cache_version, result.cache_token))
                previous = publication.census_id
            assert len(tokens) == len(transition_states) + 1
            db.session.rollback()
            assert is_quarantined_identity(root) is False
            assert is_quarantined_identity(child) is False
        finally:
            db.session.rollback()
            db.drop_all()


def test_mt1d_postgresql_migration_preserves_mt1c_and_enforces_history(monkeypatch):
    url = _url()
    _authorize(monkeypatch, url)
    config = Config(str(Path(__file__).parents[1] / "migrations" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    engine = create_engine(url)
    try:
        # Production startup creates the hardened capacity before Alembic; the
        # disposable certification mirrors that contract for the full chain.
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(128) NOT NULL PRIMARY KEY)"
            ))
        command.upgrade(config, "20260820_mt1c_quarantine_runtime")
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO ownership_certification_scope
                    (entity_type, certified_through_id, census_id, decision_epoch, activated_at)
                VALUES ('ShipmentRequest', 1, 'legacy-preserved', 1, CURRENT_TIMESTAMP)
            """))
            connection.execute(text("""
                INSERT INTO ownership_certification_decision
                    (entity_type, entity_id, classification, census_id, decision_id, decided_at)
                VALUES ('ShipmentRequest', 1, 'DETERMINISTIC',
                        'legacy-preserved', 'legacy-decision', CURRENT_TIMESTAMP)
            """))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text(
                "SELECT census_id FROM ownership_certification_scope "
                "WHERE entity_type='ShipmentRequest'"
            )).scalar_one() == "legacy-preserved"
            assert connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one() == "20260821_mt1d_canonical_census"
            assert connection.execute(text(
                "SELECT has_table_privilege('public', 'ownership_census', 'INSERT')"
            )).scalar_one() is False

        identity = scalar_identity("SyntheticMigrationResource", 1)
        with Session(engine) as session:
            publish_census(
                session,
                _publication("migration-trigger", 1, [_decision(identity)]),
                authority=_authority(),
            )
        with engine.begin() as connection, pytest.raises(DBAPIError, match="append-only"):
            connection.execute(text(
                "UPDATE ownership_decision SET classification='CONFLICT'"
            ))
        with engine.begin() as connection, pytest.raises(
            DBAPIError, match="rotate version and token"
        ):
            connection.execute(text(
                "UPDATE ownership_active_census SET cache_token=cache_token"
            ))
    finally:
        engine.dispose()
