"""Canonical tenant-scoped shared transport allocation commands (ADR-046)."""
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import or_, select

from backend.cargo_models import ExecutionUnitCargoAllocation, ShipmentCargoItem
from backend.extensions import db
from backend.models import Customer, CustomerRoleAssignment
from backend.operational_models import ExecutionUnit, OperationalShipment, Project
from backend.services.operational_service import OperationalError, organization_for_user, require_permission
from backend.services.assigned_work_authorization import authorize_work_action
from backend.services.assigned_work_authorization import authorize_document_management
from backend.services import cargo_allocation_service as allocation_history
from backend.operational_models import utcnow


def _authorized_shipment(cargo: ShipmentCargoItem, user: dict) -> OperationalShipment:
    shipment = db.session.get(OperationalShipment, cargo.operational_shipment_id)
    if not shipment or shipment.organization_id != organization_for_user(int(user["id"])):
        raise OperationalError("NOT_FOUND", "Cargo not found.", 404)
    # Allocation follows the shipment's canonical current-work scope.  A
    # project may supply business visibility, but direct shipments are rooted
    # in their responsible Expert and must not be excluded merely for lacking
    # a project.
    if not authorize_work_action(user, shipment, "shipment.read").allowed:
        raise OperationalError("NOT_FOUND", "Cargo not found.", 404)
    return shipment


def _unit(execution_public_id: str, user: dict) -> ExecutionUnit:
    """Resolve an execution inside the sole active tenant context."""
    organization_id = organization_for_user(int(user["id"]))
    unit = db.session.scalar(select(ExecutionUnit).where(
        ExecutionUnit.public_id == execution_public_id,
        ExecutionUnit.organization_id == organization_id,
    ))
    if not unit:
        raise OperationalError("NOT_FOUND", "Execution not found.", 404)
    return unit


def _customer_view(customer: Customer | None) -> dict | None:
    if not customer:
        return None
    return {
        "public_label": customer.company_name or " ".join(
            part for part in (customer.first_name, customer.last_name) if part
        ),
    }


def _cargo_view(cargo: ShipmentCargoItem, shipment: OperationalShipment) -> dict:
    owner = db.session.get(Customer, cargo.cargo_owner_customer_id) if cargo.cargo_owner_customer_id else None
    project = db.session.get(Project, shipment.project_id) if shipment.project_id else None
    return {
        "public_id": cargo.public_id,
        "description": cargo.display_name_snapshot,
        "quantity": str(cargo.quantity),
        "uom": {"code": cargo.uom_code_snapshot, "symbol": cargo.uom_symbol_snapshot},
        "cargo_owner": _customer_view(owner),
        "shipment_public_id": shipment.public_id,
        "project": {"public_id": project.public_id, "code": project.project_code} if project else None,
    }


def eligible_cargo(*, execution_public_id: str, user: dict) -> list[dict]:
    """Return only cargo the caller can allocate; no tenant-wide discovery."""
    require_permission(user, "execution_unit.update")
    _unit(execution_public_id, user)
    organization_id = organization_for_user(int(user["id"]))
    rows = db.session.scalars(
        select(ShipmentCargoItem)
        .join(OperationalShipment, OperationalShipment.id == ShipmentCargoItem.operational_shipment_id)
        .where(OperationalShipment.organization_id == organization_id)
        .order_by(OperationalShipment.public_id, ShipmentCargoItem.line_number)
    ).all()
    result = []
    for cargo in rows:
        try:
            shipment = _authorized_shipment(cargo, user)
        except OperationalError:
            continue
        if cargo.cargo_owner_customer_id is None:
            continue
        owner = db.session.get(Customer, cargo.cargo_owner_customer_id)
        if owner and owner.operational_organization_id == organization_id and owner.status == "active":
            result.append(_cargo_view(cargo, shipment))
    return result


def allocate(*, execution_public_id: str, cargo_public_id: str, allocated_quantity, user: dict) -> ExecutionUnitCargoAllocation:
    """Allocate a known-owner cargo line, enforcing tenant/project isolation."""
    require_permission(user, "execution_unit.update")
    organization_id = organization_for_user(int(user["id"]))
    unit = _unit(execution_public_id, user)
    # The cargo row is the aggregate lock for every allocation of this line.
    # It serializes concurrent writes even when the target execution rows do
    # not exist yet, which a cross-row database constraint cannot express.
    cargo = db.session.scalar(
        select(ShipmentCargoItem)
        .where(ShipmentCargoItem.public_id == cargo_public_id)
        .with_for_update()
    )
    if not unit or not cargo:
        raise OperationalError("NOT_FOUND", "Execution or cargo not found.", 404)
    shipment = _authorized_shipment(cargo, user)
    if not authorize_document_management(user, shipment).allowed:
        raise OperationalError("OWNING_TRANSPORT_EXPERT_REQUIRED", "Only the owning Transport Expert may change Cargo allocation.", 403)
    if cargo.cargo_owner_customer_id is None:
        raise OperationalError("CARGO_OWNER_REQUIRED", "Cargo owner is required for a new shared transport allocation.", 422)
    owner = db.session.get(Customer, cargo.cargo_owner_customer_id)
    if not owner or owner.operational_organization_id != organization_id:
        raise OperationalError("TENANT_SCOPE_VIOLATION", "Cargo owner is outside the active organization.", 403)
    if owner.status != "active":
        raise OperationalError("VALIDATION_FAILED", "Cargo owner must be active.", 422)
    try:
        quantity = Decimal(str(allocated_quantity))
    except (InvalidOperation, TypeError):
        raise OperationalError("VALIDATION_FAILED", "allocated_quantity must be positive.", 422)
    row = db.session.scalar(select(ExecutionUnitCargoAllocation).where(
        ExecutionUnitCargoAllocation.execution_unit_id == unit.id,
        ExecutionUnitCargoAllocation.shipment_cargo_item_id == cargo.id,
        ExecutionUnitCargoAllocation.route_stage_execution_id.is_(None),
        ExecutionUnitCargoAllocation.is_current.is_(True),
    ).with_for_update())
    if not quantity.is_finite() or quantity <= 0 or quantity.as_tuple().exponent < -6 or quantity > Decimal("999999999999.999999"):
        raise OperationalError("INVALID_QUANTITY", "allocated_quantity has invalid sign or precision.", 422)
    before = row.allocated_quantity if row else Decimal("0")
    if row:
        if before == quantity:
            return row
        row.allocated_quantity = quantity
        row.version += 1
        row.updated_by = int(user["id"])
    else:
        row = ExecutionUnitCargoAllocation(
            execution_unit_id=unit.id, shipment_cargo_item_id=cargo.id,
            operational_shipment_id=shipment.id, project_id=shipment.project_id,
            allocated_quantity=quantity, created_by=int(user["id"]), updated_by=int(user["id"]),
        )
        db.session.add(row)
    db.session.flush()
    key = f"legacy-{uuid4()}"
    allocation_history._revision(row, shipment, before, quantity, "LEGACY_RECORD", user, key, allocation_history._payload_hash({"execution": unit.public_id, "cargo": cargo.public_id, "quantity": str(quantity)}), utcnow(), None)
    return row


def release(*, execution_public_id: str, allocation_public_id: str, user: dict) -> None:
    require_permission(user, "execution_unit.update")
    unit = _unit(execution_public_id, user)
    row = db.session.scalar(select(ExecutionUnitCargoAllocation).where(
        ExecutionUnitCargoAllocation.public_id == allocation_public_id,
        ExecutionUnitCargoAllocation.execution_unit_id == unit.id,
        ExecutionUnitCargoAllocation.route_stage_execution_id.is_(None),
        ExecutionUnitCargoAllocation.is_current.is_(True),
    ))
    if not row:
        raise OperationalError("NOT_FOUND", "Allocation not found.", 404)
    # Re-check source authorization on destructive actions as well.
    cargo = db.session.scalar(select(ShipmentCargoItem).where(ShipmentCargoItem.id == row.shipment_cargo_item_id).with_for_update())
    shipment = _authorized_shipment(cargo, user)
    if not authorize_document_management(user, shipment).allowed:
        raise OperationalError("OWNING_TRANSPORT_EXPERT_REQUIRED", "Only the owning Transport Expert may change Cargo allocation.", 403)
    before = row.allocated_quantity
    row.is_current = False
    row.version += 1
    row.updated_by = int(user["id"])
    db.session.flush()
    key = f"legacy-{uuid4()}"
    allocation_history._revision(row, shipment, before, Decimal("0"), "LEGACY_RELEASE", user, key, allocation_history._payload_hash({"allocation": row.public_id, "action": "release"}), utcnow(), None)


def allocations(*, execution_public_id: str, user: dict) -> dict:
    require_permission(user, "execution_unit.read")
    unit = _unit(execution_public_id, user)
    rows = db.session.scalars(select(ExecutionUnitCargoAllocation).where(
        ExecutionUnitCargoAllocation.execution_unit_id == unit.id,
        ExecutionUnitCargoAllocation.route_stage_execution_id.is_(None),
        ExecutionUnitCargoAllocation.is_current.is_(True),
    ).order_by(ExecutionUnitCargoAllocation.created_at, ExecutionUnitCargoAllocation.public_id)).all()
    items = []
    visible_owner_ids = set()
    for row in rows:
        cargo = db.session.get(ShipmentCargoItem, row.shipment_cargo_item_id)
        try:
            shipment = _authorized_shipment(cargo, user)
        except OperationalError:
            # A list must never disclose an inaccessible allocation.
            continue
        if cargo.cargo_owner_customer_id is not None:
            visible_owner_ids.add(cargo.cargo_owner_customer_id)
        # Keep the allocation identity authoritative on this collection.  The
        # cargo projection also has a ``public_id``; merging it last silently
        # replaced the allocation ID and made the UI's release action target
        # a Cargo ID (and therefore return 404).
        items.append({**_cargo_view(cargo, shipment), "public_id": row.public_id, "allocated_quantity": str(row.allocated_quantity)})
    if len(items) <= 1:
        visible_classification = "single_cargo"
    elif any(item["cargo_owner"] is None for item in items):
        visible_classification = "multi_cargo_owner_unknown"
    else:
        visible_classification = "multi_customer_groupage" if len(visible_owner_ids) > 1 else "multi_cargo_same_owner"
    return {"allocations": items, "summary": {
        "cargo_count": len(items), "cargo_owner_count": len(visible_owner_ids),
        "source_shipment_count": len({item["shipment_public_id"] for item in items}),
        "uom_distribution": sorted({item["uom"]["code"] for item in items}),
        # Derive only from rows admitted to this response.  A restricted
        # Expert must not infer another project's allocation from a count or
        # groupage label.
        "classification": visible_classification,
    }}


def active_customers(*, execution_public_id: str, user: dict) -> list[dict]:
    require_permission(user, "execution_unit.update")
    organization_id = organization_for_user(int(user["id"]))
    _unit(execution_public_id, user)
    rows = db.session.scalars(select(Customer).join(CustomerRoleAssignment).where(
        Customer.operational_organization_id == organization_id, Customer.status == "active",
        CustomerRoleAssignment.operational_organization_id == organization_id,
        CustomerRoleAssignment.role_code == "CARRIER", CustomerRoleAssignment.is_active.is_(True),
    ).order_by(Customer.company_name, Customer.last_name, Customer.first_name)).all()
    # Customer has no public UUID in this baseline.  This is an explicitly
    # tenant-scoped selector for the carrier command, not a CRM discovery API.
    return [{"id": row.id, "label": _customer_view(row)["public_label"]} for row in rows]


def assign_carrier(*, execution_public_id: str, carrier_customer_id: int | None, user: dict) -> ExecutionUnit:
    """Assign one canonical CRM party as the actual execution carrier."""
    require_permission(user, "execution_unit.update")
    organization_id = organization_for_user(int(user["id"]))
    unit = _unit(execution_public_id, user)
    if carrier_customer_id is None:
        unit.carrier_customer_id = None
        return unit
    carrier = db.session.get(Customer, carrier_customer_id)
    eligible = db.session.scalar(select(CustomerRoleAssignment).where(
        CustomerRoleAssignment.customer_id == carrier_customer_id,
        CustomerRoleAssignment.operational_organization_id == organization_id,
        CustomerRoleAssignment.role_code == "CARRIER", CustomerRoleAssignment.is_active.is_(True),
    ))
    if not carrier or carrier.operational_organization_id != organization_id:
        raise OperationalError("TENANT_SCOPE_VIOLATION", "Carrier is outside the active organization.", 403)
    if carrier.status != "active":
        raise OperationalError("VALIDATION_FAILED", "Carrier must be active.", 422)
    if not eligible:
        raise OperationalError("VALIDATION_FAILED", "Customer is not eligible to act as Carrier.", 422)
    unit.carrier_customer_id = carrier.id
    return unit


def classification(execution_unit_id: int) -> str:
    """Derived groupage classification; unknown never becomes same-owner."""
    rows = db.session.execute(select(ShipmentCargoItem.id, ShipmentCargoItem.cargo_owner_customer_id).join(ExecutionUnitCargoAllocation, ExecutionUnitCargoAllocation.shipment_cargo_item_id == ShipmentCargoItem.id).where(
        ExecutionUnitCargoAllocation.execution_unit_id == execution_unit_id,
        ExecutionUnitCargoAllocation.is_current.is_(True),
        or_(ExecutionUnitCargoAllocation.dimension == "ACTUAL", ExecutionUnitCargoAllocation.dimension.is_(None)),
    ).distinct()).all()
    if len(rows) <= 1:
        return "single_cargo"
    owners = [owner for _, owner in rows]
    if any(owner is None for owner in owners):
        return "multi_cargo_owner_unknown"
    return "multi_customer_groupage" if len(set(owners)) > 1 else "multi_cargo_same_owner"
