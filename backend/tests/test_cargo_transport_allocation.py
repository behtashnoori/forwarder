"""RG-CARGO-TRANSPORT-ALLOCATION: many-to-many quantity invariants."""
from datetime import datetime, timezone
import pytest

from backend.cargo_models import ExecutionUnitCargoAllocation, ShipmentCargoItem, ShipmentCargoTransportAllocation
from backend.extensions import db
from backend.models import Customer, ShipmentTransportUnit
from backend.operational_models import ExecutionUnit, OperationalMembership, OperationalShipment
from backend.services import cargo_service
from backend.services import multi_unit_tracking_service as tracking_service
from backend.tests.test_cargo_traceability import traceability_app


def test_legacy_allocation_write_without_exact_execution_mapping_fails_safe(traceability_app):
    with traceability_app["app"].app_context():
        user = {"id": traceability_app["user"].id}
        membership = db.session.get(OperationalMembership, traceability_app["membership"].id)
        membership.permissions = ["operational_shipment.read", "operational_shipment.create"]
        shipment = db.session.scalar(db.select(OperationalShipment).where(OperationalShipment.public_id == "shipment-active"))
        cargoes = db.session.scalars(db.select(ShipmentCargoItem).where(ShipmentCargoItem.operational_shipment_id == shipment.id).order_by(ShipmentCargoItem.line_number)).all()
        a = ShipmentTransportUnit(operational_shipment_id=shipment.id, operational_organization_id=shipment.organization_id, ownership_scope="TENANT", unit_code="Trailer A", unit_type="truck", is_active=True)
        b = ShipmentTransportUnit(operational_shipment_id=shipment.id, operational_organization_id=shipment.organization_id, ownership_scope="TENANT", unit_code="Trailer B", unit_type="truck", is_active=True)
        db.session.add_all([a, b]); db.session.commit()
        with pytest.raises(cargo_service.CargoError, match="NEEDS_DECISION"):
            cargo_service.save_allocation(user, shipment, {"cargo_item_public_id": cargoes[0].public_id, "transport_unit_id": a.id, "allocated_quantity": "1"})
        assert db.session.scalar(db.select(ShipmentCargoTransportAllocation)) is None


def test_legacy_transport_unit_create_never_creates_current_legacy_truth(traceability_app):
    with traceability_app["app"].app_context():
        user = {"id": traceability_app["user"].id}
        membership = db.session.get(OperationalMembership, traceability_app["membership"].id)
        membership.permissions = ["operational_shipment.create"]
        shipment = db.session.scalar(
            db.select(OperationalShipment).where(OperationalShipment.public_id == "shipment-active")
        )
        with pytest.raises(cargo_service.CargoError, match="NEEDS_DECISION"):
            cargo_service.create_transport_unit(user, shipment, {
                "unit_code": "CURRENT-LEGACY-BLOCKED", "unit_type": "truck",
            })
        assert db.session.scalar(
            db.select(ShipmentTransportUnit).where(
                ShipmentTransportUnit.unit_code == "CURRENT-LEGACY-BLOCKED"
            )
        ) is None


def test_rg_direct_operation_transport_tracking_without_request(traceability_app):
    """RG-CARGO-TRANSPORT-ALLOCATION: direct execution has the normal timeline."""
    with traceability_app["app"].app_context():
        shipment = db.session.scalar(db.select(OperationalShipment).where(OperationalShipment.public_id == "shipment-active"))
        assert shipment.source_type == "direct"
        assert shipment.shipment_request_id is None
        unit = ShipmentTransportUnit(
            operational_shipment_id=shipment.id,
            operational_organization_id=shipment.organization_id,
            ownership_scope="TENANT", unit_code="Direct Trailer", unit_type="truck", is_active=True,
        )
        db.session.add(unit)
        tracking = tracking_service.enable_tracking_for_shipment(shipment, traceability_app["user"].id)
        db.session.commit()
        assert unit.tracking_id is None
        with pytest.raises(tracking_service.LegacyWriteMappingError):
            tracking_service.add_update(
                unit, traceability_app["user"].id, status="in_transit",
                occurred_at=datetime.now(timezone.utc), location_text="Bazargan",
                customer_message="Moving", internal_note="checked", is_customer_visible=True,
            )
        payload = tracking_service.build_internal_tracking_for_shipment(shipment)
        assert payload["units"][0]["source"] == "historical_legacy"
        assert payload["units"][0]["latest_status"] == "not_started"


def test_tracking_prefers_canonical_shared_execution_allocation(traceability_app):
    """Canonical cargo allocation wins over a coexisting legacy projection."""
    with traceability_app["app"].app_context():
        user = traceability_app["user"]
        membership = db.session.get(OperationalMembership, traceability_app["membership"].id)
        membership.permissions = ["operational_shipment.read", "operational_shipment.create"]
        shipment = db.session.scalar(
            db.select(OperationalShipment).where(OperationalShipment.public_id == "shipment-active")
        )
        cargo = db.session.scalar(
            db.select(ShipmentCargoItem).where(ShipmentCargoItem.operational_shipment_id == shipment.id)
        )
        cargo.cargo_owner_customer_id = shipment.customer_id
        customer = db.session.get(Customer, shipment.customer_id)
        customer.operational_organization_id = shipment.organization_id
        customer.ownership_scope = "TENANT"
        legacy = ShipmentTransportUnit(
            operational_shipment_id=shipment.id,
            operational_organization_id=shipment.organization_id,
            ownership_scope="TENANT", unit_code="Legacy Trailer", unit_type="truck", is_active=True,
        )
        execution = db.session.scalar(
            db.select(ExecutionUnit).where(ExecutionUnit.operational_shipment_id == shipment.id)
        )
        db.session.add(legacy)
        db.session.flush()
        db.session.add(ShipmentCargoTransportAllocation(
            operational_shipment_id=shipment.id, shipment_cargo_item_id=cargo.id,
            transport_unit_id=legacy.id, allocated_quantity="1",
            created_by=user.id, updated_by=user.id,
        ))
        db.session.add(ExecutionUnitCargoAllocation(
            execution_unit_id=execution.id, shipment_cargo_item_id=cargo.id,
            operational_shipment_id=shipment.id, project_id=shipment.project_id,
            allocated_quantity="2", created_by=user.id, updated_by=user.id,
        ))
        tracking_service.enable_tracking_for_shipment(shipment, user.id)
        db.session.commit()

        payload = tracking_service.build_internal_tracking_for_shipment(shipment)
        canonical = next(unit for unit in payload["units"] if unit.get("source") == "canonical_execution")
        assert canonical["public_id"] == execution.public_id
        assert canonical["allocated_cargo"] == [{
            "cargo_item_public_id": cargo.public_id, "cargo_name": "گیربکس",
            "cargo_owner": "Cargo Owner",
            "allocated_quantity": "2.000000", "uom_symbol": "ea",
        }]
        assert all(not unit["allocated_cargo"] for unit in payload["units"] if unit.get("source") != "canonical_execution")

        # Releasing the canonical fact makes the retained compatibility fact
        # readable again; no mutable tracking allocation is created.
        db.session.delete(db.session.scalar(db.select(ExecutionUnitCargoAllocation)))
        db.session.commit()
        released = tracking_service.build_internal_tracking_for_shipment(shipment)
        assert not any(unit.get("source") == "canonical_execution" for unit in released["units"])
        assert next(unit for unit in released["units"] if unit["id"] == legacy.id)["allocated_cargo"]
