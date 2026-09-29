"""Governed repair for the known pre-fix Request-to-Shipment Cargo defect.

This module is intentionally not wired to HTTP or ordinary Product roles.  It
repairs one opaque Shipment identity after a read-only plan has been reviewed.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from backend.cargo_models import (
    CargoAllocationTransfer,
    ExecutionUnitCargoAllocation,
    ShipmentCargoItem,
    ShipmentCargoTransportAllocation,
)
from backend.delivery_models import CargoDelivery
from backend.extensions import db
from backend.models import (
    Customer,
    ExpertQuote,
    ExpertUser,
    Province,
    RequestCargoItem,
    ShipmentRequest,
)
from backend.operational_models import (
    ExecutionUnit,
    OperationalAudit,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOrganization,
    OperationalOutbox,
    OperationalShipment,
    RouteCargoDestination,
    RouteLeg,
    RoutePlan,
    RouteStageExecution,
)
from backend.reported_fact_models import (
    OperationalEventCargoImpact,
    OperationalEventReportContext,
)
from backend.services.admin_authorization_service import PLATFORM_ADMIN, effective_authority


REPAIR_TYPE = "REQUEST_TO_SHIPMENT_CREATION_CONTINUITY"
REPAIR_REASON = "KNOWN_REQUEST_TO_SHIPMENT_CREATION_CONTINUITY_DEFECT"
REPAIR_ACTION = "shipment_cargo.creation_continuity_repaired"
IDEMPOTENCY_OPERATION = "cargo_continuity_repair"
IDEMPOTENCY_KEY = "known-request-to-shipment-creation-defect-v1"


class CargoContinuityRepairError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _result(shipment_public_id: str) -> dict[str, Any]:
    return {
        "repair_type": REPAIR_TYPE,
        "reason": REPAIR_REASON,
        "shipment_public_id": shipment_public_id,
        "eligibility": "YES",
        "state": "MISSING_CONTINUITY",
        "checks": [],
        "conflicts": [],
        "proposed": {},
    }


def _fail(result: dict[str, Any], code: str, message: str) -> None:
    result["eligibility"] = "NO"
    item = {"code": code, "message": message}
    if item not in result["conflicts"]:
        result["conflicts"].append(item)
    result["checks"].append({"code": code, "result": "FAIL", "message": message})


def _pass(result: dict[str, Any], code: str, message: str) -> None:
    result["checks"].append({"code": code, "result": "PASS", "message": message})


def _rows(statement, *, lock: bool, lock_of=None):
    if lock:
        statement = statement.with_for_update(of=lock_of) if lock_of else statement.with_for_update()
    return db.session.scalars(statement).all()


def _one(statement, *, lock: bool):
    if lock:
        statement = statement.with_for_update()
    return db.session.scalar(statement)


def _maintenance_actor(
    username: str, *, lock: bool
) -> tuple[ExpertUser, OperationalMembership]:
    identity = str(username or "").strip()
    if not identity:
        raise CargoContinuityRepairError(
            "MAINTENANCE_ACTOR_REQUIRED", "An explicit maintenance actor is required.", 403
        )
    actor_query = select(ExpertUser).where(ExpertUser.username == identity)
    actor = db.session.scalar(actor_query.with_for_update() if lock else actor_query)
    if actor is None or not actor.is_active or effective_authority(actor) != PLATFORM_ADMIN:
        raise CargoContinuityRepairError(
            "MAINTENANCE_AUTHORITY_REQUIRED",
            "An active System Admin is required for Cargo continuity repair.",
            403,
        )
    membership_query = (
        select(OperationalMembership)
        .join(
            OperationalOrganization,
            OperationalOrganization.id == OperationalMembership.organization_id,
        )
        .where(
            OperationalMembership.user_id == actor.id,
            OperationalMembership.is_active.is_(True),
            OperationalOrganization.is_active.is_(True),
        )
    )
    if lock:
        membership_query = membership_query.with_for_update(of=OperationalMembership)
    memberships = db.session.scalars(membership_query).all()
    if len(memberships) != 1:
        raise CargoContinuityRepairError(
            "MAINTENANCE_TENANT_REQUIRED",
            "The System Admin must have exactly one active organization membership for this maintenance command.",
            403,
        )
    organization_query = select(OperationalOrganization).where(
        OperationalOrganization.id == memberships[0].organization_id,
        OperationalOrganization.is_active.is_(True),
    )
    if lock:
        organization_query = organization_query.with_for_update()
    if db.session.scalar(organization_query) is None:
        raise CargoContinuityRepairError(
            "MAINTENANCE_TENANT_REQUIRED",
            "The maintenance tenant must remain active for this command.",
            403,
        )
    return actor, memberships[0]


def _requested_destination(request_row: ShipmentRequest) -> dict[str, Any]:
    if request_row.shipping_type == "domestic":
        province = db.session.get(Province, request_row.dest_province_id)
        return {
            "kind": "domestic",
            "province_id": request_row.dest_province_id,
            "province_name_fa": province.name_fa if province else None,
            "county_id": request_row.dest_county_id,
            "city_id": request_row.dest_city_id,
        }
    return {
        "kind": "international",
        "country_id": request_row.dest_country_id,
        "country": request_row.dest_country,
        "international_city_id": request_row.dest_international_city_id,
        "international_city": request_row.dest_city_international,
        "iran_destination_type": request_row.iran_dest_type,
        "iran_destination_customs_office_id": request_row.iran_dest_customs_office_id,
        "iran_destination_city_id": request_row.iran_dest_city_id,
    }


def _creation_defect_audit(
    cargo: ShipmentCargoItem,
    shipment: OperationalShipment,
    *,
    lock: bool,
) -> OperationalAudit | None:
    audits = _rows(
        select(OperationalAudit).where(
            OperationalAudit.entity_type == "ShipmentCargoItem",
            OperationalAudit.entity_id == cargo.id,
            OperationalAudit.action == "SHIPMENT_CARGO_CREATED",
            OperationalAudit.organization_id == shipment.organization_id,
        ),
        lock=lock,
    )
    if len(audits) != 1:
        return None
    audit = audits[0]
    metadata = audit.metadata_json or {}
    changes = metadata.get("changes") or {}
    required = (
        "source_request_public_id",
        "source_request_cargo_item_public_id",
        "requested_quantity",
    )
    if any(
        (changes.get(field) or {}).get("before") is not None
        or (changes.get(field) or {}).get("after") is not None
        for field in required
    ):
        return None
    if any(field not in changes for field in required):
        return None
    changed_fields = metadata.get("changed_fields")
    if not isinstance(changed_fields, list) or not set(required).issubset(changed_fields):
        return None
    if (
        metadata.get("cargo_public_id") != cargo.public_id
        or metadata.get("shipment_public_id") != shipment.public_id
        or metadata.get("version") != 1
        or audit.actor_user_id != shipment.created_by_user_id
        or cargo.created_by != shipment.created_by_user_id
    ):
        return None
    return audit


def _shipment_creation_evidence(
    shipment: OperationalShipment, quote: ExpertQuote, *, lock: bool
) -> bool:
    audits = _rows(
        select(OperationalAudit).where(
            OperationalAudit.organization_id == shipment.organization_id,
            OperationalAudit.entity_type == "OperationalShipment",
            OperationalAudit.entity_id == shipment.id,
            OperationalAudit.action == "operational_shipment.created",
        ),
        lock=lock,
    )
    ledgers = _rows(
        select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == shipment.organization_id,
            OperationalIdempotency.operation == "create_shipment",
            OperationalIdempotency.resource_type == "accepted_quote",
            OperationalIdempotency.command_resource_id == quote.id,
            OperationalIdempotency.result_resource_id == shipment.id,
        ),
        lock=lock,
    )
    if len(audits) != 1 or len(ledgers) != 1:
        return False
    metadata = audits[0].metadata_json or {}
    return (
        audits[0].actor_user_id == shipment.created_by_user_id
        and metadata.get("shipment_public_id") == shipment.public_id
        and metadata.get("source_type") == "accepted_quote"
        and metadata.get("customer_id") == shipment.customer_id
        and len(ledgers[0].request_hash or "") == 64
    )


def _explicit_path(
    plan: RoutePlan, result: dict[str, Any], *, lock: bool
) -> tuple[list[RouteLeg], RouteLeg] | None:
    legs = _rows(
        select(RouteLeg)
        .where(RouteLeg.route_plan_id == plan.id)
        .order_by(RouteLeg.sequence_number, RouteLeg.id),
        lock=lock,
    )
    if not legs:
        _fail(result, "ROUTE_PLAN_EMPTY", "The exact RoutePlan has no RouteLeg.")
        return None
    if len(legs) == 1:
        if legs[0].parent_route_leg_id is not None:
            _fail(result, "ROUTE_PATH_INVALID", "The one-leg RoutePlan must be a root path.")
            return None
        return legs, legs[0]
    if not any(leg.parent_route_leg_id is not None for leg in legs):
        _fail(
            result,
            "ROUTE_PATH_NOT_EXPLICIT",
            "A multi-leg historical route without explicit parent path cannot prove the Cargo terminal path.",
        )
        return None
    by_id = {leg.id: leg for leg in legs}
    if any(
        leg.parent_route_leg_id is not None and leg.parent_route_leg_id not in by_id
        for leg in legs
    ):
        _fail(result, "ROUTE_PATH_INVALID", "The RoutePlan contains an invalid parent path.")
        return None
    children = {leg.parent_route_leg_id for leg in legs if leg.parent_route_leg_id is not None}
    leaves = [leg for leg in legs if leg.id not in children]
    if len(leaves) != 1:
        _fail(
            result,
            "ROUTE_TERMINAL_AMBIGUOUS",
            "The RoutePlan has more than one possible terminal destination.",
        )
        return None
    reverse_path: list[RouteLeg] = []
    seen: set[int] = set()
    current = leaves[0]
    while current:
        if current.id in seen:
            _fail(result, "ROUTE_PATH_INVALID", "The RoutePlan path contains a cycle.")
            return None
        seen.add(current.id)
        reverse_path.append(current)
        current = by_id.get(current.parent_route_leg_id)
    path = list(reversed(reverse_path))
    if len(path) != len(legs):
        _fail(
            result,
            "ROUTE_PATH_AMBIGUOUS",
            "The RoutePlan contains legs outside the one provable Cargo path.",
        )
        return None
    for previous, following in zip(path, path[1:]):
        if following.sequence_number <= previous.sequence_number:
            _fail(
                result,
                "ROUTE_PATH_INVALID",
                "The RoutePlan parent path is not sequence-ordered.",
            )
            return None
        if (
            previous.destination_location_id,
            previous.destination_logistics_point_id,
        ) != (
            following.origin_location_id,
            following.origin_logistics_point_id,
        ):
            _fail(
                result,
                "ROUTE_PATH_DISCONTINUOUS",
                "The one terminal branch is not location-continuous.",
            )
            return None
    return path, leaves[0]


def _fingerprint(proposed: dict[str, Any]) -> str:
    payload = json.dumps(proposed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _existing_repair_audits(
    cargo_id: int, organization_id: int, *, lock: bool
) -> list[OperationalAudit]:
    return _rows(
        select(OperationalAudit).where(
            OperationalAudit.entity_type == "ShipmentCargoItem",
            OperationalAudit.entity_id == cargo_id,
            OperationalAudit.action == REPAIR_ACTION,
            OperationalAudit.organization_id == organization_id,
        ),
        lock=lock,
    )


def _evaluate(
    shipment_public_id: str,
    actor_username: str,
    expected_request_tracking_code: str,
    expected_cargo_public_id: str,
    expected_source_request_cargo_public_id: str,
    expected_route_plan_id: int,
    expected_terminal_route_leg_id: int,
    *,
    lock: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = _result(str(shipment_public_id))
    actor, membership = _maintenance_actor(actor_username, lock=lock)
    shipment = _one(
        select(OperationalShipment).where(
            OperationalShipment.public_id == str(shipment_public_id)
        ),
        lock=lock,
    )
    if shipment is None:
        raise CargoContinuityRepairError(
            "RESOURCE_NOT_FOUND", "Operational Shipment was not found.", 404
        )
    if membership.organization_id != shipment.organization_id:
        raise CargoContinuityRepairError(
            "MAINTENANCE_TENANT_MISMATCH",
            "The maintenance actor membership does not match the Shipment tenant.",
            403,
        )
    _pass(result, "MAINTENANCE_AUTHORITY", "System maintenance authority and tenant are exact.")

    if shipment.source_type != "accepted_quote":
        _fail(result, "DIRECT_SHIPMENT_NOT_ELIGIBLE", "A direct Shipment cannot receive fabricated Request lineage.")
        return result, {"actor": actor, "shipment": shipment}
    request_row = _one(
        select(ShipmentRequest).where(ShipmentRequest.id == shipment.shipment_request_id),
        lock=lock,
    )
    quote = _one(select(ExpertQuote).where(ExpertQuote.id == shipment.accepted_quote_id), lock=lock)
    if request_row is None or quote is None:
        _fail(result, "COMMERCIAL_LINEAGE_MISSING", "The Shipment Request or accepted Quote is missing.")
        return result, {"actor": actor, "shipment": shipment}
    customer = (
        _one(select(Customer).where(Customer.id == request_row.customer_id), lock=lock)
        if request_row.customer_id is not None
        else None
    )
    expected_request = str(expected_request_tracking_code or "").strip()
    if not expected_request:
        _fail(result, "EXPECTED_SOURCE_REQUEST_REQUIRED", "The exact expected source Request tracking code is required.")
    elif request_row.tracking_code != expected_request:
        _fail(
            result,
            "EXPECTED_SOURCE_REQUEST_MISMATCH",
            "The stored source Request identity does not exactly match the operator-reviewed Request identity.",
        )
    else:
        _pass(result, "EXPECTED_SOURCE_REQUEST_MATCH", "The stored source Request exactly matches the reviewed Request identity.")
    commercial_exact = (
        quote.shipment_request_id == request_row.id
        and quote.customer_response == "accepted"
        and quote.operational_organization_id == shipment.organization_id
        and request_row.operational_organization_id == shipment.organization_id
        and request_row.ownership_scope == "TENANT"
        and request_row.customer_id is not None
        and shipment.customer_id == request_row.customer_id
        and customer is not None
        and customer.ownership_scope == "TENANT"
        and customer.operational_organization_id == shipment.organization_id
    )
    if not commercial_exact:
        _fail(result, "COMMERCIAL_LINEAGE_CONFLICT", "Accepted Quote, Request, Customer, and tenant lineage do not match exactly.")
    else:
        _pass(result, "COMMERCIAL_LINEAGE_EXACT", "Accepted Quote and source Request lineage are exact.")

    request_cargo_rows = _rows(
        select(RequestCargoItem)
        .where(RequestCargoItem.shipment_request_id == request_row.id)
        .order_by(RequestCargoItem.position, RequestCargoItem.id),
        lock=lock,
    )
    cargo_rows = _rows(
        select(ShipmentCargoItem)
        .where(ShipmentCargoItem.operational_shipment_id == shipment.id)
        .order_by(ShipmentCargoItem.line_number, ShipmentCargoItem.id),
        lock=lock,
    )
    if len(request_cargo_rows) != 1:
        _fail(result, "SOURCE_REQUEST_CARGO_AMBIGUOUS", "Exactly one source Request Cargo must be provable.")
    if len(cargo_rows) != 1:
        _fail(result, "SHIPMENT_CARGO_AMBIGUOUS", "This bounded repair requires exactly one affected Shipment Cargo.")
    if len(request_cargo_rows) != 1 or len(cargo_rows) != 1:
        return result, {"actor": actor, "shipment": shipment, "request": request_row, "quote": quote}
    source = request_cargo_rows[0]
    cargo = cargo_rows[0]
    if (
        cargo.public_id != str(expected_cargo_public_id or "").strip()
        or source.public_id
        != str(expected_source_request_cargo_public_id or "").strip()
    ):
        _fail(
            result,
            "EXPECTED_CARGO_BINDING_MISMATCH",
            "The exact Shipment Cargo or source Request Cargo does not match the operator-reviewed identities.",
        )
    else:
        _pass(
            result,
            "EXPECTED_CARGO_BINDING_MATCH",
            "Shipment Cargo and source Request Cargo match the reviewed opaque identities.",
        )
    if source.quantity is None or source.uom_id is None:
        _fail(result, "SOURCE_REQUESTED_QUANTITY_MISSING", "The source Request Cargo lacks requested quantity or UOM.")
    else:
        _pass(result, "SOURCE_REQUESTED_QUANTITY_PRESENT", "Source requested quantity and UOM are present.")
    if source.cargo_type_id is None or source.cargo_type_id != cargo.cargo_type_id or source.uom_id != cargo.uom_id:
        _fail(result, "SOURCE_CARGO_FACT_CONFLICT", "Source Cargo Type/UOM does not match the historical Shipment Cargo snapshot.")
    elif cargo.uom_code_snapshot != source.uom.immutable_code or cargo.uom_symbol_snapshot != source.uom.symbol:
        _fail(result, "SOURCE_UOM_SNAPSHOT_CONFLICT", "The historical Shipment Cargo UOM snapshot does not match the source Request Cargo.")
    else:
        _pass(result, "SOURCE_CARGO_FACTS_EXACT", "Source Cargo Type and UOM match the immutable Shipment Cargo snapshot.")
    if cargo.cargo_owner_customer_id != request_row.customer_id:
        _fail(result, "CARGO_CUSTOMER_CONFLICT", "Cargo Customer does not match the accepted Request Customer.")

    creation_audit = _creation_defect_audit(cargo, shipment, lock=lock)
    creation_boundary = _shipment_creation_evidence(shipment, quote, lock=lock)
    if creation_audit is None or not creation_boundary:
        _fail(result, "KNOWN_DEFECT_SIGNATURE_NOT_PROVEN", "Immutable Cargo creation history does not prove the known missing-continuity defect.")
    else:
        _pass(result, "KNOWN_DEFECT_SIGNATURE_PROVEN", "Cargo creation history proves the three continuity facts were omitted.")

    plans = _rows(
        select(RoutePlan)
        .where(RoutePlan.operational_shipment_id == shipment.id)
        .order_by(RoutePlan.revision_number, RoutePlan.id),
        lock=lock,
    )
    if len(plans) != 1:
        _fail(result, "ROUTE_PLAN_REVISION_AMBIGUOUS", "Exactly one original RoutePlan revision must be provable.")
        return result, {
            "actor": actor,
            "shipment": shipment,
            "request": request_row,
            "quote": quote,
            "source": source,
            "cargo": cargo,
        }
    plan = plans[0]
    if plan.id != expected_route_plan_id:
        _fail(
            result,
            "EXPECTED_ROUTE_PLAN_MISMATCH",
            "The exact RoutePlan does not match the operator-reviewed creation plan identity.",
        )
    if not (
        plan.revision_number == 1
        and plan.created_from_plan_id is None
        and plan.is_active
        and plan.status == "active"
        and plan.created_by_user_id == shipment.created_by_user_id
    ):
        _fail(result, "ROUTE_PLAN_CREATION_REVISION_NOT_PROVEN", "The exact active RoutePlan is not the original creation revision.")
    else:
        _pass(result, "ROUTE_PLAN_CREATION_REVISION_PROVEN", "The exact original active RoutePlan revision is proven.")
    path_result = _explicit_path(plan, result, lock=lock)
    if path_result is None:
        return result, {
            "actor": actor,
            "shipment": shipment,
            "request": request_row,
            "quote": quote,
            "source": source,
            "cargo": cargo,
            "plan": plan,
        }
    path, terminal = path_result
    if terminal.id != expected_terminal_route_leg_id:
        _fail(
            result,
            "EXPECTED_TERMINAL_LEG_MISMATCH",
            "The terminal RouteLeg does not match the operator-reviewed creation path identity.",
        )
    _pass(result, "UNIQUE_ROUTE_DESTINATION", "Exactly one persisted terminal Cargo path is provable.")

    mappings = _rows(
        select(RouteCargoDestination).where(
            RouteCargoDestination.shipment_cargo_item_id == cargo.id
        ),
        lock=lock,
    )
    repair_audits = _existing_repair_audits(
        cargo.id, shipment.organization_id, lock=lock
    )
    proposed = {
        "shipment_public_id": shipment.public_id,
        "cargo_public_id": cargo.public_id,
        "source_request_public_id": request_row.public_id,
        "source_request_tracking_code": request_row.tracking_code,
        "source_request_cargo_item_public_id": source.public_id,
        "requested_quantity": str(source.quantity) if source.quantity is not None else None,
        "requested_uom": {
            "code": source.uom.immutable_code if source.uom else None,
            "symbol": source.uom.symbol if source.uom else None,
        },
        "route_plan_id": plan.id,
        "route_plan_revision": plan.revision_number,
        "terminal_route_leg_id": terminal.id,
        "requested_destination": _requested_destination(request_row),
        "operational_planned_destination": terminal.destination_snapshot,
        "facts_to_add": [
            "source_shipment_request_id",
            "source_request_cargo_item_id",
            "requested_quantity",
            "route_cargo_destination",
            "repair_audit",
        ],
    }
    fingerprint_basis = {
        key: value for key, value in proposed.items() if key != "facts_to_add"
    }
    fingerprint_basis["repair_fact_set"] = list(proposed["facts_to_add"])
    fingerprint = _fingerprint(fingerprint_basis)
    result["proposed"] = proposed
    result["fingerprint_basis"] = fingerprint_basis
    result["plan_fingerprint"] = fingerprint

    repair_ledgers = _rows(
        select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == shipment.organization_id,
            OperationalIdempotency.operation == IDEMPOTENCY_OPERATION,
            OperationalIdempotency.resource_type == "operational_shipment",
            OperationalIdempotency.command_resource_id == shipment.id,
            OperationalIdempotency.idempotency_key == IDEMPOTENCY_KEY,
        ),
        lock=lock,
    )
    repair_outboxes = _rows(
        select(OperationalOutbox).where(
            OperationalOutbox.organization_id == shipment.organization_id,
            OperationalOutbox.event_type == "cargo_continuity.repaired",
            OperationalOutbox.aggregate_type == "ShipmentCargoItem",
            OperationalOutbox.aggregate_id == cargo.id,
        ),
        lock=lock,
    )
    repair_artifact_present = bool(
        repair_audits or repair_ledgers or repair_outboxes
    )
    if repair_artifact_present:
        audit = repair_audits[0] if len(repair_audits) == 1 else None
        ledger = repair_ledgers[0] if len(repair_ledgers) == 1 else None
        outbox = repair_outboxes[0] if len(repair_outboxes) == 1 else None
        metadata = (audit.metadata_json or {}) if audit else {}
        payload = (outbox.payload or {}) if outbox else {}
        audit_actor = (
            _one(
                select(ExpertUser).where(ExpertUser.id == audit.actor_user_id),
                lock=lock,
            )
            if audit
            else None
        )
        ledger_response = (ledger.response_json or {}) if ledger else {}
        expected_missing_facts = [
            "source_shipment_request_id",
            "source_request_cargo_item_id",
            "requested_quantity",
            "route_cargo_destination",
        ]
        exact_mapping = (
            len(mappings) == 1
            and mappings[0].operational_shipment_id == shipment.id
            and mappings[0].route_plan_id == plan.id
            and mappings[0].shipment_cargo_item_id == cargo.id
            and mappings[0].destination_route_leg_id == terminal.id
        )
        exact_state = (
            audit is not None
            and ledger is not None
            and outbox is not None
            and cargo.source_shipment_request_id == request_row.id
            and cargo.source_request_cargo_item_id == source.id
            and cargo.requested_quantity == source.quantity
            and exact_mapping
            and metadata.get("repair_type") == REPAIR_TYPE
            and metadata.get("reason") == REPAIR_REASON
            and metadata.get("shipment_public_id") == shipment.public_id
            and metadata.get("cargo_public_id") == cargo.public_id
            and metadata.get("source_request_public_id") == request_row.public_id
            and metadata.get("source_request_cargo_item_public_id") == source.public_id
            and metadata.get("accepted_quote_id") == shipment.accepted_quote_id
            and metadata.get("route_plan_id") == plan.id
            and metadata.get("route_plan_revision") == plan.revision_number
            and metadata.get("terminal_route_leg_id") == terminal.id
            and metadata.get("requested_destination")
            == proposed["requested_destination"]
            and metadata.get("operational_planned_destination")
            == proposed["operational_planned_destination"]
            and metadata.get("before_missing_facts") == expected_missing_facts
            and metadata.get("facts_added") == expected_missing_facts
            and metadata.get("requested_quantity") == str(source.quantity)
            and metadata.get("requested_uom_code_snapshot")
            == cargo.uom_code_snapshot
            and metadata.get("requested_uom_symbol_snapshot")
            == cargo.uom_symbol_snapshot
            and metadata.get("preserved_timestamp")
            == (cargo.updated_at.isoformat() if cargo.updated_at else None)
            and bool(metadata.get("approval_reference"))
            and audit_actor is not None
            and metadata.get("actor_username") == audit_actor.username
            and metadata.get("operator") == audit_actor.username
            and metadata.get("plan_fingerprint") == fingerprint
            and ledger.request_hash == fingerprint
            and ledger.result_resource_id == cargo.id
            and ledger_response.get("shipment_public_id") == shipment.public_id
            and ledger_response.get("plan_fingerprint") == fingerprint
            and ledger_response.get("repair_type") == REPAIR_TYPE
            and ledger_response.get("apply_result") == "CHANGED"
            and payload.get("shipment_public_id") == shipment.public_id
            and payload.get("cargo_public_id") == cargo.public_id
            and payload.get("repair_type") == REPAIR_TYPE
            and payload.get("reason") == REPAIR_REASON
            and payload.get("plan_fingerprint") == fingerprint
        )
        if exact_state:
            result["state"] = "ALREADY_REPAIRED"
            result["proposed"]["facts_to_add"] = []
            _pass(result, "IDEMPOTENT_REPLAY", "The exact governed repair is already present; replay is unchanged.")
        else:
            _fail(result, "REPAIR_STATE_DRIFT", "Existing repair history conflicts with current Cargo or route state.")
    else:
        if mappings:
            _fail(result, "EXISTING_CARGO_DESTINATION_CONFLICT", "Cargo already has a route destination without this governed repair history.")
        if any(
            value is not None
            for value in (
                cargo.source_shipment_request_id,
                cargo.source_request_cargo_item_id,
                cargo.requested_quantity,
            )
        ):
            _fail(result, "PARTIAL_CONTINUITY_CONFLICT", "Cargo lineage or requested quantity is already partially populated.")
        else:
            _pass(result, "CONTINUITY_FACTS_MISSING", "All and only the governed continuity facts are currently missing.")

    if cargo.actual_quantity is not None and source.quantity is not None and cargo.actual_quantity != source.quantity:
        _fail(result, "ACTUAL_QUANTITY_CONFLICT", "Actual quantity contradicts the proposed requested quantity continuity.")

    path_ids = {leg.id for leg in path}
    stages = _rows(
        select(RouteStageExecution).where(
            RouteStageExecution.operational_shipment_id == shipment.id
        ),
        lock=lock,
    )
    execution_ids: list[str] = []
    for stage in stages:
        unit = _one(select(ExecutionUnit).where(ExecutionUnit.id == stage.execution_unit_id), lock=lock)
        if (
            stage.organization_id != shipment.organization_id
            or stage.route_plan_id != plan.id
            or stage.route_leg_id not in path_ids
            or unit is None
            or unit.organization_id != shipment.organization_id
            or unit.operational_shipment_id not in {None, shipment.id}
        ):
            _fail(result, "EXECUTION_ROUTE_CONFLICT", "Existing Execution does not belong to the same Shipment, RoutePlan revision, and repaired Cargo path.")
            break
        execution_ids.append(unit.public_id)
    owned_execution_units = _rows(
        select(ExecutionUnit).where(
            ExecutionUnit.operational_shipment_id == shipment.id
        ),
        lock=lock,
    )
    staged_unit_ids = {stage.execution_unit_id for stage in stages}
    if any(unit.id not in staged_unit_ids for unit in owned_execution_units):
        _fail(
            result,
            "EXECUTION_ROUTE_CONFLICT",
            "A Shipment-owned Execution has no exact RouteStageExecution on the repaired path.",
        )
    if not any(check["code"] == "EXECUTION_ROUTE_CONFLICT" for check in result["checks"]):
        _pass(result, "EXISTING_EXECUTION_PRESERVED", "Existing Execution is absent or belongs to the exact repaired path and will not be changed.")
    result["existing_execution_public_ids"] = sorted(set(execution_ids))

    legacy_allocations = _rows(
        select(ShipmentCargoTransportAllocation).where(
            ShipmentCargoTransportAllocation.shipment_cargo_item_id == cargo.id
        ),
        lock=lock,
    )
    canonical_allocations = _rows(
        select(ExecutionUnitCargoAllocation).where(
            ExecutionUnitCargoAllocation.shipment_cargo_item_id == cargo.id
        ),
        lock=lock,
    )
    if legacy_allocations:
        _fail(result, "LEGACY_ALLOCATION_AMBIGUOUS", "Legacy Cargo allocation has no exact route-stage proof.")
    for allocation in canonical_allocations:
        stage = (
            _one(
                select(RouteStageExecution).where(
                    RouteStageExecution.id == allocation.route_stage_execution_id
                ),
                lock=lock,
            )
            if allocation.route_stage_execution_id is not None
            else None
        )
        unit = (
            _one(
                select(ExecutionUnit).where(
                    ExecutionUnit.id == allocation.execution_unit_id
                ),
                lock=lock,
            )
            if allocation.execution_unit_id is not None
            else None
        )
        if (
            allocation.operational_shipment_id != shipment.id
            or allocation.project_id != shipment.project_id
            or stage is None
            or stage.organization_id != shipment.organization_id
            or stage.operational_shipment_id != shipment.id
            or stage.route_plan_id != plan.id
            or stage.route_leg_id not in path_ids
            or allocation.execution_unit_id != stage.execution_unit_id
            or unit is None
            or unit.organization_id != shipment.organization_id
            or unit.operational_shipment_id not in {None, shipment.id}
        ):
            _fail(result, "ALLOCATION_ROUTE_CONFLICT", "Cargo allocation is not proven on the proposed repaired path.")
            break
    transfers = _rows(
        select(CargoAllocationTransfer).where(
            CargoAllocationTransfer.shipment_cargo_item_id == cargo.id
        ),
        lock=lock,
    )
    if transfers:
        _fail(result, "ALLOCATION_TRANSFER_AMBIGUOUS", "Existing Cargo transfer history prevents a creation-continuity repair.")
    deliveries = _rows(
        select(CargoDelivery).where(CargoDelivery.cargo_item_id == cargo.id), lock=lock
    )
    if deliveries:
        _fail(result, "DELIVERY_FACT_CONFLICT", "Existing delivery facts prevent a creation-continuity repair.")
    cargo_reports = _rows(
        select(OperationalEventReportContext).where(
            OperationalEventReportContext.cargo_item_id == cargo.id
        ),
        lock=lock,
        lock_of=OperationalEventReportContext,
    )
    cargo_impacts = _rows(
        select(OperationalEventCargoImpact).where(
            OperationalEventCargoImpact.cargo_item_id == cargo.id
        ),
        lock=lock,
        lock_of=OperationalEventCargoImpact,
    )
    if cargo_reports or cargo_impacts:
        _fail(result, "DOWNSTREAM_CARGO_FACT_CONFLICT", "Cargo-scoped reported facts prevent an unambiguous creation-continuity repair.")
    if not any(
        check["code"]
        in {
            "LEGACY_ALLOCATION_AMBIGUOUS",
            "ALLOCATION_ROUTE_CONFLICT",
            "ALLOCATION_TRANSFER_AMBIGUOUS",
            "DELIVERY_FACT_CONFLICT",
            "DOWNSTREAM_CARGO_FACT_CONFLICT",
        }
        for check in result["checks"]
    ):
        _pass(result, "NO_DOWNSTREAM_CONFLICT", "No allocation, transfer, delivery, or Cargo-report fact contradicts the repair.")

    context = {
        "actor": actor,
        "membership": membership,
        "shipment": shipment,
        "request": request_row,
        "quote": quote,
        "source": source,
        "cargo": cargo,
        "plan": plan,
        "path": path,
        "terminal": terminal,
        "mappings": mappings,
        "repair_audits": repair_audits,
        "repair_ledgers": repair_ledgers,
        "repair_outboxes": repair_outboxes,
        "creation_audit": creation_audit,
    }
    return result, context


def plan_repair(
    shipment_public_id: str,
    actor_username: str,
    expected_request_tracking_code: str,
    expected_cargo_public_id: str,
    expected_source_request_cargo_public_id: str,
    expected_route_plan_id: int,
    expected_terminal_route_leg_id: int,
) -> dict[str, Any]:
    plan, _context = _evaluate(
        shipment_public_id,
        actor_username,
        expected_request_tracking_code,
        expected_cargo_public_id,
        expected_source_request_cargo_public_id,
        expected_route_plan_id,
        expected_terminal_route_leg_id,
        lock=False,
    )
    return plan


def apply_repair(
    shipment_public_id: str,
    actor_username: str,
    *,
    approval_reference: str,
    expected_plan_fingerprint: str,
    operator: str,
    expected_request_tracking_code: str,
    expected_cargo_public_id: str,
    expected_source_request_cargo_public_id: str,
    expected_route_plan_id: int,
    expected_terminal_route_leg_id: int,
) -> dict[str, Any]:
    approval = str(approval_reference or "").strip()
    named_operator = str(operator or "").strip()
    expected = str(expected_plan_fingerprint or "").strip()
    if not approval or len(approval) > 200:
        raise CargoContinuityRepairError(
            "APPROVAL_REFERENCE_REQUIRED", "A bounded approval reference is required.", 422
        )
    if not named_operator or len(named_operator) > 160:
        raise CargoContinuityRepairError(
            "OPERATOR_REQUIRED", "A bounded named operator is required.", 422
        )
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected.lower()):
        raise CargoContinuityRepairError(
            "PLAN_FINGERPRINT_REQUIRED", "The reviewed 64-character plan fingerprint is required.", 422
        )
    try:
        plan, context = _evaluate(
            shipment_public_id,
            actor_username,
            expected_request_tracking_code,
            expected_cargo_public_id,
            expected_source_request_cargo_public_id,
            expected_route_plan_id,
            expected_terminal_route_leg_id,
            lock=True,
        )
        if plan["eligibility"] != "YES":
            first = plan["conflicts"][0] if plan["conflicts"] else {
                "code": "REPAIR_NOT_ELIGIBLE",
                "message": "The Shipment is not eligible for repair.",
            }
            raise CargoContinuityRepairError(first["code"], first["message"])
        if plan.get("plan_fingerprint") != expected.lower():
            raise CargoContinuityRepairError(
                "REPAIR_PLAN_CHANGED", "The reviewed repair plan no longer matches current authoritative facts."
            )
        actor: ExpertUser = context["actor"]
        if actor.username != named_operator:
            raise CargoContinuityRepairError(
                "OPERATOR_IDENTITY_MISMATCH",
                "The named operator must exactly match the authorized System Admin identity.",
                403,
            )
        if plan["state"] == "ALREADY_REPAIRED":
            db.session.rollback()
            return {**plan, "apply_result": "UNCHANGED"}

        shipment: OperationalShipment = context["shipment"]
        request_row: ShipmentRequest = context["request"]
        source: RequestCargoItem = context["source"]
        cargo: ShipmentCargoItem = context["cargo"]
        route_plan: RoutePlan = context["plan"]
        terminal: RouteLeg = context["terminal"]

        replay = _one(
            select(OperationalIdempotency).where(
                OperationalIdempotency.organization_id == shipment.organization_id,
                OperationalIdempotency.operation == IDEMPOTENCY_OPERATION,
                OperationalIdempotency.resource_type == "operational_shipment",
                OperationalIdempotency.command_resource_id == shipment.id,
                OperationalIdempotency.idempotency_key == IDEMPOTENCY_KEY,
            ),
            lock=True,
        )
        if replay is not None:
            if replay.request_hash != expected.lower():
                raise CargoContinuityRepairError(
                    "REPAIR_IDEMPOTENCY_CONFLICT", "A different repair plan was already recorded for this Shipment."
                )
            response = dict(replay.response_json or plan)
            db.session.rollback()
            return {**response, "apply_result": "UNCHANGED"}

        original_updated_at = cargo.updated_at
        original_version = cargo.version
        changed = db.session.execute(
            update(ShipmentCargoItem)
            .where(
                ShipmentCargoItem.id == cargo.id,
                ShipmentCargoItem.version == original_version,
                ShipmentCargoItem.source_shipment_request_id.is_(None),
                ShipmentCargoItem.source_request_cargo_item_id.is_(None),
                ShipmentCargoItem.requested_quantity.is_(None),
            )
            .values(
                source_shipment_request_id=request_row.id,
                source_request_cargo_item_id=source.id,
                requested_quantity=source.quantity,
                updated_by=actor.id,
                updated_at=original_updated_at,
                version=original_version + 1,
            )
        )
        if changed.rowcount != 1:
            raise CargoContinuityRepairError(
                "REPAIR_CONCURRENT_CHANGE", "Cargo changed after eligibility was evaluated."
            )

        mapping = RouteCargoDestination(
            operational_shipment_id=shipment.id,
            route_plan_id=route_plan.id,
            shipment_cargo_item_id=cargo.id,
            destination_route_leg_id=terminal.id,
            created_by_user_id=actor.id,
        )
        db.session.add(mapping)
        db.session.flush()

        metadata = {
            "repair_type": REPAIR_TYPE,
            "reason": REPAIR_REASON,
            "approval_reference": approval,
            "actor_username": actor.username,
            "operator": named_operator,
            "shipment_public_id": shipment.public_id,
            "cargo_public_id": cargo.public_id,
            "source_request_public_id": request_row.public_id,
            "source_request_cargo_item_public_id": source.public_id,
            "accepted_quote_id": shipment.accepted_quote_id,
            "route_plan_id": route_plan.id,
            "route_plan_revision": route_plan.revision_number,
            "terminal_route_leg_id": terminal.id,
            "requested_destination": plan["proposed"]["requested_destination"],
            "operational_planned_destination": terminal.destination_snapshot,
            "plan_fingerprint": expected.lower(),
            "before_missing_facts": [
                "source_shipment_request_id",
                "source_request_cargo_item_id",
                "requested_quantity",
                "route_cargo_destination",
            ],
            "facts_added": [
                "source_shipment_request_id",
                "source_request_cargo_item_id",
                "requested_quantity",
                "route_cargo_destination",
            ],
            "requested_quantity": str(source.quantity),
            "requested_uom_code_snapshot": cargo.uom_code_snapshot,
            "requested_uom_symbol_snapshot": cargo.uom_symbol_snapshot,
            "preserved_timestamp": original_updated_at.isoformat() if original_updated_at else None,
        }
        db.session.add(
            OperationalAudit(
                organization_id=shipment.organization_id,
                actor_user_id=actor.id,
                action=REPAIR_ACTION,
                entity_type="ShipmentCargoItem",
                entity_id=cargo.id,
                metadata_json=metadata,
            )
        )
        db.session.add(
            OperationalOutbox(
                organization_id=shipment.organization_id,
                event_type="cargo_continuity.repaired",
                aggregate_type="ShipmentCargoItem",
                aggregate_id=cargo.id,
                payload={
                    "shipment_public_id": shipment.public_id,
                    "cargo_public_id": cargo.public_id,
                    "repair_type": REPAIR_TYPE,
                    "reason": REPAIR_REASON,
                    "plan_fingerprint": expected.lower(),
                },
            )
        )
        applied = {**plan, "state": "REPAIRED", "apply_result": "CHANGED"}
        applied["proposed"] = {**plan["proposed"], "facts_to_add": []}
        db.session.add(
            OperationalIdempotency(
                organization_id=shipment.organization_id,
                operation=IDEMPOTENCY_OPERATION,
                resource_type="operational_shipment",
                command_resource_id=shipment.id,
                idempotency_key=IDEMPOTENCY_KEY,
                request_hash=expected.lower(),
                result_resource_id=cargo.id,
                response_json=applied,
            )
        )
        db.session.commit()
        return applied
    except CargoContinuityRepairError:
        db.session.rollback()
        raise
    except IntegrityError as exc:
        db.session.rollback()
        raise CargoContinuityRepairError(
            "REPAIR_CONCURRENT_CONFLICT", "A concurrent repair changed the governed target."
        ) from exc
    except Exception:
        db.session.rollback()
        raise
