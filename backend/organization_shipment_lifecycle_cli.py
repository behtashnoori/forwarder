"""Guarded plan/apply/verify for the approved V1 Shipment lifecycle policy."""
from __future__ import annotations

import argparse
from datetime import timedelta
import hashlib
import json
import sys

from sqlalchemy import func, select

from backend import create_app
from backend.closure_models import (
    BLOCKER_CRITERIA,
    WARNING_CRITERIA,
    ClosureDecision,
)
from backend.config import is_production_environment
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalOrganization, OperationalShipment, utcnow
from backend.services import closure_service, shipment_stage_service
from backend.shipment_stage_models import (
    CANONICAL_STAGE_CODES,
    ShipmentOperationalStageEvent,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Approved Organization Shipment lifecycle V1")
    parser.add_argument("command", choices=("plan", "apply", "verify"))
    parser.add_argument("--organization-public-id", required=True)
    parser.add_argument("--actor-username", required=True)
    parser.add_argument("--shipment-public-id", required=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--operator")
    parser.add_argument("--approval-reference")
    return parser


def _stage_payload(expected_version: int) -> dict:
    return {
        "expected_version": expected_version,
        "effective_from": (utcnow() - timedelta(seconds=1)).isoformat(),
        "stages": [
            {
                "code": code,
                "display_name_fa": shipment_stage_service.CANONICAL_NAMES_FA[code],
                "sequence": sequence,
                "active": True,
                "required_for_completion": True,
            }
            for sequence, code in enumerate(CANONICAL_STAGE_CODES, 1)
        ],
    }


def _closure_payload(expected_version: int) -> dict:
    return {
        "expected_version": expected_version,
        "effective_from": (utcnow() - timedelta(seconds=1)).isoformat(),
        "criteria": [
            *(
                {"scope": "GENERAL", "code": code, "mandatory": True}
                for code in BLOCKER_CRITERIA
            ),
            *(
                {"scope": "GENERAL", "code": code, "mandatory": False}
                for code in WARNING_CRITERIA
            ),
        ],
    }


def _exact_stages(configuration: dict) -> bool:
    if not configuration["versions"]:
        return False
    stages = configuration["versions"][0]["stages"]
    return [row["code"] for row in stages] == list(CANONICAL_STAGE_CODES) and all(
        row["sequence"] == sequence and row["active"] and row["required_for_completion"]
        and row["display_name_fa"] == shipment_stage_service.CANONICAL_NAMES_FA[row["code"]]
        for sequence, row in enumerate(stages, 1)
    )


def _exact_closure(configuration: dict) -> bool:
    if not configuration["versions"]:
        return False
    actual = {
        (row["scope"], row["code"], row["mandatory"])
        for row in configuration["versions"][0]["criteria"]
    }
    expected = {
        *({("GENERAL", code, True) for code in BLOCKER_CRITERIA}),
        *({("GENERAL", code, False) for code in WARNING_CRITERIA}),
    }
    return actual == expected


def _context(organization_public_id: str, actor_username: str, shipment_public_id: str):
    organization = OperationalOrganization.query.filter_by(public_id=organization_public_id).one()
    actor = ExpertUser.query.filter_by(username=actor_username).one()
    shipment = OperationalShipment.query.filter_by(public_id=shipment_public_id).one()
    if shipment.organization_id != organization.id:
        raise RuntimeError("Shipment does not belong to the approved Organization")
    user = {"id": actor.id, "role": actor.role}
    if shipment_stage_service.admin_context(user) != organization.id:
        raise RuntimeError("Actor is not the active Organization Admin")
    return organization, actor, shipment, user


def _receipt(organization, shipment, user) -> dict:
    stages = shipment_stage_service.configuration(user)
    closure = closure_service.configuration(user)
    applicable_stage = shipment_stage_service.applicable(organization.id)
    applicable_policy = closure_service.applicable(shipment, utcnow())
    current_stages = stages["versions"][0]["stages"] if stages["versions"] else []
    stage_events = db.session.scalar(select(func.count()).select_from(ShipmentOperationalStageEvent).where(
        ShipmentOperationalStageEvent.operational_shipment_id == shipment.id,
    )) or 0
    closure_actions = db.session.scalar(select(func.count()).select_from(ClosureDecision).where(
        ClosureDecision.operational_shipment_id == shipment.id,
    )) or 0
    contract = {
        "stage_codes": list(CANONICAL_STAGE_CODES),
        "blockers": list(BLOCKER_CRITERIA),
        "warnings": list(WARNING_CRITERIA),
    }
    return {
        "organization_public_id": organization.public_id,
        "shipment_public_id": shipment.public_id,
        "project_id": shipment.project_id,
        "stage_configuration_exact": _exact_stages(stages),
        "closure_policy_exact": _exact_closure(closure),
        "operational_stage_count": sum(bool(row["active"]) for row in current_stages),
        "operational_stage_required_count": sum(bool(row["active"] and row["required_for_completion"]) for row in current_stages),
        "closure_policy_active": int(applicable_policy is not None),
        "stage_policy_active": int(applicable_stage is not None),
        "walkthrough_stage_progress_count": int(stage_events),
        "walkthrough_closure_action_count": int(closure_actions),
        "contract_sha256": hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    app = create_app(skip_startup=True)
    environment = str(app.config.get("APP_ENV", "development")).strip().lower()
    if is_production_environment(environment):
        print("REFUSED: this command never applies to Production.", file=sys.stderr)
        return 2
    with app.app_context():
        organization, actor, shipment, user = _context(
            args.organization_public_id, args.actor_username, args.shipment_public_id
        )
        before = _receipt(organization, shipment, user)
        if args.command in {"plan", "verify"}:
            print(json.dumps({"status": "VERIFIED" if args.command == "verify" else "PLANNED", **before}, ensure_ascii=False, sort_keys=True))
            if args.command == "verify" and not (
                before["stage_configuration_exact"] and before["closure_policy_exact"]
                and before["operational_stage_count"] == 5
                and before["operational_stage_required_count"] == 5
                and before["closure_policy_active"] == 1
                and before["walkthrough_stage_progress_count"] == 0
                and before["walkthrough_closure_action_count"] == 0
            ):
                return 3
            return 0
        if not args.confirm or not args.operator or not args.approval_reference:
            print("REFUSED: apply requires --confirm, --operator, and --approval-reference.", file=sys.stderr)
            return 2
        if before["walkthrough_stage_progress_count"] or before["walkthrough_closure_action_count"]:
            print("REFUSED: preserved Shipment already has lifecycle actions.", file=sys.stderr)
            return 3
        if not before["stage_configuration_exact"]:
            existing = shipment_stage_service.configuration(user)["versions"]
            if existing:
                print("REFUSED: an existing non-exact stage configuration requires Product Owner review.", file=sys.stderr)
                return 3
            shipment_stage_service.save_configuration(
                user, _stage_payload(0),
                f"walkthrough-org-stages-v1:{organization.public_id}",
            )
        if not before["closure_policy_exact"]:
            existing = closure_service.configuration(user)["versions"]
            if existing:
                db.session.rollback()
                print("REFUSED: an existing non-exact closure policy requires Product Owner review.", file=sys.stderr)
                return 3
            closure_service.save_policy(
                user, _closure_payload(0),
                f"walkthrough-closure-v1:{organization.public_id}",
            )
        db.session.commit()
        after = _receipt(organization, shipment, user)
        after.update(status="APPLIED", operator=args.operator, approval_reference=args.approval_reference)
        print(json.dumps(after, ensure_ascii=False, sort_keys=True))
        return 0 if all((
            after["stage_configuration_exact"], after["closure_policy_exact"],
            after["operational_stage_count"] == 5,
            after["operational_stage_required_count"] == 5,
            after["closure_policy_active"] == 1,
            after["walkthrough_stage_progress_count"] == 0,
            after["walkthrough_closure_action_count"] == 0,
        )) else 3


if __name__ == "__main__":
    raise SystemExit(main())
