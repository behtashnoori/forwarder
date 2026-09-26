"""ENSURE_CURRENT_ETA is an explicit derived write; history is a pure lookup.

Call ensure in a consistent transaction. No operational source is mutated here.
An unplaced nonzero stop range cannot prove a remaining arrival interval. Pending
the bounded Product clarification, that interval remains explicitly unavailable.
"""
from datetime import timedelta
import hashlib
import json

from sqlalchemy import select

from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem as Cargo, ExecutionUnitCargoAllocation as Allocation
from backend.eta_models import CargoEtaSnapshot as Snapshot, CargoEtaInput as Input
from backend.operational_models import (Milestone, OperationalCheckpoint, OperationalEvent,
    OperationalShipment as Shipment, RouteCargoDestination, RouteLeg, RoutePlan,
    RouteStageExecution, RouteTraversalFact, utcnow)
from backend.reported_fact_models import OperationalEventReportContext as Context, OperationalEventCargoImpact as Impact
from backend.services import operational_service as base, route_time_service as times
from backend.services import occurrence_projection_service as occurrences, customer_shipment_service as customers
from backend.services.customer_entitlement_service import authorized_customer_ids

RULESET = "ETA_RULESET_V1"
REASONS = {
    "ROUTE_UNDEFINED": "مسیر این کالا کامل تعریف نشده است.",
    "PROGRESS_UNDEFINED": "موقعیت یا پیشرفت عملیاتی کافی ثبت نشده است.",
    "PROGRESS_AMBIGUOUS": "پیشرفت کل این کالا به‌طور روشن مشخص نیست.",
    "REFERENCE_UNDEFINED": "زمان مرجع بخش باقی‌مانده تعریف نشده است.",
    "STOP_SCOPE_UNDEFINED": "جای توقف یا عملیات نسبت به نقطه رسیدن مشخص نشده است.",
    "NEXT_POINT_AMBIGUOUS": "مبنای زمان نقطه مهم بعدی مشخص نیست.",
    "DESTINATION_REACHED": "رسیدن ثبت شده است؛ برآورد رسیدن آینده ارائه نمی‌شود.",
    "SOURCE_UNAVAILABLE": "مبنای این برآورد اکنون در دسترس نیست.",
}


def stamp(value):
    return times.aware(value).isoformat() if value is not None else None


def missing(code, target=None):
    return {"available": False, "reason": code, "message": REASONS[code],
            "target": target, "earliest": None, "latest": None}


def _scope(shipment_id, cargo_id, *, user=None, account=None):
    if account is not None:
        customers.authorization_revision(account)
        shipment = db.session.scalar(customers._shipments(account).where(Shipment.public_id == shipment_id))
        if shipment is None:
            raise base.OperationalError("CUSTOMER_SHIPMENT_NOT_FOUND", "پرونده حمل در دسترس نیست.", 404)
    else:
        shipment = base.scoped_shipment(shipment_id, user)
    query = select(Cargo).where(Cargo.public_id == cargo_id, Cargo.operational_shipment_id == shipment.id)
    if account is not None:
        query = query.where(Cargo.cargo_owner_customer_id.in_(authorized_customer_ids(account)))
    cargo = db.session.scalar(query.execution_options(populate_existing=True))
    if cargo is None:
        raise base.OperationalError("ETA_NOT_FOUND", "کالا در دسترس نیست.", 404)
    return shipment, cargo


def _path(shipment, cargo):
    plan = db.session.scalar(select(RoutePlan).where(RoutePlan.operational_shipment_id == shipment.id,
        RoutePlan.is_active.is_(True), RoutePlan.status == "active"))
    if plan is None:
        return None, None, []
    mapping = db.session.scalar(select(RouteCargoDestination).where(
        RouteCargoDestination.route_plan_id == plan.id, RouteCargoDestination.shipment_cargo_item_id == cargo.id,
        RouteCargoDestination.operational_shipment_id == shipment.id))
    if mapping is None:
        return plan, None, []
    leg_id, seen, legs = mapping.destination_route_leg_id, set(), []
    while leg_id:
        if leg_id in seen:
            return plan, mapping, []
        seen.add(leg_id)
        leg = db.session.scalar(select(RouteLeg).where(RouteLeg.id == leg_id, RouteLeg.route_plan_id == plan.id))
        if leg is None or leg.status in {"cancelled", "blocked"}:
            return plan, mapping, []
        legs.append(leg)
        leg_id = leg.parent_route_leg_id
    legs.reverse()
    for previous, following in zip(legs, legs[1:]):
        if endpoint(previous, "destination") != endpoint(following, "origin"):
            return plan, mapping, []
    return plan, mapping, legs


def endpoint(leg, side):
    return (getattr(leg, side + "_location_id"), getattr(leg, side + "_logistics_point_id"))


def _label(shipment, leg, customer):
    if customer:
        return customers._geography(leg.destination_location_id, leg.destination_logistics_point_id,
                                    shipment.organization_id) or "مقصد کالای شما"
    return times.endpoint_label(leg.destination_snapshot)


def _participation(cargo, legs):
    allocations = db.session.scalars(select(Allocation).where(Allocation.shipment_cargo_item_id == cargo.id,
        Allocation.is_current.is_(True))).all()
    stages = {row.id: row for row in db.session.scalars(select(RouteStageExecution).where(
        RouteStageExecution.operational_shipment_id == cargo.operational_shipment_id,
        RouteStageExecution.route_leg_id.in_([leg.id for leg in legs]))).all()}
    by_leg = {}
    basis = []
    legacy_unknown = False
    for row in allocations:
        if row.dimension is None:
            legacy_unknown = True
            basis.append([row.id, row.version, None, str(row.allocated_quantity)])
        elif row.dimension == "ACTUAL" and row.route_stage_execution_id in stages:
            stage = stages[row.route_stage_execution_id]
            by_leg.setdefault(stage.route_leg_id, []).append(row)
            basis.append([row.id, row.version, stage.id, row.execution_unit_id, str(row.allocated_quantity)])
    split = legacy_unknown or any(len(rows) > 1 for rows in by_leg.values())
    whole_units = {}
    for rows in by_leg.values():
        if len(rows) == 1 and cargo.actual_quantity is not None and rows[0].allocated_quantity == cargo.actual_quantity:
            whole_units[rows[0].execution_unit_id] = stages[rows[0].route_stage_execution_id].route_leg_id
    return by_leg, whole_units, split, sorted(basis)


def _report_sources(shipment, cargo, legs, whole_units, customer, *, include_superseded=False):
    """Apply exact Cargo impact and source-scope gates before selecting inputs."""
    leg_ids = {leg.id for leg in legs}
    impacts = set(db.session.scalars(select(Impact.operational_event_id).where(
        Impact.cargo_item_id == cargo.id, Impact.operational_shipment_id == shipment.id)).all())
    contexts = db.session.scalars(select(Context).where(Context.organization_id == shipment.organization_id,
        Context.operational_shipment_id == shipment.id)).all()
    superseded = {row.event.supersedes_event_id for row in contexts if row.event.supersedes_event_id is not None}
    result = []
    for row in contexts:
        if row.operational_event_id in superseded and not include_superseded:
            continue
        relevant = (row.scope == "CARGO" and row.cargo_item_id == cargo.id or
                    row.scope == "ROUTE_STAGE" and row.route_leg_id in leg_ids or
                    row.scope == "EXECUTION_UNIT" and row.execution_unit_id in whole_units or
                    row.scope == "SHIPMENT" and row.operational_event_id in impacts)
        if not relevant or customer and row.operational_event_id not in impacts:
            continue
        result.append(row)
    return result


def _position(evidence, legs):
    if evidence is None or evidence.source_type not in {"canonical_location", "logistics_point"}:
        return None
    matches = []
    for index, leg in enumerate(legs):
        for side in ("origin", "destination"):
            location, facility = endpoint(leg, side)
            match = (evidence.logistics_point_id == facility if evidence.source_type == "logistics_point"
                     else evidence.canonical_location_id == location and facility is None)
            if match:
                # Node zero is the route origin; each subsequent node is an arrival.
                matches.append(index if side == "origin" else index + 1)
    nodes = set(matches)
    return nodes.pop() if len(nodes) == 1 else None


def _observations(shipment, cargo, plan, legs, customer, whole_units):
    candidates, sources, effects, reports = [], [], False, _report_sources(shipment, cargo, legs, whole_units, customer)
    for row in reports:
        event = row.event
        sources.append({"operational_event_id": event.id})
        if row.kind in {"EFFECT", "TRANSPORT_CHANGE"}:
            effects = True
        if row.kind != "LOCATION":
            continue
        node = _position(event.location_evidence, legs)
        if row.scope == "ROUTE_STAGE" and node not in {
                next(i for i, leg in enumerate(legs) if leg.id == row.route_leg_id),
                next(i for i, leg in enumerate(legs) if leg.id == row.route_leg_id) + 1}:
            node = None
        if row.scope == "EXECUTION_UNIT":
            index = next(i for i, leg in enumerate(legs) if leg.id == whole_units[row.execution_unit_id])
            if node not in {index, index + 1}:
                node = None
        if plan.created_from_plan_id is not None and (plan.effective_at is None
                or times.aware(event.occurred_at) < times.aware(plan.effective_at)):
            # Cargo/Unit reports lack an explicit mapping to a replacement plan.
            node = None
        # A location identifies a node, not completion of its remaining operations.
        candidates.append({"source": "REPORT", "id": event.id, "node": node,
            "phase": "AT_NODE", "occurred_at": stamp(event.occurred_at), "recorded_at": stamp(event.recorded_at)})
    if not customer:
        for milestone in db.session.scalars(select(Milestone).where(Milestone.route_plan_id == plan.id,
                Milestone.route_leg_id.in_([leg.id for leg in legs]),
                Milestone.milestone_type.in_(("departure", "arrival")))).all():
            # Replan's explicit inherited occurrence resolver preserves governed lineage.
            occurrence = occurrences.effective_occurrence(milestone)
            if occurrence is None:
                continue
            index = next(i for i, leg in enumerate(legs) if leg.id == milestone.route_leg_id)
            sources.append({"milestone_event_id": occurrence.id})
            candidates.append({"source": "MILESTONE", "id": occurrence.id,
                "node": index + (milestone.milestone_type == "arrival"),
                "phase": "DEPARTED" if milestone.milestone_type == "departure" else "AT_NODE",
                "occurred_at": stamp(occurrence.occurred_at), "recorded_at": stamp(occurrence.recorded_at)})
        for traversal in db.session.scalars(select(RouteTraversalFact).where(
                RouteTraversalFact.route_plan_id == plan.id,
                RouteTraversalFact.planned_route_leg_id.in_([leg.id for leg in legs]))).all():
            index = next(i for i, leg in enumerate(legs) if leg.id == traversal.planned_route_leg_id)
            leg = legs[index]
            matches = endpoint(traversal, "origin") == endpoint(leg, "origin") and endpoint(traversal, "destination") == endpoint(leg, "destination")
            sources.append({"traversal_id": traversal.id})
            for at, arrived in ((traversal.departed_at, False), (traversal.arrived_at, True)):
                if at is not None:
                    candidates.append({"source": "TRAVERSAL", "id": traversal.id,
                        "node": index + arrived if matches else None,
                        "phase": "AT_NODE" if arrived else "DEPARTED",
                        "occurred_at": stamp(at), "recorded_at": stamp(traversal.recorded_at)})
    candidates.sort(key=lambda row: (row["occurred_at"], row["source"], row["id"]))
    return candidates, sources, effects


def _calculate(shipment, cargo, *, customer=False, at=None):
    """Pure source computation; no flush, commit, snapshot or source writes."""
    at = at or utcnow()
    plan, mapping, legs = _path(shipment, cargo)
    basis = {"ruleset": RULESET, "audience": "CUSTOMER" if customer else "INTERNAL",
        "cargo": [cargo.id, cargo.version, str(cargo.actual_quantity)],
        "route": [plan.id, plan.revision_number, plan.version] if plan else None,
        "mapping": [mapping.id, mapping.version, mapping.destination_route_leg_id] if mapping else None}
    result = {"next": missing("ROUTE_UNDEFINED"), "final": missing("ROUTE_UNDEFINED"),
        "as_of": None, "recorded_at": None, "basis_label": None,
        "unquantified_effect": False, "planned_distance": None}
    sources = []
    if not legs:
        return plan, basis, result, sources
    basis["legs"] = [{"id": leg.id, "version": leg.version, "parent": leg.parent_route_leg_id,
        **times.fingerprint(leg)} for leg in legs]
    _, whole_units, split, allocation_basis = _participation(cargo, legs)
    basis["participation"] = allocation_basis
    try:
        observations, sources, effects = _observations(shipment, cargo, plan, legs, customer, whole_units)
    except base.OperationalError as exc:
        if exc.code not in {"INVALID_EVENT_LINEAGE", "AMBIGUOUS_OCCURRENCE"}:
            raise
        basis["source_error"] = exc.code
        result.update(next=missing("PROGRESS_AMBIGUOUS"), final=missing("PROGRESS_AMBIGUOUS", _label(shipment, legs[-1], customer)))
        return plan, basis, result, sources
    basis["observations"] = observations
    basis["unquantified_effect"] = effects
    # Include all relevant report identities so corrected/unquantified sources alter provenance.
    basis["source_identities"] = sorted(sources, key=lambda row: json.dumps(row, sort_keys=True))
    result["unquantified_effect"] = effects
    anchor = observations[-1] if observations else None
    reason = "PROGRESS_UNDEFINED"
    if anchor:
        same_time = [row for row in observations if row["occurred_at"] == anchor["occurred_at"]]
        positions = {row["node"] for row in same_time}
        if split or anchor["node"] is None or len(positions) != 1 or times.instant(anchor["occurred_at"]) > at:
            reason = "PROGRESS_AMBIGUOUS"
            anchor = None
    if anchor is None:
        result.update(next=missing(reason), final=missing(reason, _label(shipment, legs[-1], customer)))
        return plan, basis, result, sources
    basis["anchor"] = anchor
    node = anchor["node"]
    result.update(as_of=anchor["occurred_at"], recorded_at=anchor["recorded_at"],
                  basis_label="گزارش موقعیت عملیاتی" if anchor["source"] == "REPORT" else "رخداد ثبت‌شده مسیر")
    if node == len(legs):
        result.update(next=missing("DESTINATION_REACHED"), final=missing("DESTINATION_REACHED", _label(shipment, legs[-1], customer)))
        return plan, basis, result, sources
    references = [times.applicable(leg, shipment.organization_id, at) for leg in legs[node:]]
    basis["references"] = [{"id": ref.id, "version": ref.version,
        "movement_min": ref.movement_min_minutes, "movement_max": ref.movement_max_minutes,
        "stop_min": ref.stop_min_minutes, "stop_max": ref.stop_max_minutes} if ref else None for ref in references]
    sources += [{"reference_version_id": ref.id} for ref in references if ref]
    checkpoints = db.session.scalars(select(OperationalCheckpoint).where(
        OperationalCheckpoint.route_plan_id == plan.id,
        OperationalCheckpoint.route_leg_id == legs[node].id)).all()
    basis["next_checkpoints"] = [[row.id, row.version, row.canonical_location_id] for row in checkpoints]
    # A checkpoint within the next leg has no fractional reference travel-time basis.
    uncertain_next = any(row.canonical_location_id not in endpoint(legs[node], "destination")[:1]
                         and row.actual_departure_at is None for row in checkpoints)
    def estimate(count):
        selected = references[:count]
        label = _label(shipment, legs[node + count - 1], customer)
        if any(ref is None or ref.movement_min_minutes is None or ref.stop_min_minutes is None for ref in selected):
            return missing("REFERENCE_UNDEFINED", label)
        if any(ref.stop_max_minutes != 0 for ref in selected):
            return missing("STOP_SCOPE_UNDEFINED", label)
        lower = sum(ref.movement_min_minutes + ref.stop_min_minutes for ref in selected)
        upper = sum(ref.movement_max_minutes + ref.stop_max_minutes for ref in selected)
        origin = times.instant(anchor["occurred_at"])
        return {"available": True, "reason": None, "message": None, "target": label,
                "earliest": stamp(origin + timedelta(minutes=lower)), "latest": stamp(origin + timedelta(minutes=upper))}
    result.update(next=missing("NEXT_POINT_AMBIGUOUS") if uncertain_next else estimate(1), final=estimate(len(references)))
    return plan, basis, result, sources


def calculate(shipment, cargo, *, customer=False, at=None):
    plan, basis, result, sources = _calculate(shipment, cargo, customer=customer, at=at)
    # Time-dependent eligibility and safe geography labels can change without a
    # source-row version changing. Preserve those meaningful transitions too.
    basis["resolved_result"] = result
    return plan, basis, result, sources


def _fingerprint(basis):
    return hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def project(snapshot, *, customer=False):
    value = {"public_id": snapshot.public_id, "sequence": snapshot.sequence,
        "ruleset": snapshot.ruleset, "calculated_at": stamp(snapshot.calculated_at), **snapshot.result}
    if not customer:
        value.update(source_fingerprint=snapshot.source_fingerprint, provenance=snapshot.source_basis)
    return value


def ensure_current_eta(shipment_id, cargo_id, *, user=None, account=None):
    shipment, cargo = _scope(shipment_id, cargo_id, user=user, account=account)
    # Per-Cargo serialization does not acquire or mutate an operational aggregate.
    if db.session.get_bind().dialect.name == "postgresql":
        from sqlalchemy import text
        db.session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
                           {"identity": f"cargo_eta:{cargo.id}"})
    audience = "CUSTOMER" if account is not None else "INTERNAL"
    plan, basis, result, sources = calculate(shipment, cargo, customer=account is not None)
    fingerprint = _fingerprint(basis)
    previous = db.session.scalar(select(Snapshot).where(Snapshot.cargo_item_id == cargo.id,
        Snapshot.organization_id == shipment.organization_id, Snapshot.audience == audience)
        .order_by(Snapshot.sequence.desc()).limit(1))
    if previous and previous.source_fingerprint == fingerprint:
        return previous
    row = Snapshot(organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
        cargo_item_id=cargo.id, route_plan_id=plan.id if plan else None, audience=audience,
        sequence=previous.sequence + 1 if previous else 1, source_fingerprint=fingerprint,
        source_basis=basis, result=result)
    db.session.add(row)
    db.session.flush()
    unique = {tuple(source.items()) for source in sources}
    db.session.add_all(Input(snapshot_id=row.id, organization_id=shipment.organization_id, **dict(source)) for source in unique)
    db.session.flush()
    _scope(shipment_id, cargo_id, user=user, account=account)
    return row


def history(shipment_id, cargo_id, *, user=None, account=None, page=1):
    shipment, cargo = _scope(shipment_id, cargo_id, user=user, account=account)
    page = customers.page_number(page)
    audience = "CUSTOMER" if account is not None else "INTERNAL"
    rows = db.session.scalars(select(Snapshot).where(Snapshot.organization_id == shipment.organization_id,
        Snapshot.cargo_item_id == cargo.id, Snapshot.audience == audience)
        .order_by(Snapshot.sequence.desc()).offset((page - 1) * 20).limit(21)).all()
    allowed = None
    if account is not None:
        _, _, legs = _path(shipment, cargo)
        _, units, _, _ = _participation(cargo, legs)
        allowed = {row.operational_event_id for row in _report_sources(
            shipment, cargo, legs, units, True, include_superseded=True)}
    items = []
    for row in rows[:20]:
        value = project(row, customer=account is not None)
        if allowed is not None:
            source_ids = {source.operational_event_id for source in db.session.scalars(select(Input).where(
                Input.snapshot_id == row.id, Input.operational_event_id.is_not(None))).all()}
            if not source_ids.issubset(allowed):
                value.update(next=missing("SOURCE_UNAVAILABLE"), final=missing("SOURCE_UNAVAILABLE"),
                             as_of=None, recorded_at=None, basis_label=None, unquantified_effect=False)
        items.append(value)
    return {"items": items, "page": page, "has_next": len(rows) > 20}
