"""Route business occurrence authority. Callers own the transaction and commit."""
from datetime import timezone
from functools import wraps

from sqlalchemy import select

from backend.extensions import db
from backend.operational_models import (
    Milestone, MilestoneEvent, OperationalCheckpoint, OperationalShipment,
    RouteLeg, RoutePlan,
)

OCCURRENCES = {"reported", "corrected", "CORRECTED"}
DECISIONS = {"verified", "VERIFIED"}
PHYSICAL = {"departure", "arrival", "checkpoint_arrival", "checkpoint_departure",
            "checkpoint_processing_complete"}


def atomic_command(function):
    @wraps(function)
    def command(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:
            db.session.rollback()
            raise
    return command


def fail(code, message):
    from backend.services.operational_service import OperationalError
    raise OperationalError(code, message, 409)


def aware(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc) if value else None


def effective_occurrence(milestone, seen=None):
    """Resolve a single rooted correction chain, never a recording-time winner."""
    seen = set() if seen is None else seen
    if milestone.id in seen:
        fail("INVALID_EVENT_LINEAGE", "Cyclic milestone lineage.")
    seen.add(milestone.id)
    rows = db.session.scalars(select(MilestoneEvent).where(
        MilestoneEvent.milestone_id == milestone.id,
        MilestoneEvent.event_type.in_(OCCURRENCES),
    )).all()
    if not rows and milestone.source_milestone_id:
        source = db.session.get(Milestone, milestone.source_milestone_id)
        if not source or (source.organization_id, source.operational_shipment_id, source.milestone_type) != (
            milestone.organization_id, milestone.operational_shipment_id, milestone.milestone_type
        ):
            fail("INVALID_EVENT_LINEAGE", "Invalid inherited occurrence scope.")
        return effective_occurrence(source, seen)
    if not rows:
        return None
    by_id = {row.id: row for row in rows}
    roots = [row for row in rows if row.event_type == "reported" and row.supersedes_event_id is None]
    if len(roots) != 1:
        fail("AMBIGUOUS_OCCURRENCE", "Occurrence roots require explicit reconciliation.")
    children = {}
    for row in rows:
        if row.organization_id != milestone.organization_id:
            fail("INVALID_EVENT_LINEAGE", "Event organization differs from milestone.")
        if row is roots[0]:
            continue
        target = row.supersedes_event_id
        if row.event_type not in {"corrected", "CORRECTED"} or target not in by_id or target in children:
            fail("INVALID_EVENT_LINEAGE", "Malformed or branching correction chain.")
        children[target] = row
    current, visited = roots[0], set()
    while current.id not in visited:
        visited.add(current.id)
        if current.id not in children:
            if len(visited) != len(rows):
                fail("INVALID_EVENT_LINEAGE", "Disconnected correction chain.")
            return current
        current = children[current.id]
    fail("INVALID_EVENT_LINEAGE", "Cyclic correction chain.")


def validate_target(milestone, target, correction=False):
    if target is None or target.event_type not in OCCURRENCES or (
        target.organization_id != milestone.organization_id or target.milestone_id != milestone.id
    ):
        fail("INVALID_EVENT_TARGET", "Target must be an occurrence on the same milestone.")
    if correction and effective_occurrence(milestone).id != target.id:
        fail("STALE_OCCURRENCE", "Only the effective occurrence may be corrected.")


def assert_new_root(milestone):
    if effective_occurrence(milestone) is not None:
        fail("OCCURRENCE_ALREADY_REPORTED", "Use a correction to replace an occurrence.")


def ensure_leg_milestones(leg, shipment):
    for code, planned in (("departure", leg.planned_departure), ("arrival", leg.planned_arrival)):
        row = db.session.scalar(select(Milestone).where(
            Milestone.route_leg_id == leg.id, Milestone.milestone_type == code,
        ))
        if row is None:
            db.session.add(Milestone(
                organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
                route_plan_id=leg.route_plan_id, route_leg_id=leg.id,
                milestone_type=code, planned_at=planned, projected_at=planned,
            ))


def active_plan(shipment):
    return db.session.scalar(select(RoutePlan).where(
        RoutePlan.operational_shipment_id == shipment.id, RoutePlan.is_active.is_(True),
    ))


def shipment_state(shipment, plan, legs):
    if shipment.lifecycle_status == "cancelled":
        return "cancelled", "EXPLICIT_CANCEL"
    required = [leg for leg in legs if leg.status != "cancelled"]
    if required and all(leg.status == "completed" for leg in required):
        return "completed", "ALL_REQUIRED_ACTIVE_LEGS_COMPLETED"
    if any(leg.actual_departure or leg.actual_arrival or leg.status in {"in_progress", "completed"} for leg in required):
        return "in_progress", "ACTIVE_LEGS_IN_PROGRESS"
    return "planned", "NO_ACTIVE_EXECUTION" if required else "EMPTY_ROUTE" if not legs else "UNRESOLVED_ROUTE_STATE"


def project_shipment(shipment):
    plan = active_plan(shipment)
    legs = db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id == plan.id)).all() if plan else []
    status, reason = shipment_state(shipment, plan, legs)
    if shipment.lifecycle_status != status:
        shipment.lifecycle_status = status
        shipment.version += 1
    return "EMPTY_EXECUTABLE_ROUTE" if reason == "EMPTY_ROUTE" else reason


def inherited_projections(milestone):
    """Follow explicit shipment-local lineage, stopping at independent facts."""
    occurrence = effective_occurrence(milestone)
    if occurrence is None:
        return []
    descendants, frontier, seen = [], [milestone], {milestone.id}
    while frontier:
        parents = {row.id: row for row in frontier}
        children = db.session.scalars(select(Milestone).where(
            Milestone.source_milestone_id.in_(parents),
            Milestone.organization_id == milestone.organization_id,
            Milestone.operational_shipment_id == milestone.operational_shipment_id,
        ).order_by(Milestone.id).with_for_update()).all()
        frontier = []
        for child in children:
            if child.id in seen:
                fail("INVALID_EVENT_LINEAGE", "Cyclic descendant milestone lineage.")
            seen.add(child.id)
            parent = parents[child.source_milestone_id]
            if child.milestone_type != parent.milestone_type:
                fail("INVALID_EVENT_LINEAGE", "Inherited milestone type differs.")
            for row in (parent, child):
                plan = db.session.get(RoutePlan, row.route_plan_id)
                if not plan or plan.operational_shipment_id != milestone.operational_shipment_id:
                    fail("INVALID_EVENT_LINEAGE", "Inherited route belongs to another shipment.")
            for model, field, source_field in (
                (RouteLeg, "route_leg_id", "source_route_leg_id"),
                (OperationalCheckpoint, "checkpoint_id", "source_checkpoint_id"),
            ):
                parent_id, child_id = getattr(parent, field), getattr(child, field)
                if parent_id is None and child_id is None:
                    continue
                owner = db.session.get(model, child_id) if child_id else None
                source = db.session.get(model, parent_id) if parent_id else None
                if (not owner or not source or getattr(owner, source_field) != parent_id
                        or owner.route_plan_id != child.route_plan_id
                        or source.route_plan_id != parent.route_plan_id):
                    fail("INVALID_EVENT_LINEAGE", "Inherited owner lineage is inconsistent.")
            # The resolver validates local chains. A valid local root is independent;
            # malformed replacement chains fail closed rather than being overwritten.
            effective = effective_occurrence(child)
            if effective is None or effective.id != occurrence.id:
                continue
            descendants.append(child)
            frontier.append(child)
    return descendants


def _project_one(milestone):
    occurrence = effective_occurrence(milestone)
    if occurrence:
        milestone.occurred_at = occurrence.occurred_at
        verified = db.session.scalar(select(MilestoneEvent.id).where(
            MilestoneEvent.event_type.in_(DECISIONS),
            MilestoneEvent.related_event_id == occurrence.id,
        )) is not None
        milestone.verification_state = "verified" if verified else "reported"
        milestone.projected_state = "reported"
        if milestone.milestone_type in PHYSICAL and (milestone.route_leg_id or milestone.checkpoint_id):
            milestone.lifecycle_status = "COMPLETED"
            milestone.completed_at = occurrence.occurred_at
    if milestone.route_leg_id and milestone.milestone_type in {"departure", "arrival"}:
        leg = db.session.scalar(select(RouteLeg).where(RouteLeg.id == milestone.route_leg_id).with_for_update())
        values = {}
        for row in db.session.scalars(select(Milestone).where(Milestone.route_leg_id == leg.id)):
            if row.milestone_type in {"departure", "arrival"}:
                event = effective_occurrence(row)
                values[row.milestone_type] = event.occurred_at if event else None
        departure, arrival = values.get("departure"), values.get("arrival")
        if departure and arrival and aware(arrival) < aware(departure):
            fail("INVALID_ACTUAL_CHRONOLOGY", "Arrival cannot precede departure.")
        leg.actual_departure, leg.actual_arrival = departure, arrival
        if leg.status not in {"blocked", "cancelled"}:
            leg.status = "completed" if arrival else "in_progress" if departure else leg.status
        leg.version += 1
    if milestone.checkpoint_id:
        checkpoint = db.session.scalar(select(OperationalCheckpoint).where(
            OperationalCheckpoint.id == milestone.checkpoint_id,
        ).with_for_update())
        values = {}
        for row in db.session.scalars(select(Milestone).where(Milestone.checkpoint_id == checkpoint.id)):
            event = effective_occurrence(row)
            values[row.milestone_type] = event.occurred_at if event else None
        arrival, departure = values.get("checkpoint_arrival"), values.get("checkpoint_departure")
        if departure and (not arrival or aware(departure) < aware(arrival)):
            fail("INVALID_ACTUAL_CHRONOLOGY", "Checkpoint departure requires an earlier explicit arrival.")
        checkpoint.actual_arrival_at, checkpoint.actual_departure_at = arrival, departure
        if checkpoint.status not in {"blocked", "cancelled"}:
            checkpoint.status = ("completed" if departure else "ready_to_depart" if values.get("checkpoint_processing_complete")
                                 else "arrived" if arrival else "planned")


def project(milestone):
    """Rebuild source and inherited facts in the caller's atomic transaction."""
    shipment = db.session.scalar(select(OperationalShipment).where(
        OperationalShipment.id == milestone.operational_shipment_id,
        OperationalShipment.organization_id == milestone.organization_id,
    ).with_for_update())
    if shipment is None:
        fail("INVALID_EVENT_LINEAGE", "Milestone shipment scope is inconsistent.")
    descendants = inherited_projections(milestone)
    _project_one(milestone)
    for descendant in descendants:
        _project_one(descendant)
        descendant.version += 1
        if descendant.checkpoint_id:
            checkpoint = db.session.get(OperationalCheckpoint, descendant.checkpoint_id)
            checkpoint.verification_state = descendant.verification_state
            checkpoint.version += 1
    db.session.flush()
    project_shipment(shipment)


def block_checkpoint(checkpoint, shipment, user, reason):
    """Explicit operational condition; never creates occurrence evidence."""
    if checkpoint.status in {"cancelled", "completed", "blocked"}:
        return
    from backend.services.operational_service import _audit
    previous = checkpoint.status
    checkpoint.status = "blocked"
    checkpoint.version += 1
    _audit(shipment.organization_id, user["id"], "checkpoint.blocked", "OperationalCheckpoint",
           checkpoint.id, {"reason": reason, "previous_status": previous})
