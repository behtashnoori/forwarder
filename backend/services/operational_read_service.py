"""Read-only route evidence, scoped history and audit contracts."""
from sqlalchemy import select, and_, or_
from backend.extensions import db
from backend.operational_models import (Milestone, MilestoneEvent, RoutePlan, RouteLeg,
    OperationalCheckpoint, OperationalAudit, OperationalWorkItem)
from backend.external_reference_models import OperationalShipmentExternalReference
from backend.services import occurrence_projection_service as authority

VERSION = "route-occurrence-v1"


def classification(event):
    return "VERIFICATION_DECISION" if event.event_type in authority.DECISIONS else (
        "CORRECTION" if event.event_type in {"corrected", "CORRECTED"} else
        "PHYSICAL_OCCURRENCE" if event.event_type == "reported" else "LIFECYCLE_COMMAND")


def business_label(event):
    return {"VERIFICATION_DECISION": "Verified", "CORRECTION": "Corrected", "PHYSICAL_OCCURRENCE": "Reported"}.get(
        classification(event), "Route prepared" if event.event_type == "INITIALIZED" else "Lifecycle changed")


def iso(value):
    return authority.aware(value).isoformat() if value else None


def scope(plan):
    return {"route_plan_id": plan.id if plan else None,
            "route_revision": plan.revision_number if plan else None,
            "is_active": bool(plan and plan.is_active), "projection_version": VERSION,
            "route_version": plan.version if plan else None}


def time_value(planned, projected, actual):
    return {"planned_at": iso(planned), "projected_at": iso(projected), "actual_at": iso(actual),
            "effective_at": iso(actual or projected or planned),
            "time_source": "actual" if actual else "projected" if projected else "planned" if planned else "unavailable"}


def evidence(milestone, plan):
    try:
        event = authority.effective_occurrence(milestone)
    except Exception as error:
        from backend.services.operational_service import OperationalError
        if not isinstance(error, OperationalError):
            raise
        return {"milestone_public_id": milestone.public_id, "effective_event_public_id": None,
                "reason_code": "UNRESOLVED_ROUTE_STATE", "diagnostic_code": error.code, **scope(plan)}
    source = db.session.get(Milestone, event.milestone_id) if event else None
    source_plan = db.session.get(RoutePlan, source.route_plan_id) if source and source.route_plan_id else None
    return {"milestone_public_id": milestone.public_id,
            "effective_event_public_id": event.public_id if event else None,
            "effective_occurred_at": iso(event.occurred_at) if event else None,
            "source_milestone_public_id": source.public_id if source else None,
            "source_route_plan_id": source_plan.id if source_plan else None,
            "source_route_revision": source_plan.revision_number if source_plan else None,
            "inherited": bool(event and event.milestone_id != milestone.id),
            "reason_code": "EFFECTIVE_OCCURRENCE" if event else "NO_OCCURRENCE", **scope(plan)}


def current_route(shipment, plan=...):
    plan = authority.active_plan(shipment) if plan is ... else plan
    legs = db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id == plan.id)
        .order_by(RouteLeg.sequence_number)).all() if plan else []
    milestones = db.session.scalars(select(Milestone).where(Milestone.route_plan_id == plan.id,
        Milestone.organization_id == shipment.organization_id, Milestone.operational_shipment_id == shipment.id)).all() if plan else []
    proofs = {m.id: evidence(m, plan) for m in milestones}
    leg_views = []
    for leg in legs:
        sources = {m.milestone_type: proofs[m.id] for m in milestones
                   if m.route_leg_id == leg.id and m.milestone_type in {"departure", "arrival"}}
        milestone_ids = {m.milestone_type: m.public_id for m in milestones
                         if m.route_leg_id == leg.id and m.milestone_type in {"departure", "arrival"}}
        leg_views.append({"id": leg.id, "status": leg.status, "source_route_leg_id": leg.source_route_leg_id,
            "departure_milestone_id": milestone_ids.get("departure"),
            "arrival_milestone_id": milestone_ids.get("arrival"),
            "departure": time_value(leg.planned_departure, leg.projected_departure, leg.actual_departure),
            "arrival": time_value(leg.planned_arrival, leg.projected_arrival, leg.actual_arrival),
            "occurrence_sources": sources,
            "reason_code": "EXPLICIT_" + leg.status.upper() if leg.status in {"blocked", "cancelled"}
                else "ARRIVAL_OCCURRED" if sources.get("arrival", {}).get("effective_event_public_id")
                else "DEPARTURE_OCCURRED" if sources.get("departure", {}).get("effective_event_public_id")
                else "UNRESOLVED_ROUTE_STATE" if leg.actual_arrival or leg.actual_departure or leg.status in {"completed", "in_progress"}
                else "NO_ACTIVE_EXECUTION", **scope(plan)})
    status, reason = authority.shipment_state(shipment, plan, legs)
    if any(p["reason_code"] == "UNRESOLVED_ROUTE_STATE" for p in proofs.values()) or any(
        leg["reason_code"] == "UNRESOLVED_ROUTE_STATE" for leg in leg_views):
        reason = "UNRESOLVED_ROUTE_STATE"
    checkpoints = db.session.scalars(select(OperationalCheckpoint).where(OperationalCheckpoint.route_plan_id == plan.id)).all() if plan else []
    return {"scope": "current_route", **scope(plan), "status": status,
            "checkpoints": [{"id": c.id, "status": c.status, "source_checkpoint_id": c.source_checkpoint_id,
                "arrival": time_value(c.planned_arrival_at, c.projected_arrival_at, c.actual_arrival_at),
                "departure": time_value(c.planned_departure_at, c.projected_departure_at, c.actual_departure_at),
                "occurrence_sources": {m.milestone_type: proofs[m.id] for m in milestones if m.checkpoint_id == c.id}}
                for c in checkpoints],
            "shipment_status_reason": reason, "contributing_legs": [v for v in leg_views if v["status"] != "cancelled"],
            "route_legs": leg_views, "milestone_evidence": proofs,
            "stored_status": shipment.lifecycle_status,
            "projection_consistent": status == shipment.lifecycle_status}


def audit_query(shipment):
    plans = select(RoutePlan.id).where(RoutePlan.operational_shipment_id == shipment.id)
    milestones = select(Milestone.id).where(Milestone.operational_shipment_id == shipment.id,
                                            Milestone.organization_id == shipment.organization_id)
    targets = {"OperationalShipment": [shipment.id], "RoutePlan": plans,
        "RouteLeg": select(RouteLeg.id).where(RouteLeg.route_plan_id.in_(plans)),
        "OperationalCheckpoint": select(OperationalCheckpoint.id).where(OperationalCheckpoint.route_plan_id.in_(plans)),
        "Milestone": milestones,
        "MilestoneEvent": select(MilestoneEvent.id).where(MilestoneEvent.milestone_id.in_(milestones),
            MilestoneEvent.organization_id == shipment.organization_id),
        "OperationalWorkItem": select(OperationalWorkItem.id).where(OperationalWorkItem.operational_shipment_id == shipment.id,
            OperationalWorkItem.organization_id == shipment.organization_id),
        "shipment_external_reference": select(OperationalShipmentExternalReference.id).where(
            OperationalShipmentExternalReference.operational_shipment_id == shipment.id,
            OperationalShipmentExternalReference.organization_id == shipment.organization_id)}
    return select(OperationalAudit).where(OperationalAudit.organization_id == shipment.organization_id,
        or_(*(and_(OperationalAudit.entity_type == kind, OperationalAudit.entity_id.in_(ids)) for kind, ids in targets.items())))


def event_view(event, shipment):
    milestone = db.session.get(Milestone, event.milestone_id)
    plan = db.session.get(RoutePlan, milestone.route_plan_id) if milestone.route_plan_id else None
    category = classification(event)
    related = event.related_event_id if category == "VERIFICATION_DECISION" else None
    legacy = category == "VERIFICATION_DECISION" and not related
    related = related or (event.supersedes_event_id if legacy else None)
    supersedes = event.supersedes_event_id if category == "CORRECTION" else None
    target_id = related or supersedes
    target = db.session.get(MilestoneEvent, target_id) if target_id else None
    valid = bool(target and target.milestone_id == event.milestone_id and
                 target.organization_id == shipment.organization_id and target.event_type in authority.OCCURRENCES)
    source = db.session.get(Milestone, milestone.source_milestone_id) if milestone.source_milestone_id else None
    return {"id": event.id, "public_id": event.public_id, "milestone_id": milestone.id,
        "milestone_public_id": milestone.public_id, "milestone_type": milestone.milestone_type,
        "milestone_context": {"type_snapshot": milestone.milestone_type_snapshot,
            "expected_point_snapshot": milestone.expected_point_snapshot, "target_metadata": milestone.target_metadata,
            "planned_at": iso(milestone.planned_at), "source_milestone_id": milestone.source_milestone_id},
        "source_milestone_public_id": source.public_id if source and source.operational_shipment_id == shipment.id
            and source.organization_id == shipment.organization_id else None,
        "classification": category, "event_type": event.event_type,
        "business_label": business_label(event),
        "actor_user_id": event.actor_user_id, "occurred_at": iso(event.occurred_at), "recorded_at": iso(event.recorded_at),
        "reason": event.reason, "source_channel": event.source_channel,
        "related_event_public_id": target.public_id if valid and related else None,
        "supersedes_event_public_id": target.public_id if valid and supersedes else None,
        "relationship_status": "LEGACY_PROVEN" if valid and legacy else "RESOLVED" if valid else
            "UNRESOLVED" if target_id or category in {"VERIFICATION_DECISION", "CORRECTION"} else "NOT_APPLICABLE",
        "diagnostics": {"raw_event_type": event.event_type}, **scope(plan)}


def history(shipment, page=1, per_page=50, user=None):
    from backend.services.unified_shipment_history import history as unified_history
    return unified_history(shipment, page, per_page, user)


def plan_has_execution(plan):
    legs = db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id == plan.id)).all()
    if any(l.actual_departure or l.actual_arrival or l.status in {"completed", "in_progress"} for l in legs):
        return True
    checkpoints = db.session.scalars(select(OperationalCheckpoint).where(OperationalCheckpoint.route_plan_id == plan.id)).all()
    if any(c.actual_arrival_at or c.actual_departure_at or c.status in {"arrived", "departed", "completed"} for c in checkpoints):
        return True
    return any(authority.effective_occurrence(m) is not None or m.occurred_at is not None
        for m in db.session.scalars(select(Milestone).where(Milestone.route_plan_id == plan.id)))
