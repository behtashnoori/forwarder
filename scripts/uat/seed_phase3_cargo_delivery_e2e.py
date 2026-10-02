"""Owned P3-08 two-Customer browser graph extends its P3-05 dependency."""
import json
import os
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import create_app
from backend.extensions import db
from backend.geonames_geography_catalog import DATASET_ID as GEONAMES_DATASET_ID
from backend.cargo_models import ShipmentCargoItem
from backend.models import City, Country, Customer, DocumentDefinition, ExpertUser
from backend.operational_models import OperationalShipment
from scripts.uat.canonical_geography_fixture import ensure_canonical_geography
from scripts.uat.seed_phase3_cargo_allocation_e2e import main as seed_cargo


def main():
    seed_cargo()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        ensure_canonical_geography()
        destination = (City.query.join(Country).filter(
            Country.code == "IR",
            City.dataset_id == GEONAMES_DATASET_ID,
            City.is_active.is_(True),
        ).order_by(City.geoname_id).first())
        if destination is None or destination.province is None:
            raise RuntimeError("P3-08 requires a qualified canonical delivery city")
        shipment = OperationalShipment.query.filter_by(public_id=fixture["p304_shipment"]).one()
        admin = ExpertUser.query.filter_by(username="shared_transport_e2e_admin").one()
        for order, (code, name_fa, name_en) in enumerate((
            ("HW_BILL_OF_LADING", "بارنامه", "Transport Document"),
            ("HW_INVOICE", "فاکتور", "Invoice"),
            ("HW_PACKING_LIST", "پکینگ لیست", "Packing List"),
            ("HW_DELIVERY_RECEIPT", "رسید تحویل", "Delivery Receipt"),
        ), start=1):
            if DocumentDefinition.query.filter_by(code=code).one_or_none() is None:
                db.session.add(DocumentDefinition(
                    code=code,
                    title=name_fa,
                    name_fa=name_fa,
                    name_en=name_en,
                    is_required=False,
                    allowed_formats='["pdf"]',
                    max_file_size_bytes=2 * 1024 * 1024,
                    max_active_file_count=4,
                    sort_order=-100 + order,
                    applicability_scope="all",
                    catalog_lifecycle_status="ACTIVE",
                    source_review_status="VERIFIED",
                    created_by=admin.id,
                    updated_by=admin.id,
                ))
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
        fixture.update(
            p308_cargo_b=b.public_id,
            p308_status=shipment.lifecycle_status,
            p308_geography={
                "country_id": destination.country_id,
                "admin1_geoname_id": destination.province.geoname_id,
                "city_geoname_id": destination.geoname_id,
            },
        )
    path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__": main()
