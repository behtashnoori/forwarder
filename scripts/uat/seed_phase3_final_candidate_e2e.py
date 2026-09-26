"""Seed the owned P3-15 browser proof, including test-adapter recovery links."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    CustomerGamification,
    CustomerPortalRecoveryRequest,
    CustomerPortalRecoveryToken,
)
from backend.services.customer_account_lifecycle_service import issue_recovery_token
from scripts.uat.seed_operational_workspace_phase1_e2e import main as seed_workspace


def _assert_owned_database() -> None:
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("P3-15 E2E seed requires APP_ENV=uat")
    parsed = make_url(os.environ["DATABASE_URL"])
    if parsed.host != "127.0.0.1" or not (parsed.database or "").startswith(
        "forwarder_workspace_phase1_"
    ):
        raise RuntimeError(
            "P3-15 E2E seed is restricted to its owned loopback database"
        )


def main() -> None:
    _assert_owned_database()
    seed_workspace()
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).resolve()
    fixture = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)

    with app.app_context():
        customer = CustomerGamification.query.filter_by(
            email=fixture["portal_customer_email"]
        ).one()
        expired = issue_recovery_token(customer, "RESET")
        CustomerPortalRecoveryToken.query.filter_by(customer_id=customer.id).update(
            {"expires_at": datetime.utcnow() - timedelta(seconds=1)}
        )
        db.session.commit()
        recovery_request = CustomerPortalRecoveryRequest(
            customer_id=customer.id,
            purpose="RESET",
            delivery_channel="MANUAL_LINK",
            delivery_status="MANUAL_ISSUED",
            delivery_attempted_at=datetime.utcnow(),
        )
        db.session.add(recovery_request)
        db.session.flush()
        valid = issue_recovery_token(
            customer, "RESET", recovery_request=recovery_request
        )

        fixture["recovery"] = {
            "valid_token": valid,
            "expired_token": expired,
            "request_public_id": recovery_request.public_id,
            "adapter": "OWNED_UAT_MANUAL_LINK",
        }

    manifest_path.write_text(
        json.dumps(fixture, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    print("PHASE3_FINAL_CANDIDATE_FIXTURE_SEEDED=YES")


if __name__ == "__main__":
    main()
