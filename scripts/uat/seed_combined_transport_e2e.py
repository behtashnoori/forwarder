"""Seed the owned disposable Combined Transport browser qualification database."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import CustomerGamification, ExpertUser, Province, TransportMethod
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OrganizationHostname,
)
from backend.request_transport_catalog import (
    COMBINED_TRANSPORT_CODE,
    COMBINED_TRANSPORT_DESCRIPTION_FA,
    COMBINED_TRANSPORT_LABEL_FA,
)
from backend.services.user_service import hash_password


CUSTOMER_ID = 900021
USERNAME = "combined_transport_e2e_expert"


def one(model, **filters):
    return db.session.query(model).filter_by(**filters).one_or_none()


def main() -> None:
    password = os.environ["FORWARDER_E2E_PASSWORD"]
    app = create_app(skip_startup=True)
    with app.app_context():
        org = one(OperationalOrganization, name="[COMBINED-E2E] Organization")
        if org is None:
            org = OperationalOrganization(name="[COMBINED-E2E] Organization")
            db.session.add(org)
            db.session.flush()

        hostname = one(OrganizationHostname, hostname="127.0.0.1")
        if hostname is None:
            hostname = OrganizationHostname(
                organization_id=org.id,
                hostname="127.0.0.1",
                is_primary=True,
                is_active=True,
            )
            db.session.add(hostname)
        else:
            hostname.organization_id = org.id
            hostname.is_primary = True
            hostname.is_active = True

        expert = one(ExpertUser, username=USERNAME)
        if expert is None:
            expert = ExpertUser(username=USERNAME, full_name="کارشناس حمل ترکیبی")
            db.session.add(expert)
        expert.password_hash = hash_password(password)
        expert.role = "expert"
        expert.authority = "EXPERT"
        expert.is_active = True
        expert.can_handle_domestic = True
        expert.can_handle_international = True
        db.session.flush()

        membership = one(
            OperationalMembership,
            organization_id=org.id,
            user_id=expert.id,
        )
        if membership is None:
            membership = OperationalMembership(
                organization_id=org.id,
                user_id=expert.id,
                permissions=["operational_shipment.read"],
            )
            db.session.add(membership)
        membership.is_active = True
        membership.permissions = ["operational_shipment.read"]

        for code, name in (("CTE", "تهران"), ("CIS", "اصفهان")):
            if one(Province, code=code) is None:
                db.session.add(Province(code=code, name_fa=name))

        customer = db.session.get(CustomerGamification, CUSTOMER_ID)
        if customer is None:
            customer = CustomerGamification(
                id=CUSTOMER_ID,
                email="combined-transport-browser@example.test",
                phone="09120000921",
                is_email_verified=True,
                total_requests=0,
                completed_requests=0,
                loyalty_points=0,
                customer_level="bronze",
            )
            db.session.add(customer)

        combined = one(TransportMethod, name=COMBINED_TRANSPORT_CODE)
        if combined is None:
            combined = TransportMethod(name=COMBINED_TRANSPORT_CODE)
            db.session.add(combined)
        combined.name_fa = COMBINED_TRANSPORT_LABEL_FA
        combined.description = COMBINED_TRANSPORT_DESCRIPTION_FA
        combined.is_active = True

        db.session.commit()
        print(json.dumps({
            "customer_id": customer.id,
            "expert_id": expert.id,
            "organization_id": org.id,
            "username": USERNAME,
        }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
