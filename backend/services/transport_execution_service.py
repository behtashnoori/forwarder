"""P3-04 route-stage transport execution on the ADR-046 ExecutionUnit SOR."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.extensions import db
from backend.models import (
    Customer,
    CustomerRoleAssignment,
    TransportEquipmentType,
    TransportMeansType,
)
from backend.operational_models import (
    ExecutionTransportEquipmentSnapshot,
    ExecutionTransportRevision,
    ExecutionUnit,
    OperationalAudit,
    OperationalShipment,
    RouteLeg,
    RoutePlan,
    RouteStageExecution,
    utcnow,
)
from backend.organization_reference_catalog_models import (
    OrganizationTransportEquipmentTypeActivation,
    OrganizationTransportMeansTypeActivation,
)
from backend.services.assigned_work_authorization import (
    authorize_document_management,
)
from backend.services.operational_service import (
    OperationalError,
    require_permission,
    scoped_shipment,
)
from backend.services.organization_reference_catalog_service import (
    is_definition_active_for_organization,
)


from backend.services import closure_commands as closure_guard


def _fail(code: str, message: str, status: int = 422):
    raise OperationalError(code, message, status)


def _hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(payload: dict, field: str, limit: int) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        _fail("VALIDATION_FAILED", f"{field} must be text.")
    value = value.strip()
    if len(value) > limit:
        _fail("VALIDATION_FAILED", f"{field} is too long.")
    return value or None


def _effective_at(payload: dict) -> datetime:
    value = payload.get("effective_at")
    if value in (None, ""):
        return utcnow()
    if not isinstance(value, str):
        _fail("VALIDATION_FAILED", "effective_at must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationalError(
            "VALIDATION_FAILED",
            "effective_at must be an ISO-8601 timestamp.",
            422,
        ) from exc
    if parsed.tzinfo is None:
        _fail("VALIDATION_FAILED", "effective_at must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _idempotency(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
        _fail(
            "IDEMPOTENCY_KEY_REQUIRED",
            "A valid Idempotency-Key header is required.",
            400,
        )
    return value.strip()


def _shipment(public_id: str, user: dict, *, mutation_permission: str | None = None):
    shipment = scoped_shipment(public_id, user)
    if mutation_permission:
        require_permission(user, mutation_permission)
        decision = authorize_document_management(user, shipment)
        if not decision.allowed:
            _fail(
                "OWNING_TRANSPORT_EXPERT_REQUIRED",
                "Only the owning Transport Expert can manage transport executions.",
                403,
            )
    return shipment


def _plan(shipment: OperationalShipment, plan_id: int, *, active=False) -> RoutePlan:
    query = select(RoutePlan).where(
        RoutePlan.id == plan_id,
        RoutePlan.operational_shipment_id == shipment.id,
    )
    if active:
        query = query.where(
            RoutePlan.is_active.is_(True), RoutePlan.status == "active"
        )
    row = db.session.scalar(query)
    if row is None:
        _fail("ROUTE_STAGE_NOT_FOUND", "Route stage was not found.", 404)
    return row


def _leg(plan: RoutePlan, leg_id: int) -> RouteLeg:
    row = db.session.scalar(
        select(RouteLeg).where(
            RouteLeg.id == leg_id, RouteLeg.route_plan_id == plan.id
        )
    )
    if row is None:
        _fail("ROUTE_STAGE_NOT_FOUND", "Route stage was not found.", 404)
    return row


def _active_means(public_id: str, organization_id: int) -> TransportMeansType:
    row = db.session.scalar(
        select(TransportMeansType).where(TransportMeansType.public_id == str(public_id))
    )
    if (
        row is None
        or not row.is_active
        or not is_definition_active_for_organization(
            OrganizationTransportMeansTypeActivation,
            "transport_means_type_id",
            row.id,
            organization_id,
        )
    ):
        _fail(
            "ORGANIZATION_REFERENCE_NOT_ACTIVE",
            "نوع وسیله حمل برای این سازمان فعال نیست.",
            409,
        )
    return row


def _active_equipment(public_id: str, organization_id: int):
    row = db.session.scalar(
        select(TransportEquipmentType).where(
            TransportEquipmentType.public_id == str(public_id)
        )
    )
    if (
        row is None
        or not row.is_active
        or not is_definition_active_for_organization(
            OrganizationTransportEquipmentTypeActivation,
            "transport_equipment_type_id",
            row.id,
            organization_id,
        )
    ):
        _fail(
            "ORGANIZATION_REFERENCE_NOT_ACTIVE",
            "نوع واحد یا ظرف حمل برای این سازمان فعال نیست.",
            409,
        )
    return row


def _carrier(value, organization_id: int) -> Customer | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        _fail("VALIDATION_FAILED", "carrier_customer_id must be an integer or null.")
    try:
        customer_id = int(value)
    except (TypeError, ValueError):
        _fail("VALIDATION_FAILED", "carrier_customer_id must be an integer or null.")
    row = db.session.get(Customer, customer_id)
    eligible = db.session.scalar(
        select(CustomerRoleAssignment).where(
            CustomerRoleAssignment.customer_id == customer_id,
            CustomerRoleAssignment.operational_organization_id == organization_id,
            CustomerRoleAssignment.role_code == "CARRIER",
            CustomerRoleAssignment.is_active.is_(True),
        )
    )
    if row is None or row.operational_organization_id != organization_id:
        _fail("TENANT_SCOPE_VIOLATION", "Carrier is outside the active organization.", 403)
    if row.status != "active" or eligible is None:
        _fail("CARRIER_NOT_SELECTABLE", "Carrier is not active for this organization.", 409)
    return row


def _customer_label(row: Customer | None) -> str | None:
    if row is None:
        return None
    return row.company_name or " ".join(
        value for value in (row.first_name, row.last_name) if value
    )


def _equipment(payload: dict, organization_id: int):
    values = payload.get("equipment", [])
    if values is None:
        values = []
    if not isinstance(values, list) or len(values) > 20:
        _fail("VALIDATION_FAILED", "equipment must be a list of at most 20 items.")
    resolved = []
    for index, item in enumerate(values, start=1):
        if not isinstance(item, dict):
            _fail("VALIDATION_FAILED", "Each equipment item must be an object.")
        unknown = set(item) - {"type_public_id", "identifier", "details"}
        if unknown:
            _fail("UNKNOWN_FIELDS", "Unknown equipment fields are not allowed.")
        type_id = item.get("type_public_id")
        if not isinstance(type_id, str) or not type_id:
            _fail("VALIDATION_FAILED", "equipment type_public_id is required.")
        resolved.append(
            (
                index,
                _active_equipment(type_id, organization_id),
                _text(item, "identifier", 160),
                _text(item, "details", 500),
            )
        )
    return resolved


def _configuration(payload: dict, organization_id: int):
    allowed = {
        "transport_means_type_public_id",
        "carrier_customer_id",
        "means_identifier",
        "means_details",
        "driver_name",
        "driver_contact",
        "equipment",
        "effective_at",
        "reason",
        "expected_version",
    }
    if not isinstance(payload, dict):
        _fail("VALIDATION_FAILED", "Request body must be a JSON object.")
    if set(payload) - allowed:
        _fail("UNKNOWN_FIELDS", "Unknown transport execution fields are not allowed.")
    means_id = payload.get("transport_means_type_public_id")
    if not isinstance(means_id, str) or not means_id:
        _fail("VALIDATION_FAILED", "transport_means_type_public_id is required.")
    return {
        "means": _active_means(means_id, organization_id),
        "carrier": _carrier(payload.get("carrier_customer_id"), organization_id),
        "means_identifier": _text(payload, "means_identifier", 160),
        "means_details": _text(payload, "means_details", 500),
        "driver_name": _text(payload, "driver_name", 160),
        "driver_contact": _text(payload, "driver_contact", 160),
        "effective_at": _effective_at(payload),
        "reason": _text(payload, "reason", 500),
        "equipment": _equipment(payload, organization_id),
    }


def _revision(
    unit: ExecutionUnit,
    configuration: dict,
    *,
    revision_number: int,
    actor_id: int,
    idempotency_key: str,
    request_hash: str,
):
    means = configuration["means"]
    carrier = configuration["carrier"]
    row = ExecutionTransportRevision(
        organization_id=unit.organization_id,
        execution_unit_id=unit.id,
        revision_number=revision_number,
        transport_means_type_id=means.id,
        means_type_code_snapshot=means.immutable_code,
        means_type_fa_snapshot=means.fa_name,
        means_type_en_snapshot=means.en_name,
        carrier_customer_id=carrier.id if carrier else None,
        carrier_label_snapshot=_customer_label(carrier),
        means_identifier=configuration["means_identifier"],
        means_details=configuration["means_details"],
        driver_name=configuration["driver_name"],
        driver_contact=configuration["driver_contact"],
        effective_at=configuration["effective_at"],
        recorded_by_user_id=actor_id,
        reason=configuration["reason"],
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    db.session.add(row)
    db.session.flush()
    for sequence, equipment_type, identifier, details in configuration["equipment"]:
        db.session.add(
            ExecutionTransportEquipmentSnapshot(
                transport_revision_id=row.id,
                sequence_number=sequence,
                transport_equipment_type_id=equipment_type.id,
                equipment_type_code_snapshot=equipment_type.immutable_code,
                equipment_type_fa_snapshot=equipment_type.fa_name,
                equipment_type_en_snapshot=equipment_type.en_name,
                identifier=identifier,
                details=details,
            )
        )
    unit.carrier_customer_id = carrier.id if carrier else None
    unit.vehicle_reference = configuration["means_identifier"]
    unit.display_name = means.fa_name
    return row


def active_reference_ids(organization_id: int) -> tuple[set[int], set[int], set[int]]:
    """Return the current selectable intersection without affecting snapshots."""
    means_ids = set(db.session.scalars(
        select(TransportMeansType.id)
        .join(
            OrganizationTransportMeansTypeActivation,
            OrganizationTransportMeansTypeActivation.transport_means_type_id
            == TransportMeansType.id,
        )
        .where(
            TransportMeansType.is_active.is_(True),
            OrganizationTransportMeansTypeActivation.organization_id == organization_id,
            OrganizationTransportMeansTypeActivation.status == "ACTIVE",
        )
    ).all())
    equipment_ids = set(db.session.scalars(
        select(TransportEquipmentType.id)
        .join(
            OrganizationTransportEquipmentTypeActivation,
            OrganizationTransportEquipmentTypeActivation.transport_equipment_type_id
            == TransportEquipmentType.id,
        )
        .where(
            TransportEquipmentType.is_active.is_(True),
            OrganizationTransportEquipmentTypeActivation.organization_id
            == organization_id,
            OrganizationTransportEquipmentTypeActivation.status == "ACTIVE",
        )
    ).all())
    carrier_ids = set(db.session.scalars(
        select(Customer.id)
        .join(CustomerRoleAssignment, CustomerRoleAssignment.customer_id == Customer.id)
        .where(
            Customer.operational_organization_id == organization_id,
            Customer.status == "active",
            CustomerRoleAssignment.operational_organization_id == organization_id,
            CustomerRoleAssignment.role_code == "CARRIER",
            CustomerRoleAssignment.is_active.is_(True),
        )
    ).all())
    return means_ids, equipment_ids, carrier_ids


def revision_projection(
    row: ExecutionTransportRevision | None,
    active_means_ids: set[int] | None = None,
    active_equipment_ids: set[int] | None = None,
    active_carrier_ids: set[int] | None = None,
) -> dict | None:
    if row is None:
        return None
    if (
        active_means_ids is None
        or active_equipment_ids is None
        or active_carrier_ids is None
    ):
        active_means_ids, active_equipment_ids, active_carrier_ids = (
            active_reference_ids(row.organization_id)
        )
    equipment = [
        {
            "sequence": item.sequence_number,
            "type": {
                "public_id": item.transport_equipment_type.public_id,
                "code": item.equipment_type_code_snapshot,
                "fa_name": item.equipment_type_fa_snapshot,
                "en_name": item.equipment_type_en_snapshot,
                "currently_active": item.transport_equipment_type_id
                in active_equipment_ids,
            },
            "identifier": item.identifier,
            "details": item.details,
        }
        for item in row.equipment
    ]
    incomplete = []
    if row.carrier_customer_id is None:
        incomplete.append("CARRIER")
    if row.means_identifier is None:
        incomplete.append("MEANS_IDENTIFIER")
    if any(item["identifier"] is None for item in equipment):
        incomplete.append("EQUIPMENT_IDENTIFIER")
    return {
        "public_id": row.public_id,
        "revision_number": row.revision_number,
        "means": {
            "public_id": row.transport_means_type.public_id,
            "code": row.means_type_code_snapshot,
            "fa_name": row.means_type_fa_snapshot,
            "en_name": row.means_type_en_snapshot,
            "currently_active": row.transport_means_type_id in active_means_ids,
        },
        "carrier": (
            {
                "id": row.carrier_customer_id,
                "label": row.carrier_label_snapshot,
                "currently_active": row.carrier_customer_id in active_carrier_ids,
            }
            if row.carrier_customer_id is not None
            else None
        ),
        "means_identifier": row.means_identifier,
        "means_details": row.means_details,
        "driver": {
            "name": row.driver_name,
            "contact": row.driver_contact,
        },
        "equipment": equipment,
        "effective_at": _iso(row.effective_at),
        "recorded_at": _iso(row.recorded_at),
        "recorded_by_user_id": row.recorded_by_user_id,
        "reason": row.reason,
        "incomplete_fields": incomplete,
    }


def _execution_projection(
    row: RouteStageExecution,
    active_means_ids: set[int],
    active_equipment_ids: set[int],
    active_carrier_ids: set[int],
) -> dict:
    revisions = sorted(
        row.execution_unit.transport_revisions,
        key=lambda item: (item.revision_number, item.id),
    )
    return {
        "public_id": row.public_id,
        "execution_public_id": row.execution_unit.public_id,
        "unit_version": row.execution_unit.version,
        "created_at": _iso(row.created_at),
        "current": revision_projection(
            revisions[-1] if revisions else None,
            active_means_ids,
            active_equipment_ids,
            active_carrier_ids,
        ),
        "history": [
            revision_projection(
                item, active_means_ids, active_equipment_ids, active_carrier_ids
            )
            for item in reversed(revisions)
        ],
    }


def _can_manage(user: dict, shipment: OperationalShipment) -> bool:
    return authorize_document_management(user, shipment).allowed


def list_for_plan(shipment_public_id: str, plan_id: int, user: dict) -> dict:
    require_permission(user, "execution_unit.read")
    shipment = _shipment(shipment_public_id, user)
    plan = _plan(shipment, plan_id)
    legs = db.session.scalars(
        select(RouteLeg)
        .where(RouteLeg.route_plan_id == plan.id)
        .order_by(RouteLeg.sequence_number, RouteLeg.id)
    ).all()
    rows = db.session.scalars(
        select(RouteStageExecution)
        .where(
            RouteStageExecution.organization_id == shipment.organization_id,
            RouteStageExecution.operational_shipment_id == shipment.id,
            RouteStageExecution.route_plan_id == plan.id,
        )
        .options(
            selectinload(RouteStageExecution.execution_unit)
            .selectinload(ExecutionUnit.transport_revisions)
            .selectinload(ExecutionTransportRevision.equipment),
            selectinload(RouteStageExecution.execution_unit)
            .selectinload(ExecutionUnit.transport_revisions)
            .selectinload(ExecutionTransportRevision.transport_means_type),
            selectinload(RouteStageExecution.execution_unit)
            .selectinload(ExecutionUnit.transport_revisions)
            .selectinload(ExecutionTransportRevision.carrier_customer),
        )
        .order_by(RouteStageExecution.created_at, RouteStageExecution.id)
    ).all()
    active_means_ids, active_equipment_ids, active_carrier_ids = (
        active_reference_ids(shipment.organization_id)
    )
    grouped: dict[int, list[dict]] = {leg.id: [] for leg in legs}
    for row in rows:
        grouped.setdefault(row.route_leg_id, []).append(
            _execution_projection(
                row, active_means_ids, active_equipment_ids, active_carrier_ids
            )
        )
    return {
        "plan": {
            "id": plan.id,
            "revision_number": plan.revision_number,
            "status": plan.status,
            "is_active": plan.is_active,
        },
        "can_manage": _can_manage(user, shipment),
        "stages": [
            {
                "id": leg.id,
                "sequence_number": leg.sequence_number,
                "branch_label": leg.branch_label,
                "origin": leg.origin_snapshot,
                "destination": leg.destination_snapshot,
                "executions": grouped.get(leg.id, []),
            }
            for leg in legs
        ],
    }


def options(shipment_public_id: str, user: dict) -> dict:
    require_permission(user, "execution_unit.read")
    shipment = _shipment(shipment_public_id, user)
    organization_id = shipment.organization_id
    means = db.session.scalars(
        select(TransportMeansType)
        .join(
            OrganizationTransportMeansTypeActivation,
            OrganizationTransportMeansTypeActivation.transport_means_type_id
            == TransportMeansType.id,
        )
        .where(
            TransportMeansType.is_active.is_(True),
            OrganizationTransportMeansTypeActivation.organization_id
            == organization_id,
            OrganizationTransportMeansTypeActivation.status == "ACTIVE",
        )
        .order_by(TransportMeansType.display_order, TransportMeansType.immutable_code)
    ).all()
    equipment = db.session.scalars(
        select(TransportEquipmentType)
        .join(
            OrganizationTransportEquipmentTypeActivation,
            OrganizationTransportEquipmentTypeActivation.transport_equipment_type_id
            == TransportEquipmentType.id,
        )
        .where(
            TransportEquipmentType.is_active.is_(True),
            OrganizationTransportEquipmentTypeActivation.organization_id
            == organization_id,
            OrganizationTransportEquipmentTypeActivation.status == "ACTIVE",
        )
        .order_by(
            TransportEquipmentType.display_order,
            TransportEquipmentType.immutable_code,
        )
    ).all()
    carriers = db.session.scalars(
        select(Customer)
        .join(
            CustomerRoleAssignment,
            CustomerRoleAssignment.customer_id == Customer.id,
        )
        .where(
            Customer.operational_organization_id == organization_id,
            Customer.status == "active",
            CustomerRoleAssignment.operational_organization_id == organization_id,
            CustomerRoleAssignment.role_code == "CARRIER",
            CustomerRoleAssignment.is_active.is_(True),
        )
        .order_by(Customer.company_name, Customer.last_name, Customer.first_name)
    ).all()
    reference = lambda row: {
        "public_id": row.public_id,
        "code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
    }
    return {
        "means": [reference(row) for row in means],
        "equipment": [reference(row) for row in equipment],
        "carriers": [
            {"id": row.id, "label": _customer_label(row)} for row in carriers
        ],
    }


def create(
    shipment_public_id: str,
    plan_id: int,
    leg_id: int,
    payload: dict,
    user: dict,
    idempotency_key: str,
):
    key = _idempotency(idempotency_key)
    shipment = _shipment(
        shipment_public_id, user, mutation_permission="execution_unit.create"
    )
    closure_guard.deny_new(shipment)
    plan = _plan(shipment, plan_id, active=True)
    leg = _leg(plan, leg_id)
    organization_id = shipment.organization_id
    request_hash = _hash(
        {
            "shipment_public_id": shipment_public_id,
            "route_plan_id": plan_id,
            "route_leg_id": leg_id,
            "payload": payload,
        }
    )
    existing = db.session.scalar(
        select(RouteStageExecution).where(
            RouteStageExecution.organization_id == organization_id,
            RouteStageExecution.idempotency_key == key,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            _fail(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key was already used with another payload.",
                409,
            )
        return existing, False

    try:
        configuration = _configuration(payload, organization_id)
        unit = ExecutionUnit(
            organization_id=organization_id,
            project_id=shipment.project_id,
            operational_shipment_id=shipment.id,
            unit_code=f"EX-{uuid.uuid4().hex[:12].upper()}",
            unit_type="transport_execution",
            created_by_user_id=int(user["id"]),
        )
        db.session.add(unit)
        db.session.flush()
        assignment = RouteStageExecution(
            organization_id=organization_id,
            operational_shipment_id=shipment.id,
            route_plan_id=plan.id,
            route_leg_id=leg.id,
            execution_unit_id=unit.id,
            idempotency_key=key,
            request_hash=request_hash,
            created_by_user_id=int(user["id"]),
        )
        db.session.add(assignment)
        _revision(
            unit,
            configuration,
            revision_number=1,
            actor_id=int(user["id"]),
            idempotency_key=key,
            request_hash=request_hash,
        )
        db.session.add(
            OperationalAudit(
                organization_id=organization_id,
                actor_user_id=int(user["id"]),
                action="ROUTE_STAGE_EXECUTION_CREATED",
                entity_type="ExecutionUnit",
                entity_id=unit.id,
                metadata_json={
                    "route_plan_id": plan.id,
                    "route_leg_id": leg.id,
                    "transport_revision": 1,
                },
            )
        )
        db.session.flush()
    except IntegrityError:
        # A concurrent replay can pass the initial lookup before the first
        # request commits.  The tenant-scoped unique key is authoritative;
        # after rollback, return only the exact same command.
        db.session.rollback()
        replay = db.session.scalar(
            select(RouteStageExecution).where(
                RouteStageExecution.organization_id == organization_id,
                RouteStageExecution.idempotency_key == key,
            )
        )
        if replay is not None and replay.request_hash == request_hash:
            return replay, False
        if replay is not None:
            _fail(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key was already used with another payload.",
                409,
            )
        raise
    return assignment, True


def _assignment(
    shipment: OperationalShipment, plan_id: int, execution_public_id: str
) -> RouteStageExecution:
    row = db.session.scalar(
        select(RouteStageExecution)
        .join(ExecutionUnit, ExecutionUnit.id == RouteStageExecution.execution_unit_id)
        .where(
            RouteStageExecution.organization_id == shipment.organization_id,
            RouteStageExecution.operational_shipment_id == shipment.id,
            RouteStageExecution.route_plan_id == plan_id,
            ExecutionUnit.public_id == execution_public_id,
        )
    )
    if row is None:
        _fail("TRANSPORT_EXECUTION_NOT_FOUND", "Transport execution was not found.", 404)
    return row


def revise(
    shipment_public_id: str,
    plan_id: int,
    execution_public_id: str,
    payload: dict,
    user: dict,
    idempotency_key: str,
):
    key = _idempotency(idempotency_key)
    request_hash = _hash(payload)
    shipment = _shipment(
        shipment_public_id, user, mutation_permission="execution_unit.update"
    )
    _plan(shipment, plan_id)
    assignment = _assignment(shipment, plan_id, execution_public_id)
    unit = db.session.scalar(
        select(ExecutionUnit)
        .where(
            ExecutionUnit.id == assignment.execution_unit_id,
            ExecutionUnit.organization_id == shipment.organization_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    existing = db.session.scalar(
        select(ExecutionTransportRevision).where(
            ExecutionTransportRevision.execution_unit_id == unit.id,
            ExecutionTransportRevision.idempotency_key == key,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            _fail(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key was already used with another payload.",
                409,
            )
        return assignment, existing, False
    expected = payload.get("expected_version")
    if isinstance(expected, bool) or not isinstance(expected, int):
        _fail("VERSION_REQUIRED", "expected_version is required.", 409)
    if expected != unit.version:
        _fail(
            "VERSION_CONFLICT",
            "expected_version does not match the current execution version.",
            409,
        )
    configuration = _configuration(payload, shipment.organization_id)
    closure_guard.unit_prior_fact(unit, configuration["effective_at"], configuration["reason"], require_reason=True)
    latest = db.session.scalar(
        select(ExecutionTransportRevision)
        .where(ExecutionTransportRevision.execution_unit_id == unit.id)
        .order_by(
            ExecutionTransportRevision.revision_number.desc(),
            ExecutionTransportRevision.id.desc(),
        )
        .limit(1)
    )
    revision_number = (latest.revision_number if latest else 0) + 1
    revision = _revision(
        unit,
        configuration,
        revision_number=revision_number,
        actor_id=int(user["id"]),
        idempotency_key=key,
        request_hash=request_hash,
    )
    unit.version += 1
    unit.updated_at = utcnow()
    db.session.add(
        OperationalAudit(
            organization_id=shipment.organization_id,
            actor_user_id=int(user["id"]),
            action="ROUTE_STAGE_EXECUTION_REVISED",
            entity_type="ExecutionUnit",
            entity_id=unit.id,
            metadata_json={
                "route_plan_id": plan_id,
                "route_leg_id": assignment.route_leg_id,
                "transport_revision": revision_number,
                "reason": configuration["reason"],
            },
        )
    )
    db.session.flush()
    return assignment, revision, True


def execution_projection(row: RouteStageExecution) -> dict:
    """Public projection helper for route handlers after a flushed command."""
    active_means_ids, active_equipment_ids, active_carrier_ids = (
        active_reference_ids(row.organization_id)
    )
    return _execution_projection(
        row, active_means_ids, active_equipment_ids, active_carrier_ids
    )
