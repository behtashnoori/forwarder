"""P3-09 has no DDL: prove live authorization joins on the actual PostgreSQL head."""
import json
import os
from uuid import uuid4
from decimal import Decimal
import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.engine import make_url
from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import CargoType, UnitOfMeasure, Customer, CustomerGamification, ExpertUser, CaseDocumentFile
from backend.cargo_models import ShipmentCargoItem as Cargo
from backend.operational_models import OperationalShipment, OperationalMembership
from backend.services import customer_entitlement_service as grants, customer_shipment_service as projection
from backend.services import delivery_service as deliveries, document_context_service as contexts, reported_fact_service as reports
from backend.services.operational_service import OperationalError
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime
from backend.tests.test_phase3_customer_shipment import new_cargo

URL = os.environ.get("P3_CUSTOMER_SHIPMENT_POSTGRES_URL", "")
HEAD = "20261008_phase3_cargo_delivery"
pytestmark = pytest.mark.skipif(not URL, reason="requires owned P3_CUSTOMER_SHIPMENT_POSTGRES_URL")


def test_postgresql18_customer_projection_live_joins_union_revoke_and_pages():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_p3_09_customer_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    config = alembic_config(URL); command.upgrade(config, HEAD)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL, "SECRET_KEY": "synthetic-p309"}, skip_startup=True)
    with app.app_context():
        ctx = _seed_runtime(app)
        shipment = OperationalShipment.query.filter_by(public_id=ctx["shipment"]).one()
        membership = OperationalMembership.query.filter_by(user_id=ctx["owner"]).one()
        membership.permissions = [*membership.permissions, "operational_shipment.create"]
        admin = ExpertUser(username="p309-pg-admin", password_hash="unused", full_name="Admin", role="manager", authority="ORGANIZATION_ADMIN", is_active=True)
        b = Customer(company_name="PRIVATE-B", ownership_scope="TENANT", operational_organization_id=shipment.organization_id, status="active")
        a = CustomerGamification(email="p309-a@example.test", phone="09009000001", operational_organization_id=shipment.organization_id)
        ab = CustomerGamification(email="p309-ab@example.test", phone="09009000002", operational_organization_id=shipment.organization_id)
        unentitled = CustomerGamification(email="p309-c@example.test", phone="09009000003", operational_organization_id=shipment.organization_id)
        uom = UnitOfMeasure(immutable_code="P309_CTN", fa_name="کارتن", en_name="Carton", symbol="ctn", measurement_dimension="COUNT", is_active=True)
        kind = CargoType(immutable_code="P309_PART", fa_name="قطعه", en_name="Part", is_active=True)
        db.session.add_all([admin, b, a, ab, unentitled, uom, kind]); db.session.flush()
        db.session.add(OperationalMembership(organization_id=shipment.organization_id, user_id=admin.id, permissions=[]))
        cargo = Cargo(operational_shipment_id=shipment.id, line_number=1, cargo_owner_customer_id=ctx["carrier"], cargo_type_id=kind.id, uom_id=uom.id,
            quantity=100, planned_quantity=100, actual_quantity=100, display_name_snapshot="Own A", cargo_type_code_snapshot=kind.immutable_code,
            cargo_type_fa_snapshot=kind.fa_name, cargo_type_en_snapshot=kind.en_name, uom_code_snapshot=uom.immutable_code,
            uom_symbol_snapshot=uom.symbol, created_by=ctx["owner"], updated_by=ctx["owner"])
        db.session.add(cargo); db.session.flush()
        other = new_cargo(cargo, shipment, b.id, "PRIVATE-CARGO-B"); other.line_number = 2
        db.session.commit()
        for portal, customers in ((a, [ctx["carrier"]]), (ab, [ctx["carrier"], b.id])):
            for customer in customers: grants.grant(shipment.organization_id, admin.id, {"portal_account_public_id": portal.public_id, "customer_id": customer}, str(uuid4()))
        db.session.commit()
        for item in (cargo, other):
            delivered, _ = deliveries.create(shipment.public_id, {"id": ctx["owner"]}, {"cargo_public_id": item.public_id, "quantity": "60" if item == cargo else "5",
                "uom_public_id": uom.public_id, "destination_text": "Own destination" if item == cargo else "PRIVATE-B-DESTINATION",
                "occurred_at": "2026-09-21T08:00:00Z", "expected_version": 0}, str(uuid4()))
            document = CaseDocumentFile(owner_type="SHIPMENT", operational_shipment_id=shipment.id, operational_organization_id=shipment.organization_id,
                is_miscellaneous=True, custom_title="PRIVATE-TITLE", original_filename="PRIVATE-FILENAME.pdf", safe_download_filename="PRIVATE-FILENAME.pdf",
                storage_key=f"synthetic/{item.public_id}.pdf", canonical_extension="pdf", detected_mime_type="application/pdf", file_size_bytes=10,
                sha256_hash="0" * 64, version_number=1, uploaded_by=ctx["owner"])
            db.session.add(document); db.session.flush()
            contexts.attach(shipment, document, ctx["owner"], contexts.prepare(shipment, "DELIVERY", delivered.public_id, "CARGO_OWNER", []))
            reports.create(shipment.public_id, {"id": ctx["owner"]}, {"scope": "CARGO", "target_public_id": item.public_id, "kind": "LOCATION",
                "source": "DRIVER_REPORT", "occurred_at": "2026-09-21T08:00:00Z", "location": {"location_text": "Own location" if item == cargo else "PRIVATE-B-LOCATION"},
                "internal_note": "PRIVATE-NOTE", "impacted_cargo_public_ids": [item.public_id]}, str(uuid4()))
            db.session.commit()
        for index in range(22):
            row = OperationalShipment(organization_id=shipment.organization_id, source_type="direct", customer_id=b.id,
                created_by_user_id=ctx["owner"], primary_responsible_expert_id=ctx["owner"])
            db.session.add(row); db.session.flush(); new_cargo(cargo, row, b.id, "PRIVATE-B-ONLY")
        db.session.commit()
        before = (OperationalShipment.query.count(), cargo.actual_quantity, shipment.version)
        value = projection.detail(a, shipment.public_id)
        assert len(value["cargo"]) == len(value["documents"]["items"]) == len(value["deliveries"]["items"]) == len(value["reported_locations"]) == 1
        assert Decimal(value["cargo"][0]["remaining"]) == 40 and "PRIVATE" not in json.dumps(value)
        assert projection.listing(a)["pagination"]["total"] == 1
        assert projection.listing(a, search="PRIVATE-B")["items"] == []
        assert len(projection.detail(ab, shipment.public_id)["cargo"]) == 2
        assert projection.listing(ab)["pagination"]["total"] == 23
        assert len(projection.listing(ab, page=2)["items"]) == 3
        assert projection.listing(unentitled)["pagination"]["total"] == 0
        for portal in (a, ab):
            grant = next(g for g in grants.configuration(shipment.organization_id, admin.id)["grants"] if g["portal_account_public_id"] == portal.public_id and g["customer_id"] == ctx["carrier"])
            grants.revoke(shipment.organization_id, admin.id, grant["public_id"])
        db.session.commit()
        with pytest.raises(OperationalError) as denied: projection.detail(a, shipment.public_id)
        assert denied.value.status == 404 and projection.listing(a)["items"] == []
        assert [c["public_id"] for c in projection.detail(ab, shipment.public_id)["cargo"]] == [other.public_id]
        assert before == (OperationalShipment.query.count(), cargo.actual_quantity, shipment.version)
        db.session.remove(); db.engine.dispose()
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    engine.dispose()
