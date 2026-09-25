"""Phase 3 P3-03 planned branches, Cargo destinations and actual-route facts."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.models import CargoType, Province, UnitOfMeasure
from backend.operational_models import (
    Milestone,
    OperationalException,
    RouteCargoDestination,
    RouteLeg,
    RoutePlan,
    RouteTraversalFact,
)
from backend.services import operational_service as operations
from backend.services import operational_read_service as reads
from backend.services import route_orchestration_service as routes
from backend.tests.test_operational_vertical_slice import (
    _payload,
    _user,
    operational_app,
)


def _endpoint(location_id):
    return {"source_type": "province", "source_id": location_id}


def _leg(sequence, origin, destination, start, *, parent=None, label=None):
    return {
        "sequence_number": sequence,
        "parent_route_leg_id": parent,
        "branch_label": label,
        "origin": _endpoint(origin),
        "destination": _endpoint(destination),
        "transport_mode": "road",
        "planned_departure": start.isoformat(),
        "planned_arrival": (start + timedelta(hours=2)).isoformat(),
    }


def _cargo_lines(app, shipment, count=2):
    ids = app.config["phase1a"]
    cargo_type = CargoType(
        immutable_code="P303_GENERAL",
        fa_name="کالای عمومی",
        en_name="General cargo",
        is_active=True,
    )
    uom = UnitOfMeasure(
        immutable_code="P303_EA",
        fa_name="عدد",
        en_name="Each",
        symbol="ea",
        measurement_dimension="COUNT",
        is_active=True,
    )
    db.session.add_all([cargo_type, uom])
    db.session.flush()
    rows = []
    for number in range(1, count + 1):
        row = ShipmentCargoItem(
            operational_shipment_id=shipment.id,
            cargo_owner_customer_id=ids["customer"],
            line_number=number,
            cargo_type=cargo_type,
            quantity=Decimal("1"),
            planned_quantity=Decimal("1"),
            uom=uom,
            display_name_snapshot=f"Cargo {number}",
            cargo_type_code_snapshot=cargo_type.immutable_code,
            cargo_type_fa_snapshot=cargo_type.fa_name,
            cargo_type_en_snapshot=cargo_type.en_name,
            uom_code_snapshot=uom.immutable_code,
            uom_symbol_snapshot=uom.symbol,
            created_by=ids["user"],
            updated_by=ids["user"],
        )
        db.session.add(row)
        rows.append(row)
    db.session.commit()
    return rows


def _branched_draft(app):
    shipment, _ = operations.create_from_accepted_quote(
        _payload(app), _user(app), "p303-source"
    )
    ids = app.config["phase1a"]
    third = Province(name_fa="مقصد دوم", code="P303-B")
    db.session.add(third)
    db.session.commit()
    start = datetime.now(timezone.utc) + timedelta(days=1)
    plan_data = routes.create_plan(shipment.id, {}, _user(app))
    root = routes.add_leg(
        shipment.id,
        plan_data["id"],
        _leg(1, ids["origin"], ids["destination"], start, label="بخش مشترک"),
        _user(app),
    )
    first = routes.add_leg(
        shipment.id,
        plan_data["id"],
        _leg(
            2,
            ids["destination"],
            ids["origin"],
            start + timedelta(hours=3),
            parent=root["id"],
            label="مقصد اول",
        ),
        _user(app),
    )
    second = routes.add_leg(
        shipment.id,
        plan_data["id"],
        _leg(
            3,
            ids["destination"],
            third.id,
            start + timedelta(hours=3),
            parent=root["id"],
            label="مقصد دوم",
        ),
        _user(app),
    )
    return shipment, db.session.get(RoutePlan, plan_data["id"]), root, first, second


def test_incomplete_route_is_saved_without_fake_times_or_milestones(operational_app):
    with operational_app.app_context():
        shipment, _ = operations.create_from_accepted_quote(
            _payload(operational_app), _user(operational_app), "p303-incomplete"
        )
        ids = operational_app.config["phase1a"]
        plan = routes.create_plan(shipment.id, {}, _user(operational_app))
        leg = routes.add_leg(
            shipment.id,
            plan["id"],
            {
                "sequence_number": 1,
                "origin": _endpoint(ids["origin"]),
                "destination": _endpoint(ids["destination"]),
            },
            _user(operational_app),
        )

        assert leg["transport_mode"] is None
        assert leg["planned_departure"] is None
        assert leg["planned_arrival"] is None
        assert Milestone.query.filter_by(route_leg_id=leg["id"]).count() == 0
        detail = routes.get_plan(shipment.id, plan["id"], _user(operational_app))
        assert detail["is_complete"] is False
        assert len(detail["incomplete_fields"]) == 3
        validation = routes.validate_plan(
            shipment.id, plan["id"], _user(operational_app)
        )
        assert validation["valid"] is False
        assert {row["code"] for row in validation["errors"]} == {
            "ROUTE_LEG_INCOMPLETE"
        }


def test_branches_cargo_destinations_actual_deviation_and_replan_history(
    operational_app,
):
    with operational_app.app_context():
        shipment, plan, root, first, second = _branched_draft(operational_app)
        cargo = _cargo_lines(operational_app, shipment)
        assigned_first = routes.assign_cargo_destination(
            shipment.id,
            plan.id,
            cargo[0].public_id,
            {"destination_route_leg_id": first["id"]},
            _user(operational_app),
        )
        routes.assign_cargo_destination(
            shipment.id,
            plan.id,
            cargo[1].public_id,
            {"destination_route_leg_id": second["id"]},
            _user(operational_app),
        )
        reassigned = routes.assign_cargo_destination(
            shipment.id,
            plan.id,
            cargo[0].public_id,
            {
                "destination_route_leg_id": second["id"],
                "expected_version": assigned_first["version"],
            },
            _user(operational_app),
        )
        assert reassigned["version"] == 2
        assert routes.validate_plan(
            shipment.id, plan.id, _user(operational_app)
        ) == {"valid": True, "errors": []}
        active = routes.activate_plan(
            shipment.id, plan.id, {"expected_version": 1}, _user(operational_app)
        )

        ids = operational_app.config["phase1a"]
        before_exceptions = OperationalException.query.count()
        actual = routes.record_traversal(
            shipment.id,
            plan.id,
            {
                "planned_route_leg_id": second["id"],
                "origin": _endpoint(ids["origin"]),
                "destination": _endpoint(ids["destination"]),
                "departed_at": (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                ).isoformat(),
                "arrived_at": (
                    datetime.now(timezone.utc) - timedelta(hours=1)
                ).isoformat(),
                "notes": "مسیر واقعی متفاوت",
            },
            _user(operational_app),
        )
        assert actual["is_deviation"] is True
        assert OperationalException.query.count() == before_exceptions
        assert reads.plan_has_execution(db.session.get(RoutePlan, plan.id)) is True

        replanned = routes.replan(
            shipment.id,
            plan.id,
            {"expected_version": active["version"], "reason": "تغییر برنامه مقصد"},
            _user(operational_app),
            "p303-replan",
        )
        cloned_legs = RouteLeg.query.filter_by(
            route_plan_id=replanned["id"]
        ).order_by(RouteLeg.sequence_number).all()
        assert [row.parent_route_leg_id for row in cloned_legs] == [
            None,
            cloned_legs[0].id,
            cloned_legs[0].id,
        ]
        assert RouteCargoDestination.query.filter_by(
            route_plan_id=replanned["id"]
        ).count() == 2
        assert RouteTraversalFact.query.filter_by(route_plan_id=plan.id).count() == 1
        assert RouteTraversalFact.query.filter_by(
            route_plan_id=replanned["id"]
        ).count() == 0
        source_detail = routes.get_plan(
            shipment.id, plan.id, _user(operational_app)
        )
        assert source_detail["actual_route"][0]["notes"] == "مسیر واقعی متفاوت"
        assert source_detail["legs"][0]["branch_label"] == "بخش مشترک"


def test_branched_route_rejects_missing_cargo_destination_and_parent_cycle(
    operational_app,
):
    with operational_app.app_context():
        shipment, plan, root, first, _second = _branched_draft(operational_app)
        _cargo_lines(operational_app, shipment, count=1)
        validation = routes.validate_plan(
            shipment.id, plan.id, _user(operational_app)
        )
        assert "CARGO_DESTINATION_REQUIRED" in {
            row["code"] for row in validation["errors"]
        }
        with pytest.raises(operations.OperationalError) as cycle:
            routes.update_leg(
                shipment.id,
                plan.id,
                root["id"],
                {
                    "expected_version": root["version"],
                    "parent_route_leg_id": first["id"],
                },
                _user(operational_app),
            )
        assert cycle.value.code == "ROUTE_BRANCH_CYCLE"


def test_only_fixed_owner_can_mutate_route_and_cross_tenant_is_hidden(
    operational_app,
):
    with operational_app.app_context():
        shipment, _ = operations.create_from_accepted_quote(
            _payload(operational_app), _user(operational_app), "p303-owner"
        )
        with pytest.raises(operations.OperationalError) as admin:
            routes.create_plan(
                shipment.id, {}, _user(operational_app, "verifier")
            )
        assert (admin.value.code, admin.value.status) == (
            "FORBIDDEN_OPERATION",
            403,
        )
        with pytest.raises(operations.OperationalError) as foreign:
            routes.create_plan(
                shipment.id, {}, _user(operational_app, "outsider")
            )
        assert (foreign.value.code, foreign.value.status) == (
            "RESOURCE_NOT_FOUND",
            404,
        )
