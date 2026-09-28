"""Owned fixture for the accepted Request Cargo to ETA continuity proof.

The browser creates the Shipment and Cargo.  This seed only supplies the
accepted commercial source, governed reference choices, route endpoints, and
transport reference data needed to exercise the real commands.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.cargo_models import CargoCatalogItem
from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import (
    CargoType,
    Country,
    Customer,
    ExpertQuote,
    ExpertUser,
    RequestCargoItem,
    ShipmentRequest,
    UnitOfMeasure,
)
from backend.operational_models import OperationalOrganization
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from scripts.uat.seed_phase3_transport_execution_e2e import (
    main as seed_transport_execution,
)


def _active_reference(model, *, organization_id: int, reference_id: int, actor_id: int):
    column = {
        OrganizationCargoTypeActivation: "cargo_type_id",
        OrganizationUnitOfMeasureActivation: "unit_of_measure_id",
    }[model]
    row = model.query.filter_by(
        organization_id=organization_id, **{column: reference_id}
    ).one_or_none()
    if row is None:
        row = model(
            organization_id=organization_id,
            **{column: reference_id},
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.session.add(row)
    row.status = "ACTIVE"
    row.updated_by = actor_id


def main() -> None:
    seed_transport_execution()
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        organization = OperationalOrganization.query.filter_by(
            name="[SHARED-E2E] Organization A"
        ).one()
        actor = ExpertUser.query.filter_by(
            username="shared_transport_e2e_restricted"
        ).one()
        customer = db.session.get(Customer, fixture["owner_a_id"])

        cargo_type = CargoType.query.filter_by(
            immutable_code="HW_CARGO_CHAIN_PARTS"
        ).one_or_none()
        if cargo_type is None:
            cargo_type = CargoType(
                immutable_code="HW_CARGO_CHAIN_PARTS",
                fa_name="قطعات مکانیکی آزمون زنجیره",
                en_name="Cargo chain mechanical parts",
                display_order=939,
                is_active=True,
                version=1,
            )
            db.session.add(cargo_type)
            db.session.flush()
        uom = UnitOfMeasure.query.filter_by(
            immutable_code="HW_CARGO_CHAIN_PIECE"
        ).one_or_none()
        if uom is None:
            uom = UnitOfMeasure(
                immutable_code="HW_CARGO_CHAIN_PIECE",
                fa_name="عدد",
                en_name="Piece",
                symbol="pcs",
                measurement_dimension="COUNT",
                display_order=939,
                is_active=True,
                version=1,
            )
            db.session.add(uom)
            db.session.flush()
        _active_reference(
            OrganizationCargoTypeActivation,
            organization_id=organization.id,
            reference_id=cargo_type.id,
            actor_id=actor.id,
        )
        _active_reference(
            OrganizationUnitOfMeasureActivation,
            organization_id=organization.id,
            reference_id=uom.id,
            actor_id=actor.id,
        )

        request_row = ShipmentRequest(
            contact_phone="09120000928",
            tracking_code="HW-CARGO-CHAIN-REQUEST",
            assigned_to=actor.id,
            customer_id=customer.id,
            operational_organization_id=organization.id,
            ownership_scope="TENANT",
            status="quoted",
        )
        db.session.add(request_row)
        db.session.flush()
        request_cargo = RequestCargoItem(
            shipment_request_id=request_row.id,
            position=1,
            cargo_type_id=cargo_type.id,
            description="مجموعه قطعات موتور آزمون زنجیره",
            quantity=Decimal("100"),
            uom_id=uom.id,
        )
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            amount=928000000,
            currency="IRR",
            created_by_expert_id=actor.id,
            customer_response="accepted",
            response_version=1,
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=organization.id,
        )
        catalog = CargoCatalogItem(
            organization_id=organization.id,
            immutable_code="HW-CARGO-CHAIN-XU7P",
            fa_name="مجموعه قطعات موتور XU7P آزمون زنجیره",
            en_name="Cargo chain XU7P engine parts",
            cargo_type_id=cargo_type.id,
            default_uom_id=uom.id,
            description="Owned browser qualification catalog item.",
            search_text="XU7P قطعات موتور cargo chain",
            created_by=actor.id,
            updated_by=actor.id,
        )
        db.session.add_all([request_cargo, quote, catalog])

        country = Country.query.filter_by(code="XZ").one_or_none()
        if country is None:
            country = Country(
                code="XZ",
                name_en="Cargo Chain Qualification",
                name_fa="کشور آزمون زنجیره",
                is_active=True,
            )
            db.session.add(country)
            db.session.flush()
        point_type = LogisticsPointType.query.filter_by(
            immutable_code="HW_CARGO_CHAIN_WAREHOUSE"
        ).one_or_none()
        if point_type is None:
            point_type = LogisticsPointType(
                immutable_code="HW_CARGO_CHAIN_WAREHOUSE",
                fa_name="انبار آزمون زنجیره",
                en_name="Cargo chain warehouse",
                display_order=939,
                is_active=True,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.session.add(point_type)
            db.session.flush()

        def point(code: str, fa_name: str, geography: str) -> LogisticsPoint:
            row = LogisticsPoint(
                organization_id=organization.id,
                immutable_code=code,
                logistics_point_type_id=point_type.id,
                fa_name=fa_name,
                en_name=code,
                normalized_name=code.lower(),
                country_id=country.id,
                geography_key=geography,
                is_active=True,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.session.add(row)
            return row

        origin = point(
            "HW-CARGO-CHAIN-ORIGIN",
            "انبار مبدأ آزمون زنجیره",
            "country:XZ:origin",
        )
        destination = point(
            "HW-CARGO-CHAIN-DESTINATION",
            "انبار مقصد آزمون زنجیره",
            "country:XZ:destination",
        )
        db.session.commit()

        fixture.update(
            {
                "hw_chain_quote_id": quote.id,
                "hw_chain_request": request_row.public_id,
                "hw_chain_request_tracking": request_row.tracking_code,
                "hw_chain_request_cargo": request_cargo.public_id,
                "hw_chain_catalog": catalog.public_id,
                "hw_chain_catalog_label": catalog.fa_name,
                "hw_chain_origin": origin.public_id,
                "hw_chain_origin_label": origin.fa_name,
                "hw_chain_destination": destination.public_id,
                "hw_chain_destination_label": destination.fa_name,
            }
        )
        manifest_path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
