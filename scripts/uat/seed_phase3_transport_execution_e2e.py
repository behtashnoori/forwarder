"""Create the owned synthetic graph for the P3-04 browser qualification."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    Customer,
    ExpertUser,
    TransportEquipmentType,
    TransportMeansType,
)
from backend.operational_models import (
    CanonicalLocation,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
    ProjectAccess,
    RouteLeg,
    RoutePlan,
)
from backend.organization_reference_catalog_models import (
    OrganizationTransportEquipmentTypeActivation,
    OrganizationTransportMeansTypeActivation,
)
from scripts.uat.seed_phase3_reference_catalog_e2e import main as seed_reference_catalog


EXECUTION_PERMISSIONS = {
    "operational_shipment.read",
    "execution_unit.read",
    "execution_unit.create",
    "execution_unit.update",
}


def _definition(model, code: str, fa_name: str, en_name: str):
    row = model.query.filter_by(immutable_code=code).one_or_none()
    if row is None:
        row = model(
            immutable_code=code,
            fa_name=fa_name,
            en_name=en_name,
            display_order=940,
            is_active=True,
        )
        db.session.add(row)
        db.session.flush()
    return row


def _activate(model, *, organization_id: int, definition_id: int, actor_id: int):
    fk = (
        "transport_means_type_id"
        if model is OrganizationTransportMeansTypeActivation
        else "transport_equipment_type_id"
    )
    row = model.query.filter_by(
        organization_id=organization_id, **{fk: definition_id}
    ).one_or_none()
    if row is None:
        row = model(
            organization_id=organization_id,
            created_by=actor_id,
            updated_by=actor_id,
            **{fk: definition_id},
        )
        db.session.add(row)
    else:
        row.status = "ACTIVE"
        row.updated_by = actor_id
    return row


def _location(source_id: int, display_name: str, country_code: str):
    row = CanonicalLocation.query.filter_by(
        source_type="international_city", source_id=source_id
    ).one_or_none()
    if row is None:
        row = CanonicalLocation(
            source_type="international_city",
            source_id=source_id,
            location_type="city",
            display_name=display_name,
            country_code=country_code,
        )
        db.session.add(row)
        db.session.flush()
    return row


def main() -> None:
    seed_reference_catalog()
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
                set(membership.permissions or []).union(EXECUTION_PERMISSIONS)
            )

        truck = _definition(
            TransportMeansType, "P304_E2E_TRUCK", "کامیون آزمایشی", "P3-04 truck"
        )
        train = _definition(
            TransportMeansType, "P304_E2E_TRAIN", "قطار آزمایشی", "P3-04 train"
        )
        foreign_means = _definition(
            TransportMeansType,
            "P304_E2E_FOREIGN_MEANS",
            "وسیله خارجی آزمایشی",
            "P3-04 foreign means",
        )
        trailer = _definition(
            TransportEquipmentType,
            "P304_E2E_TRAILER",
            "تریلر آزمایشی",
            "P3-04 trailer",
        )
        wagon = _definition(
            TransportEquipmentType,
            "P304_E2E_WAGON",
            "واگن آزمایشی",
            "P3-04 wagon",
        )
        container = _definition(
            TransportEquipmentType,
            "P304_E2E_CONTAINER",
            "کانتینر آزمایشی",
            "P3-04 container",
        )
        foreign_equipment = _definition(
            TransportEquipmentType,
            "P304_E2E_FOREIGN_EQUIPMENT",
            "تجهیز خارجی آزمایشی",
            "P3-04 foreign equipment",
        )
        for item in (truck, train):
            _activate(
                OrganizationTransportMeansTypeActivation,
                organization_id=organization.id,
                definition_id=item.id,
                actor_id=admin.id,
            )
        for item in (trailer, wagon, container):
            _activate(
                OrganizationTransportEquipmentTypeActivation,
                organization_id=organization.id,
                definition_id=item.id,
                actor_id=admin.id,
            )
        _activate(
            OrganizationTransportMeansTypeActivation,
            organization_id=foreign_organization.id,
            definition_id=foreign_means.id,
            actor_id=foreign.id,
        )
        _activate(
            OrganizationTransportEquipmentTypeActivation,
            organization_id=foreign_organization.id,
            definition_id=foreign_equipment.id,
            actor_id=foreign.id,
        )

        owner = db.session.get(Customer, fixture["owner_a_id"])
        carrier_a = db.session.get(Customer, fixture["carrier_id"])
        carrier_b = db.session.get(Customer, fixture["carrier_y_id"])
        foreign_carrier = db.session.get(Customer, fixture["foreign_carrier_id"])
        foreign_shipment = OperationalShipment.query.filter_by(
            public_id=fixture["tenant_b_shipment"]
        ).one()
        foreign_plan = RoutePlan.query.filter_by(
            operational_shipment_id=foreign_shipment.id, is_active=True
        ).one()
        foreign_leg = RouteLeg.query.filter_by(route_plan_id=foreign_plan.id).one()
        project = Project(
            organization_id=organization.id,
            primary_customer_id=owner.id,
            project_code="P3-04-E2E-TRANSPORT-EXECUTION",
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
        china = _location(994001, "چین آزمایشی", "CHN")
        khorgos = _location(994002, "خورگوس آزمایشی", "KAZ")
        aktau = _location(994003, "آکتائو آزمایشی", "KAZ")
        plan = RoutePlan(
            operational_shipment_id=shipment.id,
            revision_number=1,
            status="active",
            is_active=True,
            created_by_user_id=restricted.id,
        )
        db.session.add(plan)
        db.session.flush()
        departure = datetime.now(timezone.utc) + timedelta(days=1)
        road = RouteLeg(
            route_plan_id=plan.id,
            sequence_number=1,
            origin_location_id=china.id,
            destination_location_id=khorgos.id,
            origin_snapshot={"display_name": china.display_name},
            destination_snapshot={"display_name": khorgos.display_name},
            transport_mode="road",
            planned_departure=departure,
            planned_arrival=departure + timedelta(hours=8),
            status="planned",
            branch_label="جاده چین تا مرز",
        )
        rail = RouteLeg(
            route_plan_id=plan.id,
            sequence_number=2,
            origin_location_id=khorgos.id,
            destination_location_id=aktau.id,
            origin_snapshot={"display_name": khorgos.display_name},
            destination_snapshot={"display_name": aktau.display_name},
            transport_mode="rail",
            planned_departure=departure + timedelta(hours=10),
            planned_arrival=departure + timedelta(days=2),
            status="planned",
            branch_label="ریل خورگوس تا آکتائو",
        )
        db.session.add_all([road, rail])
        db.session.flush()
        db.session.commit()
        fixture.update(
            {
                "p304_shipment": shipment.public_id,
                "p304_project": project.public_id,
                "p304_plan": plan.id,
                "p304_road_leg": road.id,
                "p304_rail_leg": rail.id,
                "p304_truck": truck.public_id,
                "p304_train": train.public_id,
                "p304_foreign_means": foreign_means.public_id,
                "p304_trailer": trailer.public_id,
                "p304_wagon": wagon.public_id,
                "p304_container": container.public_id,
                "p304_foreign_equipment": foreign_equipment.public_id,
                "p304_carrier_a": carrier_a.id,
                "p304_carrier_b": carrier_b.id,
                "p304_foreign_carrier": foreign_carrier.id,
                "p304_carrier_a_label": carrier_a.company_name,
                "p304_carrier_b_label": carrier_b.company_name,
                "p304_foreign_leg": foreign_leg.id,
            }
        )
        manifest_path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
