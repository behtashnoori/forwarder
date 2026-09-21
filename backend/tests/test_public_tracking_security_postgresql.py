"""PostgreSQL 18 proof for the MT-3 public authority boundary."""
from __future__ import annotations

import json
import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalOrganization, OperationalShipment


CAPABILITY_A = "SR2-PA23456789012345678901"
CAPABILITY_B = "SR2-PB23456789012345678901"
PUBLIC_KEYS = {
    "tracking_number",
    "status",
    "created_at",
    "shipping_type",
    "route",
    "transport_method",
    "domestic_transport_method",
    "international_transport_method",
    "transport_method_preference",
    "assigned_at",
    "workflow_steps_simple",
    "unit_tracking",
}


def _owned_database_url() -> str:
    value = os.environ.get("MT3_TEST_DATABASE_URL")
    if not value:
        pytest.skip("MT3_TEST_DATABASE_URL is not configured")
    parsed = make_url(value)
    if parsed.host != "127.0.0.1" or not (parsed.database or "").startswith("forwarder_mt3_"):
        raise RuntimeError("MT-3 PostgreSQL proof requires its owned loopback database")
    return value


def test_postgresql_numeric_and_cross_tenant_authority_is_fail_closed():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": _owned_database_url(),
            "SECRET_KEY": "mt3-owned-postgresql-proof",
        },
        skip_startup=True,
    )
    with app.app_context():
        server_version = int(db.session.execute(text("SHOW server_version_num")).scalar_one())
        assert 180000 <= server_version < 190000

        organization_a = OperationalOrganization(name="[MT3-PG] Tenant A")
        organization_b = OperationalOrganization(name="[MT3-PG] Tenant B")
        expert = ExpertUser(
            username="mt3-postgresql-expert",
            password_hash="not-used",
            full_name="Private PostgreSQL Expert",
            role="expert",
        )
        db.session.add_all([organization_a, organization_b, expert])
        db.session.flush()
        customer_a = Customer(
            ownership_scope="TENANT",
            operational_organization_id=organization_a.id,
            company_name="Private PostgreSQL Customer A",
            phone="09121111111",
        )
        customer_b = Customer(
            ownership_scope="TENANT",
            operational_organization_id=organization_b.id,
            company_name="Private PostgreSQL Customer B",
            phone="09122222222",
        )
        db.session.add_all([customer_a, customer_b])
        db.session.flush()
        request_a = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=organization_a.id,
            customer_id=customer_a.id,
            tracking_code=CAPABILITY_A,
            contact_phone="09123333333",
            customer_first_name="Private",
            customer_last_name="PostgreSQL A",
            shipping_type="international",
            origin_country="China",
            origin_city_international="Shanghai",
            origin_address_international="Private PostgreSQL origin",
            dest_country="Iran",
            dest_city_international="Tehran",
            dest_address_international="Private PostgreSQL destination",
            international_transport_method="combined_transport",
            cargo_description="Private PostgreSQL cargo",
            special_instructions="Private PostgreSQL instruction",
            status="won",
            status_request_status="new",
        )
        request_b = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=organization_b.id,
            customer_id=customer_b.id,
            tracking_code=CAPABILITY_B,
            contact_phone="09124444444",
            status="in_progress",
            status_request_status="new",
        )
        db.session.add_all([request_a, request_b])
        db.session.flush()
        shipment_a = OperationalShipment(
            organization_id=organization_a.id,
            source_type="direct",
            customer_id=customer_a.id,
            created_by_user_id=expert.id,
            primary_responsible_expert_id=expert.id,
        )
        shipment_b = OperationalShipment(
            organization_id=organization_b.id,
            source_type="direct",
            customer_id=customer_b.id,
            created_by_user_id=expert.id,
            primary_responsible_expert_id=expert.id,
        )
        db.session.add_all([shipment_a, shipment_b])
        db.session.commit()

        client = app.test_client()
        valid = client.get(f"/api/public/track/{CAPABILITY_A}?tenant_id={organization_b.id}&request_id={request_b.id}")
        assert valid.status_code == 200
        assert valid.headers["Cache-Control"] == "no-store"
        assert valid.headers["Referrer-Policy"] == "no-referrer"
        body = valid.get_json()
        assert set(body) == PUBLIC_KEYS
        assert body["tracking_number"] == CAPABILITY_A
        assert body["status"] == "won"
        serialized = json.dumps(body, ensure_ascii=False)
        for forbidden in (
            '"id"',
            '"organization_id"',
            "09123333333",
            "Private PostgreSQL",
            "Private PostgreSQL origin",
            "Private PostgreSQL destination",
            "Private PostgreSQL cargo",
            "Private PostgreSQL instruction",
        ):
            assert forbidden not in serialized

        numeric_probes = {
            "1",
            "2",
            "3",
            "10",
            "100",
            "9999",
            str(request_a.id),
            str(request_b.id),
            str(shipment_a.id),
            str(shipment_b.id),
        }
        responses = [client.get(f"/api/public/track/{probe}") for probe in numeric_probes]
        assert sum(response.status_code == 200 for response in responses) == 0
        assert all(response.status_code == 404 for response in responses)
        assert all(response.get_json() == {"message": "درخواست یافت نشد"} for response in responses)

        foreign = client.get(f"/api/public/track/{CAPABILITY_B}")
        assert foreign.status_code == 200
        assert foreign.get_json()["tracking_number"] == CAPABILITY_B
        assert CAPABILITY_A not in json.dumps(foreign.get_json())
