"""Characterization tests for admin SLA policy backend foundation."""
from __future__ import annotations

from datetime import datetime, timedelta

import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest, SlaPolicy
from backend.security import security
from backend.services import sla_policy_service


@pytest.fixture
def sla_policy_app():
    """App with isolated DB and admin/expert users for SLA policy contracts."""
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
            username="phase11c_admin",
            password_hash=password_hash,
            full_name="Phase 11C Admin",
            email="phase11c-admin@example.test",
            role="admin",
            is_active=True,
        )
        expert = ExpertUser(
            username="phase11c_expert",
            password_hash=password_hash,
            full_name="Phase 11C Expert",
            email="phase11c-expert@example.test",
            role="expert",
            is_active=True,
        )
        db.session.add_all([admin, expert])
        db.session.commit()

        return {
            "app": app,
            "admin_token": security.generate_token(admin.id, "access"),
            "expert_token": security.generate_token(expert.id, "access"),
            "admin_id": admin.id,
            "expert_id": expert.id,
        }


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _valid_policy_payload(**overrides):
    payload = {
        "name": "Normal assigned SLA",
        "priority_scope": "normal",
        "request_status_scope": ["assigned", "in_progress"],
        "transport_method_scope": None,
        "shipping_type_scope": "all",
        "response_time_minutes": 120,
        "near_deadline_threshold_minutes": 60,
        "is_active": True,
        "sort_order": 20,
    }
    payload.update(overrides)
    return payload


def test_sla_policy_admin_auth_contract(sla_policy_app):
    """SLA policy endpoints are admin-only."""
    client = sla_policy_app["app"].test_client()
    admin_headers = _auth_headers(sla_policy_app["admin_token"])
    expert_headers = _auth_headers(sla_policy_app["expert_token"])

    missing_token = client.get("/api/admin/sla-policies")
    assert missing_token.status_code == 401
    assert missing_token.get_json() == {"error": "Token is missing"}

    forbidden_list = client.get("/api/admin/sla-policies", headers=expert_headers)
    assert forbidden_list.status_code == 403
    assert forbidden_list.get_json()["required_roles"] == ["admin"]

    forbidden_create = client.post(
        "/api/admin/sla-policies",
        headers=expert_headers,
        json=_valid_policy_payload(),
    )
    assert forbidden_create.status_code == 403
    assert forbidden_create.get_json()["required_roles"] == ["admin"]

    list_response = client.get("/api/admin/sla-policies", headers=admin_headers)
    assert list_response.status_code == 200
    assert list_response.get_json() == {"sla_policies": []}


def test_sla_policy_create_list_and_order_contract(sla_policy_app):
    """Admin can create SLA policies and list order remains deterministic."""
    client = sla_policy_app["app"].test_client()
    admin_headers = _auth_headers(sla_policy_app["admin_token"])

    second = client.post(
        "/api/admin/sla-policies",
        headers=admin_headers,
        json=_valid_policy_payload(name="Second", priority_scope="high", sort_order=20),
    )
    assert second.status_code == 201
    second_payload = second.get_json()
    assert set(second_payload.keys()) == {"message", "sla_policy"}
    assert second_payload["sla_policy"]["name"] == "Second"
    assert second_payload["sla_policy"]["is_active"] is True

    first = client.post(
        "/api/admin/sla-policies",
        headers=admin_headers,
        json=_valid_policy_payload(name="First", priority_scope="urgent", sort_order=10),
    )
    assert first.status_code == 201

    list_response = client.get("/api/admin/sla-policies", headers=admin_headers)
    assert list_response.status_code == 200
    policies = list_response.get_json()["sla_policies"]
    assert [policy["name"] for policy in policies] == ["First", "Second"]
    assert set(policies[0].keys()) == {
        "id",
        "name",
        "priority_scope",
        "request_status_scope",
        "transport_method_scope",
        "shipping_type_scope",
        "response_time_minutes",
        "near_deadline_threshold_minutes",
        "is_active",
        "sort_order",
        "created_at",
        "updated_at",
    }


def test_sla_policy_create_validation_contract(sla_policy_app):
    """Create validation keeps clear 400 errors for invalid SLA policy payloads."""
    client = sla_policy_app["app"].test_client()
    admin_headers = _auth_headers(sla_policy_app["admin_token"])

    invalid_payloads = [
        {},
        _valid_policy_payload(name=" "),
        _valid_policy_payload(priority_scope="medium"),
        _valid_policy_payload(request_status_scope=[]),
        _valid_policy_payload(response_time_minutes=0),
        _valid_policy_payload(near_deadline_threshold_minutes=0),
        _valid_policy_payload(response_time_minutes=30, near_deadline_threshold_minutes=60),
        _valid_policy_payload(is_active="yes"),
        _valid_policy_payload(sort_order=True),
        _valid_policy_payload(shipping_type_scope="regional"),
    ]

    for payload in invalid_payloads:
        response = client.post("/api/admin/sla-policies", headers=admin_headers, json=payload)
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_sla_policy_update_disable_enable_contract(sla_policy_app):
    """Admin can update and idempotently disable/enable SLA policies."""
    client = sla_policy_app["app"].test_client()
    admin_headers = _auth_headers(sla_policy_app["admin_token"])

    create_response = client.post(
        "/api/admin/sla-policies",
        headers=admin_headers,
        json=_valid_policy_payload(),
    )
    policy_id = create_response.get_json()["sla_policy"]["id"]

    update_response = client.put(
        f"/api/admin/sla-policies/{policy_id}",
        headers=admin_headers,
        json={
            "name": "Updated normal SLA",
            "priority_scope": "all",
            "request_status_scope": ["assigned"],
            "response_time_minutes": 90,
            "near_deadline_threshold_minutes": 30,
            "sort_order": 5,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()["sla_policy"]
    assert updated["name"] == "Updated normal SLA"
    assert updated["priority_scope"] == "all"
    assert updated["request_status_scope"] == ["assigned"]
    assert updated["response_time_minutes"] == 90
    assert updated["near_deadline_threshold_minutes"] == 30
    assert updated["sort_order"] == 5

    invalid_update = client.put(
        f"/api/admin/sla-policies/{policy_id}",
        headers=admin_headers,
        json={"near_deadline_threshold_minutes": 120},
    )
    assert invalid_update.status_code == 400

    missing_update = client.put("/api/admin/sla-policies/999999", headers=admin_headers, json={"name": "Missing"})
    assert missing_update.status_code == 404

    disable_response = client.patch(f"/api/admin/sla-policies/{policy_id}/disable", headers=admin_headers)
    assert disable_response.status_code == 200
    assert disable_response.get_json()["sla_policy"]["is_active"] is False

    repeat_disable = client.patch(f"/api/admin/sla-policies/{policy_id}/disable", headers=admin_headers)
    assert repeat_disable.status_code == 200
    assert repeat_disable.get_json()["sla_policy"]["is_active"] is False

    enable_response = client.patch(f"/api/admin/sla-policies/{policy_id}/enable", headers=admin_headers)
    assert enable_response.status_code == 200
    assert enable_response.get_json()["sla_policy"]["is_active"] is True


def test_sla_policy_service_resolution_and_calculation_contract(sla_policy_app):
    """SLA policy service resolves policies and calculates due/status with legacy fallback."""
    now = datetime.utcnow()

    with sla_policy_app["app"].app_context():
        assert sla_policy_service.resolve_sla_policy("normal", "assigned") is None
        assert sla_policy_service.calculate_due_at(now) == now + timedelta(minutes=120)
        assert sla_policy_service.calculate_sla_status(None, now=now) == "on_time"
        assert sla_policy_service.calculate_sla_status(now + timedelta(hours=3), now=now) == "on_time"
        assert sla_policy_service.calculate_sla_status(now + timedelta(hours=1), now=now) == "due_soon"
        assert sla_policy_service.calculate_sla_status(now - timedelta(minutes=1), now=now) == "overdue"

        urgent_policy = SlaPolicy(
            name="Urgent assigned SLA",
            priority_scope="urgent",
            request_status_scope='["assigned"]',
            shipping_type_scope="domestic",
            response_time_minutes=45,
            near_deadline_threshold_minutes=15,
            is_active=True,
            sort_order=1,
            created_at=now,
            updated_at=now,
        )
        fallback_policy = SlaPolicy(
            name="All assigned SLA",
            priority_scope="all",
            request_status_scope='["assigned", "in_progress"]',
            response_time_minutes=120,
            near_deadline_threshold_minutes=30,
            is_active=True,
            sort_order=100,
            created_at=now,
            updated_at=now,
        )
        db.session.add_all([urgent_policy, fallback_policy])
        db.session.commit()

        request_row = ShipmentRequest(
            tracking_code="SR-P11C-SERVICE",
            shipping_type="domestic",
            contact_phone="09126000001",
            status_request_status="new",
            status="assigned",
            priority="urgent",
            domestic_transport_method="road",
        )
        db.session.add(request_row)
        db.session.commit()

        resolved = sla_policy_service.resolve_sla_policy(request_row)
        assert resolved.id == urgent_policy.id
        assert sla_policy_service.calculate_due_at(now, resolved) == now + timedelta(minutes=45)
        assert sla_policy_service.calculate_sla_status(now + timedelta(minutes=20), resolved, now=now) == "on_time"
        assert sla_policy_service.calculate_sla_status(now + timedelta(minutes=10), resolved, now=now) == "due_soon"
        assert sla_policy_service.calculate_sla_status(now - timedelta(seconds=1), resolved, now=now) == "overdue"

        all_policy = sla_policy_service.resolve_sla_policy("low", "in_progress")
        assert all_policy.id == fallback_policy.id

        urgent_policy.is_active = False
        db.session.commit()
        assert sla_policy_service.resolve_sla_policy(request_row).id == fallback_policy.id
