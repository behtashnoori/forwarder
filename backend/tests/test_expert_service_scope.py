"""Expert service-scope eligibility and validation tests."""
import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.referral_engine import ReferralEngine
from backend.services import assignment_service, user_service
from backend.operational_models import OperationalMembership, OperationalOrganization


@pytest.fixture
def scope_app():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test"},
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode()
        experts = [
            ExpertUser(username="dom", password_hash=password_hash, full_name="Domestic", role="expert",
                       is_active=True, can_handle_domestic=True, can_handle_international=False),
            ExpertUser(username="intl", password_hash=password_hash, full_name="International", role="expert",
                       is_active=True, can_handle_domestic=False, can_handle_international=True),
            ExpertUser(username="hybrid", password_hash=password_hash, full_name="Hybrid", role="business_expert",
                       is_active=True, can_handle_domestic=True, can_handle_international=True),
            ExpertUser(username="inactive", password_hash=password_hash, full_name="Inactive", role="expert",
                       is_active=False, can_handle_domestic=True, can_handle_international=True),
        ]
        db.session.add_all(experts)
        organization=OperationalOrganization(public_id="scope-org",name="Scope Org",is_active=True)
        db.session.add(organization);db.session.flush()
        db.session.add_all([OperationalMembership(organization_id=organization.id,user_id=expert.id,is_active=True,permissions=[]) for expert in experts])
        db.session.commit()
        app.config["SCOPE_ORG_ID"]=organization.id
        yield app
        db.session.remove()
        db.drop_all()


def _request(shipping_type: str, code: str) -> ShipmentRequest:
    from flask import current_app
    row = ShipmentRequest(
        tracking_code=code,
        shipping_type=shipping_type,
        contact_phone="09120000000",
        status="new",
        status_request_status="new",
        ownership_scope="TENANT",
        operational_organization_id=current_app.config["SCOPE_ORG_ID"],
    )
    db.session.add(row)
    db.session.commit()
    return row


def test_automatic_assignment_filters_scope_before_round_robin(scope_app):
    with scope_app.app_context():
        domestic = _request("domestic", "SCOPE-D")
        selected = ReferralEngine(db.session).auto_assign_request(domestic.id)
        assert db.session.get(ExpertUser, selected).username in {"dom", "hybrid"}

        international = _request("international", "SCOPE-I")
        selected = ReferralEngine(db.session).auto_assign_request(international.id)
        assert db.session.get(ExpertUser, selected).username in {"intl", "hybrid"}


def test_no_eligible_expert_leaves_request_unassigned(scope_app):
    with scope_app.app_context():
        for expert in ExpertUser.query.all():
            expert.can_handle_international = False
        db.session.commit()
        request_row = _request("international", "SCOPE-NONE")
        assert ReferralEngine(db.session).auto_assign_request(request_row.id) is None
        db.session.refresh(request_row)
        assert request_row.assigned_to is None
        assert request_row.status == "new"


def test_manual_assignment_rejects_incompatible_expert(scope_app):
    with scope_app.app_context():
        request_row = _request("international", "SCOPE-M")
        domestic = ExpertUser.query.filter_by(username="dom").one()
        with pytest.raises(assignment_service.AssignmentValidationError):
            assignment_service.assign_request_to_expert(
                request_row.id, domestic.id, actor={"id": 999, "role": "admin"}
            )
        assert request_row.assigned_to is None


def test_active_expert_requires_at_least_one_scope(scope_app):
    with scope_app.app_context():
        with pytest.raises(user_service.UserValidationError):
            user_service.update_user(
                ExpertUser.query.filter_by(username="dom").one().id,
                {"can_handle_domestic": False, "can_handle_international": False},
            )


def test_existing_expert_defaults_to_hybrid(scope_app):
    with scope_app.app_context():
        password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode()
        expert = ExpertUser(
            username="legacy", password_hash=password_hash, full_name="Legacy",
            role="expert", is_active=True,
        )
        db.session.add(expert)
        db.session.commit()
        assert expert.can_handle_domestic is True
        assert expert.can_handle_international is True
