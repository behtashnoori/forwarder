"""Audit persisted P3-15 recovery outcomes in the owned browser database."""
from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.models import (
    CustomerGamification,
    CustomerPortalAccountAudit,
    CustomerPortalRecoveryRequest,
    CustomerPortalRecoveryToken,
)
from backend.security import security


def main() -> None:
    parsed = make_url(os.environ["DATABASE_URL"])
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("P3-15 audit requires APP_ENV=uat")
    if parsed.host != "127.0.0.1" or not (parsed.database or "").startswith(
        "forwarder_workspace_phase1_"
    ):
        raise RuntimeError("P3-15 audit is restricted to its owned database")

    fixture = json.loads(
        Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).read_text(encoding="utf-8")
    )
    app = create_app(skip_startup=True)
    with app.app_context():
        customer = CustomerGamification.query.filter_by(
            email=fixture["portal_customer_email"]
        ).one()
        request = CustomerPortalRecoveryRequest.query.filter_by(
            public_id=fixture["recovery"]["request_public_id"]
        ).one()
        token = CustomerPortalRecoveryToken.query.filter_by(
            recovery_request_id=request.id
        ).one()
        expired = CustomerPortalRecoveryToken.query.filter(
            CustomerPortalRecoveryToken.customer_id == customer.id,
            CustomerPortalRecoveryToken.id != token.id,
            CustomerPortalRecoveryToken.expires_at < token.created_at,
        ).one()
        assert request.delivery_channel == "MANUAL_LINK"
        assert request.delivery_status == "MANUAL_ISSUED"
        assert request.handled_at is not None
        assert token.used_at is not None
        assert token.revoked_at is None
        assert expired.used_at is None
        assert int(customer.session_generation) == 1
        assert security.verify_password(
            "P3-15-replacement-password!", customer.password_hash
        )
        assert not security.verify_password(
            os.environ["FORWARDER_E2E_CUSTOMER_PASSWORD"], customer.password_hash
        )
        assert CustomerPortalAccountAudit.query.filter_by(
            customer_id=customer.id, action="password_reset"
        ).count() == 1
        assert CustomerPortalAccountAudit.query.filter_by(
            customer_id=customer.id, action="recovery_email_suppressed"
        ).count() == 1

        print(
            json.dumps(
                {
                    "adapter": fixture["recovery"]["adapter"],
                    "request_to_valid_token": "PASS",
                    "expiry": "PASS",
                    "single_use": "PASS",
                    "password_reset_audit": "PASS",
                    "session_generation": customer.session_generation,
                    "external_email_delivery": "RELEASE_UAT_EVIDENCE_REQUIRED",
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
