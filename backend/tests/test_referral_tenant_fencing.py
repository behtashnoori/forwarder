from __future__ import annotations

import json

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ReferralRule, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.referral_engine import ReferralAssignmentRejected, ReferralEngine


@pytest.fixture()
def referral_tenants():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "referral-tenant-fencing-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        org_a = OperationalOrganization(public_id="org-a", name="Org A", is_active=True)
        org_b = OperationalOrganization(public_id="org-b", name="Org B", is_active=True)
        admin = ExpertUser(
            username="referral-admin", password_hash="x", full_name="Admin",
            role="admin", is_active=True,
        )
        valid_a = ExpertUser(
            username="valid-a", password_hash="x", full_name="Valid A",
            role="expert", is_active=True, can_handle_domestic=True,
        )
        stale_a = ExpertUser(
            username="stale-a", password_hash="x", full_name="Stale A",
            role="expert", is_active=True, can_handle_domestic=True,
        )
        expert_b = ExpertUser(
            username="expert-b", password_hash="x", full_name="Expert B",
            role="expert", is_active=True, can_handle_domestic=True,
        )
        db.session.add_all([org_a, org_b, admin, valid_a, stale_a, expert_b])
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(organization_id=org_a.id, user_id=valid_a.id, permissions=[]),
                OperationalMembership(organization_id=org_a.id, user_id=stale_a.id, permissions=[]),
                OperationalMembership(organization_id=org_b.id, user_id=expert_b.id, permissions=[]),
            ]
        )
        db.session.commit()
        yield {
            "app": app,
            "org_a": org_a.id,
            "org_b": org_b.id,
            "admin": admin.id,
            "valid_a": valid_a.id,
            "stale_a": stale_a.id,
            "expert_b": expert_b.id,
        }
        db.session.remove()
        db.drop_all()


def _request(org_id: int) -> ShipmentRequest:
    row = ShipmentRequest(
        contact_phone="09120000000",
        shipping_type="domestic",
        transport_method="road",
        domestic_transport_method="road",
        status="new",
        status_request_status="new",
        ownership_scope="TENANT",
        operational_organization_id=org_id,
        assigned_to=None,
    )
    db.session.add(row)
    db.session.flush()
    return row


def _rule(data, action: dict, *, stop_on_match: bool = True, priority: int = 1):
    row = ReferralRule(
        name=f"rule-{priority}",
        operational_organization_id=data["org_a"],
        is_active=True,
        priority=priority,
        conditions=json.dumps({"shipping_type": "domestic"}),
        action=json.dumps(action),
        stop_on_match=stop_on_match,
        created_by=data["admin"],
    )
    db.session.add(row)
    db.session.flush()
    return row


def _assign(data, request: ShipmentRequest):
    result = ReferralEngine(db.session).auto_assign_request(request.id)
    db.session.flush()
    return result


def test_direct_rule_rejects_cross_tenant_expert(referral_tenants):
    request = _request(referral_tenants["org_a"])
    _rule(referral_tenants, {"type": "direct_assign", "expert_id": referral_tenants["expert_b"]})
    assert _assign(referral_tenants, request) is None
    assert request.assigned_to is None


def test_pool_filters_cross_tenant_and_stale_candidates(referral_tenants):
    request = _request(referral_tenants["org_a"])
    stale_membership = OperationalMembership.query.filter_by(
        user_id=referral_tenants["stale_a"]
    ).one()
    stale_membership.is_active = False
    _rule(
        referral_tenants,
        {
            "type": "pool_assign",
            "expert_ids": [
                referral_tenants["expert_b"],
                referral_tenants["stale_a"],
                referral_tenants["valid_a"],
            ],
            "strategy": "round_robin",
        },
    )
    assert _assign(referral_tenants, request) == referral_tenants["valid_a"]
    assert request.assigned_to == referral_tenants["valid_a"]


def test_stale_direct_rule_after_expert_moves_organizations(referral_tenants):
    request = _request(referral_tenants["org_a"])
    old = OperationalMembership.query.filter_by(user_id=referral_tenants["stale_a"]).one()
    old.is_active = False
    db.session.add(OperationalMembership(
        organization_id=referral_tenants["org_b"],
        user_id=referral_tenants["stale_a"],
        permissions=[],
    ))
    _rule(referral_tenants, {"type": "direct_assign", "expert_id": referral_tenants["stale_a"]})
    assert _assign(referral_tenants, request) is None
    assert request.assigned_to is None


def test_inactive_membership_is_not_assignable(referral_tenants):
    request = _request(referral_tenants["org_a"])
    membership = OperationalMembership.query.filter_by(user_id=referral_tenants["valid_a"]).one()
    membership.is_active = False
    _rule(referral_tenants, {"type": "direct_assign", "expert_id": referral_tenants["valid_a"]})
    assert _assign(referral_tenants, request) is None


def test_inactive_expert_is_not_assignable(referral_tenants):
    request = _request(referral_tenants["org_a"])
    db.session.get(ExpertUser, referral_tenants["valid_a"]).is_active = False
    _rule(referral_tenants, {"type": "direct_assign", "expert_id": referral_tenants["valid_a"]})
    assert _assign(referral_tenants, request) is None


def test_duplicate_active_memberships_are_not_assignable(referral_tenants):
    request = _request(referral_tenants["org_a"])
    db.session.add(OperationalMembership(
        organization_id=referral_tenants["org_b"],
        user_id=referral_tenants["valid_a"],
        permissions=[],
    ))
    _rule(referral_tenants, {"type": "direct_assign", "expert_id": referral_tenants["valid_a"]})
    assert _assign(referral_tenants, request) is None


def test_inactive_organization_is_not_assignable(referral_tenants):
    request = _request(referral_tenants["org_a"])
    db.session.get(OperationalOrganization, referral_tenants["org_a"]).is_active = False
    _rule(referral_tenants, {"type": "direct_assign", "expert_id": referral_tenants["valid_a"]})
    assert _assign(referral_tenants, request) is None


def test_valid_same_organization_direct_assignment_succeeds(referral_tenants):
    request = _request(referral_tenants["org_a"])
    _rule(referral_tenants, {"type": "direct_assign", "expert_id": referral_tenants["valid_a"]})
    assert _assign(referral_tenants, request) == referral_tenants["valid_a"]
    assert request.assigned_to == referral_tenants["valid_a"]


def test_final_assignment_boundary_rejects_forced_cross_tenant_id(referral_tenants):
    request = _request(referral_tenants["org_a"])
    with pytest.raises(ReferralAssignmentRejected, match="runtime tenant"):
        ReferralEngine(db.session)._assign_and_log(
            request=request,
            expert_id=referral_tenants["expert_b"],
            candidate_expert_ids=[referral_tenants["expert_b"]],
            debug={"forced": True},
        )
    assert request.assigned_to is None
    assert request.status == "new"


def test_rule_fallback_and_round_robin_remain_tenant_scoped(referral_tenants):
    first = _request(referral_tenants["org_a"])
    _rule(
        referral_tenants,
        {"type": "direct_assign", "expert_id": referral_tenants["expert_b"]},
        stop_on_match=False,
        priority=1,
    )
    _rule(
        referral_tenants,
        {
            "type": "pool_assign",
            "expert_ids": [referral_tenants["expert_b"], referral_tenants["valid_a"]],
            "strategy": "round_robin",
        },
        priority=2,
    )
    assert _assign(referral_tenants, first) == referral_tenants["valid_a"]
    second = _request(referral_tenants["org_a"])
    assert _assign(referral_tenants, second) == referral_tenants["valid_a"]
