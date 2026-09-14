"""Bounded, read-only composition of authoritative shipment history sources."""

from sqlalchemy import func, literal, select, union_all

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import (
    DelayReason, ExceptionReason, Milestone, MilestoneEvent, OperationalAudit,
    OperationalDelay, OperationalException, OperationalShipment, OperationalWorkItem, RoutePlan,
)
from backend.external_reference_models import OperationalShipmentExternalReference
from backend.mdpm_models import DocumentReadinessAudit, OperationalDocumentRequirement
from backend.services.assigned_work_authorization import authorize_work_action
from backend.services.operational_service import OperationalError
from backend.services import operational_read_service as reads


DOCUMENT_ACTIONS = {
    "RequirementMaterialized", "ArtifactAssociated", "ArtifactAssociationSuperseded",
    "ArtifactAssociationRemoved", "ReviewStarted", "DocumentApproved",
    "DocumentRejected", "DocumentVerified", "ApplicabilityResolved",
    "OverrideGranted", "OverrideRevoked", "OverrideConsumed",
}
OMIT_AUDIT_ACTIONS = {
    "operational_shipment.created", "route_plan.created", "route_plan.replanned",
    "operational_delay.created", "operational_delay.resolved",
    "operational_exception.created", "operational_exception.resolved",
}


def _branch(kind, ident, phase, instant, predicate):
    return select(literal(kind).label("kind"), ident.label("id"),
                  literal(phase).label("phase"), instant.label("sort_at")).where(*predicate)


def _actor(user_id):
    user = db.session.get(ExpertUser, user_id) if user_id else None
    return (user.full_name or user.username) if user else None


def _base(kind, row, phase, category, business_type, occurred_at, recorded_at, actor_id):
    return {
        "history_id": f"{kind}:{row.id}:{phase}", "category": category,
        "classification": category,
        "business_type": business_type, "occurred_at": reads.iso(occurred_at),
        "recorded_at": reads.iso(recorded_at), "actor": _actor(actor_id),
        "source_entity_type": kind, "source_entity_id": getattr(row, "public_id", None),
        "reason_label": None, "note": None, "status": None,
        "route_revision": None, "relationship_status": None,
    }


def _item(shipment, kind, ident, phase):
    if kind == "shipment":
        row = shipment
        item = _base(kind, row, phase, "SHIPMENT", "operational_shipment.created",
                     None, row.created_at, row.created_by_user_id)
        item["source_type"] = row.source_type
        item["source_entity_id"] = row.public_id
        if row.shipment_request_id:
            request = db.session.get(ShipmentRequest, row.shipment_request_id)
            item["request_public_id"] = request.public_id if request else None
        return item
    if kind == "event":
        row = db.session.get(MilestoneEvent, ident)
        view = reads.event_view(row, shipment)
        category = "ROUTE_OCCURRENCE" if view["classification"] in {
            "PHYSICAL_OCCURRENCE", "VERIFICATION_DECISION", "CORRECTION"
        } else "EXECUTION_STAGE"
        milestone = db.session.get(Milestone, row.milestone_id)
        if milestone.checkpoint_id:
            category = "CHECKPOINT"
        item = _base(kind, row, phase, category, row.event_type,
                     row.occurred_at, row.recorded_at, row.actor_user_id)
        item.update(view)
        item["source_entity_id"] = row.public_id
        item["actor"] = _actor(row.actor_user_id)
        item["reason_label"] = row.reason
        item["note"] = row.note
        return item
    if kind == "revision":
        row = db.session.get(RoutePlan, ident)
        source_plan = db.session.get(RoutePlan, row.created_from_plan_id) if row.created_from_plan_id else None
        item = _base(kind, row, phase, "ROUTE",
                     "route_plan.replanned" if row.created_from_plan_id else "route_plan.created",
                     None, row.created_at, row.created_by_user_id)
        item.update({"classification": "REPLAN_REVISION", "id": row.id,
                     "route_revision": row.revision_number, "source_route_plan_id": row.created_from_plan_id,
                     "source_route_revision": source_plan.revision_number if source_plan else None,
                     "reason": row.replan_reason, "reason_label": row.replan_reason,
                     "status": row.status, "is_active": row.is_active,
                     "business_label": "Route changed" if row.created_from_plan_id else "Route prepared"})
        return item
    if kind in {"delay", "exception"}:
        model = OperationalDelay if kind == "delay" else OperationalException
        reason_model = DelayReason if kind == "delay" else ExceptionReason
        row = db.session.get(model, ident)
        reason = db.session.get(reason_model, row.reason_id)
        occurred = row.started_at if kind == "delay" else row.occurred_at
        resolution_audit = db.session.scalar(select(OperationalAudit).where(
            OperationalAudit.organization_id == shipment.organization_id,
            OperationalAudit.entity_type == model.__name__,
            OperationalAudit.entity_id == row.id,
            OperationalAudit.action == f"operational_{kind}.resolved",
        ).order_by(OperationalAudit.id.desc())) if phase == "resolved" else None
        item = _base(kind, row, phase, kind.upper(), f"operational_{kind}.{phase}",
                     row.resolved_at if phase == "resolved" else occurred,
                     row.created_at if phase == "created" else resolution_audit.recorded_at if resolution_audit else None,
                     row.resolved_by_user_id if phase == "resolved" else row.created_by_user_id)
        item.update({"reason_label": reason.fa_name or reason.en_name if reason else None,
                     "reason_code": reason.immutable_code if reason else None,
                     "note": row.note, "status": "resolved" if phase == "resolved" else "recorded",
                     "milestone_public_id": db.session.get(Milestone, row.milestone_id).public_id if row.milestone_id else None})
        return item
    if kind == "document":
        row = db.session.get(DocumentReadinessAudit, ident)
        req = db.session.get(OperationalDocumentRequirement, row.requirement_id) if row.requirement_id else None
        item = _base(kind, row, phase, "DOCUMENT", row.event_type, None, row.created_at, row.actor_user_id)
        item["document_label"] = (req.definition.name_fa or req.definition.title) if req else None
        item["source_entity_id"] = row.public_id
        item["reason_label"] = row.evidence.get("reason") if isinstance(row.evidence, dict) else None
        return item
    audit = db.session.get(OperationalAudit, ident)
    if audit.entity_type == "shipment_external_reference":
        ref = db.session.get(OperationalShipmentExternalReference, audit.entity_id)
        item = _base(kind, audit, phase, "REFERENCE", audit.action, None,
                     audit.recorded_at, audit.actor_user_id)
        item.update({"source_entity_id": ref.public_id, "reference_type_label": ref.reference_type.name_fa,
                     "reference_value": ref.raw_value, "status": ref.lifecycle_status,
                     "reason_label": ref.reason, "evidence_attached": ref.evidence_document_file_id is not None})
        if ref.supersedes_reference_id:
            previous = db.session.get(OperationalShipmentExternalReference, ref.supersedes_reference_id)
            item["supersedes_reference_public_id"] = previous.public_id if previous else None
        return item
    item = _base(kind, audit, phase, "WORK_ITEM" if audit.entity_type == "OperationalWorkItem" else "ROUTE" if audit.entity_type == "RoutePlan" else "AUDIT",
                 audit.action, None, audit.recorded_at, audit.actor_user_id)
    if audit.entity_type == "RoutePlan":
        plan = db.session.get(RoutePlan, audit.entity_id)
        item["route_revision"] = plan.revision_number if plan else None
    if audit.entity_type == "OperationalWorkItem":
        work = db.session.get(OperationalWorkItem, audit.entity_id)
        item["source_is_projection"] = True
        item["work_type"] = work.work_type if work else None
        item["status"] = "resolved" if "resolved" in audit.action else "open" if "opened" in audit.action else None
        item["reason_label"] = work.resolution_reason if work and "resolved" in audit.action else work.reason if work else None
    return item


def history(shipment, page=1, per_page=50, user=None):
    try:
        page, per_page = int(page), int(per_page)
    except (ValueError, TypeError) as exc:
        raise OperationalError("INVALID_PAGINATION", "Pagination must be numeric.", 422) from exc
    if page < 1 or not 1 <= per_page <= 100:
        raise OperationalError("INVALID_PAGINATION", "Page must be positive; per_page must be 1–100.", 422)
    org = shipment.organization_id
    milestone_ids = select(Milestone.id).where(Milestone.organization_id == org,
        Milestone.operational_shipment_id == shipment.id)
    branches = [
        _branch("shipment", OperationalShipment.id, "created", OperationalShipment.created_at,
                (OperationalShipment.id == shipment.id, OperationalShipment.organization_id == org)),
        _branch("event", MilestoneEvent.id, "recorded", MilestoneEvent.occurred_at,
                (MilestoneEvent.organization_id == org, MilestoneEvent.milestone_id.in_(milestone_ids))),
        _branch("revision", RoutePlan.id, "created", RoutePlan.created_at,
                (RoutePlan.operational_shipment_id == shipment.id,)),
    ]
    for kind, model, time_field in (("delay", OperationalDelay, OperationalDelay.started_at),
                                    ("exception", OperationalException, OperationalException.occurred_at)):
        predicate = (model.organization_id == org, model.operational_shipment_id == shipment.id)
        branches.append(_branch(kind, model.id, "created", time_field, predicate))
        branches.append(_branch(kind, model.id, "resolved", model.resolved_at,
                                (*predicate, model.resolved_at.is_not(None))))
    audit_ids = reads.audit_query(shipment).with_only_columns(OperationalAudit.id)
    branches.append(_branch("audit", OperationalAudit.id, "recorded", OperationalAudit.recorded_at,
        (OperationalAudit.id.in_(audit_ids), OperationalAudit.entity_type.not_in((
            "MilestoneEvent", "OperationalDelay", "OperationalException")),
         (OperationalAudit.entity_type != "RoutePlan") | (OperationalAudit.action == "route_plan.activated"),
         OperationalAudit.action.not_in(OMIT_AUDIT_ACTIONS),
         (OperationalAudit.entity_type != "OperationalWorkItem") |
         OperationalAudit.action.in_(("work_item.opened", "work_item.reopened", "work_item.resolved", "route_exception.opened", "route_exception.resolved")))))
    if shipment.source_type != "direct" and user is not None and authorize_work_action(user, shipment, "document_readiness.read").allowed:
        branches.append(_branch("document", DocumentReadinessAudit.id, "recorded", DocumentReadinessAudit.created_at,
            (DocumentReadinessAudit.organization_id == org,
             DocumentReadinessAudit.operational_shipment_id == shipment.id,
             DocumentReadinessAudit.event_type.in_(DOCUMENT_ACTIONS))))
    feed = union_all(*branches).subquery()
    total = db.session.scalar(select(func.count()).select_from(feed)) or 0
    rows = db.session.execute(select(feed).order_by(feed.c.sort_at.desc(), feed.c.kind,
        feed.c.phase, feed.c.id.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    items = [_item(shipment, row.kind, row.id, row.phase) for row in rows]
    return {"scope": "shipment_history", "current_route": reads.scope(reads.authority.active_plan(shipment)),
            "ordering": "business_time_desc_kind_phase_id; audit_only_uses_recorded_at",
            "items": items, "page": page, "per_page": per_page, "total": total,
            "has_more": page * per_page < total}
