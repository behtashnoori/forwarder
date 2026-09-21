"""Phase 1A domain, transaction, permission, and API contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import pytest

from backend import create_app
from backend.extensions import db
from backend.cargo_models import CargoCatalogItem, ShipmentCargoItem
from backend.models import (
    CargoType,
    Customer,
    ExpertQuote,
    ExpertUser,
    Province,
    ShipmentRequest,
    UnitOfMeasure,
)
from backend.operational_models import (
    Milestone,
    MilestoneEvent,
    OperationalAudit,
    OperationalMembership,
    OperationalOrganization,
    OperationalOutbox,
    OperationalShipment,
    OperationalWorkItem,
    Project,
    ProjectAccess,
    RouteLeg,
    RoutePlan,
)
from backend.services import operational_service as service
from backend.services.request_transport_projection import project_existing_request_transport
from backend.request_transport_catalog import COMBINED_TRANSPORT_CODE
from backend.services import document_readiness_service, economics_service
from backend.services.expert_scope_service import EXPERT_BASELINE_OPERATIONAL_PERMISSIONS
from backend.auth import auth_manager


@pytest.fixture()
def operational_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "phase1a-test",
        }
    )
    with app.app_context():
        org = OperationalOrganization(name="Synthetic Operations")
        other_org = OperationalOrganization(name="Other Synthetic Operations")
        user = ExpertUser(
            username="phase1a-operator",
            password_hash="unused",
            full_name="Phase1A Operator",
            role="expert",
            is_active=True,
        )
        outsider = ExpertUser(
            username="phase1a-outsider",
            password_hash="unused",
            full_name="Phase1A Outsider",
            role="expert",
            is_active=True,
        )
        verifier = ExpertUser(
            username="phase1a-verifier",
            password_hash="unused",
            full_name="Phase1A Verifier",
            role="manager",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        db.session.add_all([org, other_org, user, outsider, verifier])
        db.session.flush()
        all_permissions = [
            "operational_shipment.read",
            "operational_shipment.create",
            "operational_shipment.create_direct",
            "milestone_event.create",
            "milestone.verify",
            "milestone.correct",
            "work_item.read",
            "work_item.manage",
            "route_plan.read",
            "route_plan.create",
            "route_plan.activate",
            "route_plan.replan",
            "route_leg.manage",
            "checkpoint.read",
            "checkpoint.report",
            "checkpoint.verify",
            "route_exception.read",
            "route_exception.manage",
            "document_readiness.read",
            "economics.commitment.create",
        ]
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id, user_id=user.id, permissions=all_permissions
                ),
                OperationalMembership(
                    organization_id=org.id,
                    user_id=verifier.id,
                    permissions=all_permissions,
                ),
                OperationalMembership(
                    organization_id=other_org.id,
                    user_id=outsider.id,
                    permissions=all_permissions,
                ),
            ]
        )
        origin = Province(name_fa="مبدأ", code="P1A-O")
        destination = Province(name_fa="مقصد", code="P1A-D")
        customer = Customer(
            first_name="Canonical",
            last_name="Customer",
            phone="09000000000",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        foreign_customer = Customer(
            first_name="Foreign",
            last_name="Customer",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=other_org.id,
        )
        db.session.add_all([origin, destination, customer, foreign_customer])
        db.session.flush()
        request = ShipmentRequest(
            contact_phone="09000000000",
            shipping_type="domestic",
            transport_method="road",
            domestic_transport_method="Rail Transport",
            international_transport_method="Sea Freight",
            transport_method_preference="customer_choice",
            status="waiting_for_customer",
            status_request_status="new",
            assigned_to=user.id,
            customer_id=customer.id,
            operational_organization_id=org.id,
            ownership_scope="TENANT",
        )
        db.session.add(request)
        db.session.flush()
        accepted = ExpertQuote(
            shipment_request_id=request.id,
            amount=1000,
            currency="IRR",
            created_by_expert_id=user.id,
            created_at=datetime.now(timezone.utc),
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=org.id,
        )
        declined = ExpertQuote(
            shipment_request_id=request.id,
            amount=900,
            currency="IRR",
            created_by_expert_id=user.id,
            created_at=datetime.now(timezone.utc),
            customer_response="declined",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=org.id,
        )
        db.session.add_all([accepted, declined])
        db.session.commit()
        app.config["phase1a"] = {
            "org": org.id,
            "other_org": other_org.id,
            "user": user.id,
            "verifier": verifier.id,
            "outsider": outsider.id,
            "accepted": accepted.id,
            "declined": declined.id,
            "origin": origin.id,
            "destination": destination.id,
            "customer": customer.id,
            "foreign_customer": foreign_customer.id,
        }
    yield app


def _user(app, key="user"):
    ids = app.config["phase1a"]
    return {"id": ids[key], "role": "expert", "username": key}


def _payload(app, quote="accepted", departure=None, arrival=None):
    ids = app.config["phase1a"]
    departure = departure or datetime.now(timezone.utc) + timedelta(hours=1)
    arrival = arrival or departure + timedelta(hours=5)
    return {
        "accepted_quote_id": ids[quote],
        "planned_departure": departure.isoformat(),
        "planned_arrival": arrival.isoformat(),
        "origin": {"source_type": "province", "source_id": ids["origin"]},
        "destination": {"source_type": "province", "source_id": ids["destination"]},
        "transport_mode": "road",
    }


def _direct_payload(app, departure=None, arrival=None):
    payload = _payload(app, departure=departure, arrival=arrival)
    payload.pop("accepted_quote_id")
    return {
        "source_type": "direct",
        "customer_id": app.config["phase1a"]["customer"],
        "project_public_id": None,
        "route": payload,
    }


def test_direct_create_converges_on_shared_aggregate_and_replays(operational_app):
    with operational_app.app_context():
        before_requests = ShipmentRequest.query.count()
        before_quotes = ExpertQuote.query.count()
        payload = _direct_payload(operational_app)
        shipment, created = service.create_direct(
            payload, _user(operational_app), "direct-1"
        )
        replay, recreated = service.create_direct(
            payload, _user(operational_app), "direct-1"
        )

        assert created is True and recreated is False and replay.id == shipment.id
        assert (
            shipment.source_type == "direct"
            and shipment.customer_id == operational_app.config["phase1a"]["customer"]
        )
        assert (
            shipment.shipment_request_id is None and shipment.accepted_quote_id is None
        )
        assert ShipmentRequest.query.count() == before_requests
        assert ExpertQuote.query.count() == before_quotes
        assert RoutePlan.query.count() == 1 and RouteLeg.query.count() == 1
        assert {row.milestone_type for row in Milestone.query.all()} == {
            "departure",
            "arrival",
        }
        assert (
            OperationalAudit.query.filter_by(
                action="operational_shipment.created"
            ).count()
            == 1
        )
        outbox = OperationalOutbox.query.filter_by(
            event_type="operational_shipment.created"
        ).one()
        assert outbox.payload["_ownership_census"] == {
            "census_id": "legacy-mt1c",
            "cache_version": 0,
            "cache_token": 0,
        }

        changed = _direct_payload(operational_app)
        changed["route"]["transport_mode"] = "rail"
        with pytest.raises(service.OperationalError) as conflict:
            service.create_direct(changed, _user(operational_app), "direct-1")
        assert conflict.value.code == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"


def test_direct_permission_is_not_implied_by_legacy_or_quote_permission(
    operational_app,
):
    with operational_app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        for permission in (
            "operational_shipment.create",
            "operational_shipment.create_from_quote",
        ):
            membership.permissions = ["operational_shipment.read", permission]
            db.session.commit()
            with pytest.raises(service.OperationalError) as forbidden:
                service.create_direct(
                    _direct_payload(operational_app),
                    _user(operational_app),
                    f"denied-{permission}",
                )
            assert forbidden.value.code == "FORBIDDEN_OPERATION"


def test_expert_operational_baseline_allows_direct_creation(operational_app):
    """Provisioning supplies create_direct; the endpoint guard still enforces it."""
    with operational_app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        membership.permissions = list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS)
        db.session.commit()
        shipment, created = service.create_direct(
            _direct_payload(operational_app), _user(operational_app), "baseline-direct"
        )
        assert created is True and shipment.source_type == "direct"


def test_direct_http_list_detail_and_source_specific_capabilities(operational_app):
    client = operational_app.test_client()
    created = client.post(
        "/api/operational-shipments",
        json=_direct_payload(operational_app),
        headers={**_auth(operational_app), "Idempotency-Key": "direct-http"},
    )
    assert created.status_code == 201
    source = created.json["data"]["source"]
    assert source["type"] == "direct"
    assert source["shipment_request_id"] is None and source["accepted_quote_id"] is None

    listing = client.get(
        "/api/operational-shipments?customer=0900", headers=_auth(operational_app)
    )
    assert listing.status_code == 200
    assert [row["public_id"] for row in listing.json["data"]] == [
        created.json["data"]["public_id"]
    ]

    with operational_app.app_context():
        shipment = OperationalShipment.query.filter_by(
            public_id=created.json["data"]["public_id"]
        ).one()
        milestone = Milestone.query.filter_by(
            operational_shipment_id=shipment.id, milestone_type="departure"
        ).one()
        readiness = document_readiness_service.transition_readiness(
            shipment, milestone, "READY"
        )
        assert (
            readiness["applicability"] == "NOT_APPLICABLE"
            and readiness["allowed"] is True
        )
        with pytest.raises(service.OperationalError) as documents:
            document_readiness_service.materialization_preview(
                shipment.public_id, _user(operational_app)
            )
        assert documents.value.code == "SOURCE_CAPABILITY_NOT_APPLICABLE"
        with pytest.raises(service.OperationalError) as economics:
            economics_service.quote_preview(shipment.public_id, _user(operational_app))
        assert economics.value.code == "SOURCE_CAPABILITY_NOT_APPLICABLE"


def _auth(app, key="user"):
    with app.app_context():
        token = auth_manager.generate_tokens(app.config["phase1a"][key])["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _auth_user(app, user_id):
    with app.app_context():
        token = auth_manager.generate_tokens(user_id)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_baseline_direct_creator_opens_route_detail_but_peer_cannot(operational_app):
    with operational_app.app_context():
        ids = operational_app.config["phase1a"]
        membership = OperationalMembership.query.filter_by(user_id=ids["user"]).one()
        membership.permissions = list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS)
        peer = ExpertUser(
            username="phase1a-peer",
            password_hash="unused",
            full_name="Phase1A Peer",
            role="expert",
            is_active=True,
        )
        db.session.add(peer)
        db.session.flush()
        db.session.add(OperationalMembership(
            organization_id=ids["org"],
            user_id=peer.id,
            permissions=list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS),
        ))
        db.session.commit()
        peer_id = peer.id

    client = operational_app.test_client()
    direct_payload = _direct_payload(operational_app)
    created = client.post(
        "/api/operational-shipments",
        json=direct_payload,
        headers={**_auth(operational_app), "Idempotency-Key": "baseline-detail"},
    )
    assert created.status_code == 201
    shipment_id = created.json["data"]["public_id"]
    owner_headers = _auth(operational_app)
    for path in (
        f"/api/operational-shipments/{shipment_id}",
        f"/api/operational-shipments/{shipment_id}/route-plans",
        f"/api/operational-shipments/{shipment_id}/timeline",
        f"/api/operational-shipments/{shipment_id}/route-exceptions",
    ):
        assert client.get(path, headers=owner_headers).status_code == 200
        assert client.get(path, headers=_auth_user(operational_app, peer_id)).status_code == 404
    replay_probe = client.post(
        "/api/operational-shipments",
        json=direct_payload,
        headers={
            **_auth_user(operational_app, peer_id),
            "Idempotency-Key": "baseline-detail",
        },
    )
    assert replay_probe.status_code == 404


def test_operation_list_filters_cover_direct_and_request_derived_shipments(operational_app):
    departure = datetime(2030, 1, 10, 10, tzinfo=timezone.utc)
    arrival = departure + timedelta(hours=5)
    with operational_app.app_context():
        direct, _ = service.create_direct(
            _direct_payload(operational_app, departure, arrival),
            _user(operational_app),
            "filter-direct",
        )
        derived, _ = service.create_from_accepted_quote(
            _payload(operational_app, departure=departure, arrival=arrival),
            _user(operational_app),
            "filter-derived",
        )
        expected = {direct.public_id, derived.public_id}

    client = operational_app.test_client()
    headers = _auth(operational_app)

    def ids_for(query):
        response = client.get(f"/api/operational-shipments?{query}", headers=headers)
        assert response.status_code == 200, response.get_json()
        return {row["public_id"] for row in response.json["data"]}

    assert ids_for("origin=%D9%85%D8%A8%D8%AF%D8%A3") == expected
    assert ids_for("origin=%D9%85%D9%82%D8%B5%D8%AF") == set()
    assert ids_for("destination=%D9%85%D9%82%D8%B5%D8%AF") == expected
    assert ids_for("status=planned") == expected
    assert ids_for("customer=Canonical") == expected
    assert ids_for("date_from=2029-01-01T00:00:00Z") == expected
    assert ids_for("date_to=2031-01-01T00:00:00Z") == expected
    assert ids_for("overdue=false") == expected
    outsider = client.get(
        "/api/operational-shipments?origin=%D9%85%D8%A8%D8%AF%D8%A3",
        headers=_auth(operational_app, "outsider"),
    )
    assert outsider.status_code == 200 and outsider.json["data"] == []


def test_direct_and_request_operation_catalog_cargo_allocation_tracking_and_scope(operational_app):
    with operational_app.app_context():
        ids = operational_app.config["phase1a"]
        membership = OperationalMembership.query.filter_by(user_id=ids["user"]).one()
        membership.permissions = list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS) + [
            "execution_unit.read", "execution_unit.create", "execution_unit.update",
        ]
        cargo_type = CargoType(
            public_id="uat-cargo-type", immutable_code="UAT_GENERAL",
            fa_name="کالای آزمون", en_name="UAT cargo", display_order=1,
            is_active=True, version=1,
        )
        uom = UnitOfMeasure(
            public_id="uat-uom", immutable_code="UAT_EA", fa_name="عدد",
            en_name="Each", display_order=1, is_active=True, version=1,
            symbol="ea", measurement_dimension="COUNT",
        )
        db.session.add_all([cargo_type, uom])
        db.session.flush()
        active = CargoCatalogItem(
            public_id="uat-active-catalog", organization_id=ids["org"],
            immutable_code="UAT-ACTIVE", fa_name="کالای فعال",
            en_name="Active cargo", cargo_type=cargo_type, default_uom=uom,
            is_active=True, created_by=ids["user"], updated_by=ids["user"],
        )
        inactive = CargoCatalogItem(
            public_id="uat-inactive-catalog", organization_id=ids["org"],
            immutable_code="UAT-INACTIVE", fa_name="کالای غیرفعال",
            en_name="Inactive cargo", cargo_type=cargo_type, default_uom=uom,
            is_active=False, created_by=ids["user"], updated_by=ids["user"],
        )
        foreign = CargoCatalogItem(
            public_id="uat-foreign-catalog", organization_id=ids["other_org"],
            immutable_code="UAT-FOREIGN", fa_name="کالای سازمان دیگر",
            en_name="Foreign cargo", cargo_type=cargo_type, default_uom=uom,
            is_active=True, created_by=ids["outsider"], updated_by=ids["outsider"],
        )
        peer = ExpertUser(
            username="request-cargo-peer", password_hash="unused",
            full_name="Request Cargo Peer", role="expert", is_active=True,
        )
        db.session.add_all([active, inactive, foreign, peer])
        db.session.flush()
        db.session.add(OperationalMembership(
            organization_id=ids["org"], user_id=peer.id,
            permissions=list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS),
        ))
        db.session.commit()
        peer_id = peer.id

    client = operational_app.test_client()
    headers = _auth(operational_app)
    direct = client.post(
        "/api/operational-shipments",
        json=_direct_payload(operational_app),
        headers={**headers, "Idempotency-Key": "direct-cargo-chain"},
    )
    assert direct.status_code == 201
    direct_id = direct.json["data"]["public_id"]
    options = client.get("/api/internal/cargo-options", headers=headers)
    assert options.status_code == 200
    assert [row["public_id"] for row in options.json["catalog"]] == ["uat-active-catalog"]
    cargo_payload = {
        "line_number": 1,
        "catalog_item_public_id": "uat-active-catalog",
        "cargo_type_public_id": "uat-cargo-type",
        "quantity": "12.5",
        "uom_public_id": "uat-uom",
    }
    direct_cargo = client.post(
        f"/api/internal/operational-shipments/{direct_id}/cargo-items",
        json={**cargo_payload, "quantity": "3.25"},
        headers=headers,
    )
    assert direct_cargo.status_code == 201
    assert direct_cargo.json["item"]["quantity"] == "3.250000"

    eligible = client.get("/api/operations/selectors/accepted-quotes", headers=headers)
    assert eligible.status_code == 200
    assert [row["id"] for row in eligible.json["items"]] == [operational_app.config["phase1a"]["accepted"]]
    quote_payload = _payload(operational_app)
    created = client.post(
        "/api/operational-shipments/from-accepted-quote",
        json=quote_payload,
        headers={**headers, "Idempotency-Key": "request-cargo-chain"},
    )
    assert created.status_code == 201, created.get_json()
    shipment_id = created.json["data"]["public_id"]
    assert client.get(f"/api/operational-shipments/{shipment_id}", headers=headers).status_code == 200

    cargo = client.post(
        f"/api/internal/operational-shipments/{shipment_id}/cargo-items",
        json=cargo_payload,
        headers=headers,
    )
    assert cargo.status_code == 201, cargo.get_json()
    cargo_id = cargo.json["item"]["public_id"]
    assert cargo.json["item"]["quantity"] == "12.500000"
    assert cargo.json["item"]["uom_public_id"] == "uat-uom"
    for catalog_id, status in (("uat-inactive-catalog", 422), ("uat-foreign-catalog", 404)):
        rejected = client.post(
            f"/api/internal/operational-shipments/{shipment_id}/cargo-items",
            json={**cargo_payload, "line_number": 2, "catalog_item_public_id": catalog_id},
            headers=headers,
        )
        assert rejected.status_code == status

    with operational_app.app_context():
        shipment = OperationalShipment.query.filter_by(public_id=shipment_id).one()
        shipment_customer = db.session.get(Customer, shipment.customer_id)
        shipment_customer.operational_organization_id = shipment.organization_id
        shipment_customer.ownership_scope = "TENANT"
        project = Project(
            organization_id=shipment.organization_id, primary_customer_id=shipment.customer_id,
            project_code="UAT-REQUEST-JOURNEY", tracking_code="uat-request-journey",
            created_by_user_id=operational_app.config["phase1a"]["user"],
        )

        db.session.add(project); db.session.flush()
        db.session.add(ProjectAccess(
            organization_id=shipment.organization_id, project_id=project.id,
            user_id=operational_app.config["phase1a"]["user"],
            created_by_user_id=operational_app.config["phase1a"]["user"],
        ))
        shipment.project_id = project.id; db.session.commit()
        project_public_id = project.public_id
    unit = client.post(
        f"/api/v2/projects/{project_public_id}/execution-units",
        json={"unit_type": "truck", "display_name": "UAT Truck",
              "operational_shipment_public_id": shipment_id}, headers=headers,
    )
    assert unit.status_code == 201
    allocation = client.post(
        f"/api/v2/projects/{project_public_id}/execution-units/{unit.json['data']['public_id']}/allocations",
        json={"cargo_public_id": cargo_id, "allocated_quantity": "12.5"}, headers=headers,
    )
    assert allocation.status_code == 201, allocation.get_json()
    enabled = client.post(
        f"/api/internal/operational-shipments/{shipment_id}/transport-tracking/enable",
        headers=headers,
    )
    assert enabled.status_code == 200
    tracked = client.post(
        f"/api/v2/projects/{project_public_id}/execution-units/{unit.json['data']['public_id']}/events",
        json={
            "expected_version": 1, "event_type": "in_transit", "lifecycle_status": "in_progress",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "location": {"location_text": "Tehran"}, "visibility": "customer",
            "customer_message": "On route",
        },
        headers={**headers, "Idempotency-Key": "uat-tracking-event"},
    )
    assert tracked.status_code == 201
    timeline = client.get(
        f"/api/v2/projects/{project_public_id}/execution-units/{unit.json['data']['public_id']}/timeline",
        headers=headers,
    )
    assert timeline.json["data"][0]["location"]["display_name"] == "Tehran"

    peer_headers = _auth_user(operational_app, peer_id)
    assert client.get(f"/api/operational-shipments/{shipment_id}", headers=peer_headers).status_code == 404
    assert client.get(
        f"/api/internal/operational-shipments/{shipment_id}/cargo-items",
        headers=peer_headers,
    ).status_code == 404
    assert client.get("/api/operations/selectors/accepted-quotes", headers=peer_headers).json["items"] == []
    unauthorized_replay_payload = {**quote_payload, "transport_mode": "rail"}
    replay_probe = client.post(
        "/api/operational-shipments/from-accepted-quote",
        json=unauthorized_replay_payload,
        headers={**peer_headers, "Idempotency-Key": "request-cargo-chain"},
    )
    assert replay_probe.status_code == 404


def test_direct_create_hides_foreign_tenant_customer_and_creates_no_shipment(operational_app):
    with operational_app.app_context():
        payload = _direct_payload(operational_app)
        payload["customer_id"] = operational_app.config["phase1a"]["foreign_customer"]
        before = OperationalShipment.query.count()
        with pytest.raises(service.OperationalError) as denied:
            service.create_direct(payload, _user(operational_app), "foreign-customer")
        assert denied.value.code == "RESOURCE_NOT_FOUND"
        assert OperationalShipment.query.count() == before


def test_create_from_accepted_quote_is_complete_and_idempotent(operational_app):
    with operational_app.app_context():
        payload = _payload(operational_app)
        first, created = service.create_from_accepted_quote(
            payload, _user(operational_app), "create-1"
        )
        replay, recreated = service.create_from_accepted_quote(
            payload, _user(operational_app), "create-1"
        )
        assert created is True and recreated is False and replay.id == first.id
        assert (
            first.primary_responsible_expert_id
            == db.session.get(
                ExpertQuote, payload["accepted_quote_id"]
            ).created_by_expert_id
            == operational_app.config["phase1a"]["user"]
        )
        assert OperationalShipment.query.count() == 1
        assert RoutePlan.query.count() == 1 and RouteLeg.query.count() == 1
        assert {m.milestone_type for m in Milestone.query.all()} == {
            "departure",
            "arrival",
        }
        assert (
            OperationalAudit.query.filter_by(
                action="operational_shipment.created"
            ).count()
            == 1
        )
        assert (
            OperationalOutbox.query.filter_by(
                event_type="operational_shipment.created"
            ).count()
            == 1
        )
        with pytest.raises(service.OperationalError) as reused_quote:
            service.create_from_accepted_quote(
                payload, _user(operational_app), "create-2"
            )
        assert reused_quote.value.code == "OPERATIONAL_SHIPMENT_ALREADY_EXISTS"


def test_create_guards_quote_timeline_location_and_tenant(operational_app):
    with operational_app.app_context():
        with pytest.raises(service.OperationalError) as rejected:
            service.create_from_accepted_quote(
                _payload(operational_app, "declined"),
                _user(operational_app),
                "declined",
            )
        assert rejected.value.code == "QUOTE_NOT_ACCEPTED"
        bad = _payload(operational_app)
        bad["planned_arrival"] = bad["planned_departure"][:-6]
        with pytest.raises(service.OperationalError):
            service.create_from_accepted_quote(bad, _user(operational_app), "bad-time")
        same = _payload(operational_app)
        same["destination"] = same["origin"]
        with pytest.raises(service.OperationalError) as invalid:
            service.create_from_accepted_quote(same, _user(operational_app), "same")
        assert invalid.value.code == "INVALID_ROUTE_TIMELINE"
        with pytest.raises(service.OperationalError) as no_scope:
            service.create_from_accepted_quote(
                _payload(operational_app), {"id": 999999, "role": "expert"}, "none"
            )
        assert no_scope.value.code == "TENANT_SCOPE_VIOLATION"


def test_report_verify_correct_and_work_item_lifecycle(operational_app):
    with operational_app.app_context():
        shipment, _ = service.create_from_accepted_quote(
            _payload(operational_app), _user(operational_app), "events"
        )
        milestone = Milestone.query.filter_by(milestone_type="departure").one()
        occurred = datetime.now(timezone.utc) - timedelta(minutes=10)
        event = service.record_event(
            shipment.id,
            milestone.id,
            {"occurred_at": occurred.isoformat()},
            _user(operational_app),
            "report-1",
        )
        assert (
            event.event_type == "reported"
            and milestone.verification_state == "reported"
        )
        assert (
            service.record_event(
                shipment.id,
                milestone.id,
                {"occurred_at": occurred.isoformat()},
                _user(operational_app),
                "report-1",
            ).id
            == event.id
        )
        old_version = milestone.version
        service.verify_milestone(
            shipment.id, milestone.id, old_version, _user(operational_app, "verifier")
        )
        assert milestone.verification_state == "verified"
        with pytest.raises(service.OperationalError) as stale:
            service.verify_milestone(
                shipment.id, milestone.id, old_version, _user(operational_app)
            )
        assert stale.value.code == "STALE_AGGREGATE_VERSION"
        corrected = service.correct_milestone(
            shipment.id,
            milestone.id,
            {
                "occurred_at": occurred.isoformat(),
                "reason": "Corrected operator timestamp",
                "expected_version": milestone.version,
            },
            _user(operational_app),
            "correct-1",
        )
        assert corrected.event_type == "corrected" and corrected.supersedes_event_id
        assert MilestoneEvent.query.count() == 3


def test_reconcile_is_idempotent_and_verify_resolves_work(operational_app):
    with operational_app.app_context():
        past = datetime.now(timezone.utc) - timedelta(hours=3)
        shipment, _ = service.create_from_accepted_quote(
            _payload(
                operational_app, departure=past, arrival=past + timedelta(hours=1)
            ),
            _user(operational_app),
            "overdue",
        )
        assert service.reconcile_overdue(user_id=_user(operational_app)["id"]) == 2
        assert service.reconcile_overdue(user_id=_user(operational_app)["id"]) == 0
        milestone = Milestone.query.filter_by(milestone_type="departure").one()
        service.record_event(
            shipment.id,
            milestone.id,
            {"occurred_at": past.isoformat()},
            _user(operational_app),
            "late-report",
        )
        service.verify_milestone(
            shipment.id,
            milestone.id,
            milestone.version,
            _user(operational_app, "verifier"),
        )
        assert (
            OperationalWorkItem.query.filter_by(
                milestone_id=milestone.id, status="resolved"
            ).count()
            == 1
        )


def test_cross_tenant_detail_and_queue_are_hidden(operational_app):
    with operational_app.app_context():
        shipment, _ = service.create_from_accepted_quote(
            _payload(operational_app), _user(operational_app), "tenant"
        )
        with pytest.raises(service.OperationalError) as hidden:
            service.scoped_shipment(shipment.id, _user(operational_app, "outsider"))
        assert hidden.value.status == 404
        public_id = shipment.public_id

    response = operational_app.test_client().get(
        f"/api/operational-shipments/{public_id}",
        headers=_auth(operational_app, "outsider"),
    )
    assert response.status_code == 404
    assert response.json["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_permission_denied_and_correction_reason_required(operational_app):
    with operational_app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        membership.permissions = ["operational_shipment.read"]
        db.session.commit()
        readonly = {
            "id": operational_app.config["phase1a"]["user"],
            "role": "business_expert",
        }
        with pytest.raises(service.OperationalError) as forbidden:
            service.create_from_accepted_quote(
                _payload(operational_app), readonly, "forbidden"
            )
        assert forbidden.value.code == "FORBIDDEN_OPERATION"
        membership.permissions = [
            "operational_shipment.read",
            "operational_shipment.create",
            "milestone_event.create",
            "milestone.verify",
            "milestone.correct",
            "work_item.read",
            "work_item.manage",
        ]
        db.session.commit()
        shipment, _ = service.create_from_accepted_quote(
            _payload(operational_app), _user(operational_app), "reason"
        )
        milestone = Milestone.query.first()
        with pytest.raises(service.OperationalError) as reason:
            service.correct_milestone(
                shipment.id,
                milestone.id,
                {
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "expected_version": milestone.version,
                },
                _user(operational_app),
                "correct",
            )
        assert reason.value.code == "CORRECTION_REASON_REQUIRED"


def test_http_create_list_detail_and_error_envelopes(operational_app):
    client = operational_app.test_client()
    headers = {**_auth(operational_app), "Idempotency-Key": "http-create"}
    payload = _payload(operational_app)
    created = client.post(
        "/api/operational-shipments/from-accepted-quote", json=payload, headers=headers
    )
    assert created.status_code == 201 and created.json["meta"]["created"] is True
    replay = client.post(
        "/api/operational-shipments/from-accepted-quote", json=payload, headers=headers
    )
    assert (
        replay.status_code == 200
        and replay.json["data"]["public_id"] == created.json["data"]["public_id"]
    )
    listing = client.get(
        "/api/operational-shipments?status=planned&customer=0900&page=1&per_page=5",
        headers=_auth(operational_app),
    )
    assert listing.status_code == 200 and listing.json["meta"]["page"] == 1
    assert {
        "customer",
        "current_milestone",
        "overdue",
        "open_work_item_count",
    } <= listing.json["data"][0].keys()
    detail = client.get(
        f"/api/operational-shipments/{created.json['data']['public_id']}",
        headers=_auth(operational_app),
    )
    assert detail.status_code == 200 and "audit_summary" in detail.json["data"]
    assert detail.json["data"]["public_id"] == created.json["data"]["public_id"]
    assert set(detail.json["data"]) == {
        "public_id", "status", "operational_provenance", "scope",
        "recent_events_scope", "history_scope", "version", "customer",
        "project_public_id", "source", "route_plan", "route_leg", "route_legs",
        "current_milestone", "overdue", "overdue_since", "open_work_item_count",
        "milestones", "recent_events", "open_work_items", "audit_summary",
    }
    assert set(detail.json["data"]["source"]) == {
        "type", "accepted_quote_id", "shipment_request_id", "request_public_id",
        "quote_amount", "request_transport",
    }
    assert detail.json["data"]["source"]["request_transport"] == {
        "shipping_type": "domestic",
        "transport_method": "road",
        "domestic_transport_method": "Rail Transport",
        "international_transport_method": "Sea Freight",
        "transport_method_preference": "customer_choice",
    }
    missing = client.get(
        "/api/operational-shipments/11111111-1111-4111-8111-111111111111",
        headers=_auth(operational_app),
    )
    assert (
        missing.status_code == 404
        and missing.json["error"]["code"] == "RESOURCE_NOT_FOUND"
    )
    mismatch = dict(_payload(operational_app))
    mismatch["transport_mode"] = "rail"
    conflict = client.post(
        "/api/operational-shipments/from-accepted-quote", json=mismatch, headers=headers
    )
    assert (
        conflict.status_code == 409
        and conflict.json["error"]["code"]
        == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"
    )


def test_http_shipment_list_deduplicates_multileg_active_plan_before_pagination(
    operational_app,
):
    with operational_app.app_context():
        shipment, _ = service.create_from_accepted_quote(
            _payload(operational_app), _user(operational_app), "dedup-list"
        )
        shipment_public_id = shipment.public_id
        plan = RoutePlan.query.filter_by(
            operational_shipment_id=shipment.id, is_active=True
        ).one()
        first_leg = RouteLeg.query.filter_by(route_plan_id=plan.id).one()
        for sequence in (2, 3):
            db.session.add(
                RouteLeg(
                    route_plan_id=plan.id,
                    sequence_number=sequence,
                    origin_location_id=first_leg.origin_location_id,
                    destination_location_id=first_leg.destination_location_id,
                    origin_snapshot=first_leg.origin_snapshot,
                    destination_snapshot=first_leg.destination_snapshot,
                    transport_mode=first_leg.transport_mode,
                    planned_departure=first_leg.planned_departure
                    + timedelta(hours=sequence),
                    planned_arrival=first_leg.planned_arrival
                    + timedelta(hours=sequence),
                )
            )
        db.session.commit()

    response = operational_app.test_client().get(
        "/api/operational-shipments?page=1&per_page=1",
        headers=_auth(operational_app),
    )

    assert response.status_code == 200
    assert [row["public_id"] for row in response.json["data"]] == [shipment_public_id]
    assert response.json["meta"] == {
        "page": 1,
        "per_page": 1,
        "has_more": False,
    }


def test_request_intent_and_actual_route_modes_never_infer_or_mutate_each_other(operational_app):
    with operational_app.app_context():
        request_row = ShipmentRequest.query.one()
        request_row.domestic_transport_method = COMBINED_TRANSPORT_CODE
        db.session.commit()

        shipment, _ = service.create_from_accepted_quote(
            _payload(operational_app), _user(operational_app), "combined-route-independence"
        )
        plan = RoutePlan.query.filter_by(
            operational_shipment_id=shipment.id, is_active=True
        ).one()
        first = RouteLeg.query.filter_by(route_plan_id=plan.id).one()
        for sequence, mode in ((2, "rail"), (3, "road")):
            db.session.add(RouteLeg(
                route_plan_id=plan.id,
                sequence_number=sequence,
                origin_location_id=first.origin_location_id,
                destination_location_id=first.destination_location_id,
                origin_snapshot=first.origin_snapshot,
                destination_snapshot=first.destination_snapshot,
                transport_mode=mode,
                planned_departure=first.planned_departure + timedelta(hours=sequence),
                planned_arrival=first.planned_arrival + timedelta(hours=sequence),
            ))
        db.session.commit()

        assert project_existing_request_transport(request_row)["domestic_transport_method"] == COMBINED_TRANSPORT_CODE
        assert [leg.transport_mode for leg in RouteLeg.query.filter_by(route_plan_id=plan.id).order_by(RouteLeg.sequence_number)] == [
            "road", "rail", "road",
        ]

        first.transport_mode = "sea"
        db.session.commit()
        assert project_existing_request_transport(request_row)["domestic_transport_method"] == COMBINED_TRANSPORT_CODE

        request_row.domestic_transport_method = "Road Transport"
        db.session.commit()
        assert project_existing_request_transport(request_row)["domestic_transport_method"] == "Road Transport"
        assert [leg.transport_mode for leg in RouteLeg.query.filter_by(route_plan_id=plan.id).order_by(RouteLeg.sequence_number)] == [
            "sea", "rail", "road",
        ]

        invalid_payload = _direct_payload(operational_app)
        invalid_payload["route"]["transport_mode"] = COMBINED_TRANSPORT_CODE
        with pytest.raises(service.OperationalError) as invalid:
            service.create_direct(invalid_payload, _user(operational_app), "combined-is-not-a-leg")
        assert invalid.value.code == "VALIDATION_FAILED"


def test_http_permission_validation_transition_and_stale_conflicts(operational_app):
    with operational_app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        membership.permissions = ["operational_shipment.read"]
        db.session.commit()
    forbidden = operational_app.test_client().post(
        "/api/operational-shipments/from-accepted-quote",
        json=_payload(operational_app),
        headers={**_auth(operational_app), "Idempotency-Key": "forbidden-http"},
    )
    assert (
        forbidden.status_code == 403
        and forbidden.json["error"]["code"] == "FORBIDDEN_OPERATION"
    )
    with operational_app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        membership.permissions = [
            "operational_shipment.read",
            "operational_shipment.create",
            "milestone_event.create",
            "milestone.verify",
            "milestone.correct",
            "work_item.read",
            "work_item.manage",
        ]
        db.session.commit()
    invalid = _payload(operational_app)
    invalid["planned_arrival"] = "invalid"
    response = operational_app.test_client().post(
        "/api/operational-shipments/from-accepted-quote",
        json=invalid,
        headers={**_auth(operational_app), "Idempotency-Key": "invalid-http"},
    )
    assert (
        response.status_code == 422
        and response.json["error"]["code"] == "INVALID_ROUTE_TIMELINE"
        and "traceback" not in response.get_data(as_text=True).lower()
    )


def test_opaque_shipment_http_boundary_is_tenant_scoped(operational_app):
    client = operational_app.test_client()
    created = client.post(
        "/api/operational-shipments/from-accepted-quote",
        json=_payload(operational_app),
        headers={**_auth(operational_app), "Idempotency-Key": "opaque-boundary"},
    )
    assert created.status_code == 201
    public_id = created.json["data"]["public_id"]

    for suffix in ("", "/route-plans", "/timeline", "/route-exceptions"):
        same_tenant = client.get(
            f"/api/operational-shipments/{public_id}{suffix}",
            headers=_auth(operational_app),
        )
        assert same_tenant.status_code == 200
        cross_tenant = client.get(
            f"/api/operational-shipments/{public_id}{suffix}",
            headers=_auth(operational_app, "outsider"),
        )
        assert cross_tenant.status_code == 404
        assert cross_tenant.json["error"]["code"] == "RESOURCE_NOT_FOUND"

    numeric = client.get("/api/operational-shipments/1", headers=_auth(operational_app))
    unknown = client.get(
        "/api/operational-shipments/11111111-1111-4111-8111-111111111111",
        headers=_auth(operational_app),
    )
    assert numeric.status_code == 404
    assert unknown.status_code == 404
    assert "id" not in created.json["data"]


def test_legacy_operational_openapi_exact_runtime_parity_and_opacity(operational_app):
    text = (
        Path(__file__).resolve().parents[2] / "docs" / "openapi" / "openapi.yaml"
    ).read_text(encoding="utf-8")
    documented: dict[str, set[str]] = {}
    current = None
    for line in text.splitlines():
        match = re.match(
            r"^  (/api/(?:operational-shipments|operational-work-items)[^:]*):\s*$",
            line,
        )
        if match:
            current = match.group(1)
            documented[current] = set()
            continue
        if re.match(r"^  /api/", line):
            current = None
        method = re.match(r"^    (get|post|patch|delete):", line)
        if current and method:
            documented[current].add(method.group(1).upper())
    runtime: dict[str, set[str]] = {}
    for rule in operational_app.url_map.iter_rules():
        if not rule.endpoint.startswith("operations."):
            continue
        path = re.sub(r"<(?:(?:int|uuid):)?([^>]+)>", r"{\1}", str(rule))
        if path.startswith(
            ("/api/operational-shipments", "/api/operational-work-items")
        ):
            runtime.setdefault(path, set()).update(
                set(rule.methods) - {"HEAD", "OPTIONS"}
            )
    assert documented == runtime
    assert "format: uuid" in text
    assert "Numeric database IDs are rejected" in text
    assert "/api/operational-shipments/by-public-id" not in text
