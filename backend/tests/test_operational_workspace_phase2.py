from datetime import timedelta

import pytest

from backend.extensions import db
from backend.models import ExpertUser
from backend.oip_models import OipSituation
from backend.operational_models import (
    ExceptionReason,
    OperationalException,
    OperationalMembership,
    OperationalSlaCommitment,
    OperationalWorkItem,
    OrganizationSlaRule,
    utcnow,
)
from backend.services import oip_service
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
