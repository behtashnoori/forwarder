"""Read-only, source-specific OIP verification; never discovers attention work."""
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import or_, select

from backend.extensions import db
from backend.oip_models import (
    OipAttentionProjection, OipFactReference, OipSignal, OipSituation,
    OipSituationEvidence, OipThresholdPolicy,
)
from backend.operational_models import Project
from backend.services.oip_service import POLICIES, PROJECTION_VERSION, _hash
from backend.services.control_tower_translation import utc


@dataclass(frozen=True)
class VerifiedEnrichment:
    """Internal comparable policy cohort, never source payload or provenance."""
    policy_id: str
    policy_version: str
    urgency: str
    severity: str
    promotes_urgent: bool
    # Opaque parity inputs. They are populated only after the full governed
    # OIP verification below and are never used to discover or rank work.
    situation_identity_key: str | None = None
    source_watermark: str | None = None
    calculated_at: str | None = None
    priority: str | None = None


def _current_threshold(context, shipment, at):
    project = db.session.scalar(select(Project).where(
        Project.id == shipment.project_id, Project.organization_id == context.organization_id,
    ).execution_options(populate_existing=True)) if shipment.project_id else None
    scopes = [((OipThresholdPolicy.scope_type == "ENTERPRISE") &
               (OipThresholdPolicy.scope_public_id == "ENTERPRISE"))]
    if project:
        scopes.append((OipThresholdPolicy.scope_type == "PROJECT") &
                      (OipThresholdPolicy.scope_public_id == project.public_id))
    rows = db.session.scalars(select(OipThresholdPolicy).where(
        OipThresholdPolicy.organization_id == context.organization_id,
        OipThresholdPolicy.signal_type == "NEXT_MILESTONE_OVERDUE",
        OipThresholdPolicy.is_active.is_(True),
        OipThresholdPolicy.effective_from <= at,
        or_(OipThresholdPolicy.effective_to.is_(None), OipThresholdPolicy.effective_to > at),
        or_(*scopes),
    ).execution_options(populate_existing=True)).all()
    preferred = [p for p in rows if p.scope_type == "PROJECT"] or rows
    return max(preferred, key=lambda p: (p.version, utc(p.effective_from), p.id)) if preferred else None


def _governed_overdue(context, shipment, situation, signal, due, at):
    evaluation = (signal.derivation or {}).get("evaluation")
    if not isinstance(evaluation, dict):
        return False
    policy = _current_threshold(context, shipment, at)
    if not policy or not policy.authority or not policy.source:
        return False
    seconds = policy.value * {"MINUTE": 60, "HOUR": 3600, "DAY": 86400}[policy.unit]
    expected = {
        "status": "CONFIGURED", "policy_public_id": policy.public_id,
        "policy_version": policy.version, "value": policy.value, "unit": policy.unit,
        "scope": policy.scope_type, "scope_public_id": policy.scope_public_id,
        "authority": policy.authority, "source": policy.source,
        "reason": "AFTER_AUTHORIZED_TOLERANCE",
        "time_source": "RUNTIME_OPERATIONAL_WORK_ITEM_DUE",
    }
    try:
        from datetime import datetime
        evaluated = utc(datetime.fromisoformat(evaluation["evaluated_at"]))
        evaluated_due = utc(datetime.fromisoformat(evaluation["effective_due_at"]))
    except (KeyError, TypeError, ValueError):
        return False
    return (all(evaluation.get(k) == v for k, v in expected.items())
            and str(policy.version) == situation.policy_version == signal.policy_version
            and evaluated_due == due and evaluated == utc(situation.calculated_at)
            and utc(policy.effective_from) <= evaluated
            and due is not None and due + timedelta(seconds=seconds) < evaluated <= at
            and (situation.priority_explanation or {}).get("evaluation") == evaluation)


def verified_enrichments(context, shipment, *, situation_type, source_type,
                         source_public_id, source_version, dimensions, occurred_at,
                         due_at=None, authoritative_due=False, work_item_id=None, at):
    """Caller has refreshed scope and validated an active A/B row in this read.

    Every lookup is constrained to this shipment AND underlying source before
    materialization. No queue, health mutation, reconcile or tenant-wide scan.
    """
    policy = POLICIES[situation_type]
    identity = _hash([context.organization_id, situation_type, context.shipment_public_id,
                      dimensions, policy["id"], policy["version"].split(".")[0]])
    watermark = f"{source_type}:{source_public_id}:{source_version}"
    query = select(OipSituation, OipFactReference, OipSignal, OipAttentionProjection).join(
        OipSituationEvidence, OipSituationEvidence.situation_id == OipSituation.id,
    ).join(OipFactReference, OipFactReference.id == OipSituationEvidence.fact_reference_id).join(
        OipSignal, OipSignal.id == OipSituationEvidence.signal_id,
    ).join(OipAttentionProjection, OipAttentionProjection.situation_id == OipSituation.id).where(
        OipSituation.organization_id == context.organization_id,
        OipSituation.subject_type == "SHIPMENT",
        OipSituation.subject_public_id == context.shipment_public_id,
        OipSituation.situation_type == situation_type,
        OipSituation.identity_key == identity,
        OipSituation.status.in_(("OPEN", "ACKNOWLEDGED", "IN_PROGRESS")),
        OipSituationEvidence.is_current.is_(True),
        OipFactReference.organization_id == context.organization_id,
        OipFactReference.subject_type == "SHIPMENT",
        OipFactReference.subject_public_id == context.shipment_public_id,
        OipFactReference.source_domain == "OPERATIONAL_EXECUTION",
        OipFactReference.source_type == source_type,
        OipFactReference.source_public_id == source_public_id,
        OipFactReference.source_version == str(source_version),
        OipFactReference.validity == "CURRENT",
        OipFactReference.superseded_by_public_id.is_(None),
        OipSignal.organization_id == context.organization_id,
        OipSignal.subject_type == "SHIPMENT",
        OipSignal.subject_public_id == context.shipment_public_id,
        OipSignal.signal_type == situation_type,
        OipSignal.active.is_(True),
    ).execution_options(populate_existing=True)
    result = []
    for s, fact, signal, projection in db.session.execute(query):
        if (s.identity_dimensions != dimensions or signal.dedup_key != identity
                or (signal.derivation or {}).get("condition") != "authoritative source predicate"
                or (signal.derivation or {}).get("inputs") != dimensions
                or s.policy_id != policy["id"] or signal.policy_id != policy["id"]
                or s.freshness_status != "FRESH" or s.resolved_at is not None
                or s.source_watermark != watermark or signal.source_watermark != watermark
                or projection.source_watermark != watermark
                or s.projection_version != PROJECTION_VERSION
                or projection.projection_version != PROJECTION_VERSION
                or utc(fact.occurred_at) != utc(occurred_at)
                or utc(s.due_at) != utc(due_at)
                or not (utc(signal.observed_at) <= utc(s.calculated_at) <= utc(projection.calculated_at) <= at)
                or projection.operational_work_item_id not in (None, work_item_id)):
            continue
        if situation_type == "NEXT_MILESTONE_OVERDUE":
            if not _governed_overdue(context, shipment, s, signal, utc(due_at), at):
                continue
        elif s.policy_version != policy["version"] or signal.policy_version != policy["version"]:
            continue
        comparable = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if s.urgency not in comparable or s.severity not in comparable:
            continue
        promotes = (s.urgency == "CRITICAL" or s.severity == "CRITICAL"
                    or situation_type in {"ACTIVE_DELAY_OR_EXCEPTION", "NEXT_MILESTONE_OVERDUE"}
                    and s.urgency == s.severity == "HIGH"
                    or s.urgency == "HIGH" and authoritative_due
                    and due_at is not None and utc(due_at) < at)
        verified = VerifiedEnrichment(
            s.policy_id,
            s.policy_version,
            s.urgency,
            s.severity,
            promotes,
            situation_identity_key=s.identity_key,
            source_watermark=s.source_watermark,
            calculated_at=utc(s.calculated_at).isoformat(),
            priority=s.priority,
        )
        if verified not in result:
            result.append(verified)
    return tuple(result)
