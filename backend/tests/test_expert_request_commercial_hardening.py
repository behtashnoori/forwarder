"""Owning-Expert Customer linkage and derived commercial-state contracts."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend import create_app
from backend.customer_entitlement_models import CustomerEntitlement
from backend.extensions import db
from backend.models import (
    CRMCustomerLinkAudit,
    Customer,
    ExpertConsoleLog,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture
def commercial_app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "commercial-test-secret",
    }, skip_startup=True)
    with app.app_context():
        db.create_all()
        org = OperationalOrganization(public_id="commercial-org", name="Commercial Org", is_active=True)
        foreign_org = OperationalOrganization(public_id="foreign-org", name="Foreign Org", is_active=True)
        owner = ExpertUser(
            username="commercial-owner", password_hash="unused", full_name="Owning Expert",
            role="expert", authority="EXPERT", is_active=True,
        )
        peer = ExpertUser(
            username="commercial-peer", password_hash="unused", full_name="Peer Expert",
            role="expert", authority="EXPERT", is_active=True,
        )
        db.session.add_all([org, foreign_org, owner, peer])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=org.id, user_id=owner.id, is_active=True, permissions=[]),
            OperationalMembership(organization_id=org.id, user_id=peer.id, is_active=True, permissions=[]),
        ])
        customers = [
            Customer(
                operational_organization_id=org.id, ownership_scope="TENANT", status="active",
                first_name="آرمان", last_name="تجارت", company_name="آرمان تجارت", phone="09120000001",
                email="arman@example.test",
            ),
            Customer(
                operational_organization_id=org.id, ownership_scope="TENANT", status="active",
                first_name="بهین", last_name="بار", company_name="بهین بار", phone="09120000002",
                email="behin@example.test",
            ),
            Customer(
                operational_organization_id=org.id, ownership_scope="TENANT", status="inactive",
                first_name="غیرفعال", last_name="سازمان", company_name="غیرفعال", email="inactive@example.test",
            ),
            Customer(
                operational_organization_id=foreign_org.id, ownership_scope="TENANT", status="active",
                first_name="بیگانه", last_name="سازمان", company_name="سازمان دیگر", email="foreign@example.test",
            ),
        ]
        db.session.add_all(customers)
        db.session.flush()

        def add_request(code: str, status: str) -> ShipmentRequest:
            row = ShipmentRequest(
                tracking_code=code,
                shipping_type="domestic",
                contact_phone="09121111111",
                customer_first_name="درخواست",
                customer_last_name="آزمایشی",
                status=status,
                status_request_status=status,
                assigned_to=owner.id,
                ownership_scope="TENANT",
                operational_organization_id=org.id,
            )
            db.session.add(row)
            db.session.flush()
            return row

        accepted = add_request("COMM-ACCEPTED", "waiting_for_customer")
        discussion = add_request("COMM-DISCUSSION", "waiting_for_customer")
        declined = add_request("COMM-DECLINED", "waiting_for_customer")
        waiting = add_request("COMM-WAITING", "waiting_for_customer")
        completed = add_request("COMM-COMPLETED", "won")
        now = datetime.utcnow()
        db.session.add(ExpertQuote(
            shipment_request_id=accepted.id,
            amount=1_100_000,
            currency="IRR",
            created_by_expert_id=owner.id,
            created_at=now - timedelta(hours=1),
            customer_response="discussion",
            customer_response_message="شرایط پرداخت نیاز به مذاکره دارد",
            responded_at=now - timedelta(minutes=50),
        ))
        db.session.add(ExpertQuote(
            shipment_request_id=waiting.id,
            amount=900_000,
            currency="IRR",
            created_by_expert_id=owner.id,
            created_at=now - timedelta(hours=2),
            customer_response="accepted",
            responded_at=now - timedelta(hours=1, minutes=50),
        ))
        for position, (row, response, message) in enumerate([
            (accepted, "accepted", None),
            (discussion, "discussion", "لطفاً شرایط پرداخت بازبینی شود"),
            (declined, "declined", None),
            (waiting, None, None),
        ]):
            db.session.add(ExpertQuote(
                shipment_request_id=row.id,
                amount=1_234_500 + position,
                currency="IRR",
                created_by_expert_id=owner.id,
                created_at=now + timedelta(seconds=position),
                customer_response=response,
                customer_response_message=message,
                responded_at=(now + timedelta(minutes=position + 1)) if response else None,
            ))
        db.session.add(ExpertConsoleLog(
            shipment_request_id=accepted.id,
            expert_user_id=owner.id,
            action="status_change",
            old_status="in_progress",
            new_status="waiting_for_customer",
            note="تغییر وضعیت تجاری توسط کارشناس",
            created_at=now + timedelta(minutes=10),
        ))
        db.session.commit()
        seed = {
            "app": app,
            "owner_token": create_session_tokens(owner.id)["access_token"],
            "peer_token": create_session_tokens(peer.id)["access_token"],
            "request_public_id": accepted.public_id,
            "request_id": accepted.id,
            "active_customer_ids": [customers[0].id, customers[1].id],
            "inactive_customer_id": customers[2].id,
            "foreign_customer_id": customers[3].id,
        }
        yield seed
        db.session.remove()
        db.drop_all()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_owning_expert_search_link_and_relink_are_tenant_bounded_and_audited(commercial_app):
    client = commercial_app["app"].test_client()
    request_public_id = commercial_app["request_public_id"]
    owner_headers = auth(commercial_app["owner_token"])

    assert client.get(
        f"/api/expert/requests/{request_public_id}/organization-customer",
        headers=auth(commercial_app["peer_token"]),
    ).status_code == 404

    search = client.get(
        f"/api/expert/requests/{request_public_id}/organization-customers?search=بار",
        headers=owner_headers,
    )
    assert search.status_code == 200
    assert [row["company_name"] for row in search.get_json()["customers"]] == ["بهین بار"]

    for rejected_id in (commercial_app["inactive_customer_id"], commercial_app["foreign_customer_id"]):
        rejected = client.put(
            f"/api/expert/requests/{request_public_id}/organization-customer",
            headers=owner_headers,
            json={"customer_id": rejected_id},
        )
        assert rejected.status_code == 404

    with commercial_app["app"].app_context():
        entitlement_count = CustomerEntitlement.query.count()

    first_id, second_id = commercial_app["active_customer_ids"]
    linked = client.put(
        f"/api/expert/requests/{request_public_id}/organization-customer",
        headers=owner_headers,
        json={"customer_id": first_id},
    )
    assert linked.status_code == 200
    assert linked.get_json()["operation"] == "link"
    relinked = client.put(
        f"/api/expert/requests/{request_public_id}/organization-customer",
        headers=owner_headers,
        json={"customer_id": second_id},
    )
    assert relinked.status_code == 200
    assert relinked.get_json()["operation"] == "relink"
    reopened = client.get(
        f"/api/expert/requests/{request_public_id}/organization-customer",
        headers=owner_headers,
    )
    assert reopened.status_code == 200
    assert reopened.get_json()["customer"]["id"] == second_id

    with commercial_app["app"].app_context():
        request_row = db.session.get(ShipmentRequest, commercial_app["request_id"])
        assert request_row.customer_id == second_id
        assert request_row.status == "waiting_for_customer"
        audits = CRMCustomerLinkAudit.query.order_by(CRMCustomerLinkAudit.id).all()
        assert [(row.operation, row.source) for row in audits] == [
            ("link", "expert_request_review"),
            ("relink", "expert_request_review"),
        ]
        assert CustomerEntitlement.query.count() == entitlement_count


def test_commercial_buckets_counts_detail_and_timeline_share_one_projection(commercial_app):
    client = commercial_app["app"].test_client()
    headers = auth(commercial_app["owner_token"])

    needs_action = client.get("/api/expert/requests?bucket=needs_action&per_page=50", headers=headers)
    assert needs_action.status_code == 200
    needs_payload = needs_action.get_json()
    assert needs_payload["pagination"]["total"] == 3
    assert {row["commercial"]["latest_quote_response"] for row in needs_payload["requests"]} == {
        "accepted", "discussion", "declined",
    }

    waiting = client.get("/api/expert/requests?bucket=waiting_for_customer", headers=headers)
    assert waiting.status_code == 200
    assert [row["tracking_number"] for row in waiting.get_json()["requests"]] == ["COMM-WAITING"]

    kpis = client.get("/api/expert/dashboard/kpis", headers=headers)
    assert kpis.status_code == 200
    counts = kpis.get_json()["counts"]
    assert counts["needs_action"] == 3
    assert counts["waiting_for_customer"] == 1
    assert counts["completed"] == 1

    linked = client.put(
        f"/api/expert/requests/{commercial_app['request_public_id']}/organization-customer",
        headers=headers,
        json={"customer_id": commercial_app["active_customer_ids"][0]},
    )
    assert linked.status_code == 200

    detail = client.get(
        f"/api/expert/requests/{commercial_app['request_public_id']}", headers=headers,
    )
    assert detail.status_code == 200
    body = detail.get_json()
    assert body["status"] == "waiting_for_customer"
    assert body["commercial"]["request_status_label_fa"] == "در انتظار جمع‌بندی کارشناس"
    assert body["commercial"]["next_action"]["code"] == "expert_finalize_accepted"
    assert len(body["quote_history"]) == 2
    assert any(event["title"] == "پیشنهاد برای مشتری ارسال شد" for event in body["timeline"])
    assert any(event["title"] == "مشتری درخواست مذاکره کرد" for event in body["timeline"])
    assert any(event["title"] == "مشتری پیشنهاد را پذیرفت" for event in body["timeline"])
    assert any(event["title"] == "وضعیت تجاری درخواست تغییر کرد" for event in body["timeline"])
    assert any(event["title"] == "مشتری سازمان به درخواست متصل شد" for event in body["timeline"])
    assert all("old_customer_id" not in (event.get("description") or "") for event in body["timeline"])


def test_every_supported_request_status_remains_discoverable_and_bucket_counts_match_rows(commercial_app):
    app = commercial_app["app"]
    with app.app_context():
        owner_id = ExpertUser.query.filter_by(username="commercial-owner").one().id
        org_id = OperationalOrganization.query.filter_by(public_id="commercial-org").one().id
        created: dict[str, str] = {}
        for status in ("new", "assigned", "in_progress", "quoted", "waiting_for_customer", "won", "lost", "closed"):
            row = ShipmentRequest(
                tracking_code=f"STATUS-{status.upper()}",
                shipping_type="domestic",
                contact_phone="09123333333",
                status=status,
                status_request_status=status,
                assigned_to=owner_id,
                ownership_scope="TENANT",
                operational_organization_id=org_id,
            )
            db.session.add(row)
            db.session.flush()
            created[status] = row.public_id
            if status == "waiting_for_customer":
                db.session.add(ExpertQuote(
                    shipment_request_id=row.id,
                    amount=1_000_000,
                    currency="IRR",
                    created_by_expert_id=owner_id,
                ))
        db.session.commit()

    client = app.test_client()
    headers = auth(commercial_app["owner_token"])
    for status, public_id in created.items():
        filtered = client.get(f"/api/expert/requests?status={status}&per_page=100", headers=headers)
        assert filtered.status_code == 200
        assert public_id in {row["public_id"] for row in filtered.get_json()["requests"]}
        detail = client.get(f"/api/expert/requests/{public_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.get_json()["commercial"]["request_status"] == status

    kpis = client.get("/api/expert/dashboard/kpis", headers=headers).get_json()["counts"]
    count_keys = {
        "all": "total_visible",
        "new": "new",
        "assigned": "assigned",
        "in_progress": "in_progress",
        "quoted": "quoted",
        "waiting_for_customer": "waiting_for_customer",
        "needs_action": "needs_action",
        "completed": "completed",
    }
    for bucket, count_key in count_keys.items():
        rows = client.get(f"/api/expert/requests?bucket={bucket}&per_page=100", headers=headers).get_json()
        assert rows["pagination"]["total"] == kpis[count_key]
