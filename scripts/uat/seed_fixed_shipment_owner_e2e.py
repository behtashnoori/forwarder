"""Seed the owned ADR-047 fixed Shipment owner browser database."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    Country,
    Customer,
    CustomerGamification,
    ExpertUser,
    InternationalCity,
    Province,
    ShipmentRequest,
)
from backend.operational_models import (
    ExceptionReason,
    OperationalMembership,
    OperationalOrganization,
    OrganizationHostname,
)
from backend.services.user_service import hash_password


DATABASE_NAME = "forwarder_integrated_cert_fixed_shipment_owner_e2e"
REQUEST_PUBLIC_ID = "47000000-0000-4700-8700-000000000001"
CUSTOMER_ID = 947001
USERNAMES = {
    "e1": "fixed_owner_e2e_e1",
    "e2": "fixed_owner_e2e_e2",
    "admin": "fixed_owner_e2e_admin",
}


def _assert_owned_database() -> None:
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("ADR-047 E2E seed requires APP_ENV=uat")
    parsed = make_url(os.environ["DATABASE_URL"])
    if parsed.host != "127.0.0.1" or parsed.database != DATABASE_NAME:
        raise RuntimeError("ADR-047 E2E seed is restricted to its owned loopback database")


def _user(key: str, password: str, *, authority: str, role: str) -> ExpertUser:
    return ExpertUser(
        username=USERNAMES[key],
        password_hash=hash_password(password),
        full_name={
            "e1": "کارشناس مالک ثابت یک",
            "e2": "کارشناس درخواست دو",
            "admin": "مدیر ناظر سازمان",
        }[key],
        role=role,
        authority=authority,
        is_active=True,
        can_handle_domestic=True,
        can_handle_international=True,
    )


def main() -> None:
    _assert_owned_database()
    password = os.environ["FORWARDER_E2E_PASSWORD"]
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).resolve()
    app = create_app(skip_startup=True)
    with app.app_context():
        organization = OperationalOrganization(
            public_id=str(uuid4()),
            name="[ADR-047-E2E] Organization",
            is_active=True,
        )
        e1 = _user("e1", password, authority="EXPERT", role="expert")
        e2 = _user("e2", password, authority="EXPERT", role="expert")
        admin = _user(
            "admin", password, authority="ORGANIZATION_ADMIN", role="admin"
        )
        db.session.add_all([organization, e1, e2, admin])
        db.session.flush()

        db.session.add(OrganizationHostname(
            organization_id=organization.id,
            hostname="127.0.0.1",
            is_primary=True,
            is_active=True,
        ))
        db.session.add_all([
            OperationalMembership(
                organization_id=organization.id,
                user_id=e1.id,
                is_active=True,
                permissions=[
                    "request.read",
                    "request.quote",
                    "operational_shipment.read",
                    "operational_shipment.create",
                    "operational_shipment.create_from_quote",
                    "operational_execution.manage",
                ],
            ),
            OperationalMembership(
                organization_id=organization.id,
                user_id=e2.id,
                is_active=True,
                permissions=["request.read", "operational_shipment.read"],
            ),
            OperationalMembership(
                organization_id=organization.id,
                user_id=admin.id,
                is_active=True,
                permissions=[
                    "request.read",
                    "operational_shipment.read",
                    "operational_shipment.create",
                ],
            ),
        ])

        crm_customer = Customer(
            first_name="مشتری",
            last_name="مالک ثابت",
            phone="09124700001",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
        )
        portal_customer = CustomerGamification(
            id=CUSTOMER_ID,
            email="fixed-owner-e2e@example.invalid",
            phone="09124700001",
            first_name="مشتری",
            last_name="مالک ثابت",
            is_email_verified=True,
            total_requests=1,
            completed_requests=0,
            loyalty_points=0,
            customer_level="bronze",
        )
        db.session.add_all([crm_customer, portal_customer])
        db.session.flush()

        db.session.add(ExceptionReason(
            organization_id=organization.id,
            immutable_code="ADR047_E2E_EXCEPTION",
            fa_name="استثنای گواهی مالک ثابت",
            en_name="Fixed owner qualification exception",
            created_by_user_id=e1.id,
            updated_by_user_id=e1.id,
        ))

        iran = db.session.scalar(db.select(Country).where(Country.code == "IR"))
        if iran is None:
            iran = Country(code="IR", name_en="Iran", name_fa="ایران", is_active=True)
            db.session.add(iran)
            db.session.flush()
        else:
            iran.is_active = True

        origin = Province(name_fa="مبدأ مالک ثابت", code="A47O")
        destination_province = Province(name_fa="مقصد مالک ثابت", code="A47D")
        db.session.add_all([origin, destination_province])
        db.session.flush()
        destination = InternationalCity(
            country_id=iran.id,
            name_en="Fixed Owner Destination",
            name_fa="مقصد مالک ثابت",
            un_locode="IRF47",
            is_active=True,
        )
        db.session.add(destination)
        db.session.flush()

        now = datetime.now(timezone.utc)
        request_row = ShipmentRequest(
            public_id=REQUEST_PUBLIC_ID,
            operational_organization_id=organization.id,
            ownership_scope="TENANT",
            tracking_code="ADR047-E2E-REQUEST",
            shipping_type="domestic",
            domestic_transport_method="road",
            contact_phone=portal_customer.phone,
            customer_first_name=portal_customer.first_name,
            customer_last_name=portal_customer.last_name,
            customer_id=crm_customer.id,
            gamification_customer_id=portal_customer.id,
            status_request_status="new",
            status="assigned",
            assigned_to=e1.id,
            created_at=now,
            ready_at=now,
        )
        db.session.add(request_row)
        db.session.commit()

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "usernames": USERNAMES,
                    "organization_id": organization.id,
                    "e1_id": e1.id,
                    "e2_id": e2.id,
                    "admin_id": admin.id,
                    "customer_id": portal_customer.id,
                    "request_id": request_row.id,
                    "request_public_id": request_row.public_id,
                    "tracking_code": request_row.tracking_code,
                    "origin_province_id": origin.id,
                    "destination_identity": f"international_city:{destination.id}",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print(json.dumps({"seeded": True, "request": request_row.public_id}))


if __name__ == "__main__":
    main()
