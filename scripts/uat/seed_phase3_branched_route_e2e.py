"""Create the owned synthetic graph for the P3-03 browser qualification."""
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
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import CargoType, Country, Customer, ExpertUser, Province, UnitOfMeasure
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
    ProjectAccess,
)
from scripts.uat.seed_phase3_cargo_lineage_e2e import main as seed_cargo_lineage


ROUTE_PERMISSIONS = {
    "route_plan.read",
    "route_plan.create",
    "route_plan.activate",
    "route_plan.replan",
    "route_leg.manage",
    "checkpoint.report",
}


def _province(code: str, name: str) -> Province:
    row = Province.query.filter_by(code=code).one_or_none()
    if row is None:
        row = Province(code=code, name_fa=name, is_active=True)
        db.session.add(row)
        db.session.flush()
    return row


def _cargo(
    shipment: OperationalShipment,
    *,
    line: int,
    name: str,
    owner: Customer,
    cargo_type: CargoType,
    uom: UnitOfMeasure,
    user_id: int,
) -> ShipmentCargoItem:
    row = ShipmentCargoItem(
        operational_shipment_id=shipment.id,
        cargo_owner_customer_id=owner.id,
        line_number=line,
        cargo_type_id=cargo_type.id,
        quantity=Decimal("10" if line == 1 else "20"),
        planned_quantity=Decimal("10" if line == 1 else "20"),
        uom_id=uom.id,
        display_name_snapshot=name,
        cargo_type_code_snapshot=cargo_type.immutable_code,
        cargo_type_fa_snapshot=cargo_type.fa_name,
        cargo_type_en_snapshot=cargo_type.en_name,
        uom_code_snapshot=uom.immutable_code,
        uom_symbol_snapshot=uom.symbol,
        created_by=user_id,
        updated_by=user_id,
    )
    db.session.add(row)
    db.session.flush()
    return row


def main() -> None:
    seed_cargo_lineage()
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        organization = OperationalOrganization.query.filter_by(
            name="[SHARED-E2E] Organization A"
        ).one()
        foreign_organization = OperationalOrganization.query.filter_by(
            name="[SHARED-E2E] Organization B"
        ).one()
        restricted = ExpertUser.query.filter_by(
            username="shared_transport_e2e_restricted"
        ).one()
        admin = ExpertUser.query.filter_by(
            username="shared_transport_e2e_admin"
        ).one()
        foreign = ExpertUser.query.filter_by(
            username="shared_transport_e2e_foreign"
        ).one()
        for user in (restricted, admin, foreign):
            membership = OperationalMembership.query.filter_by(user_id=user.id).one()
            membership.permissions = sorted(
                set(membership.permissions or []).union(ROUTE_PERMISSIONS)
            )

        owner = db.session.get(Customer, fixture["owner_a_id"])
        cargo_type = CargoType.query.filter_by(immutable_code="SHARED_E2E").one()
        uom = UnitOfMeasure.query.filter_by(immutable_code="PALLET").one()
        project = Project(
            organization_id=organization.id,
            primary_customer_id=owner.id,
            project_code="P3-03-E2E-BRANCHED-ROUTE",
            lifecycle_status="in_progress",
            created_by_user_id=admin.id,
        )
        db.session.add(project)
        db.session.flush()
        shipment = OperationalShipment(
            organization_id=organization.id,
            project_id=project.id,
            source_type="direct",
            customer_id=owner.id,
            lifecycle_status="in_progress",
            created_by_user_id=admin.id,
            primary_responsible_expert_id=restricted.id,
        )
        db.session.add(shipment)
        db.session.flush()
        db.session.add(
            ProjectAccess(
                organization_id=organization.id,
                project_id=project.id,
                user_id=restricted.id,
                created_by_user_id=admin.id,
            )
        )
        cargo_a = _cargo(
            shipment,
            line=1,
            name="[P3-03-E2E] کالای مقصد تهران",
            owner=owner,
            cargo_type=cargo_type,
            uom=uom,
            user_id=restricted.id,
        )
        cargo_b = _cargo(
            shipment,
            line=2,
            name="[P3-03-E2E] کالای مقصد قزوین",
            owner=owner,
            cargo_type=cargo_type,
            uom=uom,
            user_id=restricted.id,
        )
        places = {
            "origin": _province("P303-O", "مبدأ آزمایشی پی‌سه"),
            "hub": _province("P303-H", "مرکز مشترک پی‌سه"),
            "tehran": _province("P303-T", "تهران پی‌سه"),
            "qazvin": _province("P303-Q", "قزوین پی‌سه"),
            "deviation": _province("P303-D", "مقصد واقعی متفاوت پی‌سه"),
        }
        country = Country.query.filter_by(code="QZ").one_or_none()
        if country is None:
            country = Country(
                code="QZ",
                name_en="P3 synthetic country",
                name_fa="کشور آزمایشی پی‌سه",
                is_active=True,
            )
            db.session.add(country)
            db.session.flush()
        point_type = LogisticsPointType.query.filter_by(
            immutable_code="P3_E2E_FOREIGN_DEPOT"
        ).one_or_none()
        if point_type is None:
            point_type = LogisticsPointType(
                immutable_code="P3_E2E_FOREIGN_DEPOT",
                fa_name="انبار خارجی آزمایشی",
                en_name="P3 foreign depot",
                is_active=True,
                created_by=foreign.id,
                updated_by=foreign.id,
            )
            db.session.add(point_type)
            db.session.flush()
        foreign_point = LogisticsPoint(
            organization_id=foreign_organization.id,
            immutable_code="P3-E2E-FOREIGN-ONLY",
            logistics_point_type_id=point_type.id,
            fa_name="نقطه خارجی غیرمجاز پی‌سه",
            normalized_name="p3 foreign only point",
            country_id=country.id,
            geography_key=f"country:{country.id}",
            is_active=True,
            created_by=foreign.id,
            updated_by=foreign.id,
        )
        db.session.add(foreign_point)
        db.session.flush()
        db.session.commit()
        fixture.update(
            {
                "p3_route_shipment": shipment.public_id,
                "p3_route_project": project.public_id,
                "p3_route_cargo_a": cargo_a.public_id,
                "p3_route_cargo_b": cargo_b.public_id,
                "p3_route_places": {
                    key: {"id": row.id, "label": row.name_fa}
                    for key, row in places.items()
                },
                "p3_route_foreign_logistics_point": foreign_point.public_id,
            }
        )
        manifest_path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
