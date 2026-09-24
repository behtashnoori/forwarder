"""Operational Workspace Phase 1 authorization and projection contracts."""

from datetime import datetime, timedelta, timezone

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import (
    Milestone,
    OperationalMembership,
    OperationalShipment,
    OperationalWorkItem,
)
from backend.services import operational_service as service
from backend.tests.test_operational_vertical_slice import (
    _auth,
    _auth_user,
    _direct_payload,
    _payload,
    _user,
    operational_app,
)


def _create_workspace_shipment(app, key="workspace"):
    departure = datetime.now(timezone.utc) + timedelta(hours=2)
    shipment, _ = service.create_from_accepted_quote(
        _payload(
            app,
            departure=departure,
            arrival=departure + timedelta(hours=6),
        ),
        _user(app),
        key,
    )
    return shipment


def _same_org_peer(app) -> int:
    ids = app.config["phase1a"]
    owner_membership = OperationalMembership.query.filter_by(
        user_id=ids["user"]
    ).one()
    peer = ExpertUser(
        username="workspace-peer",
        password_hash="unused",
        full_name="Workspace Peer",
        role="expert",
        authority="EXPERT",
        is_active=True,
    )
    db.session.add(peer)
    db.session.flush()
    db.session.add(
        OperationalMembership(
            organization_id=ids["org"],
            user_id=peer.id,
            permissions=list(owner_membership.permissions or []),
        )
    )
    db.session.commit()
    return peer.id


def test_workspace_requires_authentication_and_shipment_read(operational_app):
    client = operational_app.test_client()
    assert client.get("/api/operational-workspace").status_code == 401

    with operational_app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        membership.permissions = [
            permission
            for permission in membership.permissions
            if permission != "operational_shipment.read"
        ]
        db.session.commit()

    denied = client.get(
        "/api/operational-workspace", headers=_auth(operational_app)
    )
    assert denied.status_code == 403
    assert denied.json["error"]["code"] == "FORBIDDEN_OPERATION"


def test_workspace_fixed_owner_survives_request_reassignment(operational_app):
    with operational_app.app_context():
        shipment = _create_workspace_shipment(operational_app)
        shipment_public_id = shipment.public_id
        peer_id = _same_org_peer(operational_app)
        request_row = db.session.get(ShipmentRequest, shipment.shipment_request_id)
        request_row.assigned_to = peer_id
        db.session.commit()
        assert shipment.primary_responsible_expert_id == operational_app.config[
            "phase1a"
        ]["user"]

    client = operational_app.test_client()
    owner = client.get(
        "/api/operational-workspace", headers=_auth(operational_app)
    )
    assert owner.status_code == 200
    assert owner.json["meta"]["active_shipment_count"] == 1
    owner_card, = owner.json["data"]["active_shipments"]
    assert owner_card["public_id"] == shipment_public_id
    assert owner_card["responsible_expert"] == {
        "display_name": "Phase1A Operator"
    }
    assert "id" not in (owner_card.get("customer") or {})

    peer = client.get(
        "/api/operational-workspace", headers=_auth_user(operational_app, peer_id)
    )
    assert peer.status_code == 200
    assert peer.json["meta"]["active_shipment_count"] == 0
    assert peer.json["data"]["active_shipments"] == []

    foreign = client.get(
        "/api/operational-workspace", headers=_auth(operational_app, "outsider")
    )
    assert foreign.status_code == 200
    assert foreign.json["meta"]["active_shipment_count"] == 0
    assert foreign.json["data"]["active_shipments"] == []


def test_workspace_uses_existing_follow_up_and_event_facts(operational_app):
    now = datetime.now(timezone.utc)
    with operational_app.app_context():
        shipment = _create_workspace_shipment(operational_app, "workspace-facts")
        milestone = Milestone.query.filter_by(
            operational_shipment_id=shipment.id,
            milestone_type="departure",
        ).one()
        service.record_event(
            shipment.public_id,
            milestone.id,
            {"occurred_at": now.isoformat()},
            _user(operational_app),
            "workspace-event",
        )
        db.session.add_all(
            [
                OperationalWorkItem(
                    organization_id=shipment.organization_id,
                    operational_shipment_id=shipment.id,
                    milestone_id=milestone.id,
                    work_type="OVERDUE_MILESTONE",
                    severity="critical",
                    detected_at=now - timedelta(minutes=10),
                    due_at=now - timedelta(minutes=5),
                    reason="existing operational follow-up",
                ),
                OperationalWorkItem(
                    organization_id=shipment.organization_id,
                    operational_shipment_id=shipment.id,
                    milestone_id=milestone.id,
                    work_type="OVERDUE_MILESTONE",
                    status="resolved",
                    severity="warning",
                    detected_at=now - timedelta(hours=2),
                    due_at=now - timedelta(hours=1),
                    reason="resolved source fact",
                ),
            ]
        )
        db.session.commit()
        shipment_public_id = shipment.public_id

    client = operational_app.test_client()
    response = client.get(
        "/api/operational-workspace", headers=_auth(operational_app)
    )
    repeat = client.get(
        "/api/operational-workspace", headers=_auth(operational_app)
    )

    assert response.status_code == 200
    assert response.json["meta"]["attention_available"] is True
    assert response.json["meta"]["open_follow_up_count"] == 1
    attention, = response.json["data"]["attention_items"]
    assert attention["identity"] == repeat.json["data"]["attention_items"][0][
        "identity"
    ]
    assert attention["shipment"]["public_id"] == shipment_public_id
    assert attention["kind"] == "OVERDUE_MILESTONE"
    assert attention["severity"] == "critical"
    assert "level" not in attention
    assert attention["source"] == {
        "type": "OperationalWorkItem",
        "version": 1,
        "status": "open",
    }
    assert attention["source_path"] == (
        f"/operations/shipments/{shipment_public_id}"
    )
    update, = response.json["data"]["recent_updates"]
    assert update["shipment_public_id"] == shipment_public_id
    assert update["occurred_at"] and update["recorded_at"]
    card, = response.json["data"]["active_shipments"]
    assert card["route_summary"]["origin"]["display_name"] == "مبدأ"
    assert card["route_summary"]["destination"]["display_name"] == "مقصد"
    assert set(card["route_summary"]["origin"]) == {"display_name"}
    assert set(card["route_summary"]["destination"]) == {"display_name"}
    assert card["route_summary"]["transport_modes"] == ["road"]
    assert card["route_summary"]["leg_count"] == 1
    assert card["latest_update"]["recorded_at"] == update["recorded_at"]


def test_workspace_does_not_disclose_followups_without_existing_permission(
    operational_app,
):
    now = datetime.now(timezone.utc)
    with operational_app.app_context():
        shipment = _create_workspace_shipment(
            operational_app, "workspace-no-work-permission"
        )
        milestone = Milestone.query.filter_by(
            operational_shipment_id=shipment.id,
            milestone_type="departure",
        ).one()
        db.session.add(
            OperationalWorkItem(
                organization_id=shipment.organization_id,
                operational_shipment_id=shipment.id,
                milestone_id=milestone.id,
                work_type="OVERDUE_MILESTONE",
                severity="critical",
                detected_at=now - timedelta(minutes=10),
                due_at=now - timedelta(minutes=5),
                reason="not visible without WorkItem read",
            )
        )
        membership = OperationalMembership.query.filter_by(
            user_id=operational_app.config["phase1a"]["user"]
        ).one()
        membership.permissions = [
            permission
            for permission in membership.permissions
            if permission != "work_item.read"
        ]
        db.session.commit()

    response = operational_app.test_client().get(
        "/api/operational-workspace", headers=_auth(operational_app)
    )
    assert response.status_code == 200
    assert response.json["meta"]["attention_available"] is False
    assert response.json["meta"]["open_follow_up_count"] is None
    assert response.json["data"]["attention_items"] == []
    card, = response.json["data"]["active_shipments"]
    assert card["open_work_item_count"] is None


def test_active_shipment_filter_and_validation(operational_app):
    with operational_app.app_context():
        active, _ = service.create_direct(
            _direct_payload(operational_app),
            _user(operational_app),
            "active-filter",
        )
        active_public_id = active.public_id
        terminal = _create_workspace_shipment(operational_app, "terminal-filter")
        terminal.lifecycle_status = "completed"
        terminal_public_id = terminal.public_id
        db.session.commit()

    client = operational_app.test_client()
    active_response = client.get(
        "/api/operational-shipments?active=true",
        headers=_auth(operational_app),
    )
    assert active_response.status_code == 200
    assert [row["public_id"] for row in active_response.json["data"]] == [
        active_public_id
    ]

    terminal_response = client.get(
        "/api/operational-shipments?active=false",
        headers=_auth(operational_app),
    )
    assert terminal_response.status_code == 200
    assert [row["public_id"] for row in terminal_response.json["data"]] == [
        terminal_public_id
    ]

    invalid = client.get(
        "/api/operational-shipments?active=yes",
        headers=_auth(operational_app),
    )
    assert invalid.status_code == 422
    assert invalid.json["error"]["code"] == "VALIDATION_FAILED"


def test_workspace_limit_is_bounded_and_counts_full_authorized_population(
    operational_app,
):
    with operational_app.app_context():
        _create_workspace_shipment(operational_app, "workspace-limit-quote")
        service.create_direct(
            _direct_payload(operational_app),
            _user(operational_app),
            "workspace-limit-direct",
        )

    client = operational_app.test_client()
    response = client.get(
        "/api/operational-workspace?limit=1", headers=_auth(operational_app)
    )
    assert response.status_code == 200
    assert response.json["meta"]["active_shipment_count"] == 2
    assert len(response.json["data"]["active_shipments"]) == 1

    for value in ("0", "21", "not-an-integer"):
        invalid = client.get(
            f"/api/operational-workspace?limit={value}",
            headers=_auth(operational_app),
        )
        assert invalid.status_code == 422
        assert invalid.json["error"]["code"] == "VALIDATION_FAILED"
