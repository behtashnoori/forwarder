"""Provision deterministic Slice 6 personas after the repository-native UAT seed."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bcrypt

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_cli import PHASE1B_ALL_PERMISSIONS, PHASE1B_NOW, seed_phase1b_uat
from backend.operational_models import OperationalMembership, OperationalOrganization


def main() -> None:
    app = create_app(skip_startup=True)
    with app.app_context():
        password = os.environ["FORWARDER_UAT_PASSWORD"]
        seed_phase1b_uat(app, password)
        organization = OperationalOrganization.query.filter_by(name="[PHASE1B-UAT] Organization A").one()
        base_read = ["operational_shipment.read", "work_item.read", "route_plan.read", "checkpoint.read", "route_exception.read", "operational_execution.read", "document_readiness.read"]
        personas = {
            "direct_only": [*base_read, "operational_shipment.create_direct"],
            "quote_only": [*base_read, "operational_shipment.create_from_quote"],
            "legacy_quote": [*base_read, "operational_shipment.create"],
            "both": [*base_read, "operational_shipment.create_direct", "operational_shipment.create_from_quote"],
        }
        for suffix, permissions in personas.items():
            user = ExpertUser(username=f"phase1b_uat_{suffix}", password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), full_name=f"[SLICE6-UAT] {suffix}", role="expert", is_active=True)
            db.session.add(user)
            db.session.flush()
            db.session.add(OperationalMembership(organization_id=organization.id, user_id=user.id, permissions=permissions))
        admin = ExpertUser.query.filter_by(username="phase1b_uat_admin").one()
        admin.role = "admin"
        membership = OperationalMembership.query.filter_by(user_id=admin.id).one()
        membership.permissions = sorted(set(PHASE1B_ALL_PERMISSIONS) | {"operational_shipment.create_direct", "operational_shipment.create_from_quote"})
        for sequence in range(1, 9):
            phone = f"090000006{sequence:02d}"
            customer = Customer(first_name="Governed", last_name=f"Slice 6 Customer {sequence}", phone=phone, status="active")
            db.session.add(customer)
            db.session.flush()
            request = ShipmentRequest(contact_phone=phone, customer_first_name="Governed", customer_last_name=f"Slice 6 Customer {sequence}", status="waiting_for_customer", status_request_status="new", assigned_to=admin.id, customer_id=customer.id)
            db.session.add(request)
            db.session.flush()
            db.session.add(ExpertQuote(shipment_request_id=request.id, amount=1910 + sequence, currency="USD", created_by_expert_id=admin.id, created_at=PHASE1B_NOW, customer_response="accepted", responded_at=PHASE1B_NOW, operational_organization_id=organization.id))
        db.session.commit()


if __name__ == "__main__":
    main()
