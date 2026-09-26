"""Owned synthetic P3-11 cases; operational commands establish all ETA facts."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import create_app
from backend.extensions import db
from backend.models import CargoType, Customer, CustomerGamification, ExpertUser, Province, UnitOfMeasure, TransportMeansType
from backend.operational_models import CanonicalLocation, Milestone, OperationalCheckpoint, OperationalMembership, OperationalShipment, RouteLeg
from backend.security import security
from backend.services import customer_entitlement_service as grants, operational_service as operations
from backend.services import reported_fact_service as reports, route_orchestration_service as routes, route_time_service as times
from scripts.uat.seed_phase3_branched_route_e2e import main as seed_route, _cargo


def main():
    seed_route()  # Its root guard requires the exact owned local database prefix.
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        template = OperationalShipment.query.filter_by(public_id=fixture["p3_route_shipment"]).one()
        owner = db.session.get(ExpertUser, template.primary_responsible_expert_id)
        admin = ExpertUser.query.filter_by(username="shared_transport_e2e_admin").one()
        membership = OperationalMembership.query.filter_by(user_id=owner.id).one()
        membership.permissions = sorted(set(membership.permissions) | {"milestone_event.create", "milestone.correct", "operational_shipment.create"})
        actor = {"id": owner.id}
        customer = db.session.get(Customer, fixture["owner_a_id"])
        other = Customer(company_name="مشتری خصوصی دوم", operational_organization_id=template.organization_id,
                         ownership_scope="TENANT", status="active")
        db.session.add(other); db.session.flush()
        accounts = {}
        for name, crm in (("a", customer), ("b", other)):
            account = CustomerGamification(email=f"p311-{name}@example.test", phone=f"0900111000{len(accounts)}",
                first_name="مشتری", last_name=name, is_email_verified=True,
                operational_organization_id=template.organization_id,
                password_hash=security.hash_password(os.environ["FORWARDER_E2E_PASSWORD"]))
            db.session.add(account); db.session.flush()
            grants.grant(template.organization_id, admin.id, {"portal_account_public_id": account.public_id,
                         "customer_id": crm.id}, str(uuid4()))
            accounts[name] = {"email": account.email, "public_id": account.public_id}
        db.session.commit()
        kind = CargoType.query.filter_by(immutable_code="SHARED_E2E").one()
        uom = UnitOfMeasure.query.filter_by(immutable_code="PALLET").one()
        from backend.organization_reference_catalog_models import OrganizationTransportMeansTypeActivation
        truck = TransportMeansType(immutable_code="P311_TRUCK", fa_name="کامیون آزمون", en_name="Test truck", is_active=True)
        db.session.add(truck); db.session.flush()
        db.session.add(OrganizationTransportMeansTypeActivation(organization_id=template.organization_id,
            transport_means_type_id=truck.id, created_by=admin.id, updated_by=admin.id))
        db.session.commit()
        basis = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(hours=2)
        cases = {}
        for case_index, name in enumerate(("departure", "arrived", "complete", "next_departure", "zero", "unknown", "missing_later", "origin", "destination", "split")):
            shipment = OperationalShipment(organization_id=template.organization_id, project_id=template.project_id,
                source_type="direct", customer_id=customer.id, lifecycle_status="planned",
                created_by_user_id=owner.id, primary_responsible_expert_id=owner.id)
            db.session.add(shipment); db.session.flush()
            cargo = _cargo(shipment, line=1, name=f"آزمون زمان رسیدن {name}", owner=customer,
                          cargo_type=kind, uom=uom, user_id=owner.id)
            db.session.commit()
            plan = routes.create_plan(shipment.id, {}, actor)
            places = []
            for index in range(5):
                place = Province(code=f"P311-{case_index}-{index}", name_fa=f"نقطه {index+1} {name}", is_active=True)
                db.session.add(place); places.append(place)
            db.session.commit()
            count = 3 if name == "missing_later" else 2
            legs = []
            for index in range(count):
                start = basis + timedelta(days=1, hours=index*12)
                leg = routes.add_leg(shipment.id, plan["id"], {"sequence_number": index+1,
                    "parent_route_leg_id": legs[-1]["id"] if legs else None,
                    "origin": {"source_type": "province", "source_id": places[index].id},
                    "destination": {"source_type": "province", "source_id": places[index+1].id},
                    "transport_mode": "road", "planned_departure": start.isoformat(),
                    "planned_arrival": (start + timedelta(hours=2)).isoformat()}, actor)
                legs.append(leg)
            private_cargo = None
            if name == "arrived":
                private_cargo = _cargo(shipment, line=2, name="PRIVATE-CARGO-B", owner=other,
                                       cargo_type=kind, uom=uom, user_id=owner.id)
                db.session.commit()
                private = routes.add_leg(shipment.id, plan["id"], {"sequence_number": 3,
                    "parent_route_leg_id": legs[0]["id"],
                    "origin": {"source_type": "province", "source_id": places[1].id},
                    "destination": {"source_type": "province", "source_id": places[4].id},
                    "transport_mode": "road", "planned_departure": (basis+timedelta(days=2)).isoformat(),
                    "planned_arrival": (basis+timedelta(days=2,hours=2)).isoformat()}, actor)
                routes.assign_cargo_destination(shipment.id, plan["id"], private_cargo.public_id,
                                               {"destination_route_leg_id": private["id"]}, actor)
            routes.assign_cargo_destination(shipment.id, plan["id"], cargo.public_id,
                                           {"destination_route_leg_id": legs[-1]["id"]}, actor)
            checkpoint = None
            if name == "complete":
                incoming = db.session.get(RouteLeg, legs[0]["id"])
                checkpoint = routes.add_checkpoint(shipment.id, plan["id"], {"sequence_number": 1,
                    "route_leg_id": incoming.id, "canonical_location_id": incoming.destination_location_id,
                    "checkpoint_type": "transshipment", "planned_arrival_at": incoming.planned_arrival.isoformat(),
                    "planned_departure_at": (incoming.planned_arrival+timedelta(hours=8)).isoformat()}, actor)
            references = []
            for index, leg in enumerate(legs):
                if name == "missing_later" and index == 2:
                    continue
                stop = (0, 0) if name == "zero" else (None, None) if name == "unknown" else (240, 480)
                version, _ = times.save({"id": admin.id}, {
                    "origin": {"source_type": "province", "source_id": places[index].id},
                    "destination": {"source_type": "province", "source_id": places[index+1].id},
                    "transport_mode": "road", "movement_min_minutes": 60, "movement_max_minutes": 120,
                    "stop_min_minutes": stop[0], "stop_max_minutes": stop[1],
                    "effective_from": (basis-timedelta(days=1)).isoformat()}, str(uuid4()))
                db.session.commit()
                source_leg = db.session.get(RouteLeg, leg["id"])
                times.select_basis(shipment.public_id, plan["id"], source_leg.id, actor,
                    {"expected_version": source_leg.version, "expected_selection_revision": 0,
                     "reference_version_public_id": version.public_id}, str(uuid4()))
                db.session.commit()
                references.append({"public_id": version.reference.public_id if hasattr(version, "reference") else None,
                                   "id": version.id, "reference_id": version.reference_id})
            routes.activate_plan(shipment.id, plan["id"], {"expected_version": 1}, actor)
            if name == "split":
                from backend.services import cargo_allocation_service as allocations
                from backend.services import transport_execution_service as executions
                cargo.actual_quantity = 10
                db.session.commit()
                for index in range(2):
                    stage, _ = executions.create(shipment.public_id, plan["id"], legs[0]["id"],
                        {"transport_means_type_public_id": truck.public_id, "means_identifier": f"P311-SPLIT-{index}",
                         "equipment": []}, actor, str(uuid4()))
                    db.session.commit()
                    allocations.set_allocation(shipment.public_id, cargo.public_id, stage.public_id,
                        {"dimension": "ACTUAL", "quantity": "5", "expected_version": 0}, actor, str(uuid4()))
                    db.session.commit()
            incoming = db.session.get(RouteLeg, legs[0]["id"])
            location_id = incoming.origin_location_id if name == "origin" else db.session.get(RouteLeg, legs[-1]["id"]).destination_location_id if name == "destination" else incoming.destination_location_id
            location = db.session.get(CanonicalLocation, location_id)
            report = None
            if name in {"departure", "next_departure"}:
                milestone = Milestone.query.filter_by(route_leg_id=legs[0 if name == "departure" else 1]["id"], milestone_type="departure").one()
                operations.record_event(shipment.id, milestone.id, {"occurred_at": basis.isoformat()}, actor, str(uuid4()))
            else:
                report, _ = reports.create(shipment.public_id, actor, {"scope": "CARGO", "target_public_id": cargo.public_id,
                    "kind": "LOCATION", "source": "CARRIER_REPORT", "occurred_at": basis.isoformat(),
                    "location": {"canonical_location_public_id": location.public_id},
                    "impacted_cargo_public_ids": [cargo.public_id], "internal_note": "PRIVATE-NOTE"}, str(uuid4()))
                db.session.commit()
            if checkpoint:
                for action, extra in (("arrive", 0), ("complete_processing", 60)):
                    cp = db.session.get(OperationalCheckpoint, checkpoint["id"])
                    routes.checkpoint_command(shipment.id, cp.id, {"expected_version": cp.version,
                        "occurred_at": (basis+timedelta(minutes=extra)).isoformat()}, actor, str(uuid4()), action)
            from backend.route_time_models import OrganizationRouteTime
            for ref in references:
                ref["public_id"] = db.session.get(OrganizationRouteTime, ref["reference_id"]).public_id
            cases[name] = {"shipment": shipment.public_id, "cargo": cargo.public_id, "plan": plan["id"],
                "private_cargo": private_cargo.public_id if private_cargo else None,
                "report": report.event.public_id if report else None, "location": location.public_id,
                "references": references, "basis": basis.isoformat(), "checkpoint": checkpoint["id"] if checkpoint else None}
        fixture.update(p311_cases=cases, p311_accounts=accounts)
        path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
