"""Characterization tests for user management route contracts."""
from __future__ import annotations

import json
from datetime import datetime

import bcrypt
import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend import create_app
from backend.extensions import db
from backend.models import (
    Activity,
    AssignmentLog,
    AssignmentRule,
    CRMCustomerLinkAudit,
    Customer,
    ExpertConsoleLog,
    ExpertConsoleMessage,
    ExpertConsoleNotification,
    ExpertQuote,
    ExpertSpecialization,
    ExpertUser,
    Opportunity,
    ReferralAssignmentLog,
    ReferralRule,
    ReferralRuleState,
    Report,
    ShipmentRequest,
    Task,
    TransportMethod,
)
from backend.security import security
from backend.services.auth_session_service import create_session_tokens
from backend.services import assignment_service, user_delete_service
from backend.operational_models import OperationalMembership, OperationalOrganization


@pytest.fixture
def user_management_app():
    """App with isolated DB and user-management seed data."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
        admin = ExpertUser(
            username="phase5b_admin",
            password_hash=password_hash,
            full_name="Phase 5B Admin",
            email="phase5b-admin@example.test",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        expert = ExpertUser(
            username="phase5b_expert",
            password_hash=password_hash,
            full_name="Phase 5B Expert",
            email="phase5b-expert@example.test",
            role="expert",
            department="operations",
            is_active=True,
        )
        other_expert = ExpertUser(
            username="phase5b_other",
            password_hash=password_hash,
            full_name="Phase 5B Other",
            email="phase5b-other@example.test",
            role="business_expert",
            is_active=True,
        )
        db.session.add_all([admin, expert, other_expert])
        db.session.flush()
        organization = OperationalOrganization(public_id="um-org-a", name="Organization A", is_active=True)
        db.session.add(organization)
        db.session.flush()
        db.session.add_all([OperationalMembership(organization_id=organization.id, user_id=user.id, is_active=True, permissions=[]) for user in (admin, expert, other_expert)])

        road = TransportMethod(
            name="road",
            name_fa="Road",
            description="Road transport",
            is_active=True,
        )
        air = TransportMethod(
            name="air",
            name_fa="Air",
            description="Air transport",
            is_active=True,
        )
        inactive = TransportMethod(
            name="rail",
            name_fa="Rail",
            description="Inactive rail",
            is_active=False,
        )
        db.session.add_all([road, air, inactive])
        db.session.flush()

        specialization = ExpertSpecialization(
            expert_user_id=expert.id,
            transport_method_id=road.id,
            proficiency_level="advanced",
            is_primary=True,
        )
        assigned_request = ShipmentRequest(
            tracking_code="UM-P5B-001",
            shipping_type="domestic",
            contact_phone="09123456789",
            customer_first_name="Ali",
            customer_last_name="Rahimi",
            transport_method="road",
            domestic_transport_method="road",
            status_request_status="new",
            status="assigned",
            assigned_to=expert.id,
            operational_organization_id=organization.id,
            ownership_scope="TENANT",
        )
        high_rule = AssignmentRule(
            name="High priority",
            description="High priority rule",
            rule_type="priority",
            conditions=json.dumps({"priority": "high"}),
            priority=10,
            is_active=True,
            created_by=admin.id,
            operational_organization_id=organization.id,
        )
        low_rule = AssignmentRule(
            name="Low workload",
            description="Low workload rule",
            rule_type="workload",
            conditions=json.dumps({"max_workload": 4}),
            priority=2,
            is_active=False,
            created_by=admin.id,
            operational_organization_id=organization.id,
        )
        db.session.add_all([specialization, assigned_request, high_rule, low_rule])
        db.session.commit()

        return {
            "app": app,
            "admin_id": admin.id,
            "expert_id": expert.id,
            "other_expert_id": other_expert.id,
            "road_id": road.id,
            "air_id": air.id,
            "request_id": assigned_request.id,
            "high_rule_id": high_rule.id,
            "low_rule_id": low_rule.id,
            "admin_token": create_session_tokens(admin.id)["access_token"],
            "expert_token": create_session_tokens(expert.id)["access_token"],
        }


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_auth_role_requirements_and_read_shapes(user_management_app):
    """Admin-only user-management reads keep auth, forbidden, and response shapes."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])
    expert_headers = _auth_headers(user_management_app["expert_token"])

    unauthenticated = client.get("/api/user-management/users")
    assert unauthenticated.status_code == 401
    assert unauthenticated.get_json() == {"error": "Token is missing"}

    forbidden = client.get("/api/user-management/users", headers=expert_headers)
    assert forbidden.status_code == 403
    assert forbidden.get_json() == {
        "error": "دسترسی غیرمجاز",
        "required_roles": ["admin"],
        "user_role": "expert",
    }

    users_response = client.get("/api/user-management/users", headers=admin_headers)
    assert users_response.status_code == 200
    users_payload = users_response.get_json()
    assert set(users_payload.keys()) == {"users"}
    assert [user["full_name"] for user in users_payload["users"]] == [
        "Phase 5B Admin",
        "Phase 5B Expert",
        "Phase 5B Other",
    ]
    expert_payload = next(user for user in users_payload["users"] if user["id"] == user_management_app["expert_id"])
    assert set(expert_payload.keys()) == {
        "id",
        "username",
        "full_name",
        "email",
        "phone",
        "role",
        "department",
            "is_active",
                "can_handle_domestic",
                "can_handle_international",
                "sla_response_work_minutes",
                "created_at",
        "last_login_at",
        "manager",
        "subordinates_count",
        "specializations",
        "workload",
    }
    assert expert_payload["specializations"] == [
        {
            "id": expert_payload["specializations"][0]["id"],
            "transport_method": {"id": user_management_app["road_id"], "name": "Road"},
            "proficiency_level": "advanced",
            "is_primary": True,
        }
    ]
    assert expert_payload["workload"] == 1

    transport_response = client.get("/api/user-management/transport-methods", headers=admin_headers)
    assert transport_response.status_code == 200
    assert transport_response.get_json()["transport_methods"] == [
        {
            "id": user_management_app["air_id"],
            "name": "air",
            "name_fa": "Air",
            "description": "Air transport",
            "is_active": True,
            "created_at": transport_response.get_json()["transport_methods"][0]["created_at"],
        },
        {
            "id": user_management_app["road_id"],
            "name": "road",
            "name_fa": "Road",
            "description": "Road transport",
            "is_active": True,
            "created_at": transport_response.get_json()["transport_methods"][1]["created_at"],
        },
    ]

    invalid_create = client.post("/api/user-management/transport-methods", headers=admin_headers, json={})
    assert invalid_create.status_code == 500
    assert invalid_create.get_json() == {"error": "خطا در ایجاد روش حمل"}

    create_transport = client.post(
        "/api/user-management/transport-methods",
        headers=admin_headers,
        json={
            "name": "sea",
            "name_fa": "Sea",
            "description": "Sea transport",
            "is_active": False,
        },
    )
    assert create_transport.status_code == 201
    create_payload = create_transport.get_json()
    assert set(create_payload.keys()) == {"message", "transport_method_id"}
    assert create_payload["message"] == "روش حمل با موفقیت ایجاد شد"

    with user_management_app["app"].app_context():
        created_method = db.session.get(TransportMethod, create_payload["transport_method_id"])
        assert created_method is not None
        assert created_method.name == "sea"
        assert created_method.name_fa == "Sea"
        assert created_method.description == "Sea transport"
        assert created_method.is_active is False

    ping_response = client.get("/api/user-management/ping")
    assert ping_response.status_code == 200
    assert ping_response.get_json() == {"message": "User Management API is running"}


def test_user_create_update_not_found_and_persistence_contracts(user_management_app):
    """User create/update keeps current validation, status codes, payloads, and commits."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])

    missing_username = client.post("/api/user-management/users", headers=admin_headers, json={})
    assert missing_username.status_code == 400
    assert missing_username.get_json() == {"error": "نام کاربری الزامی است"}

    duplicate_username = client.post(
        "/api/user-management/users",
        headers=admin_headers,
        json={
            "username": "phase5b_expert",
            "password": "test123",
            "full_name": "Duplicate",
            "role": "expert",
        },
    )
    assert duplicate_username.status_code == 400
    assert duplicate_username.get_json() == {"error": "نام کاربری قبلاً استفاده شده است"}

    create_response = client.post(
        "/api/user-management/users",
        headers=admin_headers,
        json={
            "username": "phase5b_created",
            "password": "test123",
            "full_name": "Phase 5B Created",
            "email": " CREATED@EXAMPLE.TEST ",
            "phone": " 09120000000 ",
            "role": "expert",
            "department": " sales ",
            "manager_id": user_management_app["admin_id"],
            "sla_response_work_minutes": 90,
            "specializations": [
                {
                    "transport_method_id": user_management_app["air_id"],
                    "proficiency_level": "intermediate",
                    "is_primary": False,
                }
            ],
        },
    )
    assert create_response.status_code == 201
    create_payload = create_response.get_json()
    assert set(create_payload.keys()) == {"message", "user_id"}
    assert create_payload["message"] == "کاربر با موفقیت ایجاد شد"

    with user_management_app["app"].app_context():
        created = db.session.get(ExpertUser, create_payload["user_id"])
        assert created is not None
        assert created.password_hash != "test123"
        assert bcrypt.checkpw(b"test123", created.password_hash.encode("utf-8"))
        assert created.email == "created@example.test"
        assert created.phone == "09120000000"
        assert created.department == "sales"
        assert created.sla_response_work_minutes == 90
        assert len(created.specializations) == 1
        assert created.specializations[0].transport_method_id == user_management_app["air_id"]

    duplicate_email = client.post(
        "/api/user-management/users",
        headers=admin_headers,
        json={
            "username": "phase5b_duplicate_email",
            "password": "test123",
            "full_name": "Duplicate Email",
            "email": "created@example.test",
            "role": "expert",
        },
    )
    assert duplicate_email.status_code == 409
    assert duplicate_email.get_json() == {"error": "ایمیل تکراری است یا قبلاً استفاده شده است."}

    missing_update = client.put(
        "/api/user-management/users/999999",
        headers=admin_headers,
        json={"full_name": "Missing"},
    )
    assert missing_update.status_code == 404
    assert missing_update.get_json() == {"error": "کاربر یافت نشد"}

    update_response = client.put(
        f"/api/user-management/users/{create_payload['user_id']}",
        headers=admin_headers,
        json={
            "username": "phase5b_created_updated",
            "full_name": "Phase 5B Created Updated",
            "role": "business_expert",
            "department": "crm",
            "is_active": False,
            "manager_id": None,
            "sla_response_work_minutes": 45,
            "specializations": [
                {
                    "transport_method_id": user_management_app["road_id"],
                    "proficiency_level": "expert",
                    "is_primary": True,
                }
            ],
        },
    )
    assert update_response.status_code == 200
    assert update_response.get_json() == {"message": "اطلاعات کاربر به‌روزرسانی شد"}

    with user_management_app["app"].app_context():
        updated = db.session.get(ExpertUser, create_payload["user_id"])
        assert updated.username == "phase5b_created_updated"
        assert updated.full_name == "Phase 5B Created Updated"
        assert updated.role == "business_expert"
        assert updated.department == "crm"
        assert updated.is_active is False
        assert updated.manager_id is None
        assert updated.sla_response_work_minutes == 45
        assert len(updated.specializations) == 1
        assert updated.specializations[0].transport_method_id == user_management_app["road_id"]
        assert updated.specializations[0].proficiency_level == "expert"
        assert updated.specializations[0].is_primary is True


@pytest.mark.parametrize(
    "value",
    [0, -1, 10081, 1.5, "not-a-number", True, False],
)
def test_sla_update_rejects_invalid_values(user_management_app, value):
    client = user_management_app["app"].test_client()
    response = client.put(
        f"/api/user-management/users/{user_management_app['expert_id']}",
        headers=_auth_headers(user_management_app["admin_token"]),
        json={"sla_response_work_minutes": value},
    )
    assert response.status_code == 400
    with user_management_app["app"].app_context():
        assert (
            db.session.get(ExpertUser, user_management_app["expert_id"])
            .sla_response_work_minutes
            == 120
        )


def test_sla_default_response_authorization_and_historical_deadline(user_management_app):
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])
    expert_headers = _auth_headers(user_management_app["expert_token"])

    create_response = client.post(
        "/api/user-management/users",
        headers=admin_headers,
        json={
            "username": "sla_default_expert",
            "password": "test123",
            "full_name": "SLA Default Expert",
            "role": "expert",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.get_json()["user_id"]

    list_response = client.get("/api/user-management/users", headers=admin_headers)
    created_payload = next(
        user for user in list_response.get_json()["users"] if user["id"] == created_id
    )
    assert created_payload["sla_response_work_minutes"] == 120

    forbidden = client.put(
        f"/api/user-management/users/{created_id}",
        headers=expert_headers,
        json={"sla_response_work_minutes": 30},
    )
    assert forbidden.status_code == 403

    with user_management_app["app"].app_context():
        request_row = db.session.get(
            ShipmentRequest, user_management_app["request_id"]
        )
        request_row.sla_due_at = datetime(2026, 7, 27, 8, 30)
        db.session.commit()

    valid = client.put(
        f"/api/user-management/users/{created_id}",
        headers=admin_headers,
        json={"sla_response_work_minutes": 30},
    )
    assert valid.status_code == 200
    with user_management_app["app"].app_context():
        assert db.session.get(ExpertUser, created_id).sla_response_work_minutes == 30
        assert db.session.get(
            ShipmentRequest, user_management_app["request_id"]
        ).sla_due_at == datetime(2026, 7, 27, 8, 30)


def test_user_delete_cleanup_and_hard_delete_contract(user_management_app):
    """Hard delete removes owned rows and clears only nullable references."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])
    expert_id = user_management_app["expert_id"]

    delete_self = client.delete(f"/api/user-management/users/{user_management_app['admin_id']}", headers=admin_headers)
    assert delete_self.status_code == 400
    assert delete_self.get_json() == {"error": "امکان حذف حساب خودتان وجود ندارد"}

    missing_delete = client.delete("/api/user-management/users/999999", headers=admin_headers)
    assert missing_delete.status_code == 404
    assert missing_delete.get_json() == {"error": "کاربر یافت نشد"}

    with user_management_app["app"].app_context():
        protected_admin = ExpertUser(
            username="phase5b_protected_admin",
            password_hash=bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8"),
            full_name="Phase 5B Protected Admin",
            email="phase5b-protected-admin@example.test",
            role="admin",
            is_active=True,
        )
        db.session.add(protected_admin)
        db.session.commit()
        protected_admin_id = protected_admin.id

    delete_admin = client.delete(f"/api/user-management/users/{protected_admin_id}", headers=admin_headers)
    assert delete_admin.status_code == 400
    assert delete_admin.get_json() == {"error": "امکان حذف کاربر با نقش مدیر وجود ندارد"}

    with user_management_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, user_management_app["request_id"])
        user_rule = AssignmentRule(
            name="Expert-created rule",
            description="Rule owned by expert",
            rule_type="priority",
            conditions=json.dumps({"priority": "urgent"}),
            priority=4,
            is_active=True,
            created_by=expert_id,
        )
        subordinate = ExpertUser(
            username="phase5b_subordinate",
            password_hash=bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8"),
            full_name="Phase 5B Subordinate",
            email="phase5b-subordinate@example.test",
            role="expert",
            manager_id=expert_id,
            is_active=True,
        )
        log = ExpertConsoleLog(
            shipment_request_id=request_row.id,
            expert_user_id=expert_id,
            action="seed",
            note="Seed log",
        )
        message = ExpertConsoleMessage(
            shipment_request_id=request_row.id,
            expert_user_id=expert_id,
            message_type="internal_note",
            content="Seed message",
        )
        notification = ExpertConsoleNotification(
            shipment_request_id=request_row.id,
            expert_user_id=expert_id,
            notification_type="seed",
            title="Seed notification",
            message="Seed notification",
        )
        activity = Activity(
            shipment_request_id=request_row.id,
            expert_user_id=expert_id,
            activity_type="note",
            subject="Seed activity",
        )
        task = Task(title="Seed task", assigned_to=expert_id, created_by=expert_id)
        report = Report(name="Seed report", report_type="activity", created_by=expert_id)
        customer = Customer(
            first_name="Phase 5B",
            last_name="Customer",
            email="phase5b-customer@example.test",
        )
        db.session.add(customer)
        db.session.flush()
        opportunity = Opportunity(
            customer_id=customer.id,
            title="Seed opportunity",
            stage="qualified",
            assigned_to=expert_id,
        )
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            amount=125000,
            currency="IRR",
            created_by_expert_id=expert_id,
        )
        crm_audit = CRMCustomerLinkAudit(
            shipment_request_id=request_row.id,
            operation="link",
            performed_by_user_id=expert_id,
            performed_by_role="expert",
            source="test",
        )
        referral_rule = ReferralRule(
            name="Expert-owned referral rule",
            conditions=json.dumps({}),
            action=json.dumps({"type": "direct_assign", "expert_id": expert_id}),
            created_by=expert_id,
        )
        db.session.add_all([
            user_rule,
            subordinate,
            log,
            message,
            notification,
            activity,
            task,
            report,
            opportunity,
            quote,
            crm_audit,
            referral_rule,
        ])
        db.session.flush()
        assignment_log = AssignmentLog(
            shipment_request_id=request_row.id,
            assigned_expert_id=expert_id,
            assignment_rule_id=user_rule.id,
            assignment_method="automatic",
            assignment_reason="Seed assignment",
        )
        preserved_assignment_log = AssignmentLog(
            shipment_request_id=request_row.id,
            assigned_expert_id=user_management_app["other_expert_id"],
            assignment_rule_id=user_rule.id,
            assignment_method="automatic",
            assignment_reason="Preserved assignment history",
        )
        referral_state = ReferralRuleState(rule_id=referral_rule.id, rr_index=1)
        deleted_referral_log = ReferralAssignmentLog(
            request_id=request_row.id,
            rule_id=referral_rule.id,
            selected_expert_id=expert_id,
            strategy_used="direct",
        )
        preserved_referral_log = ReferralAssignmentLog(
            request_id=request_row.id,
            rule_id=referral_rule.id,
            selected_expert_id=user_management_app["other_expert_id"],
            strategy_used="direct",
        )
        db.session.add_all([
            assignment_log,
            preserved_assignment_log,
            referral_state,
            deleted_referral_log,
            preserved_referral_log,
        ])
        db.session.commit()
        user_rule_id = user_rule.id
        subordinate_id = subordinate.id
        opportunity_id = opportunity.id
        quote_id = quote.id
        crm_audit_id = crm_audit.id
        referral_rule_id = referral_rule.id
        deleted_referral_log_id = deleted_referral_log.id
        preserved_referral_log_id = preserved_referral_log.id
        preserved_assignment_log_id = preserved_assignment_log.id

    delete_response = client.delete(f"/api/user-management/users/{expert_id}", headers=admin_headers)
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {"message": "کاربر و تمام داده‌های مرتبط با موفقیت حذف شدند"}

    with user_management_app["app"].app_context():
        assert db.session.get(ExpertUser, expert_id) is None
        assert db.session.get(ExpertUser, subordinate_id).manager_id is None
        assert db.session.get(ShipmentRequest, user_management_app["request_id"]).assigned_to is None
        assert db.session.get(Opportunity, opportunity_id).assigned_to is None
        assert db.session.get(AssignmentRule, user_rule_id) is None
        assert db.session.get(AssignmentLog, preserved_assignment_log_id).assignment_rule_id is None
        assert db.session.get(ExpertQuote, quote_id) is None
        assert ExpertQuote.query.filter_by(created_by_expert_id=expert_id).count() == 0
        assert db.session.get(CRMCustomerLinkAudit, crm_audit_id).performed_by_user_id is None
        assert db.session.get(ReferralRule, referral_rule_id) is None
        assert ReferralRuleState.query.filter_by(rule_id=referral_rule_id).count() == 0
        assert db.session.get(ReferralAssignmentLog, deleted_referral_log_id) is None
        assert db.session.get(ReferralAssignmentLog, preserved_referral_log_id).rule_id is None
        assert ExpertSpecialization.query.filter_by(expert_user_id=expert_id).count() == 0
        assert AssignmentLog.query.filter_by(assigned_expert_id=expert_id).count() == 0
        assert ExpertConsoleLog.query.filter_by(expert_user_id=expert_id).count() == 0
        assert ExpertConsoleMessage.query.filter_by(expert_user_id=expert_id).count() == 0
        assert ExpertConsoleNotification.query.filter_by(expert_user_id=expert_id).count() == 0
        assert Activity.query.filter_by(expert_user_id=expert_id).count() == 0
        assert Task.query.filter(
            (Task.assigned_to == expert_id) | (Task.created_by == expert_id)
        ).count() == 0
        assert Report.query.filter_by(created_by=expert_id).count() == 0


def test_user_without_dependencies_is_permanently_deleted(user_management_app):
    """A plain non-admin user is removed rather than deactivated."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])

    with user_management_app["app"].app_context():
        plain_user = ExpertUser(
            username="plain_delete_user",
            password_hash=bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8"),
            full_name="Plain Delete User",
            role="expert",
            is_active=True,
        )
        db.session.add(plain_user)
        db.session.commit()
        plain_user_id = plain_user.id

    response = client.delete(
        f"/api/user-management/users/{plain_user_id}", headers=admin_headers
    )
    assert response.status_code == 200

    with user_management_app["app"].app_context():
        assert db.session.get(ExpertUser, plain_user_id) is None


def test_user_delete_failure_rolls_back_and_hides_database_details(
    user_management_app, monkeypatch
):
    """A mid-cleanup database error restores all rows and returns a safe error."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])
    expert_id = user_management_app["expert_id"]

    with user_management_app["app"].app_context():
        quote = ExpertQuote(
            shipment_request_id=user_management_app["request_id"],
            amount=250000,
            currency="IRR",
            created_by_expert_id=expert_id,
        )
        db.session.add(quote)
        db.session.commit()
        quote_id = quote.id

    def fail_after_related_cleanup(_target_user):
        raise SQLAlchemyError(
            'NotNullViolation expert_quote.created_by_expert_id params="secret"'
        )

    monkeypatch.setattr(
        user_delete_service, "cleanup_user_owned_rules", fail_after_related_cleanup
    )
    response = client.delete(
        f"/api/user-management/users/{expert_id}", headers=admin_headers
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "خطا در حذف کاربر"}
    assert "NotNullViolation" not in response.get_data(as_text=True)
    assert "expert_quote" not in response.get_data(as_text=True)

    with user_management_app["app"].app_context():
        assert db.session.get(ExpertUser, expert_id) is not None
        assert db.session.get(ExpertQuote, quote_id) is not None


def test_assignment_rule_crud_and_no_delete_endpoint_contract(user_management_app):
    """Assignment rule endpoints keep list order, create/update payloads, and no DELETE route."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])

    list_response = client.get("/api/user-management/assignment-rules", headers=admin_headers)
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert set(list_payload.keys()) == {"assignment_rules"}
    assert [rule["id"] for rule in list_payload["assignment_rules"]] == [
        user_management_app["high_rule_id"],
        user_management_app["low_rule_id"],
    ]
    first_rule = list_payload["assignment_rules"][0]
    assert set(first_rule.keys()) == {
        "id",
        "name",
        "description",
        "rule_type",
        "conditions",
        "priority",
        "is_active",
        "created_by",
        "created_at",
        "updated_at",
    }
    assert first_rule["conditions"] == {"priority": "high"}
    assert first_rule["created_by"] == {
        "id": user_management_app["admin_id"],
        "name": "Phase 5B Admin",
    }

    create_response = client.post(
        "/api/user-management/assignment-rules",
        headers=admin_headers,
        json={
            "name": "Created assignment rule",
            "description": "Created via characterization",
            "rule_type": "transport_method",
            "conditions": {"transport_method": "road"},
            "priority": 7,
            "is_active": True,
        },
    )
    assert create_response.status_code == 201
    create_payload = create_response.get_json()
    assert set(create_payload.keys()) == {"message", "rule_id"}
    assert create_payload["message"] == "قانون ارجاع با موفقیت ایجاد شد"

    missing_update = client.put(
        "/api/user-management/assignment-rules/999999",
        headers=admin_headers,
        json={"name": "Missing"},
    )
    assert missing_update.status_code == 404
    assert missing_update.get_json() == {"error": "قانون ارجاع یافت نشد"}

    update_response = client.put(
        f"/api/user-management/assignment-rules/{create_payload['rule_id']}",
        headers=admin_headers,
        json={
            "name": "Updated assignment rule",
            "conditions": {"transport_method": "air"},
            "priority": 8,
            "is_active": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.get_json() == {"message": "قانون ارجاع به‌روزرسانی شد"}

    delete_response = client.delete(
        f"/api/user-management/assignment-rules/{create_payload['rule_id']}",
        headers=admin_headers,
    )
    assert delete_response.status_code == 405
    assert delete_response.get_json() == {"error": "The method is not allowed for the requested URL."}

    with user_management_app["app"].app_context():
        created_rule = db.session.get(AssignmentRule, create_payload["rule_id"])
        assert created_rule.name == "Updated assignment rule"
        assert json.loads(created_rule.conditions) == {"transport_method": "air"}
        assert created_rule.priority == 8
        assert created_rule.is_active is False
        assert created_rule.created_by == user_management_app["admin_id"]
        assert isinstance(created_rule.updated_at, datetime)


def _legacy_assignment_statistics_and_manual_assignment_failure_contract(user_management_app, monkeypatch):
    """Stats read shape and preserved manual-assignment failure remain unchanged."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])

    stats_response = client.get("/api/user-management/assignment-statistics", headers=admin_headers)
    assert stats_response.status_code == 200
    stats_payload = stats_response.get_json()
    assert set(stats_payload.keys()) == {
        "total_assignments",
        "automatic_assignments",
        "manual_assignments",
        "expert_workloads",
    }
    assert stats_payload["total_assignments"] == 0
    assert stats_payload["automatic_assignments"] == 0
    assert stats_payload["manual_assignments"] == 0
    assert {item["expert_id"] for item in stats_payload["expert_workloads"]} == {
        user_management_app["admin_id"],
        user_management_app["expert_id"],
        user_management_app["other_expert_id"],
    }
    expert_workload = next(
        item for item in stats_payload["expert_workloads"] if item["expert_id"] == user_management_app["expert_id"]
    )
    assert expert_workload == {
        "expert_id": user_management_app["expert_id"],
        "expert_name": "Phase 5B Expert",
        "workload": 1,
    }

    manual_missing = client.post("/api/user-management/manual-assignment", headers=admin_headers, json={})
    assert manual_missing.status_code == 500
    assert manual_missing.get_json() == {"error": "خطا در ارجاع دستی"}

    manual_response = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={
            "request_id": user_management_app["request_id"],
            "expert_id": user_management_app["other_expert_id"],
            "reason": "Phase 5B manual",
        },
    )
    assert manual_response.status_code == 500
    assert manual_response.get_json() == {"error": "خطا در ارجاع دستی"}

    with user_management_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, user_management_app["request_id"])
        assert request_row.assigned_to == user_management_app["expert_id"]
        assert request_row.status == "assigned"
        assert AssignmentLog.query.filter_by(shipment_request_id=user_management_app["request_id"]).count() == 0
        assert ExpertConsoleLog.query.filter_by(
            shipment_request_id=user_management_app["request_id"],
            action="assignment",
        ).count() == 0
        assert ExpertConsoleNotification.query.filter_by(
            shipment_request_id=user_management_app["request_id"],
            notification_type="assignment",
        ).count() == 0

    def fail_after_staged_assignment_log() -> None:
        db.session.add(
            AssignmentLog(
                shipment_request_id=user_management_app["request_id"],
                assigned_expert_id=user_management_app["other_expert_id"],
                assignment_method="manual",
                assignment_reason="rollback probe",
            )
        )
        db.session.flush()
        raise RuntimeError("manual assignment staged rollback probe")

    monkeypatch.setattr(
        assignment_service,
        "preserve_manual_assignment_failure",
        fail_after_staged_assignment_log,
    )

    rollback_response = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={
            "request_id": user_management_app["request_id"],
            "expert_id": user_management_app["other_expert_id"],
            "reason": "Phase 5H rollback probe",
        },
    )
    assert rollback_response.status_code == 500
    assert rollback_response.get_json() == {"error": "خطا در ارجاع دستی"}

    with user_management_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, user_management_app["request_id"])
        assert request_row.assigned_to == user_management_app["expert_id"]
        assert request_row.status == "assigned"
        assert AssignmentLog.query.filter_by(
            shipment_request_id=user_management_app["request_id"],
            assignment_method="manual",
            assignment_reason="rollback probe",
        ).count() == 0


def test_assignment_statistics_and_manual_assignment_contract(user_management_app, monkeypatch):
    """Stats read shape and manual-assignment validation, side effects, and rollback stay explicit."""
    client = user_management_app["app"].test_client()
    admin_headers = _auth_headers(user_management_app["admin_token"])

    stats_response = client.get("/api/user-management/assignment-statistics", headers=admin_headers)
    assert stats_response.status_code == 200
    stats_payload = stats_response.get_json()
    assert set(stats_payload.keys()) == {
        "total_assignments",
        "automatic_assignments",
        "manual_assignments",
        "expert_workloads",
    }
    assert stats_payload["total_assignments"] == 0
    assert stats_payload["automatic_assignments"] == 0
    assert stats_payload["manual_assignments"] == 0

    missing_request_id = client.post("/api/user-management/manual-assignment", headers=admin_headers, json={})
    assert missing_request_id.status_code == 400
    assert missing_request_id.get_json() == {"error": "شناسه درخواست الزامی است"}

    missing_expert_id = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={"request_id": user_management_app["request_id"]},
    )
    assert missing_expert_id.status_code == 400
    assert missing_expert_id.get_json() == {"error": "شناسه کارشناس الزامی است"}

    missing_request = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={"request_id": 999999, "expert_id": user_management_app["other_expert_id"]},
    )
    assert missing_request.status_code == 404
    assert missing_request.get_json() == {"error": "درخواست یافت نشد"}

    missing_expert = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={"request_id": user_management_app["request_id"], "expert_id": 999999},
    )
    assert missing_expert.status_code == 404
    assert missing_expert.get_json() == {"error": "کارشناس یافت نشد"}

    with user_management_app["app"].app_context():
        inactive_expert = ExpertUser(
            username="phase5i_inactive",
            password_hash=bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8"),
            full_name="Phase 5I Inactive",
            email="phase5i-inactive@example.test",
            role="expert",
            is_active=False,
        )
        db.session.add(inactive_expert)
        db.session.commit()
        inactive_expert_id = inactive_expert.id

    inactive_assignment = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={"request_id": user_management_app["request_id"], "expert_id": inactive_expert_id},
    )
    assert inactive_assignment.status_code == 400
    assert inactive_assignment.get_json() == {"error": "کارشناس غیرفعال است"}

    manual_response = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={
            "request_id": user_management_app["request_id"],
            "expert_id": user_management_app["other_expert_id"],
            "reason": "Phase 5I manual",
        },
    )
    assert manual_response.status_code == 200
    assert manual_response.get_json() == {
        "message": "درخواست با موفقیت ارجاع داده شد",
        "assigned_to": {"id": user_management_app["other_expert_id"], "name": "Phase 5B Other"},
    }

    with user_management_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, user_management_app["request_id"])
        assert request_row.assigned_to == user_management_app["other_expert_id"]
        assert request_row.status == "assigned"
        assert request_row.has_unread_for_assignee is True
        assert request_row.sla_due_at is not None
        assert AssignmentLog.query.filter_by(shipment_request_id=user_management_app["request_id"]).count() == 0
        assignment_log = ExpertConsoleLog.query.filter_by(
            shipment_request_id=user_management_app["request_id"],
            expert_user_id=user_management_app["other_expert_id"],
            action="assignment",
        ).one()
        assert assignment_log.old_status == "assigned"
        assert assignment_log.new_status == "assigned"
        assignment_notification = ExpertConsoleNotification.query.filter_by(
            shipment_request_id=user_management_app["request_id"],
            expert_user_id=user_management_app["other_expert_id"],
            notification_type="assignment",
        ).one()
        assert assignment_notification.is_read is False

    with user_management_app["app"].app_context():
        rollback_request = ShipmentRequest(
            tracking_code="UM-P5I-ROLLBACK",
            shipping_type="domestic",
            contact_phone="09120000001",
            customer_first_name="Rollback",
            customer_last_name="Probe",
            transport_method="road",
            domestic_transport_method="road",
            status_request_status="new",
            status="new",
            assigned_to=user_management_app["expert_id"],
        )
        db.session.add(rollback_request)
        db.session.commit()
        rollback_request_id = rollback_request.id

    def fail_after_staged_assignment_notification(request_id: int, expert_id: int):
        db.session.flush()
        raise RuntimeError("manual assignment staged rollback probe")

    monkeypatch.setattr(
        assignment_service,
        "create_assignment_notification_if_needed",
        fail_after_staged_assignment_notification,
    )

    rollback_response = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={
            "request_id": rollback_request_id,
            "expert_id": user_management_app["other_expert_id"],
            "reason": "Phase 5I rollback probe",
        },
    )
    assert rollback_response.status_code == 500
    assert rollback_response.get_json() == {"error": "خطا در ارجاع دستی"}

    with user_management_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, rollback_request_id)
        assert request_row.assigned_to == user_management_app["expert_id"]
        assert request_row.status == "new"
        assert request_row.sla_due_at is None
        assert ExpertConsoleLog.query.filter_by(shipment_request_id=rollback_request_id, action="assignment").count() == 0
        assert ExpertConsoleNotification.query.filter_by(
            shipment_request_id=rollback_request_id,
            notification_type="assignment",
        ).count() == 0
