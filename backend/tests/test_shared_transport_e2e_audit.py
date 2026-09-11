"""Focused regression coverage for the Scenario E supplemental audit."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.cargo_models import ShipmentCargoItem
from backend.models import Customer
from backend.operational_models import OperationalShipment
from scripts.uat.audit_shared_transport_e2e import (
    audit_acceptance_e_owner_identity,
    resolve_cargo_shipment,
)


class AuditSession:
    """Small identity-map session double that preserves the audit's FK lookup."""

    def __init__(self, cargo, shipments, owners):
        self.cargo = cargo
        self.rows = {
            OperationalShipment: shipments,
            Customer: owners,
        }
        self.get_calls = []

    def scalar(self, statement):
        return self.cargo

    def get(self, model, identity):
        self.get_calls.append((model, identity))
        return self.rows.get(model, {}).get(identity)


def _contract(
    *, shipment_present=True, owner_present=True, owner_org=41, shipment_org=41
):
    cargo = SimpleNamespace(
        public_id="cargo-a",
        operational_shipment_id=701,
        cargo_owner_customer_id=801,
    )
    shipment = SimpleNamespace(id=701, organization_id=shipment_org)
    owner = SimpleNamespace(id=801, operational_organization_id=owner_org)
    session = AuditSession(
        cargo,
        {701: shipment} if shipment_present else {},
        {801: owner} if owner_present else {},
    )
    return session, {"cargo_a": "cargo-a", "owner_b_id": 801}


def test_scenario_e_owner_audit_resolves_shipment_by_fk():
    session, fixture = _contract()

    audit_acceptance_e_owner_identity(session, fixture)

    assert session.get_calls[0] == (OperationalShipment, 701)
    assert not hasattr(session.cargo, "operational_shipment")


def test_scenario_e_owner_audit_fails_closed_for_missing_shipment():
    session, fixture = _contract(shipment_present=False)

    with pytest.raises(RuntimeError, match="missing operational shipment"):
        audit_acceptance_e_owner_identity(session, fixture)


def test_scenario_e_owner_audit_fails_for_tenant_mismatch():
    session, fixture = _contract(owner_org=42, shipment_org=41)

    with pytest.raises(RuntimeError, match="owner tenant audit failed"):
        audit_acceptance_e_owner_identity(session, fixture)


def test_scenario_e_owner_audit_fails_closed_for_missing_owner():
    session, fixture = _contract(owner_present=False)

    with pytest.raises(RuntimeError, match="missing cargo owner"):
        audit_acceptance_e_owner_identity(session, fixture)


def test_scenario_e_owner_audit_fails_closed_for_null_shipment_fk():
    session, fixture = _contract()
    session.cargo.operational_shipment_id = None

    with pytest.raises(RuntimeError, match="no operational shipment FK"):
        audit_acceptance_e_owner_identity(session, fixture)


def test_scenario_i_resolves_shipment_from_cargo_fk():
    session, _ = _contract()

    shipment = resolve_cargo_shipment(session, session.cargo, "Acceptance I Cargo I")

    assert shipment is session.rows[OperationalShipment][701]
    assert session.get_calls == [(OperationalShipment, 701)]


def test_scenario_i_shipment_resolution_fails_closed_when_target_is_missing():
    session, _ = _contract(shipment_present=False)

    with pytest.raises(RuntimeError, match="Acceptance I Cargo I references a missing operational shipment"):
        resolve_cargo_shipment(session, session.cargo, "Acceptance I Cargo I")


def test_runtime_audit_never_accesses_nonexistent_cargo_relationship():
    source = (Path(__file__).parents[2] / "scripts" / "uat" / "audit_shared_transport_e2e.py").read_text(encoding="utf-8")

    assert ".operational_shipment)" not in source
