"""Fail-closed, bounded authority for the isolated Control Tower read model.

The boundary derives every tenant, persona and responsibility fact from current
Golden persistence. It grants no source capability and returns only lineage
needed by the Control Tower projection. Candidate and revalidation queries are
batched so request/owner authorization does not become an N+1 read.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import logging
from typing import ClassVar, Iterable

from sqlalchemy import or_, select

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
)
from backend.services.assigned_work_authorization import (
    EXPERT,
    ORGANIZATION_ADMIN,
    PLATFORM_ADMIN,
    _actor_id,
    _authority,
    _has_capability,
    _membership,
    assigned_shipment_scope,
)

_logger = logging.getLogger("authorization.control_tower")
_ELIGIBLE = ("planned", "in_progress")
MAX_SUMMARY_SHIPMENTS = 100


class ControlTowerScopeDenied(Exception):
    """Opaque authorization failure; no resource/foreign identity disclosure."""

    def __init__(self):
        super().__init__("Control Tower summary authority is unavailable.")


class ControlTowerResponsibilityInvariant(Exception):
    """Responsibility could not be certified; partial disclosure is forbidden."""

    def __init__(self):
        super().__init__("Control Tower responsibility invariant failed.")


class ControlTowerPopulationLimit(Exception):
    """The bounded read cannot safely evaluate the full authorized population."""

    def __init__(self):
        super().__init__("Control Tower population exceeds the bounded evaluator.")


@dataclass(frozen=True)
class SummaryAuthorityContext:
    purpose: ClassVar[str] = "CONTROL_TOWER_V1_OPERATIONAL_SUMMARY"
    policy: ClassVar[str] = "GOLDEN_CONTROL_TOWER_D1"
    shipment_id: int
    shipment_public_id: str
    organization_id: int
    root_type: str
    root_id: int
    responsible_expert_id: int
    responsible_expert_name: str
    actor_id: int
    actor_persona: str


def _current_actor(actor: dict):
    user_id = _actor_id(actor)
    user = (
        db.session.scalar(
            select(ExpertUser)
            .where(ExpertUser.id == user_id)
            .execution_options(populate_existing=True)
        )
        if user_id is not None
        else None
    )
    if user is None or not user.is_active:
        raise ControlTowerScopeDenied()
    persona = _authority(user)
    if persona == PLATFORM_ADMIN:
        raise ControlTowerScopeDenied()
    if (user.authority or "").upper() not in {EXPERT, ORGANIZATION_ADMIN}:
        raise ControlTowerScopeDenied()
    membership = _membership(user.id)
    if membership is None or not _has_capability(
        membership, "operational_shipment.read"
    ):
        raise ControlTowerScopeDenied()
    return user.id, persona, membership.organization_id


def _candidate_query(actor_id: int, persona: str, organization_id: int):
    query = select(OperationalShipment).where(
        OperationalShipment.organization_id == organization_id,
        OperationalShipment.lifecycle_status.in_(_ELIGIBLE),
        assigned_shipment_scope({"id": actor_id}),
    )
    if persona == EXPERT:
        assigned_requests = select(ShipmentRequest.id).where(
            ShipmentRequest.operational_organization_id == organization_id,
            ShipmentRequest.ownership_scope == "TENANT",
            ShipmentRequest.assigned_to == actor_id,
        )
        query = query.where(
            or_(
                (OperationalShipment.source_type == "accepted_quote")
                & OperationalShipment.shipment_request_id.in_(assigned_requests),
                (OperationalShipment.source_type == "direct")
                & (OperationalShipment.primary_responsible_expert_id == actor_id),
            )
        )
    return query.execution_options(populate_existing=True)


def _invariant(shipment: OperationalShipment, reason: str):
    _logger.error(
        "control_tower_responsibility_invariant organization_id=%s shipment_id=%s reason=%s",
        shipment.organization_id,
        shipment.id,
        reason,
    )
    raise ControlTowerResponsibilityInvariant()


def _contexts_for_rows(
    rows: Iterable[OperationalShipment], actor_id: int, persona: str
) -> tuple[SummaryAuthorityContext, ...]:
    rows = tuple(rows)
    request_ids = {
        row.shipment_request_id
        for row in rows
        if row.source_type == "accepted_quote" and row.shipment_request_id is not None
    }
    requests = (
        {
            row.id: row
            for row in db.session.scalars(
                select(ShipmentRequest)
                .where(ShipmentRequest.id.in_(request_ids))
                .execution_options(populate_existing=True)
            ).all()
        }
        if request_ids
        else {}
    )

    responsibility = {}
    for shipment in rows:
        if shipment.source_type == "accepted_quote":
            request = requests.get(shipment.shipment_request_id)
            if (
                request is None
                or request.operational_organization_id != shipment.organization_id
                or request.ownership_scope != "TENANT"
            ):
                _invariant(shipment, "INVALID_REQUEST_ROOT")
            responsibility[shipment.id] = (
                request.assigned_to,
                "ShipmentRequest",
                request.id,
            )
        elif shipment.source_type == "direct":
            responsibility[shipment.id] = (
                shipment.primary_responsible_expert_id,
                "OperationalShipment",
                shipment.id,
            )
        else:
            _invariant(shipment, "INVALID_RESPONSIBILITY_ROOT")

    owner_ids = {value[0] for value in responsibility.values() if value[0] is not None}
    owners = (
        {
            row.id: row
            for row in db.session.scalars(
                select(ExpertUser)
                .where(ExpertUser.id.in_(owner_ids))
                .execution_options(populate_existing=True)
            ).all()
        }
        if owner_ids
        else {}
    )
    memberships = defaultdict(list)
    if owner_ids:
        for member in db.session.scalars(
            select(OperationalMembership)
            .join(
                OperationalOrganization,
                OperationalOrganization.id == OperationalMembership.organization_id,
            )
            .where(
                OperationalMembership.user_id.in_(owner_ids),
                OperationalMembership.is_active.is_(True),
                OperationalOrganization.is_active.is_(True),
            )
            .execution_options(populate_existing=True)
        ).all():
            memberships[member.user_id].append(member)

    result = []
    for shipment in rows:
        responsible_id, root_type, root_id = responsibility[shipment.id]
        if persona == EXPERT and responsible_id != actor_id:
            continue
        if responsible_id is None:
            _invariant(shipment, "MISSING_RESPONSIBLE_EXPERT")
        responsible = owners.get(responsible_id)
        if (
            responsible is None
            or not responsible.is_active
            or (responsible.authority or "").upper() != EXPERT
        ):
            _invariant(shipment, "INVALID_RESPONSIBLE_EXPERT")
        owner_memberships = memberships.get(responsible.id, [])
        if (
            len(owner_memberships) != 1
            or owner_memberships[0].organization_id != shipment.organization_id
        ):
            _invariant(shipment, "INVALID_RESPONSIBLE_MEMBERSHIP")
        result.append(
            SummaryAuthorityContext(
                shipment.id,
                shipment.public_id,
                shipment.organization_id,
                root_type,
                root_id,
                responsible.id,
                responsible.full_name,
                actor_id,
                persona,
            )
        )
    return tuple(result)


def governed_summary_scope(actor: dict) -> tuple[SummaryAuthorityContext, ...]:
    """Return at most the complete bounded authorized active population."""
    with db.session.no_autoflush:
        actor_id, persona, organization_id = _current_actor(actor)
        rows = db.session.scalars(
            _candidate_query(actor_id, persona, organization_id)
            .order_by(
                OperationalShipment.created_at.desc(),
                OperationalShipment.public_id.asc(),
            )
            .limit(MAX_SUMMARY_SHIPMENTS + 1)
        ).all()
        if len(rows) > MAX_SUMMARY_SHIPMENTS:
            _logger.error(
                "control_tower_population_limit organization_id=%s limit=%s",
                organization_id,
                MAX_SUMMARY_SHIPMENTS,
            )
            raise ControlTowerPopulationLimit()
        return _contexts_for_rows(rows, actor_id, persona)


def refresh_summary_contexts(
    actor: dict, contexts: Iterable[SummaryAuthorityContext]
) -> tuple[SummaryAuthorityContext, ...]:
    """Re-establish a retained bounded set using batched current persistence."""
    with db.session.no_autoflush:
        contexts = tuple(contexts)
        actor_id, persona, organization_id = _current_actor(actor)
        if any(context.actor_id != actor_id for context in contexts):
            raise ControlTowerScopeDenied()
        if not contexts:
            return ()
        ids = tuple(context.shipment_id for context in contexts)
        rows = db.session.scalars(
            _candidate_query(actor_id, persona, organization_id).where(
                OperationalShipment.id.in_(ids)
            )
        ).all()
        if len(rows) != len(set(ids)):
            raise ControlTowerScopeDenied()
        fresh_by_id = {
            context.shipment_id: context
            for context in _contexts_for_rows(rows, actor_id, persona)
        }
        if set(fresh_by_id) != set(ids):
            raise ControlTowerScopeDenied()
        return tuple(fresh_by_id[context.shipment_id] for context in contexts)


def refresh_summary_context(
    actor: dict, context: SummaryAuthorityContext
) -> SummaryAuthorityContext:
    """Compatibility wrapper for source-specific single-context checks."""
    return refresh_summary_contexts(actor, (context,))[0]
