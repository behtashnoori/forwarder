from datetime import timedelta

import pytest

from backend.extensions import db
from backend.models import ExpertUser
from backend.oip_models import OipProjectionHealthHistory, OipProjectionState, OipSituation, OipSituationHistory
from backend.operational_models import (
    ExceptionReason,
    Milestone,
    OperationalException,
    OperationalMembership,
    OperationalSlaCommitment,
    OperationalWorkItem,
    OrganizationSlaRule,
    utcnow,
)
from backend.services import oip_service
from backend.services.control_tower_read_model import compose_control_tower
from backend.services import operational_action_service as action_service
from backend.services import operational_execution_service as execution_service
from backend.services import operational_service
from backend.services import organization_sla_service as sla_service
from backend.tests.test_operational_vertical_slice import (
    _auth,
    _payload,
    _user,
    operational_app,
)


def _admin(app, key="verifier"):
    return {
        "id": app.config["phase1a"][key],
        "role": "manager",
        "authority": "ORGANIZATION_ADMIN",
    }


def _permission(app, user_key, *permissions):
    membership = OperationalMembership.query.filter_by(
        user_id=app.config["phase1a"][user_key]
    ).one()
    membership.permissions = sorted(set(membership.permissions or ()) | set(permissions))
    db.session.commit()


def _shipment(app, key):
    row, _ = operational_service.create_from_accepted_quote(
        _payload(app), _user(app), key
    )
    return row


def _exception(app, shipment, occurred_at):
    reason = ExceptionReason(
        organization_id=shipment.organization_id,
        immutable_code=f"SYNTHETIC_{shipment.id}",
        fa_name="استثنای مصنوعی آزمون",
        en_name="Synthetic test exception",
        definition="Synthetic Phase 2 test data",
        created_by_user_id=app.config["phase1a"]["user"],
        updated_by_user_id=app.config["phase1a"]["user"],
    )
    db.session.add(reason)
    db.session.flush()
    row = OperationalException(
        organization_id=shipment.organization_id,
        operational_shipment_id=shipment.id,
        reason_id=reason.id,
        occurred_at=occurred_at,
        impact_summary="نیاز به هماهنگی مجدد",
        evidence_summary="گزارش مصنوعی آزمون",
        note="داده مصنوعی",
        created_by_user_id=app.config["phase1a"]["user"],
    )
    db.session.add(row)
    db.session.commit()
    return row


def test_sla_admin_is_tenant_scoped_versioned_and_has_no_default(operational_app):
    client = operational_app.test_client()
    with operational_app.app_context():
        shipment = _shipment(operational_app, "phase2-no-default")
        assert sla_service.shipment_status(shipment)["status"] == "NOT_CONFIGURED"
        outsider = db.session.get(
            ExpertUser, operational_app.config["phase1a"]["outsider"]
        )
        outsider.authority = "ORGANIZATION_ADMIN"
        db.session.commit()

    denied = client.get("/api/organization-sla-rules", headers=_auth(operational_app))
    assert denied.status_code == 403

    created = client.post(
        "/api/organization-sla-rules",
        headers=_auth(operational_app, "verifier"),
        json={
            "process_type": "EXCEPTION_RESPONSE",
            "name": "پاسخ مصنوعی به استثنا",
            "duration_minutes": 60,
            "warning_minutes": 15,
            "is_active": True,
        },
    )
    assert created.status_code == 201
    rule = created.json["data"]
    assert rule["version"] == 1

    foreign_list = client.get(
        "/api/organization-sla-rules", headers=_auth(operational_app, "outsider")
    )
    assert foreign_list.status_code == 200
    assert foreign_list.json["data"]["rules"] == []
    foreign_update = client.patch(
        f"/api/organization-sla-rules/{rule['public_id']}",
        headers=_auth(operational_app, "outsider"),
        json={"expected_version": 1, "duration_minutes": 30},
    )
    assert foreign_update.status_code == 404

    updated = client.patch(
        f"/api/organization-sla-rules/{rule['public_id']}",
        headers=_auth(operational_app, "verifier"),
        json={"expected_version": 1, "duration_minutes": 90, "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json["data"]["version"] == 2
    assert updated.json["data"]["is_active"] is False
    history = client.get(
        f"/api/organization-sla-rules/{rule['public_id']}/history",
        headers=_auth(operational_app, "verifier"),
    )
    assert [row["action"] for row in history.json["data"]] == [
        "organization_sla_rule.created",
        "organization_sla_rule.updated",
    ]


def test_sla_evaluation_attention_workspace_and_control_tower(operational_app):
    with operational_app.app_context():
        _permission(
            operational_app,
            "user",
            "operational_execution.read",
            "operational_execution.manage",
        )
        rule = sla_service.create_rule(
            {
                "process_type": "EXCEPTION_RESPONSE",
                "name": "آزمون هشدار پاسخ",
                "duration_minutes": 60,
                "warning_minutes": 15,
                "is_active": True,
            },
            _admin(operational_app),
        )
        shipment = _shipment(operational_app, "phase2-sla-warning")
        started = utcnow() + timedelta(seconds=1)
        exception = _exception(operational_app, shipment, started)

        healthy_at = started + timedelta(minutes=10)
        first = oip_service.reconcile(
            organization_id=shipment.organization_id,
            calculation_time=healthy_at,
        )
        assert first["sla_evaluation"]["created_commitments"] == 1
        commitment = OperationalSlaCommitment.query.one()
        assert commitment.rule_snapshot["public_id"] == rule["public_id"]
        assert commitment.evaluation_status == "WITHIN"
        assert OipSituation.query.filter_by(
            situation_type="SLA_COMMITMENT_RISK"
        ).count() == 0

        warning_at = started + timedelta(minutes=50)
        oip_service.reconcile(
            organization_id=shipment.organization_id,
            calculation_time=warning_at,
        )
        commitment = OperationalSlaCommitment.query.one()
        assert commitment.evaluation_status == "WARNING"
        situation = OipSituation.query.filter_by(
            situation_type="SLA_COMMITMENT_RISK"
        ).one()
        stable_public_id = situation.public_id

        oip_service.reconcile(
            organization_id=shipment.organization_id,
            calculation_time=warning_at,
        )
        assert OipSituation.query.filter_by(
            situation_type="SLA_COMMITMENT_RISK"
        ).one().public_id == stable_public_id

        shipment_public_id = shipment.public_id
        exception_public_id = exception.public_id

    client = operational_app.test_client()
    workspace = client.get(
        "/api/operational-workspace", headers=_auth(operational_app)
    )
    assert workspace.status_code == 200
    sla_attention = [
        row
        for row in workspace.json["data"]["attention_items"]
        if row["kind"] == "SLA_COMMITMENT_RISK"
    ]
    assert len(sla_attention) == 1
    assert "قاعده" in sla_attention[0]["why"]
    assert sla_attention[0]["source"]["type"] == "OperationalSlaCommitment"
    card = next(
        row
        for row in workspace.json["data"]["active_shipments"]
        if row["public_id"] == shipment_public_id
    )
    assert card["sla"]["status"] == "WARNING"
    assert card["sla"]["commitments"][0]["source"]["public_id"] == exception_public_id
    exception_attention = next(
        row
        for row in workspace.json["data"]["attention_items"]
        if row["kind"] == "ACTIVE_DELAY_OR_EXCEPTION"
        and row["source"]["public_id"] == exception_public_id
    )
    assert exception_attention["truth"]["contract_version"] == "attention-truth-v1"

    tower = client.get("/api/control-tower/shipments", headers=_auth(operational_app))
    assert tower.status_code == 200
    item = next(
        row for row in tower.json["data"]["items"] if row["key"] == shipment_public_id
    )
    semantics = {item["primaryReason"]["semantic"]} | {
        row["semantic"] for row in item["additionalReasons"]
    }
    assert "sla_warning" in semantics
    assert "exception_open" in semantics
    exception_reason = next(
        row
        for row in [item["primaryReason"], *item["additionalReasons"]]
        if row["semantic"] == "exception_open"
    )
    # The HTTP request observes real current time, while this fixture evaluates
    # its warning slightly in the future. The route therefore correctly omits
    # a not-yet-fresh parity proof. Re-observe at that governed evaluation time
    # to compare the two read models without weakening the freshness boundary.
    assert "truth" not in exception_reason
    with operational_app.app_context():
        governed = compose_control_tower(
            {"id": _user(operational_app)["id"]}, at=warning_at + timedelta(seconds=1)
        )
        governed_item = next(
            row for row in governed.items if row.shipment_reference == shipment_public_id
        )
        governed_exception = next(
            row
            for row in [governed_item.primary_reason, *governed_item.additional_reasons]
            if row.semantic == "exception_open"
        )
    assert governed_exception.truth == exception_attention["truth"]
    assert tower.json["data"]["attentionEvaluation"]["sourceWatermark"] == (
        workspace.json["meta"]["attention_projection"]["source_watermark"]
    )


def test_action_uses_fixed_owner_preserves_history_and_is_independent(operational_app):
    with operational_app.app_context():
        _permission(
            operational_app,
            "user",
            "operational_execution.read",
            "operational_execution.manage",
        )
        shipment = _shipment(operational_app, "phase2-action")
        exception = _exception(operational_app, shipment, utcnow())
        actor = _user(operational_app)
        action = action_service.create_action(
            shipment.public_id,
            {
                "context_type": "EXCEPTION",
                "exception_public_id": exception.public_id,
                "what": "پیگیری پاسخ طرف عملیاتی",
                "expected_result": "دریافت پاسخ ثبت‌شده",
                "due_at": (utcnow() + timedelta(hours=2)).isoformat(),
            },
            actor,
        )
        assert action["responsible"]["user_id"] == shipment.primary_responsible_expert_id
        assert action["responsible"]["basis"] == "SHIPMENT_TRANSPORT_EXPERT"

        action = action_service.record_follow_up(
            shipment.public_id,
            action["public_id"],
            {"note": "تماس انجام شد", "expected_version": action["version"]},
            actor,
        )
        execution_service.resolve_condition(
            "exception",
            shipment.public_id,
            exception.public_id,
            {"expected_version": exception.version},
            actor,
        )
        row = OperationalWorkItem.query.filter_by(public_id=action["public_id"]).one()
        assert row.status == "open"

        with pytest.raises(operational_service.OperationalError) as missing_result:
            action_service.resolve_action(
                shipment.public_id,
                action["public_id"],
                {"result": "", "expected_version": action["version"]},
                actor,
            )
        assert missing_result.value.code == "VALIDATION_FAILED"
        db.session.rollback()

        action = action_service.resolve_action(
            shipment.public_id,
            action["public_id"],
            {"result": "پاسخ دریافت و ثبت شد", "expected_version": action["version"]},
            actor,
        )
        assert action["status"] == "resolved"
        assert action["result"] == "پاسخ دریافت و ثبت شد"
        history = action_service.action_history(
            shipment.public_id, action["public_id"], actor
        )
        assert [event["action"] for event in history] == [
            "operational_action.created",
            "operational_action.follow_up_recorded",
            "operational_action.resolved",
        ]

        with pytest.raises(operational_service.OperationalError) as foreign:
            action_service.list_actions(
                shipment.public_id, _user(operational_app, "outsider")
            )
        assert foreign.value.code == "RESOURCE_NOT_FOUND"


def test_rule_edit_catches_up_old_version_before_prospective_change(operational_app):
    with operational_app.app_context():
        created = sla_service.create_rule(
            {
                "process_type": "ACTION_FOLLOW_UP",
                "name": "نسخه نخست مصنوعی",
                "duration_minutes": 30,
                "warning_minutes": 5,
                "is_active": True,
            },
            _admin(operational_app),
        )
        shipment = _shipment(operational_app, "phase2-rule-catchup")
        action_service.create_action(
            shipment.public_id,
            {
                "context_type": "SHIPMENT",
                "what": "پیگیری پیش از تغییر قاعده",
                "due_at": (utcnow() + timedelta(hours=1)).isoformat(),
            },
            _user(operational_app),
        )
        updated = sla_service.update_rule(
            created["public_id"],
            {
                "expected_version": created["version"],
                "duration_minutes": 90,
                "warning_minutes": 10,
            },
            _admin(operational_app),
        )
        commitment = OperationalSlaCommitment.query.one()
        assert commitment.rule_version == 1
        assert commitment.rule_snapshot["duration_minutes"] == 30
        assert updated["version"] == 2
        assert OrganizationSlaRule.query.one().duration_minutes == 90


def test_reconcile_skips_legacy_direct_overdue_source_without_project_policy(operational_app):
    with operational_app.app_context():
        shipment = _shipment(operational_app, "phase2-direct-overdue-oip")
        milestone = Milestone.query.filter_by(
            operational_shipment_id=shipment.id
        ).first()
        db.session.add(
            OperationalWorkItem(
                organization_id=shipment.organization_id,
                operational_shipment_id=shipment.id,
                milestone_id=milestone.id,
                work_type="OVERDUE_MILESTONE",
                severity="warning",
                detected_at=utcnow(),
                due_at=utcnow() - timedelta(minutes=1),
                reason="Legacy direct-shipment workspace signal",
            )
        )
        db.session.commit()

        result = oip_service.reconcile(organization_id=shipment.organization_id)

        assert result["status"] == "FRESH"
        assert all(
            row["type"] != "NEXT_MILESTONE_OVERDUE" for row in result["results"]
        )


def test_background_catch_up_retry_idempotency_and_clock_freshness(operational_app):
    with operational_app.app_context():
        _permission(
            operational_app,
            "user",
            "operational_execution.read",
            "operational_execution.manage",
        )
        sla_service.create_rule(
            {
                "process_type": "EXCEPTION_RESPONSE",
                "name": "پایداری ارزیابی مصنوعی",
                "duration_minutes": 60,
                "warning_minutes": 15,
                "is_active": True,
            },
            _admin(operational_app),
        )
        shipment = _shipment(operational_app, "phase25-reliability")
        started = utcnow() + timedelta(seconds=1)
        _exception(operational_app, shipment, started)
        healthy_at = started + timedelta(minutes=10)
        warning_at = started + timedelta(minutes=50)
        breached_at = started + timedelta(hours=3)

        healthy = oip_service.reconcile(
            organization_id=shipment.organization_id,
            calculation_time=healthy_at,
        )
        assert healthy["status"] == "FRESH"
        assert healthy["run_summary"]["source_items_evaluated"] >= 1
        assert healthy["projection_health"]["next_evaluation_due_at"]

        stale = oip_service.projection_health_for_organization(
            shipment.organization_id,
            checked_at=warning_at,
        )
        assert stale["health_state"] == "STALE"
        assert stale["reason_code"] == "EVALUATION_TIME_BOUNDARY_REACHED"

        caught_up = oip_service.reconcile(
            organization_id=shipment.organization_id,
            calculation_time=breached_at,
        )
        commitment = OperationalSlaCommitment.query.one()
        situation = OipSituation.query.filter_by(
            situation_type="SLA_COMMITMENT_RISK"
        ).one()
        assert caught_up["status"] == "FRESH"
        assert commitment.evaluation_status == "BREACHED"
        assert oip_service._utc_aware(commitment.due_at) < oip_service._utc_aware(commitment.evaluated_at)
        assert oip_service._utc_aware(situation.first_detected_at) == breached_at
        assert oip_service._utc_aware(situation.first_detected_at) > oip_service._utc_aware(commitment.due_at)

        situation_id = situation.public_id
        situation_history_count = OipSituationHistory.query.filter_by(
            situation_id=situation.id
        ).count()
        repeated = oip_service.reconcile(
            organization_id=shipment.organization_id,
            calculation_time=breached_at,
        )
        assert repeated["run_summary"]["resulting_changes"] == 0
        assert OipSituation.query.filter_by(
            situation_type="SLA_COMMITMENT_RISK"
        ).one().public_id == situation_id
        assert OipSituationHistory.query.filter_by(
            situation_id=situation.id
        ).count() == situation_history_count

        with pytest.raises(operational_service.OperationalError):
            oip_service.reconcile(
                organization_id=shipment.organization_id,
                calculation_time=breached_at + timedelta(minutes=1),
                _failure_point="after_work_items",
            )
        degraded = oip_service.projection_health_for_organization(
            shipment.organization_id,
            checked_at=breached_at + timedelta(minutes=1),
        )
        assert degraded["health_state"] == "DEGRADED"
        assert degraded["last_evaluation_success_at"] == breached_at.isoformat()
        recovered = oip_service.reconcile(
            organization_id=shipment.organization_id,
            calculation_time=breached_at + timedelta(minutes=2),
        )
        assert recovered["status"] == "FRESH"
        assert OipSituation.query.filter_by(
            situation_type="SLA_COMMITMENT_RISK"
        ).count() == 1
        terminal_runs = [
            row.details_json
            for row in OipProjectionHealthHistory.query.filter_by(
                organization_id=shipment.organization_id
            ).all()
            if row.details_json and row.details_json.get("duration_ms") is not None
        ]
        assert {row["outcome"] for row in terminal_runs} >= {"FRESH", "FAILED"}


def test_abandoned_evaluation_is_degraded_then_recovered(operational_app):
    with operational_app.app_context():
        shipment = _shipment(operational_app, "phase25-abandoned")
        oip_service.reconcile(organization_id=shipment.organization_id)
        state = db.session.get(OipProjectionState, shipment.organization_id)
        abandoned_run = "11111111-1111-4111-8111-111111111111"
        state.status = "REBUILDING"
        state.active_run_id = abandoned_run
        state.rebuild_started_at = utcnow() - timedelta(minutes=30)
        db.session.commit()

        abandoned = oip_service.projection_health_for_organization(
            shipment.organization_id
        )
        assert abandoned["health_state"] == "DEGRADED"
        assert abandoned["reason_code"] == "ABANDONED_EVALUATION_RUN"

        recovered = oip_service.reconcile(organization_id=shipment.organization_id)
        assert recovered["status"] == "FRESH"
        assert any(
            row.reason_code == "ABANDONED_EVALUATION_RUN"
            and (row.details_json or {}).get("abandoned_run_id") == abandoned_run
            for row in OipProjectionHealthHistory.query.filter_by(
                organization_id=shipment.organization_id
            ).all()
        )
