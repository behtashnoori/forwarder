"""P3-04 route-stage execution, immutable history, and fail-closed scope."""

from __future__ import annotations

from pathlib import Path

import yaml

from backend.extensions import db
from backend.models import (
    Customer,
    CustomerRoleAssignment,
    TransportEquipmentType,
    TransportMeansType,
)
from backend.operational_models import (
    ExecutionUnit,
    OperationalEvent,
    OperationalMembership,
    OperationalShipment,
    Project,
    RouteLeg,
    RoutePlan,
)
from backend.organization_reference_catalog_models import (
    OrganizationTransportEquipmentTypeActivation,
    OrganizationTransportMeansTypeActivation,
)
from backend.services import execution_unit_service as unit_service
from backend.services import operational_service as operations
from backend.services import transport_execution_service as executions
from backend.tests.test_operational_vertical_slice import (
    _auth,
    _payload,
    _user,
    operational_app,
)


def _reference(model, code, fa, en):
    return model(
        immutable_code=code,
        fa_name=fa,
        en_name=en,
        is_active=True,
    )


def _setup(app):
    ids = app.config["phase1a"]
    membership = OperationalMembership.query.filter_by(user_id=ids["user"]).one()
    membership.permissions = sorted(
        set(membership.permissions or [])
        | {"execution_unit.read", "execution_unit.create", "execution_unit.update"}
    )
    verifier_membership = OperationalMembership.query.filter_by(
        user_id=ids["verifier"]
    ).one()
    verifier_membership.permissions = sorted(
        set(verifier_membership.permissions or [])
        | {"execution_unit.read", "execution_unit.create", "execution_unit.update"}
    )

    truck = _reference(TransportMeansType, "P304_TRUCK", "کامیون", "Truck")
    train = _reference(TransportMeansType, "P304_TRAIN", "قطار", "Train")
    foreign_means = _reference(
        TransportMeansType, "P304_FOREIGN", "وسیله خارجی", "Foreign means"
    )
    trailer = _reference(
        TransportEquipmentType, "P304_TRAILER", "تریلر", "Trailer"
    )
    wagon = _reference(TransportEquipmentType, "P304_WAGON", "واگن", "Wagon")
    container = _reference(
        TransportEquipmentType, "P304_CONTAINER", "کانتینر", "Container"
    )
    db.session.add_all([truck, train, foreign_means, trailer, wagon, container])
    db.session.flush()
    db.session.add_all(
        [
            OrganizationTransportMeansTypeActivation(
                organization_id=ids["org"],
                transport_means_type_id=item.id,
                created_by=ids["user"],
                updated_by=ids["user"],
            )
            for item in (truck, train)
        ]
        + [
            OrganizationTransportMeansTypeActivation(
                organization_id=ids["other_org"],
                transport_means_type_id=foreign_means.id,
                created_by=ids["outsider"],
                updated_by=ids["outsider"],
            )
        ]
        + [
            OrganizationTransportEquipmentTypeActivation(
                organization_id=ids["org"],
                transport_equipment_type_id=item.id,
                created_by=ids["user"],
                updated_by=ids["user"],
            )
            for item in (trailer, wagon, container)
        ]
    )
    carrier_a = Customer(
        operational_organization_id=ids["org"],
        ownership_scope="TENANT",
        company_name="Carrier A",
        status="active",
    )
    carrier_b = Customer(
        operational_organization_id=ids["org"],
        ownership_scope="TENANT",
        company_name="Carrier B",
        status="active",
    )
    foreign_carrier = Customer(
        operational_organization_id=ids["other_org"],
        ownership_scope="TENANT",
        company_name="Foreign Carrier",
        status="active",
    )
    db.session.add_all([carrier_a, carrier_b, foreign_carrier])
    db.session.flush()
    db.session.add_all(
        [
            CustomerRoleAssignment(
                customer_id=row.id,
                operational_organization_id=row.operational_organization_id,
                role_code="CARRIER",
                is_active=True,
            )
            for row in (carrier_a, carrier_b, foreign_carrier)
        ]
    )
    db.session.commit()

    shipment, _ = operations.create_from_accepted_quote(
        _payload(app), _user(app), "p304-source"
    )
    plan = RoutePlan.query.filter_by(
        operational_shipment_id=shipment.id, is_active=True
    ).one()
    leg = RouteLeg.query.filter_by(route_plan_id=plan.id).one()
    return {
        "shipment": shipment.public_id,
        "shipment_id": shipment.id,
        "plan": plan.id,
        "leg": leg.id,
        "truck": truck.public_id,
        "train": train.public_id,
        "foreign_means": foreign_means.public_id,
        "trailer": trailer.public_id,
        "wagon": wagon.public_id,
        "container": container.public_id,
        "carrier_a": carrier_a.id,
        "carrier_b": carrier_b.id,
        "foreign_carrier": foreign_carrier.id,
    }


def _payload_for(ctx, *, means=None, carrier=None, identifier=None, equipment=None):
    return {
        "transport_means_type_public_id": means or ctx["truck"],
        "carrier_customer_id": carrier,
        "means_identifier": identifier,
        "equipment": equipment or [],
    }


def test_multiple_executions_progressive_details_and_rail_chain(operational_app):
    with operational_app.app_context():
        ctx = _setup(operational_app)
        first, created = executions.create(
            ctx["shipment"],
            ctx["plan"],
            ctx["leg"],
            _payload_for(
                ctx,
                carrier=ctx["carrier_a"],
                equipment=[{"type_public_id": ctx["trailer"]}],
            ),
            _user(operational_app),
            "p304-first",
        )
        second, _ = executions.create(
            ctx["shipment"],
            ctx["plan"],
            ctx["leg"],
            _payload_for(
                ctx,
                carrier=ctx["carrier_b"],
                identifier="TRUCK-18",
                equipment=[
                    {"type_public_id": ctx["trailer"], "identifier": "T-18"}
                ],
            ),
            _user(operational_app),
            "p304-second",
        )
        rail, _ = executions.create(
            ctx["shipment"],
            ctx["plan"],
            ctx["leg"],
            _payload_for(
                ctx,
                means=ctx["train"],
                carrier=ctx["carrier_a"],
                identifier="TRAIN-C",
                equipment=[
                    {"type_public_id": ctx["wagon"], "identifier": "W-01"},
                    {"type_public_id": ctx["container"], "identifier": "C-01"},
                ],
            ),
            _user(operational_app),
            "p304-rail",
        )
        db.session.commit()

        listed = executions.list_for_plan(
            ctx["shipment"], ctx["plan"], _user(operational_app)
        )
        rows = listed["stages"][0]["executions"]
        assert created is True and len(rows) == 3
        assert {row["execution_public_id"] for row in rows} == {
            first.execution_unit.public_id,
            second.execution_unit.public_id,
            rail.execution_unit.public_id,
        }
        first_projection = next(
            row for row in rows
            if row["execution_public_id"] == first.execution_unit.public_id
        )
        assert first_projection["current"]["incomplete_fields"] == [
            "MEANS_IDENTIFIER",
            "EQUIPMENT_IDENTIFIER",
        ]
        rail_projection = next(
            row for row in rows
            if row["execution_public_id"] == rail.execution_unit.public_id
        )
        assert rail_projection["current"]["means"]["code"] == "P304_TRAIN"
        assert [item["type"]["code"] for item in rail_projection["current"]["equipment"]] == [
            "P304_WAGON",
            "P304_CONTAINER",
        ]


def test_change_history_pins_old_event_and_inactive_reference_stays_readable(
    operational_app,
):
    with operational_app.app_context():
        ctx = _setup(operational_app)
        assignment, _ = executions.create(
            ctx["shipment"], ctx["plan"], ctx["leg"],
            _payload_for(ctx, carrier=ctx["carrier_a"], identifier="TRUCK-A"),
            _user(operational_app), "p304-history-create",
        )
        db.session.flush()
        unit = assignment.execution_unit
        old_event, _ = unit_service.create_event(
            unit,
            {
                "expected_version": 1,
                "visibility": "customer",
                "customer_message": "movement recorded",
                "internal_note": "under truck A",
            },
            _user(operational_app),
            "p304-event-a",
        )
        assert old_event.transport_revision.revision_number == 1

        _, revision, changed = executions.revise(
            ctx["shipment"], ctx["plan"], unit.public_id,
            {
                **_payload_for(
                    ctx, carrier=ctx["carrier_b"], identifier="TRUCK-B",
                    equipment=[
                        {"type_public_id": ctx["trailer"], "identifier": "T-02"}
                    ],
                ),
                "expected_version": 2,
                "reason": "تعویض وسیله",
            },
            _user(operational_app), "p304-history-revise",
        )
        db.session.flush()
        assert changed is True and revision.revision_number == 2
        new_event, _ = unit_service.create_event(
            unit,
            {"expected_version": 3, "internal_note": "under truck B"},
            _user(operational_app),
            "p304-event-b",
        )
        db.session.commit()
        assert old_event.transport_revision.means_identifier == "TRUCK-A"
        assert new_event.transport_revision.means_identifier == "TRUCK-B"

        truck = TransportMeansType.query.filter_by(public_id=ctx["truck"]).one()
        trailer = TransportEquipmentType.query.filter_by(
            public_id=ctx["trailer"]
        ).one()
        OrganizationTransportMeansTypeActivation.query.filter_by(
            organization_id=operational_app.config["phase1a"]["org"],
            transport_means_type_id=truck.id,
        ).update({"status": "INACTIVE"})
        OrganizationTransportEquipmentTypeActivation.query.filter_by(
            organization_id=operational_app.config["phase1a"]["org"],
            transport_equipment_type_id=trailer.id,
        ).update({"status": "INACTIVE"})
        db.session.commit()
        listed = executions.list_for_plan(
            ctx["shipment"], ctx["plan"], _user(operational_app)
        )["stages"][0]["executions"][0]
        assert listed["current"]["means_identifier"] == "TRUCK-B"
        assert listed["current"]["means"]["currently_active"] is False
        assert listed["current"]["equipment"][0]["type"]["currently_active"] is False
        assert [item["means_identifier"] for item in listed["history"]] == [
            "TRUCK-B", "TRUCK-A"
        ]
        selectable = executions.options(ctx["shipment"], _user(operational_app))
        assert ctx["truck"] not in {item["public_id"] for item in selectable["means"]}
        assert ctx["trailer"] not in {
            item["public_id"] for item in selectable["equipment"]
        }
        timeline = unit_service.timeline(unit, {})
        assert [item["transport_context"]["means_identifier"] for item in timeline["data"]] == [
            "TRUCK-B", "TRUCK-A"
        ]
        customer_timeline = unit_service.timeline(unit, {}, customer=True)
        assert len(customer_timeline["data"]) == 1
        assert "transport_context" not in customer_timeline["data"][0]
        assert "internal_note" not in customer_timeline["data"][0]


def test_tenant_reference_carrier_owner_and_guessed_ids_fail_closed(
    operational_app,
):
    with operational_app.app_context():
        ctx = _setup(operational_app)
        base = _payload_for(ctx, carrier=ctx["carrier_a"])
        for payload, expected in [
            (_payload_for(ctx, carrier=ctx["foreign_carrier"]), "TENANT_SCOPE_VIOLATION"),
            (_payload_for(ctx, means=ctx["foreign_means"]), "ORGANIZATION_REFERENCE_NOT_ACTIVE"),
        ]:
            try:
                executions.create(
                    ctx["shipment"], ctx["plan"], ctx["leg"], payload,
                    _user(operational_app), f"negative-{expected}",
                )
            except operations.OperationalError as exc:
                assert exc.code == expected
                db.session.rollback()
            else:
                raise AssertionError("cross-tenant input was accepted")

        for actor in (_user(operational_app, "verifier"), _user(operational_app, "outsider")):
            try:
                executions.create(
                    ctx["shipment"], ctx["plan"], ctx["leg"], base,
                    actor, f"owner-negative-{actor['id']}",
                )
            except operations.OperationalError as exc:
                assert exc.status in {403, 404}
                db.session.rollback()
            else:
                raise AssertionError("non-owner mutation was accepted")

        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        membership.is_active = False
        db.session.commit()
        try:
            executions.create(
                ctx["shipment"], ctx["plan"], ctx["leg"], base,
                _user(operational_app), "inactive-owner",
            )
        except operations.OperationalError as exc:
            assert exc.status == 403
        else:
            raise AssertionError("inactive membership mutation was accepted")


def test_http_contract_reopens_multiple_executions_and_ignores_project_compatibility(
    operational_app,
):
    with operational_app.app_context():
        ctx = _setup(operational_app)
    client = operational_app.test_client()
    url = (
        f"/api/operational-shipments/{ctx['shipment']}/route-plans/{ctx['plan']}"
        f"/legs/{ctx['leg']}/transport-executions"
    )
    for index, carrier in enumerate((ctx["carrier_a"], ctx["carrier_b"]), start=1):
        response = client.post(
            url,
            headers={**_auth(operational_app), "Idempotency-Key": f"http-{index}"},
            json=_payload_for(ctx, carrier=carrier, identifier=f"TRUCK-{index}"),
        )
        assert response.status_code == 201, response.get_json()

    with operational_app.app_context():
        shipment = OperationalShipment.query.filter_by(public_id=ctx["shipment"]).one()
        other_project = Project(
            organization_id=shipment.organization_id,
            primary_customer_id=shipment.customer_id,
            project_code="P304-COMPAT",
            tracking_code="p304-compat-tracking",
            created_by_user_id=operational_app.config["phase1a"]["user"],
        )
        db.session.add(other_project)
        db.session.flush()
        ExecutionUnit.query.filter_by(operational_shipment_id=shipment.id).update(
            {"project_id": other_project.id}
        )
        db.session.commit()

    reopened = client.get(
        f"/api/operational-shipments/{ctx['shipment']}/route-plans/{ctx['plan']}/transport-executions",
        headers=_auth(operational_app),
    )
    assert reopened.status_code == 200
    rows = reopened.get_json()["data"]["stages"][0]["executions"]
    assert [row["current"]["means_identifier"] for row in rows] == [
        "TRUCK-1", "TRUCK-2"
    ]
    with operational_app.app_context():
        assert OperationalEvent.query.count() == 0


def test_openapi_exposes_only_the_bounded_p3_04_commands():
    document = yaml.safe_load(
        (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "openapi"
            / "openapi.yaml"
        ).read_text(encoding="utf-8")
    )
    paths = document["paths"]
    expected = {
        "/api/operational-shipments/{shipment_id}/transport-execution-options": "get",
        "/api/operational-shipments/{shipment_id}/route-plans/{plan_id}/transport-executions": "get",
        "/api/operational-shipments/{shipment_id}/route-plans/{plan_id}/legs/{leg_id}/transport-executions": "post",
        "/api/operational-shipments/{shipment_id}/route-plans/{plan_id}/transport-executions/{execution_id}/revisions": "post",
    }
    for path, method in expected.items():
        assert method in paths[path]
    assert not any(
        "transport-executions" in path and path.endswith("/allocations")
        for path in paths
    )
