"""Narrow production reconciliation for the Forwarder Expert shipment workflow.

This command deliberately changes only the selected active Expert membership and
the three ADR-039 external-reference records.  It never creates users,
memberships, tenants, shipments, or reference codes.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

from sqlalchemy import or_, select

from backend import create_app
from backend.extensions import db
from backend.external_reference_models import ExternalReferenceType
from backend.external_reference_type_package import load_package
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership
from pathlib import Path
from dotenv import load_dotenv


PERMISSIONS = ("execution_unit.create", "execution_unit.update")
SUPPORTED_CODES = (
    "BILL_OF_LADING_NUMBER",
    "AIR_WAYBILL_NUMBER",
    "CMR_NUMBER",
)
PACKAGE_PATH = Path(__file__).parents[1] / "backend" / "reference_data" / "external_references" / "external-reference-types-v1.0.0.json"


def _membership_projection(membership: OperationalMembership, user: ExpertUser) -> dict[str, Any]:
    permissions = sorted({item for item in membership.permissions if isinstance(item, str) and item})
    return {
        "membership_id": membership.id,
        "organization_id": membership.organization_id,
        "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role},
        "permissions": permissions,
        "missing_permissions": [item for item in PERMISSIONS if item not in permissions],
    }


def _reference_projection(row: ExternalReferenceType | None) -> dict[str, Any]:
    if row is None:
        return {"exists": False}
    return {
        "exists": True,
        "lifecycle_status": row.lifecycle_status,
        "allows_operational_shipment": row.allows_operational_shipment,
        "display_labels": {"fa": row.name_fa, "en": row.name_en},
        "planned_changes": {
            "lifecycle_status": "ACTIVE" if row.lifecycle_status != "ACTIVE" else None,
            "allows_operational_shipment": True if not row.allows_operational_shipment else None,
        },
    }


def _eligible_memberships() -> list[tuple[OperationalMembership, ExpertUser]]:
    return db.session.execute(
        select(OperationalMembership, ExpertUser)
        .join(ExpertUser, ExpertUser.id == OperationalMembership.user_id)
        .where(
            OperationalMembership.is_active.is_(True),
            ExpertUser.is_active.is_(True),
            ExpertUser.role == "expert",
        )
        .order_by(ExpertUser.id, OperationalMembership.organization_id)
    ).all()


def _selected_memberships(identifier: str | None) -> list[tuple[OperationalMembership, ExpertUser]]:
    if not identifier:
        return _eligible_memberships()
    candidate = identifier.strip()
    if not candidate:
        return []
    clauses = [ExpertUser.username == candidate, ExpertUser.email == candidate]
    if candidate.isdigit():
        clauses.append(ExpertUser.id == int(candidate))
    return db.session.execute(
        select(OperationalMembership, ExpertUser)
        .join(ExpertUser, ExpertUser.id == OperationalMembership.user_id)
        .where(
            OperationalMembership.is_active.is_(True), ExpertUser.is_active.is_(True),
            ExpertUser.role == "expert", or_(*clauses),
        ).order_by(OperationalMembership.organization_id)
    ).all()


def run(*, user_identifier: str | None, execute: bool) -> tuple[int, dict[str, Any]]:
    rows = _selected_memberships(user_identifier)
    if not user_identifier:
        return 2, {"result": "USER_SELECTION_REQUIRED", "eligible_memberships": [_membership_projection(m, u) for m, u in rows]}
    if not rows:
        return 2, {"result": "NO_ELIGIBLE_EXPERT_MEMBERSHIP", "user_identifier": user_identifier}
    if len(rows) != 1:
        return 2, {"result": "AMBIGUOUS_EXPERT_MEMBERSHIP", "user_identifier": user_identifier, "memberships": [_membership_projection(m, u) for m, u in rows]}

    membership, user = rows[0]
    package = load_package(PACKAGE_PATH)
    definitions = {item["code"]: item for item in package.definitions}
    references = {row.code: row for row in ExternalReferenceType.query.filter(ExternalReferenceType.code.in_(SUPPORTED_CODES)).all()}
    before = {code: _reference_projection(references.get(code)) for code in SUPPORTED_CODES}
    missing = [code for code in SUPPORTED_CODES if code not in references]
    conflicts = {
        code: [field for field, expected in (
            ("name_fa", definitions[code]["name_fa"]),
            ("name_en", definitions[code]["name_en"]),
            ("source_authority", definitions[code]["provenance"]["source_authority"]),
            ("provenance_reference", definitions[code]["provenance"]["source_reference"]),
        ) if getattr(row, field) != expected]
        for code, row in references.items()
    }
    conflicts = {code: fields for code, fields in conflicts.items() if fields}
    plan = {
        "membership": _membership_projection(membership, user),
        "references": before,
        "missing_reference_codes": missing,
        "definition_conflicts": conflicts,
    }
    if missing:
        return 2, {"result": "REFERENCE_RECORD_MISSING_STOP", "mode": "execute" if execute else "validate", "plan": plan,
                    "message": "A governed record is missing. This tool will not create it because selecting an authorized package actor is a production-domain decision."}
    if conflicts:
        return 2, {"result": "REFERENCE_DEFINITION_CONFLICT_STOP", "mode": "execute" if execute else "validate", "plan": plan}
    if not execute:
        return 0, {"result": "VALIDATED", "mode": "validate", "plan": plan}

    current = list(membership.permissions)
    membership.permissions = current + [item for item in PERMISSIONS if item not in current]
    for row in references.values():
        row.lifecycle_status = "ACTIVE"
        row.allows_operational_shipment = True
    db.session.commit()
    after_references = {code: _reference_projection(ExternalReferenceType.query.filter_by(code=code).one()) for code in SUPPORTED_CODES}
    return 0, {
        "result": "REPAIRED", "mode": "execute",
        "before": plan,
        "after": {"membership": _membership_projection(membership, user), "references": after_references},
        "permissions_added": [item for item in PERMISSIONS if item not in current],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safely reconcile the Forwarder production Expert workflow.")
    parser.add_argument("--user-identifier")
    parser.add_argument("--environment-file", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-repair")
    args = parser.parse_args(argv)
    if args.execute and args.confirm_repair != "REPAIR":
        parser.error("--execute requires --confirm-repair REPAIR")
    if args.environment_file:
        if not args.environment_file.is_file():
            parser.error("production environment file was not found")
        load_dotenv(args.environment_file, override=True)
        if os.environ.get("APP_ENV", "").lower() not in {"production", "prod"}:
            parser.error("environment file must identify Production")
    app = create_app(skip_startup=True)
    with app.app_context():
        code, report = run(user_identifier=args.user_identifier, execute=args.execute)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
