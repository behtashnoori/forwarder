"""Focused MDPM-1 readiness, replacement, conditional and override contracts."""

from datetime import datetime, timezone

from backend.tests.test_operational_execution_190 import actor
from backend.extensions import db
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    DocumentDefinition,
    ExpertQuote,
)
from backend.operational_models import (
    OperationalMembership,
    OperationalShipment,
    Project,
)
from backend.project_configuration_models import (
    MilestoneType,
    ProjectDocumentRequirement,
)
from backend.services import document_readiness_service as docs
from backend.services import operational_execution_service as execution

pytest_plugins = ("backend.tests.test_operational_execution_190",)


def _seed(app, *, level="REQUIRED", assessment="APPROVED"):
    membership = db.session.get(OperationalMembership, 1)
    membership.permissions = list(membership.permissions) + [
        "document_readiness.read",
        "document_readiness.manage",
        "document_readiness.assess",
        "document_readiness.verify",
        "document_readiness.override",
    ]
    shipment = OperationalShipment.query.one()
    project = db.session.get(Project, shipment.project_id)
    mt = MilestoneType.query.one()
    definition = DocumentDefinition(
        code=f"DOC-{level}-{assessment}",
        title="Gate document",
        is_required=True,
        allowed_formats='["pdf"]',
        max_file_size_bytes=1000,
        max_active_file_count=1,
        applicability_scope="all",
    )
    db.session.add(definition)
    db.session.flush()
    configured = ProjectDocumentRequirement(
        project_id=project.id,
        document_definition_id=definition.id,
        requirement_level=level,
        required_assessment_level=assessment,
        target_milestone_type_id=mt.id,
        target_status="READY",
        created_by=app.config["ctx"]["operator"],
        updated_by=app.config["ctx"]["operator"],
    )
    db.session.add(configured)
    db.session.commit()
    milestones, _ = execution.initialize(
        shipment.public_id, {"expected_shipment_version": 1}, actor(app)
    )
    requirements, _ = docs.materialize(
        shipment.public_id, {"expected_shipment_version": 2}, actor(app)
    )
    return shipment, milestones[0], requirements[0], definition


def _artifact(shipment, definition, version=1):
    case_req = CaseDocumentRequirement(
        operational_organization_id=shipment.organization_id,
        shipment_request_id=shipment.shipment_request_id,
        source_definition_id=definition.id,
        source_definition_code=definition.code,
        source_definition_revision=1,
        title=definition.title,
        is_required=True,
        allowed_formats='["pdf"]',
        max_file_size_bytes=1000,
        max_active_file_count=1,
        sort_order=0,
    )
    db.session.add(case_req)
    db.session.flush()
    file = CaseDocumentFile(
        operational_organization_id=shipment.organization_id,
        shipment_request_id=shipment.shipment_request_id,
        case_requirement_id=case_req.id,
        is_miscellaneous=False,
        original_filename=f"v{version}.pdf",
        safe_download_filename=f"v{version}.pdf",
        storage_key=f"mdpm/{version}",
        canonical_extension="pdf",
        detected_mime_type="application/pdf",
        file_size_bytes=10,
        sha256_hash="a" * 64,
        version_number=version,
        status="active",
    )
    db.session.add(file)
    db.session.commit()
    return file


def test_missing_and_unapproved_block_then_approval_allows(execution_app):
    with execution_app.app_context():
        shipment, milestone, requirement, definition = _seed(execution_app)
        assert (
            docs.transition_readiness(shipment, milestone, "READY")[
                "blocking_requirements"
            ][0]["code"]
            == "DOC_ARTIFACT_MISSING"
        )
        artifact = _artifact(shipment, definition)
        docs.associate(
            shipment.public_id,
            requirement.public_id,
            {
                "artifact_public_id": artifact.public_id,
                "expected_requirement_version": 1,
            },
            actor(execution_app),
        )
        assert (
            docs.transition_readiness(shipment, milestone, "READY")[
                "blocking_requirements"
            ][0]["code"]
            == "DOC_APPROVAL_REQUIRED"
        )
        docs.assess(
            shipment.public_id,
            requirement.public_id,
            {"decision": "APPROVED"},
            actor(execution_app),
        )
        assert docs.transition_readiness(shipment, milestone, "READY")["allowed"]


def test_verification_conditional_replacement_and_single_use_override(execution_app):
    with execution_app.app_context():
        shipment, milestone, requirement, definition = _seed(
            execution_app, level="CONDITIONAL", assessment="VERIFIED"
        )
        assert (
            docs.transition_readiness(shipment, milestone, "READY")[
                "blocking_requirements"
            ][0]["code"]
            == "DOC_REQUIREMENT_UNRESOLVED"
        )
        docs.resolve_applicability(
            shipment.public_id,
            requirement.public_id,
            {
                "decision": "APPLICABLE",
                "reason": "Applies",
                "expected_requirement_version": 1,
            },
            actor(execution_app),
        )
        artifact = _artifact(shipment, definition)
        docs.associate(
            shipment.public_id,
            requirement.public_id,
            {
                "artifact_public_id": artifact.public_id,
                "expected_requirement_version": 2,
            },
            actor(execution_app),
        )
        docs.assess(
            shipment.public_id,
            requirement.public_id,
            {"decision": "APPROVED"},
            actor(execution_app),
        )
        assert (
            docs.transition_readiness(shipment, milestone, "READY")[
                "blocking_requirements"
            ][0]["code"]
            == "DOC_VERIFICATION_REQUIRED"
        )
        override = docs.create_override(
            shipment.public_id,
            requirement.public_id,
            {
                "milestone_public_id": milestone.public_id,
                "target_status": "READY",
                "authority": "Duty manager",
                "reason": "Urgent release",
            },
            actor(execution_app),
        )
        execution.transition(
            shipment.public_id,
            milestone.public_id,
            {"target_status": "READY", "expected_version": milestone.version},
            actor(execution_app),
        )
        assert (
            override["state"] == "ACTIVE"
        )  # returned projection is immutable; durable row is consumed
        from backend.mdpm_models import TransitionOverride

        assert (
            TransitionOverride.query.filter_by(public_id=override["public_id"])
            .one()
            .state
            == "CONSUMED"
        )


def test_eligible_projection_status_and_remove_are_exact_versioned(execution_app):
    with execution_app.app_context():
        shipment, _, requirement, definition = _seed(execution_app)
        artifact = _artifact(shipment, definition)
        eligible = docs.list_eligible_artifacts(
            shipment.public_id, requirement.public_id, actor(execution_app)
        )
        assert eligible == [
            {
                "artifact_public_id": artifact.public_id,
                "filename": "v1.pdf",
                "version": 1,
            }
        ]
        associated = docs.associate(
            shipment.public_id,
            requirement.public_id,
            {
                "artifact_public_id": artifact.public_id,
                "expected_requirement_version": 1,
            },
            actor(execution_app),
        )
        assert associated["readiness_status"] == "PENDING_REVIEW"
        assert associated["artifact"]["version"] == 1
        removed = docs.remove_association(
            shipment.public_id,
            requirement.public_id,
            {"expected_requirement_version": 2},
            actor(execution_app),
        )
        assert removed["artifact"] is None
        assert removed["readiness_status"] == "MISSING"


def test_file_without_proven_tenant_is_not_eligible(execution_app):
    with execution_app.app_context():
        shipment, _, requirement, definition = _seed(execution_app)
        artifact = _artifact(shipment, definition)
        artifact.operational_organization_id = None
        db.session.commit()
        assert (
            docs.list_eligible_artifacts(
                shipment.public_id, requirement.public_id, actor(execution_app)
            )
            == []
        )
        try:
            docs.associate(
                shipment.public_id,
                requirement.public_id,
                {
                    "artifact_public_id": artifact.public_id,
                    "expected_requirement_version": 1,
                },
                actor(execution_app),
            )
        except Exception as exc:
            assert getattr(exc, "code", None) == "ARTIFACT_NOT_ELIGIBLE"
        else:
            raise AssertionError(
                "tenant-ambiguous artifact association must fail closed"
            )


def test_same_request_file_can_satisfy_independent_shipment_requirements(execution_app):
    with execution_app.app_context():
        first, _, first_requirement, definition = _seed(execution_app)
        artifact = _artifact(first, definition)
        quote = ExpertQuote(
            shipment_request_id=first.shipment_request_id,
            amount=2,
            currency="IRR",
            created_by_expert_id=execution_app.config["ctx"]["operator"],
            created_at=datetime.now(timezone.utc),
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=first.organization_id,
        )
        db.session.add(quote)
        db.session.flush()
        second = OperationalShipment(
            organization_id=first.organization_id,
            project_id=first.project_id,
            shipment_request_id=first.shipment_request_id,
            accepted_quote_id=quote.id,
            created_by_user_id=execution_app.config["ctx"]["operator"],
        )
        db.session.add(second)
        db.session.commit()
        second_requirements, _ = docs.materialize(
            second.public_id,
            {"expected_shipment_version": 1},
            actor(execution_app),
        )
        first_projection = docs.associate(
            first.public_id,
            first_requirement.public_id,
            {
                "artifact_public_id": artifact.public_id,
                "expected_requirement_version": 1,
            },
            actor(execution_app),
        )
        second_projection = docs.associate(
            second.public_id,
            second_requirements[0].public_id,
            {
                "artifact_public_id": artifact.public_id,
                "expected_requirement_version": 1,
            },
            actor(execution_app),
        )
        assert first_projection["artifact"]["artifact_public_id"] == artifact.public_id
        assert second_projection["artifact"]["artifact_public_id"] == artifact.public_id
        assert first_requirement.public_id != second_requirements[0].public_id
