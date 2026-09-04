"""RG-CARGO-TRANSPORT-ALLOCATION: many-to-many quantity invariants."""
from datetime import datetime, timezone
import pytest

from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.models import ShipmentTransportUnit
from backend.operational_models import OperationalMembership, OperationalShipment
from backend.services import cargo_service
from backend.services import multi_unit_tracking_service as tracking_service
from backend.tests.test_cargo_traceability import traceability_app


def test_rg_cargo_transport_allocation_many_to_many_and_invariants(traceability_app):
    with traceability_app["app"].app_context():
        user = {"id": traceability_app["user"].id}
        membership = db.session.get(OperationalMembership, traceability_app["membership"].id)
        membership.permissions = ["operational_shipment.read", "operational_shipment.create"]
        shipment = db.session.scalar(db.select(OperationalShipment).where(OperationalShipment.public_id == "shipment-active"))
        cargoes = db.session.scalars(db.select(ShipmentCargoItem).where(ShipmentCargoItem.operational_shipment_id == shipment.id).order_by(ShipmentCargoItem.line_number)).all()
        a = ShipmentTransportUnit(operational_shipment_id=shipment.id, operational_organization_id=shipment.organization_id, ownership_scope="TENANT", unit_code="Trailer A", unit_type="truck", is_active=True)
        b = ShipmentTransportUnit(operational_shipment_id=shipment.id, operational_organization_id=shipment.organization_id, ownership_scope="TENANT", unit_code="Trailer B", unit_type="truck", is_active=True)
        db.session.add_all([a, b]); db.session.commit()
        # Multiple cargo items on one transport and one cargo split across two transports.
        first = cargo_service.save_allocation(user, shipment, {"cargo_item_public_id": cargoes[0].public_id, "transport_unit_id": a.id, "allocated_quantity": "1"})
        cargo_service.save_allocation(user, shipment, {"cargo_item_public_id": cargoes[1].public_id, "transport_unit_id": a.id, "allocated_quantity": "2"})
        cargo_service.save_allocation(user, shipment, {"cargo_item_public_id": cargoes[0].public_id, "transport_unit_id": b.id, "allocated_quantity": "1"})
        view = cargo_service.shipment_allocation_view(user, shipment)
        assert len(view["allocations"]) == 3
        assert cargo_service.shipment_item_dict(cargoes[0])["remaining_quantity"] == "0.000000"
        with pytest.raises(cargo_service.CargoError):
            cargo_service.save_allocation(user, shipment, {"cargo_item_public_id": cargoes[1].public_id, "transport_unit_id": b.id, "allocated_quantity": "4"})
        with pytest.raises(cargo_service.CargoError):
            cargo_service.save_allocation(user, shipment, {"cargo_item_public_id": cargoes[1].public_id, "transport_unit_id": b.id, "allocated_quantity": "0"})
        cargo_service.delete_allocation(user, shipment, first.public_id)
        assert cargo_service.shipment_item_dict(cargoes[0])["remaining_quantity"] == "1.000000"


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
        assert unit.tracking_id == tracking.id
        tracking_service.add_update(
            unit, traceability_app["user"].id, status="in_transit",
            occurred_at=datetime.now(timezone.utc), location_text="Bazargan",
            customer_message="Moving", internal_note="checked", is_customer_visible=True,
        )
        db.session.commit()
        payload = tracking_service.build_internal_tracking_for_shipment(shipment)
        assert payload["units"][0]["latest_status"] == "in_transit"
        assert payload["units"][0]["history"][0]["location"]["location_name"] == "Bazargan"
