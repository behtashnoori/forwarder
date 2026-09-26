"""Owned P3-09 shared Shipment, real grants and exact private document bytes."""
import io
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
from werkzeug.datastructures import FileStorage

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import create_app
from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem as Cargo
from backend.models import Country, Customer, CustomerGamification, ExpertUser, InternationalCity
from backend.operational_models import CanonicalLocation, OperationalShipment, RouteCargoDestination, RouteLeg, RouteStageExecution
from backend.security import security
from backend.services import customer_entitlement_service as grants, delivery_service as deliveries
from backend.services import reported_fact_service as reports, shipment_document_service as documents, cargo_allocation_service as allocations
from scripts.uat.seed_phase3_cargo_delivery_e2e import main as seed_delivery

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


def main():
    seed_delivery()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        shipment = OperationalShipment.query.filter_by(public_id=fixture["p304_shipment"]).one()
        a = Cargo.query.filter_by(public_id=fixture["p305_cargo"]).one()
        b = Cargo.query.filter_by(public_id=fixture["p308_cargo_b"]).one()
        admin = ExpertUser.query.filter_by(username="shared_transport_e2e_admin").one()
        accounts = []
        for index, name in enumerate(("a", "b", "c", "ab")):
            row = CustomerGamification(email=f"p309-{name}@example.test", phone=f"0900900000{index}", first_name="مشتری", last_name=name,
                password_hash=security.hash_password(os.environ["FORWARDER_E2E_PASSWORD"]),
                operational_organization_id=shipment.organization_id, is_email_verified=True)
            db.session.add(row); accounts.append(row)
        db.session.flush()
        # Explicit synthetic public geography; the inherited fixture deliberately
        # has only internal snapshots, which the Customer must never fall back to.
        country = Country(name_en="P309 synthetic", name_fa="کشور آزمایشی", code="ZZ")
        db.session.add(country); db.session.flush()
        for source_id in (994001, 994002, 994003):
            canonical = CanonicalLocation.query.filter_by(source_type="international_city", source_id=source_id).one()
            db.session.add(InternationalCity(id=source_id, name_en=f"P309-{source_id}",
                name_fa=canonical.display_name, country_id=country.id))
        db.session.add(InternationalCity(id=994004, name_en="P309-B-destination",
            name_fa="مقصد اختصاصی مشتری دوم", country_id=country.id))
        destination_b = CanonicalLocation(source_type="international_city", source_id=994004,
            location_type="city", display_name="PRIVATE-B-SNAPSHOT", country_code="ZZ")
        db.session.add(destination_b); db.session.flush()
        rail = db.session.get(RouteLeg, fixture["p304_rail_leg"])
        branch_b = RouteLeg(route_plan_id=rail.route_plan_id, sequence_number=3,
            parent_route_leg_id=fixture["p304_road_leg"], origin_location_id=rail.origin_location_id,
            destination_location_id=destination_b.id, origin_snapshot=rail.origin_snapshot,
            destination_snapshot={"display_name": "PRIVATE-B-SNAPSHOT"}, transport_mode="rail",
            planned_departure=rail.planned_departure, planned_arrival=rail.planned_arrival, status="planned")
        db.session.add(branch_b); db.session.flush()
        for portal, owners in ((accounts[0], [a.cargo_owner_customer_id]), (accounts[1], [b.cargo_owner_customer_id]),
                              (accounts[3], [a.cargo_owner_customer_id, b.cargo_owner_customer_id])):
            for owner in owners: grants.grant(shipment.organization_id, admin.id, {"portal_account_public_id": portal.public_id, "customer_id": owner}, str(uuid4()))
        db.session.add(RouteCargoDestination(route_plan_id=fixture["p304_plan"], operational_shipment_id=shipment.id,
            shipment_cargo_item_id=b.id, destination_route_leg_id=branch_b.id, created_by_user_id=shipment.primary_responsible_expert_id))
        db.session.commit()
        actor = {"id": shipment.primary_responsible_expert_id}
        for item, stage in ((a, fixture["p305_first"]), (b, fixture["p305_second"])):
            allocations.set_allocation(shipment.public_id, item.public_id, stage,
                {"dimension": "ACTUAL", "quantity": str(item.actual_quantity), "expected_version": 0}, actor, str(uuid4()))
            unit = RouteStageExecution.query.filter_by(public_id=stage).one().execution_unit
            unit.lifecycle_status = "in_progress"
        db.session.commit()
        payload = {"cargo_public_id": a.public_id, "quantity": "60", "uom_public_id": a.uom.public_id,
            "destination_text": "انبار مشتری الف", "occurred_at": "2026-09-21T08:00:00Z", "expected_version": 0}
        first, _ = deliveries.create(shipment.public_id, actor, payload, str(uuid4())); db.session.commit()
        deliveries.create(shipment.public_id, actor, {**payload, "quantity": "35"}, str(uuid4())); db.session.commit()
        correction, _ = deliveries.create(shipment.public_id, actor, {**payload, "quantity": "58", "expected_version": 1,
            "corrects_public_id": first.public_id, "reason": "PRIVATE-CORRECTION-CAUSE"}, str(uuid4())); db.session.commit()
        doc_ids = {}
        for name, context, target in (("a", "CARGO", a.public_id), ("b", "CARGO", b.public_id), ("delivery", "DELIVERY", correction.public_id)):
            file = FileStorage(stream=io.BytesIO(PDF + f"\n%{name}\n".encode()), filename=f"PRIVATE-{name}.pdf", content_type="application/pdf")
            doc = documents.upload(shipment, actor, file, "PRIVATE-DOCUMENT-TITLE", None, str(uuid4()),
                context_type=context, target_public_id=target, visibility="CARGO_OWNER")
            doc_ids[name] = doc.public_id
        for item, text, stage in ((a, "نزدیک مرز؛ کالای شما در مسیر است", fixture["p305_first"]), (b, "PRIVATE-B-LOCATION", fixture["p305_second"])):
            unit = RouteStageExecution.query.filter_by(public_id=stage).one().execution_unit
            reports.create(shipment.public_id, actor, {"scope": "EXECUTION_UNIT", "target_public_id": unit.public_id,
                "kind": "LOCATION", "source": "CARRIER_REPORT", "occurred_at": "2026-09-21T08:00:00Z",
                "location": {"location_text": text}, "customer_message": text, "internal_note": "PRIVATE-INTERNAL-NOTE",
                "impacted_cargo_public_ids": [item.public_id]}, str(uuid4()))
            db.session.commit()
        fixture.update(p309_accounts={name: {"public_id": row.public_id, "email": row.email} for name, row in zip(("a", "b", "c", "ab"), accounts)},
            p309_documents=doc_ids, p309_customer_a=a.cargo_owner_customer_id, p309_customer_b=b.cargo_owner_customer_id,
            p309_customer_a_label=db.session.get(Customer, a.cargo_owner_customer_id).company_name)
        db.session.remove()
    path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__": main()
