"""Authorized relational attention index and bounded Control Tower windows.

This module selects identities and population-global metadata only.  Existing
D1 adapters remain the authority for the detailed page projection and verify
the selected rank before anything is serialized.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    and_,
    case,
    cast,
    exists,
    func,
    literal,
    or_,
    select,
    union_all,
)

from backend.extensions import db
from backend.mdpm_models import (
    ArtifactAssociation,
    DocumentAssessment,
    OperationalDocumentRequirement,
    TransitionOverride,
)
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    ExpertUser,
    ShipmentRequest,
)
from backend.oip_models import (
    OipAttentionProjection,
    OipFactReference,
    OipSignal,
    OipSituation,
    OipSituationEvidence,
)
from backend.operational_models import (
    DelayReason,
    ExceptionReason,
    Milestone,
    OperationalCheckpoint,
    OperationalDelay,
    OperationalException,
    OperationalMembership,
    OperationalOrganization,
    OperationalSlaCommitment,
    OperationalShipment,
    OperationalWorkItem,
    RouteLeg,
    RoutePlan,
)
from backend.services.control_tower_scope import (
    ControlTowerResponsibilityInvariant,
    governed_summary_population,
)
from backend.services.oip_service import POLICIES, PROJECTION_VERSION


@dataclass(frozen=True)
class AttentionWindowRow:
    shipment_id: int
    shipment_public_id: str
    attention: str
    order_key: tuple


@dataclass(frozen=True)
class AttentionWindow:
    rows: tuple[AttentionWindowRow, ...]
    total: int
    attention_counts: dict[str, int]
    has_more: bool


def _authorized_population(actor):
    authority = governed_summary_population(actor)
    authorized = authority.query.with_only_columns(
        OperationalShipment.id.label("shipment_id"),
        OperationalShipment.public_id.label("shipment_public_id"),
        OperationalShipment.organization_id.label("organization_id"),
        OperationalShipment.source_type.label("source_type"),
        OperationalShipment.shipment_request_id.label("shipment_request_id"),
        OperationalShipment.primary_responsible_expert_id.label("owner_id"),
    ).cte("control_tower_authorized")

    lineage = select(
        authorized,
        ShipmentRequest.public_id.label("request_public_id"),
        ShipmentRequest.operational_organization_id.label("request_organization_id"),
        ShipmentRequest.ownership_scope.label("request_ownership_scope"),
        authorized.c.owner_id,
    ).select_from(
        authorized.outerjoin(
            ShipmentRequest,
            ShipmentRequest.id == authorized.c.shipment_request_id,
        )
    ).cte("control_tower_lineage")

    active_owner_memberships = select(func.count(OperationalMembership.user_id)).select_from(
        OperationalMembership.__table__.join(
            OperationalOrganization,
            OperationalOrganization.id == OperationalMembership.organization_id,
        )
    ).where(
        OperationalMembership.user_id == lineage.c.owner_id,
        OperationalMembership.is_active.is_(True),
        OperationalOrganization.is_active.is_(True),
    ).scalar_subquery()
    owner_in_tenant = exists(select(literal(1)).select_from(
        OperationalMembership.__table__.join(
            OperationalOrganization,
            OperationalOrganization.id == OperationalMembership.organization_id,
        )
    ).where(
        OperationalMembership.user_id == lineage.c.owner_id,
        OperationalMembership.organization_id == lineage.c.organization_id,
        OperationalMembership.is_active.is_(True),
        OperationalOrganization.is_active.is_(True),
    ))
    valid_lineage = or_(
        and_(
            lineage.c.source_type == "accepted_quote",
            lineage.c.shipment_request_id.is_not(None),
            lineage.c.request_organization_id == lineage.c.organization_id,
            lineage.c.request_ownership_scope == "TENANT",
        ),
        and_(
            lineage.c.source_type == "direct",
            lineage.c.shipment_request_id.is_(None),
        ),
    )
    certified = select(
        lineage.c.shipment_id,
        lineage.c.shipment_public_id,
        lineage.c.organization_id,
        lineage.c.source_type,
        lineage.c.shipment_request_id,
        lineage.c.request_public_id,
        lineage.c.owner_id,
        ExpertUser.full_name.label("owner_name"),
    ).select_from(
        lineage.join(ExpertUser, ExpertUser.id == lineage.c.owner_id)
    ).where(
        valid_lineage,
        ExpertUser.is_active.is_(True),
        func.upper(func.coalesce(ExpertUser.authority, "")) == "EXPERT",
        active_owner_memberships == 1,
        owner_in_tenant,
    ).cte("control_tower_certified")

    has_request = exists(select(literal(1)).select_from(certified).where(
        certified.c.source_type == "accepted_quote"
    ))
    has_oip = exists(select(literal(1)).select_from(
        certified.join(
            OipSituation,
            and_(
                OipSituation.organization_id == certified.c.organization_id,
                OipSituation.subject_type == "SHIPMENT",
                OipSituation.subject_public_id == certified.c.shipment_public_id,
            ),
        )
    ).where(
        OipSituation.status.in_(("OPEN", "ACKNOWLEDGED", "IN_PROGRESS")),
        OipSituation.resolved_at.is_(None),
    ))
    counts = db.session.execute(select(
        select(func.count()).select_from(authorized).scalar_subquery(),
        select(func.count()).select_from(certified).scalar_subquery(),
        has_request,
        has_oip,
    )).one()
    if counts[0] != counts[1]:
        raise ControlTowerResponsibilityInvariant()
    return certified, bool(counts[2]), bool(counts[3])


def _search_population(population, search: str | None):
    if not search:
        return select(population).cte("control_tower_searched")
    escaped = search.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    return select(population).where(or_(
        func.lower(population.c.shipment_public_id).like(pattern, escape="\\"),
        func.lower(func.coalesce(population.c.request_public_id, "")).like(pattern, escape="\\"),
        func.lower(population.c.owner_name).like(pattern, escape="\\"),
    )).cte("control_tower_searched")


def _oip_promotions(at):
    """One bounded relational view of rank-affecting verified OIP links."""
    linked = (
        OipSituation.__table__
        .join(
            OipSituationEvidence,
            OipSituationEvidence.situation_id == OipSituation.id,
        )
        .join(
            OipFactReference,
            OipFactReference.id == OipSituationEvidence.fact_reference_id,
        )
        .join(OipSignal, OipSignal.id == OipSituationEvidence.signal_id)
        .join(
            OipAttentionProjection,
            OipAttentionProjection.situation_id == OipSituation.id,
        )
    )
    expected_policy = case(*(
        (OipSituation.situation_type == kind, value["id"])
        for kind, value in POLICIES.items()
    ))
    expected_version = case(*(
        (OipSituation.situation_type == kind, value["version"])
        for kind, value in POLICIES.items()
        if kind != "NEXT_MILESTONE_OVERDUE"
    ))
    watermark = (
        OipFactReference.source_type
        + literal(":")
        + OipFactReference.source_public_id
        + literal(":")
        + OipFactReference.source_version
    )
    return select(
        OipSituation.organization_id,
        OipSituation.subject_public_id,
        OipSituation.situation_type,
        OipSituation.urgency,
        OipSituation.severity,
        OipSituation.due_at,
        OipFactReference.source_type,
        OipFactReference.source_public_id,
        OipFactReference.source_version,
        OipFactReference.occurred_at,
        OipAttentionProjection.operational_work_item_id,
    ).select_from(linked).where(
        OipSituation.subject_type == "SHIPMENT",
        OipSituation.status.in_(("OPEN", "ACKNOWLEDGED", "IN_PROGRESS")),
        OipSituation.freshness_status == "FRESH",
        OipSituation.resolved_at.is_(None),
        OipSituation.projection_version == PROJECTION_VERSION,
        OipSituation.identity_key == OipSignal.dedup_key,
        OipSituation.policy_id == expected_policy,
        OipSituation.source_watermark == watermark,
        OipSituationEvidence.is_current.is_(True),
        OipFactReference.organization_id == OipSituation.organization_id,
        OipFactReference.subject_type == "SHIPMENT",
        OipFactReference.subject_public_id == OipSituation.subject_public_id,
        OipFactReference.source_domain == "OPERATIONAL_EXECUTION",
        OipFactReference.validity == "CURRENT",
        OipFactReference.superseded_by_public_id.is_(None),
        OipSignal.organization_id == OipSituation.organization_id,
        OipSignal.subject_type == "SHIPMENT",
        OipSignal.subject_public_id == OipSituation.subject_public_id,
        OipSignal.signal_type == OipSituation.situation_type,
        OipSignal.policy_id == expected_policy,
        OipSignal.active.is_(True),
        OipSignal.source_watermark == watermark,
        OipSituation.policy_version == OipSignal.policy_version,
        or_(
            OipSituation.situation_type == "NEXT_MILESTONE_OVERDUE",
            OipSituation.policy_version == expected_version,
        ),
        OipAttentionProjection.source_watermark == watermark,
        OipAttentionProjection.projection_version == PROJECTION_VERSION,
        OipSignal.observed_at <= OipSituation.calculated_at,
        OipSituation.calculated_at <= OipAttentionProjection.calculated_at,
        OipAttentionProjection.calculated_at <= at,
    ).cte("control_tower_oip_promotions")


def _oip_promotion(
    promotions,
    *,
    organization_id,
    shipment_public_id,
    situation_type,
    source_type,
    source_public_id,
    source_version,
    occurred_at,
    due_at=None,
    authoritative_due=None,
    work_item_id=None,
    at,
):
    """Correlate one reason with the compact verified-enrichment view.

    Detailed D1 evaluation checks the complete identity/dimension contract for
    the selected page.  Any disagreement fails the response closed.
    """
    if promotions is None:
        return literal(False)
    promotion = or_(
        promotions.c.urgency == "CRITICAL",
        promotions.c.severity == "CRITICAL",
        and_(
            situation_type in {"ACTIVE_DELAY_OR_EXCEPTION", "NEXT_MILESTONE_OVERDUE"},
            promotions.c.urgency == "HIGH",
            promotions.c.severity == "HIGH",
        ),
    )
    if authoritative_due is not None:
        promotion = or_(
            promotion,
            and_(
                authoritative_due,
                due_at.is_not(None),
                due_at < at,
                promotions.c.urgency == "HIGH",
            ),
        )
    conditions = [
        promotions.c.organization_id == organization_id,
        promotions.c.subject_public_id == shipment_public_id,
        promotions.c.situation_type == situation_type,
        promotions.c.source_type == source_type,
        promotions.c.source_public_id == cast(source_public_id, String),
        promotions.c.source_version == cast(source_version, String),
        promotions.c.occurred_at == occurred_at,
        promotion,
    ]
    if due_at is None:
        conditions.append(promotions.c.due_at.is_(None))
    else:
        conditions.append(promotions.c.due_at == due_at)
    if work_item_id is not None:
        conditions.append(or_(
            promotions.c.operational_work_item_id.is_(None),
            promotions.c.operational_work_item_id == work_item_id,
        ))
    return exists(select(literal(1)).select_from(promotions).where(*conditions))


def _reason_select(shipment_id, attention_rank, due_at, onset_at):
    null_time = cast(literal(None), DateTime(timezone=True))
    return select(
        shipment_id.label("shipment_id"),
        cast(attention_rank, Integer).label("attention_rank"),
        (due_at if due_at is not None else null_time).label("due_at"),
        (onset_at if onset_at is not None else null_time).label("onset_at"),
    )


def _execution_reasons(population, promotions, at):
    delay_milestone = Milestone.__table__.alias("control_tower_delay_milestone")
    delay_join = (
        population.join(
            OperationalDelay,
            OperationalDelay.operational_shipment_id == population.c.shipment_id,
        )
        .join(
            DelayReason,
            and_(
                DelayReason.id == OperationalDelay.reason_id,
                DelayReason.organization_id == population.c.organization_id,
            ),
        )
        .outerjoin(
            delay_milestone,
            and_(
                delay_milestone.c.id == OperationalDelay.milestone_id,
                delay_milestone.c.operational_shipment_id == population.c.shipment_id,
                delay_milestone.c.organization_id == population.c.organization_id,
            ),
        )
    )
    delay_promoted = _oip_promotion(
        promotions,
        organization_id=population.c.organization_id,
        shipment_public_id=population.c.shipment_public_id,
        situation_type="ACTIVE_DELAY_OR_EXCEPTION",
        source_type="OperationalDelay",
        source_public_id=OperationalDelay.public_id,
        source_version=OperationalDelay.version,
        occurred_at=OperationalDelay.started_at,
        at=at,
    )
    delays = _reason_select(
        population.c.shipment_id,
        case((delay_promoted, 0), else_=1),
        None,
        OperationalDelay.started_at,
    ).select_from(delay_join).where(
        OperationalDelay.organization_id == population.c.organization_id,
        OperationalDelay.resolved_at.is_(None),
        or_(
            OperationalDelay.milestone_id.is_(None),
            delay_milestone.c.id.is_not(None),
        ),
    )

    exception_milestone = Milestone.__table__.alias("control_tower_exception_milestone")
    exception_join = (
        population.join(
            OperationalException,
            OperationalException.operational_shipment_id == population.c.shipment_id,
        )
        .join(
            ExceptionReason,
            and_(
                ExceptionReason.id == OperationalException.reason_id,
                ExceptionReason.organization_id == population.c.organization_id,
            ),
        )
        .outerjoin(
            exception_milestone,
            and_(
                exception_milestone.c.id == OperationalException.milestone_id,
                exception_milestone.c.operational_shipment_id == population.c.shipment_id,
                exception_milestone.c.organization_id == population.c.organization_id,
            ),
        )
    )
    exception_promoted = _oip_promotion(
        promotions,
        organization_id=population.c.organization_id,
        shipment_public_id=population.c.shipment_public_id,
        situation_type="ACTIVE_DELAY_OR_EXCEPTION",
        source_type="OperationalException",
        source_public_id=OperationalException.public_id,
        source_version=OperationalException.version,
        occurred_at=OperationalException.occurred_at,
        at=at,
    )
    exceptions = _reason_select(
        population.c.shipment_id,
        case((exception_promoted, 0), else_=1),
        None,
        OperationalException.occurred_at,
    ).select_from(exception_join).where(
        OperationalException.organization_id == population.c.organization_id,
        OperationalException.resolved_at.is_(None),
        or_(
            OperationalException.milestone_id.is_(None),
            exception_milestone.c.id.is_not(None),
        ),
    )
    return delays, exceptions


def _work_reasons(population, promotions, at):
    milestone_plan = RoutePlan.__table__.alias("control_tower_milestone_plan")
    milestone_checkpoint = OperationalCheckpoint.__table__.alias("control_tower_milestone_checkpoint")
    milestone_leg = RouteLeg.__table__.alias("control_tower_milestone_leg")
    milestone_join = (
        population.join(
            OperationalWorkItem,
            OperationalWorkItem.operational_shipment_id == population.c.shipment_id,
        )
        .join(
            Milestone,
            and_(
                Milestone.id == OperationalWorkItem.milestone_id,
                Milestone.operational_shipment_id == population.c.shipment_id,
                Milestone.organization_id == population.c.organization_id,
            ),
        )
        .join(
            milestone_plan,
            and_(
                milestone_plan.c.id == Milestone.route_plan_id,
                milestone_plan.c.operational_shipment_id == population.c.shipment_id,
                milestone_plan.c.is_active.is_(True),
                milestone_plan.c.status == "active",
            ),
        )
        .outerjoin(
            milestone_checkpoint,
            and_(
                milestone_checkpoint.c.id == Milestone.checkpoint_id,
                milestone_checkpoint.c.route_plan_id == milestone_plan.c.id,
                milestone_checkpoint.c.status != "cancelled",
            ),
        )
        .outerjoin(
            milestone_leg,
            and_(
                milestone_leg.c.id == Milestone.route_leg_id,
                milestone_leg.c.route_plan_id == milestone_plan.c.id,
                milestone_leg.c.status != "cancelled",
            ),
        )
    )
    authoritative_due = OperationalWorkItem.due_at == Milestone.planned_at
    milestone_due = case((authoritative_due, OperationalWorkItem.due_at))
    milestone_promoted = _oip_promotion(
        promotions,
        organization_id=population.c.organization_id,
        shipment_public_id=population.c.shipment_public_id,
        situation_type="NEXT_MILESTONE_OVERDUE",
        source_type="OperationalMilestoneDue",
        source_public_id=Milestone.public_id,
        source_version=Milestone.version,
        occurred_at=OperationalWorkItem.detected_at,
        due_at=OperationalWorkItem.due_at,
        authoritative_due=authoritative_due,
        work_item_id=OperationalWorkItem.id,
        at=at,
    )
    milestone_reasons = _reason_select(
        population.c.shipment_id,
        case((milestone_promoted, 0), else_=1),
        milestone_due,
        OperationalWorkItem.detected_at,
    ).select_from(milestone_join).where(
        OperationalWorkItem.organization_id == population.c.organization_id,
        OperationalWorkItem.status == "open",
        OperationalWorkItem.work_type == "OVERDUE_MILESTONE",
        Milestone.verification_state != "verified",
        Milestone.lifecycle_status.not_in(("COMPLETED", "SKIPPED", "CANCELLED")),
        or_(Milestone.checkpoint_id.is_(None), milestone_checkpoint.c.id.is_not(None)),
        or_(Milestone.route_leg_id.is_(None), milestone_leg.c.id.is_not(None)),
    )

    checkpoint_plan = RoutePlan.__table__.alias("control_tower_checkpoint_plan")
    checkpoint = OperationalCheckpoint.__table__.alias("control_tower_checkpoint")
    checkpoint_leg = RouteLeg.__table__.alias("control_tower_checkpoint_leg")
    checkpoint_join = (
        population.join(
            OperationalWorkItem,
            OperationalWorkItem.operational_shipment_id == population.c.shipment_id,
        )
        .join(
            checkpoint_plan,
            and_(
                checkpoint_plan.c.id == OperationalWorkItem.route_plan_id,
                checkpoint_plan.c.operational_shipment_id == population.c.shipment_id,
                checkpoint_plan.c.is_active.is_(True),
                checkpoint_plan.c.status == "active",
            ),
        )
        .join(
            checkpoint,
            and_(
                checkpoint.c.id == OperationalWorkItem.checkpoint_id,
                checkpoint.c.route_plan_id == checkpoint_plan.c.id,
                checkpoint.c.status != "cancelled",
            ),
        )
        .outerjoin(
            checkpoint_leg,
            and_(
                checkpoint_leg.c.id == checkpoint.c.route_leg_id,
                checkpoint_leg.c.route_plan_id == checkpoint_plan.c.id,
                checkpoint_leg.c.status != "cancelled",
            ),
        )
    )
    checkpoint_due_value = func.coalesce(
        checkpoint.c.projected_arrival_at,
        checkpoint.c.planned_arrival_at,
        checkpoint.c.projected_departure_at,
        checkpoint.c.planned_departure_at,
    )
    authoritative_checkpoint_due = and_(
        OperationalWorkItem.work_type != "ROUTE_DEPENDENCY_BLOCKED",
        OperationalWorkItem.due_at == checkpoint_due_value,
    )
    checkpoint_due = case((authoritative_checkpoint_due, OperationalWorkItem.due_at))
    source_public_id = literal("owi-") + cast(OperationalWorkItem.id, String)
    situation_type = case(
        (OperationalWorkItem.work_type == "CHECKPOINT_OVERDUE", "CHECKPOINT_OVERDUE"),
        (OperationalWorkItem.work_type == "ROUTE_DEPENDENCY_BLOCKED", "ROUTE_DEPENDENCY_BLOCKED"),
        else_="REPLAN_REQUIRED",
    )
    promoted_conditions = []
    for work_type in ("CHECKPOINT_OVERDUE", "ROUTE_DEPENDENCY_BLOCKED", "REPLAN_REQUIRED"):
        promoted_conditions.append(and_(
            OperationalWorkItem.work_type == work_type,
            _oip_promotion(
                promotions,
                organization_id=population.c.organization_id,
                shipment_public_id=population.c.shipment_public_id,
                situation_type=work_type,
                source_type="OperationalWorkItem",
                source_public_id=source_public_id,
                source_version=OperationalWorkItem.version,
                occurred_at=OperationalWorkItem.detected_at,
                due_at=OperationalWorkItem.due_at,
                authoritative_due=authoritative_checkpoint_due,
                work_item_id=OperationalWorkItem.id,
                at=at,
            ),
        ))
    base_urgent = and_(
        OperationalWorkItem.work_type.in_(("ROUTE_DEPENDENCY_BLOCKED", "REPLAN_REQUIRED")),
        OperationalWorkItem.severity == "critical",
    )
    checkpoint_reasons = _reason_select(
        population.c.shipment_id,
        case((or_(base_urgent, *promoted_conditions), 0), else_=1),
        checkpoint_due,
        OperationalWorkItem.detected_at,
    ).select_from(checkpoint_join).where(
        OperationalWorkItem.organization_id == population.c.organization_id,
        OperationalWorkItem.status == "open",
        OperationalWorkItem.work_type.in_((
            "CHECKPOINT_OVERDUE",
            "ROUTE_DEPENDENCY_BLOCKED",
            "REPLAN_REQUIRED",
        )),
        or_(checkpoint.c.route_leg_id.is_(None), checkpoint_leg.c.id.is_not(None)),
    )
    action_promoted = _oip_promotion(
        promotions,
        organization_id=population.c.organization_id,
        shipment_public_id=population.c.shipment_public_id,
        situation_type="ACTION_FOLLOW_UP",
        source_type="OperationalWorkItem",
        source_public_id=OperationalWorkItem.public_id,
        source_version=OperationalWorkItem.version,
        occurred_at=OperationalWorkItem.detected_at,
        due_at=OperationalWorkItem.due_at,
        authoritative_due=literal(True),
        work_item_id=OperationalWorkItem.id,
        at=at,
    )
    action_reasons = _reason_select(
        population.c.shipment_id,
        case(
            (or_(OperationalWorkItem.due_at < at, action_promoted), 0),
            else_=1,
        ),
        OperationalWorkItem.due_at,
        OperationalWorkItem.detected_at,
    ).select_from(
        population.join(
            OperationalWorkItem,
            OperationalWorkItem.operational_shipment_id == population.c.shipment_id,
        )
    ).where(
        OperationalWorkItem.organization_id == population.c.organization_id,
        OperationalWorkItem.status == "open",
        OperationalWorkItem.work_type == "FOLLOW_UP",
    )
    return milestone_reasons, checkpoint_reasons, action_reasons


def _sla_reasons(population):
    return _reason_select(
        population.c.shipment_id,
        case(
            (OperationalSlaCommitment.evaluation_status == "BREACHED", 0),
            else_=1,
        ),
        OperationalSlaCommitment.due_at,
        OperationalSlaCommitment.started_at,
    ).select_from(
        population.join(
            OperationalSlaCommitment,
            OperationalSlaCommitment.operational_shipment_id == population.c.shipment_id,
        )
    ).where(
        OperationalSlaCommitment.organization_id == population.c.organization_id,
        OperationalSlaCommitment.completed_at.is_(None),
        OperationalSlaCommitment.evaluation_status.in_(("WARNING", "BREACHED")),
    )


def _readiness_reasons(population, at):
    target_status = case(
        (Milestone.lifecycle_status == "PENDING", "READY"),
        (Milestone.lifecycle_status == "READY", "IN_PROGRESS"),
        (Milestone.lifecycle_status == "IN_PROGRESS", "COMPLETED"),
        (Milestone.lifecycle_status == "BLOCKED", "READY"),
    )
    milestones = select(
        Milestone.id.label("milestone_id"),
        Milestone.operational_shipment_id.label("shipment_id"),
        Milestone.organization_id.label("organization_id"),
        Milestone.milestone_type.label("milestone_type"),
        target_status.label("target_status"),
        func.row_number().over(
            partition_by=Milestone.operational_shipment_id,
            order_by=(Milestone.sequence.asc().nulls_last(), Milestone.id.asc()),
        ).label("position"),
    ).select_from(
        population.join(
            Milestone,
            Milestone.operational_shipment_id == population.c.shipment_id,
        )
    ).where(
        population.c.source_type != "direct",
        Milestone.organization_id == population.c.organization_id,
        Milestone.lifecycle_status.not_in(("COMPLETED", "SKIPPED", "CANCELLED")),
        target_status.is_not(None),
    ).cte("control_tower_milestones")
    next_milestone = select(milestones).where(
        milestones.c.position == 1
    ).cte("control_tower_next_milestone")

    association_rows = select(
        ArtifactAssociation.id.label("association_id"),
        ArtifactAssociation.requirement_id,
        ArtifactAssociation.organization_id,
        ArtifactAssociation.document_file_id,
        ArtifactAssociation.artifact_version,
        func.row_number().over(
            partition_by=ArtifactAssociation.requirement_id,
            order_by=(ArtifactAssociation.associated_at.desc(), ArtifactAssociation.id.desc()),
        ).label("position"),
    ).where(ArtifactAssociation.state == "ACTIVE").cte("control_tower_associations")
    current_association = select(association_rows).where(
        association_rows.c.position == 1
    ).cte("control_tower_current_association")

    assessment_rows = select(
        DocumentAssessment.association_id,
        DocumentAssessment.organization_id,
        DocumentAssessment.decision,
        func.row_number().over(
            partition_by=DocumentAssessment.association_id,
            order_by=(DocumentAssessment.created_at.desc(), DocumentAssessment.id.desc()),
        ).label("position"),
    ).cte("control_tower_assessments")
    current_assessment = select(assessment_rows).where(
        assessment_rows.c.position == 1
    ).cte("control_tower_current_assessment")

    joined = (
        population.join(
            next_milestone,
            next_milestone.c.shipment_id == population.c.shipment_id,
        )
        .join(
            OperationalDocumentRequirement,
            and_(
                OperationalDocumentRequirement.operational_shipment_id == population.c.shipment_id,
                OperationalDocumentRequirement.organization_id == population.c.organization_id,
                OperationalDocumentRequirement.target_milestone_type == next_milestone.c.milestone_type,
                OperationalDocumentRequirement.target_status == next_milestone.c.target_status,
                OperationalDocumentRequirement.is_active.is_(True),
            ),
        )
        .outerjoin(
            current_association,
            current_association.c.requirement_id == OperationalDocumentRequirement.id,
        )
        .outerjoin(
            CaseDocumentFile,
            CaseDocumentFile.id == current_association.c.document_file_id,
        )
        .outerjoin(
            CaseDocumentRequirement,
            CaseDocumentRequirement.id == CaseDocumentFile.case_requirement_id,
        )
        .outerjoin(
            current_assessment,
            current_assessment.c.association_id == current_association.c.association_id,
        )
    )
    overridden = exists(select(literal(1)).where(
        TransitionOverride.organization_id == population.c.organization_id,
        TransitionOverride.operational_shipment_id == population.c.shipment_id,
        TransitionOverride.requirement_id == OperationalDocumentRequirement.id,
        TransitionOverride.milestone_id == next_milestone.c.milestone_id,
        TransitionOverride.target_status == next_milestone.c.target_status,
        TransitionOverride.state == "ACTIVE",
        or_(TransitionOverride.expires_at.is_(None), TransitionOverride.expires_at > at),
    ))
    unresolved = and_(
        OperationalDocumentRequirement.requirement_level == "CONDITIONAL",
        OperationalDocumentRequirement.applicability_state == "UNRESOLVED",
    )
    valid_artifact = and_(
        current_association.c.association_id.is_not(None),
        current_association.c.organization_id == population.c.organization_id,
        CaseDocumentFile.id.is_not(None),
        CaseDocumentFile.operational_organization_id == population.c.organization_id,
        CaseDocumentFile.shipment_request_id == population.c.shipment_request_id,
        CaseDocumentFile.status == "active",
        CaseDocumentFile.version_number == current_association.c.artifact_version,
        CaseDocumentRequirement.id.is_not(None),
        CaseDocumentRequirement.operational_organization_id == population.c.organization_id,
        CaseDocumentRequirement.shipment_request_id == population.c.shipment_request_id,
        CaseDocumentRequirement.source_definition_id == OperationalDocumentRequirement.document_definition_id,
    )
    valid_assessment_tenant = or_(
        current_assessment.c.association_id.is_(None),
        current_assessment.c.organization_id == population.c.organization_id,
    )
    definite = and_(
        ~unresolved,
        OperationalDocumentRequirement.applicability_state != "NOT_APPLICABLE",
        or_(
            ~valid_artifact,
            current_assessment.c.decision == "REJECTED",
            and_(
                OperationalDocumentRequirement.required_assessment_level == "VERIFIED",
                current_assessment.c.decision != "VERIFIED",
            ),
            and_(
                OperationalDocumentRequirement.required_assessment_level == "APPROVED",
                or_(
                    current_assessment.c.decision.is_(None),
                    current_assessment.c.decision.not_in(("APPROVED", "VERIFIED")),
                ),
            ),
        ),
    )
    return _reason_select(
        population.c.shipment_id,
        case((definite, 1), else_=2),
        None,
        None,
    ).select_from(joined).where(
        OperationalDocumentRequirement.requirement_level != "OPTIONAL",
        valid_assessment_tenant,
        ~overridden,
        or_(unresolved, definite),
    )


def _ranked_population(actor, at: datetime, search: str | None):
    authorized, has_request, has_oip = _authorized_population(actor)
    population = _search_population(authorized, search)
    promotions = _oip_promotions(at) if has_oip else None
    reason_queries = [
        *_execution_reasons(population, promotions, at),
        *_work_reasons(population, promotions, at),
        _sla_reasons(population),
    ]
    if has_request:
        reason_queries.append(_readiness_reasons(population, at))
    reasons = union_all(*reason_queries).cte("control_tower_reasons")
    minimum = select(
        reasons.c.shipment_id,
        func.min(reasons.c.attention_rank).label("attention_rank"),
    ).group_by(reasons.c.shipment_id).cte("control_tower_minimum_attention")
    aggregate = select(
        reasons.c.shipment_id,
        minimum.c.attention_rank,
        func.min(case(
            (reasons.c.attention_rank == minimum.c.attention_rank, reasons.c.due_at),
        )).label("due_at"),
        func.min(case(
            (reasons.c.attention_rank == minimum.c.attention_rank, reasons.c.onset_at),
        )).label("onset_at"),
    ).join(
        minimum, minimum.c.shipment_id == reasons.c.shipment_id
    ).group_by(
        reasons.c.shipment_id, minimum.c.attention_rank
    ).cte("control_tower_attention_aggregate")
    due_bucket = case(
        (aggregate.c.due_at < at, 0),
        (aggregate.c.due_at.is_not(None), 1),
        else_=2,
    )
    attention = case(
        (aggregate.c.attention_rank == 0, "urgent"),
        (aggregate.c.attention_rank == 1, "follow_up"),
        else_="review",
    )
    return select(
        population.c.shipment_id,
        population.c.shipment_public_id,
        aggregate.c.attention_rank,
        attention.label("attention"),
        due_bucket.label("due_bucket"),
        aggregate.c.due_at,
        aggregate.c.onset_at,
    ).join(
        aggregate, aggregate.c.shipment_id == population.c.shipment_id
    ).cte("control_tower_ranked")


def select_attention_window(
    actor,
    *,
    at: datetime,
    page_size: int,
    offset: int,
    attention: str | None,
    search: str | None,
) -> AttentionWindow:
    ranked = _ranked_population(actor, at, search)
    with_counts = select(
        ranked,
        func.sum(case((ranked.c.attention == "urgent", 1), else_=0)).over().label("urgent"),
        func.sum(case((ranked.c.attention == "follow_up", 1), else_=0)).over().label("follow_up"),
        func.sum(case((ranked.c.attention == "review", 1), else_=0)).over().label("review"),
    ).cte("control_tower_ranked_counts")
    filtered = select(
        with_counts,
        func.count().over().label("total"),
    )
    if attention is not None:
        filtered = filtered.where(with_counts.c.attention == attention)
    filtered = filtered.cte("control_tower_filtered_counts")
    page_rows = db.session.execute(select(filtered).order_by(
        filtered.c.attention_rank.asc(),
        filtered.c.due_bucket.asc(),
        filtered.c.due_at.asc().nulls_last(),
        filtered.c.onset_at.asc().nulls_last(),
        filtered.c.shipment_public_id.asc(),
    ).offset(offset).limit(page_size + 1)).all()
    if page_rows:
        totals_row = page_rows[0]
    else:
        # The requested offset may have become empty after concurrent changes.
        totals_row = db.session.execute(select(
            func.coalesce(func.sum(case((
                ranked.c.attention == attention if attention is not None else literal(True), 1
            ), else_=0)), 0).label("total"),
            func.coalesce(func.sum(case((ranked.c.attention == "urgent", 1), else_=0)), 0).label("urgent"),
            func.coalesce(func.sum(case((ranked.c.attention == "follow_up", 1), else_=0)), 0).label("follow_up"),
            func.coalesce(func.sum(case((ranked.c.attention == "review", 1), else_=0)), 0).label("review"),
        ).select_from(ranked)).one()
    has_more = len(page_rows) > page_size
    selected = page_rows[:page_size]
    rows = tuple(AttentionWindowRow(
        row.shipment_id,
        row.shipment_public_id,
        row.attention,
        (
            row.attention_rank,
            row.due_bucket,
            row.due_at,
            row.onset_at,
            row.shipment_public_id,
        ),
    ) for row in selected)
    return AttentionWindow(
        rows,
        int(totals_row.total),
        {
            "urgent": int(totals_row.urgent),
            "follow_up": int(totals_row.follow_up),
            "review": int(totals_row.review),
        },
        has_more,
    )
