"""Control Tower Slice 1: scope, live lineage, revocation and purpose limits."""
from dataclasses import fields, replace
from types import SimpleNamespace

import pytest
from sqlalchemy import event, update

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment
from backend.services.control_tower_scope import (
    MAX_SUMMARY_SHIPMENTS,
    ControlTowerPopulationLimit,
    ControlTowerResponsibilityInvariant, ControlTowerScopeDenied,
    governed_summary_scope, refresh_summary_context,
)
from backend.services import operational_execution_service as execution
from backend.services import route_orchestration_service as route
from backend.services import oip_service as oip
from backend.services.operational_service import OperationalError


@pytest.fixture()
def tower():
    app = create_app({
        "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "control-tower-slice-1",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        org = OperationalOrganization(name="one", is_active=True)
        foreign_org = OperationalOrganization(name="foreign", is_active=True)
        db.session.add_all([org, foreign_org])
        db.session.flush()

        def user(name, tenant, authority="EXPERT"):
            row = ExpertUser(username=name, full_name=name, password_hash="x",
                             authority=authority, role="expert", is_active=True)
            db.session.add(row)
            db.session.flush()
            member = OperationalMembership(user_id=row.id, organization_id=tenant.id,
                                           is_active=True,
                                           permissions=["operational_shipment.read"])
            db.session.add(member)
            db.session.flush()
            return row, member

        a, am = user("a", org)
        b, bm = user("b", org)
        admin, adminm = user("admin", org, "ORGANIZATION_ADMIN")
        foreign, fm = user("foreign-secret-name", foreign_org)
        platform = ExpertUser(username="platform", full_name="platform", password_hash="x",
                              authority="PLATFORM_ADMIN", role="admin", is_active=True)
        customer = Customer(first_name="Synthetic", last_name="Customer", phone="09110000000", status="active")
        db.session.add_all([platform, customer])
        db.session.flush()

        def shipment(source="accepted_quote", owner=a, tenant=org, status="planned"):
            request = None
            kwargs = {}
            if source == "accepted_quote":
                request = ShipmentRequest(operational_organization_id=tenant.id,
                                          ownership_scope="TENANT", assigned_to=owner.id,
                                          contact_phone="09110000001")
                db.session.add(request)
                db.session.flush()
                quote = ExpertQuote(shipment_request_id=request.id, amount=1,
                                    created_by_expert_id=owner.id, operational_organization_id=tenant.id)
                db.session.add(quote)
                db.session.flush()
                kwargs = {"shipment_request_id": request.id, "accepted_quote_id": quote.id}
            else:
                kwargs = {"customer_id": customer.id, "primary_responsible_expert_id": owner.id}
            row = OperationalShipment(organization_id=tenant.id, source_type=source,
                                      lifecycle_status=status, created_by_user_id=owner.id, **kwargs)
            db.session.add(row)
            db.session.commit()
            return row, request

        db.session.commit()
        yield SimpleNamespace(app=app, org=org, foreign_org=foreign_org, a=a, am=am,
                              b=b, bm=bm, admin=admin, adminm=adminm, foreign=foreign,
                              fm=fm, platform=platform, shipment=shipment)
        db.session.remove()
        db.drop_all()


def _ids(actor):
    return {context.shipment_id for context in governed_summary_scope({"id": actor.id})}


@pytest.mark.parametrize("source", ["accepted_quote", "direct"])
@pytest.mark.parametrize("status", ["planned", "in_progress"])
def test_expert_and_admin_eligible_scope_and_resolved_responsibility(tower, source, status):
    row, request = tower.shipment(source=source, status=status)
    assert _ids(tower.a) == {row.id}
    assert _ids(tower.b) == set()
    assert _ids(tower.admin) == {row.id}
    for actor in (tower.a, tower.admin):
        context, = governed_summary_scope({"id": actor.id})
        assert context.organization_id == tower.org.id
        assert context.shipment_public_id == row.public_id
        assert context.responsible_expert_id == tower.a.id
        assert context.responsible_expert_name == tower.a.full_name
        assert context.actor_persona == actor.authority
        assert (context.root_type, context.root_id) == (
            ("ShipmentRequest", request.id) if request else ("OperationalShipment", row.id)
        )
        assert context.purpose == "CONTROL_TOWER_V1_OPERATIONAL_SUMMARY"


@pytest.mark.parametrize("source", ["accepted_quote", "direct"])
def test_foreign_and_terminal_shipments_excluded_before_evaluation(tower, source):
    for status in ("completed", "cancelled"):
        row, request = tower.shipment(source=source, status=status)
        # Invalid terminal responsibility must not affect evaluation/metadata.
        if request:
            request.assigned_to = None
        else:
            row.primary_responsible_expert_id = None
    tower.shipment(source=source, owner=tower.foreign, tenant=tower.foreign_org)
    db.session.commit()
    assert _ids(tower.a) == set()
    assert _ids(tower.admin) == set()


@pytest.mark.parametrize("source", ["accepted_quote", "direct"])
def test_reassignment_refreshes_persisted_scope_and_revokes_old_context(tower, source):
    row, request = tower.shipment(source=source)
    context, = governed_summary_scope({"id": tower.a.id})
    model, key, identity = (
        (ShipmentRequest, "assigned_to", request.id) if request else
        (OperationalShipment, "primary_responsible_expert_id", row.id)
    )
    # Change committed persistence without synchronizing the retained ORM rows.
    with db.engine.begin() as connection:
        connection.execute(update(model).where(model.id == identity).values({key: tower.b.id}))
    assert _ids(tower.a) == set()
    assert _ids(tower.b) == {row.id}
    with pytest.raises(ControlTowerScopeDenied):
        refresh_summary_context({"id": tower.a.id}, context)
    admin_context, = governed_summary_scope({"id": tower.admin.id})
    assert admin_context.responsible_expert_id == tower.b.id


@pytest.mark.parametrize("membership,permissions", [
    (False, []), (True, []),
    (True, ["operational_shipment.read", "work_item.read", "route_exception.read",
            "oip.read", "operational_execution.read", "document_readiness.read"]),
])
def test_platform_admin_denied_even_with_accidental_grants(tower, membership, permissions):
    tower.shipment()
    if membership:
        db.session.add(OperationalMembership(user_id=tower.platform.id,
                       organization_id=tower.org.id, is_active=True, permissions=permissions))
        db.session.commit()
    with pytest.raises(ControlTowerScopeDenied):
        governed_summary_scope({"id": tower.platform.id, "authority": "EXPERT", "role": "expert"})


@pytest.mark.parametrize("source", ["accepted_quote", "direct"])
@pytest.mark.parametrize("failure", [
    "missing", "foreign", "inactive", "admin_owner", "platform_owner", "invalid_persona",
    "revoked_owner_membership", "ambiguous_owner_membership", "missing_owner",
])
def test_invalid_responsibility_is_unavailable_without_identity_leak(tower, source, failure, caplog):
    row, request = tower.shipment(source=source, owner=tower.b)
    if failure in {"missing", "foreign", "missing_owner"}:
        owner = {"missing": None, "foreign": tower.foreign.id, "missing_owner": 999999}[failure]
        if request:
            request.assigned_to = owner
        else:
            row.primary_responsible_expert_id = owner
    elif failure == "inactive":
        tower.b.is_active = False
    elif failure.endswith("owner") or failure == "invalid_persona":
        tower.b.authority = {"admin_owner": "ORGANIZATION_ADMIN", "platform_owner": "PLATFORM_ADMIN",
                             "invalid_persona": "UNKNOWN"}[failure]
    elif failure == "revoked_owner_membership":
        tower.bm.is_active = False
    else:
        db.session.add(OperationalMembership(user_id=tower.b.id, organization_id=tower.foreign_org.id,
                                            is_active=True, permissions=[]))
    db.session.commit()
    with pytest.raises(ControlTowerResponsibilityInvariant) as caught:
        governed_summary_scope({"id": tower.admin.id})
    assert "control_tower_responsibility_invariant" in caplog.text
    assert tower.foreign.full_name not in caplog.text + str(caught.value)
    # An Expert cannot learn another owner's invalid work through diagnostics.
    caplog.clear()
    assert _ids(tower.a) == set()
    assert caplog.text == ""


@pytest.mark.parametrize("failure", ["foreign_root", "uncertified_root", "missing_root"])
def test_broken_request_lineage_has_no_direct_owner_fallback(tower, failure):
    row, request = tower.shipment()
    row.primary_responsible_expert_id = tower.a.id
    if failure == "foreign_root":
        # Simulate corrupt persisted lineage without weakening canonical guards.
        db.session.execute(update(ShipmentRequest).where(ShipmentRequest.id == request.id)
                           .values(operational_organization_id=tower.foreign_org.id))
    elif failure == "uncertified_root":
        db.session.execute(update(ShipmentRequest).where(ShipmentRequest.id == request.id)
                           .values(ownership_scope=None))
    else:
        row.shipment_request_id = 999999
    db.session.commit()
    with pytest.raises(ControlTowerResponsibilityInvariant):
        governed_summary_scope({"id": tower.admin.id})
    assert _ids(tower.a) == set()


@pytest.mark.parametrize("persona", ["EXPERT", "ORGANIZATION_ADMIN"])
@pytest.mark.parametrize("revocation", ["inactive", "membership", "organization", "ambiguous", "persona"])
def test_live_actor_revocation_denies_scope_and_retained_context(tower, persona, revocation):
    actor, member = (tower.a, tower.am) if persona == "EXPERT" else (tower.admin, tower.adminm)
    tower.shipment()
    context, = governed_summary_scope({"id": actor.id})
    with db.engine.begin() as connection:
        if revocation == "inactive":
            connection.execute(update(ExpertUser).where(ExpertUser.id == actor.id).values(is_active=False))
        elif revocation == "persona":
            connection.execute(update(ExpertUser).where(ExpertUser.id == actor.id).values(authority="PLATFORM_ADMIN"))
        elif revocation == "membership":
            connection.execute(update(OperationalMembership).where(OperationalMembership.id == member.id).values(is_active=False))
        elif revocation == "organization":
            connection.execute(update(OperationalOrganization).where(OperationalOrganization.id == tower.org.id).values(is_active=False))
        else:
            connection.execute(OperationalMembership.__table__.insert().values(
                user_id=actor.id, organization_id=tower.foreign_org.id, is_active=True, permissions=[]))
    stale_actor = {"id": actor.id, "authority": persona, "role": "admin"}
    with pytest.raises(ControlTowerScopeDenied):
        governed_summary_scope(stale_actor)
    with pytest.raises(ControlTowerScopeDenied):
        refresh_summary_context(stale_actor, context)


def test_supplied_persona_role_and_context_fields_cannot_broaden_scope(tower):
    row, _ = tower.shipment(owner=tower.b)
    assert governed_summary_scope({"id": tower.a.id, "authority": "ORGANIZATION_ADMIN", "role": "admin"}) == ()
    own, _ = tower.shipment()
    context, = governed_summary_scope({"id": tower.a.id})
    with pytest.raises(ControlTowerScopeDenied):
        refresh_summary_context({"id": tower.b.id}, context)
    with pytest.raises(ControlTowerScopeDenied):
        refresh_summary_context({"id": tower.a.id}, replace(context, shipment_id=row.id))
    # Display/persona/tenant hints in old contexts never replace fresh authority.
    fresh = refresh_summary_context({"id": tower.a.id}, replace(
        context, organization_id=tower.foreign_org.id, actor_persona="ORGANIZATION_ADMIN",
        responsible_expert_name="forged", responsible_expert_id=tower.foreign.id))
    assert fresh.shipment_id == own.id
    assert fresh.organization_id == tower.org.id
    assert fresh.actor_persona == "EXPERT"
    assert fresh.responsible_expert_name == "a"


@pytest.mark.parametrize("change", ["terminal", "missing_owner", "inactive_owner", "membership", "lineage"])
def test_admin_retained_context_rechecks_eligibility_and_responsibility(tower, change):
    row, request = tower.shipment()
    context, = governed_summary_scope({"id": tower.admin.id})
    if change == "terminal":
        row.lifecycle_status = "completed"
    elif change == "missing_owner":
        request.assigned_to = None
    elif change == "inactive_owner":
        tower.a.is_active = False
    elif change == "membership":
        tower.am.is_active = False
    else:
        db.session.execute(update(ShipmentRequest).where(ShipmentRequest.id == request.id)
                           .values(operational_organization_id=tower.foreign_org.id))
    db.session.commit()
    expected = ControlTowerScopeDenied if change == "terminal" else ControlTowerResponsibilityInvariant
    with pytest.raises(expected):
        refresh_summary_context({"id": tower.admin.id}, context)


@pytest.mark.parametrize("persona", ["EXPERT", "ORGANIZATION_ADMIN"])
def test_summary_authority_does_not_grant_direct_source_access(tower, persona):
    row, _ = tower.shipment()
    actor = tower.a if persona == "EXPERT" else tower.admin
    user = {"id": actor.id}
    reads = (
        lambda: route.list_route_exceptions(user),
        lambda: execution._shipment(row.public_id, user),
        lambda: oip.queue(user),
    )
    before = []
    for read in reads:
        try:
            before.append(("ok", type(read()).__name__))
        except OperationalError as exc:
            before.append(("error", exc.status, exc.code))
    context, = governed_summary_scope(user)
    assert refresh_summary_context(user, context).shipment_id == row.id
    after = []
    for read in reads:
        try:
            after.append(("ok", type(read()).__name__))
        except OperationalError as exc:
            after.append(("error", exc.status, exc.code))
    assert after == before
    assert db.session.get(OperationalMembership, tower.am.id).permissions == [
        "operational_shipment.read"
    ]
    assert db.session.get(OperationalMembership, tower.adminm.id).permissions == [
        "operational_shipment.read"
    ]


def test_boundary_performs_no_source_reads_writes_or_public_payload_projection(tower):
    tower.shipment()
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.lower())

    event.listen(db.engine, "before_cursor_execute", capture)
    try:
        context, = governed_summary_scope({"id": tower.a.id})
        refresh_summary_context({"id": tower.a.id}, context)
    finally:
        event.remove(db.engine, "before_cursor_execute", capture)
    assert statements and all(s.lstrip().startswith("select") for s in statements)
    for forbidden in ("operational_delay", "operational_exception", "operational_work_item",
                      "route_plan", "route_checkpoint", "oip_", "case_document", "economics_", "expert_quote"):
        assert not any(forbidden in s for s in statements), forbidden
    assert {f.name for f in fields(context)} == {
        "shipment_id", "shipment_public_id", "organization_id", "root_type", "root_id",
        "responsible_expert_id", "responsible_expert_name", "actor_id", "actor_persona",
    }


def test_admin_invariant_aborts_whole_scope_and_clean_empty_remains_distinct(tower):
    assert governed_summary_scope({"id": tower.admin.id}) == ()
    tower.shipment()
    row, _ = tower.shipment(source="direct", owner=tower.b)
    row.primary_responsible_expert_id = None
    db.session.commit()
    with pytest.raises(ControlTowerResponsibilityInvariant):
        governed_summary_scope({"id": tower.admin.id})


def test_malformed_persisted_actor_authority_is_denied(tower):
    tower.shipment()
    tower.a.authority = "UNKNOWN"
    db.session.commit()
    with pytest.raises(ControlTowerScopeDenied):
        governed_summary_scope({"id": tower.a.id, "authority": "EXPERT"})


@pytest.mark.parametrize("actor", [{}, {"id": "invalid"}, {"id": 999999}])
def test_invalid_identity_fails_closed(tower, actor):
    with pytest.raises(ControlTowerScopeDenied):
        governed_summary_scope(actor)


def test_revoked_control_tower_capability_denies_expert(tower):
    tower.shipment()
    tower.am.permissions = []
    db.session.commit()
    with pytest.raises(ControlTowerScopeDenied):
        governed_summary_scope({"id": tower.a.id})


def test_authorized_population_is_hard_bounded(tower):
    for _ in range(MAX_SUMMARY_SHIPMENTS + 1):
        tower.shipment(source="direct")
    with pytest.raises(ControlTowerPopulationLimit):
        governed_summary_scope({"id": tower.a.id})
