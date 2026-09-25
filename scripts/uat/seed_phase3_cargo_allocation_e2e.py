"""Add a synthetic P3-05 Cargo journey to the owned P3-04 browser graph."""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.models import CargoType, UnitOfMeasure
from backend.operational_models import OperationalShipment, RouteCargoDestination, RouteLeg
from backend.organization_reference_catalog_models import OrganizationCargoTypeActivation, OrganizationUnitOfMeasureActivation
from backend.services import transport_execution_service as executions
from scripts.uat.seed_phase3_transport_execution_e2e import main as seed_transport


def main() -> None:
    seed_transport()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        shipment = OperationalShipment.query.filter_by(public_id=fixture["p304_shipment"]).one()
        road = db.session.get(RouteLeg, fixture["p304_road_leg"])
        rail = db.session.get(RouteLeg, fixture["p304_rail_leg"])
        rail.parent_route_leg_id = road.id
        cargo_type = CargoType(immutable_code="P305_E2E_PARTS", fa_name="قطعات موتور", en_name="Engine parts", is_active=True)
        uom = UnitOfMeasure(immutable_code="P305_E2E_CARTON", fa_name="کارتن", en_name="Carton", symbol="کارتن", measurement_dimension="COUNT", is_active=True)
        db.session.add_all([cargo_type, uom])
        db.session.flush()
        db.session.add_all([
            OrganizationCargoTypeActivation(organization_id=shipment.organization_id, cargo_type_id=cargo_type.id, created_by=shipment.primary_responsible_expert_id, updated_by=shipment.primary_responsible_expert_id),
            OrganizationUnitOfMeasureActivation(organization_id=shipment.organization_id, unit_of_measure_id=uom.id, created_by=shipment.primary_responsible_expert_id, updated_by=shipment.primary_responsible_expert_id),
        ])
        cargo = ShipmentCargoItem(
            operational_shipment_id=shipment.id,
            line_number=1,
            cargo_owner_customer_id=shipment.customer_id,
            cargo_type=cargo_type,
            uom=uom,
            quantity=Decimal("100"), planned_quantity=Decimal("100"), actual_quantity=Decimal("95"),
            display_name_snapshot="قطعات موتور", cargo_type_code_snapshot=cargo_type.immutable_code,
            cargo_type_fa_snapshot=cargo_type.fa_name, cargo_type_en_snapshot=cargo_type.en_name,
            uom_code_snapshot=uom.immutable_code, uom_symbol_snapshot=uom.symbol,
            created_by=shipment.primary_responsible_expert_id,
            updated_by=shipment.primary_responsible_expert_id,
        )
        db.session.add(cargo)
        db.session.flush()
        db.session.add(RouteCargoDestination(
            route_plan_id=fixture["p304_plan"], operational_shipment_id=shipment.id,
            shipment_cargo_item_id=cargo.id, destination_route_leg_id=rail.id,
            created_by_user_id=shipment.primary_responsible_expert_id,
        ))
        actor = {"id": shipment.primary_responsible_expert_id}
        road_payload = lambda identifier: {
            "transport_means_type_public_id": fixture["p304_truck"],
            "carrier_customer_id": fixture["p304_carrier_a"],
            "means_identifier": identifier,
            "equipment": [{"type_public_id": fixture["p304_trailer"], "identifier": f"TRAILER-{identifier}"}],
        }
        rail_payload = {
            "transport_means_type_public_id": fixture["p304_train"],
            "carrier_customer_id": fixture["p304_carrier_a"],
            "means_identifier": "WAGON-7",
            "equipment": [{"type_public_id": fixture["p304_wagon"], "identifier": "WAGON-7"}],
        }
        first, _ = executions.create(shipment.public_id, fixture["p304_plan"], road.id, road_payload("TRUCK-12"), actor, "p305-e2e-road-1")
        second, _ = executions.create(shipment.public_id, fixture["p304_plan"], road.id, road_payload("TRUCK-18"), actor, "p305-e2e-road-2")
        third, _ = executions.create(shipment.public_id, fixture["p304_plan"], rail.id, rail_payload, actor, "p305-e2e-rail")
        db.session.commit()
        fixture.update(p305_cargo=cargo.public_id, p305_first=first.public_id, p305_second=second.public_id, p305_third=third.public_id)
    path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
