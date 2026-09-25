"""Seed the disposable, local-only Shared Transport browser qualification graph.

The password and fixture manifest location are supplied only by the parent
qualification process.  This module never logs either value.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.cargo_models import ExecutionUnitCargoAllocation, ShipmentCargoItem, ShipmentCargoTransportAllocation
from backend.extensions import db
from backend.models import CargoType, Customer, CustomerRoleAssignment, ExpertUser, ShipmentTracking, ShipmentTransportUnit, UnitOfMeasure
from backend.operational_models import (
    CanonicalLocation, ExecutionUnit, OperationalMembership, OperationalOrganization,
    OperationalShipment, Project, ProjectAccess,
    RouteLeg, RoutePlan,
)
from backend.services.user_service import hash_password
from backend.services.multi_unit_tracking_service import enable_tracking_for_shipment


PREFIX = "shared_transport_e2e_"
PERMISSIONS = ["operational_shipment.read", "operational_shipment.create", "operational_shipment.create_direct", "operational_execution.read", "execution_unit.read", "execution_unit.create", "execution_unit.update"]


def one(model, **where):
    return model.query.filter_by(**where).one_or_none()


def customer(name: str, org_id: int) -> Customer:
    row = one(Customer, company_name=name, operational_organization_id=org_id)
    if row is None:
        row = Customer(company_name=name, first_name="Shared", last_name="E2E", status="active", operational_organization_id=org_id, ownership_scope="TENANT")
        db.session.add(row); db.session.flush()
    return row


def carrier_eligible(row: Customer) -> None:
    assignment = one(CustomerRoleAssignment, customer_id=row.id, role_code="CARRIER")
    if assignment is None:
        db.session.add(CustomerRoleAssignment(customer_id=row.id, operational_organization_id=row.operational_organization_id, role_code="CARRIER", is_active=True))
    else:
        assignment.is_active = True


def qualification_route_locations() -> tuple[CanonicalLocation, CanonicalLocation]:
    """Return stable local-only endpoints for a complete operational graph."""
    origin = one(CanonicalLocation, source_type="country", source_id=990001)
    if origin is None:
        origin = CanonicalLocation(
            source_type="country", source_id=990001, location_type="country",
            display_name="[SHARED-E2E] Origin", country_code="IRN",
        )
        db.session.add(origin)
    destination = one(CanonicalLocation, source_type="international_city", source_id=990002)
    if destination is None:
        destination = CanonicalLocation(
            source_type="international_city", source_id=990002, location_type="city",
            display_name="[SHARED-E2E] Destination", country_code="ARE",
        )
        db.session.add(destination)
    db.session.flush()
    return origin, destination


def add_active_route(shipment: OperationalShipment, *, user_id: int,
                     origin: CanonicalLocation, destination: CanonicalLocation) -> None:
    """Seed the route envelope required by the Shipment list contract."""
    plan = RoutePlan(
        operational_shipment_id=shipment.id, revision_number=1, status="active",
        is_active=True, created_by_user_id=user_id,
    )
    db.session.add(plan)
    db.session.flush()
    departure = datetime.now(timezone.utc) + timedelta(days=1)
    db.session.add(RouteLeg(
        route_plan_id=plan.id, sequence_number=1,
        origin_location_id=origin.id, destination_location_id=destination.id,
        origin_snapshot={"display_name": origin.display_name},
        destination_snapshot={"display_name": destination.display_name},
        transport_mode="road", planned_departure=departure,
        planned_arrival=departure + timedelta(days=2), status="planned",
    ))


def fixture_user(*, suffix: str, authority: str, password: str) -> ExpertUser:
    """Create a local qualification identity to the current User contract.

    Organization administrators cannot be created through ``create_user`` by
    design.  This is consequently the narrow, explicit fixture factory for
    every authority used by this harness; it keeps the model defaults and the
    production password-hashing implementation in one place.
    """
    username = PREFIX + suffix
    user = one(ExpertUser, username=username)
    if user is None:
        user = ExpertUser(
            username=username,
            password_hash=hash_password(password),
            full_name=f"[SHARED-E2E] {suffix}",
            role="expert" if authority == "EXPERT" else "admin",
            authority=authority,
            is_active=True,
            can_handle_domestic=True,
            can_handle_international=True,
            sla_response_work_minutes=120,
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.password_hash = hash_password(password)
        user.authority = authority
        user.role = "expert" if authority == "EXPERT" else "admin"
        user.is_active = True
        user.can_handle_domestic = True
        user.can_handle_international = True
        user.sla_response_work_minutes = 120
    return user


def validate_fixture_graph(*, org_a, org_b, users, projects, shipments, cargoes, uoms, carriers, owner_a, owner_b, foreign_owner, owner_x, owner_y, foreign_carrier, units) -> None:
    """Fail before browser startup when this qualification graph has drifted."""
    checks = {
        "organizations": len({org_a.id, org_b.id}) == 2,
        "authenticated_users": all(user.password_hash and user.is_active for user in users.values()),
        "restricted_scope": one(ProjectAccess, organization_id=org_a.id, project_id=projects["A"].id, user_id=users["restricted"].id) is not None,
        "restricted_scope_is_narrow": one(ProjectAccess, organization_id=org_a.id, project_id=projects["B"].id, user_id=users["restricted"].id) is None,
        "d_mixed_uom": (str(cargoes["A"].quantity), cargoes["A"].uom_code_snapshot, str(cargoes["B"].quantity), cargoes["B"].uom_code_snapshot, str(cargoes["C"].quantity), cargoes["C"].uom_code_snapshot) == ("20", "PALLET", "8", "TON", "350", "CARTON"),
        "e_owner_lifecycle": owner_a.operational_organization_id == owner_b.operational_organization_id == org_a.id and foreign_owner.operational_organization_id == org_b.id,
        "f_carrier_lifecycle": len(carriers) == 2 and all(row.operational_organization_id == org_a.id and row.status == "active" for row in carriers),
        "projects": len(projects) == 10 and len(shipments) == 10,
        "shipment_list_route_contract": all(
            db.session.query(RoutePlan).filter_by(
                operational_shipment_id=shipment.id, is_active=True
            ).count() == 1
            and db.session.query(RouteLeg).join(RoutePlan).filter(
                RoutePlan.operational_shipment_id == shipment.id,
                RoutePlan.is_active.is_(True),
            ).count() >= 1
            for shipment in shipments.values()
        ),
        "cargo_uoms": set(uoms) == {"PALLET", "TON", "CARTON"} and len(cargoes) == 10,
        "b_same_owner_identity": (
            shipments["SB"].id != shipments["A"].id
            and cargoes["SB"].id != cargoes["A"].id
            and cargoes["SB"].cargo_owner_customer_id
            == cargoes["A"].cargo_owner_customer_id
            == owner_a.id
        ),
        # I owns an isolated, initially unallocated canonical lifecycle.
        "i_initial_contract": (
            projects["I"].organization_id == org_a.id
            and shipments["I"].project_id == projects["I"].id
            and cargoes["I"].operational_shipment_id == shipments["I"].id
            and not db.session.query(ExecutionUnitCargoAllocation).filter_by(shipment_cargo_item_id=cargoes["I"].id).count()
            and units["I-X"].project_id == units["I-Y"].project_id == projects["I"].id
        ),
        "e_null_owner": cargoes["N"].cargo_owner_customer_id is None,
        # This is a historical, ownerless cargo line, not a no-tracking-data
        # case.  Its legacy transport context must be readable without ever
        # assigning a synthetic cargo owner.
        "e_null_owner_tracking": (
            one(ShipmentTracking, operational_shipment_id=shipments["N"].id) is not None
            and one(ShipmentTransportUnit, operational_shipment_id=shipments["N"].id, unit_code="SHARED-E2E-LEGACY-NULL-OWNER") is not None
            and one(ShipmentCargoTransportAllocation, operational_shipment_id=shipments["N"].id, shipment_cargo_item_id=cargoes["N"].id) is not None
        ),
        # C is the PR-02 dual-role Customer.  X/Y remain the same-name,
        # distinct-identity proof for the pre-existing cargo journey.
        "pr02_dual_role_owner": cargoes["C"].cargo_owner_customer_id != cargoes["A"].cargo_owner_customer_id,
        "c1_distinct_owner": cargoes["A"].cargo_owner_customer_id != cargoes["B"].cargo_owner_customer_id,
        "c2_same_name_distinct_identity": (
            cargoes["X"].cargo_owner_customer_id != cargoes["Y"].cargo_owner_customer_id
            and owner_x.company_name == owner_y.company_name
        ),
        # H must prove a complete, independent tenant graph rather than only
        # a foreign Customer/ExecutionUnit dangling from Organization B.
        "h_true_tenant_b_graph": (
            projects["T"].organization_id == org_b.id
            and shipments["T"].organization_id == org_b.id
            and shipments["T"].project_id == projects["T"].id
            and cargoes["T"].operational_shipment_id == shipments["T"].id
            and cargoes["T"].cargo_owner_customer_id == foreign_owner.id
            and foreign_owner.operational_organization_id == org_b.id
            and foreign_carrier.operational_organization_id == org_b.id
            and units["T"].organization_id == org_b.id
            and units["T"].project_id == projects["T"].id
            and units["T"].operational_shipment_id == shipments["T"].id
            and units["T"].carrier_customer_id == foreign_carrier.id
            and one(ExecutionUnitCargoAllocation, execution_unit_id=units["T"].id, shipment_cargo_item_id=cargoes["T"].id) is not None
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise RuntimeError("Shared Transport E2E fixture contract invalid: " + ", ".join(failures))


def main() -> None:
    password = os.environ["FORWARDER_E2E_PASSWORD"]
    manifest = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    app = create_app(skip_startup=True)
    with app.app_context():
        org_a = one(OperationalOrganization, name="[SHARED-E2E] Organization A") or OperationalOrganization(name="[SHARED-E2E] Organization A")
        org_b = one(OperationalOrganization, name="[SHARED-E2E] Organization B") or OperationalOrganization(name="[SHARED-E2E] Organization B")
        db.session.add_all([org_a, org_b]); db.session.flush()
        users = {}
        # The primary browser actor is the same-tenant Organization Admin,
        # which is authorized for the surrounding project configuration UI as
        # well as the shared-execution command.  The restricted expert remains
        # dedicated to the later isolation acceptance.
        for suffix, org, authority in (("operator", org_a, "ORGANIZATION_ADMIN"), ("restricted", org_a, "EXPERT"), ("zero", org_a, "EXPERT"), ("admin", org_a, "ORGANIZATION_ADMIN"), ("foreign", org_b, "ORGANIZATION_ADMIN")):
            user = fixture_user(suffix=suffix, authority=authority, password=password)
            membership = one(OperationalMembership, organization_id=org.id, user_id=user.id)
            if membership is None:
                membership = OperationalMembership(organization_id=org.id, user_id=user.id)
                db.session.add(membership)
            membership.permissions = PERMISSIONS; membership.is_active = True
            users[suffix] = user
        # Platform administration is deliberately global: it authenticates
        # without an OperationalMembership and must not acquire tenant scope
        # merely to exercise the qualification.
        users["platform"] = fixture_user(suffix="platform", authority="PLATFORM_ADMIN", password=password)
        db.session.flush()
        primary_expert = users[
            "restricted"
            if os.environ.get("FORWARDER_E2E_PRIMARY_EXPERT") == "restricted"
            else "operator"
        ]
        owner_a = customer("[SHARED-E2E] Customer A", org_a.id)
        # Customer's database identity, rather than its display text, is the test invariant.
        owner_a2 = Customer(company_name="[SHARED-E2E] Customer A Duplicate", first_name="Shared", last_name="E2E Duplicate", status="active", operational_organization_id=org_a.id, ownership_scope="TENANT")
        owner_b = customer("[SHARED-E2E] Customer B", org_a.id)
        # PR-02 deterministic party matrix.  These are deliberately ordinary
        # Customer identities: Carrier is additive eligibility, while C is
        # simultaneously a contextual Cargo Owner.
        owner_c = customer("[SHARED-E2E] Customer C", org_a.id)
        inactive_customer = customer("[SHARED-E2E] Customer D", org_a.id)
        inactive_customer.status = "inactive"
        owner_x = customer("[SHARED-E2E] Same Name Owner", org_a.id)
        owner_y = Customer(company_name="[SHARED-E2E] Same Name Owner", first_name="Different", last_name="Identity", status="active", operational_organization_id=org_a.id, ownership_scope="TENANT")
        carrier = customer("[SHARED-E2E] Carrier X", org_a.id)
        carrier_y = customer("[SHARED-E2E] Carrier Y", org_a.id)
        foreign_owner = customer("[SHARED-E2E] Foreign Customer", org_b.id)
        foreign_carrier = customer("[SHARED-E2E] Foreign Carrier", org_b.id)
        for carrier_party in (owner_b, owner_c, carrier, carrier_y, foreign_carrier):
            carrier_eligible(carrier_party)
        db.session.add(owner_a2); db.session.flush()
        cargo_type = CargoType.query.filter_by(immutable_code="SHARED_E2E").one_or_none()
        if cargo_type is None:
            cargo_type = CargoType(immutable_code="SHARED_E2E", fa_name="بار آزمایشی", en_name="Qualification Cargo", display_order=999, is_active=True, version=1)
            db.session.add(cargo_type)
        uoms = {}
        for code, fa, symbol in (("PALLET", "پالت", "PALLET"), ("TON", "تن", "TON"), ("CARTON", "کارتن", "CARTON")):
            unit = UnitOfMeasure.query.filter_by(immutable_code=code).one_or_none()
            if unit is None:
                unit = UnitOfMeasure(immutable_code=code, fa_name=fa, en_name=code.title(), symbol=symbol, measurement_dimension="COUNT", display_order=999, is_active=True, version=1)
                db.session.add(unit)
            uoms[code] = unit
        db.session.flush()
        projects, shipments, cargoes = {}, {}, {}
        db.session.add(owner_y); db.session.flush()
        for key, owner, qty, uom in (("A", owner_a, "20", "PALLET"), ("B", owner_b, "8", "TON"), ("C", owner_c, "350", "CARTON"), ("D", owner_a2, "1", "PALLET"), ("X", owner_x, "2", "TON"), ("Y", owner_y, "3", "CARTON"), ("SB", owner_a, "4", "PALLET")):
            project = Project(organization_id=org_a.id, primary_customer_id=owner.id, project_code=f"SHARED-E2E-{key}", lifecycle_status="in_progress", created_by_user_id=users["admin"].id)
            db.session.add(project); db.session.flush()
            shipment = OperationalShipment(organization_id=org_a.id, project_id=project.id, source_type="direct", customer_id=owner.id, lifecycle_status="in_progress", created_by_user_id=users["admin"].id, primary_responsible_expert_id=primary_expert.id)
            db.session.add(shipment); db.session.flush()
            cargo_name = "[SHARED-E2E] Scenario B Same Owner Cargo" if key == "SB" else f"[SHARED-E2E] Cargo {key}"
            cargo = ShipmentCargoItem(operational_shipment_id=shipment.id, cargo_owner_customer_id=owner.id, line_number=1, cargo_type_id=cargo_type.id, quantity=qty, uom_id=uoms[uom].id, display_name_snapshot=cargo_name, cargo_type_code_snapshot=cargo_type.immutable_code, cargo_type_fa_snapshot=cargo_type.fa_name, cargo_type_en_snapshot=cargo_type.en_name, uom_code_snapshot=uoms[uom].immutable_code, uom_symbol_snapshot=uoms[uom].symbol, created_by=users["admin"].id, updated_by=users["admin"].id)
            db.session.add(cargo)
            projects[key], shipments[key], cargoes[key] = project, shipment, cargo
        project = Project(organization_id=org_a.id, primary_customer_id=owner_a.id, project_code="SHARED-E2E-N", lifecycle_status="in_progress", created_by_user_id=users["admin"].id)
        db.session.add(project); db.session.flush()
        shipment = OperationalShipment(organization_id=org_a.id, project_id=project.id, source_type="direct", customer_id=owner_a.id, lifecycle_status="in_progress", created_by_user_id=users["admin"].id, primary_responsible_expert_id=primary_expert.id)
        db.session.add(shipment); db.session.flush()
        cargo = ShipmentCargoItem(operational_shipment_id=shipment.id, cargo_owner_customer_id=None, line_number=1, cargo_type_id=cargo_type.id, quantity="1", uom_id=uoms["PALLET"].id, display_name_snapshot="[SHARED-E2E] Cargo NULL Owner", cargo_type_code_snapshot=cargo_type.immutable_code, cargo_type_fa_snapshot=cargo_type.fa_name, cargo_type_en_snapshot=cargo_type.en_name, uom_code_snapshot=uoms["PALLET"].immutable_code, uom_symbol_snapshot=uoms["PALLET"].symbol, created_by=users["admin"].id, updated_by=users["admin"].id)
        db.session.add(cargo)
        projects["N"], shipments["N"], cargoes["N"] = project, shipment, cargo
        # I is deliberately separate from A-H.  It begins with no canonical
        # or legacy allocation and has two authorized execution targets.
        project = Project(organization_id=org_a.id, primary_customer_id=owner_a.id, project_code="SHARED-E2E-I", lifecycle_status="in_progress", created_by_user_id=users["admin"].id)
        db.session.add(project); db.session.flush()
        shipment = OperationalShipment(organization_id=org_a.id, project_id=project.id, source_type="direct", customer_id=owner_a.id, lifecycle_status="in_progress", created_by_user_id=users["admin"].id, primary_responsible_expert_id=primary_expert.id)
        db.session.add(shipment); db.session.flush()
        cargo = ShipmentCargoItem(operational_shipment_id=shipment.id, cargo_owner_customer_id=owner_a.id, line_number=1, cargo_type_id=cargo_type.id, quantity="5", uom_id=uoms["PALLET"].id, display_name_snapshot="[SHARED-E2E] Cargo I", cargo_type_code_snapshot=cargo_type.immutable_code, cargo_type_fa_snapshot=cargo_type.fa_name, cargo_type_en_snapshot=cargo_type.en_name, uom_code_snapshot=uoms["PALLET"].immutable_code, uom_symbol_snapshot=uoms["PALLET"].symbol, created_by=users["admin"].id, updated_by=users["admin"].id)
        db.session.add(cargo); db.session.flush()
        projects["I"], shipments["I"], cargoes["I"] = project, shipment, cargo
        # A complete independent Organization B graph is required for H.  It
        # deliberately has no relation to any Organization A record.
        project = Project(organization_id=org_b.id, primary_customer_id=foreign_owner.id, project_code="SHARED-E2E-TENANT-B", lifecycle_status="in_progress", created_by_user_id=users["foreign"].id)
        db.session.add(project); db.session.flush()
        shipment = OperationalShipment(organization_id=org_b.id, project_id=project.id, source_type="direct", customer_id=foreign_owner.id, lifecycle_status="in_progress", created_by_user_id=users["foreign"].id, primary_responsible_expert_id=users["foreign"].id)
        db.session.add(shipment); db.session.flush()
        cargo = ShipmentCargoItem(operational_shipment_id=shipment.id, cargo_owner_customer_id=foreign_owner.id, line_number=1, cargo_type_id=cargo_type.id, quantity="7", uom_id=uoms["PALLET"].id, display_name_snapshot="[SHARED-E2E] Tenant B Cargo", cargo_type_code_snapshot=cargo_type.immutable_code, cargo_type_fa_snapshot=cargo_type.fa_name, cargo_type_en_snapshot=cargo_type.en_name, uom_code_snapshot=uoms["PALLET"].immutable_code, uom_symbol_snapshot=uoms["PALLET"].symbol, created_by=users["foreign"].id, updated_by=users["foreign"].id)
        db.session.add(cargo); db.session.flush()
        projects["T"], shipments["T"], cargoes["T"] = project, shipment, cargo
        # The operational list is route-envelope based.  The shared transport
        # graph must therefore be complete operational data, not bare shipment
        # rows only visible through deep links.
        origin, destination = qualification_route_locations()
        for seeded_shipment in shipments.values():
            actor = users["foreign"] if seeded_shipment.organization_id == org_b.id else users["admin"]
            add_active_route(seeded_shipment, user_id=actor.id, origin=origin, destination=destination)
        db.session.flush()
        unit = ExecutionUnit(organization_id=org_a.id, project_id=projects["A"].id, operational_shipment_id=shipments["A"].id, unit_code="SHARED-E2E-UNIT", unit_type="road", lifecycle_status="ready", created_by_user_id=users["admin"].id)
        legacy_canonical_unit = ExecutionUnit(organization_id=org_a.id, project_id=projects["D"].id, operational_shipment_id=shipments["D"].id, unit_code="SHARED-E2E-LEGACY-CURRENT", unit_type="road", lifecycle_status="ready", created_by_user_id=users["admin"].id)
        foreign_unit = ExecutionUnit(organization_id=org_b.id, project_id=projects["T"].id, operational_shipment_id=shipments["T"].id, carrier_customer_id=foreign_carrier.id, unit_code="SHARED-E2E-FOREIGN", unit_type="road", lifecycle_status="ready", created_by_user_id=users["foreign"].id)
        i_unit_x = ExecutionUnit(organization_id=org_a.id, project_id=projects["I"].id, operational_shipment_id=shipments["I"].id, unit_code="SHARED-E2E-I-X", unit_type="road", lifecycle_status="ready", created_by_user_id=users["admin"].id)
        i_unit_y = ExecutionUnit(organization_id=org_a.id, project_id=projects["I"].id, operational_shipment_id=shipments["I"].id, unit_code="SHARED-E2E-I-Y", unit_type="road", lifecycle_status="ready", created_by_user_id=users["admin"].id)
        db.session.add_all([unit, legacy_canonical_unit, foreign_unit, i_unit_x, i_unit_y]); db.session.flush()
        db.session.add(ExecutionUnitCargoAllocation(execution_unit_id=foreign_unit.id, shipment_cargo_item_id=cargoes["T"].id, operational_shipment_id=shipments["T"].id, project_id=projects["T"].id, allocated_quantity=cargoes["T"].quantity, created_by=users["foreign"].id, updated_by=users["foreign"].id))
        # Historical fixture: direct seeded legacy rows are test evidence only;
        # the product has no legacy allocation mutator.  A1 has legacy truth
        # alone. A2 also has a canonical allocation, which must win in Tracking.
        legacy_units = {}
        for key, shipment, cargo, canonical in (
            ("A1", shipments["D"], cargoes["D"], False),
            ("A2", shipments["D"], cargoes["D"], True),
            ("NULL-OWNER", shipments["N"], cargoes["N"], False),
        ):
            legacy = ShipmentTransportUnit(
                operational_organization_id=org_a.id, ownership_scope="TENANT",
                operational_shipment_id=shipment.id, unit_code=f"SHARED-E2E-LEGACY-{key}",
                unit_type="truck", display_name=f"[SHARED-E2E] Historical {key}",
                created_by_user_id=users["admin"].id,
            )
            db.session.add(legacy); db.session.flush()
            db.session.add(ShipmentCargoTransportAllocation(
                operational_shipment_id=shipment.id, shipment_cargo_item_id=cargo.id,
                transport_unit_id=legacy.id, allocated_quantity=cargo.quantity,
                created_by=users["admin"].id, updated_by=users["admin"].id,
            ))
            enable_tracking_for_shipment(shipment, users["admin"].id)
            if canonical:
                db.session.add(ExecutionUnitCargoAllocation(
                    execution_unit_id=legacy_canonical_unit.id, shipment_cargo_item_id=cargo.id,
                    operational_shipment_id=shipment.id, project_id=shipment.project_id,
                    allocated_quantity=cargo.quantity, created_by=users["admin"].id, updated_by=users["admin"].id,
                ))
            legacy_units[key] = shipment
        for shipment in shipments.values():
            enable_tracking_for_shipment(shipment, users["admin"].id)
        for project in projects.values():
            if project.organization_id == org_a.id:
                db.session.add(ProjectAccess(organization_id=org_a.id, project_id=project.id, user_id=users["operator"].id, created_by_user_id=users["admin"].id))
        db.session.add(ProjectAccess(organization_id=org_a.id, project_id=projects["A"].id, user_id=users["restricted"].id, created_by_user_id=users["admin"].id))
        db.session.flush()
        validate_fixture_graph(org_a=org_a, org_b=org_b, users=users, projects=projects, shipments=shipments, cargoes=cargoes, uoms=uoms, carriers=(carrier, carrier_y), owner_a=owner_a, owner_b=owner_b, foreign_owner=foreign_owner, owner_x=owner_x, owner_y=owner_y, foreign_carrier=foreign_carrier, units={"A": unit, "T": foreign_unit, "I-X": i_unit_x, "I-Y": i_unit_y})
        db.session.commit()
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"project_a": projects["A"].public_id, "project_b": projects["B"].public_id, "unit": unit.public_id, "cargo_a": cargoes["A"].public_id, "cargo_b": cargoes["B"].public_id, "cargo_c": cargoes["C"].public_id, "cargo_x": cargoes["X"].public_id, "cargo_y": cargoes["Y"].public_id, "cargo_null_owner": cargoes["N"].public_id, "shipment_a": shipments["A"].public_id, "shipment_b": shipments["B"].public_id, "shipment_c": shipments["C"].public_id, "shipment_x": shipments["X"].public_id, "shipment_y": shipments["Y"].public_id, "shipment_null_owner": shipments["N"].public_id, "project_i": projects["I"].public_id, "shipment_i": shipments["I"].public_id, "cargo_i": cargoes["I"].public_id, "unit_i_x": i_unit_x.public_id, "unit_i_y": i_unit_y.public_id, "owner_a_id": owner_a.id, "owner_b_id": owner_b.id, "owner_c_id": owner_c.id, "inactive_customer_id": inactive_customer.id, "foreign_owner_id": foreign_owner.id, "owner_x_id": owner_x.id, "owner_y_id": owner_y.id, "same_owner_name": owner_x.company_name, "carrier_id": carrier.id, "carrier_y_id": carrier_y.id, "foreign_unit": foreign_unit.public_id, "foreign_customer_id": foreign_owner.id, "foreign_carrier_id": foreign_carrier.id, "tenant_b_project": projects["T"].public_id, "tenant_b_shipment": shipments["T"].public_id, "tenant_b_cargo": cargoes["T"].public_id, "legacy_only_shipment": legacy_units["A1"].public_id, "legacy_canonical_shipment": legacy_units["A2"].public_id}), encoding="utf-8")
        fixture_payload = json.loads(manifest.read_text(encoding="utf-8"))
        fixture_payload.update({
            "scenario_b_same_owner_shipment": shipments["SB"].public_id,
            "scenario_b_same_owner_cargo": cargoes["SB"].public_id,
            "scenario_b_same_owner_customer_id": cargoes["SB"].cargo_owner_customer_id,
        })
        manifest.write_text(json.dumps(fixture_payload), encoding="utf-8")


if __name__ == "__main__":
    main()
