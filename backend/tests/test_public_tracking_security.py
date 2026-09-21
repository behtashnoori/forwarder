"""MT-3 regression contract for public Request tracking authority and privacy."""
from __future__ import annotations

import json

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import CaseDocumentFile, Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalOrganization, OperationalShipment
from backend.services.shipment_service import build_shipment_request_payload, generate_tracking_code
from backend.services.tracking_service import PUBLIC_TRACKING_CAPABILITY_PATTERN


CAPABILITY_A = "SR2-AAAAAAAAAAAAAAAAAAAAAA"
CAPABILITY_B = "SR2-BBBBBBBBBBBBBBBBBBBBBB"
UNKNOWN_CAPABILITY = "SR2-ZZZZZZZZZZZZZZZZZZZZZZ"
NOT_FOUND = {"message": "درخواست یافت نشد"}
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


@pytest.fixture()
def public_tracking_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "mt3-public-tracking-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        expert = ExpertUser(
            id=50,
            username="mt3-expert",
            password_hash="not-used",
            full_name="Private Expert Name",
            email="private-expert@example.test",
            phone="09121111111",
            role="expert",
        )
        organization_a = OperationalOrganization(id=70, name="MT3 Tenant A")
        organization_b = OperationalOrganization(id=80, name="MT3 Tenant B")
        customer_a = Customer(
            id=90,
            ownership_scope="TENANT",
            operational_organization_id=organization_a.id,
            company_name="Private Customer A",
            phone="09122222222",
        )
        customer_b = Customer(
            id=91,
            ownership_scope="TENANT",
            operational_organization_id=organization_b.id,
            company_name="Private Customer B",
            phone="09123333333",
        )
        db.session.add_all([expert, organization_a, organization_b])
        db.session.flush()
        db.session.add_all([customer_a, customer_b])
        db.session.flush()
        request_a = ShipmentRequest(
            id=10,
            ownership_scope="TENANT",
            operational_organization_id=organization_a.id,
            customer_id=customer_a.id,
            tracking_code=CAPABILITY_A,
            contact_phone="09124444444",
            customer_first_name="Private",
            customer_last_name="Customer",
            shipping_type="international",
            origin_country="China",
            origin_city_international="Shanghai",
            origin_address_international="Private origin address",
            dest_country="Iran",
            dest_city_international="Tehran",
            dest_address_international="Private destination address",
            transport_method="sea freight",
            international_transport_method="sea freight",
            transport_method_preference="customer_choice",
            cargo_description="Private cargo description",
            cargo_value=123456,
            special_instructions="Private handling instruction",
            assigned_to=expert.id,
            status="won",
            status_request_status="new",
        )
        request_b = ShipmentRequest(
            id=20,
            ownership_scope="TENANT",
            operational_organization_id=organization_b.id,
            customer_id=customer_b.id,
            tracking_code=CAPABILITY_B,
            contact_phone="09125555555",
            shipping_type="domestic",
            status="in_progress",
            status_request_status="new",
        )
        legacy_request = ShipmentRequest(
            id=30,
            ownership_scope="TENANT",
            operational_organization_id=organization_a.id,
            tracking_code="SR000030",
            contact_phone="09126666666",
            status="new",
            status_request_status="new",
        )
        db.session.add_all([request_a, request_b, legacy_request])
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request_a.id,
            amount=987654321,
            currency="EUR",
            note="Private quote note",
            customer_response="discussion",
            customer_response_message="Private quote discussion",
            created_by_expert_id=expert.id,
            operational_organization_id=organization_a.id,
        )
        document = CaseDocumentFile(
            operational_organization_id=organization_a.id,
            owner_type="REQUEST",
            shipment_request_id=request_a.id,
            is_miscellaneous=True,
            custom_title="Private document title",
            original_filename="private-document.pdf",
            safe_download_filename="private-document.pdf",
            storage_key="private/tenant-a/request-10/document.pdf",
            canonical_extension="pdf",
            detected_mime_type="application/pdf",
            file_size_bytes=123,
            sha256_hash="a" * 64,
            uploaded_by=expert.id,
        )
        shipment_a = OperationalShipment(
            id=100,
            organization_id=organization_a.id,
            source_type="direct",
            customer_id=customer_a.id,
            created_by_user_id=expert.id,
            primary_responsible_expert_id=expert.id,
        )
        shipment_b = OperationalShipment(
            id=200,
            organization_id=organization_b.id,
            source_type="direct",
            customer_id=customer_b.id,
            created_by_user_id=expert.id,
            primary_responsible_expert_id=expert.id,
        )
        db.session.add_all([quote, document, shipment_a, shipment_b])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def _assert_not_found(response):
    assert response.status_code == 404
    assert response.get_json() == NOT_FOUND
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_valid_capability_resolves_only_its_exact_public_safe_projection(public_tracking_app):
    client = public_tracking_app.test_client()
    response = client.get(f"/api/public/track/{CAPABILITY_A}?request_id=20&tenant_id=80")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    body = response.get_json()
    assert set(body) == PUBLIC_KEYS
    assert body["tracking_number"] == CAPABILITY_A
    assert body["status"] == "won"
    assert body["route"] == {
        "origin": {
            "province": None,
            "county": None,
            "city": None,
            "country": "China",
            "city_international": "Shanghai",
        },
        "destination": {
            "province": None,
            "county": None,
            "city": None,
            "country": "Iran",
            "city_international": "Tehran",
        },
    }
    serialized = json.dumps(body, ensure_ascii=False)
    for forbidden in (
        '"id"',
        '"organization_id"',
        "09124444444",
        "Private Customer",
        "Private Expert Name",
        "private-expert@example.test",
        "Private origin address",
        "Private destination address",
        "Private cargo description",
        "Private handling instruction",
        "Private quote note",
        "Private quote discussion",
        "Private document title",
        "private-document.pdf",
        "private/tenant-a",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize("identifier", ["1", "2", "3", "10", "20", "30", "100", "200", "9999"])
def test_numeric_request_shipment_and_enumeration_ids_never_resolve(public_tracking_app, identifier):
    _assert_not_found(public_tracking_app.test_client().get(f"/api/public/track/{identifier}"))


@pytest.mark.parametrize(
    "identifier",
    [
        "SR000030",
        "SR-ABC123",
        "not-a-capability",
        "00000000000000000000000001",
        "SR2-too-short",
        UNKNOWN_CAPABILITY,
    ],
)
def test_legacy_malformed_and_unknown_values_share_one_non_disclosing_failure(
    public_tracking_app, identifier
):
    _assert_not_found(public_tracking_app.test_client().get(f"/api/public/track/{identifier}"))


def test_each_tenant_capability_resolves_only_its_own_server_derived_resource(public_tracking_app):
    client = public_tracking_app.test_client()
    tenant_a = client.get(f"/api/public/track/{CAPABILITY_A}").get_json()
    tenant_b = client.get(f"/api/public/track/{CAPABILITY_B}").get_json()
    assert tenant_a["tracking_number"] == CAPABILITY_A
    assert tenant_b["tracking_number"] == CAPABILITY_B
    assert tenant_a["status"] == "won"
    assert tenant_b["status"] == "in_progress"
    assert CAPABILITY_B not in json.dumps(tenant_a)
    assert CAPABILITY_A not in json.dumps(tenant_b)


def test_generator_issues_only_versioned_128_bit_capabilities(public_tracking_app):
    with public_tracking_app.app_context():
        code = generate_tracking_code(ShipmentRequest(id=123456, contact_phone="09120000000"))
    assert PUBLIC_TRACKING_CAPABILITY_PATTERN.fullmatch(code)
    assert len(code) == 26
    assert "123456" not in code


def test_generator_has_no_predictable_collision_fallback(public_tracking_app, monkeypatch):
    monkeypatch.setattr("backend.services.shipment_service.secrets.token_urlsafe", lambda _size: "A" * 22)
    with public_tracking_app.app_context(), pytest.raises(
        RuntimeError, match="unable to allocate a unique public tracking capability"
    ):
        generate_tracking_code(ShipmentRequest(id=999999, contact_phone="09120000000"))


def test_public_create_payload_never_falls_back_to_numeric_identity(public_tracking_app):
    with public_tracking_app.app_context(), pytest.raises(
        RuntimeError, match="no public tracking capability"
    ):
        build_shipment_request_payload(
            ShipmentRequest(id=123456, contact_phone="09120000000")
        )
