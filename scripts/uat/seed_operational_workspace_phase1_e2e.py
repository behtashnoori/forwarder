"""Seed the owned Operational Workspace Phase 1 browser database."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    Customer,
    CustomerGamification,
    ExpertQuote,
    ExpertUser,
    Province,
    ShipmentRequest,
    ShipmentTracking,
    ShipmentTransportUnit,
    ShipmentTransportUnitUpdate,
    TransportMethod,
)
from backend.operational_models import (
    Milestone,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    OperationalWorkItem,
    OrganizationHostname,
)
from backend.security import security
from backend.services import operational_service
from backend.services.user_service import hash_password as hash_expert_password


PUBLIC_CAPABILITY = "SR2-AAAAAAAAAAAAAAAAAAAAAA"
USERNAMES = {
    "owner": "workspace_phase1_owner",
    "peer": "workspace_phase1_peer",
    "empty": "workspace_phase1_empty",
    "foreign": "workspace_phase1_foreign",
    "admin": "workspace_phase1_admin",
}


def _assert_owned_database() -> None:
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("Workspace E2E seed requires APP_ENV=uat")
    parsed = make_url(os.environ["DATABASE_URL"])
    database = parsed.database or ""
    if parsed.host != "127.0.0.1" or not database.startswith(
        ("forwarder_workspace_phase1_", "forwarder_workspace_phase2_")
    ):
        raise RuntimeError(
            "Workspace E2E seed is restricted to its owned loopback database"
        )


def _expert(key: str, password: str, *, authority: str = "EXPERT", role: str = "expert"):
    return ExpertUser(
        username=USERNAMES[key],
        password_hash=hash_expert_password(password),
        full_name={
            "owner": "کارشناس مالک ثابت",
            "peer": "کارشناس ارجاع جدید",
            "empty": "کارشناس بدون محموله",
            "foreign": "کارشناس سازمان دیگر",
            "admin": "مدیر سازمان آزمایشی",
        }[key],
        role=role,
        authority=authority,
        is_active=True,
        can_handle_domestic=True,
        can_handle_international=True,
    )


def _permissions() -> list[str]:
    return [
        "request.read",
        "request.quote",
        "operational_shipment.read",
        "operational_shipment.create",
        "operational_shipment.create_direct",
        "operational_shipment.create_from_quote",
        "milestone_event.create",
        "milestone.verify",
        "milestone.correct",
        "work_item.read",
        "work_item.manage",
        "route_plan.read",
        "route_plan.create",
        "route_plan.activate",
        "route_plan.replan",
        "route_leg.manage",
        "checkpoint.read",
        "checkpoint.report",
        "checkpoint.verify",
        "route_exception.read",
        "route_exception.manage",
        "document_readiness.read",
        "oip.read",
        "personal_dashboard.read",
    ]


def main() -> None:
    _assert_owned_database()
    expert_password = os.environ["FORWARDER_E2E_PASSWORD"]
    customer_password = os.environ["FORWARDER_E2E_CUSTOMER_PASSWORD"]
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).resolve()
    app = create_app(skip_startup=True)

    with app.app_context():
        org = OperationalOrganization(name="[Workspace Phase 1] Tenant A")
        foreign_org = OperationalOrganization(name="[Workspace Phase 1] Tenant B")
        owner = _expert("owner", expert_password)
        peer = _expert("peer", expert_password)
        empty = _expert("empty", expert_password)
        foreign = _expert("foreign", expert_password)
        admin = _expert(
            "admin", expert_password, authority="ORGANIZATION_ADMIN", role="admin"
        )
        combined_transport = TransportMethod(
            name="Combined Transport",
            name_fa="حمل ترکیبی",
            description="Workspace Phase 1 anonymous intake fixture",
            is_active=True,
        )
        db.session.add_all(
            [org, foreign_org, owner, peer, empty, foreign, admin, combined_transport]
        )
        db.session.flush()

        db.session.add(
            OrganizationHostname(
                organization_id=org.id,
                hostname="127.0.0.1",
                is_primary=True,
                is_active=True,
            )
        )
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id,
                    user_id=user.id,
                    permissions=_permissions(),
                )
                for user in (owner, peer, empty, admin)
            ]
            + [
                OperationalMembership(
                    organization_id=foreign_org.id,
                    user_id=foreign.id,
                    permissions=_permissions(),
                )
            ]
        )

        origin = Province(name_fa="تهران", code="OW-P1-THR")
        destination = Province(name_fa="تبریز", code="OW-P1-TBZ")
        foreign_origin = Province(name_fa="شیراز", code="OW-P1-SHZ")
        db.session.add_all([origin, destination, foreign_origin])
        db.session.flush()

        crm_customer = Customer(
            company_name="مشتری عملیاتی آزمایشی",
            phone="09120000001",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        foreign_customer = Customer(
            company_name="مشتری سازمان دیگر",
            phone="09120000002",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=foreign_org.id,
        )
        portal_customer = CustomerGamification(
            email="workspace-phase1-customer@example.invalid",
            phone="09120000003",
            first_name="مشتری",
            last_name="آزمایشی",
            password_hash=security.hash_password(customer_password),
            account_status="ACTIVE",
            operational_organization_id=org.id,
            is_email_verified=True,
            total_requests=1,
            completed_requests=0,
            loyalty_points=0,
            customer_level="bronze",
        )
        db.session.add_all([crm_customer, foreign_customer, portal_customer])
        db.session.flush()

        now = datetime.now(timezone.utc)
        source_request = ShipmentRequest(
            operational_organization_id=org.id,
            ownership_scope="TENANT",
            tracking_code="OW-OPERATIONAL-001",
            shipping_type="domestic",
            domestic_transport_method="Road Transport",
            transport_method="road",
            contact_phone=crm_customer.phone,
            customer_first_name="مشتری",
            customer_last_name="عملیاتی",
            customer_id=crm_customer.id,
            status_request_status="new",
            status="waiting_for_customer",
            assigned_to=owner.id,
            created_at=now - timedelta(days=2),
            ready_at=now - timedelta(days=2),
        )
        db.session.add(source_request)
        db.session.flush()
        accepted_quote = ExpertQuote(
            shipment_request_id=source_request.id,
            amount=4_700_000,
            currency="IRR",
            note="پیشنهاد پذیرفته‌شده محموله عملیاتی",
            created_by_expert_id=owner.id,
            created_at=now - timedelta(days=1),
            customer_response="accepted",
            response_version=1,
            responded_by_customer_id=portal_customer.id,
            responded_at=now - timedelta(hours=20),
            operational_organization_id=org.id,
        )
        db.session.add(accepted_quote)
        db.session.commit()

        route_payload = {
            "accepted_quote_id": accepted_quote.id,
            "planned_departure": (now - timedelta(hours=3)).isoformat(),
            "planned_arrival": (now + timedelta(hours=8)).isoformat(),
            "origin": {"source_type": "province", "source_id": origin.id},
            "destination": {
                "source_type": "province",
                "source_id": destination.id,
            },
            "transport_mode": "road",
        }
        active_shipment, _ = operational_service.create_from_accepted_quote(
            route_payload,
            {"id": owner.id, "role": owner.role, "authority": owner.authority},
            "workspace-phase1-active",
        )
        departure = Milestone.query.filter_by(
            operational_shipment_id=active_shipment.id,
            milestone_type="departure",
        ).one()
        operational_service.record_event(
            active_shipment.public_id,
            departure.id,
            {"occurred_at": (now - timedelta(hours=2)).isoformat()},
            {"id": owner.id, "role": owner.role, "authority": owner.authority},
            "workspace-phase1-departure",
        )
        arrival = Milestone.query.filter_by(
            operational_shipment_id=active_shipment.id,
            milestone_type="arrival",
        ).one()
        db.session.add(
            OperationalWorkItem(
                organization_id=org.id,
                operational_shipment_id=active_shipment.id,
                milestone_id=arrival.id,
                work_type="OVERDUE_MILESTONE",
                severity="warning",
                detected_at=now - timedelta(minutes=30),
                due_at=now - timedelta(minutes=15),
                reason="پیگیری آزمایشی موجود برای گواه محصول",
            )
        )

        terminal_payload = {
            "source_type": "direct",
            "customer_id": crm_customer.id,
            "project_public_id": None,
            "route": {
                "planned_departure": (now - timedelta(days=4)).isoformat(),
                "planned_arrival": (now - timedelta(days=3)).isoformat(),
                "origin": {"source_type": "province", "source_id": origin.id},
                "destination": {
                    "source_type": "province",
                    "source_id": destination.id,
                },
                "transport_mode": "road",
            },
        }
        terminal_shipment, _ = operational_service.create_direct(
            terminal_payload,
            {"id": owner.id, "role": owner.role, "authority": owner.authority},
            "workspace-phase1-terminal",
        )
        terminal_shipment.lifecycle_status = "completed"

        foreign_payload = {
            "source_type": "direct",
            "customer_id": foreign_customer.id,
            "project_public_id": None,
            "route": {
                "planned_departure": (now + timedelta(hours=1)).isoformat(),
                "planned_arrival": (now + timedelta(hours=6)).isoformat(),
                "origin": {
                    "source_type": "province",
                    "source_id": foreign_origin.id,
                },
                "destination": {
                    "source_type": "province",
                    "source_id": destination.id,
                },
                "transport_mode": "road",
            },
        }
        foreign_shipment, _ = operational_service.create_direct(
            foreign_payload,
            {"id": foreign.id, "role": foreign.role, "authority": foreign.authority},
            "workspace-phase1-foreign",
        )

        portal_request = ShipmentRequest(
            operational_organization_id=org.id,
            ownership_scope="TENANT",
            tracking_code=PUBLIC_CAPABILITY,
            shipping_type="international",
            international_transport_method="Combined Transport",
            transport_method="road",
            transport_method_preference="customer_choice",
            origin_country="China",
            origin_city_international="Shanghai",
            origin_address_international="Private origin address",
            dest_country="Iran",
            dest_city_international="Tehran",
            dest_address_international="Private destination address",
            contact_phone=portal_customer.phone,
            customer_first_name=portal_customer.first_name,
            customer_last_name=portal_customer.last_name,
            customer_id=crm_customer.id,
            gamification_customer_id=portal_customer.id,
            status_request_status="new",
            status="in_progress",
            assigned_to=owner.id,
            created_at=now - timedelta(days=1),
            ready_at=now - timedelta(days=1),
        )
        db.session.add(portal_request)
        db.session.flush()
        db.session.add_all(
            [
                ExpertQuote(
                    shipment_request_id=portal_request.id,
                    amount=1_100_000,
                    currency="IRR",
                    note="پیشنهاد پیشین",
                    created_by_expert_id=owner.id,
                    created_at=now - timedelta(hours=6),
                    customer_response="discussion",
                    customer_response_message="پیام سابق مشتری",
                    response_version=1,
                    responded_by_customer_id=portal_customer.id,
                    responded_at=now - timedelta(hours=5),
                    operational_organization_id=org.id,
                ),
                ExpertQuote(
                    shipment_request_id=portal_request.id,
                    amount=1_250_000,
                    currency="IRR",
                    note="پیشنهاد جاری برای پاسخ مرورگری",
                    created_by_expert_id=owner.id,
                    created_at=now - timedelta(hours=2),
                    response_version=0,
                    operational_organization_id=org.id,
                ),
            ]
        )
        tracking = ShipmentTracking(
            operational_organization_id=org.id,
            shipment_request_id=portal_request.id,
            is_enabled=True,
            enabled_at=now - timedelta(hours=20),
            enabled_by_user_id=owner.id,
        )
        db.session.add(tracking)
        db.session.flush()
        unit = ShipmentTransportUnit(
            operational_organization_id=org.id,
            ownership_scope="TENANT",
            tracking_id=tracking.id,
            unit_code="OW-PHASE1-UNIT",
            unit_type="container",
            display_name="کانتینر گواه Workspace",
            vehicle_reference="PUBLIC-WORKSPACE-UNIT",
            created_by_user_id=owner.id,
        )
        db.session.add(unit)
        db.session.flush()
        db.session.add(
            ShipmentTransportUnitUpdate(
                operational_organization_id=org.id,
                ownership_scope="TENANT",
                unit_id=unit.id,
                status="in_transit",
                location="Bandar Abbas",
                location_text="Bandar Abbas",
                customer_message="در مسیر مقصد",
                internal_note="Private workspace tracking note",
                is_customer_visible=True,
                occurred_at=now - timedelta(hours=4),
                created_by_user_id=owner.id,
            )
        )
        db.session.commit()

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "usernames": USERNAMES,
                    "owner_id": owner.id,
                    "peer_id": peer.id,
                    "request_id": source_request.id,
                    "active_shipment_public_id": active_shipment.public_id,
                    "terminal_shipment_public_id": terminal_shipment.public_id,
                    "foreign_shipment_public_id": foreign_shipment.public_id,
                    "portal_customer_email": portal_customer.email,
                    "portal_request_public_id": portal_request.public_id,
                    "portal_request_id": portal_request.id,
                    "public_capability": PUBLIC_CAPABILITY,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print("OPERATIONAL_WORKSPACE_PHASE1_FIXTURE_SEEDED=YES")


if __name__ == "__main__":
    main()
