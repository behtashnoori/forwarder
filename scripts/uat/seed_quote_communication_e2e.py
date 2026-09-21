"""Seed the owned disposable Simple Quote Communication browser database."""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    CustomerGamification,
    ExpertQuote,
    ExpertUser,
    RequestCargoItem,
    ShipmentRequest,
)
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OrganizationHostname,
)
from backend.request_transport_catalog import COMBINED_TRANSPORT_CODE
from backend.services.user_service import hash_password


USERNAME = "quote_communication_e2e_expert"
CUSTOMER_IDS = {"approve": 910001, "discussion": 910002, "reject": 910003}
REQUEST_PUBLIC_IDS = {
    "approve": "a1000000-0000-4100-8100-000000000001",
    "discussion": "b2000000-0000-4200-8200-000000000002",
    "reject": "c3000000-0000-4300-8300-000000000003",
}
QUOTE_PUBLIC_IDS = {
    "approve": "a1000000-0000-4100-8100-000000000011",
    "discussion": "b2000000-0000-4200-8200-000000000012",
    "reject": "c3000000-0000-4300-8300-000000000013",
}


def _assert_owned_database() -> None:
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("Quote communication E2E seed requires APP_ENV=uat")
    parsed = make_url(os.environ["DATABASE_URL"])
    if parsed.host != "127.0.0.1" or parsed.database != "forwarder_integrated_cert_quote_communication_e2e":
        raise RuntimeError("Quote communication E2E seed is restricted to its owned loopback database")


def main() -> None:
    _assert_owned_database()
    password = os.environ["FORWARDER_E2E_PASSWORD"]
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).resolve()
    app = create_app(skip_startup=True)
    with app.app_context():
        organization = OperationalOrganization(
            public_id=str(uuid4()),
            name="[QUOTE-COMM-E2E] Organization",
            is_active=True,
        )
        expert = ExpertUser(
            username=USERNAME,
            password_hash=hash_password(password),
            full_name="کارشناس ارتباط پیشنهاد",
            role="expert",
            authority="EXPERT",
            is_active=True,
            can_handle_domestic=True,
            can_handle_international=True,
        )
        db.session.add_all([organization, expert])
        db.session.flush()
        db.session.add_all([
            OrganizationHostname(
                organization_id=organization.id,
                hostname="127.0.0.1",
                is_primary=True,
                is_active=True,
            ),
            OperationalMembership(
                organization_id=organization.id,
                user_id=expert.id,
                is_active=True,
                permissions=[
                    "request.read",
                    "request.quote",
                    "operational_shipment.read",
                ],
            ),
        ])

        fixtures: dict[str, dict[str, object]] = {}
        now = datetime.utcnow()
        for index, (journey, customer_id) in enumerate(CUSTOMER_IDS.items(), start=1):
            customer = CustomerGamification(
                id=customer_id,
                email=f"quote-{journey}@example.invalid",
                phone=f"09125550{index:03d}",
                first_name="مشتری",
                last_name={
                    "approve": "تأیید",
                    "discussion": "گفتگو",
                    "reject": "رد",
                }[journey],
                is_email_verified=True,
                total_requests=1,
                completed_requests=0,
                loyalty_points=0,
                customer_level="bronze",
            )
            request_row = ShipmentRequest(
                public_id=REQUEST_PUBLIC_IDS[journey],
                operational_organization_id=organization.id,
                ownership_scope="TENANT",
                tracking_code=f"QC-E2E-{journey.upper()}",
                shipping_type="domestic",
                contact_phone=customer.phone,
                customer_first_name=customer.first_name,
                customer_last_name=customer.last_name,
                domestic_transport_method=(
                    COMBINED_TRANSPORT_CODE if journey == "discussion" else "road"
                ),
                status_request_status="new",
                status="waiting_for_customer",
                assigned_to=expert.id,
                gamification_customer_id=customer.id,
                created_at=now + timedelta(seconds=index),
                ready_at=now + timedelta(seconds=index),
            )
            db.session.add_all([customer, request_row])
            db.session.flush()
            if journey == "discussion":
                db.session.add_all([
                    RequestCargoItem(
                        shipment_request_id=request_row.id,
                        position=1,
                        description="کالای اول برای حمل ترکیبی",
                    ),
                    RequestCargoItem(
                        shipment_request_id=request_row.id,
                        position=2,
                        description="کالای دوم برای حمل ترکیبی",
                    ),
                ])
            quote = ExpertQuote(
                public_id=QUOTE_PUBLIC_IDS[journey],
                shipment_request_id=request_row.id,
                operational_organization_id=organization.id,
                amount=1_250_000 + (index * 10_000),
                currency="EUR",
                note=f"پیشنهاد رسمی {journey}",
                valid_until=date.today() + timedelta(days=30),
                created_by_expert_id=expert.id,
                created_at=now + timedelta(seconds=10 + index),
            )
            db.session.add(quote)
            db.session.flush()
            fixtures[journey] = {
                "customer_id": customer.id,
                "request_id": request_row.id,
                "request_public_id": request_row.public_id,
                "tracking_code": request_row.tracking_code,
                "quote_public_id": quote.public_id,
                "initial_amount": quote.amount,
                "initial_currency": quote.currency,
            }

        db.session.commit()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "username": USERNAME,
                    "expert_id": expert.id,
                    "organization_id": organization.id,
                    "journeys": fixtures,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print(json.dumps({"seeded": True, "journeys": sorted(fixtures)}, sort_keys=True))


if __name__ == "__main__":
    main()
