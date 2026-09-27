import pytest

from backend import create_app
from backend.auth import AuthManager
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_cli import bootstrap_self_hosted_admin
from backend.operational_models import OperationalAudit, OperationalMembership, OperationalOrganization
from backend.services.admin_authorization_service import (
    ORGANIZATION_ADMIN_PERMISSION,
    has_organization_admin_capability,
    user_capabilities,
)


@pytest.fixture()
def context():
    app = create_app({
        "TESTING": True,
        "APP_ENV": "testing",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "admin-composition-test",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        organization = OperationalOrganization(name="Self-hosted Organization")
        user = ExpertUser(
            username="self-hosted-admin",
            password_hash="x",
            full_name="Self-hosted Admin",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        db.session.add_all([organization, user])
        db.session.commit()
        yield app, organization, user
        db.session.remove()
        db.drop_all()


def test_system_admin_has_no_implicit_tenant_capability(context):
    _application, organization, user = context
    assert user_capabilities(user) == ["SYSTEM_ADMIN"]
    assert not has_organization_admin_capability(user)
    membership = OperationalMembership(
        organization_id=organization.id,
        user_id=user.id,
        permissions=[],
        is_active=True,
    )
    db.session.add(membership)
    db.session.commit()
    assert user_capabilities(user) == ["SYSTEM_ADMIN"]
    assert not has_organization_admin_capability(user)


def test_bootstrap_composes_both_capabilities_idempotently_with_audit(context):
    _application, organization, user = context
    first = bootstrap_self_hosted_admin(
        username=user.username,
        organization_public_id=organization.public_id,
        operator="install.operator",
        approval_reference="SELF-HOSTED-INSTALL",
    )
    assert first["status"] == "CHANGED"
    assert first["capabilities"] == ["SYSTEM_ADMIN", "ORGANIZATION_ADMIN"]
    membership = OperationalMembership.query.one()
    assert membership.organization_id == organization.id
    assert ORGANIZATION_ADMIN_PERMISSION in membership.permissions
    assert has_organization_admin_capability(user)
    assert user_capabilities(user) == ["SYSTEM_ADMIN", "ORGANIZATION_ADMIN"]
    assert OperationalAudit.query.filter_by(action="self_hosted_admin.composed").count() == 1

    second = bootstrap_self_hosted_admin(
        username=user.username,
        organization_public_id=organization.public_id,
        operator="install.operator",
        approval_reference="SELF-HOSTED-INSTALL",
    )
    assert second["status"] == "UNCHANGED"
    assert not second["audit_recorded"]
    assert OperationalMembership.query.count() == 1
    assert OperationalAudit.query.filter_by(action="self_hosted_admin.composed").count() == 1


def test_system_only_http_is_denied_and_explicit_dual_http_uses_own_tenant(context):
    application, organization, user = context
    membership = OperationalMembership(
        organization_id=organization.id,
        user_id=user.id,
        permissions=[],
        is_active=True,
    )
    db.session.add(membership)
    db.session.commit()
    token = AuthManager().generate_tokens(user.id)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client = application.test_client()

    denied = client.get(
        "/api/admin/organization-reference-catalog/cargo-types", headers=headers
    )
    assert denied.status_code == 403

    bootstrap_self_hosted_admin(
        username=user.username,
        organization_public_id=organization.public_id,
        operator="install.operator",
        approval_reference="SELF-HOSTED-INSTALL",
    )
    allowed = client.get(
        "/api/admin/organization-reference-catalog/cargo-types", headers=headers
    )
    assert allowed.status_code == 200
    assert allowed.get_json()["items"] == []
