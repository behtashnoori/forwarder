"""Owner commands and deliberately separate, allowlisted report projections."""
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import func, select

from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem, ExecutionUnitCargoAllocation
from backend.models import Customer, ExpertUser
from backend.operational_models import (ExecutionTransportRevision, ExecutionUnit, OperationalEvent,
    OperationalIdempotency, OperationalShipment, RouteCargoDestination, RouteLeg, RoutePlan, RouteStageExecution)
from backend.reported_fact_models import (OperationalEventCargoImpact as Impact,
    OperationalEventReportContext as Context, REPORTED_EVENT_TYPE, SOURCES, KINDS, SCOPES)
from backend.services.assigned_work_authorization import authorize_document_management
from backend.services.customer_entitlement_service import authorized_customer_ids
from backend.services.execution_unit_service import _event_location_evidence
from backend.services.legacy_datetime import serialize_legacy_utc_datetime as iso
from backend.services.operational_service import OperationalError, require_permission, scoped_shipment

GENERIC_MESSAGE = "در روند حمل این محموله یک تغییر عملیاتی ثبت شده است."
DELAY_MESSAGE = "به دلیل شرایط عملیاتی، حرکت محموله با تأخیر مواجه شده است."
FIELDS = {"scope", "target_public_id", "kind", "source", "occurred_at", "location",
          "internal_note", "customer_message", "impacted_cargo_public_ids", "customer_effect",
          "corrects_public_id", "reason"}


def fail(message, status=422, code="REPORT_INVALID"):
    raise OperationalError(code, message, status)


def text(value, limit):
    if value is None:
        return None
    if not isinstance(value, str) or len(value.strip()) > limit:
        fail("متن گزارش معتبر نیست.")
    return value.strip() or None


def instant(value):
    if not isinstance(value, str):
        fail("زمان وقوع با منطقه زمانی لازم است.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail("زمان وقوع معتبر نیست.")
    if result.tzinfo is None:
        fail("منطقه زمانی وقوع لازم است.")
    return result.astimezone(timezone.utc)


def _can_manage(user, shipment):
    try:
        require_permission(user, "operational_shipment.create")
        return authorize_document_management(user, shipment).allowed
    except OperationalError:
        return False


def _contexts(shipment):
    return select(Context).join(OperationalEvent, OperationalEvent.id == Context.operational_event_id).where(
        Context.operational_shipment_id == shipment.id, Context.organization_id == shipment.organization_id,
        OperationalEvent.event_type == REPORTED_EVENT_TYPE)


def _target(shipment, scope, identity):
    values = {"route_plan_id": None, "route_leg_id": None, "execution_unit_id": None, "cargo_item_id": None}
    if scope == "SHIPMENT":
        if identity not in (None, "", shipment.public_id):
            fail("دامنه پرونده حمل معتبر نیست.")
        return values
    if not isinstance(identity, str) or not identity:
        fail("بخش حمل را انتخاب کنید.")
    row = None
    if scope == "CARGO":
        row = db.session.scalar(select(ShipmentCargoItem).where(
            ShipmentCargoItem.public_id == identity, ShipmentCargoItem.operational_shipment_id == shipment.id))
        if row: values["cargo_item_id"] = row.id
    elif scope == "EXECUTION_UNIT":
        row = db.session.scalar(select(ExecutionUnit).where(ExecutionUnit.public_id == identity,
            ExecutionUnit.organization_id == shipment.organization_id,
            select(RouteStageExecution.id).where(RouteStageExecution.execution_unit_id == ExecutionUnit.id,
                RouteStageExecution.operational_shipment_id == shipment.id,
                RouteStageExecution.organization_id == shipment.organization_id).exists()))
        if row: values["execution_unit_id"] = row.id
    elif scope == "ROUTE_STAGE":
        if identity.isdecimal():
            row = db.session.scalar(select(RouteLeg).join(RoutePlan).where(RouteLeg.id == int(identity),
                RoutePlan.operational_shipment_id == shipment.id))
        if row: values.update(route_plan_id=row.route_plan_id, route_leg_id=row.id)
    if row is None:
        fail("بخش حمل یافت نشد.", 404, "REPORT_TARGET_NOT_FOUND")
    return values


def create(shipment_public_id, user, payload, key):
    shipment = scoped_shipment(shipment_public_id, user)
    if not _can_manage(user, shipment):
        fail("فقط کارشناس مسئول می‌تواند گزارش ثبت کند.", 403, "REPORT_FORBIDDEN")
    shipment = db.session.scalar(select(OperationalShipment).where(OperationalShipment.id == shipment.id)
        .with_for_update().execution_options(populate_existing=True))
    if not _can_manage(user, shipment):
        fail("اختیار ثبت گزارش تغییر کرده است.", 403, "REPORT_FORBIDDEN")
    if not isinstance(payload, dict) or set(payload) - FIELDS:
        fail("اطلاعات گزارش معتبر نیست.")
    if not isinstance(key, str) or not key.strip() or len(key) > 100:
        fail("شناسه امن درخواست لازم است.")
    key = key.strip()
    fingerprint = hashlib.sha256(json.dumps({"actor": int(user["id"]), "payload": payload}, sort_keys=True).encode()).hexdigest()
    replay = db.session.scalar(select(OperationalIdempotency).where(
        OperationalIdempotency.organization_id == shipment.organization_id,
        OperationalIdempotency.operation == "record_reported_fact", OperationalIdempotency.resource_type == "shipment",
        OperationalIdempotency.command_resource_id == shipment.id, OperationalIdempotency.idempotency_key == key))
    if replay:
        if replay.request_hash != fingerprint:
            fail("شناسه درخواست برای گزارش دیگری استفاده شده است.", 409, "REPORT_REPLAY_CONFLICT")
        return db.session.get(Context, replay.result_resource_id), False
    scope, kind, source = payload.get("scope"), payload.get("kind"), payload.get("source")
    if (not isinstance(scope, str) or scope not in SCOPES or not isinstance(kind, str)
            or kind not in KINDS or not isinstance(source, str) or source not in SOURCES):
        fail("نوع، منبع و بخش گزارش را مشخص کنید.")
    targets = _target(shipment, scope, payload.get("target_public_id"))
    occurred = instant(payload.get("occurred_at"))
    effect = payload.get("customer_effect", "CHANGE")
    if not isinstance(effect, str) or effect not in {"CHANGE", "DELAY"}:
        fail("اثر ثبت‌شده معتبر نیست.")
    identities = payload.get("impacted_cargo_public_ids", [])
    if not isinstance(identities, list) or len(identities) > 1000 or any(not isinstance(x, str) for x in identities) or len(set(identities)) != len(identities):
        fail("کالاهای متأثر معتبر نیستند.")
    cargo = db.session.scalars(select(ShipmentCargoItem).where(
        ShipmentCargoItem.operational_shipment_id == shipment.id, ShipmentCargoItem.public_id.in_(identities))).all() if identities else []
    if len(cargo) != len(identities):
        fail("کالای متأثر یافت نشد.", 404, "REPORT_TARGET_NOT_FOUND")
    if kind == "LOCATION" and scope == "CARGO" and any(c.id != targets["cargo_item_id"] for c in cargo):
        fail("گزارش موقعیت یک کالا، موقعیت کالای دیگری نیست؛ اثر عملیاتی را جدا ثبت کنید.")
    reason = text(payload.get("reason"), 500)
    previous = None
    correction_id = payload.get("corrects_public_id")
    if correction_id is not None and (not isinstance(correction_id, str) or not correction_id.strip() or len(correction_id) > 100):
        fail("شناسه گزارش قبلی معتبر نیست.")
    if payload.get("corrects_public_id"):
        previous = db.session.scalar(_contexts(shipment).where(OperationalEvent.public_id == payload["corrects_public_id"]))
        if previous is None:
            fail("گزارش قبلی یافت نشد.", 404, "REPORT_NOT_FOUND")
        if db.session.scalar(select(OperationalEvent.id).where(
            OperationalEvent.supersedes_event_id == previous.operational_event_id,
            OperationalEvent.event_type == REPORTED_EVENT_TYPE).limit(1)):
            fail("گزارش قبلاً اصلاح شده است؛ نسخه جاری را دوباره بخوانید.", 409, "REPORT_ALREADY_CORRECTED")
    revision = None
    if targets["execution_unit_id"]:
        revision = db.session.scalar(select(ExecutionTransportRevision).where(
            ExecutionTransportRevision.execution_unit_id == targets["execution_unit_id"],
            ExecutionTransportRevision.effective_at <= occurred).order_by(
                ExecutionTransportRevision.effective_at.desc(), ExecutionTransportRevision.id.desc()).limit(1))
    event = OperationalEvent(organization_id=shipment.organization_id, project_id=shipment.project_id, execution_unit_id=targets["execution_unit_id"],
        transport_revision_id=revision.id if revision else None, event_type=REPORTED_EVENT_TYPE,
        source=source, occurred_at=occurred, actor_user_id=int(user["id"]),
        internal_note=text(payload.get("internal_note"), 4000), customer_message=text(payload.get("customer_message"), 1000),
        visibility="internal", attention_required=False, delayed=False,
        idempotency_key="p307-" + hashlib.sha256(f"{shipment.id}:{key}".encode()).hexdigest(), request_hash=fingerprint,
        supersedes_event_id=previous.operational_event_id if previous else None)
    # The existing evidence builder consumes organization_id; it does not infer
    # a unit, coordinate, confidence or checkpoint from this Shipment context.
    location = payload.get("location")
    if location is not None:
        location_fields = {"location_text", "logistics_point_public_id", "canonical_location_public_id", "tracking_location_reference_id"}
        if not isinstance(location, dict) or set(location) - location_fields:
            fail("موقعیت گزارش‌شده معتبر نیست.")
        if "location_text" in location and not isinstance(location["location_text"], str):
            fail("متن موقعیت معتبر نیست.")
    evidence = _event_location_evidence(shipment, payload)
    if evidence is not None and evidence.source_type == "manual":
        # Manual text permits 255 chars; the master-data label column holds 200.
        # Preserve the complete report in its existing manual snapshot column.
        evidence.display_name_snapshot = None
    if kind == "LOCATION" and evidence is None:
        fail("موقعیت گزارش‌شده را وارد کنید.")
    event.location_evidence = evidence
    db.session.add(event)
    db.session.flush()
    row = Context(operational_event_id=event.id, organization_id=shipment.organization_id,
        operational_shipment_id=shipment.id, scope=scope, kind=kind, customer_effect=effect,
        correction_reason=reason, **targets)
    db.session.add(row)
    db.session.flush()
    db.session.add_all([Impact(operational_event_id=event.id, cargo_item_id=c.id,
        operational_shipment_id=shipment.id) for c in cargo])
    db.session.add(OperationalIdempotency(organization_id=shipment.organization_id,
        operation="record_reported_fact", resource_type="shipment", command_resource_id=shipment.id,
        idempotency_key=key, request_hash=fingerprint, result_resource_id=event.id))
    db.session.flush()
    return row, True


def _location(row):
    evidence = row.event.location_evidence
    return (evidence.location_text_snapshot or evidence.display_name_snapshot) if evidence else None


def _target_identity(row):
    if row.scope == "CARGO": return db.session.get(ShipmentCargoItem, row.cargo_item_id).public_id
    if row.scope == "EXECUTION_UNIT": return db.session.get(ExecutionUnit, row.execution_unit_id).public_id
    if row.scope == "ROUTE_STAGE": return str(row.route_leg_id)
    return None


def options(shipment):
    cargo = db.session.scalars(select(ShipmentCargoItem).where(ShipmentCargoItem.operational_shipment_id == shipment.id)
        .order_by(ShipmentCargoItem.line_number)).all()
    cargo_options = []
    for c in cargo:
        owner = db.session.get(Customer, c.cargo_owner_customer_id) if c.cargo_owner_customer_id else None
        cargo_options.append({"public_id": c.public_id, "label": f"{c.display_name_snapshot or 'کالا'} · {owner.company_name or owner.first_name or 'مشتری' if owner else 'مشتری نامشخص'}"})
    legs = db.session.execute(select(RouteLeg, RoutePlan).join(RoutePlan).where(
        RoutePlan.operational_shipment_id == shipment.id).order_by(RoutePlan.id, RouteLeg.sequence_number)).all()
    units = db.session.scalars(select(ExecutionUnit).where(ExecutionUnit.organization_id == shipment.organization_id,
        select(RouteStageExecution.id).where(
            RouteStageExecution.execution_unit_id == ExecutionUnit.id,
            RouteStageExecution.operational_shipment_id == shipment.id).exists()).order_by(ExecutionUnit.id)).all()
    unit_options = []
    for unit in units:
        revision = db.session.scalar(select(ExecutionTransportRevision).where(
            ExecutionTransportRevision.execution_unit_id == unit.id).order_by(ExecutionTransportRevision.revision_number.desc()).limit(1))
        label = f"{revision.means_identifier} · {unit.unit_code}" if revision and revision.means_identifier else unit.unit_code
        unit_options.append({"public_id": unit.public_id, "label": label if unit.is_active else f"{label} · سابقه اجرای غیرفعال"})
    return {"cargo": cargo_options,
            "ROUTE_STAGE": [{"public_id": str(leg.id), "label": f"مسیر {plan.revision_number} · بخش {leg.sequence_number}"} for leg, plan in legs],
            "EXECUTION_UNIT": unit_options,
            "CARGO": cargo_options, "SHIPMENT": []}


def listing(shipment_public_id, user, page=1):
    shipment = scoped_shipment(shipment_public_id, user)
    try: page = max(1, int(page))
    except (ValueError, TypeError): fail("شماره صفحه معتبر نیست.")
    order = (OperationalEvent.occurred_at.desc(), OperationalEvent.recorded_at.desc(), OperationalEvent.id.desc())
    base = _contexts(shipment)
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    page_rows = db.session.scalars(base.order_by(*order).offset((page-1)*20).limit(20)).all()
    successors = select(OperationalEvent.supersedes_event_id).join(Context,
        Context.operational_event_id == OperationalEvent.id).where(
            Context.operational_shipment_id == shipment.id,
            OperationalEvent.supersedes_event_id.is_not(None))
    ranked = select(Context.operational_event_id.label("event_id"), func.row_number().over(
        partition_by=(Context.scope, Context.route_leg_id, Context.execution_unit_id, Context.cargo_item_id),
        order_by=order).label("position")).join(OperationalEvent, OperationalEvent.id == Context.operational_event_id).where(
            Context.organization_id == shipment.organization_id, Context.operational_shipment_id == shipment.id,
            Context.kind == "LOCATION", OperationalEvent.id.not_in(successors)).subquery()
    latest_rows = db.session.scalars(base.where(Context.operational_event_id.in_(
        select(ranked.c.event_id).where(ranked.c.position == 1))).order_by(*order)).all()
    rows = list({r.operational_event_id: r for r in [*page_rows, *latest_rows]}.values())
    row_ids = [r.operational_event_id for r in rows]
    superseded = set(db.session.scalars(successors.where(OperationalEvent.supersedes_event_id.in_(row_ids))).all())
    choices = options(shipment)
    labels = {scope: {x["public_id"]: x["label"] for x in choices[scope]} for scope in SCOPES}
    impacts = db.session.execute(select(Impact.operational_event_id, ShipmentCargoItem.public_id).join(
        ShipmentCargoItem, ShipmentCargoItem.id == Impact.cargo_item_id).where(Impact.operational_shipment_id == shipment.id,
            Impact.operational_event_id.in_(row_ids))).all()
    impacted = {}
    for event_id, cargo_id in impacts: impacted.setdefault(event_id, []).append(cargo_id)
    items = {}
    for row in rows:
        event = row.event
        actor = db.session.get(ExpertUser, event.actor_user_id)
        target = _target_identity(row)
        item = {"public_id": event.public_id, "scope": row.scope, "target_public_id": target,
            "scope_label": labels[row.scope].get(target, SCOPES[row.scope]), "kind": row.kind,
            "source": event.source, "source_label": SOURCES[event.source], "location": _location(row),
            "occurred_at": iso(event.occurred_at), "recorded_at": iso(event.recorded_at),
            "actor_user_id": event.actor_user_id, "internal_note": event.internal_note,
            "actor_label": actor.full_name or actor.username if actor else "کارشناس",
            "customer_message": event.customer_message, "customer_effect": row.customer_effect,
            "impacted_cargo_public_ids": impacted.get(event.id, []), "reason": row.correction_reason,
            "corrects_public_id": db.session.get(OperationalEvent, event.supersedes_event_id).public_id if event.supersedes_event_id else None,
            "status": "SUPERSEDED" if event.id in superseded else "CURRENT"}
        items[event.id] = item
    return {"items": [items[r.operational_event_id] for r in page_rows], "page": page, "total": total,
            "reported_locations": [items[r.operational_event_id] for r in latest_rows],
            "options": choices, "can_manage": _can_manage(user, shipment)}


def customer_timeline(shipment, account, *, limit=50):
    """A future private Customer surface may use this; raw envelope stays internal."""
    allowed = select(ShipmentCargoItem.id).where(ShipmentCargoItem.operational_shipment_id == shipment.id,
        ShipmentCargoItem.cargo_owner_customer_id.in_(authorized_customer_ids(account)))
    if account.operational_organization_id != shipment.organization_id:
        return []
    authorized_impact = select(Impact.operational_event_id).where(
        Impact.operational_event_id == Context.operational_event_id, Impact.cargo_item_id.in_(allowed)).exists()
    rows = db.session.scalars(_contexts(shipment).where(authorized_impact).order_by(
        OperationalEvent.occurred_at.desc(), OperationalEvent.recorded_at.desc(), OperationalEvent.id.desc()).limit(min(max(limit, 1), 100))).all()
    superseded = set(db.session.scalars(select(OperationalEvent.supersedes_event_id).join(Context,
        Context.operational_event_id == OperationalEvent.id).where(Context.operational_shipment_id == shipment.id,
            OperationalEvent.supersedes_event_id.is_not(None))).all())
    own_ids = set(db.session.scalars(allowed).all())
    result = []
    for row in rows:
        location_allowed = row.kind == "LOCATION" and (row.scope != "CARGO" or row.cargo_item_id in own_ids)
        if row.scope == "EXECUTION_UNIT":
            # An impact on A does not disclose the location of a unit carrying
            # only B. Current own-cargo participation is a conservative read gate.
            location_allowed = location_allowed and db.session.scalar(select(ExecutionUnitCargoAllocation.id).where(
                ExecutionUnitCargoAllocation.execution_unit_id == row.execution_unit_id,
                ExecutionUnitCargoAllocation.shipment_cargo_item_id.in_(own_ids),
                ExecutionUnitCargoAllocation.is_current.is_(True),
                ExecutionUnitCargoAllocation.dimension == "ACTUAL",
                ExecutionUnitCargoAllocation.allocated_quantity > 0).limit(1)) is not None
        if row.scope == "ROUTE_STAGE":
            # Only the customer's own destination ancestry is a relevant route.
            leaves = db.session.scalars(select(RouteCargoDestination.destination_route_leg_id).where(
                RouteCargoDestination.route_plan_id == row.route_plan_id,
                RouteCargoDestination.shipment_cargo_item_id.in_(own_ids))).all()
            relevant = set()
            for leg_id in leaves:
                while leg_id and leg_id not in relevant:
                    relevant.add(leg_id)
                    leg = db.session.get(RouteLeg, leg_id)
                    leg_id = leg.parent_route_leg_id if leg else None
            location_allowed = location_allowed and row.route_leg_id in relevant
        result.append({"public_id": row.event.public_id, "kind": row.kind,
            "message": row.event.customer_message or (DELAY_MESSAGE if row.customer_effect == "DELAY" else GENERIC_MESSAGE),
            "occurred_at": iso(row.event.occurred_at), "recorded_at": iso(row.event.recorded_at),
            "source_label": SOURCES[row.event.source], "scope_label": SCOPES[row.scope],
            "reported_location": _location(row) if location_allowed else None,
            "status": "SUPERSEDED" if row.operational_event_id in superseded else "CURRENT",
            "is_correction": row.event.supersedes_event_id is not None})
    return result
