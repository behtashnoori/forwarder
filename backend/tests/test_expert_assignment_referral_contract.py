"""Characterization tests for expert console, assignment, and referral contracts."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    AssignmentLog,
    AssignmentRule,
    ExpertConsoleLog,
    ExpertConsoleMessage,
    ExpertConsoleNotification,
    ExpertQuote,
    ExpertUser,
    Province,
    ReferralAssignmentLog,
    ReferralRule,
    ShipmentRequest,
)
from backend.services.auth_session_service import create_session_tokens
from backend.operational_models import OperationalMembership, OperationalOrganization


@pytest.fixture
def expert_contract_app():
    """App with isolated DB and expert/assignment/referral seed data."""
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
            username="phase4h_admin",
            password_hash=password_hash,
            full_name="Phase 4H Admin",
            email="phase4h-admin@example.test",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        expert = ExpertUser(
            username="phase4h_expert",
            password_hash=password_hash,
            full_name="Phase 4H Expert",
            email="phase4h-expert@example.test",
            role="expert",
            is_active=True,
        )
        other_expert = ExpertUser(
            username="phase4h_other_expert",
            password_hash=password_hash,
            full_name="Phase 4H Other Expert",
            email="phase4h-other@example.test",
            role="expert",
            is_active=True,
        )
        organization = OperationalOrganization(name="Expert Contract Organization")
        db.session.add_all([admin, expert, other_expert, organization])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(
                organization_id=organization.id,
                user_id=user.id,
                permissions=["request.read"] if user is admin else [],
            )
            for user in (admin, expert, other_expert)
        ])

        province = Province(code="phase4h", name_fa="Phase 4H Province")
        db.session.add(province)
        db.session.flush()

        request_row = ShipmentRequest(
            ownership_scope="TENANT", operational_organization_id=organization.id,
            tracking_code="SR-P4H001",
            shipping_type="domestic",
            contact_phone="09123456789",
            customer_first_name="Ali",
            customer_last_name="Rahimi",
            transport_method="road",
            domestic_transport_method="road",
            transport_method_preference="customer_choice",
            cargo_description="Phase 4H cargo",
            cargo_weight=12.5,
            cargo_volume=3.0,
            cargo_value=1000.0,
            special_instructions="Keep dry",
            status_request_status="new",
            status="new",
            priority="normal",
            assigned_to=expert.id,
            has_unread_for_assignee=True,
            sla_due_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.session.add(request_row)
        db.session.flush()

        notification = ExpertConsoleNotification(
            expert_user_id=expert.id,
            shipment_request_id=request_row.id,
            notification_type="seed",
            title="Seed notification",
            message="Seed message",
            is_read=False,
            created_at=datetime.utcnow(),
        )
        assignment_rule = AssignmentRule(
            name="High priority rule",
            description="Seed assignment rule",
            rule_type="priority",
            conditions=json.dumps({"priority": "high"}),
            priority=10,
            is_active=True,
            created_by=admin.id,
            operational_organization_id=organization.id,
        )
        referral_rule = ReferralRule(
            name="Pool referral rule",
            is_active=True,
            priority=1,
            conditions=json.dumps({"shipping_type": "domestic"}),
            action=json.dumps(
                {
                    "type": "pool_assign",
                    "expert_ids": [expert.id, other_expert.id],
                    "strategy": "round_robin",
                }
            ),
            stop_on_match=True,
            created_by=admin.id,
            operational_organization_id=organization.id,
        )
        db.session.add_all([notification, assignment_rule, referral_rule])
        db.session.commit()

        return {
            "app": app,
            "organization_id": organization.id,
            "admin_id": admin.id,
            "expert_id": expert.id,
            "other_expert_id": other_expert.id,
            "province_id": province.id,
            "request_id": request_row.id,
            "referral_rule_id": referral_rule.id,
            "admin_token": create_session_tokens(admin.id)["access_token"],
            "expert_token": create_session_tokens(expert.id)["access_token"],
            "other_expert_token": create_session_tokens(other_expert.id)[
                "access_token"
            ],
        }


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _international_request_payload(phone: str, cargo_description: str) -> dict:
    return {
        "shipping_type": "international",
        "origin_country": "Turkey",
        "origin_city_international": "Istanbul",
        "dest_country": "Iran",
        "dest_city_international": "Tehran",
        "contact_phone": phone,
        "customer_first_name": "Public",
        "customer_last_name": "RoundRobin",
        "international_transport_method": "air",
        "transport_method_preference": "customer_choice",
        "cargo_description": cargo_description,
    }


def test_expert_auth_login_refresh_logout_contract(expert_contract_app):
    """Expert auth endpoints keep current login, refresh, and logout response shapes."""
    client = expert_contract_app["app"].test_client()

    login_response = client.post(
        "/api/expert/auth/login",
        json={"username": "phase4h_admin", "password": "test123"},
        headers={"Origin": "http://127.0.0.1:3000"},
    )
    assert login_response.status_code == 200
    login_data = login_response.get_json()
    assert set(login_data.keys()) == {"success", "expert", "tokens"}
    assert login_data["success"] is True
    assert set(login_data["expert"].keys()) == {
        "id",
        "username",
        "full_name",
        "email",
        "role",
        "authority",
    }
    assert {"access_token", "refresh_token", "token_type", "expires_in"}.issubset(
        login_data["tokens"].keys()
    )
    assert login_response.headers["Access-Control-Allow-Credentials"] == "true"

    refresh_response = client.post(
        "/api/expert/auth/refresh",
        json={"refresh_token": login_data["tokens"]["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert {"access_token", "refresh_token", "token_type", "expires_in"}.issubset(
        refresh_response.get_json().keys()
    )

    logout_response = client.post(
        "/api/expert/auth/logout",
        headers=_auth_headers(login_data["tokens"]["access_token"]),
    )
    assert logout_response.status_code == 200
    assert logout_response.get_json() == {"message": "با موفقیت خارج شدید"}


def test_expert_request_read_contracts_and_access_errors(expert_contract_app):
    """Expert request list/detail endpoints keep auth, access, pagination, and response shapes."""
    client = expert_contract_app["app"].test_client()
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    other_headers = _auth_headers(expert_contract_app["other_expert_token"])

    unauthenticated = client.get("/api/expert/requests")
    assert unauthenticated.status_code == 401
    assert unauthenticated.get_json() == {"error": "Token is missing"}

    unauthenticated_detail = client.get(
        f"/api/expert/requests/{expert_contract_app['request_id']}"
    )
    assert unauthenticated_detail.status_code == 401
    assert unauthenticated_detail.get_json() == {"error": "Token is missing"}

    list_response = client.get(
        "/api/expert/requests?per_page=1", headers=expert_headers
    )
    assert list_response.status_code == 200
    list_data = list_response.get_json()
    assert set(list_data.keys()) == {"requests", "pagination"}
    assert set(list_data["pagination"].keys()) == {
        "page",
        "per_page",
        "total",
        "pages",
        "has_next",
        "has_prev",
    }
    assert len(list_data["requests"]) == 1
    assert set(list_data["requests"][0].keys()) == {
        "id",
        "public_id",
        "tracking_number",
        "status",
        "priority",
        "created_at",
        "sla_due_at",
        "sla_status",
        "assigned_to",
        "customer",
        "route",
        "transport_method",
        "international_transport_method",
        "domestic_transport_method",
        "transport_method_preference",
        "cargo",
        "has_unread",
    }

    missing_detail = client.get("/api/expert/requests/999999", headers=expert_headers)
    assert missing_detail.status_code == 404
    assert missing_detail.get_json() == {"error": "درخواست یافت نشد"}

    forbidden_detail = client.get(
        f"/api/expert/requests/{expert_contract_app['request_id']}",
        headers=other_headers,
    )
    assert forbidden_detail.status_code == 403
    assert forbidden_detail.get_json() == {"error": "شما به این درخواست دسترسی ندارید"}

    detail_response = client.get(
        f"/api/expert/requests/{expert_contract_app['request_id']}",
        headers=expert_headers,
    )
    assert detail_response.status_code == 200
    detail_data = detail_response.get_json()
    assert set(detail_data.keys()) == {
        "id",
        "public_id",
        "tracking_number",
        "status",
        "priority",
        "created_at",
        "sla_due_at",
        "sla_status",
        "assigned_to",
        "customer",
        "route",
        "transport_method",
        "international_transport_method",
        "domestic_transport_method",
        "transport_method_preference",
        "cargo",
        "dates",
        "timeline",
        "messages",
        "has_unread",
        "latest_quote",
    }
    assert set(detail_data["assigned_to"].keys()) == {"id", "name", "username"}
    assert detail_data["assigned_to"]["id"] == expert_contract_app["expert_id"]
    assert {
        "transport_method": detail_data["transport_method"],
        "international_transport_method": detail_data["international_transport_method"],
        "domestic_transport_method": detail_data["domestic_transport_method"],
        "transport_method_preference": detail_data["transport_method_preference"],
    } == {
        "transport_method": "road",
        "international_transport_method": None,
        "domestic_transport_method": "road",
        "transport_method_preference": "customer_choice",
    }
    opaque_detail = client.get(
        f"/api/expert/requests/{detail_data['public_id']}", headers=expert_headers
    )
    assert opaque_detail.status_code == 200
    assert opaque_detail.get_json()["public_id"] == detail_data["public_id"]
    assert client.get(
        "/api/expert/requests/not-a-uuid", headers=expert_headers
    ).status_code == 404
    assert set(detail_data["customer"].keys()) == {
        "first_name",
        "last_name",
        "phone",
        "full_name",
    }
    assert detail_data["customer"]["full_name"] == "Ali Rahimi"
    assert set(detail_data["route"].keys()) == {
        "origin",
        "destination",
        "shipping_type",
        "iran_destination",
        "canonical_ids",
        "location_state",
    }
    assert detail_data["route"]["location_state"] == "canonical"
    assert detail_data["route"]["canonical_ids"] == {
        "origin_country_id": None,
        "origin_international_city_id": None,
        "dest_country_id": None,
        "dest_international_city_id": None,
    }
    endpoint_keys = {
        "province",
        "county",
        "city",
        "country",
        "international_city",
        "address",
    }
    assert set(detail_data["route"]["origin"].keys()) == endpoint_keys
    assert set(detail_data["route"]["destination"].keys()) == endpoint_keys
    assert set(detail_data["cargo"].keys()) == {
        "description",
        "weight",
        "volume",
        "value",
        "special_instructions",
    }
    assert detail_data["cargo"]["description"] == "Phase 4H cargo"
    assert set(detail_data["dates"].keys()) == {"pickup_date", "delivery_date"}
    assert detail_data["latest_quote"] is None
    assert detail_data["messages"] == []
    assert detail_data["timeline"] == []


def test_expert_request_list_filters_visibility_and_order_contract(expert_contract_app):
    """Request list keeps current visibility, filters, pagination, and ordering."""
    client = expert_contract_app["app"].test_client()
    admin_headers = _auth_headers(expert_contract_app["admin_token"])
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    other_headers = _auth_headers(expert_contract_app["other_expert_token"])
    expert_id = expert_contract_app["expert_id"]
    other_expert_id = expert_contract_app["other_expert_id"]
    base_time = datetime(2026, 1, 1, 10, 0, 0)

    with expert_contract_app["app"].app_context():
        original_request = db.session.get(
            ShipmentRequest, expert_contract_app["request_id"]
        )
        original_request.created_at = base_time

        other_request = ShipmentRequest(
            ownership_scope="TENANT", operational_organization_id=expert_contract_app["organization_id"],
            tracking_code="SR-P4O002",
            shipping_type="domestic",
            contact_phone="09120000002",
            customer_first_name="Sara",
            customer_last_name="Karimi",
            transport_method="air",
            domestic_transport_method="air",
            transport_method_preference="customer_choice",
            cargo_description="Needle machinery",
            cargo_weight=20.0,
            cargo_volume=5.0,
            cargo_value=2000.0,
            status_request_status="new",
            status="waiting_for_customer",
            priority="high",
            assigned_to=other_expert_id,
            has_unread_for_assignee=False,
            created_at=base_time + timedelta(minutes=2),
            ready_at=base_time + timedelta(minutes=2),
            sla_due_at=base_time + timedelta(hours=4),
        )
        unassigned_request = ShipmentRequest(
            ownership_scope="TENANT", operational_organization_id=expert_contract_app["organization_id"],
            tracking_code="SR-P4O003",
            shipping_type="domestic",
            contact_phone="09120000003",
            customer_first_name="Mina",
            customer_last_name="Azadi",
            transport_method="road",
            domestic_transport_method="road",
            transport_method_preference="forwarder_suggestion",
            cargo_description="General cargo",
            status_request_status="lost",
            status="assigned",
            priority="urgent",
            assigned_to=None,
            has_unread_for_assignee=True,
            created_at=base_time + timedelta(minutes=1),
            ready_at=base_time + timedelta(minutes=1),
        )
        db.session.add_all([other_request, unassigned_request])
        db.session.commit()
        other_request_id = other_request.id
        unassigned_request_id = unassigned_request.id

    expert_response = client.get("/api/expert/requests", headers=expert_headers)
    assert expert_response.status_code == 200
    expert_payload = expert_response.get_json()
    assert [item["id"] for item in expert_payload["requests"]] == [
        expert_contract_app["request_id"]
    ]
    assert expert_payload["pagination"]["total"] == 1

    other_response = client.get("/api/expert/requests", headers=other_headers)
    assert other_response.status_code == 200
    other_payload = other_response.get_json()
    assert [item["id"] for item in other_payload["requests"]] == [other_request_id]
    assert other_payload["requests"][0]["assigned_to"] == {
        "id": other_expert_id,
        "name": "Phase 4H Other Expert",
    }
    assert other_payload["requests"][0]["has_unread"] is False

    admin_response = client.get(
        "/api/expert/requests?per_page=1&page=1", headers=admin_headers
    )
    assert admin_response.status_code == 200
    admin_payload = admin_response.get_json()
    assert [item["id"] for item in admin_payload["requests"]] == [other_request_id]
    assert admin_payload["pagination"] == {
        "page": 1,
        "per_page": 1,
        "total": 3,
        "pages": 3,
        "has_next": True,
        "has_prev": False,
    }

    ascending_response = client.get(
        "/api/expert/requests?sort_by=created_at&sort_order=asc",
        headers=admin_headers,
    )
    assert ascending_response.status_code == 200
    assert [item["id"] for item in ascending_response.get_json()["requests"]] == [
        expert_contract_app["request_id"],
        unassigned_request_id,
        other_request_id,
    ]

    assigned_filter_response = client.get(
        f"/api/expert/requests?assigned_to={expert_id}",
        headers=admin_headers,
    )
    assert assigned_filter_response.status_code == 200
    assert [item["id"] for item in assigned_filter_response.get_json()["requests"]] == [
        expert_contract_app["request_id"]
    ]

    status_filter_response = client.get(
        "/api/expert/requests?status=won,lost,closed",
        headers=admin_headers,
    )
    assert status_filter_response.status_code == 200
    assert status_filter_response.get_json()["requests"] == []

    stale_legacy_new_response = client.get(
        "/api/expert/requests?status=new",
        headers=admin_headers,
    )
    assert stale_legacy_new_response.status_code == 200
    assert [
        item["id"] for item in stale_legacy_new_response.get_json()["requests"]
    ] == [expert_contract_app["request_id"]]

    canonical_waiting_response = client.get(
        "/api/expert/requests?status=waiting_for_customer",
        headers=admin_headers,
    )
    assert canonical_waiting_response.status_code == 200
    assert [
        item["id"] for item in canonical_waiting_response.get_json()["requests"]
    ] == [other_request_id]

    priority_search_response = client.get(
        "/api/expert/requests?priority=high&search=Needle",
        headers=admin_headers,
    )
    assert priority_search_response.status_code == 200
    priority_search_payload = priority_search_response.get_json()
    assert [item["id"] for item in priority_search_payload["requests"]] == [
        other_request_id
    ]
    assert priority_search_payload["requests"][0]["customer"] == {
        "name": "Sara Karimi",
        "phone": "09120000002",
    }


def test_expert_request_filters_and_kpis_use_canonical_status_only(expert_contract_app):
    """Stale legacy status_request_status must not drive lifecycle filters or KPIs."""
    client = expert_contract_app["app"].test_client()
    admin_headers = _auth_headers(expert_contract_app["admin_token"])
    expert_id = expert_contract_app["expert_id"]

    with expert_contract_app["app"].app_context():
        stale_legacy_request = ShipmentRequest(
            ownership_scope="TENANT", operational_organization_id=expert_contract_app["organization_id"],
            tracking_code="SR-CANON001",
            shipping_type="domestic",
            contact_phone="09129999999",
            customer_first_name="Canonical",
            customer_last_name="Status",
            transport_method="road",
            domestic_transport_method="road",
            transport_method_preference="customer_choice",
            cargo_description="Canonical status cargo",
            status_request_status="new",
            status="waiting_for_customer",
            priority="normal",
            assigned_to=expert_id,
            has_unread_for_assignee=True,
            created_at=datetime(2026, 1, 2, 10, 0, 0),
            ready_at=datetime(2026, 1, 2, 10, 0, 0),
        )
        db.session.add(stale_legacy_request)
        db.session.commit()
        stale_legacy_request_id = stale_legacy_request.id

    new_filter_response = client.get(
        "/api/expert/requests?status=new", headers=admin_headers
    )
    assert new_filter_response.status_code == 200
    assert stale_legacy_request_id not in [
        item["id"] for item in new_filter_response.get_json()["requests"]
    ]

    waiting_filter_response = client.get(
        "/api/expert/requests?status=waiting_for_customer",
        headers=admin_headers,
    )
    assert waiting_filter_response.status_code == 200
    assert [item["id"] for item in waiting_filter_response.get_json()["requests"]] == [
        stale_legacy_request_id
    ]

    kpi_response = client.get("/api/expert/dashboard/kpis", headers=admin_headers)
    assert kpi_response.status_code == 200
    kpi_payload = kpi_response.get_json()
    assert kpi_payload["counts"]["new"] == 1
    assert kpi_payload["counts"]["waiting_for_customer"] == 1


def test_expert_message_contracts_access_creation_and_listing(expert_contract_app):
    """Message behavior keeps access checks, creation side effects, and request-detail listing shape."""
    client = expert_contract_app["app"].test_client()
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    other_headers = _auth_headers(expert_contract_app["other_expert_token"])
    request_id = expert_contract_app["request_id"]

    forbidden_message = client.post(
        f"/api/expert/requests/{request_id}/messages",
        headers=other_headers,
        json={"content": "Forbidden note"},
    )
    assert forbidden_message.status_code == 403
    assert forbidden_message.get_json() == {"error": "شما به این درخواست دسترسی ندارید"}

    missing_request_message = client.post(
        "/api/expert/requests/999999/messages",
        headers=expert_headers,
        json={"content": "Missing request note"},
    )
    assert missing_request_message.status_code == 404
    assert missing_request_message.get_json() == {"error": "درخواست یافت نشد"}

    message_response = client.post(
        f"/api/expert/requests/{request_id}/messages",
        headers=expert_headers,
        json={
            "type": "internal_note",
            "subject": "Internal subject",
            "content": "Internal content",
        },
    )
    assert message_response.status_code == 200
    message_payload = message_response.get_json()
    assert set(message_payload.keys()) == {"message", "message_id"}
    assert message_payload["message"] == "پیام با موفقیت اضافه شد"

    detail_response = client.get(
        f"/api/expert/requests/{request_id}", headers=expert_headers
    )
    assert detail_response.status_code == 200
    detail_messages = detail_response.get_json()["messages"]
    assert detail_messages[0] == {
        "id": message_payload["message_id"],
        "type": "internal_note",
        "subject": "Internal subject",
        "content": "Internal content",
        "is_read_by_customer": False,
        "customer_response": None,
        "created_at": detail_messages[0]["created_at"],
        "created_by": "Phase 4H Expert",
    }

    with expert_contract_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        assert request_row.status == "new"
        assert (
            ExpertConsoleMessage.query.filter_by(
                shipment_request_id=request_id,
                message_type="internal_note",
                subject="Internal subject",
                content="Internal content",
            ).count()
            == 1
        )
        assert (
            ExpertConsoleLog.query.filter_by(
                shipment_request_id=request_id,
                action="message_added",
                note="پیام internal_note اضافه شد",
            ).count()
            == 1
        )


def test_expert_assignment_contracts_access_not_found_and_side_effects(
    expert_contract_app,
):
    """Assignment endpoint keeps access, not-found responses, and assignment side effects."""
    client = expert_contract_app["app"].test_client()
    admin_headers = _auth_headers(expert_contract_app["admin_token"])
    other_headers = _auth_headers(expert_contract_app["other_expert_token"])
    request_id = expert_contract_app["request_id"]
    other_expert_id = expert_contract_app["other_expert_id"]
    forbidden_assignment = client.post(
        f"/api/expert/requests/{request_id}/assign",
        headers=other_headers,
        json={"expert_id": other_expert_id},
    )
    assert forbidden_assignment.status_code == 403
    assert forbidden_assignment.get_json() == {
        "error": "شما به این درخواست دسترسی ندارید"
    }

    missing_request_assignment = client.post(
        "/api/expert/requests/999999/assign",
        headers=admin_headers,
        json={"expert_id": other_expert_id},
    )
    assert missing_request_assignment.status_code == 404
    assert missing_request_assignment.get_json() == {"error": "درخواست یافت نشد"}

    missing_expert_assignment = client.post(
        f"/api/expert/requests/{request_id}/assign",
        headers=admin_headers,
        json={"expert_id": 999999},
    )
    assert missing_expert_assignment.status_code == 404
    assert missing_expert_assignment.get_json() == {"error": "کارشناس یافت نشد"}

    assign_response = client.post(
        f"/api/expert/requests/{request_id}/assign",
        headers=admin_headers,
        json={"expert_id": other_expert_id},
    )
    assert assign_response.status_code == 200
    assert assign_response.get_json() == {
        "message": "درخواست با موفقیت ارجاع داده شد",
        "assigned_to": {"id": other_expert_id, "name": "Phase 4H Other Expert"},
    }

    with expert_contract_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        assert request_row.assigned_to == other_expert_id
        assert request_row.status == "assigned"
        assert request_row.has_unread_for_assignee is True

        assignment_log = ExpertConsoleLog.query.filter_by(
            shipment_request_id=request_id,
            expert_user_id=other_expert_id,
            action="assignment",
            old_status="new",
            new_status="assigned",
            note="ارجاع به کارشناس: Phase 4H Other Expert",
        ).one()
        assert assignment_log.ip_address is not None

        assignment_notification = ExpertConsoleNotification.query.filter_by(
            expert_user_id=other_expert_id,
            shipment_request_id=request_id,
            notification_type="assignment",
            title="ارجاع درخواست جدید",
            message=f"درخواست {request_id} به شما ارجاع داده شد",
            is_read=False,
        ).one()
        assert assignment_notification.created_at is not None


def test_expert_assignment_status_quote_message_notification_contracts(
    expert_contract_app,
):
    """Mutation endpoints keep assignment/status/quote/message/notification response and side-effect contracts."""
    client = expert_contract_app["app"].test_client()
    admin_headers = _auth_headers(expert_contract_app["admin_token"])
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    other_headers = _auth_headers(expert_contract_app["other_expert_token"])
    request_id = expert_contract_app["request_id"]
    other_expert_id = expert_contract_app["other_expert_id"]

    missing_expert = client.post(
        f"/api/expert/requests/{request_id}/assign",
        headers=admin_headers,
        json={},
    )
    assert missing_expert.status_code == 400
    assert missing_expert.get_json() == {"error": "شناسه کارشناس الزامی است"}

    assign_response = client.post(
        f"/api/expert/requests/{request_id}/assign",
        headers=admin_headers,
        json={"expert_id": other_expert_id},
    )
    assert assign_response.status_code == 200
    assert assign_response.get_json() == {
        "message": "درخواست با موفقیت ارجاع داده شد",
        "assigned_to": {"id": other_expert_id, "name": "Phase 4H Other Expert"},
    }

    invalid_status = client.post(
        f"/api/expert/requests/{request_id}/status",
        headers=other_headers,
        json={"status": "invalid"},
    )
    assert invalid_status.status_code == 400
    assert invalid_status.get_json() == {"error": "وضعیت نامعتبر است"}

    status_response = client.post(
        f"/api/expert/requests/{request_id}/status",
        headers=other_headers,
        json={"status": "in_progress", "note": "Started"},
    )
    assert status_response.status_code == 200
    assert status_response.get_json() == {
        "message": "وضعیت با موفقیت به‌روزرسانی شد",
        "status": "in_progress",
    }

    forbidden_latest_quote = client.get(
        f"/api/expert/requests/{request_id}/quote/latest", headers=expert_headers
    )
    assert forbidden_latest_quote.status_code == 403
    assert forbidden_latest_quote.get_json() == {
        "error": "شما به این درخواست دسترسی ندارید"
    }

    missing_quote_target = client.post(
        "/api/expert/requests/999999/quote",
        headers=other_headers,
        json={"amount": "12345"},
    )
    assert missing_quote_target.status_code == 404
    assert missing_quote_target.get_json() == {"error": "درخواست یافت نشد"}

    missing_amount = client.post(
        f"/api/expert/requests/{request_id}/quote", headers=other_headers, json={}
    )
    assert missing_amount.status_code == 400
    assert missing_amount.get_json() == {"error": "مبلغ الزامی است"}

    non_numeric_amount = client.post(
        f"/api/expert/requests/{request_id}/quote",
        headers=other_headers,
        json={"amount": "not-a-number"},
    )
    assert non_numeric_amount.status_code == 400
    assert non_numeric_amount.get_json() == {"error": "مبلغ باید عدد باشد"}

    negative_amount = client.post(
        f"/api/expert/requests/{request_id}/quote",
        headers=other_headers,
        json={"amount": -1},
    )
    assert negative_amount.status_code == 400
    assert negative_amount.get_json() == {"error": "مبلغ نامعتبر است"}

    quote_response = client.post(
        f"/api/expert/requests/{request_id}/quote",
        headers=other_headers,
        json={
            "amount": "12345",
            "currency": "IRR",
            "note": "Quote note",
            "valid_until": "2026-08-01",
        },
    )
    assert quote_response.status_code == 200
    quote_data = quote_response.get_json()
    assert set(quote_data.keys()) == {"ok", "quote", "request"}
    assert quote_data["ok"] is True
    assert quote_data["quote"]["amount"] == 12345
    assert quote_data["quote"]["valid_until"] == "2026-08-01"
    assert quote_data["request"] == {"id": request_id, "status": "waiting_for_customer"}

    latest_quote_response = client.get(
        f"/api/expert/requests/{request_id}/quote/latest", headers=other_headers
    )
    assert latest_quote_response.status_code == 200
    assert set(latest_quote_response.get_json()["quote"].keys()) == {
        "id",
        "amount",
        "currency",
        "note",
        "valid_until",
        "created_at",
        "customer_response",
        "responded_at",
        "created_by",
    }

    missing_content = client.post(
        f"/api/expert/requests/{request_id}/messages",
        headers=other_headers,
        json={"type": "customer_message"},
    )
    assert missing_content.status_code == 400
    assert missing_content.get_json() == {"error": "محتوای پیام الزامی است"}

    message_response = client.post(
        f"/api/expert/requests/{request_id}/messages",
        headers=other_headers,
        json={
            "type": "customer_message",
            "subject": "Follow up",
            "content": "Please review quote",
        },
    )
    assert message_response.status_code == 200
    assert set(message_response.get_json().keys()) == {"message", "message_id"}
    assert message_response.get_json()["message"] == "پیام با موفقیت اضافه شد"

    notifications_response = client.get(
        "/api/expert/notifications?unread_only=true", headers=other_headers
    )
    assert notifications_response.status_code == 200
    notifications_data = notifications_response.get_json()
    assert set(notifications_data.keys()) == {"notifications", "unread_count"}
    assert notifications_data["unread_count"] >= 1
    assert set(notifications_data["notifications"][0].keys()) == {
        "id",
        "type",
        "title",
        "message",
        "is_read",
        "created_at",
        "shipment_request_id",
    }

    mark_read_response = client.post(
        "/api/expert/notifications/mark-read",
        headers=other_headers,
        json={"mark_all": True},
    )
    assert mark_read_response.status_code == 200
    assert set(mark_read_response.get_json().keys()) == {"message", "marked_count"}

    with expert_contract_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        assert request_row.assigned_to == other_expert_id
        assert request_row.status == "waiting_for_customer"
        assert ExpertQuote.query.filter_by(shipment_request_id=request_id).count() == 1
        assert (
            ExpertConsoleMessage.query.filter_by(shipment_request_id=request_id).count()
            == 1
        )
        assert (
            ExpertConsoleLog.query.filter_by(shipment_request_id=request_id).count()
            >= 3
        )
        assert (
            ExpertConsoleNotification.query.filter_by(
                expert_user_id=other_expert_id
            ).count()
            >= 3
        )


def test_expert_notification_contracts_scope_order_and_mark_read(expert_contract_app):
    """Notification endpoints keep expert scoping, ordering, unread counts, and mark-read behavior."""
    client = expert_contract_app["app"].test_client()
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    expert_id = expert_contract_app["expert_id"]
    other_expert_id = expert_contract_app["other_expert_id"]
    request_id = expert_contract_app["request_id"]

    with expert_contract_app["app"].app_context():
        older = ExpertConsoleNotification(
            expert_user_id=expert_id,
            shipment_request_id=request_id,
            notification_type="older",
            title="Older notification",
            message="Older message",
            is_read=False,
            created_at=datetime.utcnow() + timedelta(minutes=1),
        )
        newest = ExpertConsoleNotification(
            expert_user_id=expert_id,
            shipment_request_id=request_id,
            notification_type="newest",
            title="Newest notification",
            message="Newest message",
            is_read=False,
            created_at=datetime.utcnow() + timedelta(minutes=2),
        )
        other_expert_notification = ExpertConsoleNotification(
            expert_user_id=other_expert_id,
            shipment_request_id=request_id,
            notification_type="other_expert",
            title="Other expert notification",
            message="Other expert message",
            is_read=False,
            created_at=datetime.utcnow() + timedelta(minutes=3),
        )
        db.session.add_all([older, newest, other_expert_notification])
        db.session.commit()
        newest_id = newest.id
        other_expert_notification_id = other_expert_notification.id

    list_response = client.get(
        "/api/expert/notifications?unread_only=true&limit=1",
        headers=expert_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert set(list_payload.keys()) == {"notifications", "unread_count"}
    assert list_payload["unread_count"] == 3
    assert len(list_payload["notifications"]) == 1
    assert list_payload["notifications"][0]["id"] == newest_id
    assert list_payload["notifications"][0]["type"] == "newest"
    assert list_payload["notifications"][0]["is_read"] is False

    invalid_mark_read = client.post(
        "/api/expert/notifications/mark-read",
        headers=expert_headers,
        json={},
    )
    assert invalid_mark_read.status_code == 400
    assert invalid_mark_read.get_json() == {
        "error": "شناسه اعلان‌ها یا mark_all الزامی است"
    }

    mark_specific_response = client.post(
        "/api/expert/notifications/mark-read",
        headers=expert_headers,
        json={"notification_ids": [newest_id, other_expert_notification_id]},
    )
    assert mark_specific_response.status_code == 200
    assert mark_specific_response.get_json() == {
        "message": "1 اعلان به عنوان خوانده شده علامت‌گذاری شد",
        "marked_count": 1,
    }

    with expert_contract_app["app"].app_context():
        assert db.session.get(ExpertConsoleNotification, newest_id).is_read is True
        assert (
            db.session.get(
                ExpertConsoleNotification, other_expert_notification_id
            ).is_read
            is False
        )


def test_referral_rule_crud_contracts(expert_contract_app):
    """Referral rule create/update/delete endpoints keep validation, response, and persistence contracts."""
    client = expert_contract_app["app"].test_client()
    admin_headers = _auth_headers(expert_contract_app["admin_token"])
    other_expert_id = expert_contract_app["other_expert_id"]

    missing_name = client.post(
        "/api/admin/referral-rules",
        headers=admin_headers,
        json={"action": {"type": "direct_assign", "expert_id": other_expert_id}},
    )
    assert missing_name.status_code == 400
    assert missing_name.get_json() == {"error": "نام قانون الزامی است"}

    invalid_action = client.post(
        "/api/admin/referral-rules",
        headers=admin_headers,
        json={"name": "Invalid referral", "action": {"type": "invalid"}},
    )
    assert invalid_action.status_code == 400
    assert invalid_action.get_json() == {
        "error": "action باید نوع direct_assign یا pool_assign داشته باشد"
    }

    create_response = client.post(
        "/api/admin/referral-rules",
        headers=admin_headers,
        json={
            "name": "Direct referral",
            "priority": 7,
            "conditions": {"shipping_type": "domestic"},
            "action": {"type": "direct_assign", "expert_id": other_expert_id},
            "stop_on_match": False,
        },
    )
    assert create_response.status_code == 201
    create_payload = create_response.get_json()
    assert set(create_payload.keys()) == {"message", "rule_id"}
    assert create_payload["message"] == "قانون ارجاع با موفقیت ایجاد شد"
    rule_id = create_payload["rule_id"]

    update_invalid_action = client.put(
        f"/api/admin/referral-rules/{rule_id}",
        headers=admin_headers,
        json={"action": {"type": "invalid"}},
    )
    assert update_invalid_action.status_code == 400
    assert update_invalid_action.get_json() == {
        "error": "action.type باید direct_assign یا pool_assign باشد"
    }

    update_response = client.put(
        f"/api/admin/referral-rules/{rule_id}",
        headers=admin_headers,
        json={"name": "Updated referral", "priority": 3, "is_active": False},
    )
    assert update_response.status_code == 200
    assert update_response.get_json() == {"message": "قانون ارجاع به‌روزرسانی شد"}

    delete_missing = client.delete(
        "/api/admin/referral-rules/999999", headers=admin_headers
    )
    assert delete_missing.status_code == 404
    assert delete_missing.get_json() == {"error": "قانون ارجاع یافت نشد"}

    delete_response = client.delete(
        f"/api/admin/referral-rules/{rule_id}", headers=admin_headers
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {"message": "قانون ارجاع حذف شد"}

    with expert_contract_app["app"].app_context():
        assert db.session.get(ReferralRule, rule_id) is None


def test_referral_engine_uses_matching_active_referral_rule(expert_contract_app):
    """A matching active referral rule drives auto-assignment before global fallback."""
    from backend.referral_engine import referral_engine

    app = expert_contract_app["app"]
    with app.app_context():
        request_row = ShipmentRequest(
            tracking_code="SR-P4H-RULE",
            shipping_type="domestic",
            contact_phone="09123456780",
            customer_first_name="Rule",
            customer_last_name="Match",
            transport_method="road",
            domestic_transport_method="road",
            transport_method_preference="customer_choice",
            status_request_status="new",
            status="new",
            priority="normal",
            assigned_to=None,
            has_unread_for_assignee=True,
            ownership_scope="TENANT",
            operational_organization_id=expert_contract_app["organization_id"],
        )
        db.session.add(request_row)
        db.session.commit()
        request_id = request_row.id

        selected_expert_id = referral_engine.auto_assign_request(request_id)

        updated_request = db.session.get(ShipmentRequest, request_id)
        assert selected_expert_id in {
            expert_contract_app["expert_id"],
            expert_contract_app["other_expert_id"],
        }
        assert updated_request.assigned_to == selected_expert_id
        assert updated_request.status == "assigned"
        assert updated_request.sla_due_at is not None
        original_deadline = updated_request.sla_due_at
        assert referral_engine.auto_assign_request(request_id) == selected_expert_id
        assert (
            db.session.get(ShipmentRequest, request_id).sla_due_at == original_deadline
        )

        referral_log = (
            db.session.query(ReferralAssignmentLog)
            .filter_by(request_id=request_id)
            .one()
        )
        assert referral_log.rule_id == expert_contract_app["referral_rule_id"]
        assert referral_log.strategy_used == "round_robin"
        assert json.loads(referral_log.candidate_expert_ids) == [
            expert_contract_app["expert_id"],
            expert_contract_app["other_expert_id"],
        ]

        console_log = (
            db.session.query(ExpertConsoleLog)
            .filter_by(
                shipment_request_id=request_id,
                action="assignment",
                new_status="assigned",
            )
            .one()
        )
        assert console_log.expert_user_id == selected_expert_id


def test_referral_engine_falls_back_when_no_referral_rule_matches(expert_contract_app):
    """No matching referral rule preserves the existing global round-robin assignment behavior."""
    from backend.referral_engine import referral_engine

    app = expert_contract_app["app"]
    with app.app_context():
        request_row = ShipmentRequest(
            tracking_code="SR-P4H-FALLBACK",
            shipping_type="international",
            contact_phone="09123456781",
            customer_first_name="Rule",
            customer_last_name="Fallback",
            origin_country="Turkey",
            origin_city_international="Istanbul",
            dest_country="Iran",
            dest_city_international="Tehran",
            international_transport_method="air",
            transport_method_preference="customer_choice",
            status_request_status="new",
            status="new",
            priority="normal",
            assigned_to=None,
            has_unread_for_assignee=True,
            ownership_scope="TENANT",
            operational_organization_id=expert_contract_app["organization_id"],
        )
        db.session.add(request_row)
        db.session.commit()
        request_id = request_row.id

        selected_expert_id = referral_engine.auto_assign_request(request_id)

        updated_request = db.session.get(ShipmentRequest, request_id)
        assert selected_expert_id in {
            expert_contract_app["expert_id"],
            expert_contract_app["other_expert_id"],
        }
        assert updated_request.assigned_to == selected_expert_id
        assert updated_request.status == "assigned"
        assert updated_request.sla_due_at is not None

        referral_log = (
            db.session.query(ReferralAssignmentLog)
            .filter_by(request_id=request_id)
            .one()
        )
        assert referral_log.rule_id is None
        assert referral_log.strategy_used == "round_robin"


def test_assignment_engine_sets_once_and_no_candidate_leaves_null(
    expert_contract_app, monkeypatch
):
    from backend.assignment_engine import AssignmentEngine

    with expert_contract_app["app"].app_context():
        request_row = ShipmentRequest(
            tracking_code="SR-SLA-AUTO",
            shipping_type="domestic",
            contact_phone="09123456784",
            transport_method="road",
            domestic_transport_method="road",
            status_request_status="new",
            status="new",
            ownership_scope="TENANT",
            operational_organization_id=expert_contract_app["organization_id"],
        )
        db.session.add(request_row)
        db.session.commit()
        request_id = request_row.id
        engine = AssignmentEngine(db.session)
        monkeypatch.setattr(
            engine,
            "_find_best_expert",
            lambda _request: expert_contract_app["expert_id"],
        )
        assert engine.assign_request(request_id) == expert_contract_app["expert_id"]
        deadline = db.session.get(ShipmentRequest, request_id).sla_due_at
        assert deadline is not None

        assert (
            engine.assign_request(
                request_id, assignment_method="override", reason="reassignment"
            )
            == expert_contract_app["expert_id"]
        )
        assert db.session.get(ShipmentRequest, request_id).sla_due_at == deadline

        no_candidate = ShipmentRequest(
            tracking_code="SR-SLA-NONE",
            shipping_type="domestic",
            contact_phone="09123456785",
            transport_method="road",
            domestic_transport_method="road",
            status_request_status="new",
            status="new",
        )
        db.session.add(no_candidate)
        db.session.commit()
        monkeypatch.setattr(engine, "_find_best_expert", lambda _request: None)
        assert engine.assign_request(no_candidate.id) is None
        assert db.session.get(ShipmentRequest, no_candidate.id).sla_due_at is None


def test_referral_preview_does_not_set_deadline(expert_contract_app):
    from backend.referral_engine import referral_engine

    with expert_contract_app["app"].app_context():
        request_row = ShipmentRequest(
            tracking_code="SR-SLA-PREVIEW",
            shipping_type="domestic",
            contact_phone="09123456786",
            transport_method="road",
            domestic_transport_method="road",
            status_request_status="new",
            status="new",
            ownership_scope="TENANT",
            operational_organization_id=expert_contract_app["organization_id"],
        )
        db.session.add(request_row)
        db.session.commit()
        assert "error" not in referral_engine.preview_assignment(request_row.id)
        assert db.session.get(ShipmentRequest, request_row.id).sla_due_at is None


def test_public_request_creation_does_not_use_tenant_round_robin_before_ownership(
    expert_contract_app,
):
    """Public intake remains unassigned until organization ownership is certified."""
    client = expert_contract_app["app"].test_client()

    first_response = client.post(
        "/api/shipment-request",
        json=_international_request_payload(
            "09123456782", "Round robin public request 1"
        ),
    )
    second_response = client.post(
        "/api/shipment-request",
        json=_international_request_payload(
            "09123456783", "Round robin public request 2"
        ),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert set(first_response.get_json().keys()) == {"message", "id", "tracking_code"}
    assert set(second_response.get_json().keys()) == {"message", "id", "tracking_code"}

    first_request_id = first_response.get_json()["id"]
    second_request_id = second_response.get_json()["id"]

    with expert_contract_app["app"].app_context():
        first_request = db.session.get(ShipmentRequest, first_request_id)
        second_request = db.session.get(ShipmentRequest, second_request_id)

        assert first_request.assigned_to is None and second_request.assigned_to is None
        assert first_request.ownership_scope == "INTAKE" and second_request.ownership_scope == "INTAKE"
        assert db.session.query(ReferralAssignmentLog).filter(ReferralAssignmentLog.request_id.in_([first_request_id, second_request_id])).count() == 0


def test_public_request_creation_with_inactive_expert_still_waits_for_tenant(expert_contract_app):
    """Expert state cannot bypass the unowned-intake referral fence."""
    client = expert_contract_app["app"].test_client()

    with expert_contract_app["app"].app_context():
        other_expert = db.session.get(
            ExpertUser, expert_contract_app["other_expert_id"]
        )
        other_expert.is_active = False
        db.session.commit()

    response = client.post(
        "/api/shipment-request",
        json=_international_request_payload(
            "09123456784", "Inactive expert skip request"
        ),
    )

    assert response.status_code == 201
    request_id = response.get_json()["id"]

    with expert_contract_app["app"].app_context():
        created_request = db.session.get(ShipmentRequest, request_id)
        assert created_request.assigned_to is None
        assert created_request.ownership_scope == "INTAKE"
        assert db.session.query(ReferralAssignmentLog).filter_by(request_id=request_id).count() == 0


def test_public_request_creation_remains_unassigned_when_no_active_expert_exists(
    expert_contract_app,
):
    """No active expert leaves the created request unassigned without changing the API response shape."""
    client = expert_contract_app["app"].test_client()

    with expert_contract_app["app"].app_context():
        db.session.get(ExpertUser, expert_contract_app["expert_id"]).is_active = False
        db.session.get(
            ExpertUser, expert_contract_app["other_expert_id"]
        ).is_active = False
        db.session.commit()

    response = client.post(
        "/api/shipment-request",
        json=_international_request_payload("09123456785", "No active expert request"),
    )

    assert response.status_code == 201
    assert set(response.get_json().keys()) == {"message", "id", "tracking_code"}
    request_id = response.get_json()["id"]

    with expert_contract_app["app"].app_context():
        created_request = db.session.get(ShipmentRequest, request_id)
        assert created_request.assigned_to is None
        assert created_request.status == "new"
        assert (
            db.session.query(ReferralAssignmentLog)
            .filter_by(request_id=request_id)
            .count()
            == 0
        )
        assert (
            db.session.query(ExpertConsoleNotification)
            .filter_by(shipment_request_id=request_id)
            .count()
            == 0
        )


def test_public_request_creation_waits_for_certified_tenant_before_referral(expert_contract_app):
    """Unowned public intake cannot consume tenant referral policy."""
    client = expert_contract_app["app"].test_client()

    response = client.post(
        "/api/shipment-request",
        json={
            "shipping_type": "domestic",
            "origin_province_id": expert_contract_app["province_id"],
            "dest_province_id": expert_contract_app["province_id"],
            "contact_phone": "09123456782",
            "customer_first_name": "Public",
            "customer_last_name": "Referral",
            "transport_method": "road",
            "domestic_transport_method": "road",
            "transport_method_preference": "customer_choice",
            "cargo_description": "Public request referral test",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    request_id = payload["id"]

    with expert_contract_app["app"].app_context():
        created_request = db.session.get(ShipmentRequest, request_id)
        assert created_request.assigned_to is None
        assert created_request.ownership_scope == "INTAKE"
        assert db.session.query(ReferralAssignmentLog).filter_by(request_id=request_id).count() == 0


def test_assignment_and_referral_rule_read_and_manual_assignment_contracts(
    expert_contract_app,
):
    """Assignment/referral admin endpoints keep auth, read shapes, preview, and manual assignment behavior."""
    client = expert_contract_app["app"].test_client()
    admin_headers = _auth_headers(expert_contract_app["admin_token"])
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    request_id = expert_contract_app["request_id"]

    forbidden_assignment_rules = client.get(
        "/api/user-management/assignment-rules", headers=expert_headers
    )
    assert forbidden_assignment_rules.status_code == 403
    assert forbidden_assignment_rules.get_json()["required_roles"] == ["admin"]

    assignment_rules_response = client.get(
        "/api/user-management/assignment-rules", headers=admin_headers
    )
    assert assignment_rules_response.status_code == 200
    assignment_rules_data = assignment_rules_response.get_json()
    assert set(assignment_rules_data.keys()) == {"assignment_rules"}
    assert set(assignment_rules_data["assignment_rules"][0].keys()) == {
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

    referral_rules_response = client.get(
        "/api/admin/referral-rules", headers=admin_headers
    )
    assert referral_rules_response.status_code == 200
    referral_rules_data = referral_rules_response.get_json()
    assert set(referral_rules_data.keys()) == {"referral_rules"}
    assert set(referral_rules_data["referral_rules"][0].keys()) == {
        "id",
        "name",
        "is_active",
        "priority",
        "conditions",
        "action",
        "stop_on_match",
        "created_by",
        "created_at",
        "updated_at",
        "action_type",
        "pool_expert_count",
        "strategy",
    }

    preview_missing_id = client.post(
        "/api/admin/referral-rules/preview", headers=admin_headers, json={}
    )
    assert preview_missing_id.status_code == 400
    assert preview_missing_id.get_json() == {"error": "request_id الزامی است"}

    preview_response = client.post(
        "/api/admin/referral-rules/preview",
        headers=admin_headers,
        json={"request_id": request_id},
    )
    assert preview_response.status_code == 200
    assert {
        "matched_rule",
        "candidates",
        "selected_expert",
        "strategy_used",
        "debug_trace",
    }.issubset(preview_response.get_json().keys())
    with expert_contract_app["app"].app_context():
        assert db.session.get(ShipmentRequest, request_id).sla_due_at is not None


def test_user_management_manual_assignment_fix_contract(expert_contract_app):
    """Manual assignment now uses the shared assignment path and side effects."""
    client = expert_contract_app["app"].test_client()
    admin_headers = _auth_headers(expert_contract_app["admin_token"])
    request_id = expert_contract_app["request_id"]
    other_expert_id = expert_contract_app["other_expert_id"]

    missing_request = client.post(
        "/api/user-management/manual-assignment", headers=admin_headers, json={}
    )
    assert missing_request.status_code == 400
    assert missing_request.get_json() == {"error": "شناسه درخواست الزامی است"}

    missing_expert = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={"request_id": request_id},
    )
    assert missing_expert.status_code == 400
    assert missing_expert.get_json() == {"error": "شناسه کارشناس الزامی است"}

    manual_response = client.post(
        "/api/user-management/manual-assignment",
        headers=admin_headers,
        json={
            "request_id": request_id,
            "expert_id": other_expert_id,
            "reason": "Phase 5I manual",
        },
    )
    assert manual_response.status_code == 200
    assert manual_response.get_json() == {
        "message": "درخواست با موفقیت ارجاع داده شد",
        "assigned_to": {"id": other_expert_id, "name": "Phase 4H Other Expert"},
    }

    with expert_contract_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, request_id)
        assert request_row.assigned_to == other_expert_id
        assert request_row.status == "assigned"
        assert request_row.has_unread_for_assignee is True
        assert request_row.sla_due_at is not None
        assert (
            AssignmentLog.query.filter_by(shipment_request_id=request_id).count() == 0
        )
        assert (
            ExpertConsoleLog.query.filter_by(
                shipment_request_id=request_id,
                expert_user_id=other_expert_id,
                action="assignment",
                old_status="new",
                new_status="assigned",
            ).count()
            == 1
        )
        assert (
            ExpertConsoleNotification.query.filter_by(
                shipment_request_id=request_id,
                expert_user_id=other_expert_id,
                notification_type="assignment",
                is_read=False,
            ).count()
            == 1
        )


def test_api_reassignment_revokes_old_expert_immediately(expert_contract_app):
    """The reassignment command and protected reads use the same current root."""
    client = expert_contract_app["app"].test_client()
    request_id = expert_contract_app["request_id"]
    a_headers = _auth_headers(expert_contract_app["expert_token"])
    b_headers = _auth_headers(expert_contract_app["other_expert_token"])
    admin_headers = _auth_headers(expert_contract_app["admin_token"])

    assert client.get(f"/api/expert/requests/{request_id}", headers=a_headers).status_code == 200
    assert client.get("/api/expert/requests", headers=a_headers).get_json()["pagination"]["total"] == 1
    reassigned = client.post(
        f"/api/admin/shipment-requests/{request_id}/assign",
        headers=admin_headers,
        json={"expert_id": expert_contract_app["other_expert_id"]},
    )
    assert reassigned.status_code == 200

    # No cached token, browser list, or remembered numeric ID preserves A's
    # authorization.  The denial is non-disclosing at the operational route.
    assert client.get(f"/api/expert/requests/{request_id}", headers=a_headers).status_code == 403
    assert client.get(f"/api/expert/requests/{request_id}/tracking", headers=a_headers).status_code == 403
    assert client.get("/api/expert/requests", headers=a_headers).get_json()["pagination"]["total"] == 0
    assert client.get(f"/api/expert/requests/{request_id}", headers=b_headers).status_code == 200
    assert client.get(f"/api/expert/requests/{request_id}/tracking", headers=b_headers).status_code == 200
    assert client.get("/api/expert/requests", headers=b_headers).get_json()["pagination"]["total"] == 1


def test_golden_new_request_counter_and_list_share_scope_through_mutations(
    expert_contract_app,
):
    """Freeze the current status, assignee, tenant, and pagination count contract."""
    client = expert_contract_app["app"].test_client()
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    other_headers = _auth_headers(expert_contract_app["other_expert_token"])
    admin_headers = _auth_headers(expert_contract_app["admin_token"])

    def list_total(headers, status):
        response = client.get(
            f"/api/expert/requests?status={status}&per_page=1", headers=headers
        )
        assert response.status_code == 200
        return response.get_json()["pagination"]["total"]

    def counts(headers):
        response = client.get("/api/expert/dashboard/kpis", headers=headers)
        assert response.status_code == 200
        return response.get_json()["counts"]

    assert list_total(expert_headers, "new") == 1
    assert counts(expert_headers)["new"] == 1

    with expert_contract_app["app"].app_context():
        created = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=expert_contract_app["organization_id"],
            tracking_code="SR-GOLDEN-COUNT",
            shipping_type="domestic",
            contact_phone="09120000999",
            status_request_status="new",
            status="new",
            assigned_to=expert_contract_app["expert_id"],
            created_at=datetime(2026, 1, 2, 10, 0, 0),
        )
        db.session.add(created)
        db.session.commit()
        created_id = created.id

    assert list_total(expert_headers, "new") == 2
    assert counts(expert_headers)["new"] == 2

    transition = client.post(
        f"/api/expert/requests/{created_id}/status",
        headers=expert_headers,
        json={"status": "in_progress"},
    )
    assert transition.status_code == 200
    assert list_total(expert_headers, "new") == 1
    assert list_total(expert_headers, "in_progress") == 1
    assert counts(expert_headers)["new"] == 1
    assert counts(expert_headers)["in_progress"] == 1

    reassigned = client.post(
        f"/api/admin/shipment-requests/{expert_contract_app['request_id']}/assign",
        headers=admin_headers,
        json={"expert_id": expert_contract_app["other_expert_id"]},
    )
    assert reassigned.status_code == 200
    assert list_total(expert_headers, "new") == 0
    assert counts(expert_headers)["new"] == 0
    assert list_total(other_headers, "assigned") == 1
    assert counts(other_headers)["new"] == 0


def test_phase_b4_canonical_population_covers_filters_pagination_tenants_and_revocation(
    expert_contract_app,
):
    """Count and list remain two database views over one authorized population."""
    client = expert_contract_app["app"].test_client()
    expert_headers = _auth_headers(expert_contract_app["expert_token"])
    other_headers = _auth_headers(expert_contract_app["other_expert_token"])
    admin_headers = _auth_headers(expert_contract_app["admin_token"])

    def request_list(headers, *, status=None, page=1, per_page=20, search=None):
        query = [f"page={page}", f"per_page={per_page}"]
        if status:
            query.append(f"status={status}")
        if search:
            query.append(f"search={search}")
        response = client.get(
            f"/api/expert/requests?{'&'.join(query)}",
            headers=headers,
        )
        assert response.status_code == 200
        return response.get_json()

    def kpis(headers, *, search=None):
        suffix = f"?search={search}" if search else ""
        response = client.get(f"/api/expert/dashboard/kpis{suffix}", headers=headers)
        assert response.status_code == 200
        return response.get_json()

    with expert_contract_app["app"].app_context():
        fixed_created_at = datetime(2026, 1, 2, 10, 0, 0)
        created_rows = []
        for index in range(5):
            row = ShipmentRequest(
                ownership_scope="TENANT",
                operational_organization_id=expert_contract_app["organization_id"],
                tracking_code=f"SR-B4-{index}",
                shipping_type="domestic",
                contact_phone=f"0912000100{index}",
                customer_first_name="Needle" if index == 0 else "Canonical",
                customer_last_name=f"Request {index}",
                status_request_status="new",
                status="new",
                assigned_to=expert_contract_app["expert_id"],
                created_at=fixed_created_at,
            )
            db.session.add(row)
            created_rows.append(row)

        same_tenant_other_expert = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=expert_contract_app["organization_id"],
            tracking_code="SR-B4-OTHER-EXPERT",
            shipping_type="domestic",
            contact_phone="09120001100",
            status_request_status="new",
            status="new",
            assigned_to=expert_contract_app["other_expert_id"],
            created_at=fixed_created_at,
        )
        foreign_organization = OperationalOrganization(name="Phase B4 Foreign Organization")
        db.session.add_all([same_tenant_other_expert, foreign_organization])
        db.session.flush()
        foreign_request = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=foreign_organization.id,
            tracking_code="SR-B4-FOREIGN",
            shipping_type="domestic",
            contact_phone="09120001101",
            status_request_status="new",
            status="new",
            assigned_to=expert_contract_app["expert_id"],
            created_at=fixed_created_at,
        )
        db.session.add(foreign_request)
        db.session.commit()
        created_ids = [row.id for row in created_rows]

    # CREATE + TENANT/ASSIGNMENT: the Expert gains exactly five eligible rows;
    # same-tenant work assigned elsewhere and foreign-tenant work stay excluded.
    new_population = request_list(expert_headers, status="new", per_page=2)
    assert new_population["pagination"]["total"] == 6
    assert kpis(expert_headers)["counts"]["new"] == 6
    assert kpis(expert_headers)["counts"]["total_visible"] == 6

    # Organization Admin is still tenant-fenced while seeing this tenant's
    # assigned requests under the existing request.read capability.
    assert request_list(admin_headers, status="new")["pagination"]["total"] == 7
    assert kpis(admin_headers)["counts"]["new"] == 7

    # PAGINATION: totals are population totals, pages are stable/disjoint, and
    # changing page size or reading beyond the last page does not change total.
    first_page = request_list(expert_headers, status="new", page=1, per_page=2)
    second_page = request_list(expert_headers, status="new", page=2, per_page=2)
    repeated_first_page = request_list(expert_headers, status="new", page=1, per_page=2)
    first_ids = [row["id"] for row in first_page["requests"]]
    second_ids = [row["id"] for row in second_page["requests"]]
    assert first_ids == [row["id"] for row in repeated_first_page["requests"]]
    assert set(first_ids).isdisjoint(second_ids)
    assert first_page["pagination"]["total"] == second_page["pagination"]["total"] == 6
    assert request_list(expert_headers, status="new", per_page=3)["pagination"]["total"] == 6
    beyond = request_list(expert_headers, status="new", page=99, per_page=2)
    assert beyond["requests"] == []
    assert beyond["pagination"]["total"] == 6

    # FILTER + REFRESH: status/search predicates match and repeated reads are
    # identical without client-side reconstruction.
    searched_list = request_list(expert_headers, status="new", search="Needle")
    searched_kpis = kpis(expert_headers, search="Needle")
    assert searched_list["pagination"]["total"] == 1
    assert searched_kpis["counts"]["new"] == 1
    assert searched_kpis["counts"]["total_visible"] == 1
    assert request_list(expert_headers, status="new", search="Needle") == searched_list
    assert kpis(expert_headers, search="Needle") == searched_kpis

    # STATUS TRANSITION: both views leave new and enter in-progress together.
    transitioned_id = created_ids[0]
    transition = client.post(
        f"/api/expert/requests/{transitioned_id}/status",
        headers=expert_headers,
        json={"status": "in_progress"},
    )
    assert transition.status_code == 200
    assert request_list(expert_headers, status="new")["pagination"]["total"] == 5
    assert request_list(expert_headers, status="in_progress")["pagination"]["total"] == 1
    transitioned_kpis = kpis(expert_headers)["counts"]
    assert transitioned_kpis["new"] == 5
    assert transitioned_kpis["in_progress"] == 1

    # REASSIGNMENT: current ownership revokes the old Expert and grants the new
    # Expert. Existing Golden semantics change the request to assigned, so the
    # new Expert gains total-visible/assigned rather than a fabricated new count.
    old_total = kpis(expert_headers)["counts"]["total_visible"]
    new_total = kpis(other_headers)["counts"]["total_visible"]
    reassigned = client.post(
        f"/api/admin/shipment-requests/{expert_contract_app['request_id']}/assign",
        headers=admin_headers,
        json={"expert_id": expert_contract_app["other_expert_id"]},
    )
    assert reassigned.status_code == 200
    assert kpis(expert_headers)["counts"]["total_visible"] == old_total - 1
    assert kpis(other_headers)["counts"]["total_visible"] == new_total + 1
    assert request_list(other_headers, status="assigned")["pagination"]["total"] == 1
    assert client.get(
        f"/api/expert/requests/{expert_contract_app['request_id']}",
        headers=expert_headers,
    ).status_code == 403

    # REVOKED MEMBERSHIP: neither row data nor aggregate existence is disclosed.
    with expert_contract_app["app"].app_context():
        membership = OperationalMembership.query.filter_by(
            organization_id=expert_contract_app["organization_id"],
            user_id=expert_contract_app["expert_id"],
        ).one()
        membership.is_active = False
        db.session.commit()

    assert request_list(expert_headers)["pagination"]["total"] == 0
    revoked_counts = kpis(expert_headers)["counts"]
    assert revoked_counts == {
        "total_visible": 0,
        "new": 0,
        "in_progress": 0,
        "waiting_for_customer": 0,
        "closed_today": 0,
    }
