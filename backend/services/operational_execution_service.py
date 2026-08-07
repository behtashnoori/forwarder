"""Bounded Release 1.9.0 operational execution commands and read models."""

from __future__ import annotations
from datetime import timezone
import hashlib
import json
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.extensions import db
from backend.operational_models import (
    DelayReason,
    ExceptionReason,
    Milestone,
    MilestoneEvent,
    OperationalAudit,
    OperationalDelay,
    OperationalException,
    OperationalShipment,
    Project,
    utcnow,
)
from backend.project_configuration_models import ProjectMilestoneDefinition
from backend.services.operational_service import (
    OperationalError,
    organization_for_user,
    require_permission,
    _parse_utc,
)

STATUSES = (
    "PENDING",
    "READY",
    "IN_PROGRESS",
    "COMPLETED",
    "SKIPPED",
    "CANCELLED",
    "BLOCKED",
)
TRANSITIONS = {
    "PENDING": {"READY", "BLOCKED", "SKIPPED", "CANCELLED"},
    "READY": {"IN_PROGRESS", "SKIPPED", "CANCELLED", "BLOCKED"},
    "IN_PROGRESS": {"COMPLETED", "BLOCKED", "CANCELLED"},
    "BLOCKED": {"READY", "PENDING", "IN_PROGRESS", "CANCELLED"},
}
EVENT_FOR = {
    "READY": "READY",
    "IN_PROGRESS": "STARTED",
    "COMPLETED": "COMPLETED",
    "SKIPPED": "SKIPPED",
    "CANCELLED": "CANCELLED",
    "BLOCKED": "BLOCKED",
}
REASON_TARGETS = {"BLOCKED", "SKIPPED", "CANCELLED"}


def _shipment(public_id: str, user: dict, permission="operational_execution.read"):
    require_permission(user, permission)
    org = organization_for_user(user["id"])
    row = db.session.scalar(
        select(OperationalShipment).where(
            OperationalShipment.public_id == public_id,
            OperationalShipment.organization_id == org,
        )
    )
    if row is None:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "Operational shipment was not found.", 404
        )
    return row


def _milestone(shipment, public_id: str, lock=False):
    query = select(Milestone).where(
        Milestone.public_id == public_id,
        Milestone.operational_shipment_id == shipment.id,
        Milestone.organization_id == shipment.organization_id,
    )
    row = db.session.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Milestone was not found.", 404)
    return row


def _audit(shipment, user, action, entity, entity_id, metadata=None):
    db.session.add(
        OperationalAudit(
            organization_id=shipment.organization_id,
            actor_user_id=user["id"],
            action=action,
            entity_type=entity,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
    )


def _event(
    m, user, event_type, effective_at=None, reason=None, note=None, supersedes=None
):
    effective = effective_at or utcnow()
    seed = (
        f"{event_type}:{m.public_id}:{m.version}:{user['id']}:{effective.isoformat()}"
    )
    row = MilestoneEvent(
        organization_id=m.organization_id,
        milestone_id=m.id,
        event_type=event_type,
        occurred_at=effective,
        actor_user_id=user["id"],
        reason=reason,
        note=note,
        supersedes_event_id=supersedes,
        idempotency_key=hashlib.sha256(seed.encode()).hexdigest()[:80],
        request_hash=hashlib.sha256(
            json.dumps(
                {
                    "event": event_type,
                    "effective": effective.isoformat(),
                    "reason": reason,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest(),
    )
    db.session.add(row)
    return row


def milestone_projection(m):
    return {
        "public_id": m.public_id,
        # Project-defined milestones are intentionally independent of routing.
        # The v2 execution API never exposes the internal numeric FK.
        "route_plan_public_id": None,
        "sequence": m.sequence,
        "milestone_type": m.milestone_type,
        "milestone_type_snapshot": m.milestone_type_snapshot,
        "expected_point_snapshot": m.expected_point_snapshot,
        "target_metadata": m.target_metadata,
        "status": m.lifecycle_status,
        "prior_active_status": m.prior_active_status,
        "planned_at": m.planned_at.isoformat() if m.planned_at else None,
        "started_at": m.started_at.isoformat() if m.started_at else None,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        "skipped_at": m.skipped_at.isoformat() if m.skipped_at else None,
        "cancelled_at": m.cancelled_at.isoformat() if m.cancelled_at else None,
        "blocked_at": m.blocked_at.isoformat() if m.blocked_at else None,
        "verification_state": m.verification_state,
        "version": m.version,
    }


def initialization_preview(shipment_id, user):
    shipment = _shipment(shipment_id, user)
    existing = db.session.scalars(
        select(Milestone)
        .where(
            Milestone.operational_shipment_id == shipment.id,
            Milestone.project_milestone_definition_id.is_not(None),
        )
        .order_by(Milestone.sequence)
    ).all()
    findings = []
    rows = []
    if shipment.project_id is None:
        findings.append(
            {
                "code": "PROJECT_REQUIRED",
                "message": "Shipment is not assigned to a Project.",
            }
        )
    definitions = (
        []
        if shipment.project_id is None
        else db.session.scalars(
            select(ProjectMilestoneDefinition)
            .where(ProjectMilestoneDefinition.project_id == shipment.project_id)
            .order_by(ProjectMilestoneDefinition.sequence)
        ).all()
    )
    active = [d for d in definitions if d.is_active]
    if not active:
        findings.append(
            {
                "code": "NO_ACTIVE_DEFINITIONS",
                "message": "Project has no active milestone definitions.",
            }
        )
    for d in definitions:
        mt = d.milestone_type
        point = d.project_logistics_point
        warnings = []
        if not d.is_active:
            warnings.append("INACTIVE_DEFINITION")
        if mt is None or not mt.is_active:
            warnings.append("MISSING_OR_INACTIVE_MILESTONE_TYPE")
        if point is not None and not point.is_active:
            warnings.append("INACTIVE_PROJECT_LOGISTICS_POINT")
        rows.append(
            {
                "definition_public_id": d.public_id,
                "sequence": d.sequence,
                "milestone_type": {
                    "public_id": mt.public_id,
                    "code": mt.immutable_code,
                    "fa_name": mt.fa_name,
                    "en_name": mt.en_name,
                }
                if mt
                else None,
                "expected_point": {
                    "public_id": point.public_id,
                    "label": point.display_label,
                    "role": point.project_role,
                }
                if point
                else None,
                "target_metadata": {
                    "target_duration_value": d.target_duration_value,
                    "warning_duration_value": d.warning_duration_value,
                    "duration_unit": d.duration_unit,
                    "required": d.is_required,
                },
                "warnings": warnings,
            }
        )
    invalid = any(
        r["warnings"] for r in rows if "INACTIVE_DEFINITION" not in r["warnings"]
    )
    return {
        "project_public_id": (
            db.session.get(Project, shipment.project_id).public_id
            if shipment.project_id
            else None
        ),
        "initialized": bool(existing),
        "existing_count": len(existing),
        "milestones": rows,
        "findings": findings,
        "confirmation_allowed": not existing and bool(active) and not invalid,
    }


def initialize(shipment_id, payload, user):
    shipment = _shipment(shipment_id, user, "operational_execution.manage")
    expected = payload.get("expected_shipment_version")
    if shipment.version != expected:
        raise OperationalError(
            "STALE_AGGREGATE_VERSION", "Shipment was changed by another operation.", 409
        )
    preview = initialization_preview(shipment_id, user)
    existing = db.session.scalars(
        select(Milestone)
        .where(
            Milestone.operational_shipment_id == shipment.id,
            Milestone.project_milestone_definition_id.is_not(None),
        )
        .order_by(Milestone.sequence)
    ).all()
    if existing:
        return existing, False
    if not preview["confirmation_allowed"]:
        raise OperationalError(
            "INITIALIZATION_NOT_ALLOWED",
            "Project milestone configuration is incomplete or inactive.",
            422,
        )
    definitions = db.session.scalars(
        select(ProjectMilestoneDefinition)
        .where(
            ProjectMilestoneDefinition.project_id == shipment.project_id,
            ProjectMilestoneDefinition.is_active.is_(True),
        )
        .order_by(ProjectMilestoneDefinition.sequence)
        .with_for_update()
    ).all()
    created = []
    for d in definitions:
        mt = d.milestone_type
        point = d.project_logistics_point
        m = Milestone(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id,
            route_plan_id=None,
            project_milestone_definition_id=d.id,
            milestone_type=mt.immutable_code,
            milestone_type_snapshot={
                "public_id": mt.public_id,
                "code": mt.immutable_code,
                "fa_name": mt.fa_name,
                "en_name": mt.en_name,
            },
            expected_point_id=point.id if point else None,
            expected_point_snapshot={
                "public_id": point.public_id,
                "label": point.display_label,
                "role": point.project_role,
            }
            if point
            else None,
            target_metadata={
                "target_duration_value": d.target_duration_value,
                "warning_duration_value": d.warning_duration_value,
                "duration_unit": d.duration_unit,
                "required": d.is_required,
            },
            sequence=d.sequence,
            lifecycle_status="PENDING",
            verification_state="planned",
        )
        db.session.add(m)
        db.session.flush()
        _event(m, user, "INITIALIZED")
        created.append(m)
    shipment.version += 1
    _audit(
        shipment,
        user,
        "operational_execution.initialized",
        "OperationalShipment",
        shipment.id,
        {"count": len(created)},
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise OperationalError(
            "INITIALIZATION_CONFLICT",
            "Milestones were initialized by another operation.",
            409,
        )
    return created, True


def list_milestones(shipment_id, user):
    shipment = _shipment(shipment_id, user)
    return [
        milestone_projection(m)
        for m in db.session.scalars(
            select(Milestone)
            .where(
                Milestone.operational_shipment_id == shipment.id,
                Milestone.project_milestone_definition_id.is_not(None),
            )
            .order_by(Milestone.sequence, Milestone.id)
        ).all()
    ]


def transition(shipment_id, milestone_id, payload, user):
    shipment = _shipment(shipment_id, user, "operational_execution.manage")
    m = _milestone(shipment, milestone_id, True)
    if m.version != payload.get("expected_version"):
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Milestone was changed by another operation.",
            409,
        )
    target = str(payload.get("target_status") or "").upper()
    reason = str(payload.get("reason") or "").strip() or None
    allowed = TRANSITIONS.get(m.lifecycle_status, set())
    if m.lifecycle_status == "BLOCKED" and target not in {
        m.prior_active_status,
        "READY",
        "CANCELLED",
    }:
        allowed = set()
    if target not in allowed:
        raise OperationalError(
            "INVALID_MILESTONE_TRANSITION",
            f"{m.lifecycle_status} cannot transition to {target}.",
            409,
        )
    if target in REASON_TARGETS and not reason:
        raise OperationalError(
            "STRUCTURED_REASON_REQUIRED", "A reason is required.", 422
        )
    # MDPM readiness is evaluated under the same transaction and locks as the
    # authoritative milestone mutation. It remains a projection, never a status.
    from backend.services import document_readiness_service as readiness_service
    readiness = readiness_service.transition_readiness(shipment, m, target, user)
    if not readiness["allowed"]:
        readiness_service._audit(
            shipment, user, "TransitionBlocked", None, m,
            {"target_status": target, "blocking_requirements": readiness["blocking_requirements"]},
        )
        db.session.commit()
        exc = OperationalError("TRANSITION_READINESS_BLOCKED", "Document readiness blocks this transition.", 409)
        exc.fields = readiness
        raise exc
    effective = (
        _parse_utc(payload.get("effective_at"), "effective_at")
        if payload.get("effective_at")
        else utcnow()
    )
    previous = m.lifecycle_status
    if target == "BLOCKED":
        m.prior_active_status = previous
        m.blocked_at = effective
    if previous == "BLOCKED" and target != "CANCELLED":
        event_type = "UNBLOCKED"
        m.blocked_at = None
    else:
        event_type = EVENT_FOR[target]
    m.lifecycle_status = target
    m.version += 1
    if target == "IN_PROGRESS":
        m.started_at = effective
    elif target == "COMPLETED":
        m.completed_at = effective
    elif target == "SKIPPED":
        m.skipped_at = effective
    elif target == "CANCELLED":
        m.cancelled_at = effective
    _event(m, user, event_type, effective, reason, payload.get("note"))
    _audit(
        shipment,
        user,
        "milestone.transitioned",
        "Milestone",
        m.id,
        {"from": previous, "to": target},
    )
    for override in readiness["_overrides"]:
        override.state = "CONSUMED"
        override.consumed_at = effective
        readiness_service._audit(
            shipment, user, "OverrideConsumed",
            db.session.get(readiness_service.OperationalDocumentRequirement, override.requirement_id), m,
            {"override_public_id": override.public_id, "target_status": target},
        )
    readiness_service._audit(
        shipment, user, "TransitionAllowed", None, m,
        {"target_status": target, "override_public_ids": [o.public_id for o in readiness["_overrides"]]},
    )
    db.session.commit()
    return milestone_projection(m)


def reopen(shipment_id, milestone_id, payload, user):
    shipment = _shipment(shipment_id, user, "operational_event.correct")
    m = _milestone(shipment, milestone_id, True)
    if m.version != payload.get("expected_version"):
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Milestone was changed by another operation.",
            409,
        )
    reason = str(payload.get("reason") or "").strip()
    if m.lifecycle_status not in {"COMPLETED", "SKIPPED", "CANCELLED"} or not reason:
        raise OperationalError(
            "INVALID_REOPEN",
            "A terminal milestone and explicit reason are required.",
            409,
        )
    previous = m.lifecycle_status
    m.lifecycle_status = "READY"
    m.completed_at = m.skipped_at = m.cancelled_at = None
    m.version += 1
    _event(m, user, "REOPENED", reason=reason)
    _audit(
        shipment,
        user,
        "milestone.reopened",
        "Milestone",
        m.id,
        {"from": previous, "reason": reason},
    )
    db.session.commit()
    return milestone_projection(m)


def events(shipment_id, user):
    shipment = _shipment(shipment_id, user)
    mids = select(Milestone.id).where(Milestone.operational_shipment_id == shipment.id)
    rows = db.session.scalars(
        select(MilestoneEvent)
        .where(
            MilestoneEvent.organization_id == shipment.organization_id,
            MilestoneEvent.milestone_id.in_(mids),
        )
        .order_by(
            MilestoneEvent.occurred_at, MilestoneEvent.recorded_at, MilestoneEvent.id
        )
    ).all()
    milestones = (
        {
            row.id: row
            for row in db.session.scalars(
                select(Milestone).where(
                    Milestone.id.in_({event.milestone_id for event in rows})
                )
            ).all()
        }
        if rows
        else {}
    )
    event_by_id = {row.id: row for row in rows}
    return [
        {
            "public_id": e.public_id,
            "milestone_public_id": milestones[e.milestone_id].public_id,
            "event_type": e.event_type,
            "effective_at": e.occurred_at.isoformat(),
            "recorded_at": e.recorded_at.isoformat(),
            "source_channel": e.source_channel,
            "reason": e.reason,
            "note": e.note,
            "verification_state": e.verification_state,
            "verified_at": e.verified_at.isoformat() if e.verified_at else None,
            "correction_of_event_public_id": event_by_id[
                e.supersedes_event_id
            ].public_id
            if e.supersedes_event_id
            else None,
        }
        for e in rows
    ]


def create_event(shipment_id, milestone_id, payload, user):
    shipment = _shipment(shipment_id, user, "operational_event.create")
    milestone = _milestone(shipment, milestone_id, True)
    if milestone.version != payload.get("expected_version"):
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Milestone was changed by another operation.",
            409,
        )
    effective = _parse_utc(payload.get("effective_at"), "effective_at")
    event = _event(
        milestone,
        user,
        "reported",
        effective,
        note=payload.get("note"),
    )
    milestone.occurred_at = effective
    milestone.verification_state = "reported"
    milestone.version += 1
    _audit(shipment, user, "milestone_event.created", "MilestoneEvent", milestone.id)
    db.session.commit()
    return event


def correct_event(shipment_id, event_id, payload, user):
    shipment = _shipment(shipment_id, user, "operational_event.correct")
    original = db.session.scalar(
        select(MilestoneEvent)
        .where(
            MilestoneEvent.public_id == event_id,
            MilestoneEvent.organization_id == shipment.organization_id,
        )
        .with_for_update()
    )
    if original is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Event was not found.", 404)
    milestone = _milestone(
        shipment, db.session.get(Milestone, original.milestone_id).public_id, True
    )
    if milestone.version != payload.get("expected_version"):
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "Milestone was changed by another operation.",
            409,
        )
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise OperationalError(
            "CORRECTION_REASON_REQUIRED", "Correction reason is required.", 422
        )
    effective = _parse_utc(payload.get("effective_at"), "effective_at")
    corrected = _event(
        milestone,
        user,
        "CORRECTED",
        effective,
        reason,
        payload.get("note"),
        original.id,
    )
    db.session.flush()
    milestone.occurred_at = effective
    milestone.verification_state = "reported"
    milestone.version += 1
    _audit(shipment, user, "milestone_event.corrected", "MilestoneEvent", corrected.id)
    db.session.commit()
    return corrected


def verify_event(shipment_id, event_id, payload, user):
    shipment = _shipment(shipment_id, user, "operational_event.verify")
    event = db.session.scalar(
        select(MilestoneEvent)
        .where(
            MilestoneEvent.public_id == event_id,
            MilestoneEvent.organization_id == shipment.organization_id,
        )
        .with_for_update()
    )
    if (
        event is None
        or db.session.get(Milestone, event.milestone_id).operational_shipment_id
        != shipment.id
    ):
        raise OperationalError("RESOURCE_NOT_FOUND", "Event was not found.", 404)
    if event.actor_user_id == user["id"]:
        raise OperationalError(
            "SELF_VERIFICATION_FORBIDDEN",
            "The asserting actor cannot verify this event.",
            403,
        )
    if event.verification_state == "verified":
        return events(shipment_id, user)
    event.verification_state = "verified"
    event.verified_by_user_id = user["id"]
    event.verified_at = utcnow()
    m = db.session.get(Milestone, event.milestone_id)
    _event(m, user, "VERIFIED", event.occurred_at, supersedes=event.id)
    _audit(shipment, user, "milestone_event.verified", "MilestoneEvent", event.id)
    db.session.commit()
    return events(shipment_id, user)


def progress(shipment_id, user):
    shipment = _shipment(shipment_id, user)
    rows = db.session.scalars(
        select(Milestone)
        .where(
            Milestone.operational_shipment_id == shipment.id,
            Milestone.project_milestone_definition_id.is_not(None),
        )
        .order_by(Milestone.sequence)
    ).all()
    counts = {s: 0 for s in STATUSES}
    for m in rows:
        counts[m.lifecycle_status] += 1
    done = counts["COMPLETED"] + counts["SKIPPED"]
    denominator = len(rows) - counts["CANCELLED"]
    percentage = round(done * 100 / denominator, 2) if denominator else 0
    current = next(
        (
            m
            for m in rows
            if m.lifecycle_status not in {"COMPLETED", "SKIPPED", "CANCELLED"}
        ),
        None,
    )
    delays = db.session.scalar(
        select(db.func.count())
        .select_from(OperationalDelay)
        .where(
            OperationalDelay.operational_shipment_id == shipment.id,
            OperationalDelay.organization_id == shipment.organization_id,
            OperationalDelay.resolved_at.is_(None),
        )
    )
    exceptions = db.session.scalar(
        select(db.func.count())
        .select_from(OperationalException)
        .where(
            OperationalException.operational_shipment_id == shipment.id,
            OperationalException.organization_id == shipment.organization_id,
            OperationalException.resolved_at.is_(None),
        )
    )
    return {
        "initialized": bool(rows),
        "total": len(rows),
        "counts": counts,
        "current_milestone": milestone_projection(current) if current else None,
        "completion_percentage": percentage,
        "completion_rule": "(COMPLETED + SKIPPED) / (total - CANCELLED) * 100; zero when denominator is zero",
        "active_delay_count": delays,
        "active_exception_count": exceptions,
    }


def reason_collection(kind, user, payload=None):
    permission = (
        f"{kind}_reason.manage" if payload is not None else "operational_execution.read"
    )
    require_permission(user, permission)
    org = organization_for_user(user["id"])
    model = DelayReason if kind == "delay" else ExceptionReason
    if payload is not None:
        code = str(payload.get("immutable_code") or "").strip().upper()
        if not code:
            raise OperationalError(
                "VALIDATION_FAILED", "immutable_code is required.", 422
            )
        row = model(
            organization_id=org,
            immutable_code=code,
            fa_name=str(payload.get("fa_name") or "").strip(),
            en_name=str(payload.get("en_name") or "").strip(),
            definition=payload.get("definition"),
            display_order=int(payload.get("display_order", 0)),
            created_by_user_id=user["id"],
            updated_by_user_id=user["id"],
        )
        db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise OperationalError(
                "DUPLICATE_REASON_CODE", "Reason code already exists.", 409
            )
    rows = db.session.scalars(
        select(model)
        .where(model.organization_id == org)
        .order_by(model.display_order, model.immutable_code)
    ).all()
    return [_reason_view(r) for r in rows]


def _reason_view(r):
    return {
        "public_id": r.public_id,
        "immutable_code": r.immutable_code,
        "fa_name": r.fa_name,
        "en_name": r.en_name,
        "definition": r.definition,
        "display_order": r.display_order,
        "is_active": r.is_active,
        "version": r.version,
    }


def update_reason(kind, public_id, payload, user):
    require_permission(user, f"{kind}_reason.manage")
    org = organization_for_user(user["id"])
    model = DelayReason if kind == "delay" else ExceptionReason
    row = db.session.scalar(
        select(model)
        .where(model.public_id == public_id, model.organization_id == org)
        .with_for_update()
    )
    if row is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "Reason was not found.", 404)
    if row.version != payload.get("version"):
        raise OperationalError(
            "STALE_AGGREGATE_VERSION", "Reason was changed by another operation.", 409
        )
    if "immutable_code" in payload and payload["immutable_code"] != row.immutable_code:
        raise OperationalError("IMMUTABLE_CODE", "Reason code cannot be changed.", 422)
    for field in ("fa_name", "en_name", "definition", "display_order", "is_active"):
        if field in payload:
            setattr(row, field, payload[field])
    row.updated_by_user_id = user["id"]
    row.version += 1
    db.session.commit()
    return _reason_view(row)


def condition_collection(kind, shipment_id, user, payload=None):
    shipment = _shipment(
        shipment_id,
        user,
        "operational_execution.manage"
        if payload is not None
        else "operational_execution.read",
    )
    model = OperationalDelay if kind == "delay" else OperationalException
    reason_model = DelayReason if kind == "delay" else ExceptionReason
    instant = "started_at" if kind == "delay" else "occurred_at"
    if payload is not None:
        reason = db.session.scalar(
            select(reason_model).where(
                reason_model.public_id == payload.get("reason_public_id"),
                reason_model.organization_id == shipment.organization_id,
                reason_model.is_active.is_(True),
            )
        )
        if reason is None:
            raise OperationalError(
                "RESOURCE_NOT_FOUND", "Active governed reason was not found.", 404
            )
        milestone = None
        if payload.get("milestone_public_id"):
            milestone = _milestone(shipment, payload["milestone_public_id"])
        row = model(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id,
            milestone_id=milestone.id if milestone else None,
            reason_id=reason.id,
            note=payload.get("note"),
            created_by_user_id=user["id"],
            **{instant: _parse_utc(payload.get(instant), instant)},
        )
        db.session.add(row)
        db.session.flush()
        _audit(shipment, user, f"operational_{kind}.created", model.__name__, row.id)
        db.session.commit()
    rows = db.session.scalars(
        select(model)
        .where(
            model.organization_id == shipment.organization_id,
            model.operational_shipment_id == shipment.id,
        )
        .order_by(getattr(model, instant).desc())
    ).all()
    return [_condition_view(r, reason_model, instant) for r in rows]


def _condition_view(r, reason_model, instant):
    reason = db.session.get(reason_model, r.reason_id)
    milestone = db.session.get(Milestone, r.milestone_id) if r.milestone_id else None
    began = getattr(r, instant)
    began_utc = began.replace(tzinfo=began.tzinfo or timezone.utc)
    ended = r.resolved_at or utcnow()
    ended_utc = ended.replace(tzinfo=ended.tzinfo or timezone.utc)
    return {
        "public_id": r.public_id,
        "milestone_public_id": milestone.public_id if milestone else None,
        "reason": _reason_view(reason),
        instant: began.isoformat(),
        "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        "active": r.resolved_at is None,
        "note": r.note,
        "duration_seconds": max(0, int((ended_utc - began_utc).total_seconds())),
        "version": r.version,
    }


def resolve_condition(kind, shipment_id, public_id, payload, user):
    shipment = _shipment(shipment_id, user, "operational_execution.manage")
    model = OperationalDelay if kind == "delay" else OperationalException
    reason_model = DelayReason if kind == "delay" else ExceptionReason
    instant = "started_at" if kind == "delay" else "occurred_at"
    row = db.session.scalar(
        select(model)
        .where(
            model.public_id == public_id,
            model.organization_id == shipment.organization_id,
            model.operational_shipment_id == shipment.id,
        )
        .with_for_update()
    )
    if row is None:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", f"{kind.title()} was not found.", 404
        )
    if row.version != payload.get("expected_version"):
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            f"{kind.title()} was changed by another operation.",
            409,
        )
    if row.resolved_at is not None:
        return _condition_view(row, reason_model, instant)
    resolved = (
        _parse_utc(payload.get("resolved_at"), "resolved_at")
        if payload.get("resolved_at")
        else utcnow()
    )
    began = getattr(row, instant).replace(
        tzinfo=getattr(row, instant).tzinfo or timezone.utc
    )
    if resolved < began:
        raise OperationalError(
            "INVALID_TIMESTAMP_ORDER", "Resolution cannot precede occurrence.", 422
        )
    row.resolved_at = resolved
    row.resolved_by_user_id = user["id"]
    row.version += 1
    _audit(shipment, user, f"operational_{kind}.resolved", model.__name__, row.id)
    db.session.commit()
    return _condition_view(row, reason_model, instant)
