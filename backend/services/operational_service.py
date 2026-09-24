"""Transactional application services for the Phase 1A operational slice."""

from __future__ import annotations
from backend.services.occurrence_projection_service import atomic_command

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import exists, or_, select, text
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.census_context import ensure_census_context
from backend.models import Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import (
    CanonicalLocation,
    Milestone,
    MilestoneEvent,
    OperationalAudit,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOutbox,
    OperationalShipment,
    OperationalWorkItem,
    Project,
    RouteLeg,
    RoutePlan,
    utcnow,
)
from backend.services.location_resolver import LocationResolutionError, ResolvedLocation
from backend.services.location_resolver import (
    resolve_location as resolve_canonical_location,
)
from backend.services.facility_endpoint_resolver import resolve_facility_endpoint, ResolvedFacilityEndpoint
from backend.services.request_transport_projection import (
    project_existing_request_transport,
)

TRANSPORT_MODES = {
    "road",
    "rail",
    "sea",
    "air",
    "multimodal_transfer",
    "customs_handling",
}


class OperationalError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def require_permission(user: dict[str, Any], permission: str) -> None:
    membership = _membership_for_user(int(user["id"]))
    if permission not in set(membership.permissions or []):
        raise OperationalError(
            "FORBIDDEN_OPERATION", "You are not allowed to perform this operation.", 403
        )


def require_any_permission(user: dict[str, Any], permissions: set[str]) -> None:
    membership = _membership_for_user(int(user["id"]))
    if not permissions.intersection(membership.permissions or []):
        raise OperationalError(
            "FORBIDDEN_OPERATION", "You are not allowed to perform this operation.", 403
        )


def _membership_for_user(user_id: int) -> OperationalMembership:
    from backend.operational_models import OperationalOrganization

    rows = db.session.scalars(
        select(OperationalMembership)
        .join(
            OperationalOrganization,
            OperationalMembership.organization_id == OperationalOrganization.id,
        )
        .where(
            OperationalMembership.user_id == user_id,
            OperationalMembership.is_active.is_(True),
            OperationalOrganization.is_active.is_(True),
        )
    ).all()
    if len(rows) != 1:
        raise OperationalError(
            "TENANT_SCOPE_VIOLATION",
            "Exactly one active operational organization membership is required.",
            403,
        )
    return rows[0]


def organization_for_user(user_id: int) -> int:
    return int(_membership_for_user(user_id).organization_id)


def _validated_responsible_expert_id(
    value: Any, organization_id: int, *, source: str
) -> int:
    """Resolve one active same-tenant Transport Expert at creation time."""
    if type(value) is not int:
        code = (
            "DIRECT_RESPONSIBLE_EXPERT_REQUIRED"
            if source == "direct"
            else "QUOTE_ISSUER_NOT_ELIGIBLE"
        )
        raise OperationalError(code, "A responsible Transport Expert is required.")
    expert = db.session.scalar(
        select(ExpertUser)
        .where(ExpertUser.id == value)
        .execution_options(populate_existing=True)
    )
    if (
        expert is None
        or not expert.is_active
        or (expert.authority or "").upper() != "EXPERT"
    ):
        code = (
            "DIRECT_RESPONSIBLE_EXPERT_NOT_ELIGIBLE"
            if source == "direct"
            else "QUOTE_ISSUER_NOT_ELIGIBLE"
        )
        raise OperationalError(
            code, "The responsible Transport Expert is not eligible.", 409
        )
    try:
        membership = _membership_for_user(expert.id)
    except OperationalError as exc:
        code = (
            "DIRECT_RESPONSIBLE_EXPERT_NOT_ELIGIBLE"
            if source == "direct"
            else "QUOTE_ISSUER_NOT_ELIGIBLE"
        )
        raise OperationalError(
            code, "The responsible Transport Expert is not eligible.", 409
        ) from exc
    if int(membership.organization_id) != int(organization_id):
        code = (
            "DIRECT_RESPONSIBLE_EXPERT_TENANT_MISMATCH"
            if source == "direct"
            else "QUOTE_ISSUER_TENANT_MISMATCH"
        )
        raise OperationalError(
            code,
            "Responsible Expert must have the Shipment tenant membership.",
            403,
        )
    return int(expert.id)


def operational_context(user: dict[str, Any]) -> dict[str, Any]:
    membership = _membership_for_user(int(user["id"]))
    return {
        "organization_id": membership.organization_id,
        "permissions": sorted(set(membership.permissions or [])),
    }


def _selector_organization(
    user: dict[str, Any], permissions: set[str]
) -> int:
    """Resolve one active tenant and authorize without relying on role names."""
    membership = _membership_for_user(int(user["id"]))
    if not permissions.intersection(membership.permissions or []):
        raise OperationalError(
            "FORBIDDEN_OPERATION", "You are not allowed to perform this operation.", 403
        )
    return int(membership.organization_id)


def _selector_terms(args: dict[str, Any]) -> tuple[str, int]:
    q = str(args.get("q") or "").strip()
    if len(q) > 160:
        raise OperationalError("VALIDATION_FAILED", "q must not exceed 160 characters.")
    try:
        limit = int(args.get("limit", 25))
    except (TypeError, ValueError) as exc:
        raise OperationalError(
            "VALIDATION_FAILED", "limit must be an integer."
        ) from exc
    if limit < 1 or limit > 100:
        raise OperationalError("VALIDATION_FAILED", "limit must be between 1 and 100.")
    return q, limit


def _customer_label(customer: Customer) -> str:
    return (
        customer.company_name
        or " ".join(
            value for value in (customer.first_name, customer.last_name) if value
        ).strip()
    )


def customer_selector(args: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    """Return active customers in the caller's single operational tenant."""
    org = _selector_organization(
        user,
        {
            "operational_shipment.create",
            "operational_shipment.create_direct",
            "operational_shipment.create_from_quote",
        },
    )
    q, limit = _selector_terms(args)
    query = select(Customer).where(
        Customer.status == "active",
        Customer.operational_organization_id == org,
    )
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                Customer.company_name.ilike(pattern),
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
            )
        )
    rows = db.session.scalars(
        query.order_by(
            Customer.company_name.asc().nullslast(),
            Customer.last_name.asc(),
            Customer.first_name.asc(),
            Customer.id.asc(),
        ).limit(limit)
    ).all()
    return {
        "items": [{"id": row.id, "label": _customer_label(row)} for row in rows],
        "meta": {"count": len(rows), "limit": limit},
    }


def project_selector(args: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    org = _selector_organization(
        user,
        {
            "operational_shipment.create_direct",
            "operational_shipment.create_from_quote",
            "operational_shipment.create",
        },
    )
    q, limit = _selector_terms(args)
    from backend.services.project_access_authorization import authorized_project_scope
    query = select(Project).where(
        Project.organization_id == org,
        authorized_project_scope(user),
        Project.lifecycle_status.not_in(("completed", "cancelled")),
    )
    customer_id = args.get("customer_id")
    if customer_id not in (None, ""):
        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError) as exc:
            raise OperationalError(
                "VALIDATION_FAILED", "customer_id must be an integer."
            ) from exc
        query = query.where(Project.primary_customer_id == customer_id)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                Project.project_code.ilike(pattern),
                Project.tracking_code.ilike(pattern),
            )
        )
    rows = db.session.scalars(
        query.order_by(
            Project.project_code.asc(), Project.tracking_code.asc(), Project.id.asc()
        ).limit(limit)
    ).all()
    return {
        "items": [
            {
                "public_id": row.public_id,
                "label": row.project_code,
                "project_code": row.project_code,
                "primary_customer_id": row.primary_customer_id,
                "lifecycle_status": row.lifecycle_status,
            }
            for row in rows
        ],
        "meta": {"count": len(rows), "limit": limit},
    }


def _eligible_quote_query(org: int, user: dict[str, Any]):
    from backend.services.assigned_work_authorization import assigned_request_scope

    return (
        select(ExpertQuote)
        .join(ShipmentRequest, ShipmentRequest.id == ExpertQuote.shipment_request_id)
        .where(
            ExpertQuote.operational_organization_id == org,
            assigned_request_scope(user),
            ExpertQuote.customer_response == "accepted",
            ShipmentRequest.customer_id.is_not(None),
            ~exists(
                select(OperationalShipment.id).where(
                    OperationalShipment.accepted_quote_id == ExpertQuote.id
                )
            ),
        )
    )


def accepted_quote_selector(
    args: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    org = _selector_organization(
        user,
        {"operational_shipment.create_from_quote", "operational_shipment.create"},
    )
    q, limit = _selector_terms(args)
    query = _eligible_quote_query(org, user)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                ShipmentRequest.tracking_code.ilike(pattern),
                ShipmentRequest.customer_first_name.ilike(pattern),
                ShipmentRequest.customer_last_name.ilike(pattern),
            )
        )
    rows = db.session.scalars(
        query.order_by(
            ExpertQuote.responded_at.desc().nullslast(), ExpertQuote.id.desc()
        ).limit(limit)
    ).all()
    items = []
    for quote in rows:
        request_row = db.session.get(ShipmentRequest, quote.shipment_request_id)
        customer = db.session.get(Customer, request_row.customer_id)
        items.append(
            {
                "id": quote.id,
                "request_public_id": request_row.tracking_code,
                "customer_label": _customer_label(customer),
                "route_label": " → ".join(
                    value
                    for value in (
                        request_row.origin_city_international,
                        request_row.dest_city_international,
                    )
                    if value
                )
                or None,
                "quote_label": f"{quote.amount} {quote.currency}",
                "accepted_at": quote.responded_at.isoformat()
                if quote.responded_at
                else None,
            }
        )
    return {"items": items, "meta": {"count": len(items), "limit": limit}}


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise OperationalError(
            "INVALID_ROUTE_TIMELINE", f"{field} must be an ISO-8601 timestamp."
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationalError(
            "INVALID_ROUTE_TIMELINE", f"{field} must be an ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None:
        raise OperationalError(
            "INVALID_ROUTE_TIMELINE", f"{field} must include a timezone."
        )
    return parsed.astimezone(timezone.utc)


def _occurrence_time(value: Any, field: str = "occurred_at") -> datetime:
    occurred = _parse_utc(value, field)
    if occurred > utcnow() + timedelta(minutes=5):
        raise OperationalError("INVALID_MILESTONE_TRANSITION", f"{field} is unreasonably far in the future.")
    return occurred


def _reject_recorded_at(payload: dict) -> None:
    if "recorded_at" in payload:
        raise OperationalError("INVALID_MILESTONE_TRANSITION", "recorded_at is server-generated.")


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _lock_idempotency_scope(
    organization_id: int,
    operation: str,
    resource_type: str,
    resource_id: int,
    key: str,
) -> None:
    """Serialize one exact command/resource/key scope for this transaction."""
    if db.session.get_bind().dialect.name != "postgresql":
        return
    scope = json.dumps(
        [organization_id, operation, resource_type, resource_id, key],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    lock_id = int.from_bytes(
        hashlib.sha256(scope.encode()).digest()[:8], "big", signed=True
    )
    db.session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id}
    )


def _require_idempotency_key(key: str) -> None:
    if not key or len(key) > 100:
        raise OperationalError(
            "VALIDATION_FAILED", "A valid Idempotency-Key is required."
        )


def _audit(
    org: int,
    actor: int,
    action: str,
    entity_type: str,
    entity_id: int,
    metadata: dict | None = None,
) -> None:
    db.session.add(
        OperationalAudit(
            organization_id=org,
            actor_user_id=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
    )


def _outbox(
    org: int,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int,
    payload: dict | None = None,
) -> None:
    context = ensure_census_context(db.session)
    event_payload = dict(payload or {})
    event_payload["_ownership_census"] = {
        "census_id": context.census_id,
        "cache_version": context.cache_version,
        "cache_token": context.cache_token,
    }
    db.session.add(
        OperationalOutbox(
            organization_id=org,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=event_payload,
        )
    )


def resolve_location(reference: dict[str, Any]) -> ResolvedLocation:
    """Expose the shared resolver through the existing operational service boundary."""
    try:
        return resolve_canonical_location(reference)
    except LocationResolutionError as exc:
        raise OperationalError(exc.code, exc.message, exc.status) from exc


def _location_snapshot(
    location: ResolvedLocation | CanonicalLocation,
) -> dict[str, Any]:
    if isinstance(location, ResolvedLocation):
        return location.snapshot()
    # Backward-compatible support for callers holding an existing canonical row.
    return {
        "canonical_location_id": location.id,
        "display_name": location.display_name,
        "location_type": location.location_type,
        "country_code": location.country_code,
        "verification_state": location.verification_state,
    }


def _endpoint(reference: dict[str, Any], organization_id: int):
    if reference.get("source_type") == "logistics_point":
        try:
            return resolve_facility_endpoint(organization_id, reference.get("source_id"))
        except LocationResolutionError as exc:
            raise OperationalError(exc.code, exc.message, exc.status) from exc
    return resolve_location(reference)


def _endpoint_location(endpoint: ResolvedLocation | ResolvedFacilityEndpoint) -> ResolvedLocation:
    return endpoint.geography if isinstance(endpoint, ResolvedFacilityEndpoint) else endpoint


def _endpoint_snapshot(endpoint: ResolvedLocation | ResolvedFacilityEndpoint) -> dict[str, Any]:
    geography = _endpoint_location(endpoint)
    snapshot = _location_snapshot(geography)
    if isinstance(endpoint, ResolvedFacilityEndpoint):
        snapshot["facility"] = endpoint.snapshot()
    return snapshot


def _endpoint_reference(endpoint: ResolvedLocation | ResolvedFacilityEndpoint) -> dict[str, Any]:
    if isinstance(endpoint, ResolvedFacilityEndpoint):
        return {
            "source_type": "logistics_point",
            "source_id": endpoint.logistics_point.public_id,
        }
    return {"source_type": endpoint.source_type, "source_id": endpoint.source_id}


def _route_command(payload: dict[str, Any], organization_id: int):
    route = payload.get("route") if isinstance(payload.get("route"), dict) else payload
    departure = _parse_utc(route.get("planned_departure"), "planned_departure")
    arrival = _parse_utc(route.get("planned_arrival"), "planned_arrival")
    if arrival < departure:
        raise OperationalError(
            "INVALID_ROUTE_TIMELINE",
            "Planned arrival cannot be before planned departure.",
        )
    origin, destination = (_endpoint(route.get("origin") or {}, organization_id), _endpoint(route.get("destination") or {}, organization_id))
    origin_location, destination_location = _endpoint_location(origin), _endpoint_location(destination)
    origin_point = origin.logistics_point.id if isinstance(origin, ResolvedFacilityEndpoint) else None
    destination_point = destination.logistics_point.id if isinstance(destination, ResolvedFacilityEndpoint) else None
    if origin_location.canonical_location.id == destination_location.canonical_location.id and origin_point == destination_point:
        raise OperationalError(
            "INVALID_ROUTE_TIMELINE", "Origin and destination must be different."
        )
    mode = str(route.get("transport_mode") or "").strip()
    if mode not in TRANSPORT_MODES:
        raise OperationalError("VALIDATION_FAILED", "transport_mode is invalid.")
    return origin, destination, mode, departure, arrival


def _project(org: int, public_id: Any, customer_id: int) -> Project | None:
    if public_id in (None, ""):
        return None
    row = db.session.scalar(
        select(Project).where(
            Project.public_id == str(public_id), Project.organization_id == org
        )
    )
    if row is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Project was not found.", 404)
    if row.primary_customer_id != customer_id:
        raise OperationalError(
            "PROJECT_CUSTOMER_MISMATCH",
            "Project customer does not match shipment customer.",
        )
    return row


def _initialize_aggregate(
    *,
    org,
    user,
    source_type,
    customer_id,
    request_id,
    quote_id,
    project,
    route,
    operation,
    resource_type,
    resource_id,
    key,
    request_hash,
    primary_responsible_expert_id=None,
):
    origin, destination, mode, departure, arrival = route
    shipment = OperationalShipment(
        organization_id=org,
        project_id=project.id if project else None,
        source_type=source_type,
        customer_id=customer_id,
        shipment_request_id=request_id,
        accepted_quote_id=quote_id,
        lifecycle_status="planned",
        created_by_user_id=user["id"],
        primary_responsible_expert_id=primary_responsible_expert_id,
    )
    db.session.add(shipment)
    db.session.flush()
    plan = RoutePlan(
        operational_shipment_id=shipment.id,
        revision=1,
        is_active=True,
        created_by_user_id=user["id"],
    )
    db.session.add(plan)
    db.session.flush()
    leg = RouteLeg(
        route_plan_id=plan.id,
        sequence_number=1,
        origin_location_id=_endpoint_location(origin).canonical_location.id,
        destination_location_id=_endpoint_location(destination).canonical_location.id,
        origin_logistics_point_id=origin.logistics_point.id if isinstance(origin, ResolvedFacilityEndpoint) else None,
        destination_logistics_point_id=destination.logistics_point.id if isinstance(destination, ResolvedFacilityEndpoint) else None,
        origin_snapshot=_endpoint_snapshot(origin),
        destination_snapshot=_endpoint_snapshot(destination),
        transport_mode=mode,
        planned_departure=departure,
        planned_arrival=arrival,
        status="planned",
    )
    db.session.add(leg)
    db.session.flush()
    db.session.add_all(
        [
            Milestone(
                organization_id=org,
                operational_shipment_id=shipment.id,
                route_plan_id=plan.id,
                route_leg_id=leg.id,
                milestone_type="departure",
                planned_at=departure,
                projected_at=departure,
            ),
            Milestone(
                organization_id=org,
                operational_shipment_id=shipment.id,
                route_plan_id=plan.id,
                route_leg_id=leg.id,
                milestone_type="arrival",
                planned_at=arrival,
                projected_at=arrival,
            ),
        ]
    )
    db.session.add(
        OperationalIdempotency(
            organization_id=org,
            operation=operation,
            resource_type=resource_type,
            command_resource_id=resource_id,
            idempotency_key=key,
            request_hash=request_hash,
            result_resource_id=shipment.id,
        )
    )
    metadata = {
        "shipment_public_id": shipment.public_id,
        "source_type": source_type,
        "customer_id": customer_id,
        "project_public_id": project.public_id if project else None,
        "idempotency_key": key,
    }
    _audit(
        org,
        user["id"],
        "operational_shipment.created",
        "OperationalShipment",
        shipment.id,
        metadata,
    )
    _outbox(
        org,
        "operational_shipment.created",
        "OperationalShipment",
        shipment.id,
        metadata,
    )
    return shipment


def create_direct(
    payload: dict[str, Any], user: dict[str, Any], key: str
) -> tuple[OperationalShipment, bool]:
    require_permission(user, "operational_shipment.create_direct")
    org = organization_for_user(int(user["id"]))
    _require_idempotency_key(key)
    if payload.get("source_type") != "direct":
        raise OperationalError(
            "INVALID_OPERATION_SOURCE", "source_type must be direct."
        )
    if "shipment_request_id" in payload or "accepted_quote_id" in payload:
        raise OperationalError(
            "COMMERCIAL_LINEAGE_NOT_ALLOWED",
            "Direct operations cannot include commercial lineage.",
        )
    customer_id = payload.get("customer_id")
    if type(customer_id) is not int:
        raise OperationalError(
            "CUSTOMER_REQUIRED", "A canonical customer_id is required."
        )
    customer = db.session.get(Customer, customer_id)
    if customer is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Customer was not found.", 404)
    if customer.status != "active":
        raise OperationalError(
            "CUSTOMER_NOT_ELIGIBLE",
            "Customer is not eligible for operational creation.",
        )
    if customer.ownership_scope != "TENANT" or customer.operational_organization_id != org:
        raise OperationalError("RESOURCE_NOT_FOUND", "Customer was not found.", 404)
    # A direct shipment created by an authorized Expert is explicitly rooted in
    # that actor unless an in-tenant responsible Expert is supplied. This is a
    # creation-time assignment, not creator-history authorization.
    responsible_id = _validated_responsible_expert_id(
        payload.get("primary_responsible_expert_id", user["id"]),
        org,
        source="direct",
    )
    project = _project(org, payload.get("project_public_id"), customer.id)
    route = _route_command(payload, org)
    canonical = {
        "source_type": "direct",
        "customer_id": customer.id,
        "primary_responsible_expert_id": responsible_id,
        "project_public_id": project.public_id if project else None,
        "route": {
            "origin": _endpoint_reference(route[0]),
            "destination": _endpoint_reference(route[1]),
            "transport_mode": route[2],
            "planned_departure": route[3].isoformat(),
            "planned_arrival": route[4].isoformat(),
        },
    }
    request_hash = _hash(canonical)
    _lock_idempotency_scope(org, "create_direct_shipment", "organization", 0, key)
    replay = db.session.scalar(
        select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == org,
            OperationalIdempotency.operation == "create_direct_shipment",
            OperationalIdempotency.resource_type == "organization",
            OperationalIdempotency.command_resource_id == 0,
            OperationalIdempotency.idempotency_key == key,
        )
    )
    if replay:
        shipment = db.session.get(OperationalShipment, replay.result_resource_id)
        from backend.services.assigned_work_authorization import authorize_work_action
        if shipment is None or not authorize_work_action(user, shipment, "shipment.read").allowed:
            raise OperationalError("RESOURCE_NOT_FOUND", "Operational shipment was not found.", 404)
        if replay.request_hash != request_hash:
            raise OperationalError(
                "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD",
                "Idempotency key was already used with a different payload.",
                409,
            )
        return shipment, False
    shipment = _initialize_aggregate(
        org=org,
        user=user,
        source_type="direct",
        customer_id=customer.id,
        request_id=None,
        quote_id=None,
        project=project,
        route=route,
        operation="create_direct_shipment",
        resource_type="organization",
        resource_id=0,
        key=key,
        request_hash=request_hash,
        primary_responsible_expert_id=responsible_id,
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise OperationalError(
            "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD",
            "Concurrent idempotency conflict.",
            409,
        ) from exc
    return shipment, True


def create_from_accepted_quote(
    payload: dict[str, Any], user: dict[str, Any], key: str
) -> tuple[OperationalShipment, bool]:
    require_any_permission(
        user, {"operational_shipment.create_from_quote", "operational_shipment.create"}
    )
    org = organization_for_user(int(user["id"]))
    _require_idempotency_key(key)
    request_hash = _hash(payload)
    quote_id = payload.get("accepted_quote_id")
    _lock_idempotency_scope(org, "create_shipment", "accepted_quote", quote_id, key)
    replay = db.session.scalar(
        select(OperationalIdempotency).where(
            OperationalIdempotency.organization_id == org,
            OperationalIdempotency.operation == "create_shipment",
            OperationalIdempotency.resource_type == "accepted_quote",
            OperationalIdempotency.command_resource_id == quote_id,
            OperationalIdempotency.idempotency_key == key,
        )
    )
    if replay:
        shipment = db.session.get(OperationalShipment, replay.result_resource_id)
        from backend.services.assigned_work_authorization import authorize_work_action
        if shipment is None or not authorize_work_action(user, shipment, "shipment.read").allowed:
            raise OperationalError("RESOURCE_NOT_FOUND", "The accepted quote was not found.", 404)
        if replay.request_hash != request_hash:
            raise OperationalError(
                "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD",
                "Idempotency key was already used with a different payload.",
                409,
            )
        return shipment, False
    quote = db.session.scalar(
        select(ExpertQuote).where(ExpertQuote.id == quote_id).with_for_update()
    )
    if quote is None:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "The accepted quote was not found.", 404
        )
    if quote.operational_organization_id != org:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "The accepted quote was not found.", 404
        )
    if quote.customer_response != "accepted":
        raise OperationalError(
            "QUOTE_NOT_ACCEPTED", "The selected quote is not accepted.", 422
        )
    request_row = db.session.get(ShipmentRequest, quote.shipment_request_id)
    if request_row is None:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "The source shipment request was not found.", 404
        )
    if (
        request_row.ownership_scope != "TENANT"
        or request_row.operational_organization_id != org
    ):
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "The accepted quote was not found.", 404
        )
    from backend.services.assigned_work_authorization import authorize_work_action
    if not authorize_work_action(user, request_row, "request.read").allowed:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "The accepted quote was not found.", 404
        )
    existing = db.session.scalar(
        select(OperationalShipment).where(
            OperationalShipment.accepted_quote_id == quote.id
        )
    )
    if existing:
        if existing.organization_id != org:
            raise OperationalError(
                "RESOURCE_NOT_FOUND",
                "The accepted quote was not found.",
                404,
            )
        raise OperationalError(
            "OPERATIONAL_SHIPMENT_ALREADY_EXISTS",
            "An operational shipment already exists for this quote.",
            409,
        )
    if request_row.customer_id is None:
        raise OperationalError(
            "CUSTOMER_REQUIRED", "The shipment request requires a canonical customer."
        )
    customer = db.session.get(Customer, request_row.customer_id)
    if (
        customer is None
        or customer.ownership_scope != "TENANT"
        or customer.operational_organization_id != org
    ):
        raise OperationalError(
            "CUSTOMER_LINEAGE_CONFLICT",
            "The accepted quote customer lineage is not tenant-consistent.",
            409,
        )
    responsible_id = _validated_responsible_expert_id(
        quote.created_by_expert_id, org, source="accepted_quote"
    )
    project = _project(org, payload.get("project_public_id"), request_row.customer_id)
    shipment = _initialize_aggregate(
        org=org,
        user=user,
        source_type="accepted_quote",
        customer_id=request_row.customer_id,
        request_id=request_row.id,
        quote_id=quote.id,
        project=project,
        route=_route_command(payload, org),
        operation="create_shipment",
        resource_type="accepted_quote",
        resource_id=quote.id,
        key=key,
        request_hash=request_hash,
        primary_responsible_expert_id=responsible_id,
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = db.session.scalar(
            select(OperationalShipment).where(
                OperationalShipment.accepted_quote_id == quote.id
            )
        )
        if existing and existing.organization_id == org:
            return existing, False
        raise OperationalError(
            "OPERATIONAL_SHIPMENT_ALREADY_EXISTS",
            "An operational shipment already exists for this quote.",
            409,
        )
    return shipment, True


def scoped_shipment(shipment_id: str, user: dict[str, Any]) -> OperationalShipment:
    """Resolve the externally supplied opaque shipment identity inside its tenant."""
    require_permission(user, "operational_shipment.read")
    org = organization_for_user(int(user["id"]))
    identity_clause = (
        OperationalShipment.id == shipment_id
        if isinstance(shipment_id, int)
        else OperationalShipment.public_id == str(shipment_id)
    )
    shipment = db.session.scalar(
        select(OperationalShipment).where(
            identity_clause,
            OperationalShipment.organization_id == org,
        )
    )
    if shipment is None:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "Operational shipment was not found.", 404
        )
    from backend.services.assigned_work_authorization import authorize_work_action
    if not authorize_work_action(user, shipment, "shipment.read").allowed:
        raise OperationalError("RESOURCE_NOT_FOUND", "Operational shipment was not found.", 404)
    return shipment


def scoped_shipment_by_public_id(
    public_id: str, user: dict[str, Any]
) -> OperationalShipment:
    """Resolve the external identity inside the caller's tenant boundary."""
    return scoped_shipment(public_id, user)


def shipment_graph(shipment: OperationalShipment) -> dict[str, Any]:
    from backend.services import operational_read_service as reads
    from backend.services import occurrence_projection_service as authority
    plan = authority.active_plan(shipment)
    route_read = reads.current_route(shipment, plan)
    legs = db.session.scalars(
        select(RouteLeg)
        .where(RouteLeg.route_plan_id == (plan.id if plan else -1))
        .order_by(RouteLeg.sequence_number)
    ).all()
    leg = legs[0] if legs else None
    leg_ids = [row.id for row in legs]
    milestones = db.session.scalars(
        select(Milestone)
        .where(
            (Milestone.route_plan_id == (plan.id if plan else -1)) | (Milestone.route_leg_id.in_(leg_ids)),
            Milestone.operational_shipment_id == shipment.id,
            Milestone.organization_id == shipment.organization_id,
        )
        .order_by(Milestone.planned_at, Milestone.id)
    ).all()
    leg_milestones = {(m.route_leg_id, m.milestone_type): m.public_id for m in milestones
                      if m.route_leg_id and m.milestone_type in {"departure", "arrival"}}
    events = db.session.scalars(
        select(MilestoneEvent)
        .where(MilestoneEvent.milestone_id.in_([m.id for m in milestones]),
               MilestoneEvent.organization_id == shipment.organization_id)
        .order_by(MilestoneEvent.recorded_at.desc(), MilestoneEvent.id.desc())
        .limit(20)
    ).all()
    work = db.session.scalars(
        select(OperationalWorkItem).where(
            OperationalWorkItem.operational_shipment_id == shipment.id,
            OperationalWorkItem.status == "open",
        )
    ).all()
    quote = (
        db.session.get(ExpertQuote, shipment.accepted_quote_id)
        if shipment.accepted_quote_id
        else None
    )
    request_row = (
        db.session.get(ShipmentRequest, shipment.shipment_request_id)
        if shipment.shipment_request_id
        else None
    )
    customer_row = (
        db.session.get(Customer, shipment.customer_id) if shipment.customer_id else None
    )
    audits = db.session.scalars(reads.audit_query(shipment).order_by(
        OperationalAudit.recorded_at.desc(), OperationalAudit.id.desc()).limit(20)).all()
    proofs = route_read["milestone_evidence"]
    current = next(
        (m for m in milestones if not proofs.get(m.id, {}).get("effective_event_public_id")),
        None,
    )
    now = utcnow()
    overdue = [
        m
        for m in milestones
        if not proofs.get(m.id, {}).get("effective_event_public_id")
        and m.planned_at is not None
        and m.planned_at.replace(tzinfo=m.planned_at.tzinfo or timezone.utc) < now
    ]
    display_name = (
        (
            customer_row.company_name
            or " ".join(
                filter(None, [customer_row.first_name, customer_row.last_name])
            ).strip()
        )
        if customer_row
        else None
    )
    customer = (
        {"id": customer_row.id, "display_name": display_name} if customer_row else None
    )
    responsible_name = db.session.scalar(
        select(ExpertUser.full_name).where(
            ExpertUser.id == shipment.primary_responsible_expert_id
        )
    )
    event_views = [reads.event_view(event, shipment) for event in events]
    latest_event = event_views[0] if event_views else None

    def leg_data(row):
        return {
            "id": row.id,
            "departure_milestone_id": leg_milestones.get((row.id, "departure")),
            "arrival_milestone_id": leg_milestones.get((row.id, "arrival")),
            "sequence_number": row.sequence_number,
            "origin": row.origin_snapshot,
            "destination": row.destination_snapshot,
            "origin_location_id": row.origin_location_id,
            "destination_location_id": row.destination_location_id,
            "origin_logistics_point_id": row.origin_logistics_point_id,
            "destination_logistics_point_id": row.destination_logistics_point_id,
            "transport_mode": row.transport_mode,
            "planned_departure": row.planned_departure.isoformat(),
            "planned_arrival": row.planned_arrival.isoformat(),
            "status": row.status,
            "version": row.version,
            "execution_provenance": next((v for v in route_read["route_legs"] if v["id"] == row.id), None),
        }

    return {
        "public_id": shipment.public_id,
        "status": route_read["status"],
        "operational_provenance": route_read,
        "scope": "current_route",
        "recent_events_scope": "current_route",
        "history_scope": "shipment_history",
        "version": shipment.version,
        "created_at": reads.iso(shipment.created_at),
        "updated_at": reads.iso(shipment.updated_at),
        "customer": customer,
        "responsible_expert": (
            {"display_name": responsible_name} if responsible_name else None
        ),
        "project_public_id": db.session.scalar(
            select(Project.public_id).where(Project.id == shipment.project_id)
        )
        if shipment.project_id
        else None,
        "source": {
            "type": shipment.source_type,
            "accepted_quote_id": shipment.accepted_quote_id,
            "shipment_request_id": shipment.shipment_request_id,
            "request_public_id": request_row.public_id if request_row else None,
            "quote_amount": quote.amount if quote else None,
            "request_transport": {
                "shipping_type": request_row.shipping_type,
                **project_existing_request_transport(request_row),
            }
            if request_row
            else None,
        },
        "route_plan": {
            "id": plan.id,
            "revision": plan.revision,
            "revision_number": plan.revision_number,
            "status": plan.status,
            "is_active": plan.is_active,
            "version": plan.version,
        } if plan else None,
        "route_leg": leg_data(leg) if leg else None,
        "route_legs": [leg_data(row) for row in legs],
        "route_summary": {
            "origin": {
                "display_name": (legs[0].origin_snapshot or {}).get("display_name")
            },
            "destination": {
                "display_name": (legs[-1].destination_snapshot or {}).get(
                    "display_name"
                )
            },
            "transport_modes": list(
                dict.fromkeys(row.transport_mode for row in legs)
            ),
            "leg_count": len(legs),
        }
        if legs
        else None,
        "latest_update": (
            {
                "event_type": latest_event["event_type"],
                "label": latest_event["business_label"],
                "milestone_type": latest_event["milestone_type"],
                "occurred_at": latest_event["occurred_at"],
                "recorded_at": latest_event["recorded_at"],
                "source": latest_event["source_channel"],
            }
            if latest_event
            else None
        ),
        "current_milestone": current.milestone_type if current else None,
        "overdue": bool(overdue),
        "overdue_since": min((m.planned_at for m in overdue), default=None).isoformat()
        if overdue
        else None,
        "open_work_item_count": len(work),
        "milestones": [
            {
                "id": m.id,
                "type": m.milestone_type,
                "planned_at": reads.iso(m.planned_at),
                "execution_evidence": proofs.get(m.id),
                "occurred_at": proofs.get(m.id, {}).get("effective_occurred_at"),
                "verification_state": m.verification_state,
                "version": m.version,
            }
            for m in milestones
        ],
        "recent_events": event_views,
        "open_work_items": [
            {
                "id": w.id,
                "milestone_id": w.milestone_id,
                "type": w.work_type,
                "due_at": w.due_at.isoformat(),
                "status": w.status,
                "version": w.version,
            }
            for w in work
        ],
        "audit_summary": [
            {"id": a.id, "action": a.action, "recorded_at": a.recorded_at.isoformat(),
             "entity_type": a.entity_type, "entity_id": a.entity_id, "scope": "shipment_audit"}
            for a in audits
        ],
    }


def _milestone_target(
    shipment_id: int, milestone_id: int, user: dict[str, Any], permission: str
):
    require_permission(user, permission)
    shipment = scoped_shipment(shipment_id, user)
    plan = db.session.scalar(
        select(RoutePlan.id).where(
            RoutePlan.operational_shipment_id == shipment.id,
            RoutePlan.is_active.is_(True),
        )
    )
    leg_ids = select(RouteLeg.id).where(RouteLeg.route_plan_id == plan)
    milestone = db.session.scalar(
        select(Milestone)
        .where(Milestone.id == milestone_id, Milestone.route_leg_id.in_(leg_ids))
        .with_for_update()
    )
    if milestone is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Milestone was not found.", 404)
    return shipment, milestone


@atomic_command
def record_event(
    shipment_id: int, milestone_id: int, payload: dict, user: dict, key: str
) -> MilestoneEvent:
    _require_idempotency_key(key)
    shipment, milestone = _milestone_target(
        shipment_id, milestone_id, user, "milestone_event.create"
    )
    existing = db.session.scalar(
        select(MilestoneEvent).where(
            MilestoneEvent.milestone_id == milestone.id,
            MilestoneEvent.idempotency_key == key,
        )
    )
    _reject_recorded_at(payload)
    occurred = _occurrence_time(payload.get("occurred_at"))
    event_hash = _hash({"occurred_at": occurred.isoformat(), "event_type": "reported"})
    if existing:
        if existing.request_hash != event_hash:
            raise OperationalError(
                "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD",
                "Idempotency key was reused with a different event payload.",
                409,
            )
        return existing
    from backend.services import occurrence_projection_service as projection
    projection.assert_new_root(milestone)
    projection.assert_leg_report_allowed(milestone, occurred)
    event = MilestoneEvent(
        organization_id=shipment.organization_id,
        milestone_id=milestone.id,
        event_type="reported",
        occurred_at=occurred,
        actor_user_id=user["id"],
        idempotency_key=key,
        request_hash=event_hash,
    )
    db.session.add(event)
    milestone.occurred_at = occurred
    milestone.projected_state = "reported"
    milestone.verification_state = "reported"
    milestone.version += 1
    _audit(
        shipment.organization_id,
        user["id"],
        "milestone.reported",
        "Milestone",
        milestone.id,
    )
    _outbox(shipment.organization_id, "milestone.reported", "Milestone", milestone.id)
    projection.project(milestone)
    db.session.commit()
    return event


@atomic_command
def verify_milestone(
    shipment_id: int, milestone_id: int, expected_version: int, user: dict
) -> Milestone:
    shipment, milestone = _milestone_target(
        shipment_id, milestone_id, user, "milestone.verify"
    )
    replay = db.session.scalar(select(MilestoneEvent).where(
        MilestoneEvent.milestone_id == milestone.id,
        MilestoneEvent.idempotency_key == f"verify:{milestone.id}:{expected_version}",
    ))
    if replay and replay.actor_user_id == user["id"]:
        return milestone
    if milestone.version != expected_version:
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Milestone was changed by another operation.",
            409,
        )
    if milestone.verification_state != "reported" or milestone.occurred_at is None:
        raise OperationalError(
            "INVALID_MILESTONE_TRANSITION",
            "Only a reported milestone can be verified.",
            409,
        )
    from backend.services import occurrence_projection_service as projection
    latest_report = projection.effective_occurrence(milestone)
    if latest_report is None:
        raise OperationalError("INVALID_EVENT_TARGET", "No occurrence is available to verify.", 409)
    if latest_report and latest_report.actor_user_id == user["id"]:
        raise OperationalError(
            "FORBIDDEN_OPERATION",
            "The reporting actor cannot verify the same milestone event.",
            403,
        )
    event = MilestoneEvent(
        organization_id=shipment.organization_id,
        milestone_id=milestone.id,
        event_type="verified",
        related_event_id=latest_report.id,
        occurred_at=milestone.occurred_at,
        actor_user_id=user["id"],
        idempotency_key=f"verify:{milestone.id}:{expected_version}",
        request_hash=_hash(
            {"expected_version": expected_version, "event_type": "verified"}
        ),
    )
    db.session.add(event)
    milestone.verification_state = "verified"
    milestone.projected_state = "reported"
    milestone.version += 1
    for item in db.session.scalars(
        select(OperationalWorkItem).where(
            OperationalWorkItem.milestone_id == milestone.id,
            OperationalWorkItem.status == "open",
        )
    ).all():
        item.status = "resolved"
        item.resolved_at = utcnow()
        item.resolved_by_user_id = user["id"]
        item.version += 1
        _audit(
            shipment.organization_id,
            user["id"],
            "work_item.resolved",
            "OperationalWorkItem",
            item.id,
        )
        _outbox(
            shipment.organization_id,
            "work_item.resolved",
            "OperationalWorkItem",
            item.id,
        )
    _audit(
        shipment.organization_id,
        user["id"],
        "milestone.verified",
        "Milestone",
        milestone.id,
    )
    _outbox(shipment.organization_id, "milestone.verified", "Milestone", milestone.id)
    db.session.commit()
    return milestone


@atomic_command
def correct_milestone(
    shipment_id: int, milestone_id: int, payload: dict, user: dict, key: str
) -> MilestoneEvent:
    _require_idempotency_key(key)
    shipment, milestone = _milestone_target(
        shipment_id, milestone_id, user, "milestone.correct"
    )
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise OperationalError(
            "CORRECTION_REASON_REQUIRED", "Correction reason is required."
        )
    expected = payload.get("expected_version")
    _reject_recorded_at(payload)
    occurred = _occurrence_time(payload.get("occurred_at"))
    event_hash = _hash(
        {
            "occurred_at": occurred.isoformat(),
            "reason": reason,
            "expected_version": expected,
            "event_type": "corrected",
        }
    )
    existing = db.session.scalar(
        select(MilestoneEvent).where(
            MilestoneEvent.milestone_id == milestone.id,
            MilestoneEvent.idempotency_key == key,
        )
    )
    if existing:
        if existing.request_hash != event_hash:
            raise OperationalError(
                "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD",
                "Idempotency key was reused with a different event payload.",
                409,
            )
        return existing
    if milestone.version != expected:
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Milestone was changed by another operation.",
            409,
        )
    from backend.services import occurrence_projection_service as projection
    previous = projection.effective_occurrence(milestone)
    if previous is None:
        raise OperationalError(
            "INVALID_MILESTONE_TRANSITION", "There is no event to correct.", 409
        )
    event = MilestoneEvent(
        organization_id=shipment.organization_id,
        milestone_id=milestone.id,
        event_type="corrected",
        occurred_at=occurred,
        actor_user_id=user["id"],
        reason=reason,
        supersedes_event_id=previous.id,
        idempotency_key=key,
        request_hash=event_hash,
    )
    db.session.add(event)
    milestone.occurred_at = occurred
    milestone.verification_state = "reported"
    milestone.projected_state = "reported"
    milestone.version += 1
    _audit(
        shipment.organization_id,
        user["id"],
        "milestone.corrected",
        "Milestone",
        milestone.id,
        {"reason": reason},
    )
    _outbox(shipment.organization_id, "milestone.corrected", "Milestone", milestone.id)
    projection.project(milestone)
    db.session.commit()
    return event


def reconcile_overdue(
    user_id: int | None = None,
    organization_id: int | None = None,
    now: datetime | None = None,
) -> int:
    from backend.census_context import census_unit_of_work

    try:
        with census_unit_of_work(db.session):
            created = _reconcile_overdue_mutations(user_id, organization_id, now)
            db.session.commit()
            return created
    except Exception:
        db.session.rollback()
        raise


def _reconcile_overdue_mutations(
    user_id: int | None = None,
    organization_id: int | None = None,
    now: datetime | None = None,
) -> int:
    if organization_id is None:
        if user_id is None:
            raise OperationalError(
                "TENANT_SCOPE_VIOLATION", "An organization scope is required.", 403
            )
        organization_id = organization_for_user(user_id)
    if db.session.get_bind().dialect.name == "postgresql":
        db.session.execute(
            text("SELECT pg_advisory_xact_lock(74101, :organization_id)"),
            {"organization_id": organization_id},
        )
    actor = user_id or db.session.scalar(
        select(OperationalMembership.user_id).where(
            OperationalMembership.organization_id == organization_id,
            OperationalMembership.is_active.is_(True),
        )
    )
    current = now or utcnow()
    created = 0
    rows = db.session.execute(
        select(Milestone, OperationalShipment)
        .join(RouteLeg, Milestone.route_leg_id == RouteLeg.id)
        .join(RoutePlan, RouteLeg.route_plan_id == RoutePlan.id)
        .join(
            OperationalShipment,
            RoutePlan.operational_shipment_id == OperationalShipment.id,
        )
        .where(
            OperationalShipment.organization_id == organization_id,
            Milestone.planned_at < current,
            Milestone.verification_state != "verified",
        )
    ).all()
    for milestone, shipment in rows:
        exists = db.session.scalar(
            select(OperationalWorkItem.id).where(
                OperationalWorkItem.milestone_id == milestone.id,
                OperationalWorkItem.work_type == "OVERDUE_MILESTONE",
                OperationalWorkItem.status == "open",
            )
        )
        if exists:
            continue
        item = OperationalWorkItem(
            organization_id=organization_id,
            operational_shipment_id=shipment.id,
            milestone_id=milestone.id,
            due_at=milestone.planned_at,
            reason="Milestone is overdue and not verified.",
        )
        db.session.add(item)
        db.session.flush()
        created += 1
        _audit(
            organization_id, actor, "work_item.opened", "OperationalWorkItem", item.id
        )
        _outbox(organization_id, "work_item.opened", "OperationalWorkItem", item.id)
    return created


def resolve_work_item(
    item_id: int, expected_version: int, user: dict
) -> OperationalWorkItem:
    require_permission(user, "work_item.manage")
    org = organization_for_user(user["id"])
    item = db.session.scalar(
        select(OperationalWorkItem)
        .where(
            OperationalWorkItem.id == item_id,
            OperationalWorkItem.organization_id == org,
        )
        .with_for_update()
    )
    if item is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Work item was not found.", 404)
    scoped_shipment(item.operational_shipment_id, user)
    if item.work_type == "FOLLOW_UP":
        raise OperationalError(
            "ACTION_RESULT_REQUIRED",
            "Operational Actions must be resolved through the Action result command.",
            422,
        )
    if item.status == "resolved":
        raise OperationalError(
            "WORK_ITEM_ALREADY_RESOLVED", "Work item is already resolved.", 409
        )
    if item.version != expected_version:
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Work item was changed by another operation.",
            409,
        )
    item.status = "resolved"
    item.version += 1
    item.resolved_at = utcnow()
    item.resolved_by_user_id = user["id"]
    _audit(org, user["id"], "work_item.resolved", "OperationalWorkItem", item.id)
    _outbox(org, "work_item.resolved", "OperationalWorkItem", item.id)
    db.session.commit()
    return item
