"""Disposable PostgreSQL proof for canonical event-location truth."""

import os
from datetime import datetime, timezone

import pytest

from backend import create_app
from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import (
    Country, Customer, ExpertUser, ShipmentTransportUnit,
    ShipmentTransportUnitUpdate,
)
from backend.cargo_models import ShipmentCargoTransportAllocation
from backend.operational_models import (
    ExecutionUnit, OperationalEventLocationEvidence, OperationalOrganization,
    OperationalShipment, Project,
)
from backend.services import execution_unit_service
from backend.services.operational_service import OperationalError
from backend.services.tracking_projection_service import project_execution_units


URL = os.environ.get("EVENT_LOCATION_DISPOSABLE_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="requires runner-owned disposable PostgreSQL")


def test_canonical_event_location_journey_immutability_tenant_fence_and_legacy_delta():
    assert "event_location_" in URL and "127.0.0.1" in URL
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL}, skip_startup=True)
    with app.app_context():
        before = (
            db.session.query(ShipmentTransportUnit).count(),
            db.session.query(ShipmentCargoTransportAllocation).count(),
            db.session.query(ShipmentTransportUnitUpdate).count(),
        )
        actor = ExpertUser(username="event-location-pg", password_hash="x", full_name="PG", role="admin")
        org_a = OperationalOrganization(name="Event Location A")
        org_b = OperationalOrganization(name="Event Location B")
        country = Country(code="XZ", name_en="Proof", name_fa="Proof")
        db.session.add_all([actor, org_a, org_b, country]); db.session.flush()
        customer = Customer(
            operational_organization_id=org_a.id, ownership_scope="TENANT",
            first_name="PG", last_name="Customer",
        )
        db.session.add(customer); db.session.flush()
        point_type = LogisticsPointType(
            immutable_code="PORT", fa_name="Port", en_name="Port",
            created_by=actor.id, updated_by=actor.id,
        )
        db.session.add(point_type); db.session.flush()
        project_a = Project(organization_id=org_a.id, primary_customer_id=customer.id,
                            project_code="PG-A", tracking_code="pg-a", created_by_user_id=actor.id)
        project_b = Project(organization_id=org_b.id, primary_customer_id=customer.id,
                            project_code="PG-B", tracking_code="pg-b", created_by_user_id=actor.id)
        db.session.add_all([project_a, project_b]); db.session.flush()
        shipment = OperationalShipment(organization_id=org_a.id, project_id=project_a.id,
            source_type="direct", customer_id=customer.id, created_by_user_id=actor.id)
        point_a = LogisticsPoint(organization_id=org_a.id, immutable_code="A-PORT",
            logistics_point_type_id=point_type.id, fa_name="Original Port", en_name="Original Port EN",
            normalized_name="original port", country_id=country.id, geography_key="XZ|A",
            created_by=actor.id, updated_by=actor.id)
        point_z = LogisticsPoint(organization_id=org_b.id, immutable_code="Z-PORT",
            logistics_point_type_id=point_type.id, fa_name="Foreign Port", en_name="Foreign Port",
            normalized_name="foreign port", country_id=country.id, geography_key="XZ|Z",
            created_by=actor.id, updated_by=actor.id)
        db.session.add_all([shipment, point_a, point_z]); db.session.flush()
        unit = ExecutionUnit(organization_id=org_a.id, project_id=project_a.id,
            operational_shipment_id=shipment.id, unit_code="PG-U", unit_type="road",
            created_by_user_id=actor.id)
        db.session.add(unit); db.session.flush()
        event, created = execution_unit_service.create_event(unit, {
            "expected_version": 1, "event_type": "in_transit", "lifecycle_status": "in_progress",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "location": {"logistics_point_public_id": point_a.public_id},
            "visibility": "customer", "customer_message": "On route",
        }, {"id": actor.id}, "pg-location")
        assert created and event.execution_unit_id == unit.id
        db.session.commit()
        evidence = db.session.query(OperationalEventLocationEvidence).one()
        assert evidence.operational_event_id == event.id
        assert evidence.logistics_point_id == point_a.id
        assert evidence.source_type == "logistics_point" and evidence.source_identity == point_a.public_id
        assert evidence.display_name_snapshot == "Original Port"
        assert evidence.country_code_snapshot == "XZ" and evidence.location_type_snapshot == "PORT"
        assert project_execution_units(org_a.id, [unit.id])[unit.id]["current_location"] == "Original Port"

        point_a.fa_name = "Renamed Master"; point_a.en_name = "Renamed Master EN"; db.session.commit()
        assert evidence.display_name_snapshot == "Original Port"
        assert evidence.logistics_point_id == point_a.id
        assert project_execution_units(org_a.id, [unit.id])[unit.id]["current_location"] == "Original Port"

        with pytest.raises(OperationalError) as denied:
            execution_unit_service.create_event(unit, {
                "expected_version": unit.version, "event_type": "foreign-location",
                "location": {"logistics_point_public_id": point_z.public_id},
            }, {"id": actor.id}, "pg-foreign")
        assert denied.value.status == 404
        db.session.rollback()
        assert db.session.query(OperationalEventLocationEvidence).count() == 1
        after = (
            db.session.query(ShipmentTransportUnit).count(),
            db.session.query(ShipmentCargoTransportAllocation).count(),
            db.session.query(ShipmentTransportUnitUpdate).count(),
        )
        assert after == before
