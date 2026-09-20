"""Slice 2 bounded source adapters. No cards, aggregation, API or writes.

Each entry point receives Slice 1 lineage, refreshes current authority before
source evaluation and again before disclosure, in the caller's read transaction.
An empty tuple is successful evaluation with no applicable disclosable reason.
Failures raise an opaque exception, so callers cannot mistake them for all-clear.
Direct shipments use existing MDPM NOT_APPLICABLE semantics, without invented
requirements. Public source services and capabilities remain independently gated.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging

from sqlalchemy import select

from backend.extensions import db
from backend.models import CaseDocumentFile, CaseDocumentRequirement, DocumentDefinition, DocumentDefinitionStage
from backend.mdpm_models import ArtifactAssociation, DocumentAssessment, OperationalDocumentRequirement, TransitionOverride
from backend.operational_models import (
    CanonicalLocation, DelayReason, ExceptionReason, Milestone, OperationalCheckpoint,
    OperationalDelay, OperationalException, OperationalShipment, OperationalWorkItem, RouteLeg, RoutePlan,
)
from backend.services import document_readiness_service as readiness
from backend.services.control_tower_scope import (
    ControlTowerResponsibilityInvariant,
    ControlTowerScopeDenied,
    refresh_summary_context,
    refresh_summary_contexts,
)
from backend.services.control_tower_oip import VerifiedEnrichment, verified_enrichments
from backend.services.control_tower_translation import (
    AttentionLevel, Semantic, SUPPORTED_BLOCKERS, TimeContext, URGENT_EXPLANATION,
    safe_display_label, time_context, translate, translate_blocker, utc,
)
from backend.operational_models import utcnow

_logger = logging.getLogger("control_tower.sources")
_WORK = {
    "CHECKPOINT_OVERDUE": Semantic.CHECKPOINT_FOLLOW_UP,
    "ROUTE_DEPENDENCY_BLOCKED": Semantic.DEPENDENCY_BLOCKED,
    "REPLAN_REQUIRED": Semantic.REPLAN_REQUIRED,
    "OVERDUE_MILESTONE": Semantic.OVERDUE_MILESTONE_FOLLOW_UP,
}


class ControlTowerSourceFailure(Exception):
    def __init__(self, source):
        self.source = source
        super().__init__("Control Tower source evaluation is unavailable.")


@dataclass(frozen=True)
class SourceIdentity:
    """Internal validation/dedup only; never future frontend provenance."""
    family: str
    key: str
    version: int
    linkage: tuple = ()


@dataclass(frozen=True)
class AttentionReason:
    semantic: Semantic
    attention_level: AttentionLevel
    title: str
    explanation: str
    time_context: tuple[TimeContext, ...]
    source_identity: SourceIdentity
    enrichment: tuple[VerifiedEnrichment, ...] = ()
    # Recognized work cohort only, for later same-model comparison; no score.
    source_severity: str | None = None


def _one(query):
    return db.session.scalar(query.execution_options(populate_existing=True))


def _all(query):
    return db.session.scalars(query.execution_options(populate_existing=True)).all()


def _evaluate(source, actor, context, reader, at):
    with db.session.no_autoflush:
        current = refresh_summary_context(actor, context)
        try:
            result = reader(actor, current, utc(at or utcnow()))
        except (ControlTowerScopeDenied, ControlTowerResponsibilityInvariant):
            raise
        except Exception as exc:
            # Restricted diagnostic has only a class, never SQL/notes/payload.
            _logger.error("control_tower_source_failure source=%s error_type=%s", source, type(exc).__name__)
            raise ControlTowerSourceFailure(source) from None
        fresh = refresh_summary_context(actor, current)
        if (fresh.organization_id, fresh.shipment_public_id, fresh.root_type, fresh.root_id,
                fresh.responsible_expert_id) != (
                current.organization_id, current.shipment_public_id, current.root_type,
                current.root_id, current.responsible_expert_id):
            raise ControlTowerScopeDenied()
        return result


def _shipment(context):
    return _one(select(OperationalShipment).where(
        OperationalShipment.id == context.shipment_id,
        OperationalShipment.organization_id == context.organization_id,
    ))


def _reason(semantic, identity, *, label=None, checkpoint_type=None,
            level=AttentionLevel.FOLLOW_UP, times=(), enrichment=(), source_severity=None):
    title, explanation = translate(semantic, label=label, checkpoint_type=checkpoint_type)
    if any(e.promotes_urgent for e in enrichment):
        level = AttentionLevel.URGENT
        explanation += " " + URGENT_EXPLANATION
    return AttentionReason(semantic, level, title, explanation,
                           tuple(t for t in times if t is not None), identity, enrichment, source_severity)


def _enrich(actor, context, shipment, **kwargs):
    # The single-source adapter revalidates around this call. The batched
    # composer revalidates the whole bounded set before and after evaluation.
    return verified_enrichments(context, shipment, **kwargs)


def evaluate_active_execution(actor, context, *, at=None):
    return _evaluate("active_execution", actor, context, _active_execution, at)


def _active_execution(actor, context, at, *, source_rows=None):
    shipment = _shipment(context)
    reasons = []
    for model, reason_model, semantic, field, kind in (
        (OperationalDelay, DelayReason, Semantic.ACTIVE_DELAY, "started_at", "delay_start"),
        (OperationalException, ExceptionReason, Semantic.ACTIVE_EXCEPTION, "occurred_at", "exception_occurrence"),
    ):
        # Each family is separately governed before reading its source rows.
        if refresh_summary_context(actor, context) != context:
            raise ControlTowerScopeDenied()
        rows = source_rows[model] if source_rows is not None else _all(select(model).where(
            model.organization_id == context.organization_id,
            model.operational_shipment_id == context.shipment_id,
            model.resolved_at.is_(None),
        ))
        for row in rows:
            label = _one(select(reason_model.fa_name).where(
                reason_model.id == row.reason_id,
                reason_model.organization_id == context.organization_id,
            ))
            if label is None or row.milestone_id and not _milestone(context, row.milestone_id):
                continue
            enrichment = _enrich(actor, context, shipment,
                situation_type="ACTIVE_DELAY_OR_EXCEPTION", source_type=model.__name__,
                source_public_id=row.public_id, source_version=row.version,
                dimensions={"source_type": model.__name__, "source_public_id": row.public_id},
                occurred_at=getattr(row, field), at=at)
            reasons.append(_reason(semantic, SourceIdentity(model.__name__, row.public_id, row.version),
                label=label, times=(time_context(kind, getattr(row, field)),), enrichment=enrichment))
    return tuple(reasons)


def _active_plan(context, plan_id):
    return _one(select(RoutePlan).where(
        RoutePlan.id == plan_id, RoutePlan.operational_shipment_id == context.shipment_id,
        RoutePlan.is_active.is_(True), RoutePlan.status == "active",
    )) if plan_id else None


def _milestone(context, milestone_id):
    return _one(select(Milestone).where(
        Milestone.id == milestone_id, Milestone.organization_id == context.organization_id,
        Milestone.operational_shipment_id == context.shipment_id,
    )) if milestone_id else None


def _checkpoint(plan, checkpoint_id):
    checkpoint = _one(select(OperationalCheckpoint).where(
        OperationalCheckpoint.id == checkpoint_id,
        OperationalCheckpoint.route_plan_id == plan.id,
        OperationalCheckpoint.status != "cancelled",
    )) if checkpoint_id else None
    if checkpoint and checkpoint.route_leg_id and not _one(select(RouteLeg.id).where(
        RouteLeg.id == checkpoint.route_leg_id, RouteLeg.route_plan_id == plan.id,
        RouteLeg.status != "cancelled",
    )):
        return None
    return checkpoint


def _checkpoint_due(checkpoint):
    return (checkpoint.projected_arrival_at or checkpoint.planned_arrival_at
            or checkpoint.projected_departure_at or checkpoint.planned_departure_at)


def evaluate_open_work(actor, context, *, at=None):
    return _evaluate("open_work", actor, context, _open_work, at)


def _open_work(actor, context, at, *, source_rows=None):
    shipment = _shipment(context)
    rows = source_rows if source_rows is not None else _all(select(OperationalWorkItem).where(
        OperationalWorkItem.organization_id == context.organization_id,
        OperationalWorkItem.operational_shipment_id == context.shipment_id,
        OperationalWorkItem.status == "open", OperationalWorkItem.work_type.in_(tuple(_WORK)),
    ))
    result, seen = [], set()
    for row in rows:
        if row.id in seen:
            continue
        seen.add(row.id)
        due, label, checkpoint_type = None, None, None
        dimensions = {"work_type": row.work_type, "milestone_id": row.milestone_id,
                      "checkpoint_id": row.checkpoint_id, "route_plan_id": row.route_plan_id}
        if row.work_type == "OVERDUE_MILESTONE":
            milestone = _milestone(context, row.milestone_id)
            plan = _active_plan(context, milestone.route_plan_id) if milestone else None
            if (not milestone or not plan
                    or milestone.verification_state == "verified"
                    or milestone.lifecycle_status in {"COMPLETED", "SKIPPED", "CANCELLED"}):
                continue
            if milestone.checkpoint_id and not _checkpoint(plan, milestone.checkpoint_id):
                continue
            if milestone.route_leg_id and not _one(select(RouteLeg.id).where(
                RouteLeg.id == milestone.route_leg_id, RouteLeg.route_plan_id == plan.id,
                RouteLeg.status != "cancelled",
            )):
                continue
            snapshot = milestone.milestone_type_snapshot or {}
            label = snapshot.get("fa_name") if isinstance(snapshot, dict) else None
            if utc(row.due_at) == utc(milestone.planned_at):
                due = row.due_at
            source_type, source_public_id, source_version = "OperationalMilestoneDue", milestone.public_id, milestone.version
            situation_type = "NEXT_MILESTONE_OVERDUE"
        else:
            plan = _active_plan(context, row.route_plan_id)
            checkpoint = _checkpoint(plan, row.checkpoint_id) if plan else None
            if not checkpoint:
                continue
            checkpoint_type = checkpoint.checkpoint_type
            label = _one(select(CanonicalLocation.display_name).where(CanonicalLocation.id == checkpoint.canonical_location_id))
            if row.work_type != "ROUTE_DEPENDENCY_BLOCKED" and utc(row.due_at) == utc(_checkpoint_due(checkpoint)):
                due = row.due_at
            source_type, source_public_id, source_version = "OperationalWorkItem", f"owi-{row.id}", row.version
            situation_type = row.work_type
        level = AttentionLevel.FOLLOW_UP
        # Only the existing route producer's comparable critical cohort.
        if row.work_type in {"ROUTE_DEPENDENCY_BLOCKED", "REPLAN_REQUIRED"} and row.severity == "critical":
            level = AttentionLevel.URGENT
        enrichment = ()
        # Invalid/stale authoritative due cannot support milestone enrichment.
        if row.work_type == "ROUTE_DEPENDENCY_BLOCKED" or due is not None:
            enrichment = _enrich(actor, context, shipment, situation_type=situation_type,
                source_type=source_type, source_public_id=source_public_id, source_version=source_version,
                dimensions=dimensions, occurred_at=row.detected_at, due_at=row.due_at,
                authoritative_due=due is not None, work_item_id=row.id, at=at)
        result.append(_reason(_WORK[row.work_type],
            SourceIdentity("OperationalWorkItem", str(row.id), row.version,
                           (row.work_type, row.route_plan_id, row.checkpoint_id, row.milestone_id)),
            label=label, checkpoint_type=checkpoint_type, level=level,
            times=(time_context("expected_due", due), time_context("work_open", row.detected_at)),
            enrichment=enrichment, source_severity=row.severity if row.severity in {"critical", "warning"} else None))
    return tuple(result)


def evaluate_bounded_sources(actor, contexts, *, at=None):
    """Composition-only batch of existing A/B base queries, never new sources.

    Refresh every supplied lineage before materializing any source. Each
    adapter still refreshes before evaluation/enrichment and after disclosure;
    prefetched rows are private to this read transaction, never an authority
    cache. C retains its existing bounded read-only applicability evaluator.
    A batch failure aborts the whole evaluation, never partial coverage.
    """
    with db.session.no_autoflush:
        contexts = tuple(contexts)
        current = refresh_summary_contexts(actor, contexts)
        if current != contexts:
            raise ControlTowerScopeDenied()
        if not current:
            return ()
        organizations = {c.organization_id for c in current}
        if len(organizations) != 1:
            raise ControlTowerScopeDenied()
        organization_id, = organizations
        shipment_ids = tuple(c.shipment_id for c in current)
        at = utc(at or utcnow())
        grouped = {model: {shipment_id: [] for shipment_id in shipment_ids}
                   for model in (OperationalDelay, OperationalException, OperationalWorkItem)}
        try:
            for model in grouped:
                query = select(model).where(
                    model.organization_id == organization_id,
                    model.operational_shipment_id.in_(shipment_ids),
                )
                if model is OperationalWorkItem:
                    query = query.where(model.status == "open", model.work_type.in_(tuple(_WORK)))
                else:
                    query = query.where(model.resolved_at.is_(None))
                for row in _all(query):
                    grouped[model][row.operational_shipment_id].append(row)
        except Exception as exc:
            _logger.error("control_tower_source_failure source=bounded_batch error_type=%s", type(exc).__name__)
            raise ControlTowerSourceFailure("bounded_batch") from None
        result = []
        for context in current:
            execution_rows = {model: grouped[model][context.shipment_id]
                              for model in (OperationalDelay, OperationalException)}
            work_rows = grouped[OperationalWorkItem][context.shipment_id]
            # Readers are fixed private implementations. Authority for the
            # complete set was refreshed above and is refreshed again below.
            execution = _active_execution(
                actor, context, at, source_rows=execution_rows
            )
            work = _open_work(actor, context, at, source_rows=work_rows)
            readiness_reasons = _readiness(actor, context, at)
            result.append((context, execution + work + readiness_reasons))
        if refresh_summary_contexts(actor, current) != current:
            raise ControlTowerScopeDenied()
        return tuple(result)


def evaluate_readiness(actor, context, *, at=None):
    return _evaluate("readiness", actor, context, _readiness, at)


def _validate_readiness_links(context, shipment, milestone, target):
    """Certify evaluator relationships before it can consume artifact state.

    Refresh ORM state as well: the existing evaluator uses identity-map-backed
    relationships. Foreign artifacts/assessments are invalid evaluation, never
    ingredients for a translated blocker or a successful empty result.
    """
    requirements = _all(select(OperationalDocumentRequirement).where(
        OperationalDocumentRequirement.organization_id == context.organization_id,
        OperationalDocumentRequirement.operational_shipment_id == context.shipment_id,
        OperationalDocumentRequirement.target_milestone_type == milestone.milestone_type,
        OperationalDocumentRequirement.target_status == target,
        OperationalDocumentRequirement.is_active.is_(True),
    ))
    labels = {}
    for req in requirements:
        _all(select(TransitionOverride).where(
            TransitionOverride.organization_id == context.organization_id,
            TransitionOverride.operational_shipment_id == context.shipment_id,
            TransitionOverride.requirement_id == req.id,
            TransitionOverride.milestone_id == milestone.id,
            TransitionOverride.target_status == target,
        ))
        definition = _one(select(DocumentDefinition).where(DocumentDefinition.id == req.document_definition_id))
        if not definition:
            raise ValueError("Invalid requirement definition")
        financial_stage = _one(select(DocumentDefinitionStage.id).where(
            DocumentDefinitionStage.document_definition_id == definition.id,
            DocumentDefinitionStage.stage_code == "PAYMENT_FINANCE",
        ))
        labels[req.public_id] = (None if definition.family_code == "FINANCE" or financial_stage
                                 else safe_display_label(definition.title))
        associations = _all(select(ArtifactAssociation).where(
            ArtifactAssociation.requirement_id == req.id, ArtifactAssociation.state == "ACTIVE",
        ))
        for assoc in associations:
            if assoc.organization_id != context.organization_id:
                raise ValueError("Invalid artifact tenant")
            artifact = _one(select(CaseDocumentFile).where(
                CaseDocumentFile.id == assoc.document_file_id,
                CaseDocumentFile.operational_organization_id == context.organization_id,
                CaseDocumentFile.shipment_request_id == shipment.shipment_request_id,
            ))
            if not artifact:
                raise ValueError("Invalid artifact linkage")
            case_requirement = _one(select(CaseDocumentRequirement).where(
                CaseDocumentRequirement.id == artifact.case_requirement_id,
                CaseDocumentRequirement.operational_organization_id == context.organization_id,
                CaseDocumentRequirement.shipment_request_id == shipment.shipment_request_id,
                CaseDocumentRequirement.source_definition_id == req.document_definition_id,
            ))
            if not case_requirement:
                raise ValueError("Invalid artifact definition")
            assessments = _all(select(DocumentAssessment).where(DocumentAssessment.association_id == assoc.id))
            if any(a.organization_id != context.organization_id for a in assessments):
                raise ValueError("Invalid assessment tenant")
    return labels


def _readiness(actor, context, at):
    shipment = _shipment(context)
    if shipment.source_type == "direct":
        return ()
    # Exact selection/target semantics of existing next_readiness; call its
    # existing transition evaluator, without invoking its public capability gate.
    milestone = _one(select(Milestone).where(
        Milestone.operational_shipment_id == context.shipment_id,
        Milestone.organization_id == context.organization_id,
        Milestone.lifecycle_status.not_in(("COMPLETED", "SKIPPED", "CANCELLED")),
    ).order_by(Milestone.sequence, Milestone.id))
    if not milestone:
        return ()
    target = {"PENDING": "READY", "READY": "IN_PROGRESS", "IN_PROGRESS": "COMPLETED", "BLOCKED": "READY"}.get(milestone.lifecycle_status)
    if not target:
        return ()
    labels = _validate_readiness_links(context, shipment, milestone, target)
    evaluated = readiness.transition_readiness(shipment, milestone, target)
    blockers = evaluated["blocking_requirements"]
    if not blockers:
        return ()
    if any(b["code"] not in SUPPORTED_BLOCKERS or b["requirement_public_id"] not in labels for b in blockers):
        raise ValueError("Invalid readiness result")
    # One next-transition reason, with source-local stable explanation ordering.
    blockers = sorted(blockers, key=lambda b: (b["code"] == "DOC_REQUIREMENT_UNRESOLVED", b["requirement_public_id"]))
    definite = any(b["code"] != "DOC_REQUIREMENT_UNRESOLVED" for b in blockers)
    semantic = Semantic.READINESS_BLOCKED if definite else Semantic.READINESS_REVIEW
    title, _ = translate(semantic)
    explanation = " ".join(translate_blocker(b["code"], labels[b["requirement_public_id"]]) for b in blockers)
    from datetime import datetime
    evaluated_at = datetime.fromisoformat(evaluated["evaluated_at"])
    return (AttentionReason(semantic, AttentionLevel.FOLLOW_UP if definite else AttentionLevel.REVIEW,
        title, explanation, (time_context("evaluated", evaluated_at),),
        SourceIdentity("readiness", milestone.public_id, milestone.version, (context.shipment_id, target))),)
