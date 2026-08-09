"""Candidate-bound, deterministic Integrated Certification Bootstrap (PR-D03)."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import bcrypt
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import create_app
from backend.extensions import db
from backend.economics_models import EconomicLine, EconomicObservation
from backend.mdpm_models import OperationalDocumentRequirement
from backend.models import (
    CaseDocumentFile, CaseDocumentRequirement, Customer, DocumentDefinition,
    ExpertQuote, ExpertUser, Province, ServiceType, ShipmentRequest,
)
from backend.oip_models import OipSituation, OipThresholdPolicy
from backend.operational_models import (
    CanonicalLocation, Milestone, OperationalMembership, OperationalOrganization,
    OperationalShipment, Project,
)
from backend.project_configuration_models import (
    MilestoneType, ProjectDocumentRequirement, ProjectMilestoneDefinition,
    ProjectService,
)
from backend.services import (
    customer_gamification_service as acceptance,
    document_readiness_service as mdpm,
    economics_service as economics,
    oip_service as oip,
    operational_execution_service as execution,
    operational_service as operations,
    quote_service,
    shipment_service,
)

ORG_NAME = "[CERTIFICATION] CERTIFICATION_ORG"
PREFIX = "certification_"
NOW = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)
PERMISSIONS = [
    "operational_shipment.read", "operational_shipment.create", "work_item.read",
    "work_item.manage", "route_plan.read", "operational_execution.read",
    "operational_execution.manage", "document_readiness.read",
    "document_readiness.manage", "document_readiness.assess",
    "document_readiness.verify", "oip.read", "oip.manage", "oip.reconcile",
    "economics.revenue.view", "economics.cost.view", "economics.margin.view",
    "economics.estimate.create", "economics.commitment.create",
    "economics.actual.create", "economics.observation.correct",
    "economics.fx.approve",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate() -> dict:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(["git", "show", "-s", "--format=%T", "HEAD"], cwd=ROOT, text=True).strip()
    migrations = sorted((ROOT / "backend/migrations/versions").glob("*.py"))
    return {
        "commit": commit, "tree": tree,
        "openapi_sha256": sha256(ROOT / "docs/openapi/openapi.yaml"),
        "migration_hashes": {p.name: sha256(p) for p in migrations},
    }


def guard(app) -> None:
    env = os.getenv("APP_ENV", "").lower()
    url = make_url(str(db.engine.url))
    if env not in {"test", "uat"} or app.config.get("ENV") == "production":
        raise RuntimeError("Refusing non-test/UAT certification target")
    if url.get_backend_name() != "postgresql" or (url.host or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Certification requires loopback PostgreSQL")
    if not (url.database or "").lower().startswith("forwarder_integrated_cert_"):
        raise RuntimeError("Certification database name is not allow-listed")


def one(model, defaults=None, **identity):
    row = db.session.scalar(select(model).filter_by(**identity))
    if row is None:
        row = model(**identity, **(defaults or {})); db.session.add(row); db.session.flush()
    return row


def identities(password: str):
    org = one(OperationalOrganization, name=ORG_NAME)
    specs = {
        "admin": ("admin", PERMISSIONS),
        "commercial": ("manager", ["operational_shipment.read", "operational_shipment.create", "economics.revenue.view", "economics.commitment.create"]),
        "operations": ("manager", [p for p in PERMISSIONS if not p.startswith("economics.")]),
        "document_reviewer": ("manager", ["operational_shipment.read", "document_readiness.read", "document_readiness.manage", "document_readiness.assess", "document_readiness.verify"]),
        "control_tower": ("manager", ["operational_shipment.read", "oip.read", "oip.manage", "oip.reconcile"]),
        "economics": ("manager", [p for p in PERMISSIONS if p.startswith("economics.")] + ["operational_shipment.read"]),
    }
    users = {}
    for name, (role, permissions) in specs.items():
        user = ExpertUser.query.filter_by(username=PREFIX + name).one_or_none()
        if user is None:
            user = ExpertUser(username=PREFIX + name, full_name=f"[CERTIFICATION] {name.replace('_',' ').title()}", role=role, is_active=True, password_hash="pending")
            db.session.add(user); db.session.flush()
        user.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        membership = one(OperationalMembership, organization_id=org.id, user_id=user.id)
        membership.permissions = permissions; membership.is_active = True
        users[name] = user
    db.session.commit()
    return org, users


def reference_and_project(org, users):
    admin = users["admin"]
    origin = one(Province, {"name_fa": "[CERTIFICATION] Origin"}, code="CERTO")
    destination = one(Province, {"name_fa": "[CERTIFICATION] Destination"}, code="CERTD")
    for province in (origin, destination):
        one(CanonicalLocation, {"location_type":"province", "display_name":province.name_fa, "country_code":"TST", "verification_state":"verified"}, source_type="province", source_id=province.id)
    service = one(ServiceType, {"fa_name":"Certification Freight", "en_name":"Certification Freight", "is_active":True}, immutable_code="CERT_FREIGHT")
    milestone_type = one(MilestoneType, {"fa_name":"دروازه گواهی", "en_name":"Certification gate", "display_order":1, "created_by":admin.id, "updated_by":admin.id}, immutable_code="CERT_GATE")
    definition = one(DocumentDefinition, {"title":"Certification approval", "is_required":True, "allowed_formats":'["pdf"]', "max_file_size_bytes":1000000, "max_active_file_count":3, "applicability_scope":"all", "created_by":admin.id, "updated_by":admin.id}, code="CERT-APPROVAL")
    customer = Customer.query.filter_by(first_name="Certification", last_name="Customer").one_or_none()
    if customer is None:
        customer=Customer(first_name="Certification",last_name="Customer");db.session.add(customer);db.session.flush()
    project = Project.query.filter_by(organization_id=org.id, project_code="CERT-GOLDEN-PATH").one_or_none()
    if project is None:
        project=Project(organization_id=org.id,primary_customer_id=customer.id,project_code="CERT-GOLDEN-PATH",tracking_code="certification-golden-path",created_by_user_id=admin.id)
        db.session.add(project);db.session.flush()
    one(ProjectService,{"is_primary":True,"is_required":True,"display_order":1,"created_by":admin.id,"updated_by":admin.id},project_id=project.id,service_type_id=service.id)
    one(ProjectMilestoneDefinition,{"sequence":1,"is_required":True,"target_duration_value":1,"warning_duration_value":2,"duration_unit":"HOUR","created_by":admin.id,"updated_by":admin.id},project_id=project.id,milestone_type_id=milestone_type.id)
    one(ProjectDocumentRequirement,{"requirement_level":"REQUIRED","required_assessment_level":"APPROVED","target_milestone_type_id":milestone_type.id,"target_status":"READY","display_order":1,"created_by":admin.id,"updated_by":admin.id},project_id=project.id,document_definition_id=definition.id)
    one(OipThresholdPolicy,{"scope_type":"ENTERPRISE","scope_public_id":"ENTERPRISE","value":1,"unit":"HOUR","effective_from":NOW-timedelta(days=30),"authority":"PR-D03 synthetic certification policy","source":"integrated certification bootstrap","created_by_user_id":admin.id,"updated_by_user_id":admin.id},organization_id=org.id,signal_type="NEXT_MILESTONE_OVERDUE",version=1)
    db.session.commit(); return origin,destination,service,definition,project


def commercial_and_shipment(org, users, origin, destination, project):
    request = ShipmentRequest.query.filter_by(contact_phone="09000000404").one_or_none()
    if request is None:
        request = shipment_service.create_shipment_request({"shipping_type":"domestic","origin_province_id":origin.id,"dest_province_id":destination.id,"contact_phone":"09000000404","customer_first_name":"Synthetic","customer_last_name":"Certification","cargo_description":"Synthetic certification cargo","transport_method":"road"}, "127.0.0.1")
    request.assigned_to=users["commercial"].id; request.project_id=project.id; db.session.commit()
    quote = ExpertQuote.query.filter_by(shipment_request_id=request.id).order_by(ExpertQuote.id).first()
    if quote is None:
        result=quote_service.create_quote_for_request(request.id,{"amount":1200,"currency":"USD","note":"Synthetic certification quote"},{"id":users["commercial"].id,"role":"admin"},"127.0.0.1")
        quote=db.session.get(ExpertQuote,result["quote"]["id"])
    if quote.customer_response is None:
        body,status=acceptance.record_quote_response(request.tracking_code,"accepted","127.0.0.1")
        if status != 200: raise RuntimeError(f"customer acceptance failed: {status} {body}")
        quote=db.session.get(ExpertQuote,quote.id)
    shipment=OperationalShipment.query.filter_by(accepted_quote_id=quote.id).one_or_none()
    if shipment is None:
        shipment,_=operations.create_from_accepted_quote({"accepted_quote_id":quote.id,"origin":{"source_type":"province","source_id":origin.id},"destination":{"source_type":"province","source_id":destination.id},"transport_mode":"road","planned_departure":(NOW-timedelta(days=3)).isoformat(),"planned_arrival":(NOW-timedelta(days=2)).isoformat()},{"id":users["operations"].id},"cert-golden-shipment-v1")
    shipment.project_id=project.id; db.session.commit(); return request,quote,shipment


def documents_and_mdpm(users, definition, request, shipment):
    actor={"id":users["document_reviewer"].id}
    execution_actor={"id":users["operations"].id}
    configured,_=execution.initialize(shipment.public_id,{"expected_shipment_version":shipment.version},execution_actor)
    shipment=db.session.get(OperationalShipment,shipment.id)
    requirements,_=mdpm.materialize(shipment.public_id,{"expected_shipment_version":shipment.version},actor)
    case_req=one(CaseDocumentRequirement,{"source_definition_code":definition.code,"source_definition_revision":definition.revision,"title":definition.title,"is_required":True,"allowed_formats":definition.allowed_formats,"max_file_size_bytes":definition.max_file_size_bytes,"max_active_file_count":definition.max_active_file_count,"sort_order":1,"applied_by":users["document_reviewer"].id},shipment_request_id=request.id,source_definition_id=definition.id)
    artifact=CaseDocumentFile.query.filter_by(case_requirement_id=case_req.id,version_number=1).one_or_none()
    if artifact is None:
        artifact=CaseDocumentFile(shipment_request_id=request.id,case_requirement_id=case_req.id,is_miscellaneous=False,original_filename="synthetic-certification.pdf",safe_download_filename="synthetic-certification.pdf",storage_key=f"integrated-certification/{shipment.public_id}/synthetic-certification.pdf",canonical_extension="pdf",detected_mime_type="application/pdf",file_size_bytes=32,sha256_hash=hashlib.sha256(b"synthetic certification artifact").hexdigest(),version_number=1,status="active",uploaded_by=users["document_reviewer"].id)
        db.session.add(artifact);db.session.commit()
    req=requirements[0] if requirements else db.session.scalar(select(OperationalDocumentRequirement).where(OperationalDocumentRequirement.operational_shipment_id==shipment.id))
    projection=mdpm.list_requirements(shipment.public_id,actor)[0]
    if not projection["artifact"]:
        projection=mdpm.associate(shipment.public_id,req.public_id,{"expected_requirement_version":req.version,"artifact_public_id":artifact.public_id,"reason":"Synthetic certification evidence"},actor)
    if projection["artifact"]["assessment"] != "APPROVED":
        projection=mdpm.assess(shipment.public_id,req.public_id,{"expected_requirement_version":projection["version"],"decision":"APPROVED","reason":"Certification review passed"},actor)
    milestone=configured[0]
    milestone=db.session.get(Milestone,milestone.id)
    if milestone.lifecycle_status=="PENDING": execution.transition(shipment.public_id,milestone.public_id,{"expected_version":milestone.version,"target_status":"READY","effective_at":NOW.isoformat(),"_idempotency_key":"cert-mdpm-ready-v1"},execution_actor)
    return artifact,req,milestone


def oip_and_economics(org, users, shipment, service, artifact):
    operations.reconcile_overdue(user_id=users["operations"].id,organization_id=org.id,now=NOW)
    oip.reconcile({"id":users["control_tower"].id},calculation_time=NOW)
    situation=db.session.scalar(select(OipSituation).where(OipSituation.organization_id==org.id,OipSituation.subject_public_id==shipment.public_id).order_by(OipSituation.id))
    if not situation: raise RuntimeError("authoritative OIP reconciliation produced no Situation")
    if situation.status=="OPEN": oip.transition(situation.public_id,"acknowledge",{"expected_version":situation.version},{"id":users["control_tower"].id})
    user={"id":users["economics"].id}
    if not EconomicLine.query.filter_by(operational_shipment_id=shipment.id).first():
        economics.quote_confirm(shipment.public_id,{"service_public_id":service.public_id,"authority":"accepted customer response","reason":"Materialize accepted commercial intent","idempotency_key":"cert-revenue-commit","evidence":[{"artifact_public_id":artifact.public_id,"artifact_version":1}]},user)
        common={"service_public_id":service.public_id,"effective_at":NOW.isoformat(),"authority":"synthetic certification controller","source_type":"CERTIFICATION_FACT","reason":"Synthetic certification fact","evidence":[{"artifact_public_id":artifact.public_id,"artifact_version":1}]}
        economics.create_line(shipment.public_id,{**common,"side":"REVENUE","stage":"ESTIMATE","money":{"amount":"1300","currency":"USD"},"idempotency_key":"cert-revenue-estimate"},user)
        cost=economics.create_line(shipment.public_id,{**common,"side":"COST","stage":"ESTIMATE","money":{"amount":"700","currency":"USD"},"idempotency_key":"cert-cost-estimate"},user)["line"]
        economics.append_observation(shipment.public_id,cost["public_id"],{**common,"stage":"COMMITMENT","money":{"amount":"750","currency":"USD"},"idempotency_key":"cert-cost-commitment"},user)
        economics.append_observation(shipment.public_id,cost["public_id"],{**common,"stage":"ACTUAL","money":{"amount":"500","currency":"USD"},"idempotency_key":"cert-cost-actual-1"},user)
        economics.append_observation(shipment.public_id,cost["public_id"],{**common,"stage":"ACTUAL","money":{"amount":"100","currency":"USD"},"idempotency_key":"cert-cost-actual-2"},user)
    projection=economics.projection(shipment.public_id,user,"USD")
    line=db.session.scalar(select(EconomicLine).where(EconomicLine.operational_shipment_id==shipment.id).order_by(EconomicLine.id))
    observation=db.session.scalar(select(EconomicObservation).where(EconomicObservation.line_id==line.id).order_by(EconomicObservation.id))
    return situation,line,observation,projection


def run(password: str) -> dict:
    app=create_app({"SQLALCHEMY_DATABASE_URI":os.environ["DATABASE_URL"],"TESTING":True,"SECRET_KEY":"process-only-certification"},skip_startup=True)
    with app.app_context():
        guard(app); binding=candidate()
        binding["migration_head"]=db.session.execute(text("select version_num from alembic_version")).scalar_one()
        org,users=identities(password)
        if OperationalOrganization.query.count()!=1: raise RuntimeError("Certification target must contain exactly one organization")
        origin,destination,service,definition,project=reference_and_project(org,users)
        request,quote,shipment=commercial_and_shipment(org,users,origin,destination,project)
        artifact,requirement,milestone=documents_and_mdpm(users,definition,request,shipment)
        situation,line,observation,projection=oip_and_economics(org,users,shipment,service,artifact)
        return {"schema_version":1,"synthetic_data":True,"candidate":binding,"organization_public_id":org.public_id,"personas":sorted(users),"trace":{"commercial_request":request.tracking_code,"quote":"accepted-quote-"+hashlib.sha256(str(quote.id).encode()).hexdigest()[:16],"project":project.public_id,"operational_shipment":shipment.public_id,"document_artifact":artifact.public_id,"mdpm_requirement":requirement.public_id,"milestone":milestone.public_id,"oip_situation":situation.public_id,"economic_line":line.public_id,"economic_observation":observation.public_id,"fx_binding":None},"derived":{"mdpm_readiness":mdpm.next_readiness(shipment.public_id,{"id":users["document_reviewer"].id}),"oip_status":situation.status,"economic_projection":projection}}


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--confirm",action="store_true");args=parser.parse_args(argv)
    if not args.confirm: raise SystemExit("Refusing write without --confirm")
    password=os.getenv("FORWARDER_CERT_PASSWORD")
    if not password or len(password)<12: raise SystemExit("FORWARDER_CERT_PASSWORD must be a temporary value of at least 12 characters")
    result=run(password);print(json.dumps(result,indent=2,default=str,ensure_ascii=False));return 0


if __name__=="__main__": raise SystemExit(main())
