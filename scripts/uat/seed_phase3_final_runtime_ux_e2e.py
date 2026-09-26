"""Owned P3-14 fixture: existing shared-Shipment data plus fresh OIP truth."""

import json
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.operational_models import (
    ExceptionReason,
    OperationalException,
    OperationalShipment,
    utcnow,
)
from backend.services import oip_service
from scripts.uat.seed_phase3_customer_shipment_e2e import main as seed_customer


def main():
    seed_customer()
    fixture_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        shipment = OperationalShipment.query.filter_by(
            public_id=fixture["p304_shipment"]
        ).one()
        reason = ExceptionReason(
            organization_id=shipment.organization_id,
            immutable_code="P314_SHARED_ATTENTION",
            fa_name="استثنای کنترل‌شده آزمون نهایی",
            en_name="P3-14 controlled qualification exception",
            definition="Owned synthetic evidence for Workspace and Control Tower parity.",
            created_by_user_id=shipment.primary_responsible_expert_id,
            updated_by_user_id=shipment.primary_responsible_expert_id,
        )
        db.session.add(reason)
        db.session.flush()
        exception = OperationalException(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id,
            reason_id=reason.id,
            occurred_at=utcnow() - timedelta(minutes=1),
            impact_summary="نیازمند بررسی هماهنگ",
            evidence_summary="داده مصنوعی و تحت مالکیت آزمون P3-14",
            note="P3-14 qualification fixture",
            created_by_user_id=shipment.primary_responsible_expert_id,
        )
        db.session.add(exception)
        db.session.commit()
        oip_service.reconcile(organization_id=shipment.organization_id)
        fixture["p314_oip_reconciled"] = True
        fixture["p314_exception"] = exception.public_id
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
