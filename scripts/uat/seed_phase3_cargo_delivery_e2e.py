"""Owned P3-08 two-Customer browser graph extends its P3-05 dependency."""
import json
import os
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import create_app
from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem
from backend.models import Customer
from backend.operational_models import OperationalShipment
from scripts.uat.seed_phase3_cargo_allocation_e2e import main as seed_cargo


def main():
    seed_cargo()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        shipment = OperationalShipment.query.filter_by(public_id=fixture["p304_shipment"]).one()
        a = ShipmentCargoItem.query.filter_by(public_id=fixture["p305_cargo"]).one()
        a.actual_quantity = Decimal("100")
        owner = Customer(company_name="مشتری دوم آزمایشی", ownership_scope="TENANT", operational_organization_id=shipment.organization_id, status="active")
        db.session.add(owner); db.session.flush()
        b = ShipmentCargoItem(operational_shipment_id=shipment.id, line_number=2, cargo_owner_customer_id=owner.id,
            cargo_type_id=a.cargo_type_id, uom_id=a.uom_id, quantity=25, planned_quantity=25, actual_quantity=25,
            display_name_snapshot="کالای مشتری دوم", cargo_type_code_snapshot=a.cargo_type_code_snapshot,
            cargo_type_fa_snapshot=a.cargo_type_fa_snapshot, cargo_type_en_snapshot=a.cargo_type_en_snapshot,
            uom_code_snapshot=a.uom_code_snapshot, uom_symbol_snapshot=a.uom_symbol_snapshot,
            created_by=shipment.primary_responsible_expert_id, updated_by=shipment.primary_responsible_expert_id)
        db.session.add(b); db.session.commit()
        fixture.update(p308_cargo_b=b.public_id, p308_status=shipment.lifecycle_status)
    path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__": main()
