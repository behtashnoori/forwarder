"""Regression coverage for tenant Expert membership permission provisioning."""
from __future__ import annotations

import pytest

from backend import create_app
from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import Country, ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens
from backend.services.expert_scope_service import (
    EXPERT_BASELINE_OPERATIONAL_PERMISSIONS,
    reconcile_expert_baseline_permissions,
)


@pytest.fixture()
def permission_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "expert-membership-permissions",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        organization = OperationalOrganization(name="Organization A", is_active=True)
        other_organization = OperationalOrganization(name="Organization B", is_active=True)
        admin = ExpertUser(
            username="organization-admin",
            password_hash="x",
            full_name="Organization Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        db.session.add_all([organization, other_organization, admin])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=organization.id, user_id=admin.id, permissions=[]
            )
        )
        country = Country(code="IR", name_en="Iran", name_fa="Iran")
        point_type = LogisticsPointType(
            immutable_code="PORT",
            fa_name="Port",
            en_name="Port",
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.session.add_all([country, point_type])
        db.session.flush()
        db.session.add_all(
            [
                LogisticsPoint(
                    organization_id=organization.id,
                    immutable_code="ANZALI",
                    logistics_point_type_id=point_type.id,
                    fa_name="Anzali",
                    normalized_name="anzali",
                    en_name="Anzali",
                    country_id=country.id,
                    geography_key="IR",
                    created_by=admin.id,
                    updated_by=admin.id,
                ),
                LogisticsPoint(
                    organization_id=other_organization.id,
                    immutable_code="OTHER",
                    logistics_point_type_id=point_type.id,
                    fa_name="Other Port",
                    normalized_name="other port",
                    en_name="Other Port",
                    country_id=country.id,
                    geography_key="IR",
                    created_by=admin.id,
                    updated_by=admin.id,
                ),
            ]
        )
        db.session.commit()
        yield app, {"admin_token": create_session_tokens(admin.id)["access_token"], "organization_id": organization.id}
        db.session.remove()
        db.drop_all()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("role", ["expert", "business_expert"])
def test_organization_expert_provisioning_receives_operational_baseline(permission_app, role):
    app, context = permission_app
    client = app.test_client()
    response = client.post(
        "/api/user-management/users",
        headers=_headers(context["admin_token"]),
        json={"username": f"new-{role}", "password": "test123", "full_name": role, "role": role},
    )
    assert response.status_code == 201
    user_id = response.get_json()["user_id"]

    with app.app_context():
        membership = OperationalMembership.query.filter_by(user_id=user_id).one()
        assert membership.organization_id == context["organization_id"]
        assert isinstance(membership.permissions, list)
        assert membership.permissions == list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS)
        expert_token = create_session_tokens(user_id)["access_token"]

    context = client.get("/api/operational-context", headers=_headers(expert_token))
    assert context.status_code == 200
    assert context.get_json()["data"]["permissions"] == list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS)

    management = client.post(
        "/api/admin/logistics-point-types",
        headers=_headers(expert_token),
        json={"immutable_code": "DENIED", "fa_name": "Denied", "en_name": "Denied"},
    )
    assert management.status_code == 403


def test_expert_baseline_reconciliation_is_additive_and_idempotent(permission_app):
    app, context = permission_app
    with app.app_context():
        empty = ExpertUser(username="empty-expert", password_hash="x", full_name="Empty", role="expert", is_active=True)
        subset = ExpertUser(username="subset-expert", password_hash="x", full_name="Subset", role="expert", is_active=True)
        explicit = ExpertUser(username="explicit-expert", password_hash="x", full_name="Explicit", role="expert", is_active=True)
        inactive = ExpertUser(username="inactive-expert", password_hash="x", full_name="Inactive", role="expert", is_active=False)
        non_expert = ExpertUser(username="non-expert", password_hash="x", full_name="Non Expert", role="crm_manager", is_active=True)
        db.session.add_all([empty, subset, explicit, inactive, non_expert]); db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=context["organization_id"], user_id=empty.id, permissions=[]),
            OperationalMembership(organization_id=context["organization_id"], user_id=subset.id, permissions=["operational_shipment.read"]),
            OperationalMembership(organization_id=context["organization_id"], user_id=explicit.id, permissions=["custom.explicit"]),
            OperationalMembership(organization_id=context["organization_id"], user_id=inactive.id, permissions=[]),
            OperationalMembership(organization_id=context["organization_id"], user_id=non_expert.id, permissions=[]),
        ])
        db.session.commit()
        plan = reconcile_expert_baseline_permissions()
        assert plan["mode"] == "dry-run" and plan["changed_memberships"] == 3
        assert OperationalMembership.query.filter_by(user_id=empty.id).one().permissions == []
        applied = reconcile_expert_baseline_permissions(apply=True); db.session.commit()
        assert applied["changed_memberships"] == 3
        assert OperationalMembership.query.filter_by(user_id=empty.id).one().permissions == list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS)
        assert OperationalMembership.query.filter_by(user_id=explicit.id).one().permissions == sorted([*EXPERT_BASELINE_OPERATIONAL_PERMISSIONS, "custom.explicit"])
        assert OperationalMembership.query.filter_by(user_id=inactive.id).one().permissions == []
        assert OperationalMembership.query.filter_by(user_id=non_expert.id).one().permissions == []
        assert reconcile_expert_baseline_permissions(apply=True)["changed_memberships"] == 0


def test_organization_crm_manager_does_not_receive_expert_permissions(permission_app):
    app, context = permission_app
    response = app.test_client().post(
        "/api/user-management/users",
        headers=_headers(context["admin_token"]),
        json={"username": "new-crm-manager", "password": "test123", "full_name": "CRM", "role": "crm_manager"},
    )
    assert response.status_code == 201
    with app.app_context():
        membership = OperationalMembership.query.filter_by(user_id=response.get_json()["user_id"]).one()
        assert isinstance(membership.permissions, list)
        assert membership.permissions == []


def test_legacy_admin_role_does_not_establish_organization_admin_authority(permission_app):
    app, context = permission_app
    with app.app_context():
        legacy_admin = ExpertUser(
            username="legacy-admin-expert",
            password_hash="x",
            full_name="Legacy Admin",
            role="admin",
            authority="EXPERT",
            is_active=True,
        )
        db.session.add(legacy_admin)
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=context["organization_id"], user_id=legacy_admin.id, permissions=[]
            )
        )
        db.session.commit()
        token = create_session_tokens(legacy_admin.id)["access_token"]

    response = app.test_client().post(
        "/api/user-management/users",
        headers=_headers(token),
        json={"username": "should-not-exist", "password": "test123", "full_name": "Denied"},
    )
    assert response.status_code == 403
