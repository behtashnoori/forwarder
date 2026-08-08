"""Characterization tests for customer gamification route contracts."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import bcrypt
import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend import create_app
from backend.extensions import db
from backend.models import (
    CustomerGamification,
    CustomerWorkflowStep,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.routes import customer_gamification as customer_gamification_routes
from backend.services import customer_gamification_service


@pytest.fixture
def customer_gamification_app():
    """App with isolated DB and customer gamification seed data."""
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
        expert = ExpertUser(
            username="phase5k_expert",
            password_hash=password_hash,
            full_name="Phase 5K Expert",
            email="phase5k-expert@example.test",
            phone="09121111111",
            role="expert",
            is_active=True,
        )
        verified_customer = CustomerGamification(
            email="verified@example.test",
            phone="09120000000",
            first_name="Verified",
            last_name="Customer",
            is_email_verified=True,
            loyalty_points=150,
            customer_level="silver",
            total_requests=2,
            completed_requests=1,
        )
        anonymous_customer = CustomerGamification(
            email="anonymous@example.test",
            phone="09120000001",
            is_email_verified=True,
            loyalty_points=50,
            customer_level="bronze",
        )
        unverified_customer = CustomerGamification(
            email="unverified@example.test",
            phone="09120000002",
            first_name="Unverified",
            is_email_verified=False,
            email_verification_token="verify-token",
            verification_expires_at=datetime.utcnow() + timedelta(hours=1),
            loyalty_points=900,
            customer_level="gold",
        )
        db.session.add_all([expert, verified_customer, anonymous_customer, unverified_customer])
        db.session.flush()

        request_row = ShipmentRequest(
            tracking_code="CG-P5K-001",
            shipping_type="domestic",
            contact_phone="09123456789",
            customer_first_name="Verified",
            customer_last_name="Customer",
            transport_method="road",
            domestic_transport_method="road",
            status_request_status="new",
            status="assigned",
            assigned_to=expert.id,
            gamification_customer_id=verified_customer.id,
        )
        other_request = ShipmentRequest(
            tracking_code="CG-P5K-OTHER",
            shipping_type="domestic",
            contact_phone="09123456780",
            customer_first_name="Other",
            customer_last_name="Customer",
            status_request_status="new",
            status="new",
            gamification_customer_id=anonymous_customer.id,
        )
        db.session.add_all([request_row, other_request])
        db.session.flush()

        step = CustomerWorkflowStep(
            customer_id=verified_customer.id,
            shipment_request_id=request_row.id,
            step_name="request_submitted",
            step_order=2,
            is_completed=True,
            completed_at=datetime.utcnow(),
            points_earned=20,
        )
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            amount=123456,
            currency="IRR",
            note="Seed quote",
            valid_until=date(2026, 8, 1),
            created_by_expert_id=expert.id,
        )
        db.session.add_all([step, quote])
        db.session.commit()

        return {
            "app": app,
            "customer_id": verified_customer.id,
            "anonymous_customer_id": anonymous_customer.id,
            "unverified_customer_id": unverified_customer.id,
            "request_id": request_row.id,
            "other_request_id": other_request.id,
            "expert_id": expert.id,
        }


def test_customer_registration_contract(customer_gamification_app):
    """Registration keeps validation, duplicate, success shape, and commit behavior."""
    client = customer_gamification_app["app"].test_client()

    missing_fields = client.post("/api/customer/register", json={})
    assert missing_fields.status_code == 400
    assert missing_fields.get_json() == {"message": "ایمیل و شماره تماس الزامی است"}

    invalid_email = client.post("/api/customer/register", json={"email": "bad-email", "phone": "09120000003"})
    assert invalid_email.status_code == 400
    assert invalid_email.get_json() == {"message": "فرمت ایمیل نامعتبر است"}

    invalid_phone = client.post("/api/customer/register", json={"email": "new@example.test", "phone": "123"})
    assert invalid_phone.status_code == 400
    assert invalid_phone.get_json() == {"message": "شماره تماس نامعتبر است"}

    created = client.post(
        "/api/customer/register",
        json={
            "email": " NewCustomer@Example.Test ",
            "phone": "09120000003",
            "first_name": " New ",
            "last_name": " Customer ",
        },
    )
    assert created.status_code == 201
    created_payload = created.get_json()
    assert set(created_payload.keys()) == {"message", "customer_id", "email_sent"}
    assert created_payload["email_sent"] is True

    duplicate = client.post(
        "/api/customer/register",
        json={"email": "newcustomer@example.test", "phone": "09120000003"},
    )
    assert duplicate.status_code == 200
    assert duplicate.get_json() == {
        "message": "این ایمیل قبلاً ثبت شده است",
        "customer_id": created_payload["customer_id"],
        "is_verified": False,
    }

    with customer_gamification_app["app"].app_context():
        customer = db.session.get(CustomerGamification, created_payload["customer_id"])
        assert customer.email == "newcustomer@example.test"
        assert customer.phone == "09120000003"
        assert customer.first_name == "New"
        assert customer.last_name == "Customer"
        assert customer.email_verification_token
        assert customer.verification_expires_at
        assert customer.is_email_verified is False
        assert customer.loyalty_points == 0
        assert customer.customer_level == "bronze"
        assert CustomerWorkflowStep.query.filter_by(customer_id=created_payload["customer_id"]).count() == 0


def test_customer_registration_email_failure_contract(customer_gamification_app, monkeypatch):
    """Registration still commits customer when email side effect reports failure."""
    client = customer_gamification_app["app"].test_client()
    monkeypatch.setattr(customer_gamification_service, "send_registration_verification_email", lambda *args: False)

    response = client.post(
        "/api/customer/register",
        json={
            "email": "email-failure@example.test",
            "phone": "09120000004",
            "first_name": "Email",
            "last_name": "Failure",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert set(payload.keys()) == {"message", "customer_id", "email_sent"}
    assert payload["email_sent"] is False

    with customer_gamification_app["app"].app_context():
        customer = db.session.get(CustomerGamification, payload["customer_id"])
        assert customer.email == "email-failure@example.test"
        assert customer.is_email_verified is False
        assert customer.email_verification_token
        assert customer.loyalty_points == 0
        assert CustomerWorkflowStep.query.filter_by(customer_id=payload["customer_id"]).count() == 0


def test_customer_registration_rollback_contract(customer_gamification_app, monkeypatch):
    """Registration rolls back the flushed customer row when commit fails."""
    client = customer_gamification_app["app"].test_client()

    def fail_commit():
        raise SQLAlchemyError("forced commit failure")

    monkeypatch.setattr(customer_gamification_service.db.session, "commit", fail_commit)

    response = client.post(
        "/api/customer/register",
        json={"email": "rollback@example.test", "phone": "09120000005"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"message": "\u062e\u0637\u0627 \u062f\u0631 \u062b\u0628\u062a\u200c\u0646\u0627\u0645"}

    with customer_gamification_app["app"].app_context():
        assert CustomerGamification.query.filter_by(email="rollback@example.test").first() is None


def test_customer_email_verification_and_complete_step_contract(customer_gamification_app):
    """Email verification and workflow completion keep point, commit, and duplicate behavior."""
    client = customer_gamification_app["app"].test_client()

    missing_token = client.get("/api/customer/verify-email")
    assert missing_token.status_code == 400
    assert missing_token.get_json() == {"message": "توکن تایید الزامی است"}

    invalid_token = client.get("/api/customer/verify-email?token=missing")
    assert invalid_token.status_code == 400
    assert invalid_token.get_json() == {"message": "توکن تایید نامعتبر یا منقضی شده است"}

    with customer_gamification_app["app"].app_context():
        expired_customer = CustomerGamification(
            email="expired@example.test",
            phone="09120000006",
            is_email_verified=False,
            email_verification_token="expired-token",
            verification_expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.session.add(expired_customer)
        db.session.commit()

    expired_token = client.get("/api/customer/verify-email?token=expired-token")
    assert expired_token.status_code == 400
    assert expired_token.get_json() == invalid_token.get_json()

    verified = client.get("/api/customer/verify-email?token=verify-token")
    assert verified.status_code == 200
    verified_payload = verified.get_json()
    assert verified_payload["customer_id"] == customer_gamification_app["unverified_customer_id"]
    assert verified_payload["loyalty_points"] == 910
    assert verified_payload["customer_level"] == "gold"

    with customer_gamification_app["app"].app_context():
        verified_customer = db.session.get(CustomerGamification, customer_gamification_app["unverified_customer_id"])
        assert verified_customer.is_email_verified is True
        assert verified_customer.email_verification_token is None
        assert verified_customer.verification_expires_at is None
        assert verified_customer.loyalty_points == 910
        assert CustomerWorkflowStep.query.filter_by(
            customer_id=customer_gamification_app["unverified_customer_id"],
            shipment_request_id=0,
            step_name="email_verified",
            is_completed=True,
            points_earned=10,
        ).count() == 1

    missing_complete_fields = client.post("/api/customer/complete-step", json={})
    assert missing_complete_fields.status_code == 400
    assert missing_complete_fields.get_json() == {"message": "تمام فیلدها الزامی است"}

    complete = client.post(
        "/api/customer/complete-step",
        json={
            "customer_id": customer_gamification_app["customer_id"],
            "request_id": customer_gamification_app["request_id"],
            "step_name": "expert_assigned",
        },
    )
    assert complete.status_code == 200
    complete_payload = complete.get_json()
    assert complete_payload["points_earned"] == 15
    assert complete_payload["total_points"] == 165
    assert complete_payload["customer_level"] == "silver"

    duplicate = client.post(
        "/api/customer/complete-step",
        json={
            "customer_id": customer_gamification_app["customer_id"],
            "request_id": customer_gamification_app["request_id"],
            "step_name": "expert_assigned",
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.get_json() == {"message": "این مرحله قبلاً تکمیل شده است"}

    with customer_gamification_app["app"].app_context():
        customer = db.session.get(CustomerGamification, customer_gamification_app["customer_id"])
        assert customer.loyalty_points == 165
        assert CustomerWorkflowStep.query.filter_by(
            customer_id=customer_gamification_app["customer_id"],
            shipment_request_id=customer_gamification_app["request_id"],
            step_name="expert_assigned",
        ).count() == 1
        expert_assigned_step = CustomerWorkflowStep.query.filter_by(
            customer_id=customer_gamification_app["customer_id"],
            shipment_request_id=customer_gamification_app["request_id"],
            step_name="expert_assigned",
        ).first()
        assert expert_assigned_step.step_order == 3
        assert expert_assigned_step.is_completed is True
        assert expert_assigned_step.points_earned == 15
        assert expert_assigned_step.completed_at


def test_customer_complete_step_missing_customer_contract(customer_gamification_app):
    """Complete-step currently creates a step even when the customer lookup misses."""
    client = customer_gamification_app["app"].test_client()

    response = client.post(
        "/api/customer/complete-step",
        json={
            "customer_id": 999999,
            "request_id": customer_gamification_app["request_id"],
            "step_name": "shipment_delivered",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["points_earned"] == 100
    assert payload["total_points"] == 0
    assert payload["customer_level"] == "bronze"

    with customer_gamification_app["app"].app_context():
        missing_customer_step = CustomerWorkflowStep.query.filter_by(
            customer_id=999999,
            shipment_request_id=customer_gamification_app["request_id"],
            step_name="shipment_delivered",
        ).first()
        assert missing_customer_step is not None
        assert missing_customer_step.step_order == 8
        assert missing_customer_step.is_completed is True
        assert missing_customer_step.points_earned == 100


def test_customer_email_verification_rollback_contract(customer_gamification_app, monkeypatch):
    """Email verification rolls back token, points, and workflow step when commit fails."""
    client = customer_gamification_app["app"].test_client()

    def fail_commit():
        raise SQLAlchemyError("forced commit failure")

    monkeypatch.setattr(customer_gamification_service.db.session, "commit", fail_commit)

    response = client.get("/api/customer/verify-email?token=verify-token")

    assert response.status_code == 500
    assert response.get_json() == {"message": "\u062e\u0637\u0627 \u062f\u0631 \u062a\u0627\u06cc\u06cc\u062f \u0627\u06cc\u0645\u06cc\u0644"}

    with customer_gamification_app["app"].app_context():
        customer = db.session.get(CustomerGamification, customer_gamification_app["unverified_customer_id"])
        assert customer.is_email_verified is False
        assert customer.email_verification_token == "verify-token"
        assert customer.verification_expires_at is not None
        assert customer.loyalty_points == 900
        assert CustomerWorkflowStep.query.filter_by(
            customer_id=customer_gamification_app["unverified_customer_id"],
            step_name="email_verified",
        ).count() == 0


def test_customer_complete_step_rollback_contract(customer_gamification_app, monkeypatch):
    """Complete-step rolls back created step and point mutation when commit fails."""
    client = customer_gamification_app["app"].test_client()

    def fail_commit():
        raise SQLAlchemyError("forced commit failure")

    monkeypatch.setattr(customer_gamification_service.db.session, "commit", fail_commit)

    response = client.post(
        "/api/customer/complete-step",
        json={
            "customer_id": customer_gamification_app["customer_id"],
            "request_id": customer_gamification_app["request_id"],
            "step_name": "quote_provided",
        },
    )

    assert response.status_code == 500
    assert response.get_json() == {"message": "\u062e\u0637\u0627 \u062f\u0631 \u062a\u06a9\u0645\u06cc\u0644 \u0645\u0631\u062d\u0644\u0647"}

    with customer_gamification_app["app"].app_context():
        customer = db.session.get(CustomerGamification, customer_gamification_app["customer_id"])
        assert customer.loyalty_points == 150
        assert CustomerWorkflowStep.query.filter_by(
            customer_id=customer_gamification_app["customer_id"],
            shipment_request_id=customer_gamification_app["request_id"],
            step_name="quote_provided",
        ).count() == 0


def test_customer_profile_and_workflow_read_contract(customer_gamification_app):
    """Profile and workflow reads keep public shape, ownership checks, quote shape, and errors."""
    client = customer_gamification_app["app"].test_client()

    missing_profile = client.get("/api/customer/profile/999999")
    assert missing_profile.status_code == 404
    assert missing_profile.get_json() == {"message": "مشتری یافت نشد"}

    profile = client.get(f"/api/customer/profile/{customer_gamification_app['customer_id']}")
    assert profile.status_code == 200
    profile_payload = profile.get_json()
    assert set(profile_payload.keys()) == {"customer", "recent_steps", "recent_requests"}
    assert set(profile_payload["customer"].keys()) == {
        "id",
        "email",
        "phone",
        "first_name",
        "last_name",
        "is_email_verified",
        "total_requests",
        "completed_requests",
        "loyalty_points",
        "customer_level",
        "created_at",
    }
    assert profile_payload["customer"]["id"] == customer_gamification_app["customer_id"]
    assert profile_payload["customer"]["email"] == "verified@example.test"
    assert profile_payload["customer"]["phone"] == "09120000000"
    assert profile_payload["customer"]["first_name"] == "Verified"
    assert profile_payload["customer"]["last_name"] == "Customer"
    assert profile_payload["customer"]["is_email_verified"] is True
    assert profile_payload["customer"]["total_requests"] == 2
    assert profile_payload["customer"]["completed_requests"] == 1
    assert profile_payload["customer"]["loyalty_points"] == 150
    assert profile_payload["customer"]["customer_level"] == "silver"
    assert profile_payload["customer"]["created_at"]
    assert set(profile_payload["recent_steps"][0].keys()) == {
        "step_name",
        "step_order",
        "is_completed",
        "completed_at",
        "points_earned",
        "created_at",
    }
    assert profile_payload["recent_steps"][0]["step_name"] == "request_submitted"
    assert profile_payload["recent_steps"][0]["step_order"] == 2
    assert profile_payload["recent_steps"][0]["is_completed"] is True
    assert profile_payload["recent_steps"][0]["points_earned"] == 20
    assert set(profile_payload["recent_requests"][0].keys()) == {
        "id",
        "shipping_type",
        "status",
        "created_at",
        "assigned_expert",
    }
    assert profile_payload["recent_requests"][0]["id"] == customer_gamification_app["request_id"]
    assert profile_payload["recent_requests"][0]["shipping_type"] == "domestic"
    assert profile_payload["recent_requests"][0]["status"] == "assigned"
    assert profile_payload["recent_requests"][0]["assigned_expert"] == {
        "id": customer_gamification_app["expert_id"],
        "full_name": "Phase 5K Expert",
        "phone": "09121111111",
    }

    missing_request_id = client.get(f"/api/customer/workflow/{customer_gamification_app['customer_id']}")
    assert missing_request_id.status_code == 400
    assert missing_request_id.get_json() == {"message": "شناسه درخواست الزامی است"}

    invalid_request_id = client.get(f"/api/customer/workflow/{customer_gamification_app['customer_id']}?request_id=bad")
    assert invalid_request_id.status_code == 400
    assert invalid_request_id.get_json() == {"message": "شناسه درخواست نامعتبر است"}

    wrong_customer = client.get(
        f"/api/customer/workflow/{customer_gamification_app['anonymous_customer_id']}"
        f"?request_id={customer_gamification_app['request_id']}"
    )
    assert wrong_customer.status_code == 404
    assert wrong_customer.get_json() == {"message": "درخواست یافت نشد یا به این مشتری تعلق ندارد"}

    workflow = client.get(
        f"/api/customer/workflow/{customer_gamification_app['customer_id']}"
        f"?request_id={customer_gamification_app['request_id']}"
    )
    assert workflow.status_code == 200
    workflow_payload = workflow.get_json()
    assert set(workflow_payload.keys()) == {
        "id",
        "shipping_type",
        "status",
        "created_at",
        "assigned_expert",
        "customer_id",
            "request_id",
            "tracking_code",
        "workflow_steps",
        "workflow_steps_simple",
        "total_points_earned",
        "completed_steps",
        "total_steps",
        "latest_quote",
    }
    assert workflow_payload["id"] == customer_gamification_app["request_id"]
    assert workflow_payload["shipping_type"] == "domestic"
    assert workflow_payload["status"] == "assigned"
    assert workflow_payload["created_at"]
    assert workflow_payload["assigned_expert"] == {
        "id": customer_gamification_app["expert_id"],
        "full_name": "Phase 5K Expert",
        "phone": "09121111111",
        "email": "phase5k-expert@example.test",
    }
    assert workflow_payload["customer_id"] == customer_gamification_app["customer_id"]
    assert workflow_payload["request_id"] == customer_gamification_app["request_id"]
    assert len(workflow_payload["workflow_steps"]) == 8
    assert set(workflow_payload["workflow_steps"][0].keys()) == {
        "name",
        "order",
        "title",
        "points",
        "is_completed",
        "completed_at",
        "points_earned",
    }
    assert workflow_payload["workflow_steps"][0]["name"] == "email_verified"
    assert workflow_payload["workflow_steps"][0]["order"] == 1
    assert workflow_payload["workflow_steps"][0]["points"] == 10
    assert workflow_payload["workflow_steps"][0]["is_completed"] is False
    assert workflow_payload["workflow_steps"][0]["points_earned"] == 0
    assert workflow_payload["workflow_steps"][1]["name"] == "request_submitted"
    assert workflow_payload["workflow_steps"][1]["is_completed"] is True
    assert workflow_payload["workflow_steps"][1]["points_earned"] == 20
    assert len(workflow_payload["workflow_steps_simple"]) == 4
    assert workflow_payload["completed_steps"] == 1
    assert workflow_payload["total_points_earned"] == 20
    assert workflow_payload["total_steps"] == 8
    assert set(workflow_payload["latest_quote"].keys()) == {
        "amount",
        "currency",
        "note",
        "valid_until",
        "created_at",
        "customer_response",
        "responded_at",
    }
    assert workflow_payload["latest_quote"]["amount"] == 123456
    assert workflow_payload["latest_quote"]["currency"] == "IRR"
    assert workflow_payload["latest_quote"]["note"] == "Seed quote"
    assert workflow_payload["latest_quote"]["valid_until"] == "2026-08-01"
    assert workflow_payload["latest_quote"]["customer_response"] is None
    assert workflow_payload["latest_quote"]["responded_at"] is None


def test_customer_leaderboard_contract(customer_gamification_app):
    """Leaderboard keeps verified-only ordering, rank, limit, anonymous fallback, and response shape."""
    client = customer_gamification_app["app"].test_client()

    with customer_gamification_app["app"].app_context():
        for index in range(25):
            db.session.add(
                CustomerGamification(
                    email=f"ranked-{index}@example.test",
                    phone=f"0912{index:07d}",
                    first_name=f"Ranked {index}",
                    is_email_verified=True,
                    loyalty_points=200 + index,
                    customer_level="silver",
                    total_requests=index,
                    completed_requests=0,
                )
            )
        db.session.commit()

    response = client.get("/api/customer/leaderboard")
    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload.keys()) == {"leaderboard", "total_customers"}
    assert payload["total_customers"] == 20
    assert len(payload["leaderboard"]) == 20
    assert payload["leaderboard"][0]["rank"] == 1
    assert payload["leaderboard"][0]["loyalty_points"] == 224
    assert payload["leaderboard"][19]["rank"] == 20
    assert all(entry["customer_id"] != customer_gamification_app["unverified_customer_id"] for entry in payload["leaderboard"])

    with customer_gamification_app["app"].app_context():
        CustomerGamification.query.filter(CustomerGamification.email.like("ranked-%")).delete(synchronize_session=False)
        db.session.commit()

    fallback_response = client.get("/api/customer/leaderboard")
    fallback_payload = fallback_response.get_json()
    anonymous_entry = next(
        entry for entry in fallback_payload["leaderboard"]
        if entry["customer_id"] == customer_gamification_app["anonymous_customer_id"]
    )
    assert anonymous_entry["name"] == "کاربر ناشناس"
