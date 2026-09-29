"""Focused qualification for governed platform maintenance admin provisioning."""
from __future__ import annotations

import json

import bcrypt
import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_cli import main as operational_cli_main
from backend.operational_models import (
    OperationalAudit,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    RoutePlan,
)
from backend.services.admin_authorization_service import (
    ORGANIZATION_ADMIN_PERMISSION,
    effective_authority,
)
from backend.services.platform_admin_provisioning_service import (
    PROVISION_ACTIONS,
    PROVISION_OPERATION,
    PlatformAdminProvisioningError,
    provision_platform_maintenance_admin,
)
from backend.services.user_service import hash_password


PASSWORD = "WalkthroughPlatformAdmin-2026!"
USERNAME = "walkthrough_platform_admin"
FULL_NAME = "Walkthrough Platform Maintenance Admin"
OPERATOR = "walkthrough.bootstrap.operator"
APPROVAL = "PLATFORM-ADMIN-BOOTSTRAP/2026-09-29"


@pytest.fixture()
def provisioning_context():
    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": "testing",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "platform-admin-provisioning-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        active = OperationalOrganization(
            name="Walkthrough Organization", is_active=True
        )
        inactive = OperationalOrganization(
            name="Inactive Organization", is_active=False
        )
        preserved_user = ExpertUser(
            username="walkthrough_admin",
            password_hash=hash_password("PreservedOrganizationAdmin!"),
            full_name="Walkthrough Organization Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        db.session.add_all([active, inactive, preserved_user])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=active.id,
                user_id=preserved_user.id,
                is_active=True,
                permissions=[ORGANIZATION_ADMIN_PERMISSION],
            )
        )
        db.session.commit()
        yield app, active, inactive, preserved_user
        db.session.remove()
        db.drop_all()


def _provision(active: OperationalOrganization, **overrides):
    values = {
        "username": USERNAME,
        "full_name": FULL_NAME,
        "password": PASSWORD,
        "organization_public_id": active.public_id,
        "operator": OPERATOR,
        "approval_reference": APPROVAL,
        "bootstrap_authorized": True,
    }
    values.update(overrides)
    return provision_platform_maintenance_admin(**values)


def _audit_rows(user_id: int):
    return list(
        db.session.scalars(
            db.select(OperationalAudit)
            .where(
                OperationalAudit.actor_user_id == user_id,
                OperationalAudit.action.in_(PROVISION_ACTIONS),
            )
            .order_by(OperationalAudit.action)
        )
    )


def test_success_creates_exact_actor_authority_membership_and_audit(
    provisioning_context,
):
    _app, active, _inactive, preserved_user = provisioning_context

    result = _provision(active)

    assert result["status"] == "CHANGED"
    assert result["username"] == USERNAME
    assert result["authority"] == "PLATFORM_ADMIN"
    assert result["state"] == "active"
    assert result["organization_public_id"] == active.public_id
    assert result["active_membership_count"] == 1
    assert result["audit_recorded"] is True

    actor = ExpertUser.query.filter_by(username=USERNAME).one()
    assert actor.is_active is True
    assert actor.role == "admin"
    assert effective_authority(actor) == "PLATFORM_ADMIN"
    assert bcrypt.checkpw(PASSWORD.encode(), actor.password_hash.encode())
    assert preserved_user.authority == "ORGANIZATION_ADMIN"

    memberships = OperationalMembership.query.filter_by(user_id=actor.id).all()
    assert len(memberships) == 1
    assert memberships[0].organization_id == active.id
    assert memberships[0].is_active is True
    assert memberships[0].permissions == [ORGANIZATION_ADMIN_PERMISSION]

    audits = _audit_rows(actor.id)
    assert [audit.action for audit in audits] == sorted(PROVISION_ACTIONS)
    assert {audit.metadata_json["governance_fact"] for audit in audits} == {
        "actor_creation",
        "authority_assignment",
        "organization_membership_assignment",
    }
    for audit in audits:
        assert audit.recorded_at is not None
        assert audit.organization_id == active.id
        assert audit.metadata_json["target_actor_id"] == actor.id
        assert audit.metadata_json["target_actor_username"] == USERNAME
        assert audit.metadata_json["target_authority"] == "PLATFORM_ADMIN"
        assert audit.metadata_json["organization_public_id"] == active.public_id
        assert audit.metadata_json["operator"] == OPERATOR
        assert audit.metadata_json["approval_reference"] == APPROVAL
        assert audit.metadata_json["resulting_state"] == "active"
        assert PASSWORD not in json.dumps(audit.metadata_json, sort_keys=True)


def test_logically_equivalent_retry_is_unchanged_without_side_effects(
    provisioning_context,
):
    _app, active, _inactive, _preserved = provisioning_context

    first = _provision(active)
    second = _provision(active)

    assert first["status"] == "CHANGED"
    assert second["status"] == "UNCHANGED"
    assert second["audit_recorded"] is False
    assert ExpertUser.query.filter_by(username=USERNAME).count() == 1
    actor = ExpertUser.query.filter_by(username=USERNAME).one()
    assert OperationalMembership.query.filter_by(user_id=actor.id).count() == 1
    assert len(_audit_rows(actor.id)) == 3
    assert OperationalIdempotency.query.filter_by(
        operation=PROVISION_OPERATION
    ).count() == 1


def test_inactive_organization_is_refused_without_identity(provisioning_context):
    _app, _active, inactive, _preserved = provisioning_context

    with pytest.raises(PlatformAdminProvisioningError) as exc_info:
        _provision(inactive)

    assert exc_info.value.code == "ORGANIZATION_INACTIVE"
    assert ExpertUser.query.filter_by(username=USERNAME).count() == 0


def test_conflicting_existing_identity_is_not_repurposed(provisioning_context):
    _app, active, _inactive, _preserved = provisioning_context
    existing = ExpertUser(
        username=USERNAME,
        password_hash=hash_password(PASSWORD),
        full_name="Different Existing Identity",
        role="admin",
        authority="PLATFORM_ADMIN",
        is_active=True,
    )
    db.session.add(existing)
    db.session.commit()

    with pytest.raises(PlatformAdminProvisioningError) as exc_info:
        _provision(active)

    assert exc_info.value.code == "IDENTITY_CONFLICT"
    assert existing.full_name == "Different Existing Identity"
    assert OperationalMembership.query.filter_by(user_id=existing.id).count() == 0


def test_conflicting_authority_is_not_elevated(provisioning_context):
    _app, active, _inactive, _preserved = provisioning_context
    existing = ExpertUser(
        username=USERNAME,
        password_hash=hash_password(PASSWORD),
        full_name=FULL_NAME,
        role="expert",
        authority="EXPERT",
        is_active=True,
    )
    db.session.add(existing)
    db.session.commit()

    with pytest.raises(PlatformAdminProvisioningError) as exc_info:
        _provision(active)

    assert exc_info.value.code == "AUTHORITY_CONFLICT"
    assert existing.authority == "EXPERT"
    assert OperationalMembership.query.filter_by(user_id=existing.id).count() == 0


def test_conflicting_membership_is_not_reassigned(provisioning_context):
    _app, active, inactive, _preserved = provisioning_context
    existing = ExpertUser(
        username=USERNAME,
        password_hash=hash_password(PASSWORD),
        full_name=FULL_NAME,
        role="admin",
        authority="PLATFORM_ADMIN",
        is_active=True,
    )
    db.session.add(existing)
    db.session.flush()
    membership = OperationalMembership(
        organization_id=inactive.id,
        user_id=existing.id,
        is_active=True,
        permissions=[ORGANIZATION_ADMIN_PERMISSION],
    )
    db.session.add(membership)
    db.session.commit()

    with pytest.raises(PlatformAdminProvisioningError) as exc_info:
        _provision(active)

    assert exc_info.value.code == "MEMBERSHIP_CONFLICT"
    assert membership.organization_id == inactive.id
    assert OperationalMembership.query.filter_by(user_id=existing.id).count() == 1


@pytest.mark.parametrize(
    "approval_reference",
    ["", " contains spaces ", "bad#reference", "x" * 201],
)
def test_malformed_approval_reference_is_refused(
    provisioning_context, approval_reference
):
    _app, active, _inactive, _preserved = provisioning_context

    with pytest.raises(PlatformAdminProvisioningError) as exc_info:
        _provision(active, approval_reference=approval_reference)

    assert exc_info.value.code == "APPROVAL_REFERENCE_INVALID"
    assert ExpertUser.query.filter_by(username=USERNAME).count() == 0


def test_bootstrap_trust_failure_is_refused_before_writes(provisioning_context):
    _app, active, _inactive, _preserved = provisioning_context

    with pytest.raises(PlatformAdminProvisioningError) as exc_info:
        _provision(active, bootstrap_authorized=False)

    assert exc_info.value.code == "BOOTSTRAP_TRUST_REQUIRED"
    assert ExpertUser.query.filter_by(username=USERNAME).count() == 0
    assert OperationalAudit.query.count() == 0
    assert OperationalIdempotency.query.count() == 0


def test_transaction_failure_rolls_back_every_provisioning_fact(
    provisioning_context, monkeypatch
):
    _app, active, _inactive, _preserved = provisioning_context

    def fail_commit():
        raise SQLAlchemyError("synthetic commit failure")

    monkeypatch.setattr(db.session, "commit", fail_commit)
    with pytest.raises(PlatformAdminProvisioningError) as exc_info:
        _provision(active)

    assert exc_info.value.code == "PERSISTENCE_FAILED"
    assert ExpertUser.query.filter_by(username=USERNAME).count() == 0
    assert OperationalMembership.query.join(ExpertUser).filter(
        ExpertUser.username == USERNAME
    ).count() == 0
    assert OperationalAudit.query.count() == 0
    assert OperationalIdempotency.query.count() == 0


def test_no_unrelated_product_mutation(provisioning_context):
    _app, active, _inactive, preserved_user = provisioning_context
    before = {
        "preserved_user": (
            preserved_user.full_name,
            preserved_user.authority,
            preserved_user.is_active,
        ),
        "shipment_requests": ShipmentRequest.query.count(),
        "shipments": OperationalShipment.query.count(),
        "route_plans": RoutePlan.query.count(),
        "organizations": OperationalOrganization.query.count(),
    }

    _provision(active)

    db.session.refresh(preserved_user)
    after = {
        "preserved_user": (
            preserved_user.full_name,
            preserved_user.authority,
            preserved_user.is_active,
        ),
        "shipment_requests": ShipmentRequest.query.count(),
        "shipments": OperationalShipment.query.count(),
        "route_plans": RoutePlan.query.count(),
        "organizations": OperationalOrganization.query.count(),
    }
    assert after == before


def test_cli_requires_confirmation_before_application_or_database_access(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        "backend.operational_cli.create_app",
        lambda **_kwargs: pytest.fail("application must not open without confirmation"),
    )
    exit_code = operational_cli_main(
        [
            "provision-platform-maintenance-admin",
            "--username",
            USERNAME,
            "--full-name",
            FULL_NAME,
            "--organization-public-id",
            "00000000-0000-0000-0000-000000000001",
            "--operator",
            OPERATOR,
            "--approval-reference",
            APPROVAL,
        ]
    )

    assert exit_code == 2
    assert "--confirm" in capsys.readouterr().err


def test_cli_reads_password_from_environment_without_disclosing_it(
    provisioning_context, monkeypatch, capsys
):
    app, active, _inactive, _preserved = provisioning_context
    monkeypatch.setenv("FORWARDER_PLATFORM_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setattr("backend.operational_cli.create_app", lambda **_kwargs: app)

    exit_code = operational_cli_main(
        [
            "provision-platform-maintenance-admin",
            "--username",
            USERNAME,
            "--full-name",
            FULL_NAME,
            "--organization-public-id",
            active.public_id,
            "--operator",
            OPERATOR,
            "--approval-reference",
            APPROVAL,
            "--confirm",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert json.loads(captured.out)["status"] == "CHANGED"
    assert PASSWORD not in captured.out
    assert PASSWORD not in captured.err
