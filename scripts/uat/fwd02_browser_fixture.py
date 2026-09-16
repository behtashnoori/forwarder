"""Synthetic FWD-02 browser qualification, loopback only, fresh SQLite file.

Run from repository root with `python -m scripts.uat.fwd02_browser_fixture`.
Never opens an existing database, imports customer data or invokes providers.
"""
import os
from pathlib import Path
from uuid import uuid4

os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import bcrypt
from backend import create_app
from backend.extensions import db
from backend.international_geography_catalog import CATALOG_SHA256, apply_catalog
from backend.models import Country, ExpertUser, ShipmentRequest
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.operational_models import OperationalOrganization, OperationalMembership
from backend.services.multi_unit_tracking_service import enable_tracking, add_unit


def create_fixture():
    root = Path(__file__).resolve().parents[2]
    directory = root / "instance" / "fwd02-qualification"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"fwd02-test-{uuid4().hex}.sqlite"
    assert not target.exists()
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + target.as_posix()}, skip_startup=True)
    with app.app_context():
        db.create_all()
        apply_catalog(expected_checksum=CATALOG_SHA256, executed_by="FWD02 fixture",
                      approval_reference="FWD02 global standard authorization", environment="qualification")
        org = OperationalOrganization(name="FWD02 Synthetic Organization")
        other = OperationalOrganization(name="FWD02 Other Synthetic Organization")
        expert = ExpertUser(username="fwd02-expert", full_name="کارشناس آزمایشی مکان", role="expert",
                            is_active=True, password_hash=bcrypt.hashpw(b"Fwd02-test-only!", bcrypt.gensalt()).decode())
        db.session.add_all([org, other, expert])
        db.session.flush()
        db.session.add(OperationalMembership(organization_id=org.id, user_id=expert.id,
                                            permissions=["logistics_point.read", "tracking.read"]))
        kind = LogisticsPointType(immutable_code="WAREHOUSE", fa_name="انبار", en_name="Warehouse",
                                  created_by=expert.id, updated_by=expert.id)
        db.session.add(kind)
        db.session.flush()
        iran = Country.query.filter_by(code="IR").one()
        for index in range(25):
            db.session.add(LogisticsPoint(organization_id=org.id, immutable_code=f"FWD02-{index:02}",
                logistics_point_type_id=kind.id, fa_name=f"انبار آزمایشی {index:02}", en_name=f"Test warehouse {index:02}",
                normalized_name=f"test warehouse {index:02}", country_id=iran.id, geography_key="IR|-|-",
                created_by=expert.id, updated_by=expert.id))
        db.session.add(LogisticsPoint(organization_id=other.id, immutable_code="OTHER-PRIVATE",
            logistics_point_type_id=kind.id, fa_name="انبار خصوصی سازمان دیگر", en_name="Other private warehouse",
            normalized_name="other private warehouse", country_id=iran.id, geography_key="IR|-|-",
            created_by=expert.id, updated_by=expert.id))
        req = ShipmentRequest(ownership_scope="TENANT", operational_organization_id=org.id,
            assigned_to=expert.id, contact_phone="09120000000", status="won", status_request_status="new",
            tracking_code="SR-FWD02X", shipping_type="international",
            customer_first_name="آزمون", customer_last_name="مکان")
        db.session.add(req)
        db.session.commit()
        tracking = enable_tracking(req, expert.id)
        add_unit(tracking, expert.id, unit_code="FWD02-TRUCK", unit_type="truck")
        db.session.commit()
        print(f"FWD02 disposable fixture: {target.name}; request {req.public_id}", flush=True)
    return app


if __name__ == "__main__":
    create_fixture().run(host="127.0.0.1", port=5052, debug=False, use_reloader=False)
