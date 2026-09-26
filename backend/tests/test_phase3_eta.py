"""Cargo-specific ETA: real source commands, history, arithmetic and privacy."""
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import pytest
from flask import session
from sqlalchemy import select

from backend.extensions import db
from backend.models import Customer, CustomerGamification
from backend.eta_models import CargoEtaSnapshot as Snapshot, CargoEtaInput as Input
from backend.operational_models import CanonicalLocation, Milestone, RouteLeg, RoutePlan
from backend.route_time_models import OrganizationRouteTime as Reference
from backend.services import eta_service as eta, route_time_service as times
from backend.services import route_orchestration_service as routes, reported_fact_service as reports
from backend.services import customer_entitlement_service as grants
from backend.tests.test_operational_vertical_slice import operational_app, _user, _auth
from backend.tests.test_phase3_branched_route import _branched_draft, _cargo_lines
from backend.tests.test_phase3_document_context import _as_customer
from backend.tests.test_phase3_customer_shipment import new_cargo


def setup(app, *, final_reference=True, stop_range=(0, 0), checkpoint=False):
    shipment, plan, root, branch_b, branch_a = _branched_draft(app)
    cargo_a = _cargo_lines(app, shipment, count=1)[0]
    ids = app.config["phase1a"]
    other = Customer(company_name="PRIVATE-CUSTOMER-B", ownership_scope="TENANT",
                     operational_organization_id=ids["org"], status="active")
    db.session.add(other); db.session.flush()
    cargo_b = new_cargo(cargo_a, shipment, other.id, "PRIVATE-CARGO-B")
    cargo_b.line_number = 2
    accounts = [CustomerGamification(email=f"eta-{i}@example.test", phone=f"0900311000{i}",
                                    operational_organization_id=ids["org"]) for i in range(2)]
    db.session.add_all(accounts); db.session.commit()
    for cargo, leg, account in ((cargo_a, branch_a, accounts[0]), (cargo_b, branch_b, accounts[1])):
        routes.assign_cargo_destination(shipment.id, plan.id, cargo.public_id,
            {"destination_route_leg_id": leg["id"]}, _user(app))
        grants.grant(ids["org"], ids["verifier"], {"portal_account_public_id": account.public_id,
                      "customer_id": cargo.cargo_owner_customer_id}, str(uuid4()))
    db.session.commit()
    checkpoint_id = None
    if checkpoint:
        leg = db.session.get(RouteLeg, root["id"])
        location = db.session.get(CanonicalLocation, leg.destination_location_id)
        for checkpoint_index in range(int(checkpoint)):
            created_checkpoint = routes.add_checkpoint(shipment.id, plan.id, {
                "sequence_number": checkpoint_index + 1, "route_leg_id": leg.id, "checkpoint_type": "transshipment",
                "canonical_location_id": location.id,
                "planned_arrival_at": times.aware(leg.planned_arrival).isoformat(),
                "planned_departure_at": (times.aware(leg.planned_arrival) + timedelta(hours=1)).isoformat()}, _user(app))["id"]
            if checkpoint_id is None:
                checkpoint_id = created_checkpoint
    references = []
    for leg_id in [root["id"], *([branch_a["id"]] if final_reference else [])]:
        leg = db.session.get(RouteLeg, leg_id)
        a = db.session.get(CanonicalLocation, leg.origin_location_id)
        b = db.session.get(CanonicalLocation, leg.destination_location_id)
        ref, _ = times.save(_user(app, "verifier"), {
            "origin": {"source_type": a.source_type, "source_id": a.source_id},
            "destination": {"source_type": b.source_type, "source_id": b.source_id}, "transport_mode": "road",
            "movement_min_minutes": 60, "movement_max_minutes": 120,
            "stop_min_minutes": stop_range[0], "stop_max_minutes": stop_range[1],
            "effective_from": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()}, str(uuid4()))
        db.session.commit(); references.append(ref.id)
        times.select_basis(shipment.public_id, plan.id, leg.id, _user(app), {
            "expected_version": leg.version, "expected_selection_revision": 0,
            "reference_version_public_id": ref.public_id}, str(uuid4()))
        db.session.commit()
    routes.activate_plan(shipment.id, plan.id, {"expected_version": 1}, _user(app))
    leg = db.session.get(RouteLeg, root["id"])
    return {"shipment": shipment.public_id, "shipment_id": shipment.id, "cargo": cargo_a.public_id,
        "cargo_b": cargo_b.public_id, "plan": plan.id, "root": root["id"], "branch": branch_a["id"],
        "accounts": [row.id for row in accounts], "references": references, "checkpoint": checkpoint_id,
        "origin": db.session.get(CanonicalLocation, leg.origin_location_id).public_id,
        "middle": db.session.get(CanonicalLocation, leg.destination_location_id).public_id}


def report(app, ctx, *, location=None, occurred=None, **extra):
    row, _ = reports.create(ctx["shipment"], _user(app), {
        "scope": "CARGO", "target_public_id": ctx["cargo"], "kind": "LOCATION",
        "source": "CARRIER_REPORT", "occurred_at": occurred or "2026-09-20T08:00:00+03:30",
        "location": location or {"canonical_location_public_id": ctx["middle"]},
        "impacted_cargo_public_ids": [ctx["cargo"]], "internal_note": "PRIVATE-CAUSE", **extra}, str(uuid4()))
    db.session.commit()
    return row.event.public_id


def ensure(app, ctx):
    row = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], user=_user(app))
    db.session.commit()
    return row


def occurrence(app, ctx, kind="departure", at="2026-09-20T08:00:00+03:30", *, leg=None):
    from backend.services import operational_service as operations
    query = Milestone.query.filter_by(route_plan_id=ctx["plan"], milestone_type=kind)
    if kind.startswith("checkpoint_"):
        from backend.operational_models import OperationalCheckpoint
        cp = db.session.get(OperationalCheckpoint, ctx["checkpoint"])
        action = {"checkpoint_arrival": "arrive", "checkpoint_processing_complete": "complete_processing"}[kind]
        routes.checkpoint_command(ctx["shipment_id"], cp.id, {"occurred_at": at, "expected_version": cp.version},
                                  _user(app), str(uuid4()), action)
        return eta.occurrences.effective_occurrence(query.filter_by(checkpoint_id=cp.id).one())
    query = query.filter_by(route_leg_id=leg or ctx["root"])
    event = operations.record_event(ctx["shipment_id"], query.one().id,
        {"occurred_at": at}, _user(app), str(uuid4()))
    db.session.commit()
    return event


def test_ranges_use_occurred_pins_and_explicit_ensure_not_history_or_list(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        assert eta.history(ctx["shipment"], ctx["cargo"], user=_user(app))["items"] == []
        assert Snapshot.query.count() == 0
        occurrence(app, ctx)
        first = ensure(app, ctx)
        result = first.result
        assert result["as_of"] == "2026-09-20T04:30:00+00:00"
        assert result["next"]["earliest"] == "2026-09-20T05:30:00+00:00"
        assert result["next"]["latest"] == "2026-09-20T06:30:00+00:00"
        assert result["final"]["earliest"] == "2026-09-20T06:30:00+00:00"
        assert result["final"]["latest"] == "2026-09-20T08:30:00+00:00"
        assert result["recorded_at"] > result["as_of"] and result["planned_distance"] is None
        assert {r.reference_version_id for r in Input.query.all() if r.reference_version_id} == set(ctx["references"])
        assert ensure(app, ctx).id == first.id
        assert Snapshot.query.count() == 1
        assert len(eta.history(ctx["shipment"], ctx["cargo"], user=_user(app))["items"]) == 1


def test_next_can_exist_when_final_reference_missing_and_newer_ambiguity_is_not_hidden(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app, final_reference=False)
        occurrence(app, ctx)
        first = ensure(app, ctx)
        assert first.result["next"]["available"] and first.result["final"]["reason"] == "REFERENCE_UNDEFINED"
        report(app, ctx, location={"location_text": "somewhere along the route"}, occurred="2026-09-21T08:00:00Z")
        second = ensure(app, ctx)
        assert second.result["next"]["reason"] == "PROGRESS_AMBIGUOUS"
        assert first.result["next"]["available"] and first.sequence + 1 == second.sequence


def test_stop_b_belongs_only_to_continuing_beyond_b(operational_app):
    with operational_app.app_context():
        ctx = setup(operational_app, stop_range=(240, 480)); occurrence(operational_app, ctx)
        result = ensure(operational_app, ctx).result
        assert result["next"]["earliest"] == "2026-09-20T05:30:00+00:00"
        assert result["next"]["latest"] == "2026-09-20T06:30:00+00:00"
        assert result["final"]["earliest"] == "2026-09-20T10:30:00+00:00"
        assert result["final"]["latest"] == "2026-09-20T16:30:00+00:00"


def test_correction_uses_corrected_occurrence_and_preserves_old_estimate(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        original = report(app, ctx)
        old = ensure(app, ctx)
        old_values = json.dumps(old.result, sort_keys=True)
        report(app, ctx, corrects_public_id=original, reason="correct occurrence", occurred="2026-09-19T08:00:00Z")
        new = ensure(app, ctx)
        assert new.result["as_of"] == "2026-09-19T08:00:00+00:00"
        assert old_values == json.dumps(old.result, sort_keys=True)
        assert old.source_fingerprint != new.source_fingerprint and Snapshot.query.count() == 2
        old.result = {}
        with pytest.raises(ValueError, match="immutable"):
            db.session.flush()
        db.session.rollback()


def test_future_reference_becomes_applicable_without_rewriting_history(operational_app, monkeypatch):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        occurrence(app, ctx)
        old = ensure(app, ctx)
        from backend.route_time_models import OrganizationRouteTimeVersion as Version
        first = db.session.get(Version, ctx["references"][0])
        reference = db.session.get(Reference, first.reference_id)
        future = datetime.now(timezone.utc) + timedelta(days=1)
        updated, _ = times.save(_user(app, "verifier"), {"expected_version": 1,
            "movement_min_minutes": 180, "movement_max_minutes": 240,
            "stop_min_minutes": 0, "stop_max_minutes": 0,
            "effective_from": future.isoformat()}, str(uuid4()), reference.public_id)
        db.session.commit()
        assert ensure(app, ctx).id == old.id
        monkeypatch.setattr(eta, "utcnow", lambda: future + timedelta(seconds=1))
        new = ensure(app, ctx)
        assert new.id != old.id and new.result["next"]["earliest"] > old.result["next"]["earliest"]
        assert any(row["id"] == updated.id for row in new.source_basis["references"])
        assert old.source_basis["references"][0]["id"] == first.id
        from backend.route_time_models import RouteLegTimeBasis
        assert RouteLegTimeBasis.query.filter_by(route_leg_id=ctx["root"]).one().reference_version_id == first.id


def test_customer_exact_cargo_branch_allowlist_live_revocation_and_no_pure_get_write(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app); report(app, ctx)
    client = app.test_client(); _as_customer(client, ctx["accounts"][0])
    path = f"/api/customer/shipments/{ctx['shipment']}/cargo/{ctx['cargo']}/eta"
    assert client.get(path + "/history").get_json()["items"] == []
    response = client.post(path + "/ensure", json={})
    assert response.status_code == 200, response.get_json()
    value = response.get_json()
    assert value["next"]["available"] and value["authorization_revision"]
    assert "PRIVATE" not in json.dumps(value) and "provenance" not in value and "source_fingerprint" not in value
    assert "no-store" in response.headers["Cache-Control"]
    other = path.replace(ctx["cargo"], ctx["cargo_b"])
    assert client.post(other + "/ensure", json={}).status_code == 404
    assert client.get(other + "/history").status_code == 404
    assert client.post(path + "/ensure", json={"actor_id": 1, "earliest": "fake"}).status_code == 422
    with app.app_context():
        ids = app.config["phase1a"]
        account = db.session.get(CustomerGamification, ctx["accounts"][0])
        grant = next(r for r in grants.configuration(ids["org"], ids["verifier"])["grants"]
                     if r["portal_account_public_id"] == account.public_id)
        grants.revoke(ids["org"], ids["verifier"], grant["public_id"]); db.session.commit()
        count = Snapshot.query.count()
    assert client.post(path + "/ensure", json={}).status_code == 404
    assert client.get(path + "/history").status_code == 404
    with app.app_context(): assert Snapshot.query.count() == count


def test_internal_api_denies_foreign_expert_and_is_idempotent(operational_app):
    app = operational_app
    with app.app_context(): ctx = setup(app); report(app, ctx)
    client = app.test_client()
    path = f"/api/operational-shipments/{ctx['shipment']}/cargo/{ctx['cargo']}/eta"
    headers = _auth(app)
    first = client.post(path + "/ensure", json={}, headers=headers)
    assert first.status_code == 200, first.get_json()
    second = client.post(path + "/ensure", json={}, headers=headers)
    assert first.get_json()["public_id"] == second.get_json()["public_id"]
    assert client.post(path + "/ensure", json={}, headers=_auth(app, "outsider")).status_code in {403, 404}
    assert client.get(path + "/history", headers=_auth(app, "outsider")).status_code in {403, 404}


def test_equal_time_conflict_and_unquantified_effect_do_not_invent_progress(operational_app):
    app = operational_app
    with app.app_context():
        ctx = setup(app)
        report(app, ctx)
        first = ensure(app, ctx)
        report(app, ctx, kind="EFFECT", location=None, customer_effect="DELAY")
        effect = ensure(app, ctx)
        assert effect.result["unquantified_effect"]
        assert effect.result["next"] == first.result["next"]
        report(app, ctx, location={"canonical_location_public_id": ctx["origin"]})
        conflict = ensure(app, ctx)
        assert conflict.result["next"]["reason"] == "PROGRESS_AMBIGUOUS"
        assert conflict.result["final"]["reason"] == "PROGRESS_AMBIGUOUS"


def test_return_to_same_result_appends_and_customer_correction_history_remains(operational_app):
    app = operational_app
    with app.test_request_context():
        session["customer_portal_session_generation"] = 0
        ctx = setup(app)
        account = db.session.get(CustomerGamification, ctx["accounts"][0])
        original = report(app, ctx)
        a = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account); db.session.commit()
        middle = report(app, ctx, corrects_public_id=original, reason="correct position", location={"canonical_location_public_id": ctx["origin"]})
        b = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account); db.session.commit()
        report(app, ctx, corrects_public_id=middle, reason="verified original point")
        again = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account); db.session.commit()
        assert again.result["next"] == a.result["next"] and b.result["next"] != a.result["next"]
        assert [a.sequence, b.sequence, again.sequence] == [1, 2, 3]
        history = eta.history(ctx["shipment"], ctx["cargo"], account=account)["items"]
        assert len(history) == 3 and [row["next"]["available"] for row in history] == [True, False, True]


def test_split_cargo_and_unit_scope_cannot_create_whole_cargo_progress(operational_app):
    from backend.tests.test_phase3_cargo_allocation import _fixture, _set
    from backend.operational_models import RouteStageExecution
    app = operational_app
    with app.app_context():
        ctx = _fixture(app)
        _set(app, ctx, ctx["first"], "ACTUAL", 55, 0, "first-part")
        _set(app, ctx, ctx["second"], "ACTUAL", 40, 0, "second-part")
        db.session.commit()
        leg = db.session.get(RouteLeg, ctx["leg"])
        stage = RouteStageExecution.query.filter_by(public_id=ctx["first"]).one()
        location = db.session.get(CanonicalLocation, leg.origin_location_id)
        reports.create(ctx["shipment"], _user(app), {"scope": "EXECUTION_UNIT", "target_public_id": stage.execution_unit.public_id,
            "kind": "LOCATION", "source": "DRIVER_REPORT", "occurred_at": "2026-09-20T08:00:00Z",
            "location": {"canonical_location_public_id": location.public_id}, "impacted_cargo_public_ids": [ctx["cargo"]]}, str(uuid4()))
        db.session.commit()
        assert ensure(app, ctx).result["next"]["reason"] == "PROGRESS_UNDEFINED"
        reports.create(ctx["shipment"], _user(app), {"scope": "CARGO", "target_public_id": ctx["cargo"],
            "kind": "LOCATION", "source": "DRIVER_REPORT", "occurred_at": "2026-09-20T09:00:00Z",
            "location": {"canonical_location_public_id": location.public_id}, "impacted_cargo_public_ids": [ctx["cargo"]]}, str(uuid4()))
        db.session.commit()
        assert ensure(app, ctx).result["next"]["reason"] == "PROGRESS_AMBIGUOUS"


def test_internal_milestone_anchor_is_not_a_private_customer_input(operational_app):
    from backend.operational_models import Milestone
    from backend.services import operational_service as operations
    app = operational_app
    with app.test_request_context():
        session["customer_portal_session_generation"] = 0
        ctx = setup(app)
        departure = Milestone.query.filter_by(route_leg_id=ctx["root"], milestone_type="departure").one()
        event = operations.record_event(ctx["shipment_id"], departure.id,
            {"occurred_at": "2026-09-20T08:00:00Z"}, _user(app), "eta-departed")
        internal = ensure(app, ctx)
        assert internal.result["as_of"] == "2026-09-20T08:00:00+00:00"
        assert internal.source_basis["anchor"]["phase"] == "DEPARTED"
        assert any(row.milestone_event_id == event.id for row in Input.query.all())
        account = db.session.get(CustomerGamification, ctx["accounts"][0])
        customer = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account)
        assert customer.result["next"]["reason"] == "PROGRESS_UNDEFINED"


def test_private_branch_report_cannot_indirectly_change_customer_estimate(operational_app):
    app = operational_app
    with app.test_request_context():
        session["customer_portal_session_generation"] = 0
        ctx = setup(app); report(app, ctx)
        account = db.session.get(CustomerGamification, ctx["accounts"][0])
        original = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account); db.session.commit()
        with pytest.raises(eta.base.OperationalError):
            report(app, ctx, target_public_id=ctx["cargo_b"], impacted_cargo_public_ids=[ctx["cargo"], ctx["cargo_b"]],
                   occurred="2026-09-21T08:00:00Z", location={"location_text": "PRIVATE OTHER CARGO LOCATION"})
        db.session.rollback()
        report(app, ctx, target_public_id=ctx["cargo_b"], impacted_cargo_public_ids=[ctx["cargo_b"]],
               occurred="2026-09-21T08:00:00Z", location={"location_text": "PRIVATE OTHER CARGO LOCATION"})
        assert eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account).id == original.id


def test_eta_openapi_matches_runtime_and_declares_explicit_ensure():
    import re
    from pathlib import Path
    import yaml
    from backend import create_app
    document = yaml.safe_load((Path(__file__).parents[2] / "docs/openapi/openapi.yaml").read_text(encoding="utf-8"))
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    runtime = {re.sub(r"<uuid:([^>]+)>", r"{\1}", str(rule)): set(rule.methods) - {"HEAD", "OPTIONS"}
               for rule in app.url_map.iter_rules() if rule.endpoint.startswith("eta.")}
    documented = {path: {method.upper() for method in spec if method in {"get", "post"}}
                  for path, spec in document["paths"].items() if "/eta/" in path}
    assert runtime == documented and len(runtime) == 4
    assert all(value == {"POST"} for key, value in runtime.items() if key.endswith("/ensure"))


def test_origin_location_is_not_a_departure_delay_or_time(operational_app):
    with operational_app.app_context():
        ctx = setup(operational_app, stop_range=(240, 480))
        report(operational_app, ctx, location={"canonical_location_public_id": ctx["origin"]})
        result = ensure(operational_app, ctx).result
        assert result["next"]["reason"] == result["final"]["reason"] == "DEPARTURE_UNDEFINED"


@pytest.mark.parametrize("stop,available", [((0, 0), True), ((None, None), False)])
def test_zero_and_unknown_intermediate_stop_are_distinct(operational_app, stop, available):
    with operational_app.app_context():
        ctx = setup(operational_app, stop_range=stop)
        occurrence(operational_app, ctx)
        result = ensure(operational_app, ctx).result
        assert result["next"]["available"]  # target B stop is never required for arrival B
        assert result["final"]["available"] is available
        report(operational_app, ctx, occurred="2026-09-20T08:00:00Z")
        assert ensure(operational_app, ctx).result["next"]["available"] is available


def test_arrival_stop_is_not_prorated_after_two_hours(operational_app, monkeypatch):
    with operational_app.app_context():
        ctx = setup(operational_app, stop_range=(240, 480))
        report(operational_app, ctx, occurred="2026-09-25T08:00:00Z")
        monkeypatch.setattr(eta, "utcnow", lambda: datetime(2026, 9, 25, 10, tzinfo=timezone.utc))
        first = ensure(operational_app, ctx)
        assert first.result["next"]["earliest"] == "2026-09-25T13:00:00+00:00"
        assert first.result["next"]["latest"] == "2026-09-25T18:00:00+00:00"
        monkeypatch.setattr(eta, "utcnow", lambda: datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
        assert ensure(operational_app, ctx).id == first.id


@pytest.mark.parametrize("stop", [(240, 480), (None, None)])
def test_next_departure_consumes_stop_even_if_unknown(operational_app, stop):
    with operational_app.app_context():
        ctx = setup(operational_app, stop_range=stop)
        report(operational_app, ctx)
        old = ensure(operational_app, ctx)
        occurrence(operational_app, ctx, at="2026-09-20T10:00:00Z", leg=ctx["branch"])
        new = ensure(operational_app, ctx)
        assert new.result["next"]["earliest"] == "2026-09-20T11:00:00+00:00"
        assert new.result["next"]["latest"] == "2026-09-20T12:00:00+00:00"
        assert new.sequence == old.sequence + 1


def test_explicit_checkpoint_operations_consume_stop_but_are_private(operational_app):
    with operational_app.test_request_context():
        session["customer_portal_session_generation"] = 0
        ctx = setup(operational_app, stop_range=(240, 480), checkpoint=True)
        report(operational_app, ctx)
        before = ensure(operational_app, ctx)
        occurrence(operational_app, ctx, "checkpoint_arrival", "2026-09-20T05:00:00Z")
        proof = occurrence(operational_app, ctx, "checkpoint_processing_complete", "2026-09-20T10:00:00Z")
        after = ensure(operational_app, ctx)
        assert after.source_basis["anchor"]["phase"] == "STOP_COMPLETE"
        assert after.source_basis["anchor"]["completion_ids"] == [proof.id]
        assert after.result["next"]["earliest"] == "2026-09-20T11:00:00+00:00"
        assert before.sequence + 1 == after.sequence
        account = db.session.get(CustomerGamification, ctx["accounts"][0])
        safe = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account)
        assert safe.result["as_of"] == "2026-09-20T04:30:00+00:00"
        assert safe.result["next"]["earliest"] == "2026-09-20T09:30:00+00:00"
        assert "CHECKPOINT_OPERATIONS" not in json.dumps(eta.project(safe, customer=True))


def test_final_arrival_stop_is_never_required(operational_app):
    with operational_app.app_context():
        ctx = setup(operational_app, stop_range=(None, None))
        occurrence(operational_app, ctx, leg=ctx["branch"])
        result = ensure(operational_app, ctx).result
        assert result["final"]["available"] and result["next"] == result["final"]
        occurrence(operational_app, ctx, "arrival", "2026-09-20T08:00:00Z", leg=ctx["branch"])
        assert ensure(operational_app, ctx).result["final"]["reason"] == "DESTINATION_REACHED"


def test_private_departure_does_not_even_create_customer_history(operational_app):
    with operational_app.test_request_context():
        session["customer_portal_session_generation"] = 0
        ctx = setup(operational_app, stop_range=(240, 480))
        report(operational_app, ctx)
        account = db.session.get(CustomerGamification, ctx["accounts"][0])
        before = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account)
        db.session.commit()
        occurrence(operational_app, ctx, leg=ctx["branch"], at="2026-09-20T08:00:00Z")
        assert eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], account=account).id == before.id


def test_one_partial_allocation_is_not_whole_cargo_progress(operational_app):
    from backend.tests.test_phase3_cargo_allocation import _fixture, _set
    with operational_app.app_context():
        ctx = _fixture(operational_app)
        _set(operational_app, ctx, ctx["first"], "ACTUAL", 55, 0, "partial-only")
        db.session.commit()
        leg = db.session.get(RouteLeg, ctx["leg"])
        location = db.session.get(CanonicalLocation, leg.origin_location_id)
        reports.create(ctx["shipment"], _user(operational_app), {"scope": "CARGO", "target_public_id": ctx["cargo"],
            "kind": "LOCATION", "source": "CARRIER_REPORT", "occurred_at": "2026-09-20T08:00:00Z",
            "location": {"canonical_location_public_id": location.public_id},
            "impacted_cargo_public_ids": [ctx["cargo"]]}, str(uuid4()))
        db.session.commit()
        assert ensure(operational_app, ctx).result["next"]["reason"] == "PROGRESS_AMBIGUOUS"


def test_partial_checkpoint_completion_does_not_consume_aggregate_stop(operational_app):
    with operational_app.app_context():
        ctx = setup(operational_app, stop_range=(240, 480), checkpoint=2)
        report(operational_app, ctx)
        before = ensure(operational_app, ctx)
        occurrence(operational_app, ctx, "checkpoint_arrival", "2026-09-20T05:00:00Z")
        occurrence(operational_app, ctx, "checkpoint_processing_complete", "2026-09-20T10:00:00Z")
        after = ensure(operational_app, ctx)
        assert after.source_basis["anchor"]["phase"] == "AT_NODE"
        assert after.result["next"] == before.result["next"]
        assert after.result["next"]["earliest"] == "2026-09-20T09:30:00+00:00"
