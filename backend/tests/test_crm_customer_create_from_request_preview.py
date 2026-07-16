"""Contract tests for CRM customer-create preview from shipment requests."""
from __future__ import annotations

from datetime import datetime

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    CRMCustomerLinkAudit,
    Customer,
    CustomerGamification,
    ExpertConsoleLog,
    ExpertQuote,
    ExpertUser,
    Opportunity,
    ShipmentRequest,
)
from backend.security import security
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture
def crm_customer_create_preview_app():
    """App with isolated CRM customer-create preview seed data."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        business_expert = ExpertUser(
            username="crm_create_preview_business_expert",
            password_hash="unused",
            full_name="CRM Create Preview Expert",
            email="crm-create-preview@example.test",
            role="business_expert",
            is_active=True,
        )
        basic_expert = ExpertUser(
            username="crm_create_preview_basic_expert",
            password_hash="unused",
            full_name="Basic Preview Expert",
            email="crm-create-preview-basic@example.test",
            role="expert",
            is_active=True,
        )
        phone_match_customer = Customer(
            first_name="Existing",
            last_name="Phone",
            company_name="Existing Phone Co",
            email="phone@example.test",
            phone="09125555555",
            mobile="09126666666",
            customer_type="customer",
            status="active",
        )
        name_match_customer = Customer(
            first_name="Raw",
            last_name="Requester",
            company_name="Name Match Co",
            email="name@example.test",
            phone="09127777777",
            customer_type="prospect",
            status="active",
        )
        gamification_customer = CustomerGamification(
            email="portal-preview@example.test",
            phone="09128888888",
            first_name="Portal",
            last_name="Preview",
            is_email_verified=True,
            total_requests=1,
            loyalty_points=20,
        )
        db.session.add_all([
            business_expert,
            basic_expert,
            phone_match_customer,
            name_match_customer,
            gamification_customer,
        ])
        db.session.flush()
        shipment_request = ShipmentRequest(
            shipping_type="international",
            origin_country="Turkey",
            origin_city_international="Istanbul",
            dest_country="Iran",
            dest_city_international="Tehran",
            contact_phone="09125555555",
            customer_first_name=" Raw ",
            customer_last_name=" Requester ",
            transport_method="road",
            status="assigned",
            status_request_status="assigned",
            assigned_to=business_expert.id,
            priority="high",
            sla_due_at=datetime(2026, 7, 10, 10, 0, 0),
            last_customer_touch_at=datetime(2026, 7, 9, 9, 0, 0),
            has_unread_for_assignee=False,
            estimated_value=1000,
            gamification_customer_id=gamification_customer.id,
        )
        incomplete_request = ShipmentRequest(
            shipping_type="domestic",
            contact_phone="09129999999",
            customer_first_name=None,
            customer_last_name="",
            status="new",
            status_request_status="new",
        )
        db.session.add_all([shipment_request, incomplete_request])
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=shipment_request.id,
            amount=1200000,
            currency="IRR",
            note="Existing quote",
            created_by_expert_id=business_expert.id,
        )
        opportunity = Opportunity(
            customer_id=phone_match_customer.id,
            title="Existing Opportunity",
            stage="lead",
            probability=10,
            status="open",
        )
        db.session.add_all([quote, opportunity])
        db.session.commit()
        return {
            "app": app,
            "token": create_session_tokens(business_expert.id)["access_token"],
            "expert_token": create_session_tokens(basic_expert.id)["access_token"],
            "request_id": shipment_request.id,
            "incomplete_request_id": incomplete_request.id,
            "phone_match_customer_id": phone_match_customer.id,
            "name_match_customer_id": name_match_customer.id,
            "business_expert_id": business_expert.id,
            "gamification_customer_id": gamification_customer.id,
        }


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _request_snapshot(request_row: ShipmentRequest) -> dict:
    return {
        "customer_id": request_row.customer_id,
        "status": request_row.status,
        "status_request_status": request_row.status_request_status,
        "assigned_to": request_row.assigned_to,
        "priority": request_row.priority,
        "sla_due_at": request_row.sla_due_at,
        "last_customer_touch_at": request_row.last_customer_touch_at,
        "has_unread_for_assignee": request_row.has_unread_for_assignee,
        "estimated_value": request_row.estimated_value,
        "gamification_customer_id": request_row.gamification_customer_id,
        "customer_first_name": request_row.customer_first_name,
        "customer_last_name": request_row.customer_last_name,
    }


def test_customer_create_preview_requires_crm_access(crm_customer_create_preview_app):
    """Preview requires CRM auth and rejects basic experts."""
    client = crm_customer_create_preview_app["app"].test_client()
    expert_headers = _auth_headers(crm_customer_create_preview_app["expert_token"])

    unauthenticated = client.get(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['request_id']}"
        "/customer-create-preview"
    )
    assert unauthenticated.status_code == 401

    rejected = client.get(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['request_id']}"
        "/customer-create-preview",
        headers=expert_headers,
    )
    assert rejected.status_code == 403


def test_customer_create_preview_returns_suggestions_duplicates_and_metadata(
    crm_customer_create_preview_app,
):
    """Preview returns safe suggestions and advisory duplicate candidates only."""
    client = crm_customer_create_preview_app["app"].test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    response = client.get(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['request_id']}"
        "/customer-create-preview",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["operation"] == "preview"
    assert data["preview_only"] is True
    assert data["shipment_request"] == {
        "id": crm_customer_create_preview_app["request_id"],
        "customer_id": None,
        "status": "assigned",
        "assigned_to": crm_customer_create_preview_app["business_expert_id"],
        "gamification_customer_id": crm_customer_create_preview_app["gamification_customer_id"],
    }
    assert data["suggested_customer"]["first_name"] == "Raw"
    assert data["suggested_customer"]["last_name"] == "Requester"
    assert data["suggested_customer"]["phone"] == "09125555555"
    assert data["suggested_customer"]["email"] is None
    assert data["suggested_customer"]["company_name"] is None
    assert data["suggested_customer"]["source"] == "shipment_request"
    assert data["suggested_customer"]["city"] == "Tehran"
    assert data["suggested_customer"]["country"] == "Iran"
    assert data["metadata"]["match_policy"] == "advisory_only"
    assert data["metadata"]["mutation_allowed"] is False
    assert data["metadata"]["can_create_without_user_review"] is False
    assert data["metadata"]["missing_fields"] == {
        "required": [],
        "recommended": ["company_name", "email", "mobile"],
    }

    candidates = data["duplicate_candidates"]
    assert [candidate["id"] for candidate in candidates] == [
        crm_customer_create_preview_app["phone_match_customer_id"],
        crm_customer_create_preview_app["name_match_customer_id"],
    ]
    assert candidates[0]["match_strength"] == "strong"
    assert candidates[0]["match_reasons"] == ["phone_or_mobile_exact"]
    assert candidates[1]["match_strength"] == "weak"
    assert candidates[1]["match_reasons"] == ["first_name_exact", "last_name_exact"]
    assert data["metadata"]["strong_duplicate_count"] == 1


def test_customer_create_preview_does_not_mutate_any_crm_or_shipment_state(
    crm_customer_create_preview_app,
):
    """Preview is read-only: no customer, link, audit, timeline, or lifecycle writes."""
    app = crm_customer_create_preview_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["request_id"],
        )
        before_snapshot = _request_snapshot(request_row)
        before_customer_count = Customer.query.count()
        before_audit_count = CRMCustomerLinkAudit.query.count()
        before_console_log_count = ExpertConsoleLog.query.count()
        before_quote_count = ExpertQuote.query.count()
        before_opportunity_count = Opportunity.query.count()
        before_gamification_count = CustomerGamification.query.count()
        before_gamification = db.session.get(
            CustomerGamification,
            crm_customer_create_preview_app["gamification_customer_id"],
        )
        before_points = before_gamification.loyalty_points

    response = client.get(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['request_id']}"
        "/customer-create-preview",
        headers=headers,
    )
    assert response.status_code == 200

    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["request_id"],
        )
        assert _request_snapshot(request_row) == before_snapshot
        assert Customer.query.count() == before_customer_count
        assert CRMCustomerLinkAudit.query.count() == before_audit_count
        assert ExpertConsoleLog.query.count() == before_console_log_count
        assert ExpertQuote.query.count() == before_quote_count
        assert Opportunity.query.count() == before_opportunity_count
        assert CustomerGamification.query.count() == before_gamification_count
        gamification_customer = db.session.get(
            CustomerGamification,
            crm_customer_create_preview_app["gamification_customer_id"],
        )
        assert gamification_customer.loyalty_points == before_points


def test_customer_create_preview_reports_missing_required_fields(
    crm_customer_create_preview_app,
):
    """Preview exposes missing Customer fields instead of inventing placeholders."""
    client = crm_customer_create_preview_app["app"].test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    response = client.get(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['incomplete_request_id']}"
        "/customer-create-preview",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["suggested_customer"]["first_name"] is None
    assert data["suggested_customer"]["last_name"] is None
    assert data["metadata"]["missing_fields"]["required"] == ["first_name", "last_name"]
    assert data["duplicate_candidates"] == []


def test_customer_create_preview_returns_404_for_missing_request(
    crm_customer_create_preview_app,
):
    """Missing shipment requests fail without writes."""
    app = crm_customer_create_preview_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    with app.app_context():
        before_customer_count = Customer.query.count()
        before_audit_count = CRMCustomerLinkAudit.query.count()
        before_console_log_count = ExpertConsoleLog.query.count()

    response = client.get(
        "/api/crm/shipment-requests/999999/customer-create-preview",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Shipment request not found"}
    with app.app_context():
        assert Customer.query.count() == before_customer_count
        assert CRMCustomerLinkAudit.query.count() == before_audit_count
        assert ExpertConsoleLog.query.count() == before_console_log_count


def test_create_customer_from_request_requires_duplicate_acknowledgement(
    crm_customer_create_preview_app,
):
    """Strong duplicate candidates block creation until explicitly acknowledged."""
    app = crm_customer_create_preview_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    with app.app_context():
        before_customer_count = Customer.query.count()
        before_audit_count = CRMCustomerLinkAudit.query.count()
        before_console_log_count = ExpertConsoleLog.query.count()

    response = client.post(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['request_id']}"
        "/create-customer",
        headers=headers,
        json={
            "customer": {
                "first_name": "Reviewed",
                "last_name": "Customer",
                "phone": "09125555555",
            },
            "link": True,
        },
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "Strong duplicate candidates require acknowledgement"
    }
    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["request_id"],
        )
        assert request_row.customer_id is None
        assert Customer.query.count() == before_customer_count
        assert CRMCustomerLinkAudit.query.count() == before_audit_count
        assert ExpertConsoleLog.query.count() == before_console_log_count


def test_create_customer_from_request_can_create_and_link_with_audit(
    crm_customer_create_preview_app,
):
    """Acknowledged create-and-link creates one Customer and link audit only."""
    app = crm_customer_create_preview_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["request_id"],
        )
        before_snapshot = _request_snapshot(request_row)
        before_customer_count = Customer.query.count()
        before_audit_count = CRMCustomerLinkAudit.query.count()
        before_console_log_count = ExpertConsoleLog.query.count()
        before_quote_count = ExpertQuote.query.count()
        before_opportunity_count = Opportunity.query.count()
        before_gamification_count = CustomerGamification.query.count()
        before_points = db.session.get(
            CustomerGamification,
            crm_customer_create_preview_app["gamification_customer_id"],
        ).loyalty_points

    response = client.post(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['request_id']}"
        "/create-customer",
        headers=headers,
        json={
            "customer": {
                "first_name": "Reviewed",
                "last_name": "Customer",
                "company_name": "Reviewed Co",
                "email": "reviewed@example.test",
                "phone": "09125555555",
                "mobile": "09120000000",
            },
            "duplicate_acknowledged": True,
            "link": True,
            "reason": "confirmed new legal entity",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["operation"] == "create_and_link"
    assert data["created_customer"]["company_name"] == "Reviewed Co"
    assert data["created_customer"]["phone"] == "09125555555"
    assert data["metadata"]["linked"] is True
    assert data["metadata"]["strong_duplicate_count"] == 1
    assert data["metadata"]["duplicate_acknowledged"] is True
    created_customer_id = data["created_customer"]["id"]
    assert data["shipment_request"]["customer_id"] == created_customer_id

    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["request_id"],
        )
        after_snapshot = _request_snapshot(request_row)
        assert after_snapshot == {**before_snapshot, "customer_id": created_customer_id}
        assert Customer.query.count() == before_customer_count + 1
        assert ExpertQuote.query.count() == before_quote_count
        assert Opportunity.query.count() == before_opportunity_count
        assert CustomerGamification.query.count() == before_gamification_count
        assert db.session.get(
            CustomerGamification,
            crm_customer_create_preview_app["gamification_customer_id"],
        ).loyalty_points == before_points
        created_customer = db.session.get(Customer, created_customer_id)
        assert created_customer.first_name == "Reviewed"
        assert created_customer.last_name == "Customer"
        assert created_customer.customer_type == "prospect"
        assert created_customer.status == "active"
        assert CRMCustomerLinkAudit.query.count() == before_audit_count + 1
        audit = CRMCustomerLinkAudit.query.filter_by(
            shipment_request_id=crm_customer_create_preview_app["request_id"],
            operation="create_and_link",
        ).one()
        assert audit.old_customer_id is None
        assert audit.new_customer_id == created_customer_id
        assert audit.reason == "confirmed new legal entity"
        assert audit.request_status_at_time == "assigned"
        assert audit.assigned_to_at_time == crm_customer_create_preview_app["business_expert_id"]
        assert (
            audit.gamification_customer_id_at_time
            == crm_customer_create_preview_app["gamification_customer_id"]
        )
        assert ExpertConsoleLog.query.count() == before_console_log_count + 1
        console_log = ExpertConsoleLog.query.filter_by(
            shipment_request_id=crm_customer_create_preview_app["request_id"],
            action="crm_customer_link",
        ).one()
        assert console_log.old_status == "assigned"
        assert console_log.new_status == "assigned"
        assert "CRM customer link create_and_link" in console_log.note


def test_create_customer_from_request_can_create_without_link_or_audit(
    crm_customer_create_preview_app,
):
    """Optional link=false creates a Customer without touching the request link."""
    app = crm_customer_create_preview_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["incomplete_request_id"],
        )
        before_snapshot = _request_snapshot(request_row)
        before_customer_count = Customer.query.count()
        before_audit_count = CRMCustomerLinkAudit.query.count()
        before_console_log_count = ExpertConsoleLog.query.count()

    response = client.post(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['incomplete_request_id']}"
        "/create-customer",
        headers=headers,
        json={
            "customer": {
                "first_name": "Standalone",
                "last_name": "Customer",
                "phone": "09129999999",
            },
            "link": False,
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["operation"] == "create"
    assert data["metadata"]["linked"] is False
    assert data["shipment_request"]["customer_id"] is None
    assert data["customer"] is None

    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["incomplete_request_id"],
        )
        assert _request_snapshot(request_row) == before_snapshot
        assert Customer.query.count() == before_customer_count + 1
        assert CRMCustomerLinkAudit.query.count() == before_audit_count
        assert ExpertConsoleLog.query.count() == before_console_log_count


def test_create_customer_from_request_rejects_invalid_payload_without_writes(
    crm_customer_create_preview_app,
):
    """Invalid reviewed data fails before Customer creation or link writes."""
    app = crm_customer_create_preview_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_create_preview_app["token"])

    with app.app_context():
        before_customer_count = Customer.query.count()
        before_audit_count = CRMCustomerLinkAudit.query.count()
        before_console_log_count = ExpertConsoleLog.query.count()

    response = client.post(
        f"/api/crm/shipment-requests/{crm_customer_create_preview_app['incomplete_request_id']}"
        "/create-customer",
        headers=headers,
        json={"customer": {"phone": "09129999999"}, "link": True},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Missing required customer fields: first_name, last_name"
    }
    with app.app_context():
        request_row = db.session.get(
            ShipmentRequest,
            crm_customer_create_preview_app["incomplete_request_id"],
        )
        assert request_row.customer_id is None
        assert Customer.query.count() == before_customer_count
        assert CRMCustomerLinkAudit.query.count() == before_audit_count
        assert ExpertConsoleLog.query.count() == before_console_log_count
