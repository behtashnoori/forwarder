from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
import json

from backend.models import ExpertUser, Province, ReferralAssignmentLog, ReferralRule, ShipmentRequest
from backend.operational_models import OrganizationHostname, OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens
from backend.services.organization_hostname_service import normalize_hostname, resolve_organization_for_host


@pytest.fixture()
def routing_app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "hostname-routing-test",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        province = Province(code="TEH", name_fa="تهران")
        samand = OperationalOrganization(public_id="samand-tarabar", name="Samand Tarabar")
        company_b = OperationalOrganization(public_id="company-b", name="Company B")
        samand_expert = ExpertUser(
            username="samand-expert", password_hash="x", full_name="Samand Expert",
            role="expert", authority="EXPERT", is_active=True, can_handle_domestic=True,
        )
        company_expert = ExpertUser(
            username="company-expert", password_hash="x", full_name="Company Expert",
            role="expert", authority="EXPERT", is_active=True, can_handle_domestic=True,
        )
        samand_admin = ExpertUser(
            username="samand-admin", password_hash="x", full_name="Samand Admin",
            role="admin", authority="ORGANIZATION_ADMIN", is_active=True,
        )
        company_admin = ExpertUser(
            username="company-admin", password_hash="x", full_name="Company Admin",
            role="admin", authority="ORGANIZATION_ADMIN", is_active=True,
        )
        db.session.add_all([province, samand, company_b, samand_expert, company_expert, samand_admin, company_admin])
        db.session.flush()
        db.session.add_all([
            OrganizationHostname(organization_id=samand.id, hostname="samand.logisticmarket.ir", is_primary=True),
            OrganizationHostname(organization_id=company_b.id, hostname="companyb.logisticmarket.ir", is_primary=True),
            OperationalMembership(organization_id=samand.id, user_id=samand_expert.id, permissions=[]),
            OperationalMembership(organization_id=samand.id, user_id=samand_admin.id, permissions=[]),
            OperationalMembership(organization_id=company_b.id, user_id=company_expert.id, permissions=[]),
            OperationalMembership(organization_id=company_b.id, user_id=company_admin.id, permissions=[]),
        ])
        db.session.commit()
        yield {
            "app": app, "province": province.id,
            "samand": samand.id, "company": company_b.id,
            "samand_expert": samand_expert.id, "company_expert": company_expert.id,
            "samand_admin_token": create_session_tokens(samand_admin.id)["access_token"],
            "company_admin_token": create_session_tokens(company_admin.id)["access_token"],
        }
        db.session.remove()
        db.drop_all()


def payload(province_id: int, **extra):
    result = {
        "shipping_type": "domestic", "origin_province_id": province_id,
        "dest_province_id": province_id, "contact_phone": "09123456789",
        "cargo_description": "Hostname routing adversarial case",
    }
    result.update(extra)
    return result


def headers(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("host", "organization_key", "expert_key"),
    [
        ("samand.logisticmarket.ir", "samand", "samand_expert"),
        ("companyb.logisticmarket.ir", "company", "company_expert"),
    ],
)
def test_exact_host_binds_and_assigns_only_within_resolved_organization(routing_app, host, organization_key, expert_key):
    client = routing_app["app"].test_client()
    response = client.post(
        "/api/shipment-request?organization_id=999999",
        base_url=f"https://{host}",
        json=payload(routing_app["province"], organization_id=999999),
    )
    assert response.status_code == 201
    with routing_app["app"].app_context():
        row = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert row.ownership_scope == "TENANT"
        assert row.operational_organization_id == routing_app[organization_key]
        assert row.assigned_to == routing_app[expert_key]
        log = ReferralAssignmentLog.query.filter_by(request_id=row.id).one()
        assert log.operational_organization_id == routing_app[organization_key]


def test_unknown_inactive_and_malformed_hosts_preserve_unowned_intake(routing_app):
    client = routing_app["app"].test_client()
    for host in ("unknown.logisticmarket.ir", "bad_host.example"):
        response = client.post("/api/shipment-request", headers={"Host": host}, json=payload(routing_app["province"]))
        assert response.status_code == 201
        with routing_app["app"].app_context():
            row = db.session.get(ShipmentRequest, response.get_json()["id"])
            assert row.ownership_scope == "INTAKE"
            assert row.operational_organization_id is None
            assert row.assigned_to is None
    with routing_app["app"].app_context():
        assert resolve_organization_for_host("samand.logisticmarket.ir:bad") is None
    with routing_app["app"].app_context():
        OrganizationHostname.query.filter_by(hostname="samand.logisticmarket.ir").one().is_active = False
        db.session.commit()
    response = client.post("/api/shipment-request", base_url="https://samand.logisticmarket.ir", json=payload(routing_app["province"]))
    with routing_app["app"].app_context():
        assert db.session.get(ShipmentRequest, response.get_json()["id"]).ownership_scope == "INTAKE"


def test_inactive_organization_fails_closed(routing_app):
    with routing_app["app"].app_context():
        db.session.get(OperationalOrganization, routing_app["samand"]).is_active = False
        db.session.commit()
        assert resolve_organization_for_host("samand.logisticmarket.ir") is None


def test_normalization_and_database_invariants(routing_app):
    assert normalize_hostname(" SAMAND.LogisticMarket.IR:443 ") == "samand.logisticmarket.ir"
    with routing_app["app"].app_context():
        db.session.add(OrganizationHostname(
            organization_id=routing_app["company"], hostname="samand.logisticmarket.ir", is_active=True,
        ))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        db.session.add(OrganizationHostname(
            organization_id=routing_app["samand"], hostname="forwarder.samandtarabar.com", is_primary=True,
        ))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_unassigned_queue_and_cross_tenant_manual_assignment_fence(routing_app):
    client = routing_app["app"].test_client()
    with routing_app["app"].app_context():
        db.session.get(ExpertUser, routing_app["samand_expert"]).is_active = False
        db.session.commit()
    response = client.post("/api/shipment-request", base_url="https://samand.logisticmarket.ir", json=payload(routing_app["province"]))
    request_id = response.get_json()["id"]
    queue = client.get("/api/admin/unassigned-requests", headers=headers(routing_app["samand_admin_token"]))
    assert queue.status_code == 200
    assert [row["id"] for row in queue.get_json()["requests"]] == [request_id]
    other_queue = client.get("/api/admin/unassigned-requests", headers=headers(routing_app["company_admin_token"]))
    assert other_queue.get_json()["requests"] == []
    cross = client.post(
        f"/api/admin/shipment-requests/{request_id}/assign",
        headers=headers(routing_app["samand_admin_token"]), json={"expert_id": routing_app["company_expert"]},
    )
    assert cross.status_code == 404


def test_assign_to_me_ignores_arbitrary_expert_identity(routing_app):
    client = routing_app["app"].test_client()
    with routing_app["app"].app_context():
        row = ShipmentRequest(
            contact_phone="09123456788", shipping_type="domestic", status="new",
            status_request_status="new", ownership_scope="TENANT",
            operational_organization_id=routing_app["company"], assigned_to=None,
        )
        db.session.add(row); db.session.commit(); request_id = row.id
        token = create_session_tokens(routing_app["company_expert"])["access_token"]
    response = client.post(
        f"/api/expert/requests/{request_id}/assign-to-me",
        headers=headers(token), json={"expert_id": routing_app["samand_expert"]},
    )
    assert response.status_code == 200
    assert response.get_json()["assigned_to"]["id"] == routing_app["company_expert"]


def test_tenant_hostname_submission_cannot_cross_assign_through_referral_rule(routing_app):
    with routing_app["app"].app_context():
        db.session.add(ReferralRule(
            name="Cross-tenant stale hostname rule",
            operational_organization_id=routing_app["samand"],
            is_active=True,
            priority=1,
            conditions=json.dumps({"shipping_type": "domestic"}),
            action=json.dumps({
                "type": "direct_assign",
                "expert_id": routing_app["company_expert"],
            }),
            stop_on_match=True,
            created_by=routing_app["samand_expert"],
        ))
        db.session.commit()

    response = routing_app["app"].test_client().post(
        "/api/shipment-request",
        base_url="https://samand.logisticmarket.ir",
        json=payload(routing_app["province"]),
    )
    assert response.status_code == 201
    with routing_app["app"].app_context():
        row = db.session.get(ShipmentRequest, response.get_json()["id"])
        assert row.operational_organization_id == routing_app["samand"]
        assert row.assigned_to is None
