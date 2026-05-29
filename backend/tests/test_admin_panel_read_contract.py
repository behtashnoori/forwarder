"""Characterization tests for admin panel read/report route contracts."""
from __future__ import annotations

from datetime import datetime, timedelta

import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import (
    AssignmentLog,
    City,
    County,
    ExpertConsoleLog,
    ExpertUser,
    Province,
    ShipmentRequest,
)
from backend.security import security
from backend.services.admin_report_service import calculate_sla_violations


@pytest.fixture
def admin_panel_app():
    """App with isolated DB and admin panel report seed data."""
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
            username="phase5m_admin",
            password_hash=password_hash,
            full_name="Phase 5M Admin",
            email="phase5m-admin@example.test",
            role="admin",
            is_active=True,
        )
        expert = ExpertUser(
            username="phase5m_expert",
            password_hash=password_hash,
            full_name="Phase 5M Expert",
            email="phase5m-expert@example.test",
            role="expert",
            is_active=True,
        )
        province = Province(code="THR", name_fa="Tehran")
        db.session.add_all([admin, expert, province])
        db.session.flush()
        county = County(name_fa="Tehran County", province_id=province.id)
        db.session.add(county)
        db.session.flush()
        city = City(name_fa="Tehran City", county_id=county.id, province_id=province.id)
        db.session.add(city)
        db.session.flush()

        now = datetime.utcnow()
        assigned_request = ShipmentRequest(
            tracking_code="AP-P5M-001",
            shipping_type="domestic",
            contact_phone="09123456789",
            customer_first_name="Assigned",
            customer_last_name="Customer",
            transport_method="legacy-road",
            domestic_transport_method="road",
            status_request_status="new",
            status="assigned",
            assigned_to=expert.id,
            origin_province_id=province.id,
            origin_county_id=county.id,
            origin_city_id=city.id,
            dest_province_id=province.id,
            dest_county_id=county.id,
            dest_city_id=city.id,
            priority="high",
            created_at=now - timedelta(hours=2),
            sla_due_at=now - timedelta(minutes=30),
        )
        won_request = ShipmentRequest(
            tracking_code="AP-P5M-002",
            shipping_type="domestic",
            contact_phone="09123456780",
            customer_first_name="Won",
            customer_last_name="Customer",
            transport_method="air",
            status_request_status="new",
            status="won",
            assigned_to=expert.id,
            origin_province_id=province.id,
            created_at=now - timedelta(days=2),
        )
        new_request = ShipmentRequest(
            tracking_code="AP-P5M-003",
            shipping_type="domestic",
            contact_phone="09123456781",
            customer_first_name="New",
            customer_last_name="Customer",
            transport_method="sea",
            status_request_status="new",
            status="new",
            assigned_to=None,
            created_at=now - timedelta(days=10),
        )
        db.session.add_all([assigned_request, won_request, new_request])
        db.session.flush()

        assignment_log = AssignmentLog(
            shipment_request_id=assigned_request.id,
            assigned_expert_id=expert.id,
            assignment_method="automatic",
            assignment_reason="Seed assignment",
            created_at=now - timedelta(hours=2),
        )
        response_log = ExpertConsoleLog(
            shipment_request_id=assigned_request.id,
            expert_user_id=expert.id,
            action="message_added",
            created_at=now - timedelta(hours=1),
        )
        db.session.add_all([assignment_log, response_log])
        db.session.commit()

        return {
            "app": app,
            "admin_token": security.generate_token(admin.id, "access"),
            "expert_token": security.generate_token(expert.id, "access"),
            "expert_id": expert.id,
            "assigned_request_id": assigned_request.id,
            "new_request_id": new_request.id,
            "province_id": province.id,
        }


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_shipment_request_detail_and_list_contract(admin_panel_app):
    """Admin request detail/list keep auth, filters, date errors, pagination, and location shape."""
    client = admin_panel_app["app"].test_client()
    admin_headers = _auth_headers(admin_panel_app["admin_token"])
    expert_headers = _auth_headers(admin_panel_app["expert_token"])
    expected_forbidden_payload = {
        "error": "\u062f\u0633\u062a\u0631\u0633\u06cc \u063a\u06cc\u0631\u0645\u062c\u0627\u0632",
        "required_roles": ["admin"],
        "user_role": "expert",
    }

    unauthenticated_detail = client.get(
        f"/api/admin/shipment-requests/{admin_panel_app['assigned_request_id']}"
    )
    assert unauthenticated_detail.status_code == 401
    assert unauthenticated_detail.get_json() == {"error": "Token is missing"}

    forbidden_detail = client.get(
        f"/api/admin/shipment-requests/{admin_panel_app['assigned_request_id']}",
        headers=expert_headers,
    )
    assert forbidden_detail.status_code == 403
    assert forbidden_detail.get_json() == expected_forbidden_payload

    unauthenticated_list = client.get("/api/admin/shipment-requests")
    assert unauthenticated_list.status_code == 401
    assert unauthenticated_list.get_json() == {"error": "Token is missing"}

    forbidden_list = client.get("/api/admin/shipment-requests", headers=expert_headers)
    assert forbidden_list.status_code == 403
    assert forbidden_list.get_json() == expected_forbidden_payload

    missing_detail = client.get("/api/admin/shipment-requests/999999", headers=admin_headers)
    assert missing_detail.status_code == 404
    assert missing_detail.get_json() == {"error": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0645\u0648\u0631\u062f\u0646\u0638\u0631 \u06cc\u0627\u0641\u062a \u0646\u0634\u062f"}

    detail = client.get(f"/api/admin/shipment-requests/{admin_panel_app['assigned_request_id']}", headers=admin_headers)
    assert detail.status_code == 200
    detail_payload = detail.get_json()
    assert set(detail_payload.keys()) == {
        "id",
        "contact_phone",
        "customer_first_name",
        "customer_last_name",
        "transport_method",
        "status",
        "priority",
        "assigned_to",
        "origin",
        "destination",
        "created_at",
        "sla_due_at",
    }
    assert detail_payload["assigned_to"] == {
        "id": admin_panel_app["expert_id"],
        "full_name": "Phase 5M Expert",
        "username": "phase5m_expert",
    }
    assert detail_payload["origin"] == {"province": "Tehran", "county": "Tehran County", "city": "Tehran City"}

    invalid_date = client.get("/api/admin/shipment-requests?date_from=not-a-date", headers=admin_headers)
    assert invalid_date.status_code == 400
    assert invalid_date.get_json() == {"error": "\u0641\u0631\u0645\u062a \u062a\u0627\u0631\u06cc\u062e \u0646\u0627\u0645\u0639\u062a\u0628\u0631 \u0627\u0633\u062a"}

    list_response = client.get(
        f"/api/admin/shipment-requests?status=assigned&province_id={admin_panel_app['province_id']}&limit=1&offset=0",
        headers=admin_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert set(list_payload.keys()) == {"requests", "pagination"}
    assert list_payload["pagination"] == {"total": 1, "limit": 1, "offset": 0, "has_more": False}
    assert len(list_payload["requests"]) == 1
    assert list_payload["requests"][0]["id"] == admin_panel_app["assigned_request_id"]
    assert list_payload["requests"][0]["assigned_to"] == admin_panel_app["expert_id"]
    assert list_payload["requests"][0]["origin"] == {"province": "Tehran", "county": "Tehran County", "city": "Tehran City"}


def test_admin_dashboard_and_assignment_summary_contract(admin_panel_app):
    """Dashboard and assignment summary keep aggregate keys, counts, and report shape."""
    client = admin_panel_app["app"].test_client()
    admin_headers = _auth_headers(admin_panel_app["admin_token"])
    expert_headers = _auth_headers(admin_panel_app["expert_token"])

    unauthenticated_dashboard = client.get("/api/admin/dashboard")
    assert unauthenticated_dashboard.status_code == 401
    assert unauthenticated_dashboard.get_json() == {"error": "Token is missing"}

    forbidden_dashboard = client.get("/api/admin/dashboard", headers=expert_headers)
    assert forbidden_dashboard.status_code == 403
    assert forbidden_dashboard.get_json() == {
        "error": "\u062f\u0633\u062a\u0631\u0633\u06cc \u063a\u06cc\u0631\u0645\u062c\u0627\u0632",
        "required_roles": ["admin"],
        "user_role": "expert",
    }

    unauthenticated_summary = client.get("/api/admin/reports/assignment-summary")
    assert unauthenticated_summary.status_code == 401
    assert unauthenticated_summary.get_json() == {"error": "Token is missing"}

    forbidden_summary = client.get(
        "/api/admin/reports/assignment-summary",
        headers=expert_headers,
    )
    assert forbidden_summary.status_code == 403
    assert forbidden_summary.get_json() == {
        "error": "دسترسی غیرمجاز",
        "required_roles": ["admin"],
        "user_role": "expert",
    }

    dashboard = client.get("/api/admin/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    dashboard_payload = dashboard.get_json()
    assert set(dashboard_payload.keys()) == {
        "total_requests",
        "requests_per_transport_method",
        "requests_per_status",
        "last_7_days_count",
        "last_24h_count",
        "unassigned_count",
        "top_provinces",
    }
    assert dashboard_payload["total_requests"] == 3
    assert dashboard_payload["requests_per_transport_method"] == {
        "air": 1,
        "road": 1,
        "sea": 1,
    }
    assert dashboard_payload["requests_per_status"] == {"assigned": 1, "new": 1, "won": 1}
    assert dashboard_payload["last_7_days_count"] == 2
    assert dashboard_payload["last_24h_count"] == 1
    assert dashboard_payload["unassigned_count"] == 1
    assert dashboard_payload["top_provinces"] == [{"province": "Tehran", "count": 2}]

    summary = client.get("/api/admin/reports/assignment-summary", headers=admin_headers)
    assert summary.status_code == 200
    summary_payload = summary.get_json()
    assert set(summary_payload.keys()) == {"assignments_per_expert", "overall_stats", "generated_at"}
    assert len(summary_payload["assignments_per_expert"]) == 1
    expert_summary = summary_payload["assignments_per_expert"][0]
    assert expert_summary == {
        "expert_id": admin_panel_app["expert_id"],
        "expert_name": "Phase 5M Expert",
        "username": "phase5m_expert",
        "role": "expert",
        "total_assignments": 2,
        "won_count": 1,
        "lost_count": 0,
        "active_count": 1,
        "conversion_rate": 50.0,
        "avg_response_time_hours": None,
    }
    assert summary_payload["overall_stats"] == {
        "total_assignments": 2,
        "total_won": 1,
        "overall_conversion_rate": 50.0,
        "avg_response_time_hours": 1.0,
        "sla_violations": 1,
    }
    assert "T" in summary_payload["generated_at"]


def test_admin_assignment_summary_sla_violation_contract(admin_panel_app):
    """Admin report SLA violation count keeps current active-status interpretation."""
    now = datetime.utcnow()

    with admin_panel_app["app"].app_context():
        db.session.add_all([
            ShipmentRequest(
                tracking_code="AP-P11B-SLA-IN-PROGRESS",
                shipping_type="domestic",
                contact_phone="09125000001",
                status_request_status="new",
                status="in_progress",
                priority="normal",
                assigned_to=admin_panel_app["expert_id"],
                sla_due_at=now - timedelta(minutes=5),
            ),
            ShipmentRequest(
                tracking_code="AP-P11B-SLA-WAITING",
                shipping_type="domestic",
                contact_phone="09125000002",
                status_request_status="new",
                status="waiting_for_customer",
                priority="high",
                assigned_to=admin_panel_app["expert_id"],
                sla_due_at=now - timedelta(minutes=10),
            ),
            ShipmentRequest(
                tracking_code="AP-P11B-SLA-FUTURE",
                shipping_type="domestic",
                contact_phone="09125000003",
                status_request_status="new",
                status="assigned",
                priority="urgent",
                assigned_to=admin_panel_app["expert_id"],
                sla_due_at=now + timedelta(hours=1),
            ),
            ShipmentRequest(
                tracking_code="AP-P11B-SLA-CLOSED",
                shipping_type="domestic",
                contact_phone="09125000004",
                status_request_status="new",
                status="closed",
                priority="low",
                assigned_to=admin_panel_app["expert_id"],
                sla_due_at=now - timedelta(hours=1),
            ),
        ])
        db.session.commit()

        assert calculate_sla_violations() == 3
