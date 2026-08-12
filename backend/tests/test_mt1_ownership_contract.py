import json
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint

from backend.models import Customer, DocumentAuditEvent, ShipmentRequest
from backend.services.ownership_service import OwnershipContractError, require_tenant_resource


def test_canonical_roots_have_explicit_ownership_envelopes():
    for model in (ShipmentRequest, Customer):
        assert "operational_organization_id" in model.__table__.c
        assert "ownership_scope" in model.__table__.c
        checks = {c.name for c in model.__table__.constraints if isinstance(c, CheckConstraint)}
        assert any("ownership_envelope" in name for name in checks)


def test_quote_has_mechanical_same_tenant_fk_in_migration():
    migration = (Path(__file__).parents[1] / "migrations/versions/20260823_mt1_ownership_expand.py").read_text(encoding="utf-8")
    assert "fk_expert_quote_request_same_org" in migration
    assert '[parent_column, "operational_organization_id"]' in migration


def test_null_or_intake_resource_cannot_be_used_as_tenant_resource():
    with pytest.raises(OwnershipContractError):
        require_tenant_resource(ShipmentRequest(ownership_scope="INTAKE"))
    with pytest.raises(OwnershipContractError):
        require_tenant_resource(ShipmentRequest())


def test_assignment_never_establishes_ownership():
    row = ShipmentRequest(ownership_scope="INTAKE", assigned_to=42)
    assert row.operational_organization_id is None
    with pytest.raises(OwnershipContractError):
        require_tenant_resource(row)


def test_tenant_resource_requires_and_returns_canonical_owner():
    row = ShipmentRequest(ownership_scope="TENANT", operational_organization_id=7)
    assert require_tenant_resource(row, expected_organization_id=7) == 7
    with pytest.raises(OwnershipContractError):
        require_tenant_resource(row, expected_organization_id=8)


def test_document_audit_is_mixed_scope_not_fake_tenant():
    checks = {c.name for c in DocumentAuditEvent.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_document_audit_event_scope" in checks


def test_machine_readable_matrix_has_no_unknown_classification():
    path = Path(__file__).parents[2] / "docs/architecture/mt-1-canonical-ownership-matrix.json"
    matrix = json.loads(path.read_text(encoding="utf-8"))
    assert "UNKNOWN" not in matrix["classifications"]
    assert matrix["decisions"]["assignment_establishes_ownership"] is False


def test_expand_migration_never_backfills_or_clears_quarantine():
    migration = (Path(__file__).parents[1] / "migrations/versions/20260823_mt1_ownership_expand.py").read_text(encoding="utf-8").lower()
    assert "update shipment_request" not in migration
    assert "update customer" not in migration
    assert "ownership_certification" not in migration
    assert "synthetic" not in migration
