"""Seed the owned disposable MT-3 PostgreSQL browser database."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    CaseDocumentFile,
    Customer,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
    ShipmentTracking,
    ShipmentTransportUnit,
    ShipmentTransportUnitUpdate,
    TransportMethod,
)
from backend.operational_models import OperationalOrganization, OperationalShipment


CAPABILITY_A = "SR2-AAAAAAAAAAAAAAAAAAAAAA"
CAPABILITY_B = "SR2-BBBBBBBBBBBBBBBBBBBBBB"


def _assert_owned_database() -> None:
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("MT-3 browser seed requires APP_ENV=uat")
    parsed = make_url(os.environ["DATABASE_URL"])
    if parsed.host != "127.0.0.1" or not (parsed.database or "").startswith("forwarder_mt3_"):
        raise RuntimeError("MT-3 browser seed is restricted to its owned loopback database")


def main() -> None:
    _assert_owned_database()
    manifest_path = Path(os.environ["MT3_E2E_FIXTURE_PATH"]).resolve()
    app = create_app(skip_startup=True)
    with app.app_context():
        organization_a = OperationalOrganization(name="[MT3-E2E] Tenant A")
        organization_b = OperationalOrganization(name="[MT3-E2E] Tenant B")
        expert = ExpertUser(
            username="mt3-e2e-expert",
            password_hash="not-used",
            full_name="Private Browser Expert",
            email="private-browser-expert@example.invalid",
            phone="09121111111",
            role="expert",
        )
        combined_transport = TransportMethod(
            name="Combined Transport",
            name_fa="حمل ترکیبی",
            description="MT-3 governed Request intent fixture",
            is_active=True,
        )
        db.session.add_all([organization_a, organization_b, expert, combined_transport])
        db.session.flush()
        customer_a = Customer(
            ownership_scope="TENANT",
            operational_organization_id=organization_a.id,
            company_name="Private Browser Customer A",
            phone="09122222222",
        )
        customer_b = Customer(
            ownership_scope="TENANT",
            operational_organization_id=organization_b.id,
            company_name="Private Browser Customer B",
            phone="09123333333",
        )
        db.session.add_all([customer_a, customer_b])
        db.session.flush()

        created = datetime(2026, 9, 20, 9, 30, 0)
        request_a = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=organization_a.id,
            customer_id=customer_a.id,
            tracking_code=CAPABILITY_A,
            contact_phone="09124444444",
            customer_first_name="Private",
            customer_last_name="Browser A",
            shipping_type="international",
            origin_country="China",
            origin_city_international="Shanghai",
            origin_address_international="Private browser origin address",
            dest_country="Iran",
            dest_city_international="Tehran",
            dest_address_international="Private browser destination address",
            transport_method="road",
            international_transport_method="Combined Transport",
            transport_method_preference="customer_choice",
            cargo_description="Private browser cargo",
            cargo_value=9_876_543,
            special_instructions="Private browser instructions",
            assigned_to=expert.id,
            status="won",
            status_request_status="new",
            created_at=created,
            ready_at=created,
        )
        request_b = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=organization_b.id,
            customer_id=customer_b.id,
            tracking_code=CAPABILITY_B,
            contact_phone="09125555555",
            shipping_type="domestic",
            assigned_to=expert.id,
            status="in_progress",
            status_request_status="new",
            created_at=created + timedelta(minutes=1),
            ready_at=created + timedelta(minutes=1),
        )
        db.session.add_all([request_a, request_b])
        db.session.flush()

        tracking = ShipmentTracking(
            operational_organization_id=organization_a.id,
            shipment_request_id=request_a.id,
            is_enabled=True,
            enabled_at=created + timedelta(hours=1),
            enabled_by_user_id=expert.id,
        )
        db.session.add(tracking)
        db.session.flush()
        unit = ShipmentTransportUnit(
            operational_organization_id=organization_a.id,
            ownership_scope="TENANT",
            tracking_id=tracking.id,
            unit_code="MT3-CNTR-001",
            unit_type="container",
            display_name="کانتینر آزمون رهگیری",
            vehicle_reference="PUBLIC-UNIT-001",
            created_by_user_id=expert.id,
        )
        db.session.add(unit)
        db.session.flush()
        db.session.add_all(
            [
                ShipmentTransportUnitUpdate(
                    operational_organization_id=organization_a.id,
                    ownership_scope="TENANT",
                    unit_id=unit.id,
                    status="departed",
                    location="Shanghai",
                    location_text="Shanghai",
                    customer_message="حرکت از مبدا",
                    internal_note="Private browser internal tracking note",
                    is_customer_visible=True,
                    occurred_at=created + timedelta(hours=2),
                    created_by_user_id=expert.id,
                ),
                ShipmentTransportUnitUpdate(
                    operational_organization_id=organization_a.id,
                    ownership_scope="TENANT",
                    unit_id=unit.id,
                    status="in_transit",
                    location="Bandar Abbas",
                    location_text="Bandar Abbas",
                    customer_message="در مسیر مقصد",
                    internal_note="Private later internal note",
                    is_customer_visible=True,
                    occurred_at=created + timedelta(days=1),
                    created_by_user_id=expert.id,
                ),
            ]
        )
        db.session.add(
            ExpertQuote(
                shipment_request_id=request_a.id,
                amount=123_456_789,
                currency="EUR",
                note="Private browser quote note",
                customer_response="discussion",
                customer_response_message="Private browser quote discussion",
                created_by_expert_id=expert.id,
                operational_organization_id=organization_a.id,
            )
        )
        db.session.add(
            CaseDocumentFile(
                operational_organization_id=organization_a.id,
                owner_type="REQUEST",
                shipment_request_id=request_a.id,
                is_miscellaneous=True,
                custom_title="Private browser document",
                original_filename="private-browser-document.pdf",
                safe_download_filename="private-browser-document.pdf",
                storage_key="private/mt3/browser-document.pdf",
                canonical_extension="pdf",
                detected_mime_type="application/pdf",
                file_size_bytes=123,
                sha256_hash="b" * 64,
                uploaded_by=expert.id,
            )
        )
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

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "capability_a": CAPABILITY_A,
                    "capability_b": CAPABILITY_B,
                    "request_a_id": request_a.id,
                    "request_b_id": request_b.id,
                    "shipment_a_id": shipment_a.id,
                    "shipment_b_id": shipment_b.id,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print("MT3_BROWSER_FIXTURE_SEEDED=YES")


if __name__ == "__main__":
    main()
