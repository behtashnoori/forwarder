"""Organization Shipment stages and the exact V1 closure contract."""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.closure_models import BLOCKER_CRITERIA, WARNING_CRITERIA, ClosureDecision
from backend.cargo_models import ShipmentCargoItem
from backend.delivery_models import CargoDelivery
from backend.extensions import db
from backend.operational_models import OperationalShipment, utcnow
from backend.services import (
    closure_service,
    delivery_service,
    shipment_stage_service,
    unified_shipment_history,
)
from backend.services.operational_service import OperationalError
from backend.shipment_stage_models import (
    CANONICAL_STAGE_CODES,
    OrganizationShipmentStageDefinitionVersion,
    ShipmentOperationalStageEvent,
    ShipmentOperationalStageInstance,
)
from backend.tests.test_operational_vertical_slice import _user, operational_app
from backend.tests.test_phase3_cargo_allocation import _set
from backend.tests.test_phase3_cargo_delivery import payload as delivery_payload
from backend.tests.test_phase3_cargo_delivery import setup as delivery_setup
from backend.tests.test_phase3_route_time import draft


def _stages(*, all_required=True, inactive=()):
    return [
        {
            "code": code,
            "display_name_fa": shipment_stage_service.CANONICAL_NAMES_FA[code],
            "sequence": index,
            "active": code not in inactive,
            "required_for_completion": all_required and code not in inactive,
        }
        for index, code in enumerate(CANONICAL_STAGE_CODES, 1)
    ]


def _save_stages(app, *, expected=0, all_required=True, inactive=(), future=False):
    effective = utcnow() + timedelta(hours=1) if future else utcnow() - timedelta(days=1)
    row, created = shipment_stage_service.save_configuration(
        _user(app, "verifier"),
        {
            "expected_version": expected,
            "effective_from": effective.isoformat(),
            "stages": _stages(all_required=all_required, inactive=inactive),
        },
        str(uuid4()),
    )
    db.session.commit()
    return row, created


def _record(app, shipment_id, stage, event_type, occurred_at):
    row, created = shipment_stage_service.record_event(
        shipment_id,
        stage["public_id"],
        _user(app),
        {
            "event_type": event_type,
            "occurred_at": occurred_at.isoformat(),
            "expected_policy_version_public_id": stage["policy_public_id"],
        },
        str(uuid4()),
    )
    db.session.commit()
    return row, created


def _projected_stages(app, shipment_id):
    view = shipment_stage_service.read(shipment_id, _user(app))
    return [dict(stage, policy_public_id=view["configuration"]["public_id"]) for stage in view["stages"]]


def _exact_policy(app):
    criteria = [
        {"scope": "GENERAL", "code": code, "mandatory": True}
        for code in BLOCKER_CRITERIA
    ] + [
        {"scope": "GENERAL", "code": code, "mandatory": False}
        for code in WARNING_CRITERIA
    ]
    row, created = closure_service.save_policy(
        _user(app, "verifier"),
        {
            "expected_version": 0,
            "effective_from": (utcnow() - timedelta(days=1)).isoformat(),
            "criteria": criteria,
        },
        str(uuid4()),
    )
    db.session.commit()
    return row, created


def _complete_stages(app, shipment_id):
    stages = _projected_stages(app, shipment_id)
    shipment = OperationalShipment.query.filter_by(public_id=shipment_id).one()
    base = shipment_stage_service.times.aware(shipment.created_at)
    for index, stage in enumerate(stages):
        started = base + timedelta(microseconds=index * 2 + 1)
        _record(app, shipment_id, stage, "STARTED", started)
        _record(app, shipment_id, stage, "COMPLETED", started + timedelta(microseconds=1))


def test_projectless_configuration_order_authority_pinning_and_immutability(operational_app):
    app = operational_app
    with app.app_context():
        shipment_id, _, _ = draft(app)
        shipment = OperationalShipment.query.filter_by(public_id=shipment_id).one()
        assert shipment.project_id is None

        version, created = _save_stages(app)
        assert created and version.version == 1
        view = shipment_stage_service.read(shipment_id, _user(app))
        assert view["project_required"] is False
        assert view["pinned"] is False
        assert [row["code"] for row in view["stages"]] == list(CANONICAL_STAGE_CODES)
        assert ShipmentOperationalStageInstance.query.count() == 0

        with pytest.raises(OperationalError):
            shipment_stage_service.configuration(_user(app, "outsider"))
        with pytest.raises(OperationalError):
            shipment_stage_service.read(shipment_id, _user(app, "outsider"))

        stages = _projected_stages(app, shipment_id)
        now = shipment_stage_service.times.aware(shipment.created_at) + timedelta(microseconds=1)
        with pytest.raises(OperationalError) as admin_denied:
            shipment_stage_service.record_event(
                shipment_id,
                stages[0]["public_id"],
                _user(app, "verifier"),
                {"event_type": "STARTED", "occurred_at": now.isoformat(),
                 "expected_policy_version_public_id": version.public_id},
                str(uuid4()),
            )
        assert admin_denied.value.code == "SHIPMENT_STAGE_EVENT_FORBIDDEN"
        db.session.rollback()

        with pytest.raises(OperationalError) as order_denied:
            _record(app, shipment_id, stages[1], "STARTED", now)
        assert order_denied.value.code == "SHIPMENT_STAGE_ORDER_VIOLATION"
        db.session.rollback()

        started, created = _record(app, shipment_id, stages[0], "STARTED", now)
        assert created and ShipmentOperationalStageInstance.query.count() == 1
        completed, created = _record(app, shipment_id, stages[0], "COMPLETED", now + timedelta(microseconds=1))
        assert created
        completed.occurred_at = now + timedelta(microseconds=3)
        with pytest.raises(ValueError, match="immutable"):
            db.session.flush()
        db.session.rollback()

        # A future version deactivates the first definition. The Shipment is pinned to
        # V1 and its historical execution remains active and readable without rewrite.
        future, _ = _save_stages(
            app,
            expected=1,
            inactive=(CANONICAL_STAGE_CODES[0],),
            future=True,
        )
        assert future.version == 2
        pinned = shipment_stage_service.read(shipment_id, _user(app))
        assert pinned["pinned"] is True and pinned["configuration"]["version"] == 1
        assert pinned["stages"][0]["active"] is True
        future_first = OrganizationShipmentStageDefinitionVersion.query.filter_by(
            policy_version_id=future.id, sequence=1
        ).one()
        assert future_first.is_active is False
        assert ShipmentOperationalStageEvent.query.count() == 2


def test_optional_final_stage_does_not_block_required_completion(operational_app):
    app = operational_app
    with app.app_context():
        shipment_id, _, _ = draft(app)
        version, _ = shipment_stage_service.save_configuration(
            _user(app, "verifier"),
            {
                "expected_version": 0,
                "effective_from": (utcnow() - timedelta(days=1)).isoformat(),
                "stages": [
                    {**row, "required_for_completion": row["sequence"] < 5}
                    for row in _stages()
                ],
            },
            str(uuid4()),
        )
        db.session.commit()
        stages = _projected_stages(app, shipment_id)
        shipment = OperationalShipment.query.filter_by(public_id=shipment_id).one()
        base = shipment_stage_service.times.aware(shipment.created_at)
        for index, stage in enumerate(stages[:4]):
            _record(app, shipment_id, stage, "STARTED", base + timedelta(microseconds=index * 2 + 1))
            _record(app, shipment_id, stage, "COMPLETED", base + timedelta(microseconds=index * 2 + 2))
        state, facts = shipment_stage_service.completion_state(shipment)
        assert version.version == 1 and state == "PASS"
        assert len(facts["required"]) == 4
        assert shipment_stage_service.read(shipment_id, _user(app))["stages"][-1]["status"] == "NOT_STARTED"


def test_new_closure_policy_rejects_legacy_or_extra_blockers(operational_app):
    app = operational_app
    with app.app_context():
        with pytest.raises(OperationalError) as denied:
            closure_service.save_policy(
                _user(app, "verifier"),
                {
                    "expected_version": 0,
                    "effective_from": (utcnow() - timedelta(days=1)).isoformat(),
                    "criteria": [{"scope": "GENERAL", "code": "NO_OPEN_EXCEPTIONS", "mandatory": True}],
                },
                str(uuid4()),
            )
        assert denied.value.code == "CLOSURE_INVALID"
        db.session.rollback()


def test_exact_closure_refusal_warning_only_success_and_unified_history(operational_app):
    app = operational_app
    with app.app_context():
        ctx = delivery_setup(app)
        shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
        assert shipment.project_id is None
        cargo = ShipmentCargoItem.query.filter_by(public_id=ctx["cargo"]).one()
        cargo.actual_quantity = None
        db.session.commit()

        _save_stages(app)
        _exact_policy(app)
        _set(app, ctx, ctx["first"], "PLANNED", 100, 0, "closure-plan")
        _set(app, ctx, ctx["first"], "ACTUAL", 95, 0, "closure-actual")
        db.session.commit()
        partial, created = delivery_service.create(
            ctx["shipment"],
            _user(app),
            delivery_payload(ctx, quantity="95", is_final=False),
            "closure-partial",
        )
        assert created and partial.is_final is False
        shipment.lifecycle_status = "completed"
        db.session.commit()

        first = closure_service.assess(shipment)
        items = {item["code"]: item for item in first["items"]}
        assert items["FINAL_DELIVERY_EXISTS"]["state"] == "FAIL"
        assert items["REQUIRED_OPERATIONAL_STAGES_COMPLETE"]["state"] == "FAIL"
        assert items["REQUIRED_DOCUMENTS_READY"]["state"] == "PASS"
        assert items["NO_BLOCKING_OPERATIONAL_ISSUE"]["state"] == "PASS"
        assert items["ACTUAL_CARGO_UNKNOWN"]["state"] == "FAIL"
        assert items["ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED"]["state"] == "FAIL"
        assert items["DELIVERED_DIFFERS_FROM_PLANNED"]["state"] == "FAIL"
        assert all(items[code]["mandatory"] is False for code in WARNING_CRITERIA)
        assert first["normal_ready"] is False

        close_command = {
            "kind": "NORMAL",
            "reason": None,
            "expected_shipment_version": shipment.version,
            "policy_version_public_id": first["policy"]["public_id"],
            "assessment_fingerprint": first["fingerprint"],
        }
        with pytest.raises(OperationalError) as refused:
            closure_service.close(ctx["shipment"], _user(app), close_command, str(uuid4()))
        assert refused.value.code == "CLOSURE_REQUIREMENTS_MISSING"
        db.session.rollback()

        final, created = delivery_service.create(
            ctx["shipment"],
            _user(app),
            delivery_payload(
                ctx,
                quantity="95",
                expected_version=partial.revision,
                corrects_public_id=partial.public_id,
                reason="تعیین صریح تحویل نهایی",
                is_final=True,
            ),
            "closure-final",
        )
        db.session.commit()
        assert created and final.is_final
        with pytest.raises(OperationalError) as duplicate_final:
            delivery_service.create(
                ctx["shipment"], _user(app),
                delivery_payload(ctx, quantity="1", is_final=True), "closure-final-duplicate",
            )
        assert duplicate_final.value.code == "FINAL_DELIVERY_EXISTS"
        db.session.rollback()

        _complete_stages(app, ctx["shipment"])
        qualified = closure_service.assess(shipment)
        qualified_items = {item["code"]: item for item in qualified["items"]}
        assert all(qualified_items[code]["state"] == "PASS" for code in BLOCKER_CRITERIA)
        assert qualified_items["ACTUAL_CARGO_UNKNOWN"]["state"] == "FAIL"
        assert qualified_items["ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED"]["state"] == "FAIL"
        assert qualified_items["DELIVERED_DIFFERS_FROM_PLANNED"]["state"] == "FAIL"
        assert qualified["normal_ready"] is True

        decision, created = closure_service.close(
            ctx["shipment"],
            _user(app),
            {
                "kind": "NORMAL",
                "reason": None,
                "expected_shipment_version": shipment.version,
                "policy_version_public_id": qualified["policy"]["public_id"],
                "assessment_fingerprint": qualified["fingerprint"],
            },
            str(uuid4()),
        )
        db.session.commit()
        assert created and shipment.lifecycle_status == "closed" and ClosureDecision.query.count() == 1

        history = unified_shipment_history.history(shipment, per_page=100, user=_user(app))
        stage_items = [item for item in history["items"] if item["category"] == "OPERATIONAL_STAGE"]
        assert len(stage_items) == 10
        assert all(item["business_label"] in {"مرحله عملیاتی شروع شد", "مرحله عملیاتی کامل شد"} for item in stage_items)
        assert all(item["stage_label"] for item in stage_items)
        assert any(item["category"] == "DELIVERY" and item["business_label"] == "تحویل نهایی محموله ثبت شد" for item in history["items"])
        assert any(item["category"] == "CLOSURE" and "الزامات" in item["business_label"] for item in history["items"])
        assert CargoDelivery.query.filter_by(is_final=True).count() == 1

        with pytest.raises(OperationalError):
            shipment_stage_service.read(ctx["shipment"], _user(app, "outsider"))

