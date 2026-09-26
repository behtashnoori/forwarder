"""Slice 3 internal, immutable Shipment summary; no endpoint or source truth.

The caller owns the read transaction. Discovery precedes every source read;
Slice 2 revalidates each adapter, and this composer revalidates the full scope
before disclosure. Never invoke source producers, serializers or write helpers.
Pagination is a current query-time view rather than a historical snapshot.
Population-global metadata comes from the same authorized relational attention
query; only the selected page is hydrated into presentation rows.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging

from flask import current_app
from sqlalchemy import select

from backend.extensions import db
from backend.models import ShipmentRequest
from backend.operational_models import OperationalShipment, RouteLeg, RoutePlan, utcnow
from backend.services import control_tower_sources as sources
from backend.services.attention_truth_contract import build_attention_truth_contract
from backend.services.control_tower_query import select_attention_window
from backend.services.control_tower_scope import (
    ControlTowerResponsibilityInvariant, ControlTowerScopeDenied,
    governed_summary_contexts, governed_summary_scope, refresh_summary_contexts,
)
from backend.services.control_tower_translation import (
    AttentionLevel, EMPTY_MESSAGE, UNAVAILABLE_MESSAGE, attention_label,
    safe_display_label, transport_modes_label, utc,
)
from backend.services.request_transport_projection import project_existing_request_transport
from backend.services.tracking_projection_service import project_operational_shipments

_logger = logging.getLogger("control_tower.composition")
_LEVEL = {AttentionLevel.URGENT: 0, AttentionLevel.FOLLOW_UP: 1, AttentionLevel.REVIEW: 2}
_ORDINAL = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_LAST = datetime.max.replace(tzinfo=timezone.utc)
_ONSET = {"delay_start", "exception_occurrence", "work_open"}


class ControlTowerCursorInvalid(Exception):
    def __init__(self):
        super().__init__("Control Tower continuation is invalid; restart the read.")


@dataclass(frozen=True)
class DisplayTime:
    label: str
    at: datetime


@dataclass(frozen=True)
class DisplayReason:
    semantic: str
    attention: str
    attention_label: str
    title: str
    explanation: str
    time: tuple[DisplayTime, ...]
    truth: dict | None = None


@dataclass(frozen=True)
class ShipmentAttentionItem:
    shipment_reference: str
    route_label: str | None
    transport_label: str | None
    attention: str
    attention_label: str
    owner_name: str
    operational_status: str
    source: dict
    request_transport: dict | None
    actual_route_modes: tuple[str, ...]
    progress: dict
    work_summary: dict
    primary_reason: DisplayReason
    additional_reasons: tuple[DisplayReason, ...]
    destination: str


@dataclass(frozen=True)
class Page:
    limit: int = 25
    offset: int = 0
    returned: int = 0
    has_more: bool = False
    next_cursor: str | None = None


@dataclass(frozen=True)
class Summary:
    total: int = 0
    attention_counts: dict[str, int] | None = None


@dataclass(frozen=True)
class ControlTowerReadModel:
    evaluated_at: datetime
    state: str
    items: tuple[ShipmentAttentionItem, ...] = ()
    page: Page = Page()
    summary: Summary = Summary()
    empty_message: str | None = None
    notice: str | None = None


def _identity(reason):
    identity = reason.source_identity
    return identity.family, identity.key, repr(identity.linkage)


def _due(reason):
    return min((utc(t.at) for t in reason.time_context
                if t.kind == "expected_due" and utc(t.at)), default=None)


def _onset(reason):
    # Readiness evaluated_at is observation time, never condition age.
    return min((utc(t.at) for t in reason.time_context
                if t.kind in _ONSET and utc(t.at)), default=None)


def _time_order(reason, at):
    due = _due(reason)
    return (0 if due and due < at else 1 if due else 2,
            due or _LAST, _onset(reason) or _LAST, _identity(reason))


def _deduplicate(reasons):
    chosen = {}
    for reason in reasons:
        identity = reason.source_identity
        # Slice 2 verified OIP is already enrichment on its base reason. Only
        # same-model proven work dimensions can merge different base records.
        if identity.family == "OperationalWorkItem" and len(identity.linkage) == 4:
            kind, plan, checkpoint, milestone = identity.linkage
            key = (identity.family, kind, milestone) if kind == "OVERDUE_MILESTONE" else (
                identity.family, kind, plan, checkpoint)
        else:
            key = identity.family, identity.key, identity.linkage
        previous = chosen.get(key)
        occurrence = lambda r: (_onset(r) or datetime.min.replace(tzinfo=timezone.utc),
                                r.source_identity.version, _identity(r))
        if previous is None or occurrence(reason) > occurrence(previous):
            chosen[key] = reason
    return tuple(chosen.values())


def _cohort(reason):
    # Never normalize unrelated urgency/severity models into one ranking.
    if reason.enrichment:
        policies = {(e.policy_id, e.policy_version) for e in reason.enrichment}
        if len(policies) != 1:
            return None, ()
        policy, version = next(iter(policies))
        rank = max((_ORDINAL[e.urgency], _ORDINAL[e.severity]) for e in reason.enrichment)
        return ("oip", policy, version), rank
    identity = reason.source_identity
    if identity.family == "OperationalWorkItem" and identity.linkage and reason.source_severity:
        return ("work", identity.linkage[0]), (reason.source_severity == "critical",)
    return None, ()


def _ordered_reasons(reasons, at):
    remaining, ordered = list(_deduplicate(reasons)), []
    while remaining:
        level = min(_LEVEL[r.attention_level] for r in remaining)
        candidates = [r for r in remaining if _LEVEL[r.attention_level] == level]
        best = {}
        for reason in candidates:
            cohort, rank = _cohort(reason)
            if cohort is not None:
                best[cohort] = max(best.get(cohort, rank), rank)
        survivors = [r for r in candidates
                     if _cohort(r)[0] is None or _cohort(r)[1] == best[_cohort(r)[0]]]
        selected = min(survivors, key=lambda r: _time_order(r, at))
        ordered.append(selected)
        remaining.remove(selected)
    return tuple(ordered)


def _display(reason, shipment_public_id):
    contracts = {}
    for value in reason.enrichment:
        if not (
            value.situation_identity_key
            and value.source_watermark
            and value.calculated_at
            and value.priority
        ):
            continue
        contract = build_attention_truth_contract(
            shipment_public_id=shipment_public_id,
            situation_identity_key=value.situation_identity_key,
            policy_id=value.policy_id,
            policy_version=value.policy_version,
            source_watermark=value.source_watermark,
            calculated_at=value.calculated_at,
            urgency=value.urgency,
            severity=value.severity,
            priority=value.priority,
        )
        contracts[contract["fingerprint"]] = contract
    truth = next(iter(contracts.values())) if len(contracts) == 1 else None
    return DisplayReason(
        reason.semantic.value,
        reason.attention_level.value.lower(),
        attention_label(reason.attention_level),
        reason.title,
        reason.explanation,
        tuple(DisplayTime(t.label, utc(t.at)) for t in reason.time_context if utc(t.at)),
        truth,
    )


def _route_context(contexts):
    """Two batched queries bounded by the already-governed Shipment IDs.

    Use only safe persisted snapshots on the active plan, without consulting
    historical geography or free text. Broken chains supply no route/transport;
    unknown or operational-only modes supply no transport label.
    """
    ids = tuple(c.shipment_id for c in contexts)
    if not ids:
        return {}
    plans = db.session.scalars(select(RoutePlan).where(
        RoutePlan.operational_shipment_id.in_(ids), RoutePlan.is_active.is_(True),
        RoutePlan.status == "active",
    ).execution_options(populate_existing=True)).all()
    plan_ids = tuple(p.id for p in plans)
    if not plan_ids:
        return {}
    legs = db.session.scalars(select(RouteLeg).where(
        RouteLeg.route_plan_id.in_(plan_ids), RouteLeg.status != "cancelled",
    ).order_by(RouteLeg.sequence_number).execution_options(populate_existing=True)).all()
    grouped = {}
    for leg in legs:
        grouped.setdefault(leg.route_plan_id, []).append(leg)
    result = {}
    for plan in plans:
        chain = grouped.get(plan.id, [])
        route, mode, actual_modes = None, None, tuple(
            leg.transport_mode for leg in chain
        )
        if chain:
            continuous = all(a.destination_location_id == b.origin_location_id
                             for a, b in zip(chain, chain[1:]))
            origin = chain[0].origin_snapshot
            destination = chain[-1].destination_snapshot
            start = safe_display_label(origin.get("display_name")) if isinstance(origin, dict) else None
            end = safe_display_label(destination.get("display_name")) if isinstance(destination, dict) else None
            if continuous and start and end:
                route = f"{start} → {end}"
                mode = transport_modes_label(leg.transport_mode for leg in chain)
        result[plan.operational_shipment_id] = {
            "route_label": route,
            "transport_label": mode,
            "actual_modes": actual_modes,
        }
    return result


def _shipment_context(contexts):
    """Batch safe identity, request-intent and canonical tracking projections."""
    ids = tuple(context.shipment_id for context in contexts)
    if not ids:
        return {}
    organizations = {context.organization_id for context in contexts}
    if len(organizations) != 1:
        raise ControlTowerScopeDenied()
    organization_id, = organizations
    shipments = {
        row.id: row
        for row in db.session.scalars(
            select(OperationalShipment).where(
                OperationalShipment.id.in_(ids),
                OperationalShipment.organization_id == organization_id,
            )
        ).all()
    }
    if set(shipments) != set(ids):
        raise ControlTowerScopeDenied()
    request_ids = {
        row.shipment_request_id
        for row in shipments.values()
        if row.shipment_request_id is not None
    }
    requests = {
        row.id: row
        for row in db.session.scalars(
            select(ShipmentRequest).where(
                ShipmentRequest.id.in_(request_ids),
                ShipmentRequest.operational_organization_id == organization_id,
                ShipmentRequest.ownership_scope == "TENANT",
            )
        ).all()
    } if request_ids else {}
    tracking = project_operational_shipments(organization_id, ids)
    result = {}
    for shipment_id, shipment in shipments.items():
        request_row = requests.get(shipment.shipment_request_id)
        if shipment.source_type == "accepted_quote" and request_row is None:
            raise ControlTowerScopeDenied()
        request_transport = None
        request_public_id = None
        if request_row is not None:
            projected = project_existing_request_transport(request_row)
            request_public_id = request_row.public_id
            request_transport = {
                "shippingType": request_row.shipping_type,
                "transportMethod": projected["transport_method"],
                "internationalTransportMethod": projected[
                    "international_transport_method"
                ],
                "domesticTransportMethod": projected["domestic_transport_method"],
                "transportMethodPreference": projected[
                    "transport_method_preference"
                ],
            }
        tracking_row = tracking.get(shipment_id) or {
            "current_location": None,
            "location_state": "UNAVAILABLE",
            "unit_count": 0,
            "latest_event_at": None,
            "latest_event_type": None,
            "source": "unavailable",
            "projection_state": "unavailable",
            "units": [],
        }
        latest_unit = max(
            (unit for unit in tracking_row["units"] if unit["latest_event_at"]),
            key=lambda unit: (
                unit["latest_event_at"],
                unit["latest_event_recorded_at"],
            ),
            default=None,
        )
        result[shipment_id] = {
            "status": shipment.lifecycle_status,
            "source": {
                "type": shipment.source_type,
                "requestPublicId": request_public_id,
            },
            "request_transport": request_transport,
            "progress": {
                "currentLocation": tracking_row["current_location"],
                "locationState": tracking_row["location_state"],
                "unitCount": tracking_row["unit_count"],
                "latestEventOccurredAt": (
                    latest_unit["latest_event_at"] if latest_unit else None
                ),
                "latestEventRecordedAt": (
                    latest_unit["latest_event_recorded_at"] if latest_unit else None
                ),
                "latestEventType": tracking_row["latest_event_type"],
                "source": tracking_row["source"],
                "projectionState": tracking_row["projection_state"],
            },
        }
    return result


def _shipment_order(reasons, reference, at):
    # Authoritative product contract F.8: sorting uses highest-level reasons'
    # earliest valid due and oldest onset. A severity-selected primary may have
    # a different due; display times stay attached to their own reason.
    level = reasons[0].attention_level
    same = [r for r in reasons if r.attention_level == level]
    due = min((_due(r) for r in same if _due(r)), default=None)
    onset = min((_onset(r) for r in same if _onset(r)), default=None)
    return (_LEVEL[level], 0 if due and due < at else 1 if due else 2,
            due or _LAST, onset or _LAST, reference)


def _signature(payload):
    return hmac.new(str(current_app.config["SECRET_KEY"]).encode(), payload, hashlib.sha256).digest()


def _cursor(offset, actor_id, page_size, attention, search):
    payload = json.dumps(
        ["control-tower-window-v2", offset, actor_id, page_size, attention, search],
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(_signature(payload) + payload).decode().rstrip("=")


def _offset(cursor, actor_id, page_size, attention, search):
    if cursor is None:
        return 0
    try:
        if not isinstance(cursor, str) or len(cursor) > 512:
            raise ValueError()
        raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        signature, payload = raw[:32], raw[32:]
        version, offset, expected_actor, expected_size, expected_attention, expected_search = json.loads(payload)
        if (not hmac.compare_digest(signature, _signature(payload))
                or version != "control-tower-window-v2"
                or expected_actor != actor_id
                or expected_size != page_size
                or expected_attention != attention
                or expected_search != search
                or type(offset) is not int or offset <= 0 or offset % page_size):
            raise ValueError()
        return offset
    except (ValueError, TypeError, UnicodeError):
        raise ControlTowerCursorInvalid() from None


def _compatibility_read(
    actor, *, evaluated_at, page_size, cursor, attention, search
):
    """Non-PostgreSQL test/development parity path.

    PostgreSQL is the governed release engine and uses the relational window.
    SQLite cannot plan the production CTE acceptably; it retains a no-ceiling
    complete evaluator so the repository's broad compatibility suite remains
    useful without becoming release-scale performance evidence.
    """
    actor_id = int(actor.get("id"))
    offset = _offset(cursor, actor_id, page_size, attention, search)
    with db.session.no_autoflush:
        try:
            contexts = governed_summary_scope(actor)
            current = refresh_summary_contexts(actor, contexts)
            ranked = []
            evaluated = sources.evaluate_bounded_sources(
                actor, current, at=evaluated_at
            )
            for context, reasons in evaluated:
                ordered = _ordered_reasons(reasons, evaluated_at)
                if ordered:
                    ranked.append((
                        _shipment_order(
                            ordered, context.shipment_public_id, evaluated_at
                        ),
                        context,
                        ordered,
                    ))
            if refresh_summary_contexts(actor, current) != current:
                raise ControlTowerScopeDenied()
            routes = _route_context(current)
            facts = _shipment_context(current)
            rows = []
            for key, context, ordered in ranked:
                level = ordered[0].attention_level
                route = routes.get(context.shipment_id, {
                    "route_label": None,
                    "transport_label": None,
                    "actual_modes": (),
                })
                fact = facts[context.shipment_id]
                rows.append((key, ShipmentAttentionItem(
                    context.shipment_public_id,
                    route["route_label"],
                    route["transport_label"],
                    level.value.lower(),
                    attention_label(level),
                    context.responsible_expert_name,
                    fact["status"],
                    fact["source"],
                    fact["request_transport"],
                    route["actual_modes"],
                    fact["progress"],
                    {"reasonCount": len(ordered), "openAttention": True},
                    _display(ordered[0], context.shipment_public_id),
                    tuple(_display(reason, context.shipment_public_id) for reason in ordered[1:]),
                    f"/operations/shipments/{context.shipment_public_id}",
                )))
            if refresh_summary_contexts(actor, current) != current:
                raise ControlTowerScopeDenied()
            if frozenset(governed_summary_scope(actor)) != frozenset(contexts):
                raise ControlTowerScopeDenied()
        except (ControlTowerScopeDenied, ControlTowerResponsibilityInvariant):
            raise
        except Exception as exc:
            _logger.error(
                "control_tower_composition_unavailable error_type=%s",
                type(exc).__name__,
            )
            return ControlTowerReadModel(
                evaluated_at, "unavailable", notice=UNAVAILABLE_MESSAGE
            )
    rows.sort(key=lambda row: row[0])
    if search:
        needle = search.casefold()
        rows = [
            row for row in rows
            if needle in row[1].shipment_reference.casefold()
            or needle in (row[1].owner_name or "").casefold()
            or needle in (row[1].source.get("requestPublicId") or "").casefold()
        ]
    counts = {
        level: sum(item.attention == level for _, item in rows)
        for level in ("urgent", "follow_up", "review")
    }
    if attention is not None:
        rows = [row for row in rows if row[1].attention == attention]
    total = len(rows)
    page_rows = rows[offset:offset + page_size]
    has_more = offset + len(page_rows) < total
    next_cursor = (
        _cursor(offset + len(page_rows), actor_id, page_size, attention, search)
        if has_more
        else None
    )
    return ControlTowerReadModel(
        evaluated_at,
        "complete",
        tuple(item for _, item in page_rows),
        Page(page_size, offset, len(page_rows), has_more, next_cursor),
        Summary(total, counts),
        EMPTY_MESSAGE if total == 0 else None,
    )


def compose_control_tower(
    actor, *, page_size=25, cursor=None, at=None, attention=None, search=None
):
    """Build only the ADR-046 read model. Denial/invariant/cursor errors raise.

    Genuine source/system failure returns unavailable with zero disclosed
    items, no continuation and no empty message. No partial-success response.
    """
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError("Control Tower page size must be between 1 and 100.")
    if attention is not None and attention not in {"urgent", "follow_up", "review"}:
        raise ValueError("Invalid attention filter.")
    if search is not None and not isinstance(search, str):
        raise ValueError("Invalid Control Tower search.")
    search = " ".join((search or "").split()) or None
    if search is not None and len(search) > 100:
        raise ValueError("Control Tower search is too long.")
    evaluated_at = utc(at or utcnow())
    if evaluated_at is None:
        raise ValueError("Control Tower requires a valid evaluation time.")
    actor_id = int(actor.get("id"))
    if db.session.get_bind().dialect.name != "postgresql":
        return _compatibility_read(
            actor,
            evaluated_at=evaluated_at,
            page_size=page_size,
            cursor=cursor,
            attention=attention,
            search=search,
        )
    with db.session.no_autoflush:
        try:
            offset = _offset(cursor, actor_id, page_size, attention, search)
            window = select_attention_window(
                actor,
                at=evaluated_at,
                page_size=page_size,
                offset=offset,
                attention=attention,
                search=search,
            )
            contexts = governed_summary_contexts(
                actor, (row.shipment_id for row in window.rows)
            )
            current = refresh_summary_contexts(actor, contexts)
            ranked = []
            for context, reasons in sources.evaluate_bounded_sources(actor, current, at=evaluated_at):
                ordered = _ordered_reasons(reasons, evaluated_at)
                if not ordered:
                    continue
                ranked.append(
                    (
                        _shipment_order(
                            ordered, context.shipment_public_id, evaluated_at
                        ),
                        context,
                        ordered,
                    )
                )
            # Later evaluations may have revoked authority over earlier rows.
            # Revalidate the selected bounded set before reading route context.
            if refresh_summary_contexts(actor, current) != current:
                raise ControlTowerScopeDenied()
            routes = _route_context(current)
            facts = _shipment_context(current)
            rows = []
            for key, context, ordered in ranked:
                level = ordered[0].attention_level
                route = routes.get(
                    context.shipment_id,
                    {
                        "route_label": None,
                        "transport_label": None,
                        "actual_modes": (),
                    },
                )
                fact = facts[context.shipment_id]
                item = ShipmentAttentionItem(
                    context.shipment_public_id,
                    route["route_label"],
                    route["transport_label"],
                    level.value.lower(),
                    attention_label(level),
                    context.responsible_expert_name,
                    fact["status"],
                    fact["source"],
                    fact["request_transport"],
                    route["actual_modes"],
                    fact["progress"],
                    {
                        "reasonCount": len(ordered),
                        "openAttention": True,
                    },
                    _display(ordered[0], context.shipment_public_id),
                    tuple(_display(reason, context.shipment_public_id) for reason in ordered[1:]),
                    f"/operations/shipments/{context.shipment_public_id}",
                )
                rows.append((key, item))
            # Also recheck selected cards and the actor when the page is empty.
            if refresh_summary_contexts(actor, current) != current:
                raise ControlTowerScopeDenied()
        except (ControlTowerScopeDenied, ControlTowerResponsibilityInvariant):
            raise
        except Exception as exc:
            _logger.error("control_tower_composition_unavailable error_type=%s", type(exc).__name__)
            return ControlTowerReadModel(evaluated_at, "unavailable", notice=UNAVAILABLE_MESSAGE)
        rows.sort(key=lambda row: row[0])
        expected = tuple((row.shipment_public_id, row.attention) for row in window.rows)
        actual = tuple((item.shipment_reference, item.attention) for _, item in rows)
        if actual != expected:
            _logger.error("control_tower_relational_detail_mismatch")
            return ControlTowerReadModel(
                evaluated_at, "unavailable", notice=UNAVAILABLE_MESSAGE
            )
        next_offset = offset + len(rows)
        next_cursor = (
            _cursor(next_offset, actor_id, page_size, attention, search)
            if window.has_more
            else None
        )
        return ControlTowerReadModel(
            evaluated_at,
            "complete",
            tuple(item for _, item in rows),
            Page(page_size, offset, len(rows), window.has_more, next_cursor),
            Summary(window.total, window.attention_counts),
            EMPTY_MESSAGE if window.total == 0 else None,
        )
