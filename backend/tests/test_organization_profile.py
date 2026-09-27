import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalAudit, OperationalMembership, OperationalOrganization
from backend.organization_profile import ProfileApplyError, apply_profile, load_profile, plan_profile
from backend.reference_data_cli import main as cli_main
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationPackagingTypeActivation,
    OrganizationTransportEquipmentTypeActivation,
    OrganizationTransportMeansTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from backend.reference_data_catalog import apply_catalog, load_catalog


@pytest.fixture()
def context():
    app = create_app({
        "TESTING": True,
        "APP_ENV": "testing",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "organization-profile-test",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        organization = OperationalOrganization(name="Profile Organization")
        admin = ExpertUser(
            username="profile-admin",
            password_hash="x",
            full_name="Profile Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        foreign = ExpertUser(
            username="foreign-admin",
            password_hash="x",
            full_name="Foreign Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        other = OperationalOrganization(name="Other Organization")
        db.session.add_all([organization, other, admin, foreign])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=organization.id, user_id=admin.id, permissions=[]),
            OperationalMembership(organization_id=other.id, user_id=foreign.id, permissions=[]),
        ])
        db.session.commit()
        yield app, organization
        db.session.remove()
        db.drop_all()


def _apply_catalog():
    catalog = load_catalog()
    plan, run = apply_catalog(
        catalog,
        environment="testing",
        executed_by="qa.operator",
        approval_reference="ADMIN-FOUNDATIONS",
        expected_checksum=catalog.checksum,
    )
    assert run.status == "succeeded" and plan.conflict_count == 0
    return catalog


def test_profile_plan_apply_is_explicit_idempotent_and_audited(context):
    _application, organization = context
    catalog = _apply_catalog()
    profile = load_profile(catalog=catalog)
    plan = plan_profile(
        profile,
        organization_public_id=organization.public_id,
        actor_username="profile-admin",
    )
    assert plan.planned_count == 60
    assert (plan.created_count, plan.unchanged_count, plan.conflict_count) == (60, 0, 0)
    assert plan.verified_global_transport_methods == 7
    assert OperationalAudit.query.count() == 0

    applied = apply_profile(
        profile,
        organization_public_id=organization.public_id,
        actor_username="profile-admin",
        operator="qa.operator",
        approval_reference="ADMIN-FOUNDATIONS",
        expected_checksum=profile.checksum,
    )
    assert applied.conflict_count == 0
    assert (
        OrganizationCargoTypeActivation.query.count(),
        OrganizationUnitOfMeasureActivation.query.count(),
        OrganizationPackagingTypeActivation.query.count(),
        OrganizationTransportMeansTypeActivation.query.count(),
        OrganizationTransportEquipmentTypeActivation.query.count(),
    ) == (14, 10, 9, 4, 23)
    assert OperationalAudit.query.filter_by(action="ORGANIZATION_REFERENCE_ACTIVE").count() == 60

    repeated = apply_profile(
        profile,
        organization_public_id=organization.public_id,
        actor_username="profile-admin",
        operator="qa.operator",
        approval_reference="ADMIN-FOUNDATIONS",
        expected_checksum=profile.checksum,
    )
    assert (repeated.created_count, repeated.unchanged_count, repeated.conflict_count) == (0, 60, 0)
    assert OperationalAudit.query.filter_by(action="ORGANIZATION_REFERENCE_ACTIVE").count() == 60


def test_profile_requires_explicit_audited_reactivation_for_inactive_history(context):
    _application, organization = context
    catalog = _apply_catalog()
    profile = load_profile(catalog=catalog)
    with pytest.raises(ProfileApplyError, match="same-tenant"):
        plan_profile(
            profile,
            organization_public_id=organization.public_id,
            actor_username="foreign-admin",
        )

    apply_profile(
        profile,
        organization_public_id=organization.public_id,
        actor_username="profile-admin",
        operator="qa.operator",
        approval_reference="ADMIN-FOUNDATIONS",
        expected_checksum=profile.checksum,
    )
    row = OrganizationUnitOfMeasureActivation.query.first()
    row.status = "INACTIVE"
    row.version += 1
    db.session.commit()
    plan = plan_profile(
        profile,
        organization_public_id=organization.public_id,
        actor_username="profile-admin",
    )
    assert plan.conflict_count == 0
    assert plan.reactivation_count == 1
    assert "explicit governed reactivation" in plan.reactivations[0]["reason"]
    with pytest.raises(ProfileApplyError, match="explicit reactivation confirmation"):
        apply_profile(
            profile,
            organization_public_id=organization.public_id,
            actor_username="profile-admin",
            operator="qa.operator",
            approval_reference="ADMIN-FOUNDATIONS",
            expected_checksum=profile.checksum,
        )
    assert row.status == "INACTIVE"
    assert row.version == 2

    applied = apply_profile(
        profile,
        organization_public_id=organization.public_id,
        actor_username="profile-admin",
        operator="qa.operator",
        approval_reference="ADMIN-FOUNDATIONS",
        expected_checksum=profile.checksum,
        confirm_reactivation=True,
    )
    assert applied.reactivation_count == 1
    assert row.status == "ACTIVE"
    assert row.version == 3
    audit = OperationalAudit.query.filter_by(
        action="ORGANIZATION_REFERENCE_ACTIVE",
        entity_type=type(row).__name__,
        entity_id=row.id,
    ).order_by(OperationalAudit.id.desc()).first()
    assert audit.metadata_json["previous_state"] == "INACTIVE"
    assert audit.metadata_json["current_state"] == "ACTIVE"

    repeated = plan_profile(
        profile,
        organization_public_id=organization.public_id,
        actor_username="profile-admin",
    )
    assert (repeated.created_count, repeated.reactivation_count, repeated.unchanged_count) == (0, 0, 60)


def test_profile_cli_plan_apply_and_safe_rerun(context, capsys):
    application, organization = context
    catalog = _apply_catalog()
    profile = load_profile(catalog=catalog)
    common = [
        "--organization-public-id", organization.public_id,
        "--actor-username", "profile-admin",
    ]
    assert cli_main(["organization-profile-plan", *common], app=application) == 0
    plan_output = capsys.readouterr().out
    assert '"created_count": 60' in plan_output
    assert '"conflict_count": 0' in plan_output

    assert cli_main([
        "organization-profile-apply", *common, "--confirm",
        "--operator", "qa.operator", "--approval-reference", "ADMIN-FOUNDATIONS",
        "--expected-checksum", profile.checksum,
    ], app=application) == 0
    assert '"status": "SUCCEEDED"' in capsys.readouterr().out

    assert cli_main(["organization-profile-plan", *common], app=application) == 0
    repeated_output = capsys.readouterr().out
    assert '"created_count": 0' in repeated_output
    assert '"unchanged_count": 60' in repeated_output
