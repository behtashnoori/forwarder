"""Characterization tests for CRM write endpoint response and commit contracts."""
from __future__ import annotations

from datetime import datetime

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Activity, Customer, ExpertUser, Opportunity
from backend.security import security
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture
def crm_write_app():
    """App with isolated test DB and CRM write seed data."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        business_expert = ExpertUser(
            username="crm_write_business_expert",
            password_hash="unused",
            full_name="CRM Write Expert",
            email="crm-write-expert@example.test",
            role="business_expert",
            is_active=True,
        )
        existing_customer = Customer(
            first_name="Sara",
            last_name="Ahmadi",
            company_name="Ahmadi Co",
            email="sara@example.test",
            phone="09121111111",
            customer_type="prospect",
            status="active",
            industry="Import",
        )
        db.session.add_all([business_expert, existing_customer])
        db.session.flush()
        existing_opportunity = Opportunity(
            customer_id=existing_customer.id,
            title="Existing Opportunity",
            description="Existing opportunity description",
            stage="lead",
            probability=10,
            value=500,
            assigned_to=business_expert.id,
            status="open",
        )
        existing_activity = Activity(
            customer_id=existing_customer.id,
            opportunity_id=existing_opportunity.id,
            expert_user_id=business_expert.id,
            activity_type="call",
            subject="Existing activity",
            description="Existing activity description",
            status="pending",
            priority="normal",
        )
        db.session.add_all([existing_opportunity, existing_activity])
        db.session.commit()
        token = create_session_tokens(business_expert.id)["access_token"]
        return {
            "app": app,
            "token": token,
            "expert_id": business_expert.id,
            "customer_id": existing_customer.id,
            "opportunity_id": existing_opportunity.id,
            "activity_id": existing_activity.id,
        }


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_crm_customer_write_endpoints_preserve_response_auth_and_commit(crm_write_app):
    """Customer create/update endpoints keep current status, JSON, auth, and DB commit behavior."""
    client = crm_write_app["app"].test_client()
    headers = _auth_headers(crm_write_app["token"])

    unauthenticated = client.post("/api/crm/customers", json={})
    assert unauthenticated.status_code == 401

    create_response = client.post(
        "/api/crm/customers",
        headers=headers,
        json={
            "first_name": "Reza",
            "last_name": "Karimi",
            "email": "reza@example.test",
            "phone": "09122222222",
            "company_name": "Karimi LLC",
            "industry": "Export",
        },
    )
    assert create_response.status_code == 201
    create_data = create_response.get_json()
    assert set(create_data.keys()) == {"message", "customer_id"}
    assert create_data["message"] == "مشتری با موفقیت ایجاد شد"

    with crm_write_app["app"].app_context():
        created_customer = db.session.get(Customer, create_data["customer_id"])
        assert created_customer is not None
        assert created_customer.first_name == "Reza"
        assert created_customer.customer_type == "prospect"
        assert created_customer.status == "active"
        assert created_customer.country == "Iran"

    missing_update = client.put("/api/crm/customers/999999", headers=headers, json={"first_name": "Missing"})
    assert missing_update.status_code == 404
    assert missing_update.get_json() == {"error": "مشتری یافت نشد"}

    update_response = client.put(
        f"/api/crm/customers/{crm_write_app['customer_id']}",
        headers=headers,
        json={"first_name": "Updated", "status": "inactive"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json() == {"message": "اطلاعات مشتری به‌روزرسانی شد"}

    with crm_write_app["app"].app_context():
        updated_customer = db.session.get(Customer, crm_write_app["customer_id"])
        assert updated_customer.first_name == "Updated"
        assert updated_customer.last_name == "Ahmadi"
        assert updated_customer.status == "inactive"
        assert updated_customer.updated_at is not None


def test_crm_opportunity_write_endpoint_preserves_response_error_and_commit(crm_write_app):
    """Opportunity create endpoint keeps current status, JSON, date parsing, and rollback behavior."""
    client = crm_write_app["app"].test_client()
    headers = _auth_headers(crm_write_app["token"])

    create_response = client.post(
        "/api/crm/opportunities",
        headers=headers,
        json={
            "customer_id": crm_write_app["customer_id"],
            "title": "New Opportunity",
            "description": "New opportunity description",
            "probability": 35,
            "value": 2500,
            "expected_close_date": "2026-06-15",
            "assigned_to": crm_write_app["expert_id"],
        },
    )
    assert create_response.status_code == 201
    create_data = create_response.get_json()
    assert set(create_data.keys()) == {"message", "opportunity_id"}
    assert create_data["message"] == "فرصت فروش با موفقیت ایجاد شد"

    with crm_write_app["app"].app_context():
        created_opportunity = db.session.get(Opportunity, create_data["opportunity_id"])
        assert created_opportunity is not None
        assert created_opportunity.title == "New Opportunity"
        assert created_opportunity.stage == "lead"
        assert created_opportunity.probability == 35
        assert created_opportunity.currency == "IRR"
        assert created_opportunity.expected_close_date.isoformat() == "2026-06-15"

    with crm_write_app["app"].app_context():
        before_count = Opportunity.query.count()

    invalid_response = client.post(
        "/api/crm/opportunities",
        headers=headers,
        json={
            "customer_id": crm_write_app["customer_id"],
            "title": "Bad Date Opportunity",
            "expected_close_date": "not-a-date",
        },
    )
    assert invalid_response.status_code == 500
    assert invalid_response.get_json() == {"error": "خطا در ایجاد فرصت فروش"}
    with crm_write_app["app"].app_context():
        assert Opportunity.query.count() == before_count

    update_response = client.put(
        f"/api/crm/opportunities/{crm_write_app['opportunity_id']}",
        headers=headers,
        json={"title": "No current update endpoint"},
    )
    assert update_response.status_code == 404


def test_crm_activity_write_endpoint_preserves_response_error_and_commit(crm_write_app):
    """Activity create endpoint keeps current status, JSON, date parsing, and rollback behavior."""
    client = crm_write_app["app"].test_client()
    headers = _auth_headers(crm_write_app["token"])

    due_date = datetime(2026, 7, 1, 9, 30, 0).isoformat()
    create_response = client.post(
        "/api/crm/activities",
        headers=headers,
        json={
            "customer_id": crm_write_app["customer_id"],
            "opportunity_id": crm_write_app["opportunity_id"],
            "expert_user_id": crm_write_app["expert_id"],
            "activity_type": "meeting",
            "subject": "Discovery meeting",
            "description": "Discuss requirements",
            "priority": "high",
            "due_date": due_date,
            "outcome": "scheduled",
            "next_action": "Prepare agenda",
        },
    )
    assert create_response.status_code == 201
    create_data = create_response.get_json()
    assert set(create_data.keys()) == {"message", "activity_id"}
    assert create_data["message"] == "فعالیت با موفقیت ایجاد شد"

    with crm_write_app["app"].app_context():
        created_activity = db.session.get(Activity, create_data["activity_id"])
        assert created_activity is not None
        assert created_activity.activity_type == "meeting"
        assert created_activity.subject == "Discovery meeting"
        assert created_activity.status == "pending"
        assert created_activity.priority == "high"
        assert created_activity.due_date.isoformat() == due_date

    with crm_write_app["app"].app_context():
        before_count = Activity.query.count()

    invalid_response = client.post(
        "/api/crm/activities",
        headers=headers,
        json={
            "customer_id": crm_write_app["customer_id"],
            "expert_user_id": crm_write_app["expert_id"],
            "activity_type": "task",
            "subject": "Bad due date",
            "due_date": "not-a-datetime",
        },
    )
    assert invalid_response.status_code == 500
    assert invalid_response.get_json() == {"error": "خطا در ایجاد فعالیت"}
    with crm_write_app["app"].app_context():
        assert Activity.query.count() == before_count

    update_response = client.put(
        f"/api/crm/activities/{crm_write_app['activity_id']}",
        headers=headers,
        json={"subject": "No current update endpoint"},
    )
    assert update_response.status_code == 404
