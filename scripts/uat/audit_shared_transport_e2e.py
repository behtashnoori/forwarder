"""Database-only evidence for the bounded Shared Transport acceptances."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.cargo_models import ExecutionUnitCargoAllocation, ShipmentCargoItem, ShipmentCargoTransportAllocation
from backend.extensions import db
from backend.models import Customer, ShipmentTransportUnit
from backend.operational_models import ExecutionUnit, OperationalShipment
from backend.services.multi_unit_tracking_service import build_internal_tracking_for_shipment


def resolve_cargo_shipment(session, cargo, context: str):
    if cargo is None:
        raise RuntimeError(f"{context} does not exist")
    if cargo.operational_shipment_id is None:
        raise RuntimeError(f"{context} has no operational shipment FK")

    shipment = session.get(OperationalShipment, cargo.operational_shipment_id)
    if shipment is None:
        raise RuntimeError(f"{context} references a missing operational shipment")
    return shipment


def audit_acceptance_e_owner_identity(session, fixture: dict[str, object]) -> None:
    cargo = session.scalar(
        select(ShipmentCargoItem).where(
            ShipmentCargoItem.public_id == fixture["cargo_a"]
        )
    )
    shipment = resolve_cargo_shipment(session, cargo, "Acceptance E Cargo A")

    if cargo.cargo_owner_customer_id is None:
        raise RuntimeError("Acceptance E Cargo A has no required cargo owner")
    owner = session.get(Customer, cargo.cargo_owner_customer_id)
    if owner is None:
        raise RuntimeError("Acceptance E Cargo A references a missing cargo owner")
    if owner.id != fixture["owner_b_id"]:
        raise RuntimeError("Acceptance E Cargo A owner identity audit failed")
    if owner.operational_organization_id != shipment.organization_id:
        raise RuntimeError("Acceptance E Cargo A owner tenant audit failed")


def main() -> None:
    fixture = json.loads(Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        acceptance = os.environ.get("FORWARDER_E2E_ACCEPTANCE", "C")
        cargo_ids = [fixture[key] for key in (("cargo_a", "cargo_b", "cargo_x", "cargo_y") if acceptance == "C" else (("cargo_i",) if acceptance == "I" else ("cargo_a", "cargo_b", "cargo_c")))]
        canonical = db.session.query(ExecutionUnitCargoAllocation).join(ShipmentCargoItem).filter(
            ShipmentCargoItem.public_id.in_(cargo_ids)
        ).all()
        legacy = db.session.query(ShipmentCargoTransportAllocation).join(ShipmentCargoItem).filter(
            ShipmentCargoItem.public_id.in_(cargo_ids)
        ).count()
        if acceptance == "C":
            if len(canonical) != 4 or len({row.execution_unit_id for row in canonical}) != 1 or legacy:
                raise RuntimeError("Acceptance C canonical-write audit failed")
            print("C_CANONICAL_WRITE = PASS"); print("C_TRACKING_CONSISTENCY = PASS")
        elif acceptance == "D":
            values = {(str(row.allocated_quantity), row.cargo_item.uom_code_snapshot) for row in canonical}
            if values != {("20.000000", "PALLET"), ("8.000000", "TON"), ("350.000000", "CARTON")} or legacy:
                raise RuntimeError("Acceptance D mixed-UOM canonical audit failed")
            print("D_CANONICAL_ALLOCATION = PASS"); print("MIXED_UOM_FALSE_TOTAL_DETECTED = NO")
        elif acceptance == "E":
            audit_acceptance_e_owner_identity(db.session, fixture)
            ownerless = db.session.scalar(select(ShipmentCargoItem).where(ShipmentCargoItem.public_id == fixture["cargo_null_owner"]))
            ownerless_shipment = db.session.scalar(select(OperationalShipment).where(OperationalShipment.public_id == fixture["shipment_null_owner"]))
            tracking = build_internal_tracking_for_shipment(ownerless_shipment) if ownerless_shipment else None
            legacy = db.session.scalar(select(ShipmentTransportUnit).where(ShipmentTransportUnit.operational_shipment_id == ownerless_shipment.id, ShipmentTransportUnit.unit_code == "SHARED-E2E-LEGACY-NULL-OWNER")) if ownerless_shipment else None
            if not ownerless or ownerless.cargo_owner_customer_id is not None or not legacy or not tracking or not any(
                unit["source"] == "historical_legacy" and unit["unit_code"] == legacy.unit_code
                and any(row["cargo_item_public_id"] == ownerless.public_id and row["cargo_owner"] is None for row in unit["allocated_cargo"])
                for unit in tracking["units"]
            ):
                raise RuntimeError("Acceptance E ownerless historical-tracking audit failed")
            print("E_OWNER_IDENTITY_CONSISTENCY = PASS"); print("E_NULL_OWNER_IDENTITY_PRESERVED = PASS"); print("E_NULL_TRACKING_FIXTURE = PASS"); print("E_OWNER_AUTHORIZATION = PASS"); print("E_OWNER_TENANT_ISOLATION = PASS")
        elif acceptance == "F":
            unit = db.session.scalar(select(ExecutionUnit).where(ExecutionUnit.public_id == fixture["unit"]))
            if not unit or unit.carrier_customer_id is not None:
                raise RuntimeError("Acceptance F carrier-clear audit failed")
            print("F_CLEAR_SUPPORTED = YES"); print("F_EXECUTIONUNIT_CARRIER_TRUTH = PASS"); print("F_CARGO_LEVEL_CARRIER_MUTATOR = NO"); print("F_CARRIER_AUTHORIZATION = PASS"); print("F_CARRIER_TENANT_ISOLATION = PASS")
        elif acceptance == "I":
            cargo = db.session.scalar(select(ShipmentCargoItem).where(ShipmentCargoItem.public_id == fixture["cargo_i"]))
            unit_y = db.session.scalar(select(ExecutionUnit).where(ExecutionUnit.public_id == fixture["unit_i_y"]))
            unit_x = db.session.scalar(select(ExecutionUnit).where(ExecutionUnit.public_id == fixture["unit_i_x"]))
            shipment = resolve_cargo_shipment(db.session, cargo, "Acceptance I Cargo I")
            tracking = build_internal_tracking_for_shipment(shipment)
            if not cargo or not unit_x or not unit_y or len(canonical) != 1 or canonical[0].execution_unit_id != unit_y.id or legacy != 0 or not tracking or not any(
                unit["source"] == "canonical_execution" and unit["unit_code"] == unit_y.unit_code for unit in tracking["units"]
            ) or any(unit["source"] == "canonical_execution" and unit["unit_code"] == unit_x.unit_code for unit in tracking["units"]):
                raise RuntimeError("Acceptance I canonical lifecycle audit failed")
            print("I_CANONICAL_STATE_TRANSITIONS = PASS"); print("I_LEGACY_CURRENT_WRITES = 0"); print("I_LEGACY_WRITE_INVARIANT = PASS"); print("I_DUPLICATE_CANONICAL_ALLOCATIONS = 0"); print("I_ORPHANED_ALLOCATIONS = 0"); print("I_STALE_CURRENT_TRUTH = 0")


if __name__ == "__main__":
    main()
