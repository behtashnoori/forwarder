from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend import create_app
from backend.cargo_models import CargoCatalogItem, ShipmentCargoItem
from backend.extensions import db
from backend.models import CargoType, Customer, ExpertUser, UnitOfMeasure
from backend.operational_models import (
    ExecutionUnit,
    OperationalEvent,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
)
from backend.services import cargo_service
from backend.services.operational_service import OperationalError


@pytest.fixture()
def traceability_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        user = ExpertUser(username="cargo-trace", password_hash="unused", full_name="Cargo Admin", role="admin")
        other_user = ExpertUser(username="cargo-other", password_hash="unused", full_name="Other Admin", role="admin")
        org = OperationalOrganization(name="Cargo Org")
        other_org = OperationalOrganization(name="Other Cargo Org")
        db.session.add_all([user, other_user, org, other_org])
        db.session.flush()
        membership = OperationalMembership(organization_id=org.id, user_id=user.id, permissions=["operational_shipment.read"])
        other_membership = OperationalMembership(organization_id=other_org.id, user_id=other_user.id, permissions=["operational_shipment.read"])
        customer = Customer(first_name="Cargo", last_name="Owner")
        cargo_type = CargoType(public_id="cargo-type", immutable_code="GENERAL", fa_name="عمومی", en_name="General", display_order=1, is_active=True, version=1)
        uom = UnitOfMeasure(public_id="uom-ea", immutable_code="EA", fa_name="عدد", en_name="Each", display_order=1, is_active=True, version=1, symbol="ea", measurement_dimension="COUNT")
        db.session.add_all([membership, other_membership, customer, cargo_type, uom])
        db.session.flush()
        project = Project(organization_id=org.id, primary_customer_id=customer.id, project_code="PRJ-CARGO", created_by_user_id=user.id)
        db.session.add(project)
        db.session.flush()
        active = OperationalShipment(public_id="shipment-active", organization_id=org.id, project_id=project.id, source_type="direct", customer_id=customer.id, lifecycle_status="in_progress", created_by_user_id=user.id)
        terminal = OperationalShipment(public_id="shipment-terminal", organization_id=org.id, project_id=project.id, source_type="direct", customer_id=customer.id, lifecycle_status="completed", created_by_user_id=user.id)
        no_location = OperationalShipment(public_id="shipment-no-location", organization_id=org.id, project_id=project.id, source_type="direct", customer_id=customer.id, lifecycle_status="planned", created_by_user_id=user.id)
        catalog = CargoCatalogItem(public_id="catalog-gearbox", organization_id=org.id, immutable_code="GEARBOX", fa_name="گیربکس", en_name="Gearbox", cargo_type=cargo_type, default_uom=uom, created_by=user.id, updated_by=user.id)
        foreign_catalog = CargoCatalogItem(public_id="catalog-foreign", organization_id=other_org.id, immutable_code="GEARBOX", fa_name="گیربکس", en_name="Gearbox", cargo_type=cargo_type, default_uom=uom, created_by=other_user.id, updated_by=other_user.id)
        db.session.add_all([active, terminal, no_location, catalog, foreign_catalog])
        db.session.flush()
        for number, shipment, quantity in ((1, active, "2"), (2, active, "3"), (1, terminal, "4"), (1, no_location, "5")):
            db.session.add(ShipmentCargoItem(operational_shipment_id=shipment.id, line_number=number, catalog_item=catalog, cargo_type=cargo_type, quantity=quantity, uom=uom, display_name_snapshot="گیربکس", cargo_type_code_snapshot="GENERAL", cargo_type_fa_snapshot="عمومی", cargo_type_en_snapshot="General", uom_code_snapshot="EA", uom_symbol_snapshot="ea", created_by=user.id, updated_by=user.id))
        unit = ExecutionUnit(project_id=project.id, operational_shipment_id=active.id, unit_code="U-1", unit_type="truck", latest_checkpoint="Older checkpoint", last_event_at=datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc), created_by_user_id=user.id)
        terminal_unit = ExecutionUnit(project_id=project.id, operational_shipment_id=terminal.id, unit_code="U-2", unit_type="truck", latest_checkpoint="Warehouse", last_event_at=datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc), created_by_user_id=user.id)
        db.session.add_all([unit, terminal_unit])
        db.session.flush()
        db.session.add(OperationalEvent(project_id=project.id, execution_unit_id=unit.id, event_type="checkpoint", checkpoint_text="Border gate", occurred_at=datetime(2026, 8, 20, 9, 25, tzinfo=timezone.utc), actor_user_id=user.id, idempotency_key="cargo-location", request_hash="hash"))
        db.session.commit()
        yield {"app": app, "user": user, "other_user": other_user, "membership": membership}
        db.session.remove()
        db.drop_all()


def test_catalog_usage_preserves_lines_counts_filters_and_canonical_location(traceability_app):
    with traceability_app["app"].app_context():
        result = cargo_service.catalog_shipment_usage({"id": traceability_app["user"].id}, "catalog-gearbox", {})
        assert result["summary"] == {"shipment_count": 3, "active_shipment_count": 2}
        assert len(result["items"]) == 4
        active = [row for row in result["items"] if row["status"] == "in_progress"]
        assert [row["quantity"] for row in active] == ["2.000000", "3.000000"]
        assert {row["uom"] for row in active} == {"ea"}
        assert active[0]["location_source"] == "operational_event"
        assert active[0]["current_location"] == "Border gate"
        assert active[0]["latest_event_at"] == "2026-08-20T09:25:00Z"
        terminal = next(row for row in result["items"] if row["status"] == "completed")
        assert terminal["location_source"] == "unavailable"
        assert terminal["current_location"] is None
        assert terminal["location_state"] == "UNAVAILABLE"
        assert terminal["reconciliation_health"] == "CACHE_CONFLICT"
        missing = next(row for row in result["items"] if row["operational_shipment_public_id"] == "shipment-no-location")
        assert missing["location_source"] == "unavailable" and missing["current_location"] is None
        assert cargo_service.catalog_shipment_usage({"id": traceability_app["user"].id}, "catalog-gearbox", {"active_only": "true"})["summary"]["shipment_count"] == 2


def test_catalog_usage_is_empty_cross_tenant_safe_and_requires_active_membership(traceability_app):
    with traceability_app["app"].app_context():
        user = {"id": traceability_app["user"].id}
        assert cargo_service.catalog_shipment_usage(user, "catalog-gearbox", {"status": "cancelled"})["items"] == []
        with pytest.raises(cargo_service.CargoError) as hidden:
            cargo_service.catalog_shipment_usage(user, "catalog-foreign", {})
        assert hidden.value.status == 404
        membership = db.session.get(OperationalMembership, traceability_app["membership"].id)
        membership.permissions = []
        db.session.commit()
        with pytest.raises(OperationalError):
            cargo_service.catalog_shipment_usage(user, "catalog-gearbox", {})
        membership.permissions = ["operational_shipment.read"]
        membership.is_active = False
        db.session.commit()
        with pytest.raises(OperationalError):
            cargo_service.catalog_shipment_usage(user, "catalog-gearbox", {})


def test_traceability_index_is_additive_and_reversible():
    migration = (Path(__file__).parents[1] / "migrations" / "versions" / "20260829_cargo_traceability_index.py").read_text(encoding="utf-8")
    assert 'down_revision = "20260828_referral_state_compat"' in migration
    assert "ix_shipment_cargo_item_catalog_shipment" in migration
    assert "create_index" in migration and "drop_index" in migration
    assert "op.execute" not in migration
