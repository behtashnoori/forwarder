"""S4 regression coverage for governed dashboard and reporting oversight."""
from __future__ import annotations

from datetime import datetime, timedelta

import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, Province, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reporting_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "s4-test"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
        platform = ExpertUser(username="s4_platform", password_hash=password_hash, full_name="Platform", email="platform@s4.test", role="admin", authority="PLATFORM_ADMIN", is_active=True)
        admin_a = ExpertUser(username="s4_admin_a", password_hash=password_hash, full_name="Admin A", email="a@s4.test", role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        admin_b = ExpertUser(username="s4_admin_b", password_hash=password_hash, full_name="Admin B", email="b@s4.test", role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        expert = ExpertUser(username="s4_expert", password_hash=password_hash, full_name="Expert", email="expert@s4.test", role="expert", authority="EXPERT", is_active=True)
        org_a, org_b, org_empty = OperationalOrganization(name="S4 A"), OperationalOrganization(name="S4 B"), OperationalOrganization(name="S4 Empty")
        province = Province(code="THR-S4", name_fa="Tehran")
        db.session.add_all([platform, admin_a, admin_b, expert, org_a, org_b, org_empty, province])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=org_a.id, user_id=admin_a.id),
            OperationalMembership(organization_id=org_b.id, user_id=admin_b.id),
            OperationalMembership(organization_id=org_a.id, user_id=expert.id),
        ])
        now = datetime.utcnow()

        def request(code, organization, status, method, age, province_id=None, shipping_type="domestic", assigned_to=None):
            return ShipmentRequest(
                tracking_code=code, contact_phone="09120000000", ownership_scope="TENANT",
                operational_organization_id=organization.id, status=status, status_request_status="new",
                domestic_transport_method=method if shipping_type == "domestic" else None,
                international_transport_method=method if shipping_type == "international" else None,
                shipping_type=shipping_type, origin_province_id=province_id, assigned_to=assigned_to,
                created_at=now - age,
            )

        db.session.add_all([
            request("S4-A-1", org_a, "new", "road", timedelta(hours=1), province.id),
            request("S4-A-2", org_a, "assigned", "air", timedelta(hours=25), province.id, assigned_to=admin_a.id),
            request("S4-A-3", org_a, "won", "sea", timedelta(days=6), None, "international"),
            request("S4-A-4", org_a, "lost", "road", timedelta(days=8), province.id),
            request("S4-B-1", org_b, "in_progress", "rail", timedelta(hours=2), province.id),
            request("S4-B-2", org_b, "closed", "road", timedelta(days=9), None, "international"),
        ])
        db.session.commit()
        return {
            "app": app,
            "headers": {"platform": _headers(create_session_tokens(platform.id)["access_token"]), "a": _headers(create_session_tokens(admin_a.id)["access_token"]), "b": _headers(create_session_tokens(admin_b.id)["access_token"]), "expert": _headers(create_session_tokens(expert.id)["access_token"])},
            "org_a": org_a.public_id, "org_b": org_b.public_id, "org_empty": org_empty.public_id,
        }


def test_dashboard_authorization_and_exact_aggregation(reporting_app):
    client, headers = reporting_app["app"].test_client(), reporting_app["headers"]
    a = client.get("/api/admin/dashboard", headers=headers["a"])
    b = client.get("/api/admin/dashboard", headers=headers["b"])
    platform = client.get("/api/admin/dashboard", headers=headers["platform"])
    platform_a = client.get(f"/api/admin/dashboard?organization_public_id={reporting_app['org_a']}", headers=headers["platform"])

    assert a.status_code == b.status_code == platform.status_code == platform_a.status_code == 200
    assert a.get_json() == {
        "total_requests": 4, "requests_per_status": {"assigned": 1, "lost": 1, "new": 1, "won": 1},
        "requests_per_transport_method": {"air": 1, "road": 2, "sea": 1}, "last_24h_count": 1,
        "last_7_days_count": 3, "unassigned_count": 1, "top_provinces": [{"province": "Tehran", "count": 3}],
    }
    assert b.get_json()["total_requests"] == 2
    assert b.get_json()["requests_per_status"] == {"closed": 1, "in_progress": 1}
    assert platform.get_json()["total_requests"] == 6
    assert platform_a.get_json() == a.get_json()


def test_reporting_tenant_filters_and_empty_contract(reporting_app):
    client, headers = reporting_app["app"].test_client(), reporting_app["headers"]
    forged = client.get(f"/api/admin/dashboard?organization_public_id={reporting_app['org_b']}", headers=headers["a"])
    invalid = client.get("/api/admin/dashboard?organization_public_id=not-an-org", headers=headers["platform"])
    empty = client.get(f"/api/admin/dashboard?organization_public_id={reporting_app['org_empty']}", headers=headers["platform"])
    expert = client.get("/api/admin/dashboard", headers=headers["expert"])

    assert forged.status_code == 403
    assert invalid.status_code == 404
    assert expert.status_code == 403
    assert empty.status_code == 200
    assert empty.get_json() == {
        "total_requests": 0, "requests_per_status": {}, "requests_per_transport_method": {},
        "last_24h_count": 0, "last_7_days_count": 0, "unassigned_count": 0, "top_provinces": [],
    }


def test_overview_and_xlsx_are_tenant_fenced_before_output(reporting_app):
    client, headers = reporting_app["app"].test_client(), reporting_app["headers"]
    overview_a = client.get("/api/admin/reports/overview?period=weekly", headers=headers["a"])
    export_a = client.get("/api/admin/reports/export.xlsx?period=weekly", headers=headers["a"])
    overview_platform_a = client.get(f"/api/admin/reports/overview?period=weekly&organization_public_id={reporting_app['org_a']}", headers=headers["platform"])
    summary_expert = client.get("/api/admin/reports/assignment-summary", headers=headers["expert"])

    assert overview_a.status_code == overview_platform_a.status_code == 200
    assert overview_a.get_json()["summary"]["total_requests"] == 3
    assert overview_platform_a.get_json()["summary"]["total_requests"] == 3
    assert export_a.status_code == 200
    assert export_a.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert summary_expert.status_code == 403
