"""MT-1D canonical identity, state, publisher, lineage and held-object tests."""
from __future__ import annotations

from hashlib import sha256

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from backend import create_app
from backend.census_context import CensusTransitioned
from backend.extensions import db
from backend.models import Activity, Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.ownership_census import (
    CensusDecisionInput,
    CensusIntegrityError,
    CensusPublication,
    OwnershipActiveCensus,
    OwnershipCensus,
    OwnershipDecision,
    StaleCensusPublication,
    UnauthorizedCensusPublisher,
    internal_publisher_authority,
    publish_census,
)
from backend.quarantine import (
    assert_instance_current,
    decision_epoch_token,
    is_quarantined_identity,
)
from backend.resource_identity import (
    InvalidResourceIdentity,
    ResourceIdentity,
    composite_identity,
    project_party_identity,
    scalar_identity,
)


FINGERPRINT = sha256(b"mt1d-test-evidence").hexdigest()
PUBLISH_TOKEN = "mt1d-pytest-publisher-token-not-for-production"


def _authority():
    return internal_publisher_authority(PUBLISH_TOKEN)


def _decision(identity, classification="DETERMINISTIC", enforcement="CLEAR", root=None):
    return CensusDecisionInput(
        identity=identity,
        classification=classification,
        enforcement_state=enforcement,
        source_fingerprint=FINGERPRINT,
        root_identity=root,
    )


def _publication(census_id, order, decisions, previous=None):
    counts = {}
    for item in decisions:
        counts[item.identity.resource_type] = counts.get(item.identity.resource_type, 0) + 1
    return CensusPublication(
        census_id=census_id,
        analysis_version="mt1d-test-v1",
        publication_order=order,
        previous_census_id=previous,
        source_fingerprint=FINGERPRINT,
        publisher="pytest-internal",
        decisions=tuple(decisions),
        scope_counts=counts,
        scope_fingerprints={name: FINGERPRINT for name in counts},
    )


@pytest.fixture()
def mt1d_app(tmp_path, monkeypatch):
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_TOKEN", PUBLISH_TOKEN)
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_DATABASE_ROLES", "sqlite")
    path = tmp_path / "mt1d.db"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{path.as_posix()}",
        "SECRET_KEY": "mt1d-test",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _persist_request(marker: str) -> ShipmentRequest:
    row = ShipmentRequest(
        tracking_code=f"MT1D-{marker}",
        contact_phone=marker,
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add(row)
    db.session.commit()
    return row


def _persist_request_with_quote(marker: str) -> tuple[ShipmentRequest, ExpertQuote]:
    user = ExpertUser(
        username=f"mt1d-{marker}",
        password_hash="x",
        full_name=marker,
        email=f"mt1d-{marker}@example.test",
        role="admin",
        is_active=True,
    )
    request = _persist_request(marker)
    db.session.add(user)
    db.session.flush()
    quote = ExpertQuote(
        shipment_request_id=request.id,
        amount=10,
        currency="IRR",
        created_by_expert_id=user.id,
    )
    db.session.add(quote)
    db.session.commit()
    return request, quote


def test_scalar_string_uuid_and_namespace_identity_are_type_safe():
    customer = scalar_identity("Customer", 123)
    shipment = scalar_identity("ShipmentRequest", 123)
    string = scalar_identity("ExternalResource", "123", kind="STRING")
    uuid = scalar_identity(
        "ExternalResource", "550E8400-E29B-41D4-A716-446655440000", kind="UUID"
    )
    assert customer.key_hash != shipment.key_hash
    assert customer.key_hash != string.key_hash
    assert uuid.components[0].value == "550e8400-e29b-41d4-a716-446655440000"
    assert ResourceIdentity.from_payload(customer.resource_type, customer.key_payload) == customer
    with pytest.raises(InvalidResourceIdentity):
        scalar_identity("Customer", "0123")
    with pytest.raises(InvalidResourceIdentity):
        scalar_identity("ExternalResource", "not-a-uuid", kind="UUID")


def test_composite_identity_is_unambiguous_and_project_party_is_lossless():
    left = composite_identity("Composite", (("A", "INTEGER", 1), ("B", "INTEGER", 23)))
    right = composite_identity("Composite", (("A", "INTEGER", 12), ("B", "INTEGER", 3)))
    assert left.key_payload != right.key_payload
    assert left.key_hash != right.key_hash
    party = project_party_identity(7, 9, "notify;party=exact")
    assert [part.name for part in party.components] == [
        "project_id", "customer_id", "party_role"
    ]
    assert party.components[-1].value == "notify;party=exact"


def test_state_machine_rejects_implicit_safe_state_and_unauthorized_publish(mt1d_app):
    identity = scalar_identity("SyntheticResource", 1)
    invalid = _publication(
        "invalid-state", 1, [_decision(identity, "UNRESOLVED", "CLEAR")]
    )
    with Session(db.engine) as session:
        with pytest.raises(UnauthorizedCensusPublisher):
            internal_publisher_authority("wrong-token")
        with pytest.raises(CensusIntegrityError):
            publish_census(
                session, invalid, authority=_authority()
            )
        with pytest.raises(UnauthorizedCensusPublisher):
            publish_census(session, _publication("unauthorized", 1, [_decision(identity)]), authority=object())


def test_atomic_publish_rollback_stale_replay_and_append_only(mt1d_app):
    identity = scalar_identity("SyntheticResource", 1)
    first = _publication("census-1", 1, [_decision(identity)])
    with Session(db.engine) as session:
        result = publish_census(
            session, first, authority=_authority()
        )
        assert result.cache_version == 1
        replay = publish_census(
            session, first, authority=_authority()
        )
        assert replay.replayed and replay.cache_token == result.cache_token

    failed = _publication(
        "census-failed",
        2,
        [_decision(identity, "UNRESOLVED", "QUARANTINED")],
        previous="census-1",
    )
    with Session(db.engine) as session:
        with pytest.raises(RuntimeError, match="injected"):
            publish_census(
                session,
                failed,
                authority=_authority(),
                failure_hook=lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            )
        assert session.get(OwnershipCensus, "census-failed") is None
        assert session.get(OwnershipActiveCensus, 1).census_id == "census-1"

    stale = _publication("census-stale", 2, [_decision(identity)], previous=None)
    with Session(db.engine) as session:
        with pytest.raises(StaleCensusPublication):
            publish_census(
                session, stale, authority=_authority()
            )
        row = session.execute(select(OwnershipDecision).limit(1)).scalar_one()
        row.classification = "CONFLICT"
        with pytest.raises(CensusIntegrityError, match="append-only"):
            session.flush()
        session.rollback()


def test_cache_transition_lineage_and_decision_versions(mt1d_app):
    request, quote = _persist_request_with_quote("lineage")
    root = scalar_identity("ShipmentRequest", request.id)
    child = scalar_identity("ExpertQuote", quote.id)
    with Session(db.engine) as session:
        first = publish_census(
            session,
            _publication("lineage-1", 1, [_decision(root), _decision(child, root=root)]),
            authority=_authority(),
        )
    # MT-1C.1 makes the pre-publication implicit transaction an immutable
    # census unit.  End it before asserting the newly active publication.
    db.session.rollback()
    assert is_quarantined_identity(child) is False
    assert decision_epoch_token() == (first.cache_version, first.cache_token)

    with Session(db.engine) as session:
        second = publish_census(
            session,
            _publication(
                "lineage-2",
                2,
                [
                    _decision(root, "DETERMINISTIC", "QUARANTINED"),
                    _decision(child, root=root),
                ],
                previous="lineage-1",
            ),
            authority=_authority(),
        )
        versions = session.execute(
            select(OwnershipDecision.decision_version)
            .where(OwnershipDecision.resource_type == "ExpertQuote")
            .order_by(OwnershipDecision.decision_version)
        ).scalars().all()
        assert versions == [1, 2]
    db.session.rollback()
    assert second.cache_version == first.cache_version + 1
    assert second.cache_token != first.cache_token
    assert is_quarantined_identity(child) is True


def test_cache_token_changes_for_every_effective_state_transition(mt1d_app):
    identity = scalar_identity("SyntheticResource", 77)
    states = [
        ("DETERMINISTIC", "CLEAR"),
        ("CONFLICT", "QUARANTINED"),
        ("DETERMINISTIC", "QUARANTINED"),
        ("DETERMINISTIC", "CLEAR"),
        ("UNRESOLVED", "QUARANTINED"),
        ("DETERMINISTIC", "CLEAR"),
    ]
    tokens = []
    previous = None
    for order, (classification, enforcement) in enumerate(states, 1):
        census_id = f"transition-{order}"
        with Session(db.engine) as session:
            result = publish_census(
                session,
                _publication(
                    census_id,
                    order,
                    [_decision(identity, classification, enforcement)],
                    previous,
                ),
                authority=_authority(),
            )
        tokens.append((result.cache_version, result.cache_token))
        previous = census_id
    assert len(set(tokens)) == len(states)
    assert [version for version, _token in tokens] == list(range(1, len(states) + 1))


def test_held_instance_revalidated_after_root_publication(mt1d_app):
    row = ShipmentRequest(
        tracking_code="MT1D-HELD",
        contact_phone="held",
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add(row)
    db.session.commit()
    row_id = row.id
    identity = scalar_identity("ShipmentRequest", row_id)
    with Session(db.engine) as session:
        publish_census(
            session,
            _publication("held-1", 1, [_decision(identity)]),
            authority=_authority(),
        )
    db.session.rollback()
    held = db.session.get(ShipmentRequest, row_id)
    db.session().expire_on_commit = False
    assert_instance_current(held)
    db.session.commit()

    with Session(db.engine) as session:
        publish_census(
            session,
            _publication(
                "held-2",
                2,
                [_decision(identity, "CONFLICT", "QUARANTINED")],
                previous="held-1",
            ),
            authority=_authority(),
        )
    with pytest.raises(CensusTransitioned):
        assert_instance_current(held)
    held.contact_phone = "must-not-write"
    with pytest.raises(CensusTransitioned):
        db.session.flush()
    db.session.rollback()
    result = db.session.execute(
        update(ShipmentRequest)
        .where(ShipmentRequest.id == row_id)
        .values(contact_phone="must-not-bulk-write")
    )
    assert result.rowcount == 0
    db.session.rollback()
    core_result = db.session.execute(
        ShipmentRequest.__table__.update()
        .where(ShipmentRequest.__table__.c.id == row_id)
        .values(contact_phone="must-not-core-write")
    )
    assert core_result.rowcount == 0
    db.session.rollback()
    core_delete = db.session.execute(
        ShipmentRequest.__table__.delete().where(
            ShipmentRequest.__table__.c.id == row_id
        )
    )
    assert core_delete.rowcount == 0
    db.session.rollback()


def test_held_descendant_follows_current_root_without_copied_hold(mt1d_app):
    user = ExpertUser(
        username="mt1d-held-child",
        password_hash="x",
        full_name="Held Child",
        email="mt1d-held-child@example.test",
        role="admin",
        is_active=True,
    )
    request = ShipmentRequest(
        tracking_code="MT1D-HELD-ROOT",
        contact_phone="root",
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add_all([user, request])
    db.session.flush()
    quote = ExpertQuote(
        shipment_request_id=request.id,
        amount=10,
        currency="IRR",
        created_by_expert_id=user.id,
    )
    db.session.add(quote)
    db.session.commit()
    root = scalar_identity("ShipmentRequest", request.id)
    child = scalar_identity("ExpertQuote", quote.id)
    with Session(db.engine) as session:
        publish_census(
            session,
            _publication("held-child-1", 1, [_decision(root), _decision(child, root=root)]),
            authority=_authority(),
        )
    db.session.rollback()
    held = db.session.get(ExpertQuote, quote.id)
    db.session().expire_on_commit = False
    assert_instance_current(held)
    db.session.commit()
    with Session(db.engine) as session:
        publish_census(
            session,
            _publication(
                "held-child-2",
                2,
                [
                    _decision(root, "INVALID_LINEAGE", "QUARANTINED"),
                    _decision(child, root=root),
                ],
                previous="held-child-1",
            ),
            authority=_authority(),
        )
    with pytest.raises(CensusTransitioned):
        assert_instance_current(held)


def test_publisher_rejects_unrelated_clear_root_lineage_laundering(mt1d_app):
    actual_request, quote = _persist_request_with_quote("lineage-attack")
    unrelated_request = _persist_request("unrelated-clear-root")
    actual = scalar_identity("ShipmentRequest", actual_request.id)
    unrelated = scalar_identity("ShipmentRequest", unrelated_request.id)
    child = scalar_identity("ExpertQuote", quote.id)
    attack = _publication(
        "lineage-attack",
        1,
        [
            _decision(actual, "CONFLICT", "QUARANTINED"),
            _decision(unrelated),
            _decision(child, root=unrelated),
        ],
    )
    with Session(db.engine) as session, pytest.raises(
        CensusIntegrityError, match="does not match database lineage"
    ):
        publish_census(
            session, attack, authority=_authority()
        )


def test_clear_multi_parent_cannot_hide_a_quarantined_parent(mt1d_app):
    user = ExpertUser(
        username="mt1d-multi-parent",
        password_hash="x",
        full_name="Multi Parent",
        email="mt1d-multi-parent@example.test",
        role="admin",
        is_active=True,
    )
    customer = Customer(first_name="Multi", last_name="Parent")
    request = ShipmentRequest(
        tracking_code="MT1D-MULTI-PARENT",
        contact_phone="multi",
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add_all([user, customer, request])
    db.session.flush()
    activity = Activity(
        customer_id=customer.id,
        shipment_request_id=request.id,
        expert_user_id=user.id,
        activity_type="note",
        subject="must inherit every parent hold",
    )
    db.session.add(activity)
    db.session.commit()
    customer_identity = scalar_identity("Customer", customer.id)
    request_identity = scalar_identity("ShipmentRequest", request.id)
    activity_identity = scalar_identity("Activity", activity.id)
    attack = _publication(
        "multi-parent-attack",
        1,
        [
            _decision(customer_identity, "CONFLICT", "QUARANTINED"),
            _decision(request_identity),
            _decision(activity_identity, root=request_identity),
        ],
    )
    with Session(db.engine) as session, pytest.raises(
        CensusIntegrityError, match="quarantined parent"
    ):
        publish_census(session, attack, authority=_authority())


def test_missing_active_marker_fails_closed_for_published_scope(mt1d_app):
    row = _persist_request("missing-active")
    identity = scalar_identity("ShipmentRequest", row.id)
    with Session(db.engine) as session:
        publish_census(
            session,
            _publication("missing-active", 1, [_decision(identity)]),
            authority=_authority(),
        )
    with Session(db.engine) as session, session.begin():
        session.execute(delete(OwnershipActiveCensus))
    db.session.rollback()
    assert is_quarantined_identity(identity) is True
