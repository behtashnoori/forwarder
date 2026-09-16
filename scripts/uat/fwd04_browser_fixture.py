"""Disposable real-backend fixture for FWD-04 browser UAT.

The fixture deliberately creates only synthetic tenant data.  Assignment is
not seeded: the browser runner calls the production assignment API so that its
normal authorization, persistence and ``ExpertConsoleLog`` fact are exercised.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import bcrypt

os.environ.setdefault("APP_ENV", "test")

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization


ASSIGNED_TRACKING = "SR-FWD04-ASSIGNED"
MISSING_FACT_TRACKING = "SR-FWD04-NOFACT"
ADMIN_USERNAME = "fwd04-assigner"
EXPERT_USERNAME = "fwd04-expert"


def create_fixture(password: str):
    """Build an isolated SQLite database and return the real Flask application."""
    if not password:
        raise ValueError("FWD04_UAT_PASSWORD is required")
    root = Path(tempfile.gettempdir()) / "forwarder-fwd04-uat"
    root.mkdir(parents=True, exist_ok=True)
    database = root / f"fwd04-{uuid4().hex}.sqlite"
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + database.as_posix()},
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        organization = OperationalOrganization(name="[FWD04-UAT] Synthetic Tenant")
        assigner = ExpertUser(
            username=ADMIN_USERNAME, full_name="[FWD04-UAT] Assignment Administrator",
            password_hash=password_hash, role="admin", authority="ORGANIZATION_ADMIN", is_active=True,
        )
        expert = ExpertUser(
            username=EXPERT_USERNAME, full_name="[FWD04-UAT] Assigned Expert",
            password_hash=password_hash, role="expert", authority="EXPERT", is_active=True,
            can_handle_international=True,
        )
        db.session.add_all([organization, assigner, expert])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=organization.id, user_id=assigner.id, is_active=True, permissions=[]),
            OperationalMembership(organization_id=organization.id, user_id=expert.id, is_active=True, permissions=[]),
        ])
        # Both rows are legitimately visible to their tenant after assignment;
        # neither receives an assignment timestamp through fixture construction.
        db.session.add_all([
            ShipmentRequest(
                ownership_scope="TENANT", operational_organization_id=organization.id,
                contact_phone="09040000001", customer_first_name="Synthetic", customer_last_name="Assigned",
                tracking_code=ASSIGNED_TRACKING, shipping_type="international", status="new",
            ),
            ShipmentRequest(
                ownership_scope="TENANT", operational_organization_id=organization.id,
                contact_phone="09040000002", customer_first_name="Synthetic", customer_last_name="No Fact",
                tracking_code=MISSING_FACT_TRACKING, shipping_type="international", status="new",
            ),
        ])
        db.session.commit()
    print(f"FWD04 disposable fixture: {database.name}; assigned={ASSIGNED_TRACKING}; no_fact={MISSING_FACT_TRACKING}", flush=True)
    return app


if __name__ == "__main__":
    create_fixture(os.getenv("FWD04_UAT_PASSWORD", "")).run(
        host="127.0.0.1", port=int(os.getenv("FWD04_UAT_API_PORT", "5054")), debug=False, use_reloader=False,
    )
