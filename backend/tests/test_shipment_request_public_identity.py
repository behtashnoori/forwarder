"""ADR-038 ShipmentRequest opaque identity contracts."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest
from backend.services.expert_request_detail_service import can_access_request_detail
from backend.services.shipment_request_identity_service import (
    canonical_uuid4,
    resolve_tenant_request_by_public_id,
)
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.models import ExpertUser


@pytest.fixture
def identity_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "identity-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        org_a = OperationalOrganization(name="Identity A", is_active=True)
        org_b = OperationalOrganization(name="Identity B", is_active=True)
        expert_a = ExpertUser(
            username="identity-a", password_hash="unused", full_name="A",
            role="expert", is_active=True,
        )
        former = ExpertUser(
            username="identity-former", password_hash="unused", full_name="Former",
            role="expert", is_active=True,
        )
        db.session.add_all([org_a, org_b, expert_a, former])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=org_a.id, user_id=expert_a.id, is_active=True, permissions=[]),
            OperationalMembership(organization_id=org_a.id, user_id=former.id, is_active=True, permissions=[]),
        ])
        same = _request("IDENTITY-SAME", org_a.id, expert_a.id)
        foreign = _request("IDENTITY-FOREIGN", org_b.id, None)
        quarantined = ShipmentRequest(
            tracking_code="IDENTITY-QUARANTINED", contact_phone="09120000003",
            status="new", status_request_status="new",
            ownership_scope="LEGACY_QUARANTINED", operational_organization_id=None,
        )
        db.session.add_all([same, foreign, quarantined])
        db.session.commit()
        app.config["identity_ids"] = {
            "org_a": org_a.id,
            "same": same.id,
            "foreign": foreign.id,
            "quarantined": quarantined.id,
            "expert": expert_a.id,
            "former": former.id,
        }
        yield app
        db.session.remove()
        db.drop_all()


def _request(code: str, organization_id: int, assigned_to: int | None) -> ShipmentRequest:
    return ShipmentRequest(
        tracking_code=code, contact_phone="09120000001", status="new",
        status_request_status="new", ownership_scope="TENANT",
        operational_organization_id=organization_id, assigned_to=assigned_to,
    )


def test_model_generates_canonical_uuid4_and_rejects_mutation(identity_app):
    with identity_app.app_context():
        row = db.session.get(ShipmentRequest, identity_app.config["identity_ids"]["same"])
        original = row.public_id
        parsed = UUID(original)
        assert parsed.version == 4
        assert original == str(parsed)
        row.public_id = str(uuid4())
        with pytest.raises(ValueError, match="public_id is immutable"):
            db.session.commit()
        db.session.rollback()
        assert db.session.get(ShipmentRequest, row.id).public_id == original


def test_duplicate_public_id_is_rejected(identity_app):
    with identity_app.app_context():
        row = db.session.get(ShipmentRequest, identity_app.config["identity_ids"]["same"])
        duplicate = _request("IDENTITY-DUPLICATE", row.operational_organization_id, None)
        duplicate.public_id = row.public_id
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_tenant_resolver_is_strict_fenced_and_not_authorization(identity_app):
    with identity_app.app_context():
        ids = identity_app.config["identity_ids"]
        same = db.session.get(ShipmentRequest, ids["same"])
        foreign = db.session.get(ShipmentRequest, ids["foreign"])
        quarantined = db.session.get(ShipmentRequest, ids["quarantined"])
        assert resolve_tenant_request_by_public_id(ids["org_a"], same.public_id).id == same.id
        assert resolve_tenant_request_by_public_id(ids["org_a"], foreign.public_id) is None
        assert resolve_tenant_request_by_public_id(ids["org_a"], quarantined.public_id) is None
        for malformed in (None, "", "1", str(uuid4()).upper(), "00000000-0000-1000-8000-000000000000"):
            assert canonical_uuid4(malformed) is None
            assert resolve_tenant_request_by_public_id(ids["org_a"], malformed) is None
        assert resolve_tenant_request_by_public_id(True, same.public_id) is None
        former = db.session.get(ExpertUser, ids["former"])
        assert can_access_request_detail(same, {"id": former.id, "role": former.role}) is False


def _migration_module():
    path = Path(__file__).parents[1] / "migrations" / "versions" / "20260902_shipment_request_public_id.py"
    spec = importlib.util.spec_from_file_location("shipment_request_public_id_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_is_uuid4_random_retry_safe_and_tracking_neutral():
    migration = _migration_module()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE shipment_request (id INTEGER PRIMARY KEY, tracking_code VARCHAR(32), public_id VARCHAR(36))"
        ))
        preserved = str(uuid4())
        connection.execute(text(
            "INSERT INTO shipment_request (id, tracking_code, public_id) VALUES "
            "(1, 'SR000001', NULL), (2, 'SR-ABC123', NULL), (3, 'SR000003', :preserved)"
        ), {"preserved": preserved})
        migration._backfill_public_ids(connection)
        migration._validate_public_ids(connection)
        first = connection.execute(text(
            "SELECT id, tracking_code, public_id FROM shipment_request ORDER BY id"
        )).all()
        migration._backfill_public_ids(connection)
        second = connection.execute(text(
            "SELECT id, tracking_code, public_id FROM shipment_request ORDER BY id"
        )).all()
    assert first == second
    assert first[2].public_id == preserved
    assert [row.tracking_code for row in first] == ["SR000001", "SR-ABC123", "SR000003"]
    assert len({row.public_id for row in first}) == 3
    for row in first:
        assert UUID(row.public_id).version == 4
        assert row.public_id == str(UUID(row.public_id))
        assert row.public_id not in {str(row.id), row.tracking_code}
