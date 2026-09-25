"""Synthetic P3-06 document audience on the P3-05 route/Cargo graph."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import CustomerGamification
from backend.operational_models import OperationalShipment
from backend.security import security
from scripts.uat.seed_phase3_cargo_allocation_e2e import main as seed_cargo


def main() -> None:
    seed_cargo()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    password = os.environ["FORWARDER_E2E_PASSWORD"]
    app = create_app(skip_startup=True)
    with app.app_context():
        shipment = OperationalShipment.query.filter_by(public_id=fixture["p304_shipment"]).one()
        accounts = []
        for name, suffix in (("الف", "a"), ("ب", "b")):
            account = CustomerGamification(
                email=f"p306-{suffix}@example.test", phone="09120000001" if suffix == "a" else "09120000002",
                first_name="مشتری", last_name=name, password_hash=security.hash_password(password),
                operational_organization_id=shipment.organization_id, is_email_verified=True,
            )
            db.session.add(account)
            accounts.append(account)
        db.session.commit()
        fixture.update(p306_account_a=accounts[0].public_id, p306_account_b=accounts[1].public_id,
                       p306_email_a=accounts[0].email, p306_email_b=accounts[1].email,
                       p306_crm_customer=shipment.customer_id)
    path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
