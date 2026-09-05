"""Step 2A dual route-endpoint identity contracts."""
from __future__ import annotations

import pytest

from backend.extensions import db
from backend.global_logistics_point_models import (
    GlobalLogisticsPoint,
    OrganizationGlobalLogisticsPointAdoption,
)
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import Country
from backend.operational_models import RouteLeg, RoutePlan
from backend.services import operational_service as operations
from backend.services import route_orchestration_service as routes
from backend.tests.test_operational_vertical_slice import (
    _direct_payload,
    _payload,
    _user,
    operational_app,
)


def _facility_foundation(app):
    ids = app.config["phase1a"]
    country = Country(code="XZ", name_en="Testland", name_fa="آزمایشستان")
    point_type = LogisticsPointType(
        immutable_code="STEP2A_WAREHOUSE",
        fa_name="انبار",
        en_name="Warehouse",
        created_by=ids["user"],
        updated_by=ids["user"],
    )
    db.session.add_all([country, point_type])
    db.session.flush()
    return country, point_type


def _point(app, country, point_type, code, name, *, organization="org", province="origin", active=True, global_point=None, adoption=None):
    ids = app.config["phase1a"]
    point = LogisticsPoint(
        organization_id=ids[organization],
        global_logistics_point_id=global_point.id if global_point else None,
        global_adoption_id=adoption.id if adoption else None,
        immutable_code=code,
        logistics_point_type_id=point_type.id,
        fa_name=name,
        en_name=name,
        normalized_name=name.lower(),
        country_id=country.id,
        province_id=ids[province] if province else None,
        geography_key=f"province:{ids[province]}" if province else f"country:{country.id}",
        short_address=f"Historical address for {name}",
        is_active=active,
        created_by=ids["user"],
        updated_by=ids["user"],
    )
    db.session.add(point)
    db.session.flush()
    return point


def _facility_payload(app, origin, destination):
    payload = _direct_payload(app)
    payload["route"]["origin"] = {
        "source_type": "logistics_point",
        "source_id": origin.public_id,
    }
    payload["route"]["destination"] = {
        "source_type": "logistics_point",
        "source_id": destination.public_id,
    }
    return payload


def test_private_facilities_persist_dual_identity_allow_same_geography_and_serialize(operational_app):
    with operational_app.app_context():
        country, point_type = _facility_foundation(operational_app)
        origin = _point(operational_app, country, point_type, "PRIVATE-A", "Private A")
        destination = _point(operational_app, country, point_type, "PRIVATE-B", "Private B")
        payload = _facility_payload(operational_app, origin, destination)
        shipment, created = operations.create_direct(
            payload,
            _user(operational_app),
            "step2a-private",
        )
        replay, recreated = operations.create_direct(
            payload,
            _user(operational_app),
            "step2a-private",
        )
        assert created and not recreated and replay.id == shipment.id

        leg = RouteLeg.query.one()
        assert leg.origin_location_id == leg.destination_location_id
        assert (leg.origin_logistics_point_id, leg.destination_logistics_point_id) == (
            origin.id,
            destination.id,
        )
        assert leg.origin_snapshot["facility"]["logistics_point_public_id"] == origin.public_id
        assert leg.destination_snapshot["facility"]["logistics_point_public_id"] == destination.public_id

        graph = operations.shipment_graph(shipment)
        serialized = graph["route_leg"]
        assert serialized["origin_location_id"] == leg.origin_location_id
        assert serialized["destination_location_id"] == leg.destination_location_id
        assert serialized["origin_logistics_point_id"] == origin.id
        assert serialized["destination_logistics_point_id"] == destination.id
        assert serialized["origin"]["facility"] == leg.origin_snapshot["facility"]
        route_leg_view = routes._serialize_leg(leg)
        assert route_leg_view["origin_location_id"] == leg.origin_location_id
        assert route_leg_view["origin_logistics_point_id"] == origin.id
        assert route_leg_view["origin"]["facility"] == leg.origin_snapshot["facility"]


def test_exact_same_facility_endpoint_is_rejected_atomically(operational_app):
    with operational_app.app_context():
        country, point_type = _facility_foundation(operational_app)
        point = _point(operational_app, country, point_type, "SAME", "Same endpoint")
        with pytest.raises(operations.OperationalError) as error:
            operations.create_direct(
                _facility_payload(operational_app, point, point),
                _user(operational_app),
                "step2a-same",
            )
        assert error.value.code == "INVALID_ROUTE_TIMELINE"
        assert RouteLeg.query.count() == 0


@pytest.mark.parametrize("failure", ["cross_tenant", "inactive", "invalid_projection"])
def test_new_facility_selection_fails_closed_before_persistence(operational_app, failure):
    with operational_app.app_context():
        country, point_type = _facility_foundation(operational_app)
        valid = _point(operational_app, country, point_type, "VALID", "Valid", province="destination")
        if failure == "cross_tenant":
            selected = _point(
                operational_app, country, point_type, "OTHER", "Other tenant",
                organization="other_org",
            )
            expected = "RESOURCE_NOT_FOUND"
        elif failure == "inactive":
            selected = _point(
                operational_app, country, point_type, "INACTIVE", "Inactive", active=False,
            )
            expected = "LOCATION_MAPPING_REQUIRED"
        else:
            country.is_active = False
            selected = _point(
                operational_app, country, point_type, "UNMAPPED", "Unmapped label and address",
                province=None,
            )
            expected = "LOCATION_MAPPING_REQUIRED"
        db.session.commit()

        with pytest.raises(operations.OperationalError) as error:
            operations.create_direct(
                _facility_payload(operational_app, selected, valid),
                _user(operational_app),
                f"step2a-{failure}",
            )
        assert error.value.code == expected
        assert RouteLeg.query.count() == 0


def test_adopted_global_point_persists_only_tenant_fk_and_keeps_provenance(operational_app):
    with operational_app.app_context():
        ids = operational_app.config["phase1a"]
        country, point_type = _facility_foundation(operational_app)
        global_point = GlobalLogisticsPoint(
            immutable_code="GLOBAL-STEP2A",
            logistics_point_type_id=point_type.id,
            fa_name="Global facility",
            en_name="Global facility",
            normalized_name="global facility",
            country_id=country.id,
            province_id=ids["origin"],
            geography_key=f"province:{ids['origin']}",
            facility_identity_key="global-step2a",
            lifecycle_status="ACTIVE",
            verification_status="VERIFIED",
            created_by=ids["user"],
            updated_by=ids["user"],
        )
        db.session.add(global_point)
        db.session.flush()
        adoption = OrganizationGlobalLogisticsPointAdoption(
            organization_id=ids["org"],
            global_logistics_point_id=global_point.id,
            status="ACTIVE",
            created_by=ids["user"],
            updated_by=ids["user"],
        )
        db.session.add(adoption)
        db.session.flush()
        adopted = _point(
            operational_app, country, point_type, "ADOPTED", "Tenant adopted",
            global_point=global_point, adoption=adoption,
        )
        destination = _point(
            operational_app, country, point_type, "PRIVATE-D", "Private destination",
            province="destination",
        )

        operations.create_direct(
            _facility_payload(operational_app, adopted, destination),
            _user(operational_app),
            "step2a-adopted",
        )
        leg = RouteLeg.query.one()
        assert leg.origin_logistics_point_id == adopted.id
        assert not hasattr(leg, "origin_global_logistics_point_id")
        assert leg.origin_snapshot["facility"]["global_provenance"] == {
            "public_id": global_point.public_id,
            "immutable_code": global_point.immutable_code,
        }


def test_replan_copies_persisted_identity_and_snapshot_after_master_change(operational_app):
    with operational_app.app_context():
        country, point_type = _facility_foundation(operational_app)
        origin = _point(operational_app, country, point_type, "REPLAN-A", "Original facility")
        destination = _point(
            operational_app, country, point_type, "REPLAN-B", "Destination facility",
            province="destination",
        )
        shipment, _ = operations.create_direct(
            _facility_payload(operational_app, origin, destination),
            _user(operational_app),
            "step2a-replan-source",
        )
        source_plan = RoutePlan.query.filter_by(operational_shipment_id=shipment.id).one()
        source_leg = RouteLeg.query.filter_by(route_plan_id=source_plan.id).one()
        original_origin_snapshot = dict(source_leg.origin_snapshot)
        original_destination_snapshot = dict(source_leg.destination_snapshot)

        origin.fa_name = "Renamed and inactive"
        origin.is_active = False
        destination.is_active = False
        db.session.commit()

        result = routes.replan(
            shipment.id,
            source_plan.id,
            {"expected_version": source_plan.version, "reason": "Preserve historical endpoints"},
            _user(operational_app),
            "step2a-replan",
        )
        clone = RouteLeg.query.filter_by(route_plan_id=result["id"]).one()
        assert clone.source_route_leg_id == source_leg.id
        assert (clone.origin_location_id, clone.destination_location_id) == (
            source_leg.origin_location_id,
            source_leg.destination_location_id,
        )
        assert (clone.origin_logistics_point_id, clone.destination_logistics_point_id) == (
            origin.id,
            destination.id,
        )
        assert clone.origin_snapshot == original_origin_snapshot
        assert clone.destination_snapshot == original_destination_snapshot


def test_geography_only_create_quote_conversion_and_replan_keep_nullable_shape(operational_app):
    with operational_app.app_context():
        shipment, _ = operations.create_from_accepted_quote(
            _payload(operational_app),
            _user(operational_app),
            "step2a-historical-quote",
        )
        source_plan = RoutePlan.query.filter_by(operational_shipment_id=shipment.id).one()
        source_leg = RouteLeg.query.filter_by(route_plan_id=source_plan.id).one()
        assert source_leg.origin_logistics_point_id is None
        assert source_leg.destination_logistics_point_id is None

        graph_leg = operations.shipment_graph(shipment)["route_leg"]
        assert graph_leg["origin_logistics_point_id"] is None
        assert graph_leg["destination_logistics_point_id"] is None
        assert "facility" not in graph_leg["origin"]

        result = routes.replan(
            shipment.id,
            source_plan.id,
            {"expected_version": source_plan.version, "reason": "Historical geography-only clone"},
            _user(operational_app),
            "step2a-historical-replan",
        )
        clone = RouteLeg.query.filter_by(route_plan_id=result["id"]).one()
        assert clone.origin_logistics_point_id is None
        assert clone.destination_logistics_point_id is None
        assert clone.origin_location_id == source_leg.origin_location_id
        assert clone.destination_location_id == source_leg.destination_location_id
