"""MT-1C.1 request, materialization, Core, and exception foundation tests."""
from __future__ import annotations

from hashlib import sha256

import pytest
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.orm import Session

from backend import create_app
from backend.census_context import (
    CensusTransitioned,
    census_unit_of_work,
    clear_census_context,
)
from backend.extensions import db
from backend.models import AssignmentLog, Customer, ExpertUser, ShipmentRequest
from backend.operational_models import (
    OperationalOrganization,
    Project,
    project_party_relationship,
)
from backend.ownership_census import (
    CensusDecisionInput,
    CensusPublication,
    internal_publisher_authority,
    publish_census,
)
from backend.quarantine import (
    QuarantinedResource,
    assert_instance_current,
    decision_epoch_token,
)
from backend.resource_identity import project_party_identity, scalar_identity


FP = sha256(b"mt1c1-foundation").hexdigest()
PUBLISH_TOKEN = "mt1c1-foundation-publisher-token"


def _authority():
    return internal_publisher_authority(PUBLISH_TOKEN)


def _decision(identity, *, clear=True, root=None):
    return CensusDecisionInput(
        identity=identity,
        classification="DETERMINISTIC" if clear else "CONFLICT",
        enforcement_state="CLEAR" if clear else "QUARANTINED",
        source_fingerprint=FP,
        root_identity=root,
    )


def _publication(census_id, order, decisions, previous=None):
    counts = {}
    for item in decisions:
        counts[item.identity.resource_type] = counts.get(item.identity.resource_type, 0) + 1
    return CensusPublication(
        census_id=census_id,
        analysis_version="mt1c1-test-v1",
        publication_order=order,
        previous_census_id=previous,
        source_fingerprint=FP,
        publisher="pytest",
        decisions=tuple(decisions),
        scope_counts=counts,
        scope_fingerprints={name: FP for name in counts},
    )


@pytest.fixture()
def foundation_app(tmp_path, monkeypatch):
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_TOKEN", PUBLISH_TOKEN)
    monkeypatch.setenv("MT1D_CENSUS_PUBLISHER_DATABASE_ROLES", "sqlite")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'mt1c1.db').as_posix()}",
            "SECRET_KEY": "mt1c1-test",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed_project_parties():
    user = ExpertUser(
        username="mt1c1-admin",
        password_hash="x",
        full_name="MT1C1",
        email="mt1c1@example.test",
        role="admin",
        is_active=True,
    )
    organization = OperationalOrganization(name="MT1C1")
    customer = Customer(company_name="MT1C1", first_name="MT", last_name="1C1")
    db.session.add_all([user, organization, customer])
    db.session.flush()
    project = Project(
        organization_id=organization.id,
        primary_customer_id=customer.id,
        project_code="MT1C1",
        created_by_user_id=user.id,
    )
    db.session.add(project)
    db.session.flush()
    project_id, customer_id = project.id, customer.id
    db.session.execute(
        project_party_relationship.insert(),
        [
            {
                "project_id": project_id,
                "customer_id": customer_id,
                "party_role": "payer",
                "source": "test",
            },
            {
                "project_id": project_id,
                "customer_id": customer_id,
                "party_role": "notify_party",
                "source": "test",
            },
        ],
    )
    db.session.commit()
    clear_census_context(db.session)
    return project_id, customer_id


def test_core_composite_select_update_delete_use_exact_canonical_identity(foundation_app):
    project_id, customer_id = _seed_project_parties()
    project = scalar_identity("Project", project_id)
    customer = scalar_identity("Customer", customer_id)
    clear_party = project_party_identity(project_id, customer_id, "payer")
    denied_party = project_party_identity(project_id, customer_id, "notify_party")
    publication = _publication(
        "core-n1",
        1,
        [
            _decision(customer),
            _decision(project),
            _decision(clear_party, root=project),
            _decision(denied_party, clear=False, root=project),
        ],
    )
    with Session(db.engine) as session:
        publish_census(session, publication, authority=_authority())
    db.session.rollback()

    rows = db.session.execute(
        select(project_party_relationship.c.project_id,
               project_party_relationship.c.customer_id,
               project_party_relationship.c.party_role)
        .order_by(project_party_relationship.c.party_role)
    ).all()
    assert rows == [(project_id, customer_id, "payer")]
    db.session.rollback()

    denied_update = db.session.execute(
        update(project_party_relationship)
        .where(project_party_relationship.c.party_role == "notify_party")
        .values(source="must-not-update")
    )
    assert denied_update.rowcount == 0
    db.session.rollback()
    denied_delete = db.session.execute(
        delete(project_party_relationship).where(
            project_party_relationship.c.party_role == "notify_party"
        )
    )
    assert denied_delete.rowcount == 0
    db.session.rollback()

    clear_update = db.session.execute(
        update(project_party_relationship)
        .where(project_party_relationship.c.party_role == "payer")
        .values(source="guarded-clear-update")
    )
    assert clear_update.rowcount == 1
    db.session.rollback()
    assert clear_party.key_hash != denied_party.key_hash
    assert clear_party.components[0].value == str(project_id)
    assert clear_party.components[2].value == "payer"

    subquery = select(project_party_relationship).subquery()
    cte = select(project_party_relationship).cte()
    alias = project_party_relationship.alias("party_alias")
    for unsupported in (
        select(subquery),
        select(cte),
        update(alias).values(source="alias-bypass"),
    ):
        with pytest.raises(QuarantinedResource):
            db.session.execute(unsupported)
        db.session.rollback()

    with pytest.raises(QuarantinedResource):
        db.session.execute(project_party_relationship.insert().values(
            project_id=project_id,
            customer_id=customer_id,
            party_role="other",
            source="uncertified-insert",
        ))
    db.session.rollback()
    with db.engine.connect() as connection:
        with pytest.raises(QuarantinedResource):
            connection.execute(select(project_party_relationship))
        with pytest.raises(QuarantinedResource):
            connection.execute(text(
                "INSERT INTO operational_outbox "
                "(organization_id,event_type,aggregate_type,aggregate_id,payload,created_at) "
                "VALUES (1,'bypass','x',1,'{}',CURRENT_TIMESTAMP)"
            ))


def test_held_instance_and_multi_statement_result_keep_one_pinned_version(foundation_app):
    request_row = ShipmentRequest(
        tracking_code="MT1C1-HELD",
        contact_phone="held",
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add(request_row)
    db.session.flush()
    request_id = request_row.id
    db.session.commit()
    clear_census_context(db.session)
    identity = scalar_identity("ShipmentRequest", request_id)
    with Session(db.engine) as session:
        publish_census(
            session,
            _publication("held-n1", 1, [_decision(identity)]),
            authority=_authority(),
        )
    db.session.rollback()

    with census_unit_of_work(db.session) as context:
        held = db.session.get(ShipmentRequest, request_id)
        count = db.session.query(ShipmentRequest).count()
        rows = db.session.query(ShipmentRequest).all()
        assert count == len(rows) == 1
        assert decision_epoch_token() == context.token
        assert_instance_current(held, purpose="serialize")


def test_session_core_side_effect_dml_cannot_bypass_parent_eligibility(foundation_app):
    expert = ExpertUser(
        username="mt1c1-core-side-effect",
        password_hash="x",
        full_name="MT1C1 Core",
        email="mt1c1-core-side-effect@example.test",
        role="expert",
        is_active=True,
    )
    request_row = ShipmentRequest(
        tracking_code="MT1C1-CORE-SIDE-EFFECT",
        contact_phone="core",
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add_all([expert, request_row])
    db.session.flush()
    expert_id, request_id = expert.id, request_row.id
    db.session.commit()
    clear_census_context(db.session)
    identity = scalar_identity("ShipmentRequest", request_id)
    with Session(db.engine) as publisher:
        publish_census(
            publisher,
            _publication("side-effect-n1", 1, [_decision(identity, clear=False)]),
            authority=_authority(),
        )
    db.session.rollback()

    core_insert = insert(AssignmentLog).values(
        shipment_request_id=request_id,
        assigned_expert_id=expert_id,
        assignment_method="automatic",
        assignment_reason="must not bypass eligibility",
    )
    with pytest.raises(QuarantinedResource):
        db.session.execute(core_insert)
    db.session.rollback()
    assert db.session.execute(
        select(AssignmentLog.id).execution_options(
            include_quarantined_for_certification=True
        )
    ).all() == []


def test_ordinary_session_job_aborts_instead_of_repinning_after_commit(foundation_app):
    request_row = ShipmentRequest(
        tracking_code="MT1C1-JOB",
        contact_phone="job",
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add(request_row)
    db.session.flush()
    request_id = request_row.id
    db.session.commit()
    clear_census_context(db.session)
    identity = scalar_identity("ShipmentRequest", request_id)
    with Session(db.engine) as session:
        publish_census(
            session,
            _publication("job-n1", 1, [_decision(identity)]),
            authority=_authority(),
        )
    db.session.rollback()

    with Session(db.engine) as job:
        assert job.get(ShipmentRequest, request_id) is not None
        job.commit()
        with Session(db.engine) as publisher:
            publish_census(
                publisher,
                _publication(
                    "job-n2",
                    2,
                    [_decision(identity, clear=False)],
                    previous="job-n1",
                ),
                authority=_authority(),
            )
        with pytest.raises(CensusTransitioned):
            job.get(ShipmentRequest, request_id)
        job.rollback()


def test_public_tracking_guard_exception_is_same_nondisclosing_404(
    foundation_app, monkeypatch
):
    from backend.quarantine import QuarantinedResource
    from backend.services import tracking_service

    client = foundation_app.test_client()
    missing = client.get("/api/public/track/unknown-opaque-token")
    monkeypatch.setattr(
        tracking_service,
        "get_public_tracking_payload",
        lambda _identifier: (_ for _ in ()).throw(
            QuarantinedResource("CONFLICT internal identity 123")
        ),
    )
    denied = client.get("/api/public/track/unknown-opaque-token")
    assert denied.status_code == missing.status_code == 404
    assert denied.get_json() == missing.get_json()
    body = denied.get_data(as_text=True).lower()
    assert not any(word in body for word in ("quarant", "conflict", "lineage", "identity"))


def test_real_public_detail_uses_one_version_and_clear_behavior_is_unchanged(
    foundation_app
):
    row = ShipmentRequest(
        tracking_code="MT1C1-PUBLIC",
        contact_phone="public",
        shipping_type="domestic",
        status="new",
        status_request_status="new",
    )
    db.session.add(row)
    db.session.flush()
    row_id = row.id
    db.session.commit()
    clear_census_context(db.session)
    identity = scalar_identity("ShipmentRequest", row_id)
    with Session(db.engine) as publisher:
        first = publish_census(
            publisher,
            _publication("public-n1", 1, [_decision(identity)]),
            authority=_authority(),
        )
    client = foundation_app.test_client()
    visible = client.get("/api/public/track/MT1C1-PUBLIC")
    assert visible.status_code == 200
    assert visible.headers["X-Ownership-Census-Version"] == str(first.cache_version)
    db.session.rollback()
    clear_census_context(db.session)

    with Session(db.engine) as publisher:
        publish_census(
            publisher,
            _publication(
                "public-n2",
                2,
                [_decision(identity, clear=False)],
                previous="public-n1",
            ),
            authority=_authority(),
        )
    denied = client.get("/api/public/track/MT1C1-PUBLIC")
    assert denied.status_code == 404
