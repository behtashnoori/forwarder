"""Characterization tests for CRM read endpoint response contracts."""
from datetime import UTC, datetime

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Activity, Customer, ExpertUser, Opportunity
from backend.security import security
from backend.services.auth_session_service import create_session_tokens
from backend.operational_models import OperationalMembership, OperationalOrganization


@pytest.fixture
def crm_app():
    """App with isolated test DB and CRM seed data."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        expert = ExpertUser(
            username="crm_read_business_expert",
            password_hash="unused",
            full_name="CRM Read Expert",
            email="crm-read-expert@example.test",
            role="business_expert",
            is_active=True,
        )
        organization = OperationalOrganization(name="CRM Read Organization")
        db.session.add_all([expert, organization])
        db.session.flush()
        db.session.add(OperationalMembership(
            organization_id=organization.id, user_id=expert.id, permissions=[]
        ))
        customer = Customer(
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
            first_name="Ali",
            last_name="Rahimi",
            company_name="Rahimi Co",
            email="ali@example.test",
            phone="09120000000",
            customer_type="customer",
            status="active",
            industry="Logistics",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.session.add(customer)
        db.session.flush()
        opportunity = Opportunity(
            operational_organization_id=organization.id,
            customer_id=customer.id,
            title="Test Opportunity",
            description="Current contract opportunity",
            stage="lead",
            probability=25,
            value=1000,
            assigned_to=expert.id,
            status="open",
            created_at=datetime(2026, 5, 18, 11, 0, 0),
        )
        activity = Activity(
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
            customer_id=customer.id,
            expert_user_id=expert.id,
            activity_type="call",
            subject="Intro call",
            description="Initial customer call",
            status="pending",
            priority="normal",
            created_at=datetime(2026, 5, 18, 12, 0, 0),
        )
        db.session.add_all([opportunity, activity])
        db.session.commit()
        token = create_session_tokens(expert.id)["access_token"]
        return {"app": app, "token": token, "customer_id": customer.id}


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_crm_read_endpoints_preserve_response_contracts(crm_app):
    """CRM read endpoints keep current keys, pagination shape, filters, and auth requirement."""
    client = crm_app["app"].test_client()
    headers = _auth_headers(crm_app["token"])

    unauthenticated = client.get("/api/crm/customers")
    assert unauthenticated.status_code == 401

    customers_response = client.get("/api/crm/customers?search=Ali&per_page=1", headers=headers)
    assert customers_response.status_code == 200
    customers_data = customers_response.get_json()
    assert set(customers_data.keys()) == {"customers", "pagination"}
    assert set(customers_data["pagination"].keys()) == {"page", "per_page", "total", "pages", "has_next", "has_prev"}
    assert customers_data["pagination"]["per_page"] == 1
    assert len(customers_data["customers"]) == 1
    assert set(customers_data["customers"][0].keys()) == {
        "id",
        "name",
        "company_name",
        "email",
        "phone",
        "customer_type",
        "status",
        "industry",
        "last_contact_at",
        "created_at",
        "total_opportunities",
        "total_activities",
    }

    missing_detail = client.get("/api/crm/customers/999999", headers=headers)
    assert missing_detail.status_code == 404
    assert missing_detail.get_json() == {"error": "مشتری یافت نشد"}

    detail_response = client.get(f"/api/crm/customers/{crm_app['customer_id']}", headers=headers)
    assert detail_response.status_code == 200
    detail_data = detail_response.get_json()
    assert set(detail_data.keys()) == {
        "id",
        "name",
        "company_name",
        "email",
        "phone",
        "mobile",
        "website",
        "industry",
        "company_size",
        "customer_type",
        "status",
        "source",
        "notes",
        "address",
        "city",
        "province",
        "postal_code",
        "country",
        "last_contact_at",
        "created_at",
        "contacts",
        "opportunities",
        "recent_activities",
    }
    assert detail_data["name"] == "Ali Rahimi"

    opportunities_response = client.get("/api/crm/opportunities?stage=lead", headers=headers)
    assert opportunities_response.status_code == 200
    opportunities_data = opportunities_response.get_json()
    assert set(opportunities_data.keys()) == {"opportunities", "pagination"}
    assert set(opportunities_data["opportunities"][0].keys()) == {
        "id",
        "title",
        "customer",
        "stage",
        "value",
        "probability",
        "status",
        "expected_close_date",
        "assigned_to",
        "created_at",
    }

    activities_response = client.get("/api/crm/activities?activity_type=call", headers=headers)
    assert activities_response.status_code == 200
    activities_data = activities_response.get_json()
    assert set(activities_data.keys()) == {"activities", "pagination"}
    assert set(activities_data["activities"][0].keys()) == {
        "id",
        "type",
        "subject",
        "description",
        "status",
        "priority",
        "due_date",
        "completed_at",
        "outcome",
        "customer",
        "expert",
        "created_at",
    }

    dashboard_response = client.get("/api/crm/dashboard/kpis", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard_data = dashboard_response.get_json()
    assert set(dashboard_data.keys()) == {
        "customers",
        "opportunities",
        "activities",
        "recent_activities",
    }
    assert dashboard_data["customers"] == {"total": 1, "new_this_month": 1}
    assert dashboard_data["opportunities"] == {
        "total": 1,
        "open": 1,
        "won": 0,
        "pipeline_value": 1000.0,
    }
    assert dashboard_data["activities"] == {"total": 1, "completed": 0}
    assert dashboard_data["recent_activities"] == [
        {
            "id": activities_data["activities"][0]["id"],
            "type": "call",
            "subject": "Intro call",
            "customer_name": "Ali Rahimi",
            "expert_name": "CRM Read Expert",
            "created_at": activities_data["activities"][0]["created_at"],
        }
    ]
