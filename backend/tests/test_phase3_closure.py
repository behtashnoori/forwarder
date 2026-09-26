"""Completed-only closure, immutable evidence and explicit historical repair."""
from datetime import timedelta
from uuid import uuid4
import pytest
from backend.extensions import db
from backend.closure_models import ClosureDecision, ClosurePolicyVersion
from backend.operational_models import OperationalShipment, RoutePlan, utcnow
from backend.services import closure_service as svc, route_orchestration_service as routes
from backend.services import cargo_service, delivery_service, occurrence_projection_service as projection
from backend.services.operational_service import OperationalError
from backend.tests.test_operational_vertical_slice import operational_app, _user, _auth
from backend.tests.test_phase3_route_time import draft
from backend.tests.test_phase3_cargo_delivery import setup as delivery_setup, payload as delivery_payload


def policy(app, criteria=None, **extra):
    values = {"expected_version": 0, "effective_from": (utcnow()-timedelta(days=1)).isoformat(),
        "criteria": criteria or [{"scope": "GENERAL", "code": "NO_OPEN_EXCEPTIONS", "mandatory": True}], **extra}
    row, _ = svc.save_policy(_user(app, "verifier"), values, str(uuid4()))
    db.session.commit()
    return row


def completed(app):
    sid, plan, _ = draft(app)
    shipment = OperationalShipment.query.filter_by(public_id=sid).one()
    shipment.lifecycle_status = "completed"
    db.session.commit()
    return shipment


def command(shipment, kind="NORMAL", reason=None):
    assessment = svc.assess(shipment)
    return {"kind": kind, "reason": reason, "expected_shipment_version": shipment.version,
        "policy_version_public_id": assessment["policy"]["public_id"] if assessment["policy"] else None,
        "assessment_fingerprint": assessment["fingerprint"]}


def close(app, shipment, kind="NORMAL", reason=None):
    row, _ = svc.close(shipment.public_id, _user(app, "verifier" if kind == "EXCEPTIONAL" else "user"),
        command(shipment, kind, reason), str(uuid4()))
    db.session.commit()
    return row


def test_normal_close_idempotency_terminal_and_pinned_policy(operational_app):
    app = operational_app
    with app.app_context():
        version = policy(app); shipment = completed(app); values = command(shipment); key = str(uuid4())
        row, created = svc.close(shipment.public_id, _user(app), values, key)
        db.session.commit()
        assert created and shipment.lifecycle_status == "closed" and row.policy_version_id == version.id
        snapshot = row.assessment
        replay, created = svc.close(shipment.public_id, _user(app), values, key)
        assert not created and replay.id == row.id and ClosureDecision.query.count() == 1
        policy(app, expected_version=1, effective_from=(utcnow()+timedelta(days=1)).isoformat())
        assert row.assessment == snapshot and row.policy_version_id == version.id
        assert projection.shipment_state(shipment, None, [])[0] == "closed"
        shipment.lifecycle_status = "completed"
        with pytest.raises(ValueError): db.session.flush()
        db.session.rollback()
        row.reason = "rewrite"
        with pytest.raises(ValueError): db.session.flush()
        db.session.rollback()


@pytest.mark.parametrize("state", ["planned", "in_progress", "cancelled"])
@pytest.mark.parametrize("kind", ["NORMAL", "EXCEPTIONAL"])
def test_both_commands_require_completed(operational_app, state, kind):
    app = operational_app
    with app.app_context():
        policy(app); shipment = completed(app); shipment.lifecycle_status = state; db.session.commit()
        with pytest.raises(OperationalError) as denied: close(app, shipment, kind, "explicit exception")
        assert denied.value.code == "CLOSURE_PREDECESSOR"
        db.session.rollback()
        assert ClosureDecision.query.count() == 0 and shipment.lifecycle_status == state


def test_missing_policy_unknown_checklist_and_exception_preserve_missing(operational_app):
    app = operational_app
    with app.app_context():
        shipment = completed(app)
        assert svc.assess(shipment)["policy"] is None
        with pytest.raises(OperationalError) as denied: close(app, shipment, "EXCEPTIONAL", "missing policy")
        assert denied.value.code == "CLOSURE_POLICY_UNDEFINED"
        db.session.rollback()
        policy(app, [{"scope":"GENERAL", "code":"ACTUAL_QUANTITY_KNOWN", "mandatory":False},
                     {"scope":"road", "code":"ACTUAL_QUANTITY_KNOWN", "mandatory":True},
                     {"scope":"sea", "code":"NO_OPEN_EXCEPTIONS", "mandatory":True}])
        assessment = svc.assess(shipment)
        assert len(assessment["items"]) == 1 and assessment["items"][0]["mandatory"]
        assert len(assessment["items"][0]["criteria"]) == 2 and assessment["items"][0]["state"] == "UNKNOWN"
        with pytest.raises(OperationalError) as denied: close(app, shipment)
        assert denied.value.code == "CLOSURE_REQUIREMENTS_MISSING"
        db.session.rollback()
        with pytest.raises(OperationalError): close(app, shipment, "EXCEPTIONAL", " ")
        db.session.rollback()
        row = close(app, shipment, "EXCEPTIONAL", "Approved with known missing evidence")
        assert row.missing_items == assessment["missing"] and row.previous_state == "completed"


def test_stale_assessment_rejected_without_partial_decision(operational_app):
    app = operational_app
    with app.app_context():
        policy(app); shipment = completed(app); values = command(shipment)
        shipment.version += 1; db.session.commit()
        with pytest.raises(OperationalError) as denied: svc.close(shipment.public_id, _user(app), values, str(uuid4()))
        assert denied.value.code == "STALE_CLOSURE_ASSESSMENT"
        db.session.rollback()
        assert ClosureDecision.query.count() == 0 and shipment.lifecycle_status == "completed"


def test_late_delivery_and_quantity_correction_keep_decision_new_operations_denied(operational_app):
    from backend.cargo_models import ShipmentCargoItem
    app = operational_app
    with app.app_context():
        ctx = delivery_setup(app); policy(app)
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        shipment.lifecycle_status = "completed"; db.session.commit()
        row = close(app, shipment, "EXCEPTIONAL", "Retain missing documents")
        snapshot = row.assessment
        late = delivery_payload(ctx, occurred_at=(svc.times.aware(row.occurred_at)-timedelta(hours=1)).isoformat())
        delivery, created = delivery_service.create(shipment.public_id, _user(app), late, str(uuid4()))
        db.session.commit()
        assert created and delivery.recorded_at > delivery.occurred_at
        with pytest.raises(OperationalError) as denied:
            delivery_service.create(shipment.public_id, _user(app), {**late, "occurred_at":(utcnow()+timedelta(seconds=1)).isoformat()}, str(uuid4()))
        assert denied.value.code == "POST_CLOSURE_PRIOR_FACT_REQUIRED"
        db.session.rollback()
        cargo = ShipmentCargoItem.query.filter_by(public_id=ctx["cargo"]).one()
        cargo_service.update_shipment_item(_user(app), cargo, {"version":cargo.version,"actual_quantity":"101","reason":"late reconciliation"})
        db.session.commit()
        with pytest.raises(cargo_service.CargoError):
            cargo_service.update_shipment_item(_user(app), cargo, {"version":cargo.version,"actual_quantity":"102"})
        db.session.rollback()
        with pytest.raises(OperationalError) as denied: routes.create_plan(shipment.public_id, {}, _user(app))
        assert denied.value.code == "SHIPMENT_CLOSED"
        db.session.rollback()
        assert shipment.lifecycle_status == "closed" and row.assessment == snapshot


def test_policy_and_close_authority_no_store_and_pure_read(operational_app):
    app = operational_app
    with app.app_context():
        policy(app); shipment = completed(app); sid = shipment.public_id; values = command(shipment, "EXCEPTIONAL", "internal reason")
    client = app.test_client()
    response = client.get('/api/admin/closure-policy', headers=_auth(app))
    assert response.status_code == 403
    response = client.post(f'/api/operational-shipments/{sid}/close', headers={**_auth(app),"Idempotency-Key":str(uuid4())}, json=values)
    assert response.status_code == 403
    response = client.get(f'/api/operational-shipments/{sid}/closure', headers=_auth(app))
    assert response.status_code == 200 and "no-store" in response.headers["Cache-Control"]
    with app.app_context():
        assert ClosureDecision.query.count() == 0 and ClosurePolicyVersion.query.count() == 1


def test_closed_command_matrix_and_shared_unit_cannot_start_new_operations(operational_app):
    from backend.services import transport_execution_service as execution, operational_execution_service as milestones
    from backend.services import shared_transport_service as shared, execution_unit_service as units
    from backend.operational_models import RouteStageExecution, ExecutionUnit
    from backend.tests.test_phase3_cargo_allocation import _fixture
    app = operational_app
    with app.app_context():
        ctx = _fixture(app); policy(app)
        from backend.operational_models import OperationalMembership
        member = OperationalMembership.query.filter_by(user_id=app.config["phase1a"]["user"]).one()
        member.permissions = list(set(member.permissions) | {"operational_execution.manage", "operational_event.correct", "route_plan.activate", "checkpoint.report", "execution_unit.update", "execution_unit.create"})
        db.session.commit()
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        shipment.lifecycle_status = "completed"; db.session.commit(); close(app, shipment, "EXCEPTIONAL", "fixture close")
        unit_id = RouteStageExecution.query.filter_by(public_id=ctx["first"]).one().execution_unit_id
        unit_public_id = db.session.get(ExecutionUnit, unit_id).public_id
        calls = [
            lambda: routes.create_plan(ctx["shipment"], {}, _user(app)),
            lambda: routes.add_leg(ctx["shipment"], ctx["plan"], {}, _user(app)),
            lambda: routes.update_leg(ctx["shipment"], ctx["plan"], ctx["leg"], {}, _user(app)),
            lambda: routes.delete_leg(ctx["shipment"], ctx["plan"], ctx["leg"], _user(app)),
            lambda: routes.add_checkpoint(ctx["shipment"], ctx["plan"], {}, _user(app)),
            lambda: routes.add_dependency(ctx["shipment"], ctx["plan"], {}, _user(app)),
            lambda: routes.activate_plan(ctx["shipment"], ctx["plan"], {}, _user(app)),
            lambda: milestones.initialize(ctx["shipment"], {}, _user(app)),
            lambda: milestones.transition(ctx["shipment"], "missing", {}, _user(app)),
            lambda: milestones.reopen(ctx["shipment"], "missing", {}, _user(app)),
            lambda: execution.create(ctx["shipment"], ctx["plan"], ctx["leg"], {}, _user(app), str(uuid4())),
            lambda: units.update_unit(db.session.get(ExecutionUnit, unit_id), {}),
            lambda: shared.allocate(execution_public_id=unit_public_id,cargo_public_id=ctx["cargo"],allocated_quantity="1",user=_user(app)),
            lambda: shared.assign_carrier(execution_public_id=unit_public_id,carrier_customer_id=None,user=_user(app)),
        ]
        for index, call in enumerate(calls):
            with pytest.raises(OperationalError) as denied: call()
            assert denied.value.code == "SHIPMENT_CLOSED", (index, denied.value.message)
            db.session.rollback()
        assert ClosureDecision.query.count() == 1 and shipment.lifecycle_status == "closed"


def test_post_closure_document_append_replace_preserve_missing_and_owner_authority(operational_app, tmp_path):
    import io
    from backend.tests.test_shipment_document_authorization import PDF
    from backend.models import CaseDocumentFile
    app = operational_app
    app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path / "p312-private")
    with app.app_context():
        policy(app,[{"scope":"GENERAL","code":"REQUIRED_DOCUMENTS_READY","mandatory":True}])
        shipment = completed(app); row = close(app, shipment, "EXCEPTIONAL", "Missing document retained")
        sid = shipment.public_id; original = row.assessment
    client = app.test_client(); path = f"/api/internal/operational-shipments/{sid}/documents"
    headers = {**_auth(app),"Idempotency-Key":str(uuid4())}
    first = client.post(path, headers=headers, data={"title":"Late evidence", "file":(io.BytesIO(PDF),"late.pdf")})
    assert first.status_code == 201
    public_id = first.get_json()["data"]["public_id"]
    second = client.post(path, headers={**_auth(app),"Idempotency-Key":str(uuid4())},
        data={"title":"Corrected evidence", "file":(io.BytesIO(PDF),"corrected.pdf"),"replaces_document_public_id":public_id})
    assert second.status_code == 201
    denied = client.post(path, headers={**_auth(app,"verifier"),"Idempotency-Key":str(uuid4())},
        data={"title":"Admin cannot upload", "file":(io.BytesIO(PDF),"admin.pdf")})
    assert denied.status_code in {403, 404}
    with app.app_context():
        assert ClosureDecision.query.one().assessment == original
        assert OperationalShipment.query.filter_by(public_id=sid).one().lifecycle_status == "closed"
        assert CaseDocumentFile.query.filter_by(public_id=public_id).one().status == "superseded"


def test_openapi_exact_routes_and_private_recursive_response_allowlists(operational_app):
    import re
    import yaml
    from pathlib import Path
    app = operational_app
    document = yaml.safe_load((Path(__file__).parents[2] / "docs/openapi/openapi.yaml").read_text(encoding="utf-8"))
    actual = {(re.sub(r"<(?:uuid|int):([^>]+)>", r"{\1}", rule.rule), method.lower())
        for rule in app.url_map.iter_rules() if rule.endpoint.startswith("closure.")
        for method in rule.methods - {"HEAD", "OPTIONS"}}
    declared = {(path, method) for path, definition in document["paths"].items()
        if "closure-policy" in path or path.endswith(("/closure", "/close"))
        for method in definition if method in {"get", "post", "put", "delete", "patch"}}
    assert actual == declared
    def check(value, schema):
        if value is None:
            assert schema.get("nullable")
            return
        if "$ref" in schema:
            schema = document["components"]["schemas"][schema["$ref"].split("/")[-1]]
        if "allOf" in schema:
            for member in schema["allOf"]: check(value, member)
            return
        if isinstance(value, dict):
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) <= set(value) <= set(schema["properties"])
            for key, item in value.items(): check(item, schema["properties"][key])
        elif isinstance(value, (list, tuple)):
            for item in value: check(item, schema["items"])
    with app.app_context():
        policy(app); shipment = completed(app)
        check(svc.configuration(_user(app, "verifier")), document["components"]["schemas"]["ClosureConfiguration"])
        check(svc.read(shipment.public_id, _user(app)), document["components"]["schemas"]["ClosureView"])
        close(app, shipment)
        value = svc.read(shipment.public_id, _user(app))
        check(value, document["components"]["schemas"]["ClosureView"])
        assert "source_facts" not in value["decision"]["assessment"]


@pytest.mark.parametrize("boundary", ["cross_tenant", "nonowner", "disabled_actor", "disabled_membership", "disabled_org", "platform", "multiple_memberships"])
def test_live_authority_denies_close_without_partial_evidence(operational_app, boundary):
    from backend.models import ExpertUser
    from backend.operational_models import OperationalMembership, OperationalOrganization
    app = operational_app
    with app.app_context():
        policy(app); shipment = completed(app); payload = command(shipment)
        user = _user(app)
        actor = db.session.get(ExpertUser, user["id"])
        member = OperationalMembership.query.filter_by(user_id=actor.id).one()
        if boundary == "cross_tenant": user = _user(app, "outsider")
        elif boundary == "nonowner": user = _user(app, "verifier")
        elif boundary == "disabled_actor": actor.is_active = False
        elif boundary == "disabled_membership": member.is_active = False
        elif boundary == "disabled_org": db.session.get(OperationalOrganization, member.organization_id).is_active = False
        elif boundary == "platform": actor.authority = "PLATFORM_ADMIN"
        else:
            db.session.add(OperationalMembership(user_id=actor.id, organization_id=app.config["phase1a"]["other_org"], permissions=["operational_shipment.read"]))
        db.session.commit()
        with pytest.raises(OperationalError): svc.close(shipment.public_id, user, payload, str(uuid4()))
        db.session.rollback()
        assert ClosureDecision.query.count() == 0 and shipment.lifecycle_status == "completed"


def test_multimodal_union_preserves_scope_and_mandatory_precedence(operational_app):
    from backend.operational_models import RouteLeg
    app = operational_app
    with app.app_context():
        shipment = completed(app)
        plan = RoutePlan.query.filter_by(operational_shipment_id=shipment.id, is_active=True).one()
        first = RouteLeg.query.filter_by(route_plan_id=plan.id).first()
        extra = RouteLeg(route_plan_id=plan.id,
            sequence_number=first.sequence_number+1, transport_mode="air", status="planned",
            origin_location_id=first.origin_location_id, destination_location_id=first.destination_location_id,
            origin_snapshot=first.origin_snapshot, destination_snapshot=first.destination_snapshot,
            planned_departure=first.planned_departure, planned_arrival=first.planned_arrival)
        db.session.add(extra); db.session.commit()
        policy(app,[{"scope":"GENERAL","code":"NO_OPEN_EXCEPTIONS","mandatory":False},
            {"scope":"road","code":"NO_OPEN_EXCEPTIONS","mandatory":True},
            {"scope":"air","code":"ACTUAL_QUANTITY_KNOWN","mandatory":True}])
        assessment = svc.assess(shipment)
        assert set(assessment["modes"]) == {"road","air"}
        values = {row["code"]:row for row in assessment["items"]}
        assert values["NO_OPEN_EXCEPTIONS"]["mandatory"]
        assert {row["scope"] for row in values["NO_OPEN_EXCEPTIONS"]["criteria"]} == {"GENERAL","road"}
        assert values["ACTUAL_QUANTITY_KNOWN"]["state"] == "UNKNOWN"
        extra.status = "cancelled"; db.session.commit()
        assert svc.assess(shipment)["modes"] == ["road"]


def test_economic_history_after_close_is_limited_to_prior_facts(operational_app):
    from backend.models import ServiceType
    from backend.operational_models import OperationalMembership
    from backend.services import economics_service as economics
    from backend.tests.test_shipment_economics import PERMISSIONS
    app = operational_app
    with app.app_context():
        policy(app); shipment = completed(app)
        member = OperationalMembership.query.filter_by(user_id=_user(app)["id"]).one()
        member.permissions = [*member.permissions, *PERMISSIONS]
        service = ServiceType(immutable_code="CLOSURE_HISTORY", fa_name="Service", en_name="Service", is_active=True)
        db.session.add(service); db.session.commit()
        decision = close(app, shipment); frozen = decision.assessment
        payload = {"side":"COST", "stage":"ACTUAL", "service_public_id":service.public_id,
            "money":{"amount":"10", "currency":"USD"}, "authority":"existing permission",
            "effective_at":(svc.times.aware(decision.occurred_at)-timedelta(hours=1)).isoformat(),
            "idempotency_key":"late-economic-fact"}
        result = economics.create_line(shipment.public_id, payload, _user(app))
        assert not result["replayed"]
        with pytest.raises(OperationalError) as denied:
            economics.create_line(shipment.public_id, {**payload, "idempotency_key":"new-economic-fact",
                "effective_at":(utcnow()+timedelta(seconds=1)).isoformat()}, _user(app))
        assert denied.value.code == "POST_CLOSURE_PRIOR_FACT_REQUIRED"
        db.session.rollback()
        assert decision.assessment == frozen and shipment.lifecycle_status == "closed"
