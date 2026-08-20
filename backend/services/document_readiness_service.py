"""Deterministic MDPM-1 document readiness policy and source-fact commands."""

from datetime import timezone
from sqlalchemy import select

from backend.extensions import db
from backend.mdpm_models import (
    ArtifactAssociation,
    DocumentAssessment,
    DocumentReadinessAudit,
    OperationalDocumentRequirement,
    RequirementApplicabilityDecision,
    TransitionOverride,
)
from backend.models import CaseDocumentFile, CaseDocumentRequirement
from backend.operational_models import Milestone, OperationalShipment, utcnow
from backend.project_configuration_models import ProjectDocumentRequirement
from backend.services.operational_service import (
    OperationalError,
    organization_for_user,
    require_permission,
)

ASSESSMENTS = {"REVIEW_STARTED", "APPROVED", "REJECTED", "VERIFIED"}


def _shipment(public_id, user, permission="document_readiness.read", lock=False):
    require_permission(user, permission)
    org = organization_for_user(user["id"])
    q = select(OperationalShipment).where(
        OperationalShipment.public_id == public_id,
        OperationalShipment.organization_id == org,
    )
    row = db.session.scalar(q.with_for_update() if lock else q)
    if not row:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "Operational shipment was not found.", 404
        )
    if row.source_type == "direct":
        raise OperationalError(
            "SOURCE_CAPABILITY_NOT_APPLICABLE",
            "Request-scoped document readiness is not applicable to direct operations.",
            409,
        )
    return row


def _requirement(shipment, public_id, lock=False):
    q = select(OperationalDocumentRequirement).where(
        OperationalDocumentRequirement.public_id == public_id,
        OperationalDocumentRequirement.operational_shipment_id == shipment.id,
        OperationalDocumentRequirement.organization_id == shipment.organization_id,
    )
    row = db.session.scalar(q.with_for_update() if lock else q)
    if not row:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "Document requirement was not found.", 404
        )
    return row


def _audit(shipment, user, event, requirement=None, milestone=None, evidence=None):
    db.session.add(
        DocumentReadinessAudit(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id,
            event_type=event,
            actor_user_id=user["id"],
            requirement_id=requirement.id if requirement else None,
            milestone_id=milestone.id if milestone else None,
            evidence=evidence or {},
        )
    )


def materialization_preview(shipment_id, user):
    shipment = _shipment(shipment_id, user)
    existing = db.session.scalars(
        select(OperationalDocumentRequirement).where(
            OperationalDocumentRequirement.operational_shipment_id == shipment.id
        )
    ).all()
    from backend.models import OrganizationDocumentRequirement, ShipmentRequest
    from backend.services.organization_document_policy_service import (
        effective_definitions,
    )

    request_row = (
        db.session.get(ShipmentRequest, shipment.shipment_request_id)
        if shipment.shipment_request_id
        else None
    )
    configured = effective_definitions(
        shipment.organization_id,
        request_row.shipping_type if request_row else "all",
        shipment.project_id,
    )
    project_rows = (
        []
        if shipment.project_id is None
        else db.session.scalars(
            select(ProjectDocumentRequirement).where(
                ProjectDocumentRequirement.project_id == shipment.project_id,
                ProjectDocumentRequirement.is_active.is_(True),
            )
        ).all()
    )
    project_by_definition = {row.document_definition_id: row for row in project_rows}
    policy_rows = db.session.scalars(
        select(OrganizationDocumentRequirement).where(
            OrganizationDocumentRequirement.operational_organization_id
            == shipment.organization_id
        )
    ).all()
    policy_by_definition = {row.document_definition_id: row for row in policy_rows}
    rows, findings = [], []
    for definition, level in configured:
        source = project_by_definition.get(definition.id)
        policy = policy_by_definition.get(definition.id)
        target = source.target_milestone_type if source else None
        warnings = []
        rows.append(
            {
                "source_requirement_public_id": source.public_id if source else None,
                "source_organization_policy_id": policy.id
                if policy and not source
                else None,
                "source_version": source.version
                if source
                else (policy.version if policy else None),
                "document_definition_public_id": definition.public_id,
                "document_definition_id": definition.id,
                "title": definition.title,
                "requirement_level": level,
                "required_assessment_level": source.required_assessment_level
                if source
                else "APPROVED",
                "target_milestone_type": target.immutable_code if target else None,
                "target_status": source.target_status if source else None,
                "warnings": warnings,
            }
        )
    active = [r for r in rows if "INACTIVE_REQUIREMENT" not in r["warnings"]]
    return {
        "initialized": bool(existing),
        "existing_count": len(existing),
        "requirements": rows,
        "findings": findings,
        "confirmation_allowed": not existing
        and bool(active)
        and not any(r["warnings"] for r in active),
    }


def materialize(shipment_id, payload, user):
    shipment = _shipment(shipment_id, user, "document_readiness.manage", True)
    if shipment.version != payload.get("expected_shipment_version"):
        raise OperationalError(
            "STALE_AGGREGATE_VERSION", "Shipment was changed by another operation.", 409
        )
    existing = db.session.scalars(
        select(OperationalDocumentRequirement).where(
            OperationalDocumentRequirement.operational_shipment_id == shipment.id
        )
    ).all()
    if existing:
        return existing, False
    preview = materialization_preview(shipment_id, user)
    if not preview["confirmation_allowed"]:
        raise OperationalError(
            "MATERIALIZATION_NOT_ALLOWED",
            "Project document configuration is incomplete or inactive.",
            422,
        )
    sources = preview["requirements"]
    created = []
    for source in sources:
        row = OperationalDocumentRequirement(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id,
            document_definition_id=source["document_definition_id"],
            source_project_requirement_id=(
                db.session.scalar(
                    select(ProjectDocumentRequirement.id).where(
                        ProjectDocumentRequirement.public_id
                        == source["source_requirement_public_id"]
                    )
                )
                if source["source_requirement_public_id"]
                else None
            ),
            source_project_requirement_public_id=source["source_requirement_public_id"],
            source_project_requirement_version=source["source_version"]
            if source["source_requirement_public_id"]
            else None,
            source_organization_policy_id=source["source_organization_policy_id"],
            requirement_level=source["requirement_level"],
            applicability_state="UNRESOLVED"
            if source["requirement_level"] == "CONDITIONAL"
            else "APPLICABLE",
            required_assessment_level=source["required_assessment_level"],
            target_milestone_type=source["target_milestone_type"],
            target_status=source["target_status"],
            created_by_user_id=user["id"],
        )
        db.session.add(row)
        db.session.flush()
        created.append(row)
        _audit(
            shipment,
            user,
            "RequirementMaterialized",
            row,
            evidence={
                "source_public_id": source["source_requirement_public_id"],
                "source_version": source["source_version"],
            },
        )
    shipment.version += 1
    db.session.commit()
    return created, True


def _active_association(req):
    return db.session.scalar(
        select(ArtifactAssociation)
        .where(
            ArtifactAssociation.requirement_id == req.id,
            ArtifactAssociation.state == "ACTIVE",
        )
        .order_by(
            ArtifactAssociation.associated_at.desc(), ArtifactAssociation.id.desc()
        )
    )


def _assessment(association):
    if not association:
        return None
    return db.session.scalar(
        select(DocumentAssessment)
        .where(DocumentAssessment.association_id == association.id)
        .order_by(DocumentAssessment.created_at.desc(), DocumentAssessment.id.desc())
    )


def _readiness_status(req, association, assessment):
    if req.applicability_state == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if req.applicability_state == "UNRESOLVED":
        return "UNRESOLVED"
    if (
        not association
        or association.artifact.status != "active"
        or association.artifact.version_number != association.artifact_version
    ):
        return "MISSING"
    if assessment and assessment.decision == "REJECTED":
        return "REJECTED"
    if req.required_assessment_level == "VERIFIED":
        return (
            "SATISFIED"
            if assessment and assessment.decision == "VERIFIED"
            else "PENDING_REVIEW"
        )
    return (
        "SATISFIED"
        if assessment and assessment.decision in {"APPROVED", "VERIFIED"}
        else "PENDING_REVIEW"
    )


def _requirement_projection(req):
    assoc = _active_association(req)
    assessment = _assessment(assoc)
    applicability = db.session.scalar(
        select(RequirementApplicabilityDecision)
        .where(RequirementApplicabilityDecision.requirement_id == req.id)
        .order_by(
            RequirementApplicabilityDecision.created_at.desc(),
            RequirementApplicabilityDecision.id.desc(),
        )
    )
    return {
        "public_id": req.public_id,
        "title": req.definition.title,
        "document_code": req.definition.code,
        "document_definition_public_id": req.definition.public_id,
        "requirement_level": req.requirement_level,
        "applicability_state": req.applicability_state,
        "required_assessment_level": req.required_assessment_level,
        "target_milestone_type": req.target_milestone_type,
        "target_status": req.target_status,
        "version": req.version,
        "readiness_status": _readiness_status(req, assoc, assessment),
        "applicability_reason": applicability.reason if applicability else None,
        "artifact": (
            {
                "association_public_id": assoc.public_id,
                "artifact_public_id": assoc.artifact.public_id,
                "filename": assoc.artifact.original_filename,
                "version": assoc.artifact_version,
                "status": assoc.artifact.status,
                "assessment": assessment.decision if assessment else "ASSOCIATED",
                "associated_at": assoc.associated_at.isoformat(),
                "association_reason": assoc.reason,
            }
            if assoc
            else None
        ),
    }


def list_requirements(shipment_id, user):
    shipment = _shipment(shipment_id, user)
    return [
        _requirement_projection(r)
        for r in db.session.scalars(
            select(OperationalDocumentRequirement)
            .where(
                OperationalDocumentRequirement.operational_shipment_id == shipment.id,
                OperationalDocumentRequirement.is_active.is_(True),
            )
            .order_by(OperationalDocumentRequirement.id)
        ).all()
    ]


def list_eligible_artifacts(shipment_id, requirement_id, user):
    shipment = _shipment(shipment_id, user)
    req = _requirement(shipment, requirement_id)
    return [
        {
            "artifact_public_id": artifact.public_id,
            "filename": artifact.original_filename,
            "version": artifact.version_number,
        }
        for artifact in db.session.scalars(
            select(CaseDocumentFile)
            .join(
                CaseDocumentRequirement,
                CaseDocumentRequirement.id == CaseDocumentFile.case_requirement_id,
            )
            .where(
                CaseDocumentFile.shipment_request_id == shipment.shipment_request_id,
                CaseDocumentFile.operational_organization_id
                == shipment.organization_id,
                CaseDocumentFile.status == "active",
                CaseDocumentFile.is_miscellaneous.is_(False),
                CaseDocumentRequirement.shipment_request_id
                == shipment.shipment_request_id,
                CaseDocumentRequirement.operational_organization_id
                == shipment.organization_id,
                CaseDocumentRequirement.source_definition_id
                == req.document_definition_id,
            )
            .order_by(CaseDocumentFile.uploaded_at.desc(), CaseDocumentFile.id.desc())
        ).all()
    ]


def associate(shipment_id, requirement_id, payload, user):
    shipment = _shipment(shipment_id, user, "document_readiness.manage", True)
    req = _requirement(shipment, requirement_id, True)
    if req.version != payload.get("expected_requirement_version"):
        raise OperationalError(
            "STALE_REQUIREMENT_VERSION",
            "Requirement was changed by another operation.",
            409,
        )
    artifact = db.session.scalar(
        select(CaseDocumentFile)
        .where(CaseDocumentFile.public_id == payload.get("artifact_public_id"))
        .with_for_update()
    )
    if (
        not artifact
        or artifact.shipment_request_id != shipment.shipment_request_id
        or artifact.operational_organization_id != shipment.organization_id
    ):
        raise OperationalError(
            "ARTIFACT_NOT_ELIGIBLE", "Artifact is not visible for this shipment.", 404
        )
    if (
        artifact.status != "active"
        or artifact.is_miscellaneous
        or not artifact.case_requirement_id
    ):
        raise OperationalError(
            "ARTIFACT_NOT_ELIGIBLE", "Artifact must be the active typed version.", 422
        )
    if artifact.case_requirement_id:
        case_req = db.session.get(CaseDocumentRequirement, artifact.case_requirement_id)
        if (
            not case_req
            or case_req.shipment_request_id != shipment.shipment_request_id
            or case_req.operational_organization_id != shipment.organization_id
            or case_req.source_definition_id != req.document_definition_id
        ):
            raise OperationalError(
                "ARTIFACT_TYPE_MISMATCH",
                "Artifact type does not match the requirement.",
                422,
            )
    old = _active_association(req)
    if old:
        old.state = "SUPERSEDED"
        old.superseded_at = utcnow()
        _audit(
            shipment,
            user,
            "ArtifactAssociationSuperseded",
            req,
            evidence={"association_public_id": old.public_id},
        )
    row = ArtifactAssociation(
        organization_id=shipment.organization_id,
        requirement_id=req.id,
        document_file_id=artifact.id,
        artifact_version=artifact.version_number,
        reason=str(payload.get("reason") or "").strip() or None,
        associated_by_user_id=user["id"],
    )
    db.session.add(row)
    req.version += 1
    db.session.flush()
    _audit(
        shipment,
        user,
        "ArtifactAssociated",
        req,
        evidence={
            "association_public_id": row.public_id,
            "artifact_public_id": artifact.public_id,
            "artifact_version": artifact.version_number,
        },
    )
    db.session.commit()
    return _requirement_projection(req)


def remove_association(shipment_id, requirement_id, payload, user):
    shipment = _shipment(shipment_id, user, "document_readiness.manage", True)
    req = _requirement(shipment, requirement_id, True)
    if req.version != payload.get("expected_requirement_version"):
        raise OperationalError(
            "STALE_REQUIREMENT_VERSION",
            "Requirement was changed by another operation.",
            409,
        )
    association = _active_association(req)
    if not association:
        raise OperationalError(
            "DOC_ARTIFACT_MISSING", "No active artifact association exists.", 409
        )
    association.state = "SUPERSEDED"
    association.superseded_at = utcnow()
    req.version += 1
    _audit(
        shipment,
        user,
        "ArtifactAssociationRemoved",
        req,
        evidence={"association_public_id": association.public_id},
    )
    db.session.commit()
    return _requirement_projection(req)


def assess(shipment_id, requirement_id, payload, user):
    decision = str(payload.get("decision") or "").upper()
    permission = (
        "document_readiness.verify"
        if decision == "VERIFIED"
        else "document_readiness.assess"
    )
    shipment = _shipment(shipment_id, user, permission, True)
    req = _requirement(shipment, requirement_id, True)
    expected_version = payload.get("expected_requirement_version")
    if expected_version is not None and req.version != expected_version:
        raise OperationalError(
            "STALE_REQUIREMENT_VERSION",
            "Requirement was changed by another operation.",
            409,
        )
    if decision not in ASSESSMENTS:
        raise OperationalError("VALIDATION_FAILED", "Assessment decision is invalid.")
    assoc = _active_association(req)
    if (
        not assoc
        or assoc.artifact.status != "active"
        or assoc.artifact.version_number != assoc.artifact_version
    ):
        raise OperationalError(
            "DOC_ARTIFACT_MISSING", "An active exact artifact version is required.", 409
        )
    reason = str(payload.get("reason") or "").strip() or None
    if decision == "REJECTED" and not reason:
        raise OperationalError(
            "STRUCTURED_REASON_REQUIRED", "Rejection reason is required."
        )
    row = DocumentAssessment(
        organization_id=shipment.organization_id,
        association_id=assoc.id,
        decision=decision,
        reason=reason,
        actor_user_id=user["id"],
    )
    db.session.add(row)
    req.version += 1
    db.session.flush()
    _audit(
        shipment,
        user,
        {
            "REVIEW_STARTED": "ReviewStarted",
            "APPROVED": "DocumentApproved",
            "REJECTED": "DocumentRejected",
            "VERIFIED": "DocumentVerified",
        }[decision],
        req,
        evidence={
            "assessment_public_id": row.public_id,
            "artifact_version": assoc.artifact_version,
        },
    )
    db.session.commit()
    return _requirement_projection(req)


def resolve_applicability(shipment_id, requirement_id, payload, user):
    shipment = _shipment(shipment_id, user, "document_readiness.manage", True)
    req = _requirement(shipment, requirement_id, True)
    if req.requirement_level != "CONDITIONAL":
        raise OperationalError(
            "VALIDATION_FAILED",
            "Only conditional requirements need applicability resolution.",
        )
    if req.version != payload.get("expected_requirement_version"):
        raise OperationalError(
            "STALE_REQUIREMENT_VERSION",
            "Requirement was changed by another operation.",
            409,
        )
    decision = str(payload.get("decision") or "").upper()
    reason = str(payload.get("reason") or "").strip()
    if decision not in {"APPLICABLE", "NOT_APPLICABLE"} or not reason:
        raise OperationalError("VALIDATION_FAILED", "Decision and reason are required.")
    db.session.add(
        RequirementApplicabilityDecision(
            organization_id=shipment.organization_id,
            requirement_id=req.id,
            decision=decision,
            reason=reason,
            actor_user_id=user["id"],
        )
    )
    req.applicability_state = decision
    req.version += 1
    _audit(
        shipment,
        user,
        "ApplicabilityResolved",
        req,
        evidence={"decision": decision, "reason": reason},
    )
    db.session.commit()
    return _requirement_projection(req)


def transition_readiness(shipment, milestone, target_status, user=None):
    if shipment.source_type == "direct":
        return {
            "allowed": True,
            "applicability": "NOT_APPLICABLE",
            "source_type": "direct",
            "operational_result": {"allowed": True},
            "document_result": {"applicability": "NOT_APPLICABLE"},
            "blocking_requirements": [],
            "warnings": [],
            "evidence_references": [],
            "configuration_requirement_versions": [],
            "override_status": {"applied": []},
            "_overrides": [],
        }
    now = utcnow()
    requirements = db.session.scalars(
        select(OperationalDocumentRequirement)
        .where(
            OperationalDocumentRequirement.operational_shipment_id == shipment.id,
            OperationalDocumentRequirement.organization_id == shipment.organization_id,
            OperationalDocumentRequirement.target_milestone_type
            == milestone.milestone_type,
            OperationalDocumentRequirement.target_status == target_status,
            OperationalDocumentRequirement.is_active.is_(True),
        )
        .with_for_update()
    ).all()
    blockers, warnings, override_rows = [], [], []
    for req in requirements:
        code = None
        assoc = _active_association(req)
        assessment = _assessment(assoc)
        if (
            req.requirement_level == "CONDITIONAL"
            and req.applicability_state == "UNRESOLVED"
        ):
            code = "DOC_REQUIREMENT_UNRESOLVED"
        elif req.applicability_state == "NOT_APPLICABLE":
            continue
        elif (
            not assoc
            or assoc.artifact.status != "active"
            or assoc.artifact.version_number != assoc.artifact_version
        ):
            code = "DOC_ARTIFACT_MISSING" if not assoc else "DOC_ARTIFACT_SUPERSEDED"
        elif assessment and assessment.decision == "REJECTED":
            code = "DOC_ARTIFACT_REJECTED"
        elif req.required_assessment_level == "VERIFIED" and (
            not assessment or assessment.decision != "VERIFIED"
        ):
            code = "DOC_VERIFICATION_REQUIRED"
        elif req.required_assessment_level == "APPROVED" and (
            not assessment or assessment.decision not in {"APPROVED", "VERIFIED"}
        ):
            code = "DOC_APPROVAL_REQUIRED"
        if code:
            ov = db.session.scalar(
                select(TransitionOverride)
                .where(
                    TransitionOverride.organization_id == shipment.organization_id,
                    TransitionOverride.operational_shipment_id == shipment.id,
                    TransitionOverride.requirement_id == req.id,
                    TransitionOverride.milestone_id == milestone.id,
                    TransitionOverride.target_status == target_status,
                    TransitionOverride.state == "ACTIVE",
                )
                .with_for_update()
            )
            if ov and (ov.expires_at is None or ov.expires_at > now):
                override_rows.append(ov)
                continue
            item = {
                "code": code,
                "requirement_public_id": req.public_id,
                "title": req.definition.title,
            }
            (warnings if req.requirement_level == "OPTIONAL" else blockers).append(item)
    return {
        "allowed": not blockers,
        "evaluated_at": now.isoformat(),
        "subject": {
            "shipment_public_id": shipment.public_id,
            "shipment_version": shipment.version,
            "milestone_public_id": milestone.public_id,
            "milestone_version": milestone.version,
        },
        "target_action": target_status,
        "operational_result": {"allowed": True},
        "document_result": {"allowed": not blockers},
        "blocking_requirements": blockers,
        "warnings": warnings,
        "evidence_references": [],
        "configuration_requirement_versions": [
            {
                "public_id": r.public_id,
                "version": r.version,
                "source_version": r.source_project_requirement_version,
            }
            for r in requirements
        ],
        "override_status": {"applied": [o.public_id for o in override_rows]},
        "_overrides": override_rows,
    }


def readiness(shipment_id, milestone_id, target_status, user):
    shipment = _shipment(shipment_id, user)
    milestone = db.session.scalar(
        select(Milestone).where(
            Milestone.public_id == milestone_id,
            Milestone.operational_shipment_id == shipment.id,
        )
    )
    if not milestone:
        raise OperationalError("RESOURCE_NOT_FOUND", "Milestone was not found.", 404)
    result = transition_readiness(shipment, milestone, str(target_status).upper())
    result.pop("_overrides", None)
    return result


def next_readiness(shipment_id, user):
    shipment = _shipment(shipment_id, user)
    milestone = db.session.scalar(
        select(Milestone)
        .where(
            Milestone.operational_shipment_id == shipment.id,
            Milestone.lifecycle_status.not_in(("COMPLETED", "SKIPPED", "CANCELLED")),
        )
        .order_by(Milestone.sequence, Milestone.id)
    )
    if not milestone:
        return None
    target = {
        "PENDING": "READY",
        "READY": "IN_PROGRESS",
        "IN_PROGRESS": "COMPLETED",
        "BLOCKED": "READY",
    }.get(milestone.lifecycle_status)
    if not target:
        return None
    result = transition_readiness(shipment, milestone, target)
    result.pop("_overrides", None)
    return result


def create_override(shipment_id, requirement_id, payload, user):
    shipment = _shipment(shipment_id, user, "document_readiness.override", True)
    req = _requirement(shipment, requirement_id, True)
    milestone = db.session.scalar(
        select(Milestone)
        .where(
            Milestone.public_id == payload.get("milestone_public_id"),
            Milestone.operational_shipment_id == shipment.id,
        )
        .with_for_update()
    )
    authority, reason = (
        str(payload.get("authority") or "").strip(),
        str(payload.get("reason") or "").strip(),
    )
    target = str(payload.get("target_status") or "").upper()
    if (
        not milestone
        or not authority
        or not reason
        or target != req.target_status
        or milestone.milestone_type != req.target_milestone_type
    ):
        raise OperationalError(
            "VALIDATION_FAILED",
            "Exact milestone, transition, authority, and reason are required.",
        )
    expires = payload.get("expires_at")
    parsed = None
    if expires:
        from datetime import datetime

        try:
            parsed = datetime.fromisoformat(
                str(expires).replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except ValueError as exc:
            raise OperationalError(
                "VALIDATION_FAILED", "expires_at must be ISO-8601."
            ) from exc
    row = TransitionOverride(
        organization_id=shipment.organization_id,
        operational_shipment_id=shipment.id,
        requirement_id=req.id,
        milestone_id=milestone.id,
        target_status=target,
        authority=authority,
        reason=reason,
        evidence_reference=str(payload.get("evidence_reference") or "").strip() or None,
        actor_user_id=user["id"],
        expires_at=parsed,
    )
    db.session.add(row)
    db.session.flush()
    _audit(
        shipment,
        user,
        "OverrideGranted",
        req,
        milestone,
        {
            "override_public_id": row.public_id,
            "authority": authority,
            "reason": reason,
            "evidence_reference": row.evidence_reference,
        },
    )
    db.session.commit()
    return {"public_id": row.public_id, "state": row.state}


def revoke_override(shipment_id, override_id, user):
    shipment = _shipment(shipment_id, user, "document_readiness.override", True)
    row = db.session.scalar(
        select(TransitionOverride)
        .where(
            TransitionOverride.public_id == override_id,
            TransitionOverride.operational_shipment_id == shipment.id,
            TransitionOverride.organization_id == shipment.organization_id,
        )
        .with_for_update()
    )
    if not row:
        raise OperationalError("RESOURCE_NOT_FOUND", "Override was not found.", 404)
    if row.state != "ACTIVE":
        raise OperationalError(
            "OVERRIDE_NOT_ACTIVE", "Override is no longer active.", 409
        )
    row.state = "REVOKED"
    row.revoked_at = utcnow()
    row.revoked_by_user_id = user["id"]
    _audit(
        shipment,
        user,
        "OverrideRevoked",
        db.session.get(OperationalDocumentRequirement, row.requirement_id),
        db.session.get(Milestone, row.milestone_id),
        {"override_public_id": row.public_id},
    )
    db.session.commit()
    return {"public_id": row.public_id, "state": row.state}
