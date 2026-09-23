"""Focused contracts for optional Customer Portal accounts."""
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import CustomerGamification, CustomerPortalAccountAudit, CustomerPortalRecoveryRequest, CustomerPortalRecoveryToken, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import OrganizationHostname, OperationalMembership, OperationalOrganization
from backend.security import security
from backend.services.auth_session_service import create_session_tokens
from backend.services.customer_account_lifecycle_service import issue_recovery_token
from backend.services.customer_portal_auth import CustomerPortalAuthError
from backend.services.shipment_service import (
    ShipmentValidationError, build_shipment_request_data, normalize_shipment_payload,
    validate_portal_organization_binding,
)


@pytest.fixture()
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SERVER_NAME": "portal.synthetic.test",
    })
    with app.app_context():
        organization = OperationalOrganization(name="Portal Signup Tenant")
        db.session.add(organization)
        db.session.flush()
        db.session.add(OrganizationHostname(
            organization_id=organization.id,
            hostname="portal.synthetic.test",
            is_primary=True,
            is_active=True,
        ))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app): return app.test_client()


def _register(client, email="portal@example.com"):
    response = client.post("/api/customer/register", base_url="https://portal.synthetic.test", json={
        "email": email, "phone": "09121234567", "password": "correct-horse-1",
        "first_name": "Synthetic", "last_name": "Customer",
    })
    assert response.status_code == 201
    return response.get_json()


def test_registration_login_session_and_change_password_revoke_generation(app, client):
    session = _register(client)
    assert session["authenticated"] is True
    logged_out = client.post(
        "/api/customer/logout", headers={"X-CSRF-Token": session["csrf_token"]}
    )
    assert logged_out.status_code == 200
    assert client.get("/api/customer/session").get_json() == {"authenticated": False}
    assert client.post(
        "/api/customer/login",
        json={"email": "portal@example.com", "password": "wrong-password-1"},
    ).status_code == 401
    logged_in = client.post(
        "/api/customer/login",
        json={"email": "portal@example.com", "password": "correct-horse-1"},
    )
    assert logged_in.status_code == 200
    csrf = logged_in.get_json()["csrf_token"]
    changed = client.post("/api/customer/password/change", headers={"X-CSRF-Token": csrf}, json={
        "current_password": "correct-horse-1", "new_password": "correct-horse-2",
    })
    assert changed.status_code == 200
    assert client.get("/api/customer/session").get_json() == {"authenticated": False}
    assert client.post("/api/customer/login", json={"email": "portal@example.com", "password": "correct-horse-1"}).status_code == 401
    assert client.post("/api/customer/login", json={"email": "portal@example.com", "password": "correct-horse-2"}).status_code == 200
    with app.app_context():
        assert CustomerPortalAccountAudit.query.filter_by(action="password_changed").count() == 1


def test_legacy_no_password_registration_never_grants_private_authority(app, client):
    response = client.post("/api/customer/register", json={
        "email": "legacy@example.com", "phone": "09121111111",
    })
    assert response.status_code == 201
    assert client.get("/api/customer/session").get_json() == {"authenticated": False}
    assert client.get("/api/customer/requests").status_code == 401
    with app.app_context():
        customer = CustomerGamification.query.filter_by(email="legacy@example.com").one()
        assert customer.password_hash is None


def test_password_signup_fails_closed_without_server_resolved_organization(app, client):
    with app.app_context():
        OrganizationHostname.query.update({"is_active": False})
        db.session.commit()
    response = client.post(
        "/api/customer/register",
        json={
            "email": "unscoped@example.com", "phone": "09121111112",
            "password": "correct-horse-1",
        },
    )
    assert response.status_code == 409
    assert response.get_json()["code"] == "ORGANIZATION_CONTEXT_REQUIRED"
    with app.app_context():
        assert CustomerGamification.query.filter_by(email="unscoped@example.com").count() == 0


def test_forgot_is_enumeration_safe_and_emailed_token_is_single_use(app, client, monkeypatch):
    delivered = []
    monkeypatch.setattr(
        "backend.services.customer_recovery_email_service.send_password_recovery_email",
        lambda recipient, reset_url, expires_at: delivered.append((recipient, reset_url, expires_at)) or "SENT",
    )
    _register(client)
    known = client.post("/api/customer/password/forgot", json={"email": "portal@example.com"})
    unknown = client.post("/api/customer/password/forgot", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.get_json() == unknown.get_json()
    assert len(delivered) == 1
    assert delivered[0][0] == "portal@example.com"
    token = parse_qs(urlparse(delivered[0][1]).query)["token"][0]
    with app.app_context():
        recovery = CustomerPortalRecoveryRequest.query.one()
        assert recovery.delivery_channel == "EMAIL"
        assert recovery.delivery_status == "SENT"
    first = client.post("/api/customer/password/reset", json={"token": token, "new_password": "new-password-123"})
    replay = client.post("/api/customer/password/reset", json={"token": token, "new_password": "new-password-456"})
    assert first.status_code == 200
    assert replay.status_code == 400


def test_nonproduction_recovery_suppresses_delivery_and_revokes_token(app, client):
    _register(client)
    response = client.post("/api/customer/password/forgot", json={"email": "portal@example.com"})
    assert response.status_code == 202
    with app.app_context():
        recovery = CustomerPortalRecoveryRequest.query.one()
        token = CustomerPortalRecoveryToken.query.one()
        assert recovery.delivery_status == "SUPPRESSED"
        assert recovery.delivery_attempted_at is not None
        assert token.revoked_at is not None


def test_unexpected_delivery_boundary_failure_is_safe_and_revokes_token(app, client, monkeypatch):
    def fail_delivery(*args, **kwargs):
        raise RuntimeError("unexpected provider failure containing token=secret")

    monkeypatch.setattr(
        "backend.services.customer_recovery_email_service.send_password_recovery_email",
        fail_delivery,
    )
    _register(client)
    response = client.post("/api/customer/password/forgot", json={"email": "portal@example.com"})
    assert response.status_code == 202
    with app.app_context():
        assert CustomerPortalRecoveryRequest.query.one().delivery_status == "FAILED"
        assert CustomerPortalRecoveryToken.query.one().revoked_at is not None


def test_private_quote_response_requires_session_csrf_ownership_and_version(app, client):
    session = _register(client)
    with app.app_context():
        customer = CustomerGamification.query.filter_by(email="portal@example.com").one()
        expert = ExpertUser(username="synthetic-expert", password_hash="x", full_name="Synthetic Expert")
        db.session.add(expert); db.session.flush()
        shipment = ShipmentRequest(shipping_type="domestic", contact_phone="09121234567", gamification_customer_id=customer.id, status="quoted")
        db.session.add(shipment); db.session.flush()
        quote = ExpertQuote(shipment_request_id=shipment.id, amount=1000, currency="IRR", created_by_expert_id=expert.id, valid_until=date.today() + timedelta(days=1))
        db.session.add(quote); db.session.commit()
        request_public_id, quote_public_id = shipment.public_id, quote.public_id
    no_csrf = client.post(f"/api/customer/requests/{request_public_id}/quotes/{quote_public_id}/response", json={"response": "accepted", "expected_response_version": 0})
    assert no_csrf.status_code == 403
    response = client.post(
        f"/api/customer/requests/{request_public_id}/quotes/{quote_public_id}/response",
        headers={"X-CSRF-Token": session["csrf_token"]},
        json={"response": "accepted", "expected_response_version": 0},
    )
    assert response.status_code == 200
    assert response.get_json()["quote"]["response_version"] == 1
    assert client.post("/api/customer/quote-response/legacy", json={"response": "accepted"}).status_code == 404


def test_client_supplied_owner_is_not_normalized_or_persisted(app):
    with app.app_context():
        normalized = normalize_shipment_payload({
            "shipping_type": "domestic", "origin_province_id": 1, "dest_province_id": 2,
            "contact_phone": "09121234567", "gamification_customer_id": 999,
        })
        assert "gamification_customer_id" not in normalized
        data = build_shipment_request_data(normalized, __import__("datetime").datetime.utcnow(), gamification_customer_id=7)
        assert data["gamification_customer_id"] == 7


def test_authenticated_account_cannot_cross_hostname_tenant(app):
    with app.app_context():
        customer = CustomerGamification(
            email="tenant-a@example.com", phone="09120000001", account_status="ACTIVE",
            operational_organization_id=101,
        )
        db.session.add(customer); db.session.commit()
        foreign_org = type("Organization", (), {"id": 202})()
        with pytest.raises(ShipmentValidationError) as caught:
            validate_portal_organization_binding(customer.id, foreign_org)
        assert caught.value.status_code == 403
        assert caught.value.code == "PORTAL_ORGANIZATION_MISMATCH"


def test_enrollment_cannot_be_used_as_an_alternate_reset(app):
    with app.app_context():
        customer = CustomerGamification(
            email="already-enrolled@example.com", phone="09120000002",
            password_hash="already-has-a-credential", account_status="ACTIVE",
        )
        db.session.add(customer); db.session.commit()
        with pytest.raises(CustomerPortalAuthError) as caught:
            issue_recovery_token(customer, "ENROLLMENT")
        assert caught.value.status_code == 409
        assert caught.value.code == "ACCOUNT_ALREADY_ENROLLED"


def test_disabled_account_cannot_login_or_use_existing_private_session(app, client):
    _register(client)
    with app.app_context():
        customer = CustomerGamification.query.filter_by(email="portal@example.com").one()
        customer.account_status = "DISABLED"; db.session.commit()
    private = client.get("/api/customer/requests")
    login = client.post("/api/customer/login", json={"email": "portal@example.com", "password": "correct-horse-1"})
    assert private.status_code == login.status_code == 401
    assert login.get_json()["code"] == "ACCOUNT_DISABLED"


def test_expired_reset_and_single_use_enrollment_tokens(app, client):
    with app.app_context():
        reset_customer = CustomerGamification(email="reset@example.com", phone="09120000003", password_hash=security.hash_password("old-password-1"), account_status="ACTIVE")
        enrollment_customer = CustomerGamification(email="enroll@example.com", phone="09120000004", password_hash=None, account_status="ACTIVE")
        db.session.add_all([reset_customer, enrollment_customer]); db.session.commit()
        expired = issue_recovery_token(reset_customer, "RESET")
        CustomerPortalRecoveryToken.query.filter_by(customer_id=reset_customer.id).update({"expires_at": datetime.utcnow() - timedelta(seconds=1)})
        db.session.commit()
        enrollment = issue_recovery_token(enrollment_customer, "ENROLLMENT")
    assert client.post("/api/customer/password/reset", json={"token": expired, "new_password": "replacement-1"}).status_code == 400
    first = client.post("/api/customer/enrollment/complete", json={"token": enrollment, "new_password": "enrolled-password-1"})
    replay = client.post("/api/customer/enrollment/complete", json={"token": enrollment, "new_password": "enrolled-password-2"})
    assert first.status_code == 200
    assert replay.status_code == 400


def test_cross_customer_request_is_nondisclosing_and_pagination_exceeds_five(app, client):
    _register(client)
    with app.app_context():
        owner = CustomerGamification.query.filter_by(email="portal@example.com").one()
        other = CustomerGamification(email="other-owner@example.com", phone="09120000005", account_status="ACTIVE")
        db.session.add(other); db.session.flush()
        rows = [ShipmentRequest(shipping_type="domestic", contact_phone=owner.phone, gamification_customer_id=owner.id, status="new") for _ in range(7)]
        foreign = ShipmentRequest(shipping_type="domestic", contact_phone=other.phone, gamification_customer_id=other.id, status="new")
        db.session.add_all([*rows, foreign]); db.session.commit()
        foreign_public_id = foreign.public_id
    page = client.get("/api/customer/requests?per_page=5&page=1").get_json()
    assert len(page["items"]) == 5
    assert page["pagination"]["total"] == 7
    assert page["pagination"]["has_next"] is True
    assert client.get(f"/api/customer/requests/{foreign_public_id}").status_code == 404


def test_organization_admin_support_is_same_org_and_uses_email_for_reset(app, client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.customer_recovery_email_service.send_password_recovery_email",
        lambda recipient, reset_url, expires_at: "SENT",
    )
    with app.app_context():
        org = OperationalOrganization(name="Synthetic Tenant")
        other_org = OperationalOrganization(name="Foreign Tenant")
        admin = ExpertUser(username="org-admin", password_hash="x", full_name="Org Admin", role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        platform_admin = ExpertUser(username="platform-admin", password_hash="x", full_name="Platform Admin", role="admin", authority="PLATFORM_ADMIN", is_active=True)
        db.session.add_all([org, other_org, admin, platform_admin]); db.session.flush()
        db.session.add(OperationalMembership(organization_id=org.id, user_id=admin.id, is_active=True))
        enrolled = CustomerGamification(email="managed@example.com", phone="09120000006", password_hash=security.hash_password("managed-password-1"), account_status="ACTIVE", operational_organization_id=org.id)
        invite = CustomerGamification(email="invite@example.com", phone="09120000007", password_hash=None, account_status="ACTIVE", operational_organization_id=org.id)
        foreign = CustomerGamification(email="foreign@example.com", phone="09120000008", password_hash=None, account_status="ACTIVE", operational_organization_id=other_org.id)
        db.session.add_all([enrolled, invite, foreign]); db.session.commit()
        token = create_session_tokens(admin.id)["access_token"]; db.session.commit()
        platform_token = create_session_tokens(platform_admin.id)["access_token"]; db.session.commit()
        enrolled_id, invite_id, foreign_id = enrolled.public_id, invite.public_id, foreign.public_id
    headers = {"Authorization": f"Bearer {token}"}
    listed = client.get("/api/admin/customer-portal-accounts", headers=headers)
    assert listed.status_code == 200
    assert {item["public_id"] for item in listed.get_json()["items"]} == {enrolled_id, invite_id}
    exact = client.get(
        f"/api/admin/customer-portal-accounts?q={invite_id}", headers=headers
    )
    assert exact.status_code == 200
    assert exact.get_json()["items"][0]["enrollment_state"] == "PENDING_ENROLLMENT"
    assert client.get(
        "/api/admin/customer-portal-accounts",
        headers={"Authorization": f"Bearer {platform_token}"},
    ).status_code == 403
    disabled = client.post(f"/api/admin/customer-portal-accounts/{enrolled_id}/status", headers=headers, json={"status": "DISABLED"})
    enabled = client.post(f"/api/admin/customer-portal-accounts/{enrolled_id}/status", headers=headers, json={"status": "ACTIVE"})
    assert disabled.status_code == enabled.status_code == 200
    reset = client.post(f"/api/admin/customer-portal-accounts/{enrolled_id}/recovery", headers=headers, json={})
    enrollment = client.post(f"/api/admin/customer-portal-accounts/{invite_id}/enrollment", headers=headers, json={})
    foreign_attempt = client.post(f"/api/admin/customer-portal-accounts/{foreign_id}/enrollment", headers=headers, json={})
    assert reset.status_code == 202
    assert enrollment.status_code == 201
    assert reset.get_json()["delivery_channel"] == "EMAIL"
    assert reset.get_json()["delivery_status"] == "SENT"
    assert "path" not in reset.get_json() and "token" not in reset.get_json()
    assert "token=" in enrollment.get_json()["path"]
    assert foreign_attempt.status_code == 404
