"""Seed the disposable MDPM-1 browser/race validation environment."""
from __future__ import annotations

import json
import os
from pathlib import Path

from backend import create_app
from backend.extensions import db
from backend.models import CaseDocumentFile, CaseDocumentRequirement, Customer, DocumentDefinition, ExpertUser
from backend.operational_models import OperationalOrganization, OperationalShipment, Project
from backend.project_configuration_models import MilestoneType, ProjectDocumentRequirement, ProjectMilestoneDefinition
from backend.services import document_readiness_service as docs
from backend.services import operational_execution_service as execution


def main() -> int:
    if os.getenv("APP_ENV") != "uat" or "mdpm_" not in os.getenv("DATABASE_URL", ""):
        raise RuntimeError("Refusing non-disposable MDPM seed target")
    app = create_app(skip_startup=True)
    with app.app_context():
        operator = ExpertUser.query.filter_by(username="phase1b_uat_admin").one()
        org = OperationalOrganization.query.filter_by(name="[PHASE1B-UAT] Organization A").one()
        shipment = OperationalShipment.query.filter_by(organization_id=org.id).order_by(OperationalShipment.id).first()
        customer = Customer.query.filter_by(first_name="MDPM", last_name="Validation").one_or_none()
        if customer is None:
            customer = Customer(first_name="MDPM", last_name="Validation")
            db.session.add(customer); db.session.flush()
        project = Project.query.filter_by(tracking_code="mdpm-validation-20260807-2215").one_or_none()
        if project is None:
            project = Project(organization_id=org.id, primary_customer_id=customer.id, project_code="MDPM-UAT",
                              tracking_code="mdpm-validation-20260807-2215", created_by_user_id=operator.id)
            db.session.add(project); db.session.flush()
        shipment.project_id = project.id
        milestone_type = MilestoneType.query.filter_by(immutable_code="MDPM_GATE").one_or_none()
        if milestone_type is None:
            milestone_type = MilestoneType(immutable_code="MDPM_GATE", fa_name="دروازه اسناد", en_name="Document gate",
                                           display_order=1, created_by=operator.id, updated_by=operator.id)
            db.session.add(milestone_type); db.session.flush()
            db.session.add(ProjectMilestoneDefinition(project_id=project.id, milestone_type_id=milestone_type.id,
                sequence=1, is_required=True, target_duration_value=1, warning_duration_value=2,
                duration_unit="HOUR", created_by=operator.id, updated_by=operator.id))
        definitions = []
        specs = (("MDPM-APPROVAL", "Approval document", "REQUIRED", "APPROVED"),
                 ("MDPM-VERIFY", "Verification document", "REQUIRED", "VERIFIED"),
                 ("MDPM-COND", "Conditional document", "CONDITIONAL", "APPROVED"))
        for order, (code, title, level, assessment) in enumerate(specs, 1):
            definition = DocumentDefinition.query.filter_by(code=code).one_or_none()
            if definition is None:
                definition = DocumentDefinition(code=code, title=title, is_required=True, allowed_formats='["pdf"]',
                    max_file_size_bytes=1000000, max_active_file_count=5, applicability_scope="all")
                db.session.add(definition); db.session.flush()
                db.session.add(ProjectDocumentRequirement(project_id=project.id, document_definition_id=definition.id,
                    requirement_level=level, required_assessment_level=assessment, target_milestone_type_id=milestone_type.id,
                    target_status="READY", display_order=order, created_by=operator.id, updated_by=operator.id))
            definitions.append(definition)
        db.session.commit()
        actor = {"id": operator.id, "role": "admin"}
        milestones, _ = execution.initialize(shipment.public_id, {"expected_shipment_version": shipment.version}, actor)
        shipment = OperationalShipment.query.filter_by(public_id=shipment.public_id).one()
        requirements, _ = docs.materialize(shipment.public_id, {"expected_shipment_version": shipment.version}, actor)
        artifacts = []
        for definition in definitions:
            case_req = CaseDocumentRequirement(shipment_request_id=shipment.shipment_request_id,
                source_definition_id=definition.id, source_definition_code=definition.code, source_definition_revision=1,
                title=definition.title, is_required=True, allowed_formats='["pdf"]', max_file_size_bytes=1000000,
                max_active_file_count=5, sort_order=0)
            db.session.add(case_req); db.session.flush()
            for version in (1, 2):
                artifact = CaseDocumentFile(shipment_request_id=shipment.shipment_request_id, case_requirement_id=case_req.id,
                    is_miscellaneous=False, original_filename=f"{definition.code.lower()}-v{version}.pdf",
                    safe_download_filename=f"{definition.code.lower()}-v{version}.pdf", storage_key=f"mdpm-validation/{definition.code}/{version}",
                    canonical_extension="pdf", detected_mime_type="application/pdf", file_size_bytes=100,
                    sha256_hash=(str(version) * 64), version_number=version, status="active")
                db.session.add(artifact); db.session.flush(); artifacts.append(artifact)
        db.session.commit()
        payload = {"seed_lineage":"phase1b_uat + mdpm_validation_seed:v1", "organization":org.public_id,
                   "username":"phase1b_uat_admin", "shipment_numeric_id":shipment.id, "shipment_public_id":shipment.public_id,
                   "milestone_public_id":milestones[0].public_id,
                   "requirements":[{"public_id":r.public_id,"title":r.definition.title,"version":r.version} for r in requirements],
                   "artifacts":[{"public_id":a.public_id,"filename":a.original_filename} for a in artifacts]}
        output = Path("instance/mdpm_validation_20260807_2215/seed-lineage.json")
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
