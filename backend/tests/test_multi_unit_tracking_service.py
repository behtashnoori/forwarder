from datetime import datetime, timedelta

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Country, Customer, ExpertUser, ShipmentRequest, TrackingLocationReference
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.operational_models import OperationalOrganization, OperationalShipment, Project
from backend.services import execution_unit_service
from backend.services.tracking_projection_service import project_execution_units
from backend.tests.canonical_tracking_fixture import (
    append_event, canonical_tracking_summary, execution_unit,
)
from backend.services.multi_unit_tracking_service import (
    TrackingValidationError,
    disable_tracking,
    enable_tracking,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed_request(status="won", tracking_code="trk-production-safe"):
    organization = OperationalOrganization(name="Tracking Test Organization")
    actor = ExpertUser(
        username="tracker",
        password_hash="not-used",
        full_name="Tracking Operator",
        role="expert",
    )
    req = ShipmentRequest(
        ownership_scope="TENANT",
        contact_phone="09120000000",
        status=status,
        status_request_status="new",
        tracking_code=tracking_code,
    )
    customer = Customer(first_name="Tracking", last_name="Customer")
    db.session.add_all([actor, organization, customer])
    db.session.flush()
    req.operational_organization_id = organization.id
    project = Project(
        organization_id=organization.id, primary_customer_id=customer.id,
        project_code=f"TRACK-{tracking_code}", tracking_code=tracking_code,
        created_by_user_id=actor.id,
    )
    db.session.add_all([req, project])
    db.session.flush()
    shipment = OperationalShipment(
        organization_id=organization.id, project_id=project.id,
        source_type="direct", customer_id=customer.id, created_by_user_id=actor.id,
        primary_responsible_expert_id=actor.id,
    )
    db.session.add(shipment)
    db.session.commit()
    return actor, req


def _project(req):
    return db.session.scalar(db.select(Project).where(Project.tracking_code == req.tracking_code))


def _shipment(req):
    return db.session.scalar(
        db.select(OperationalShipment).join(Project).where(Project.tracking_code == req.tracking_code)
    )


def test_enablement_requires_accepted_request_and_tracking_code(app):
    with app.app_context():
        actor, req = _seed_request(status="in_progress")
        with pytest.raises(TrackingValidationError, match="accepted"):
            enable_tracking(req, actor.id)
        req.status = "won"
        req.tracking_code = None
        with pytest.raises(TrackingValidationError, match="tracking code"):
            enable_tracking(req, actor.id)


def test_canonical_logistics_point_snapshots_are_tenant_safe_and_immutable(app):
    with app.app_context():
        actor, req = _seed_request()
        country = Country(code="IR", name_en="Iran", name_fa="ایران")
        point_type = LogisticsPointType(
            immutable_code="WAREHOUSE", fa_name="انبار", en_name="Warehouse",
            created_by=actor.id, updated_by=actor.id,
        )
        db.session.add_all([country, point_type])
        db.session.flush()
        point = LogisticsPoint(
            organization_id=req.operational_organization_id,
            immutable_code="TEH-WH-1", logistics_point_type_id=point_type.id,
            fa_name="انبار تهران", en_name="Tehran Warehouse",
            normalized_name="انبار تهران", country_id=country.id,
            geography_key="IR|-|-", created_by=actor.id, updated_by=actor.id,
        )
        legacy = TrackingLocationReference(
            internal_key="compat", name_fa="قدیمی", country_code="IR",
            location_type="other", reference_status="internal_reference",
        )
        db.session.add_all([point, legacy])
        db.session.commit()
        enable_tracking(req, actor.id)
        unit = execution_unit(_project(req), actor.id, shipment=_shipment(req), unit_code="U-1", unit_type="truck")
        row = append_event(
            unit, actor.id, status="in_transit",
            occurred_at=datetime.utcnow() - timedelta(minutes=1),
            logistics_point_public_id=point.public_id,
        )
        db.session.commit()
        evidence = row.location_evidence
        assert evidence.logistics_point_id == point.id
        assert evidence.display_name_snapshot == "انبار تهران"
        assert evidence.name_en_snapshot == "Tehran Warehouse"
        assert evidence.location_type_snapshot == "WAREHOUSE"
        assert execution_unit_service.timeline(unit, {}, customer=False)["data"][0]["location"]["source_type"] == "logistics_point"
        point.fa_name = "نام جدید"
        point.is_active = False
        db.session.commit()
        assert execution_unit_service.timeline(unit, {}, customer=False)["data"][0]["location"]["display_name"] == "انبار تهران"
        with pytest.raises(Exception, match="[Aa]ctive logistics point not found"):
            append_event(
                unit, actor.id, status="in_transit",
                occurred_at=datetime.utcnow() - timedelta(seconds=1),
                logistics_point_public_id=point.public_id,
            )
        point.is_active = True
        with pytest.raises(Exception, match="exactly one"):
            append_event(
                unit, actor.id, status="in_transit",
                occurred_at=datetime.utcnow() - timedelta(seconds=1),
                logistics_point_public_id=point.public_id, location_text="manual",
            )
        with pytest.raises(Exception, match="exactly one"):
            append_event(
                unit, actor.id, status="in_transit",
                occurred_at=datetime.utcnow() - timedelta(seconds=1),
                logistics_point_public_id=point.public_id, location_reference_id=legacy.id,
            )

def test_public_projection_aggregates_partial_delivery_and_hides_private_data(app):
    with app.app_context():
        actor, req = _seed_request()
        now = datetime(2026, 7, 15, 12, 0, 0)
        tracking = enable_tracking(req, actor.id, now=now - timedelta(hours=3))
        truck = execution_unit(
            _project(req), actor.id, shipment=_shipment(req),
            unit_code="TRUCK-01",
            unit_type="truck",
            display_name="Truck 1",
            vehicle_reference="  IR 12 345  ",
        )
        container = execution_unit(
            _project(req), actor.id, shipment=_shipment(req),
            unit_code="CONT-02",
            unit_type="container",
            display_name="Container 2",
            sort_order=1,
        )
        append_event(
            truck,
            actor.id,
            status="delivered",
            location_text="Tehran",
            customer_message="Delivered safely",
            internal_note="private operations detail",
            occurred_at=now - timedelta(hours=1),
        )
        append_event(
            container,
            actor.id,
            status="in_transit",
            location_text="Qom",
            customer_message="On route",
            occurred_at=now - timedelta(hours=2),
        )
        append_event(
            container,
            actor.id,
            status="delayed",
            location_text="Private depot",
            internal_note="not for customer",
            customer_visible=False,
            occurred_at=now - timedelta(minutes=30),
        )
        db.session.commit()

        payload = canonical_tracking_summary(_project(req))
        assert payload["aggregate_status"] == "partially_delivered"
        assert payload["summary"]["total_units"] == 2
        assert payload["summary"]["delivered"] == 1
        assert project_execution_units(req.operational_organization_id, [truck.id])[truck.id]["latest_event_at"] == "2026-07-15T11:00:00Z"
        public_truck = execution_unit_service.timeline(truck, {}, customer=True)
        public_container = execution_unit_service.timeline(container, {}, customer=True)
        assert public_truck["data"][0]["occurred_at"] == "2026-07-15T11:00:00Z"
        assert public_container["data"][0]["event_type"] == "in_transit"
        assert truck.vehicle_reference == "IR 12 345"
        assert "internal_note" not in str(public_truck)
        assert "Private depot" not in str(public_container)


def test_disable_tracking_retains_history_but_removes_public_projection(app):
    with app.app_context():
        actor, req = _seed_request()
        tracking = enable_tracking(req, actor.id)
        unit = execution_unit(_project(req), actor.id, shipment=_shipment(req), unit_code="W-1", unit_type="wagon")
        append_event(
            unit,
            actor.id,
            status="arrived_destination",
            location_text="Rail terminal",
            occurred_at=datetime.utcnow() - timedelta(minutes=1),
        )
        db.session.commit()

        disable_tracking(tracking, actor.id)
        db.session.commit()

        assert tracking.is_enabled is False
        assert execution_unit_service.timeline(unit, {}, customer=False)["meta"]["total"] == 1


def test_aggregate_contract_precedence_counts_and_tie_breaking(app):
    with app.app_context():
        actor, req = _seed_request()
        now = datetime(2026, 7, 15, 12, 0, 0)
        tracking = enable_tracking(req, actor.id, now=now - timedelta(hours=4))
        units = [execution_unit(_project(req), actor.id, shipment=_shipment(req), unit_code=f"U-{index}", unit_type="other") for index in range(4)]
        db.session.flush()

        assert canonical_tracking_summary(_project(req))["aggregate_status"] == "not_started"
        append_event(units[0], actor.id, status="delivered", occurred_at=now - timedelta(hours=2))
        append_event(units[1], actor.id, status="in_transit", occurred_at=now - timedelta(hours=1))
        assert canonical_tracking_summary(_project(req))["aggregate_status"] == "partially_delivered"
        append_event(units[2], actor.id, status="delayed", occurred_at=now - timedelta(minutes=30))
        assert canonical_tracking_summary(_project(req))["aggregate_status"] == "attention_required"

        same_time = now - timedelta(minutes=10)
        in_transit = append_event(units[2], actor.id, status="in_transit", occurred_at=same_time)
        delivered = append_event(units[2], actor.id, status="delivered", occurred_at=same_time)
        # Some supported databases store these recording instants at equal
        # precision. Append order is the explicit final recency rule.
        delivered.recorded_at = in_transit.recorded_at
        db.session.flush()
        db.session.expire_all()
        payload = canonical_tracking_summary(_project(req))
        projections = [
            project_execution_units(req.operational_organization_id, [units[2].id])[units[2].id]
            for _ in range(3)
        ]
        assert {row["lifecycle_status"] for row in projections} == {"delivered"}
        assert payload["summary"] == {
            "total_units": 4, "without_updates": 1, "not_started": 0, "loading": 0,
            "in_transit": 1, "delayed": 0, "arrived": 0, "delivered": 2, "cancelled": 0,
        }
        assert project_execution_units(req.operational_organization_id, [units[2].id])[units[2].id]["latest_event_at"] == "2026-07-15T11:50:00Z"

        append_event(units[3], actor.id, status="delivered", occurred_at=now - timedelta(minutes=5))
        append_event(units[1], actor.id, status="delivered", occurred_at=now - timedelta(minutes=4))
        assert canonical_tracking_summary(_project(req))["aggregate_status"] == "completed"


def test_internal_projection_serializes_canonical_tracking_instants_as_explicit_utc(app):
    with app.app_context():
        actor, req = _seed_request()
        now = datetime(2026, 8, 20, 9, 26, 0)
        tracking = enable_tracking(req, actor.id, now=datetime(2026, 8, 20, 9, 20, 0))
        unit = execution_unit(_project(req), actor.id, shipment=_shipment(req), unit_code="THR-01", unit_type="truck")
        update = append_event(
            unit,
            actor.id,
            status="in_transit",
            occurred_at=datetime(2026, 8, 20, 9, 25, 0),
        )
        db.session.flush()

        payload = project_execution_units(req.operational_organization_id, [unit.id])[unit.id]
        assert update.occurred_at.isoformat() == "2026-08-20T09:25:00+00:00"
        assert tracking.enabled_at == datetime(2026, 8, 20, 9, 20, 0)
        assert payload["latest_event_at"] == "2026-08-20T09:25:00Z"


def test_all_cancelled_and_inactive_units_are_derived_correctly(app):
    with app.app_context():
        actor, req = _seed_request()
        now = datetime(2026, 7, 15, 12, 0, 0)
        tracking = enable_tracking(req, actor.id)
        first = execution_unit(_project(req), actor.id, shipment=_shipment(req), unit_code="C-1", unit_type="container")
        second = execution_unit(_project(req), actor.id, shipment=_shipment(req), unit_code="C-2", unit_type="container")
        ignored = execution_unit(_project(req), actor.id, shipment=_shipment(req), unit_code="C-3", unit_type="container")
        ignored.is_active = False
        for unit in (first, second):
            append_event(unit, actor.id, status="cancelled", occurred_at=now - timedelta(minutes=1))
        payload = canonical_tracking_summary(_project(req))
        assert payload["aggregate_status"] == "cancelled"
        assert payload["summary"]["total_units"] == 2
