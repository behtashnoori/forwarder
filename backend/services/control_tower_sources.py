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

from sqlalchemy import select, tuple_

from backend.extensions import db
from backend.models import CaseDocumentFile, CaseDocumentRequirement, DocumentDefinition, DocumentDefinitionStage
from backend.mdpm_models import ArtifactAssociation, DocumentAssessment, OperationalDocumentRequirement, TransitionOverride
from backend.oip_models import OipSituation
from backend.operational_models import (
    CanonicalLocation, DelayReason, ExceptionReason, Milestone, OperationalCheckpoint,
    OperationalDelay, OperationalException, OperationalShipment, OperationalSlaCommitment,
    OperationalWorkItem, RouteLeg, RoutePlan,
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
    "FOLLOW_UP": Semantic.ACTION_FOLLOW_UP,
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


def _active_execution(
    actor,
    context,
    at,
    *,
    source_rows=None,
    shipment=None,
    reason_labels=None,
    scope_prevalidated=False,
    skip_enrichment=False,
):
    shipment = shipment or _shipment(context)
    reasons = []
    for model, reason_model, semantic, field, kind in (
        (OperationalDelay, DelayReason, Semantic.ACTIVE_DELAY, "started_at", "delay_start"),
        (OperationalException, ExceptionReason, Semantic.ACTIVE_EXCEPTION, "occurred_at", "exception_occurrence"),
    ):
        # Each family is separately governed before reading its source rows.
        if not scope_prevalidated and refresh_summary_context(actor, context) != context:
            raise ControlTowerScopeDenied()
        rows = source_rows[model] if source_rows is not None else _all(select(model).where(
            model.organization_id == context.organization_id,
            model.operational_shipment_id == context.shipment_id,
            model.resolved_at.is_(None),
        ))
        for row in rows:
            label = (
                reason_labels.get((model, row.reason_id))
                if reason_labels is not None
                else _one(select(reason_model.fa_name).where(
                    reason_model.id == row.reason_id,
                    reason_model.organization_id == context.organization_id,
                ))
            )
            if label is None or row.milestone_id and not _milestone(context, row.milestone_id):
                continue
            enrichment = () if skip_enrichment else _enrich(
                actor, context, shipment,
                situation_type="ACTIVE_DELAY_OR_EXCEPTION", source_type=model.__name__,
                source_public_id=row.public_id, source_version=row.version,
                dimensions={"source_type": model.__name__, "source_public_id": row.public_id},
                occurred_at=getattr(row, field), at=at,
            )
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


def _bounded_work_links(contexts, rows):
    """Batch the exact route/milestone links used by the bounded work reader."""
    contexts = {context.shipment_id: context for context in contexts}
    milestone_ids = {row.milestone_id for row in rows if row.milestone_id}
    milestones = {
        row.id: row for row in _all(select(Milestone).where(Milestone.id.in_(milestone_ids)))
    } if milestone_ids else {}
    plan_ids = {
        value for value in (
            *(row.route_plan_id for row in rows),
            *(milestone.route_plan_id for milestone in milestones.values()),
        ) if value is not None
    }
    plans = {
        row.id: row for row in _all(select(RoutePlan).where(
            RoutePlan.id.in_(plan_ids),
            RoutePlan.is_active.is_(True),
            RoutePlan.status == "active",
        ))
    } if plan_ids else {}
    checkpoint_ids = {
        value for value in (
            *(row.checkpoint_id for row in rows),
            *(milestone.checkpoint_id for milestone in milestones.values()),
        ) if value is not None
    }
    checkpoints = {
        row.id: row for row in _all(select(OperationalCheckpoint).where(
            OperationalCheckpoint.id.in_(checkpoint_ids),
            OperationalCheckpoint.status != "cancelled",
        ))
    } if checkpoint_ids else {}
    leg_ids = {
        value for value in (
            *(milestone.route_leg_id for milestone in milestones.values()),
            *(checkpoint.route_leg_id for checkpoint in checkpoints.values()),
        ) if value is not None
    }
    legs = {
        row.id: row for row in _all(select(RouteLeg).where(
            RouteLeg.id.in_(leg_ids), RouteLeg.status != "cancelled",
        ))
    } if leg_ids else {}
    location_ids = {row.canonical_location_id for row in checkpoints.values()}
    locations = dict(db.session.execute(select(
        CanonicalLocation.id, CanonicalLocation.display_name
    ).where(CanonicalLocation.id.in_(location_ids))).all()) if location_ids else {}

    result = {}
    for row in rows:
        context = contexts.get(row.operational_shipment_id)
        if context is None:
            continue
        if row.work_type == "FOLLOW_UP":
            result[row.id] = (
                row.due_at,
                None,
                None,
                "OperationalWorkItem",
                row.public_id,
                row.version,
                "ACTION_FOLLOW_UP",
            )
            continue
        if row.work_type == "OVERDUE_MILESTONE":
            milestone = milestones.get(row.milestone_id)
            plan = plans.get(milestone.route_plan_id) if milestone else None
            if (
                milestone is None
                or milestone.operational_shipment_id != context.shipment_id
                or milestone.organization_id != context.organization_id
                or plan is None
                or plan.operational_shipment_id != context.shipment_id
                or milestone.verification_state == "verified"
                or milestone.lifecycle_status in {"COMPLETED", "SKIPPED", "CANCELLED"}
            ):
                continue
            checkpoint = checkpoints.get(milestone.checkpoint_id) if milestone.checkpoint_id else None
            if milestone.checkpoint_id and (
                checkpoint is None or checkpoint.route_plan_id != plan.id
            ):
                continue
            leg = legs.get(milestone.route_leg_id) if milestone.route_leg_id else None
            if milestone.route_leg_id and (leg is None or leg.route_plan_id != plan.id):
                continue
            snapshot = milestone.milestone_type_snapshot or {}
            label = snapshot.get("fa_name") if isinstance(snapshot, dict) else None
            due = row.due_at if utc(row.due_at) == utc(milestone.planned_at) else None
            result[row.id] = (
                due,
                label,
                None,
                "OperationalMilestoneDue",
                milestone.public_id,
                milestone.version,
                "NEXT_MILESTONE_OVERDUE",
            )
            continue
        plan = plans.get(row.route_plan_id)
        checkpoint = checkpoints.get(row.checkpoint_id)
        if (
            plan is None
            or plan.operational_shipment_id != context.shipment_id
            or checkpoint is None
            or checkpoint.route_plan_id != plan.id
        ):
            continue
        leg = legs.get(checkpoint.route_leg_id) if checkpoint.route_leg_id else None
        if checkpoint.route_leg_id and (leg is None or leg.route_plan_id != plan.id):
            continue
        due = None
        if (
            row.work_type != "ROUTE_DEPENDENCY_BLOCKED"
            and utc(row.due_at) == utc(_checkpoint_due(checkpoint))
        ):
            due = row.due_at
        result[row.id] = (
            due,
            locations.get(checkpoint.canonical_location_id),
            checkpoint.checkpoint_type,
            "OperationalWorkItem",
            f"owi-{row.id}",
            row.version,
            row.work_type,
        )
    return result


def evaluate_open_work(actor, context, *, at=None):
    return _evaluate("open_work", actor, context, _open_work, at)


def _open_work(
    actor,
    context,
    at,
    *,
    source_rows=None,
    shipment=None,
    skip_enrichment=False,
    work_links=None,
):
    shipment = shipment or _shipment(context)
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
        if work_links is not None:
            link = work_links.get(row.id)
            if link is None:
                continue
            due, label, checkpoint_type, source_type, source_public_id, source_version, situation_type = link
        elif row.work_type == "FOLLOW_UP":
            due = row.due_at
            source_type, source_public_id, source_version = (
                "OperationalWorkItem", row.public_id, row.version
            )
            situation_type = "ACTION_FOLLOW_UP"
        elif row.work_type == "OVERDUE_MILESTONE":
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
        if row.work_type == "FOLLOW_UP" and utc(row.due_at) < at:
            level = AttentionLevel.URGENT
        enrichment = ()
        # Invalid/stale authoritative due cannot support milestone enrichment.
        if not skip_enrichment and (
            row.work_type == "ROUTE_DEPENDENCY_BLOCKED" or due is not None
        ):
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


def _sla_reasons(rows):
    result = []
    for row in rows:
        if row.completed_at is not None or row.evaluation_status not in {"WARNING", "BREACHED"}:
            continue
        semantic = (
            Semantic.SLA_BREACH
            if row.evaluation_status == "BREACHED"
            else Semantic.SLA_WARNING
        )
        level = (
            AttentionLevel.URGENT
            if row.evaluation_status == "BREACHED"
            else AttentionLevel.FOLLOW_UP
        )
        result.append(_reason(
            semantic,
            SourceIdentity(
                "OperationalSlaCommitment",
                row.public_id,
                row.version,
                (row.process_type, row.rule_id, row.rule_version),
            ),
            level=level,
            times=(
                time_context("expected_due", row.due_at),
                time_context("sla_started", row.started_at),
                time_context("evaluated", row.evaluated_at),
            ),
        ))
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
        shipment_rows = {
            row.id: row
            for row in _all(select(OperationalShipment).where(
                OperationalShipment.organization_id == organization_id,
                OperationalShipment.id.in_(shipment_ids),
            ))
        }
        if set(shipment_rows) != set(shipment_ids):
            raise ControlTowerScopeDenied()
        public_ids = {row.public_id for row in shipment_rows.values()}
        oip_subjects = set(db.session.scalars(select(
            OipSituation.subject_public_id
        ).where(
            OipSituation.organization_id == organization_id,
            OipSituation.subject_type == "SHIPMENT",
            OipSituation.subject_public_id.in_(public_ids),
            OipSituation.status.in_(("OPEN", "ACKNOWLEDGED", "IN_PROGRESS")),
        ).distinct()).all()) if public_ids else set()
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
        sla_by_shipment = {shipment_id: [] for shipment_id in shipment_ids}
        try:
            for row in _all(select(OperationalSlaCommitment).where(
                OperationalSlaCommitment.organization_id == organization_id,
                OperationalSlaCommitment.operational_shipment_id.in_(shipment_ids),
                OperationalSlaCommitment.completed_at.is_(None),
                OperationalSlaCommitment.evaluation_status.in_(("WARNING", "BREACHED")),
            )):
                sla_by_shipment[row.operational_shipment_id].append(row)
        except Exception as exc:
            _logger.error(
                "control_tower_source_failure source=sla_batch error_type=%s",
                type(exc).__name__,
            )
            raise ControlTowerSourceFailure("sla_batch") from None
        delay_reason_ids = {row.reason_id for values in grouped[OperationalDelay].values() for row in values}
        exception_reason_ids = {row.reason_id for values in grouped[OperationalException].values() for row in values}
        reason_labels = {}
        if delay_reason_ids:
            reason_labels.update({
                (OperationalDelay, row.id): row.fa_name
                for row in _all(select(DelayReason).where(
                    DelayReason.organization_id == organization_id,
                    DelayReason.id.in_(delay_reason_ids),
                ))
            })
        if exception_reason_ids:
            reason_labels.update({
                (OperationalException, row.id): row.fa_name
                for row in _all(select(ExceptionReason).where(
                    ExceptionReason.organization_id == organization_id,
                    ExceptionReason.id.in_(exception_reason_ids),
                ))
            })
        work_links = _bounded_work_links(
            current,
            [row for values in grouped[OperationalWorkItem].values() for row in values],
        )
        readiness_batch = _bounded_readiness(current, shipment_rows)
        result = []
        for context in current:
            shipment = shipment_rows[context.shipment_id]
            skip_enrichment = shipment.public_id not in oip_subjects
            execution_rows = {model: grouped[model][context.shipment_id]
                              for model in (OperationalDelay, OperationalException)}
            work_rows = grouped[OperationalWorkItem][context.shipment_id]
            # Readers are fixed private implementations. Authority for the
            # complete set was refreshed above and is refreshed again below.
            execution = _active_execution(
                actor,
                context,
                at,
                source_rows=execution_rows,
                shipment=shipment,
                reason_labels=reason_labels,
                scope_prevalidated=True,
                skip_enrichment=skip_enrichment,
            )
            work = _open_work(
                actor,
                context,
                at,
                source_rows=work_rows,
                shipment=shipment,
                skip_enrichment=skip_enrichment,
                work_links=work_links,
            )
            # Keep the private reader boundary so failures/revocations retain
            # their existing fail-closed behavior, while its relational state
            # is loaded once for the selected page rather than per shipment.
            readiness_reasons = _readiness(
                actor,
                context,
                at,
                shipment=shipment,
                readiness_batch=readiness_batch,
            )
            sla_reasons = _sla_reasons(sla_by_shipment[context.shipment_id])
            result.append((context, execution + work + readiness_reasons + sla_reasons))
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


def _readiness_reason(context, milestone, target, labels, blockers, evaluated_at):
    if not blockers:
        return ()
    if any(b["code"] not in SUPPORTED_BLOCKERS or b["requirement_public_id"] not in labels for b in blockers):
        raise ValueError("Invalid readiness result")
    # One next-transition reason, with source-local stable explanation ordering.
    blockers = sorted(blockers, key=lambda b: (
        b["code"] == "DOC_REQUIREMENT_UNRESOLVED", b["requirement_public_id"]
    ))
    definite = any(b["code"] != "DOC_REQUIREMENT_UNRESOLVED" for b in blockers)
    semantic = Semantic.READINESS_BLOCKED if definite else Semantic.READINESS_REVIEW
    title, _ = translate(semantic)
    explanation = " ".join(
        translate_blocker(b["code"], labels[b["requirement_public_id"]]) for b in blockers
    )
    return (AttentionReason(
        semantic,
        AttentionLevel.FOLLOW_UP if definite else AttentionLevel.REVIEW,
        title,
        explanation,
        (time_context("evaluated", evaluated_at),),
        SourceIdentity(
            "readiness", milestone.public_id, milestone.version, (context.shipment_id, target)
        ),
    ),)


def _bounded_readiness(contexts, shipment_rows):
    """Evaluate C for the selected page with a fixed relational query set.

    This is the in-memory equivalent of the existing next-transition policy.
    It deliberately validates every active association and assessment before
    consuming the current one, preserving the prior fail-closed boundary.
    """
    eligible = tuple(
        context for context in contexts
        if shipment_rows[context.shipment_id].source_type != "direct"
    )
    if not eligible:
        return {}
    organization_id = eligible[0].organization_id
    shipment_ids = tuple(context.shipment_id for context in eligible)
    milestones = _all(select(Milestone).where(
        Milestone.organization_id == organization_id,
        Milestone.operational_shipment_id.in_(shipment_ids),
        Milestone.lifecycle_status.not_in(("COMPLETED", "SKIPPED", "CANCELLED")),
    ).order_by(Milestone.operational_shipment_id, Milestone.sequence, Milestone.id))
    milestone_by_shipment = {}
    for milestone in milestones:
        milestone_by_shipment.setdefault(milestone.operational_shipment_id, milestone)

    targets = {
        "PENDING": "READY",
        "READY": "IN_PROGRESS",
        "IN_PROGRESS": "COMPLETED",
        "BLOCKED": "READY",
    }
    readiness_keys = tuple(
        (shipment_id, milestone.milestone_type, targets[milestone.lifecycle_status])
        for shipment_id, milestone in milestone_by_shipment.items()
        if milestone.lifecycle_status in targets
    )
    requirements = _all(select(OperationalDocumentRequirement).where(
        OperationalDocumentRequirement.organization_id == organization_id,
        OperationalDocumentRequirement.is_active.is_(True),
        tuple_(
            OperationalDocumentRequirement.operational_shipment_id,
            OperationalDocumentRequirement.target_milestone_type,
            OperationalDocumentRequirement.target_status,
        ).in_(readiness_keys),
    ).with_for_update()) if readiness_keys else []
    requirements_by_shipment = {shipment_id: [] for shipment_id in shipment_ids}
    for requirement in requirements:
        requirements_by_shipment[requirement.operational_shipment_id].append(requirement)

    definition_ids = {requirement.document_definition_id for requirement in requirements}
    definitions = {
        row.id: row for row in _all(select(DocumentDefinition).where(
            DocumentDefinition.id.in_(definition_ids)
        ))
    } if definition_ids else {}
    financial_definition_ids = set(db.session.scalars(select(
        DocumentDefinitionStage.document_definition_id
    ).where(
        DocumentDefinitionStage.document_definition_id.in_(definition_ids),
        DocumentDefinitionStage.stage_code == "PAYMENT_FINANCE",
    )).all()) if definition_ids else set()

    requirement_ids = tuple(requirement.id for requirement in requirements)
    associations = _all(select(ArtifactAssociation).where(
        ArtifactAssociation.requirement_id.in_(requirement_ids),
        ArtifactAssociation.state == "ACTIVE",
    ).order_by(
        ArtifactAssociation.requirement_id,
        ArtifactAssociation.associated_at.desc(),
        ArtifactAssociation.id.desc(),
    )) if requirement_ids else []
    associations_by_requirement = {requirement_id: [] for requirement_id in requirement_ids}
    for association in associations:
        associations_by_requirement[association.requirement_id].append(association)

    document_file_ids = {association.document_file_id for association in associations}
    artifacts = {
        row.id: row for row in _all(select(CaseDocumentFile).where(
            CaseDocumentFile.id.in_(document_file_ids)
        ))
    } if document_file_ids else {}
    case_requirement_ids = {
        artifact.case_requirement_id for artifact in artifacts.values()
        if artifact.case_requirement_id is not None
    }
    case_requirements = {
        row.id: row for row in _all(select(CaseDocumentRequirement).where(
            CaseDocumentRequirement.id.in_(case_requirement_ids)
        ))
    } if case_requirement_ids else {}

    association_ids = tuple(association.id for association in associations)
    assessments = _all(select(DocumentAssessment).where(
        DocumentAssessment.association_id.in_(association_ids)
    ).order_by(
        DocumentAssessment.association_id,
        DocumentAssessment.created_at.desc(),
        DocumentAssessment.id.desc(),
    )) if association_ids else []
    assessments_by_association = {association_id: [] for association_id in association_ids}
    for assessment in assessments:
        assessments_by_association[assessment.association_id].append(assessment)

    overrides = _all(select(TransitionOverride).where(
        TransitionOverride.requirement_id.in_(requirement_ids)
    ).with_for_update()) if requirement_ids else []
    overrides_by_requirement = {requirement_id: [] for requirement_id in requirement_ids}
    for override in overrides:
        overrides_by_requirement[override.requirement_id].append(override)

    evaluated_at = utcnow()
    result = {}
    context_by_shipment = {context.shipment_id: context for context in eligible}
    for shipment_id, context in context_by_shipment.items():
        shipment = shipment_rows[shipment_id]
        milestone = milestone_by_shipment.get(shipment_id)
        if milestone is None or milestone.lifecycle_status not in targets:
            result[shipment_id] = ()
            continue
        target = targets[milestone.lifecycle_status]
        labels = {}
        blockers = []
        for requirement in requirements_by_shipment[shipment_id]:
            definition = definitions.get(requirement.document_definition_id)
            if definition is None:
                raise ValueError("Invalid requirement definition")
            labels[requirement.public_id] = (
                None if definition.family_code == "FINANCE"
                or definition.id in financial_definition_ids
                else safe_display_label(definition.title)
            )
            active_associations = associations_by_requirement[requirement.id]
            for association in active_associations:
                if association.organization_id != organization_id:
                    raise ValueError("Invalid artifact tenant")
                artifact = artifacts.get(association.document_file_id)
                if artifact is None or (
                    artifact.operational_organization_id != organization_id
                    or artifact.shipment_request_id != shipment.shipment_request_id
                ):
                    raise ValueError("Invalid artifact linkage")
                case_requirement = case_requirements.get(artifact.case_requirement_id)
                if case_requirement is None or (
                    case_requirement.operational_organization_id != organization_id
                    or case_requirement.shipment_request_id != shipment.shipment_request_id
                    or case_requirement.source_definition_id != requirement.document_definition_id
                ):
                    raise ValueError("Invalid artifact definition")
                if any(
                    assessment.organization_id != organization_id
                    for assessment in assessments_by_association[association.id]
                ):
                    raise ValueError("Invalid assessment tenant")

            association = active_associations[0] if active_associations else None
            assessment = (
                assessments_by_association[association.id][0]
                if association and assessments_by_association[association.id]
                else None
            )
            code = None
            if (
                requirement.requirement_level == "CONDITIONAL"
                and requirement.applicability_state == "UNRESOLVED"
            ):
                code = "DOC_REQUIREMENT_UNRESOLVED"
            elif requirement.applicability_state == "NOT_APPLICABLE":
                continue
            elif association is None:
                code = "DOC_ARTIFACT_MISSING"
            else:
                artifact = artifacts[association.document_file_id]
                if artifact.status != "active" or artifact.version_number != association.artifact_version:
                    code = "DOC_ARTIFACT_SUPERSEDED"
                elif assessment and assessment.decision == "REJECTED":
                    code = "DOC_ARTIFACT_REJECTED"
                elif requirement.required_assessment_level == "VERIFIED" and (
                    not assessment or assessment.decision != "VERIFIED"
                ):
                    code = "DOC_VERIFICATION_REQUIRED"
                elif requirement.required_assessment_level == "APPROVED" and (
                    not assessment or assessment.decision not in {"APPROVED", "VERIFIED"}
                ):
                    code = "DOC_APPROVAL_REQUIRED"
            if code:
                overridden = any(
                    override.organization_id == organization_id
                    and override.operational_shipment_id == shipment_id
                    and override.milestone_id == milestone.id
                    and override.target_status == target
                    and override.state == "ACTIVE"
                    and (override.expires_at is None or utc(override.expires_at) > utc(evaluated_at))
                    for override in overrides_by_requirement[requirement.id]
                )
                if not overridden and requirement.requirement_level != "OPTIONAL":
                    blockers.append({
                        "code": code,
                        "requirement_public_id": requirement.public_id,
                    })
        result[shipment_id] = _readiness_reason(
            context, milestone, target, labels, blockers, utc(evaluated_at)
        )
    return result


def _readiness(actor, context, at, *, shipment=None, readiness_batch=None):
    if readiness_batch is not None:
        return readiness_batch.get(context.shipment_id, ())
    shipment = shipment or _shipment(context)
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
    from datetime import datetime
    evaluated_at = datetime.fromisoformat(evaluated["evaluated_at"])
    return _readiness_reason(
        context, milestone, target, labels, evaluated["blocking_requirements"], evaluated_at
    )
