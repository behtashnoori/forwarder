"""Tailor the shared synthetic graph for the P3-02 cargo-lineage journey."""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    CargoType,
    Customer,
    ExpertUser,
    PackagingType,
    RequestCargoItem,
    ShipmentRequest,
    UnitOfMeasure,
)
from backend.operational_models import OperationalOrganization
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationPackagingTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from scripts.uat.seed_shared_transport_e2e import main as seed_shared_transport


def _activate(model, *, organization_id: int, reference_id: int, user_id: int):
    column = {
        OrganizationCargoTypeActivation: "cargo_type_id",
        OrganizationUnitOfMeasureActivation: "unit_of_measure_id",
        OrganizationPackagingTypeActivation: "packaging_type_id",
    }[model]
    row = model.query.filter_by(
        organization_id=organization_id,
        **{column: reference_id},
    ).one_or_none()
    if row is None:
        row = model(
            organization_id=organization_id,
            **{column: reference_id},
            created_by=user_id,
            updated_by=user_id,
        )
        db.session.add(row)
    row.status = "ACTIVE"
    row.updated_by = user_id


def _uom(code: str, fa_name: str, en_name: str, symbol: str, dimension: str) -> UnitOfMeasure:
    row = UnitOfMeasure.query.filter_by(immutable_code=code).one_or_none()
    if row is None:
        row = UnitOfMeasure(
            immutable_code=code,
            fa_name=fa_name,
            en_name=en_name,
            symbol=symbol,
            measurement_dimension=dimension,
            display_order=998,
            is_active=True,
            version=1,
        )
        db.session.add(row)
        db.session.flush()
    return row


def main() -> None:
    previous = os.environ.get("FORWARDER_E2E_PRIMARY_EXPERT")
    os.environ["FORWARDER_E2E_PRIMARY_EXPERT"] = "restricted"
    try:
        seed_shared_transport()
    finally:
        if previous is None:
            os.environ.pop("FORWARDER_E2E_PRIMARY_EXPERT", None)
        else:
            os.environ["FORWARDER_E2E_PRIMARY_EXPERT"] = previous

    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        organization = OperationalOrganization.query.filter_by(
            name="[SHARED-E2E] Organization A"
        ).one()
        owner = ExpertUser.query.filter_by(
            username="shared_transport_e2e_restricted"
        ).one()
        customer_a = db.session.get(Customer, fixture["owner_a_id"])
        customer_b = db.session.get(Customer, fixture["owner_b_id"])
        cargo_type = CargoType.query.filter_by(immutable_code="SHARED_E2E").one()
        item_uom = UnitOfMeasure.query.filter_by(immutable_code="PALLET").one()
        weight_uom = _uom("P3_E2E_KG", "کیلوگرم پی‌سه", "P3 kilogram", "kg", "WEIGHT")
        volume_uom = _uom("P3_E2E_M3", "متر مکعب پی‌سه", "P3 cubic metre", "m3", "VOLUME")
        packaging = PackagingType.query.filter_by(immutable_code="P3_E2E_CRATE").one_or_none()
        if packaging is None:
            packaging = PackagingType(
                immutable_code="P3_E2E_CRATE",
                fa_name="جعبه پی‌سه",
                en_name="P3 crate",
                display_order=998,
                is_active=True,
                version=1,
            )
            db.session.add(packaging)
            db.session.flush()

        _activate(
            OrganizationCargoTypeActivation,
            organization_id=organization.id,
            reference_id=cargo_type.id,
            user_id=owner.id,
        )
        for uom in (item_uom, weight_uom, volume_uom):
            _activate(
                OrganizationUnitOfMeasureActivation,
                organization_id=organization.id,
                reference_id=uom.id,
                user_id=owner.id,
            )
        _activate(
            OrganizationPackagingTypeActivation,
            organization_id=organization.id,
            reference_id=packaging.id,
            user_id=owner.id,
        )

        request_row = ShipmentRequest(
            contact_phone="09120000302",
            tracking_code="P3-02-E2E-REQUEST",
            assigned_to=owner.id,
            customer_id=customer_a.id,
            operational_organization_id=organization.id,
            ownership_scope="TENANT",
        )
        db.session.add(request_row)
        db.session.flush()
        request_cargo = RequestCargoItem(
            shipment_request_id=request_row.id,
            position=1,
            cargo_type_id=cargo_type.id,
            description="پمپ‌های درخواستی پی‌سه",
            quantity=Decimal("12"),
            uom_id=item_uom.id,
        )
        db.session.add(request_cargo)
        db.session.commit()

        fixture.update(
            {
                "p3_request": request_row.public_id,
                "p3_request_cargo": request_cargo.public_id,
                "p3_request_tracking_code": request_row.tracking_code,
                "p3_customer_a_label": customer_a.company_name,
                "p3_customer_b_label": customer_b.company_name,
                "p3_packaging_label": packaging.fa_name,
                "p3_weight_uom_label": weight_uom.fa_name,
                "p3_volume_uom_label": volume_uom.fa_name,
            }
        )
        manifest_path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
