"""Owned synthetic graph for Organization Shipment stages and exact closure."""
from __future__ import annotations

import json
import os
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import (
    OperationalMembership,
    OperationalShipment,
    RouteLeg,
    RoutePlan,
    utcnow,
)
from backend.services import occurrence_projection_service
from scripts.uat.seed_phase3_cargo_delivery_e2e import main as seed_delivery


def main() -> None:
    seed_delivery()
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        template = OperationalShipment.query.filter_by(
            public_id=fixture["p304_shipment"]
        ).one()
        template_leg = db.session.get(RouteLeg, fixture["p304_road_leg"])
        source = ShipmentCargoItem.query.filter_by(
            public_id=fixture["p305_cargo"]
        ).one()
        owner = ExpertUser.query.filter_by(
            username="shared_transport_e2e_restricted"
        ).one()
        membership = OperationalMembership.query.filter_by(user_id=owner.id).one()
        membership.permissions = sorted(
            set(membership.permissions or []).union({"milestone_event.create"})
        )
        shipment = OperationalShipment(
            organization_id=template.organization_id,
            project_id=None,
            source_type="direct",
            customer_id=template.customer_id,
            lifecycle_status="planned",
            created_by_user_id=owner.id,
            primary_responsible_expert_id=owner.id,
            created_at=utcnow() - timedelta(days=1),
        )
        db.session.add(shipment)
        db.session.flush()
        cargo = ShipmentCargoItem(
            operational_shipment_id=shipment.id,
            cargo_owner_customer_id=source.cargo_owner_customer_id,
            line_number=1,
            catalog_item_id=source.catalog_item_id,
            cargo_type_id=source.cargo_type_id,
            quantity=Decimal("100"),
            requested_quantity=None,
            planned_quantity=Decimal("100"),
            actual_quantity=None,
            uom_id=source.uom_id,
            packaging_type_id=source.packaging_type_id,
            display_name_snapshot=source.display_name_snapshot,
            cargo_type_code_snapshot=source.cargo_type_code_snapshot,
            cargo_type_fa_snapshot=source.cargo_type_fa_snapshot,
            cargo_type_en_snapshot=source.cargo_type_en_snapshot,
            uom_code_snapshot=source.uom_code_snapshot,
            uom_symbol_snapshot=source.uom_symbol_snapshot,
            created_by=owner.id,
            updated_by=owner.id,
        )
        db.session.add(cargo)
        plan = RoutePlan(
            operational_shipment_id=shipment.id,
            revision_number=1,
            status="active",
            is_active=True,
            created_by_user_id=owner.id,
        )
        db.session.add(plan)
        db.session.flush()
        leg = RouteLeg(
            route_plan_id=plan.id,
            sequence_number=1,
            origin_location_id=template_leg.origin_location_id,
            destination_location_id=template_leg.destination_location_id,
            origin_snapshot=template_leg.origin_snapshot,
            destination_snapshot=template_leg.destination_snapshot,
            transport_mode="road",
            planned_departure=template_leg.planned_departure,
            planned_arrival=template_leg.planned_arrival,
            status="planned",
            branch_label="مسیر آزمون تکمیل و بستن",
        )
        db.session.add(leg)
        db.session.flush()
        occurrence_projection_service.ensure_leg_milestones(leg, shipment)
        db.session.commit()
        fixture.update(
            organization_stage_shipment=shipment.public_id,
            organization_stage_cargo=cargo.public_id,
            organization_stage_route_leg=leg.id,
        )
    manifest_path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
