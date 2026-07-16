"""Contract tests for manual CRM customer linking to shipment requests."""
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
def crm_customer_link_app():
    """App with isolated CRM customer-link seed data."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        business_expert = ExpertUser(
            username="crm_link_business_expert",
            password_hash="unused",
            full_name="CRM Link Expert",
            email="crm-link-expert@example.test",
            role="business_expert",
            is_active=True,
        )
        basic_expert = ExpertUser(
            username="crm_link_basic_expert",
            password_hash="unused",
            full_name="Basic Expert",
            email="crm-link-basic@example.test",
            role="expert",
            is_active=True,
        )
        customer = Customer(
            first_name="Linked",
            last_name="Customer",
            company_name="Acme Logistics",
            email="linked@example.test",
            phone="09121111111",
            mobile="09122222222",
            customer_type="customer",
            status="active",
        )
        other_customer = Customer(
            first_name="Other",
            last_name="Customer",
            company_name="Other Logistics",
            email="other@example.test",
            phone="09123333333",
            customer_type="prospect",
            status="active",
        )
        gamification_customer = CustomerGamification(
            email="portal@example.test",
            phone="09124444444",
            first_name="Portal",
            last_name="Customer",
            is_email_verified=True,
            total_requests=1,
            loyalty_points=20,
        )
        db.session.add_all([
            business_expert,
            basic_expert,
            customer,
            other_customer,
            gamification_customer,
        ])
        db.session.flush()
        shipment_request = ShipmentRequest(
            shipping_type="domestic",
            contact_phone="09125555555",
            customer_first_name="Raw",
            customer_last_name="Requester",
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
        db.session.add(shipment_request)
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=shipment_request.id,
            amount=1200000,
            currency="IRR",
            note="Existing quote",
            created_by_expert_id=business_expert.id,
        )
        opportunity = Opportunity(
            customer_id=customer.id,
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
            "customer_id": customer.id,
            "other_customer_id": other_customer.id,
            "business_expert_id": business_expert.id,
            "gamification_customer_id": gamification_customer.id,
        }


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _request_snapshot(request_row: ShipmentRequest) -> dict:
    return {
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


def test_crm_customer_link_search_and_get_require_crm_access(crm_customer_link_app):
    """Search and link-state reads require CRM auth and reject basic experts."""
    client = crm_customer_link_app["app"].test_client()
    headers = _auth_headers(crm_customer_link_app["token"])
    expert_headers = _auth_headers(crm_customer_link_app["expert_token"])

    unauthenticated = client.get("/api/crm/customer-link/customers?search=Acme")
    assert unauthenticated.status_code == 401

    rejected = client.get("/api/crm/customer-link/customers?search=Acme", headers=expert_headers)
    assert rejected.status_code == 403

    rejected_get = client.get(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=expert_headers,
    )
    assert rejected_get.status_code == 403

    rejected_link = client.put(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=expert_headers,
        json={"customer_id": crm_customer_link_app["customer_id"]},
    )
    assert rejected_link.status_code == 403

    rejected_unlink = client.delete(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=expert_headers,
    )
    assert rejected_unlink.status_code == 403

    search_response = client.get("/api/crm/customer-link/customers?search=Acme", headers=headers)
    assert search_response.status_code == 200
    search_data = search_response.get_json()
    assert set(search_data.keys()) == {"customers", "pagination"}
    assert len(search_data["customers"]) == 1
    assert search_data["customers"][0]["id"] == crm_customer_link_app["customer_id"]
    assert set(search_data["customers"][0].keys()) == {
        "id",
        "name",
        "company_name",
        "email",
        "phone",
        "mobile",
        "customer_type",
        "status",
    }

    link_state = client.get(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
    )
    assert link_state.status_code == 200
    link_data = link_state.get_json()
    assert link_data["operation"] == "read"
    assert link_data["shipment_request"]["customer_id"] is None
    assert link_data["customer"] is None


def test_link_relink_and_unlink_preserve_shipment_operational_state(crm_customer_link_app):
    """Manual link changes only customer_id and audit, not shipment operations."""
    app = crm_customer_link_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_link_app["token"])

    with app.app_context():
        request_row = db.session.get(ShipmentRequest, crm_customer_link_app["request_id"])
        before_snapshot = _request_snapshot(request_row)
        before_quote_count = ExpertQuote.query.count()
        before_customer_count = Customer.query.count()
        before_opportunity_count = Opportunity.query.count()
        before_gamification = db.session.get(
            CustomerGamification,
            crm_customer_link_app["gamification_customer_id"],
        )
        before_points = before_gamification.loyalty_points

    link_response = client.put(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
        json={"customer_id": crm_customer_link_app["customer_id"], "note": "verified manually"},
    )
    assert link_response.status_code == 200
    link_data = link_response.get_json()
    assert link_data["operation"] == "link"
    assert link_data["shipment_request"]["customer_id"] == crm_customer_link_app["customer_id"]
    assert link_data["customer"]["company_name"] == "Acme Logistics"

    with app.app_context():
        linked_request = db.session.get(ShipmentRequest, crm_customer_link_app["request_id"])
        after_link_snapshot = _request_snapshot(linked_request)
        assert after_link_snapshot == before_snapshot
        assert linked_request.customer_id == crm_customer_link_app["customer_id"]
        assert ExpertQuote.query.count() == before_quote_count
        assert Customer.query.count() == before_customer_count
        assert Opportunity.query.count() == before_opportunity_count
        gamification_customer = db.session.get(
            CustomerGamification,
            crm_customer_link_app["gamification_customer_id"],
        )
        assert gamification_customer.loyalty_points == before_points
        link_log = ExpertConsoleLog.query.filter_by(
            shipment_request_id=crm_customer_link_app["request_id"],
            action="crm_customer_link",
        ).one()
        assert link_log.old_status == "assigned"
        assert link_log.new_status == "assigned"
        assert "old_customer_id=None" in link_log.note
        link_audit = CRMCustomerLinkAudit.query.filter_by(
            shipment_request_id=crm_customer_link_app["request_id"],
            operation="link",
        ).one()
        assert link_audit.old_customer_id is None
        assert link_audit.new_customer_id == crm_customer_link_app["customer_id"]
        assert link_audit.performed_by_user_id == crm_customer_link_app["business_expert_id"]
        assert link_audit.performed_by_role == "business_expert"
        assert link_audit.source == "crm_api"
        assert link_audit.reason == "verified manually"
        assert link_audit.request_status_at_time == "assigned"
        assert link_audit.assigned_to_at_time == crm_customer_link_app["business_expert_id"]
        assert (
            link_audit.gamification_customer_id_at_time
            == crm_customer_link_app["gamification_customer_id"]
        )

    noop_response = client.put(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
        json={"customer_id": crm_customer_link_app["customer_id"]},
    )
    assert noop_response.status_code == 200
    assert noop_response.get_json()["operation"] == "noop"

    relink_response = client.put(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
        json={"customer_id": crm_customer_link_app["other_customer_id"]},
    )
    assert relink_response.status_code == 200
    assert relink_response.get_json()["operation"] == "relink"

    unlink_response = client.delete(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
        json={"note": "wrong customer"},
    )
    assert unlink_response.status_code == 200
    unlink_data = unlink_response.get_json()
    assert unlink_data["operation"] == "unlink"
    assert unlink_data["shipment_request"]["customer_id"] is None
    assert unlink_data["customer"] is None

    with app.app_context():
        unlinked_request = db.session.get(ShipmentRequest, crm_customer_link_app["request_id"])
        assert _request_snapshot(unlinked_request) == before_snapshot
        assert unlinked_request.customer_id is None
        assert ExpertQuote.query.count() == before_quote_count
        assert Customer.query.count() == before_customer_count
        assert Opportunity.query.count() == before_opportunity_count
        assert ExpertConsoleLog.query.filter_by(
            shipment_request_id=crm_customer_link_app["request_id"],
            action="crm_customer_link",
        ).count() == 3
        audits = CRMCustomerLinkAudit.query.filter_by(
            shipment_request_id=crm_customer_link_app["request_id"],
        ).order_by(CRMCustomerLinkAudit.created_at.asc(), CRMCustomerLinkAudit.id.asc()).all()
        assert [audit.operation for audit in audits] == ["link", "relink", "unlink"]
        assert audits[0].old_customer_id is None
        assert audits[0].new_customer_id == crm_customer_link_app["customer_id"]
        assert audits[1].old_customer_id == crm_customer_link_app["customer_id"]
        assert audits[1].new_customer_id == crm_customer_link_app["other_customer_id"]
        assert audits[2].old_customer_id == crm_customer_link_app["other_customer_id"]
        assert audits[2].new_customer_id is None
        assert audits[2].reason == "wrong customer"


def test_crm_customer_link_rejects_invalid_and_missing_targets(crm_customer_link_app):
    """Invalid payloads and missing request/customer targets fail without writes."""
    app = crm_customer_link_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_link_app["token"])

    missing_payload = client.put(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
        json={},
    )
    assert missing_payload.status_code == 400
    assert missing_payload.get_json() == {"error": "customer_id is required"}

    invalid_payload = client.put(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
        json={"customer_id": "not-an-int"},
    )
    assert invalid_payload.status_code == 400
    assert invalid_payload.get_json() == {"error": "customer_id must be an integer"}

    missing_customer = client.put(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
        json={"customer_id": 999999},
    )
    assert missing_customer.status_code == 404
    assert missing_customer.get_json() == {"error": "CRM customer not found"}

    missing_request = client.put(
        "/api/crm/shipment-requests/999999/customer-link",
        headers=headers,
        json={"customer_id": crm_customer_link_app["customer_id"]},
    )
    assert missing_request.status_code == 404
    assert missing_request.get_json() == {"error": "Shipment request not found"}

    missing_get = client.get("/api/crm/shipment-requests/999999/customer-link", headers=headers)
    assert missing_get.status_code == 404
    assert missing_get.get_json() == {"error": "Shipment request not found"}

    missing_unlink = client.delete("/api/crm/shipment-requests/999999/customer-link", headers=headers)
    assert missing_unlink.status_code == 404
    assert missing_unlink.get_json() == {"error": "Shipment request not found"}

    with app.app_context():
        request_row = db.session.get(ShipmentRequest, crm_customer_link_app["request_id"])
        assert request_row.customer_id is None
        assert ExpertConsoleLog.query.filter_by(action="crm_customer_link").count() == 0
        assert CRMCustomerLinkAudit.query.count() == 0


def test_crm_customer_unlink_is_idempotent(crm_customer_link_app):
    """Unlinking an already unlinked request succeeds without audit noise."""
    app = crm_customer_link_app["app"]
    client = app.test_client()
    headers = _auth_headers(crm_customer_link_app["token"])

    response = client.delete(
        f"/api/crm/shipment-requests/{crm_customer_link_app['request_id']}/customer-link",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["operation"] == "noop"
    assert data["shipment_request"]["customer_id"] is None

    with app.app_context():
        assert ExpertConsoleLog.query.filter_by(action="crm_customer_link").count() == 0
        assert CRMCustomerLinkAudit.query.count() == 0
