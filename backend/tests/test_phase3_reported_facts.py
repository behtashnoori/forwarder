"""Reported facts preserve history, authority and independent safe projections."""
from datetime import datetime, timezone
import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem
from backend.models import Customer, CustomerGamification, ExpertUser
from backend.operational_models import OperationalEvent, OperationalShipment, OperationalWorkItem, OperationalMembership, RouteStageExecution, ExecutionUnit
from backend.reported_fact_models import OperationalEventReportContext, SOURCES
from backend.services import reported_fact_service as reports, customer_entitlement_service as entitlements
from backend.services import execution_unit_service, tracking_projection_service
from backend.services.operational_service import OperationalError
from backend.tests.test_operational_vertical_slice import _auth, _user, operational_app
from backend.tests.test_phase3_cargo_allocation import _fixture, _set


def setup(app):
    ctx = _fixture(app, second_stage=True)
    ids = app.config["phase1a"]
    cargo_a = db.session.scalar(select(ShipmentCargoItem).where(ShipmentCargoItem.public_id == ctx["cargo"]))
    customer_b = Customer(company_name="SECRET-CUSTOMER-B", ownership_scope="TENANT",
                          operational_organization_id=ids["org"], status="active")
    accounts = [CustomerGamification(email=f"reported-{i}@example.test", phone=f"0900700000{i}", operational_organization_id=ids["org"]) for i in range(2)]
    db.session.add_all([customer_b, *accounts]); db.session.flush()
    cargo_b = ShipmentCargoItem(operational_shipment_id=ctx["shipment_id"], line_number=2,
        cargo_owner_customer_id=customer_b.id, cargo_type_id=cargo_a.cargo_type_id, uom_id=cargo_a.uom_id,
        quantity=25, planned_quantity=25, actual_quantity=25, display_name_snapshot="SECRET-CARGO-B",
        cargo_type_code_snapshot=cargo_a.cargo_type_code_snapshot, cargo_type_fa_snapshot=cargo_a.cargo_type_fa_snapshot,
        cargo_type_en_snapshot=cargo_a.cargo_type_en_snapshot, uom_code_snapshot=cargo_a.uom_code_snapshot,
        uom_symbol_snapshot=cargo_a.uom_symbol_snapshot, created_by=ids["user"], updated_by=ids["user"])
    db.session.add(cargo_b); db.session.flush()
    for account, customer in zip(accounts, [ids["customer"], customer_b.id]):
        entitlements.grant(ids["org"], ids["verifier"], {"portal_account_public_id": account.public_id,
            "customer_id": customer}, str(uuid4()))
    units = [db.session.scalar(select(RouteStageExecution).where(RouteStageExecution.public_id == ctx[name])).execution_unit for name in ("first", "second")]
    _set(app, ctx, ctx["first"], "ACTUAL", 55, 0, "report-own-allocation")
    db.session.commit()
    ctx.update(cargo_b=cargo_b.public_id, accounts=[a.id for a in accounts], units=[u.public_id for u in units])
    return ctx


def payload(ctx, **changes):
    return {"scope": "EXECUTION_UNIT", "target_public_id": ctx["units"][0], "kind": "LOCATION",
        "source": "CARRIER_REPORT", "occurred_at": "2026-09-20T08:30:00+03:30",
        "location": {"location_text": "نزدیک مرز A"}, "impacted_cargo_public_ids": [ctx["cargo"]], **changes}


def record(app, ctx, data=None, key=None):
    row, created = reports.create(ctx["shipment"], _user(app), data or payload(ctx), key or str(uuid4()))
    db.session.commit()
    return row, created


def test_two_units_late_correction_sources_history_and_no_side_effects(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        unit = db.session.scalar(select(ExecutionUnit).where(ExecutionUnit.public_id == ctx["units"][0]))
        before = (unit.version, unit.lifecycle_status, unit.latest_checkpoint, OperationalWorkItem.query.count())
        first, _ = record(app, ctx)
        second, _ = record(app, ctx, payload(ctx, target_public_id=ctx["units"][1], source="DRIVER_REPORT",
            location={"location_text": "نزدیک مرز B"}, impacted_cargo_public_ids=[]))
        for source in ("INTERNAL_EXPERT", "OTHER_OPERATIONAL_SOURCE"):
            record(app, ctx, payload(ctx, source=source, scope="SHIPMENT", target_public_id=None,
                kind="PROGRESS", location=None, impacted_cargo_public_ids=[]))
        correction, _ = record(app, ctx, payload(ctx, corrects_public_id=first.event.public_id,
            reason="اصلاح گزارش راننده", location={"location_text": "مرز اصلاح‌شده"}, occurred_at="2026-09-19T07:00:00Z"))
        result = reports.listing(ctx["shipment"], _user(app))
        assert len(result["reported_locations"]) == 2
        assert {x["location"] for x in result["reported_locations"]} == {"مرز اصلاح‌شده", "نزدیک مرز B"}
        assert {x["scope"] for x in result["reported_locations"]} == {"EXECUTION_UNIT"}
        assert {x["source"] for x in result["items"]} == set(SOURCES)
        original = next(x for x in result["items"] if x["public_id"] == first.event.public_id)
        revised = next(x for x in result["items"] if x["public_id"] == correction.event.public_id)
        assert original["status"] == "SUPERSEDED" and original["location"] == "نزدیک مرز A"
        assert revised["status"] == "CURRENT" and revised["reason"] == "اصلاح گزارش راننده"
        assert revised["corrects_public_id"] == original["public_id"]
        assert original["occurred_at"] == "2026-09-20T05:00:00Z"
        assert revised["occurred_at"] < revised["recorded_at"] and revised["recorded_at"].endswith("Z")
        db.session.refresh(unit)
        assert before == (unit.version, unit.lifecycle_status, unit.latest_checkpoint, OperationalWorkItem.query.count())
        assert execution_unit_service.timeline(unit, {})["meta"]["total"] == 0
        assert tracking_projection_service._effective_events([first.event, second.event, correction.event]) == []


def test_customer_safe_explicit_fallback_no_impact_and_current_entitlement(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        a, b = [db.session.get(CustomerGamification, i) for i in ctx["accounts"]]
        own, _ = record(app, ctx, payload(ctx, internal_note="SECRET-INTERNAL-CAUSE", customer_message="بار شما در حال حرکت است."))
        hidden, _ = record(app, ctx, payload(ctx, scope="CARGO", target_public_id=ctx["cargo_b"],
            location={"location_text": "SECRET-B-LOCATION"}, impacted_cargo_public_ids=[ctx["cargo_b"]]))
        effect, _ = record(app, ctx, payload(ctx, scope="CARGO", target_public_id=ctx["cargo_b"], kind="EFFECT",
            customer_effect="DELAY", internal_note="SECRET-CUSTOMER-B SECRET-CARGO-B SECRET-CAUSE",
            location={"location_text": "SECRET-B-LOCATION"}))
        generic, _ = record(app, ctx, payload(ctx, kind="TRANSPORT_CHANGE", location=None))
        foreign_unit, _ = record(app, ctx, payload(ctx, target_public_id=ctx["units"][1], location={"location_text": "SECRET-OTHER-UNIT"}))
        projected = reports.customer_timeline(shipment, a)
        items = {x["public_id"]: x for x in projected}
        assert hidden.event.public_id not in items
        assert items[own.event.public_id]["message"] == "بار شما در حال حرکت است."
        assert items[own.event.public_id]["reported_location"] == "نزدیک مرز A"
        assert items[effect.event.public_id]["message"] == reports.DELAY_MESSAGE
        assert items[effect.event.public_id]["reported_location"] is None
        assert items[generic.event.public_id]["message"] == reports.GENERIC_MESSAGE
        assert items[foreign_unit.event.public_id]["reported_location"] is None
        assert "SECRET" not in json.dumps(projected, ensure_ascii=False)
        assert {x["public_id"] for x in reports.customer_timeline(shipment, b)} == {hidden.event.public_id}
        grant = entitlements.configuration(app.config["phase1a"]["org"], app.config["phase1a"]["verifier"])["grants"]
        a_grant = next(x for x in grant if x["portal_account_public_id"] == a.public_id)
        entitlements.revoke(app.config["phase1a"]["org"], app.config["phase1a"]["verifier"], a_grant["public_id"])
        db.session.commit()
        assert reports.customer_timeline(shipment, a) == []


def test_customer_filter_precedes_limit_and_route_relevance(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        own, _ = record(app, ctx, payload(ctx, scope="ROUTE_STAGE", target_public_id=str(ctx["leg"])))
        for i in range(3):
            record(app, ctx, payload(ctx, scope="CARGO", target_public_id=ctx["cargo_b"],
                occurred_at=f"2026-09-21T0{i}:00:00Z", impacted_cargo_public_ids=[ctx["cargo_b"]]))
        rows = reports.customer_timeline(db.session.get(OperationalShipment, ctx["shipment_id"]),
            db.session.get(CustomerGamification, ctx["accounts"][0]), limit=1)
        assert len(rows) == 1 and rows[0]["public_id"] == own.event.public_id
        assert rows[0]["reported_location"] == "نزدیک مرز A"


def test_replay_correction_conflict_and_immutable_original(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        row, _ = record(app, ctx, key="same-command")
        replay, created = record(app, ctx, key="same-command")
        assert replay.operational_event_id == row.operational_event_id and not created
        with pytest.raises(OperationalError) as caught:
            record(app, ctx, payload(ctx, source="DRIVER_REPORT"), "same-command")
        assert caught.value.status == 409
        db.session.rollback()
        corrected, _ = record(app, ctx, payload(ctx, corrects_public_id=row.event.public_id))
        with pytest.raises(OperationalError) as caught:
            record(app, ctx, payload(ctx, corrects_public_id=row.event.public_id))
        assert caught.value.code == "REPORT_ALREADY_CORRECTED"
        db.session.rollback()
        row.event.event_type = "legacy"
        with pytest.raises(ValueError, match="immutable"): db.session.flush()
        db.session.rollback()
        row.correction_reason = "rewrite"
        with pytest.raises(ValueError, match="immutable"): db.session.flush()
        db.session.rollback()
        db.session.delete(corrected.event)
        with pytest.raises(ValueError, match="immutable"): db.session.flush()
        db.session.rollback()


@pytest.mark.parametrize("changes", [
    {"source": "GPS"}, {"source": []}, {"occurred_at": "2026-09-21T12:00"},
    {"scope": "UNKNOWN"}, {"location": None}, {"location": {"location_text": []}},
    {"location": {"latitude": 10}}, {"corrects_public_id": []}, {"customer_effect": []},
    {"visibility": "customer"}, {"recorded_at": "2026-01-01T00:00:00Z"},
])
def test_invalid_reports_fail_without_partial_facts(operational_app, changes):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        with pytest.raises(OperationalError): record(app, ctx, payload(ctx, **changes))
        db.session.rollback()
        assert OperationalEventReportContext.query.count() == 0


def test_http_owner_only_reopen_and_cross_tenant_fail_closed(operational_app):
    app = operational_app
    with app.app_context(): ctx = setup(app)
    client = app.test_client()
    path = f"/api/operational-shipments/{ctx['shipment']}/reported-facts"
    result = client.post(path, headers={**_auth(app), "Idempotency-Key": "http-report"}, json=payload(ctx))
    assert result.status_code == 201, result.get_json()
    reopened = client.get(path, headers=_auth(app))
    assert reopened.status_code == 200 and reopened.headers["Cache-Control"] == "no-store"
    assert reopened.get_json()["data"]["items"][0]["public_id"] == result.get_json()["public_id"]
    admin = client.get(path, headers=_auth(app, "verifier"))
    assert admin.status_code == 200 and admin.get_json()["data"]["can_manage"] is False
    for actor in ("verifier", "outsider"):
        denied = client.post(path, headers={**_auth(app, actor), "Idempotency-Key": str(uuid4())}, json=payload(ctx))
        assert denied.status_code in (403, 404)
    assert client.get(path, headers=_auth(app, "outsider")).status_code == 404
    with app.app_context():
        unit = db.session.scalar(select(ExecutionUnit).where(ExecutionUnit.public_id == ctx["units"][0]))
        with pytest.raises(OperationalError) as caught:
            execution_unit_service.create_event(unit, {"event_type": "phase3_reported_fact"}, _user(app), "old-endpoint")
        assert caught.value.code == "SCOPED_REPORT_REQUIRED"


def test_peer_platform_and_changed_owner_cannot_command(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        org = app.config["phase1a"]["org"]
        for authority in ("EXPERT", "PLATFORM_ADMIN"):
            user = ExpertUser(username=f"report-{authority}", full_name="Unassigned", password_hash="unused",
                              role="expert", authority=authority, is_active=True)
            db.session.add(user); db.session.flush()
            db.session.add(OperationalMembership(organization_id=org, user_id=user.id,
                permissions=["operational_shipment.read", "operational_shipment.create"]))
            db.session.commit()
            with pytest.raises(OperationalError) as denied:
                reports.create(ctx["shipment"], {"id": user.id}, payload(ctx), str(uuid4()))
            assert denied.value.status in (403, 404)
            db.session.rollback()
        owner = db.session.get(ExpertUser, app.config["phase1a"]["user"])
        owner.is_active = False
        db.session.commit()
        with pytest.raises(OperationalError): record(app, ctx)
        db.session.rollback()
        assert OperationalEventReportContext.query.count() == 0


def test_cargo_b_location_cannot_be_assigned_to_a_but_safe_effect_can(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        with pytest.raises(OperationalError) as denied:
            record(app, ctx, payload(ctx, scope="CARGO", target_public_id=ctx["cargo_b"]))
        assert denied.value.status == 422
        db.session.rollback()
        for target in (str(uuid4()), "foreign-cargo"):
            with pytest.raises(OperationalError) as missing:
                record(app, ctx, payload(ctx, impacted_cargo_public_ids=[target]))
            assert missing.value.status == 404
            db.session.rollback()


def test_report_openapi_runtime_contract():
    from pathlib import Path
    import yaml
    document = yaml.safe_load((Path(__file__).resolve().parents[2] / "docs/openapi/openapi.yaml").read_text(encoding="utf-8"))
    route = document["paths"]["/api/operational-shipments/{shipment_id}/reported-facts"]
    assert {"get", "post"} <= set(route)
    schema = route["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert set(schema["properties"]["source"]["enum"]) == set(SOURCES)
    assert schema["additionalProperties"] is False
    assert "recorded_at" not in schema["properties"]
