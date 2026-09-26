"""Slice 4 HTTP authority, allowlist, failures and global filter continuation."""
import json

import pytest
from datetime import datetime, timezone
from sqlalchemy import update

from backend.extensions import db
from backend.notification_models import NotificationAction, NotificationAttempt
from backend.services.auth_session_service import create_session_tokens
from backend.services import control_tower_sources as sources
from backend.routes import control_tower as control_tower_route
from backend.services.attention_truth_contract import build_attention_truth_contract
from backend.services.control_tower_translation import AttentionLevel, EMPTY_MESSAGE, UNAVAILABLE_MESSAGE
from backend.services.control_tower_read_model import DisplayReason, DisplayTime
from backend.tests.test_control_tower_scope import tower  # noqa: F401
from backend.tests.test_control_tower_sources import attention  # noqa: F401
from backend.tests.test_control_tower_read_model import add_leg, reason, stub
from backend.operational_models import CanonicalLocation, OperationalShipment

PATH = "/api/control-tower/shipments"


def test_shared_truth_contract_canonicalizes_equivalent_offsets_to_utc():
    values = {
        "shipment_public_id": "shipment-a",
        "situation_identity_key": "situation-a",
        "policy_id": "policy-a",
        "policy_version": "3",
        "source_watermark": "opaque-watermark",
        "urgency": "HIGH",
        "severity": "HIGH",
        "priority": "HIGH",
    }
    local = build_attention_truth_contract(
        **values, calculated_at="2026-09-26T11:30:00+03:30"
    )
    utc = build_attention_truth_contract(
        **values, calculated_at="2026-09-26T08:00:00+00:00"
    )
    assert local == utc
    assert local["freshness"]["calculated_at"] == "2026-09-26T08:00:00+00:00"


def test_reason_serializes_opaque_shared_truth_contract():
    truth = {
        "fingerprint": "sha256:" + "a" * 64,
        "contract_version": "attention-truth-v1",
        "rank": {
            "policy_id": "policy-a",
            "policy_version": "3",
            "urgency": "HIGH",
            "severity": "HIGH",
            "priority": "HIGH",
        },
        "freshness": {
            "status": "FRESH",
            "calculated_at": "2026-09-26T08:00:00+00:00",
            "source_watermark": "opaque-watermark",
        },
    }
    serialized = control_tower_route._reason(DisplayReason(
        "exception_open",
        "urgent",
        "اقدام فوری",
        "استثنای باز",
        "نیاز به بررسی",
        (DisplayTime("وقوع", datetime(2026, 9, 26, 8, tzinfo=timezone.utc)),),
        truth,
    ))
    assert serialized["truth"] == {
        "fingerprint": truth["fingerprint"],
        "contractVersion": "attention-truth-v1",
        "rank": {
            "policyId": "policy-a",
            "policyVersion": "3",
            "urgency": "HIGH",
            "severity": "HIGH",
            "priority": "HIGH",
        },
        "freshness": {
            "status": "FRESH",
            "calculatedAt": "2026-09-26T08:00:00+00:00",
            "sourceWatermark": "opaque-watermark",
        },
    }


def headers(actor):
    return {"Authorization": "Bearer " + create_session_tokens(actor.id)["access_token"]}


def seed(tower, monkeypatch):
    own, request = tower.shipment()
    other, _ = tower.shipment(source="direct", owner=tower.b)
    foreign, _ = tower.shipment(owner=tower.foreign, tenant=tower.foreign_org)
    stub(monkeypatch, {row.id: (reason(str(row.id)),) for row in (own, other, foreign)})
    return own, other, foreign, request


def test_expert_admin_foreign_scope_and_platform_denial(tower, monkeypatch):
    own, other, foreign, _ = seed(tower, monkeypatch)
    client = tower.app.test_client()
    for actor, expected in [(tower.a, {own.public_id}), (tower.b, {other.public_id}),
                            (tower.admin, {own.public_id, other.public_id}),
                            (tower.foreign, {foreign.public_id})]:
        response = client.get(PATH, headers=headers(actor))
        assert response.status_code == 200
        data = response.json["data"]
        assert {item["key"] for item in data["items"]} == expected
        assert data["summary"]["total"] == len(expected)
        assert sum(data["summary"]["attentionCounts"].values()) == len(expected)
        assert data["page"] == {
            "limit": 25,
            "offset": 0,
            "returned": len(expected),
            "hasMore": False,
            "nextCursor": None,
        }
        assert response.headers["Cache-Control"] == "private, no-store"
    denied = client.get(PATH, headers=headers(tower.platform))
    assert denied.status_code == 403 and "items" not in denied.json
    assert client.get(PATH).status_code == 401


@pytest.mark.parametrize("source", ["accepted_quote", "direct"])
def test_request_or_owner_mutation_cannot_transfer_fixed_scope(tower, monkeypatch, source):
    shipment, request = tower.shipment(source=source)
    stub(monkeypatch, {shipment.id: (reason("one"),)})
    client = tower.app.test_client()
    old, new = headers(tower.a), headers(tower.b)
    assert len(client.get(PATH, headers=old).json["data"]["items"]) == 1
    if request:
        request.assigned_to = tower.b.id
        db.session.commit()
    else:
        shipment.primary_responsible_expert_id = tower.b.id
        with pytest.raises(ValueError, match="responsible Expert is immutable"):
            db.session.commit()
        db.session.rollback()
    assert len(client.get(PATH, headers=old).json["data"]["items"]) == 1
    assert client.get(PATH, headers=new).json["data"]["items"] == []


def test_complete_empty_and_failure_are_distinct(tower, monkeypatch):
    client, auth = tower.app.test_client(), headers(tower.a)
    monkeypatch.setattr(
        control_tower_route.oip_service,
        "projection_health_for_organization",
        lambda _organization_id: {
            "health_state": "FRESH",
            "trustworthy": True,
            "checked_at": "2026-09-24T12:00:00+00:00",
            "last_evaluation_attempt_at": "2026-09-24T12:00:00+00:00",
            "last_evaluation_success_at": "2026-09-24T12:00:00+00:00",
            "next_evaluation_due_at": None,
            "reason_code": None,
            "reason": None,
            "last_run": None,
        },
    )
    response = client.get(PATH, headers=auth)
    assert response.status_code == 200
    assert response.json["data"]["emptyMessage"] == EMPTY_MESSAGE
    assert response.json["data"]["page"]["nextCursor"] is None
    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE-source-stack")
    monkeypatch.setattr(sources, "evaluate_bounded_sources", fail)
    response = client.get(PATH, headers=auth)
    assert response.status_code == 503
    assert response.json == {"error": {"code": "EVALUATION_UNAVAILABLE", "message": UNAVAILABLE_MESSAGE}}


def test_stale_empty_result_never_claims_healthy_operations(tower):
    response = tower.app.test_client().get(PATH, headers=headers(tower.a))
    assert response.status_code == 200
    data = response.json["data"]
    assert data["attentionEvaluation"]["state"] == "STALE"
    assert data["attentionEvaluation"]["trustworthy"] is False
    assert data["emptyMessage"] != EMPTY_MESSAGE
    assert "Attention" in data["emptyMessage"]


def test_invalid_responsibility_not_successful_empty(tower):
    shipment, _ = tower.shipment(source="direct")
    db.session.execute(update(OperationalShipment).where(
        OperationalShipment.id == shipment.id
    ).values(primary_responsible_expert_id=tower.foreign.id))
    db.session.commit()
    response = tower.app.test_client().get(PATH, headers=headers(tower.admin))
    assert response.status_code == 503
    assert response.json["error"]["message"] == UNAVAILABLE_MESSAGE


def test_cursor_round_trip_invalid_and_changed_filter(tower, monkeypatch):
    rows = [tower.shipment(source="direct")[0] for _ in range(3)]
    stub(monkeypatch, {row.id: (reason(str(row.id)),) for row in rows})
    client, auth = tower.app.test_client(), headers(tower.a)
    first = client.get(PATH, query_string={"page_size": 1}, headers=auth).json["data"]
    second = client.get(PATH, query_string={"page_size": 1, "cursor": first["page"]["nextCursor"]}, headers=auth)
    assert second.status_code == 200
    assert second.json["data"]["items"][0]["key"] != first["items"][0]["key"]
    for cursor, extra in [
        ("tampered", {}),
        (first["page"]["nextCursor"], {"attention": "follow_up"}),
        (first["page"]["nextCursor"], {"search": "changed"}),
    ]:
        response = client.get(PATH, query_string={"page_size": 1, "cursor": cursor, **extra}, headers=auth)
        assert response.status_code == 400 and response.json["error"]["code"] == "INVALID_CURSOR"


def test_attention_filter_evaluates_full_result_before_pagination(tower, monkeypatch):
    rows = [tower.shipment(source="direct")[0] for _ in range(5)]
    levels = [AttentionLevel.URGENT, AttentionLevel.FOLLOW_UP, AttentionLevel.REVIEW,
              AttentionLevel.REVIEW, AttentionLevel.REVIEW]
    stub(monkeypatch, {row.id: (reason(str(row.id), level=level),) for row, level in zip(rows, levels)})
    client, auth = tower.app.test_client(), headers(tower.a)
    cursor, found = None, []
    while True:
        query = {"page_size": 1, "attention": "review"}
        if cursor:
            query["cursor"] = cursor
        response = client.get(PATH, query_string=query, headers=auth)
        assert response.status_code == 200
        data = response.json["data"]
        assert all(item["attention"] == "review" for item in data["items"])
        found.extend(item["key"] for item in data["items"])
        cursor = data["page"]["nextCursor"]
        if not cursor:
            break
    assert set(found) == {row.public_id for row in rows[2:]} and len(found) == 3


def test_search_is_server_side_authorized_and_reports_full_matching_total(tower, monkeypatch):
    own, own_request = tower.shipment()
    other, _ = tower.shipment(source="direct", owner=tower.b)
    foreign, foreign_request = tower.shipment(owner=tower.foreign, tenant=tower.foreign_org)
    stub(monkeypatch, {
        own.id: (reason("own"),),
        other.id: (reason("other"),),
        foreign.id: (reason("foreign"),),
    })
    client = tower.app.test_client()
    by_reference = client.get(
        PATH, query_string={"search": own.public_id}, headers=headers(tower.admin)
    ).json["data"]
    assert by_reference["summary"]["total"] == 1
    assert [item["key"] for item in by_reference["items"]] == [own.public_id]
    by_request = client.get(
        PATH,
        query_string={"search": own_request.public_id},
        headers=headers(tower.admin),
    ).json["data"]
    assert by_request["summary"]["total"] == 1
    assert by_request["items"][0]["key"] == own.public_id
    hidden = client.get(
        PATH,
        query_string={"search": foreign_request.public_id},
        headers=headers(tower.admin),
    ).json["data"]
    assert hidden["summary"]["total"] == 0 and hidden["items"] == []


@pytest.mark.parametrize("query", [
    {"page_size": "bad"},
    {"page_size": 0},
    {"page_size": 101},
    {"attention": "HIGH"},
    {"search": "x" * 101},
])
def test_invalid_query_fails_safely(tower, query):
    response = tower.app.test_client().get(PATH, query_string=query, headers=headers(tower.a))
    assert response.status_code == 400 and "items" not in response.json


def test_real_source_response_allowlist_and_direct_capability_unchanged(attention):
    attention.execution()
    tower = attention.tower
    client, auth = tower.app.test_client(), headers(tower.a)
    response = client.get(PATH, headers=auth)
    assert response.status_code == 200
    item, = response.json["data"]["items"]
    assert set(item) == {
        "key", "shipmentReference", "routeLabel", "transportLabel",
        "actualRouteModes", "operationalStatus", "source",
        "requestTransport", "progress", "workSummary", "attention",
        "attentionLabel", "ownerName", "primaryReason", "additionalReasons",
        "destination",
    }
    assert set(item["primaryReason"]) == {"semantic", "title", "explanation", "time"}
    serialized = json.dumps(response.json)
    for value in ("source_identity", "OperationalDelay", "OperationalWorkItem", "provenance",
                  "revenue", "cost", "margin", "financial", "PRIVATE", "organization_id"):
        assert value not in serialized
    assert tower.am.permissions == ["operational_shipment.read"]
    assert client.get(f"/api/v2/operational-shipments/{item['key']}/execution/delays", headers=auth).status_code == 200
    assert client.get("/api/operational-work-items", headers=auth).status_code == 403
    assert client.get("/api/oip/attention", headers=auth).status_code == 403


def test_ct_gate_003_current_road_rail_route_serializes_combined_transport(attention):
    attention.execution()
    first, middle = add_leg(attention, mode="road")
    end = CanonicalLocation(source_type="city", source_id=99,
                            location_type="city", display_name="آنکارا")
    second, _ = add_leg(attention, sequence=2, origin=middle, destination=end, mode="rail")
    assert first.destination_location_id == second.origin_location_id
    assert attention.plan.is_active and attention.plan.status == "active"
    response = attention.tower.app.test_client().get(PATH, headers=headers(attention.tower.a))
    assert response.status_code == 200
    assert response.json["data"]["state"] == "complete"
    item, = response.json["data"]["items"]
    assert item["routeLabel"] == "تهران → آنکارا"
    assert item["transportLabel"] == "ترکیبی"
    assert item["actualRouteModes"] == ["road", "rail"]


def test_source_status_request_transport_and_notification_isolation(attention):
    attention.execution()
    attention.request.shipping_type = "international"
    attention.request.transport_method = "road"
    attention.request.international_transport_method = "sea"
    attention.request.domestic_transport_method = "rail"
    attention.request.transport_method_preference = "sea"
    db.session.commit()

    response = attention.tower.app.test_client().get(
        PATH, headers=headers(attention.tower.a)
    )
    assert response.status_code == 200
    item, = response.json["data"]["items"]
    assert item["shipmentReference"] == attention.shipment.public_id
    assert item["operationalStatus"] == "planned"
    assert item["source"] == {
        "type": "accepted_quote",
        "requestPublicId": attention.request.public_id,
    }
    assert item["requestTransport"] == {
        "shippingType": "international",
        "transportMethod": "road",
        "internationalTransportMethod": "sea",
        "domesticTransportMethod": "rail",
        "transportMethodPreference": "sea",
    }
    assert NotificationAction.query.count() == 0
    assert NotificationAttempt.query.count() == 0
    assert "notification" not in json.dumps(response.json).lower()


def test_revoked_expert_capability_is_governed_denial(tower):
    tower.shipment(source="direct")
    tower.am.permissions = []
    db.session.commit()
    response = tower.app.test_client().get(PATH, headers=headers(tower.a))
    assert response.status_code == 403
    assert response.json["error"]["code"] == "FORBIDDEN_OPERATION"
