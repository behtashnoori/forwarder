"""Extend the owned Workspace fixture with synthetic Phase 2 SLA evidence."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.operational_models import (
    ExceptionReason,
    OperationalAudit,
    OperationalException,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    OrganizationSlaRule,
)
from backend.services import oip_service
from scripts.uat.seed_operational_workspace_phase1_e2e import USERNAMES, main as seed_phase1


def _assert_owned_database() -> None:
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("Workspace Phase 2 E2E seed requires APP_ENV=uat")
    parsed = make_url(os.environ["DATABASE_URL"])
    if parsed.host != "127.0.0.1" or not (parsed.database or "").startswith(
        "forwarder_workspace_phase2_"
    ):
        raise RuntimeError(
            "Workspace Phase 2 E2E seed is restricted to its owned loopback database"
        )


def main() -> None:
    _assert_owned_database()
    seed_phase1()
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).resolve()
    fixture = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)

    with app.app_context():
        owner_id = fixture["owner_id"]
        org = db.session.scalar(
            db.select(OperationalOrganization)
            .join(OperationalMembership)
            .where(OperationalMembership.user_id == owner_id)
        )
        shipment = db.session.scalar(
            db.select(OperationalShipment).where(
                OperationalShipment.public_id == fixture["active_shipment_public_id"],
                OperationalShipment.organization_id == org.id,
            )
        )
        # Resolve the deterministic admin by its username without leaking an internal
        # identifier into the browser fixture contract.
        from backend.models import ExpertUser

        admin = db.session.scalar(
            db.select(ExpertUser).where(ExpertUser.username == USERNAMES["admin"])
        )
        admin_membership = db.session.scalar(
            db.select(OperationalMembership).where(
                OperationalMembership.organization_id == org.id,
                OperationalMembership.user_id == admin.id,
            )
        )
        if admin_membership is None:
            raise RuntimeError("Synthetic organization admin membership is missing")
        phase2_permissions = {
            "operational_execution.read",
            "operational_execution.manage",
            "oip.reconcile",
        }
        for membership in db.session.scalars(
            db.select(OperationalMembership).where(
                OperationalMembership.organization_id == org.id
            )
        ):
            membership.permissions = sorted(
                set(membership.permissions or ()) | phase2_permissions
            )

        now = datetime.now(timezone.utc)
        reason = ExceptionReason(
            organization_id=org.id,
            immutable_code="WORKSPACE_PHASE2_SYNTHETIC",
            fa_name="اختلال هماهنگی مصنوعی",
            en_name="Synthetic coordination disruption",
            definition="Synthetic browser qualification data for Workspace Phase 2",
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
        )
        rule = OrganizationSlaRule(
            organization_id=org.id,
            process_type="EXCEPTION_RESPONSE",
            name="پاسخ به استثنای مصنوعی",
            duration_minutes=60,
            warning_minutes=15,
            is_active=True,
            effective_from=now - timedelta(hours=3),
            version=1,
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=3),
        )
        db.session.add_all([reason, rule])
        db.session.flush()
        db.session.add(
            OperationalAudit(
                organization_id=org.id,
                actor_user_id=admin.id,
                action="organization_sla_rule.created",
                entity_type="OrganizationSlaRule",
                entity_id=rule.id,
                metadata_json={
                    "after": {
                        "public_id": rule.public_id,
                        "process_type": rule.process_type,
                        "name": rule.name,
                        "duration_minutes": rule.duration_minutes,
                        "warning_minutes": rule.warning_minutes,
                        "is_active": rule.is_active,
                        "effective_from": rule.effective_from.isoformat(),
                        "version": rule.version,
                    }
                },
            )
        )

        exceptions = []
        for suffix, age, impact, evidence in (
            (
                "healthy",
                timedelta(minutes=5),
                "اثر محدود و تحت کنترل برای اثبات وضعیت سالم",
                "گزارش مصنوعی سالم شماره ۱",
            ),
            (
                "warning",
                timedelta(minutes=50),
                "احتمال تأخیر در هماهنگی تحویل",
                "گزارش مصنوعی هشدار شماره ۲",
            ),
            (
                "breached",
                timedelta(minutes=75),
                "هماهنگی تحویل از موعد پاسخ عبور کرده است",
                "گزارش مصنوعی نقض شماره ۳",
            ),
        ):
            row = OperationalException(
                organization_id=org.id,
                operational_shipment_id=shipment.id,
                reason_id=reason.id,
                occurred_at=now - age,
                note=f"استثنای مصنوعی {suffix}",
                impact_summary=impact,
                evidence_summary=evidence,
                created_by_user_id=owner_id,
                created_at=now - age,
            )
            db.session.add(row)
            exceptions.append(row)

        db.session.commit()
        oip_service.reconcile(organization_id=org.id, calculation_time=now)

        fixture.update(
            {
                "organization_id": org.id,
                "exception_rule_public_id": rule.public_id,
                "exception_reason_public_id": reason.public_id,
                "phase2_exception_public_ids": [row.public_id for row in exceptions],
            }
        )
        manifest_path.write_text(
            json.dumps(fixture, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        print("OPERATIONAL_WORKSPACE_PHASE2_FIXTURE_SEEDED=YES")


if __name__ == "__main__":
    main()
