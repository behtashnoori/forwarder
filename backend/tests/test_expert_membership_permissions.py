"""Regression coverage for tenant Expert membership permission provisioning."""
from __future__ import annotations

import pytest

from backend import create_app
from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import Country, ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens


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
def test_organization_expert_provisioning_has_no_automatic_selector_read_permission(permission_app, role):
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
        assert membership.permissions == []
        expert_token = create_session_tokens(user_id)["access_token"]

    selector = client.get(
        "/api/internal/logistics-points/tracking-selector", headers=_headers(expert_token)
    )
    assert selector.status_code == 403

    management = client.post(
        "/api/admin/logistics-point-types",
        headers=_headers(expert_token),
        json={"immutable_code": "DENIED", "fa_name": "Denied", "en_name": "Denied"},
    )
    assert management.status_code == 403


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
