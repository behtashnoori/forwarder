"""Direct PostgreSQL evidence for P1B-UAT-001 shipment-list deduplication."""
from __future__ import annotations

import os

import pytest
from sqlalchemy.engine import make_url

from backend import create_app
from backend.auth import auth_manager
from backend.models import ExpertUser
from backend.operational_models import OperationalOrganization, OperationalShipment


def _url() -> str:
    value = os.environ.get("FORWARDER_PHASE1B_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit disposable Phase 1B PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_phase1b_uat_")
    return value


def _headers(app, username: str) -> dict[str, str]:
    with app.app_context():
        user = ExpertUser.query.filter_by(username=username).one()
        token = auth_manager.generate_tokens(user.id)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_seeded_multileg_shipment_is_unique_filtered_paginated_and_tenant_scoped():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": _url(),
        "SECRET_KEY": "phase1b-shipment-dedup-postgresql-test-only",
    }, skip_startup=True)
    client = app.test_client()

    with app.app_context():
        org_a = OperationalOrganization.query.filter_by(
            name="[PHASE1B-UAT] Organization A"
        ).one()
        shipment_a = OperationalShipment.query.filter_by(
            organization_id=org_a.id
        ).one()

    response = client.get(
        "/api/operational-shipments?page=1&per_page=1",
        headers=_headers(app, "phase1b_uat_admin"),
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json["data"]] == [shipment_a.id]
    assert response.json["meta"]["has_more"] is False

    filtered = client.get(
        "/api/operational-shipments?origin=Location&destination=Location",
        headers=_headers(app, "phase1b_uat_admin"),
    )
    assert [row["id"] for row in filtered.json["data"]] == [shipment_a.id]

    other_org = client.get(
        "/api/operational-shipments",
        headers=_headers(app, "phase1b_uat_org_b_admin"),
    )
    assert other_org.status_code == 200
    assert shipment_a.id not in {row["id"] for row in other_org.json["data"]}
