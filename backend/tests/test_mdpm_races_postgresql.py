"""Dedicated real-PostgreSQL MDPM-1 transition race evidence."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from threading import Barrier
import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.mdpm_models import (ArtifactAssociation, DocumentAssessment,
    DocumentReadinessAudit, OperationalDocumentRequirement,
    RequirementApplicabilityDecision, TransitionOverride)
from backend.models import CaseDocumentFile, ExpertUser
from backend.operational_models import (Milestone, MilestoneEvent,
    OperationalIdempotency, OperationalMembership, OperationalShipment)
from backend.services import document_readiness_service as docs
from backend.services import operational_execution_service as execution
from backend.services.operational_service import OperationalError


def _base_url():
    value = os.environ.get("MDPM_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit disposable MDPM PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert "mdpm_" in (parsed.database or "")
    return value


@pytest.fixture()
def race_app():
    base = make_url(_base_url())
    clone_name = f"forwarder_phase1b_uat_mdpm_race_{uuid.uuid4().hex[:10]}"
    admin = base.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{clone_name}" TEMPLATE "{base.database}"'))
    engine.dispose()
    clone = base.set(database=clone_name)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": clone.render_as_string(hide_password=False),
                      "SECRET_KEY": "mdpm-race"}, skip_startup=True)
    with app.app_context():
        db.session.query(DocumentAssessment).delete()
        db.session.query(TransitionOverride).delete()
        db.session.query(ArtifactAssociation).delete()
        db.session.query(RequirementApplicabilityDecision).delete()
        db.session.query(DocumentReadinessAudit).delete()
        db.session.query(OperationalIdempotency).filter_by(operation="execution_milestone_transition").delete()
        shipment = OperationalShipment.query.filter_by(project_id=1).first() or OperationalShipment.query.first()
        milestone = Milestone.query.filter_by(operational_shipment_id=shipment.id, milestone_type="MDPM_GATE").one()
        ready_event_baseline = MilestoneEvent.query.filter_by(
            milestone_id=milestone.id, event_type="READY"
        ).count()
        requirements = OperationalDocumentRequirement.query.filter_by(operational_shipment_id=shipment.id).all()
        for req in requirements:
            req.version = 1
            req.applicability_state = "UNRESOLVED" if req.requirement_level == "CONDITIONAL" else "APPLICABLE"
        milestone.lifecycle_status = "PENDING"; milestone.version = 1
        db.session.commit()
        operator = ExpertUser.query.filter_by(username="phase1b_uat_admin").one()
        app.config["race"] = {"shipment": shipment.public_id, "milestone": milestone.public_id,
            "ready_event_baseline": ready_event_baseline,
            "actor": {"id": operator.id, "role": "admin"}}
    yield app
    with app.app_context(): db.session.remove()
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name"), {"name": clone_name})
        conn.execute(text(f'DROP DATABASE "{clone_name}"'))
    engine.dispose()


def _ctx(app): return app.config["race"]


def _req(app, code):
    return db.session.scalar(select(OperationalDocumentRequirement).join(OperationalDocumentRequirement.definition).where(
        OperationalDocumentRequirement.operational_shipment_id == OperationalShipment.query.filter_by(public_id=_ctx(app)["shipment"]).one().id,
        text("document_definition.code = :code")).params(code=code))


def _artifact(code, version):
    return CaseDocumentFile.query.filter(CaseDocumentFile.original_filename == f"{code.lower()}-v{version}.pdf").one()


def _run_pair(app, left, right):
    barrier = Barrier(2)
    def run(fn):
        with app.app_context():
            barrier.wait()
            try: return ("ok", fn())
            except OperationalError as exc:
                db.session.rollback(); return (exc.code, None)
            finally: db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        return [f.result(timeout=20) for f in (pool.submit(run, left), pool.submit(run, right))]


def _transition(app, version=1, key=None, target="READY", reason=None):
    c = _ctx(app)
    return execution.transition(c["shipment"], c["milestone"],
        {"target_status": target, "expected_version": version, "reason": reason,
         "_idempotency_key": key or str(uuid.uuid4())}, c["actor"])


def _associate(app, code, version, expected):
    c = _ctx(app); req = _req(app, code); artifact = _artifact(code, version)
    return docs.associate(c["shipment"], req.public_id,
        {"artifact_public_id": artifact.public_id, "expected_requirement_version": expected}, c["actor"])


def _assess(app, code, decision, expected, reason=None):
    c = _ctx(app); req = _req(app, code)
    return docs.assess(c["shipment"], req.public_id,
        {"decision": decision, "reason": reason, "expected_requirement_version": expected}, c["actor"])


def _make_ready(app):
    _associate(app, "MDPM-APPROVAL", 1, 1); _assess(app, "MDPM-APPROVAL", "APPROVED", 2)
    _associate(app, "MDPM-VERIFY", 1, 1); _assess(app, "MDPM-VERIFY", "VERIFIED", 2)
    req = _req(app, "MDPM-COND"); c = _ctx(app)
    docs.resolve_applicability(c["shipment"], req.public_id,
        {"decision":"NOT_APPLICABLE", "reason":"race setup", "expected_requirement_version":1}, c["actor"])


def test_approval_vs_transition(race_app):
    with race_app.app_context(): _associate(race_app, "MDPM-APPROVAL", 1, 1)
    results = _run_pair(race_app,
        lambda: _assess(race_app, "MDPM-APPROVAL", "APPROVED", 2),
        lambda: _transition(race_app))
    assert {r[0] for r in results} <= {"ok", "TRANSITION_READINESS_BLOCKED"}


def test_replacement_vs_transition_drops_stale_approval(race_app):
    with race_app.app_context():
        _associate(race_app, "MDPM-APPROVAL", 1, 1); _assess(race_app, "MDPM-APPROVAL", "APPROVED", 2)
    _run_pair(race_app, lambda: _associate(race_app, "MDPM-APPROVAL", 2, 3), lambda: _transition(race_app))
    with race_app.app_context():
        c=_ctx(race_app); m=Milestone.query.filter_by(public_id=c["milestone"]).one(); s=OperationalShipment.query.filter_by(public_id=c["shipment"]).one()
        assert docs.transition_readiness(s, m, "READY")["blocking_requirements"][0]["code"] == "DOC_APPROVAL_REQUIRED"


def test_rejection_vs_transition(race_app):
    with race_app.app_context(): _associate(race_app, "MDPM-APPROVAL", 1, 1)
    results=_run_pair(race_app, lambda:_assess(race_app,"MDPM-APPROVAL","REJECTED",2,"race"), lambda:_transition(race_app))
    assert {r[0] for r in results} <= {"ok", "TRANSITION_READINESS_BLOCKED"}


def test_upload_association_vs_transition(race_app):
    results=_run_pair(race_app, lambda:_associate(race_app,"MDPM-APPROVAL",1,1), lambda:_transition(race_app))
    assert "TRANSITION_READINESS_BLOCKED" in {r[0] for r in results}


def test_conditional_resolution_vs_transition(race_app):
    def resolve():
        c=_ctx(race_app); req=_req(race_app,"MDPM-COND")
        return docs.resolve_applicability(c["shipment"],req.public_id,{"decision":"NOT_APPLICABLE","reason":"race","expected_requirement_version":1},c["actor"])
    results=_run_pair(race_app, resolve, lambda:_transition(race_app))
    assert {r[0] for r in results} <= {"ok", "TRANSITION_READINESS_BLOCKED"}


def test_override_grant_vs_transition(race_app):
    def grant():
        c=_ctx(race_app); req=_req(race_app,"MDPM-APPROVAL")
        return docs.create_override(c["shipment"],req.public_id,{"milestone_public_id":c["milestone"],"target_status":"READY","authority":"race","reason":"race"},c["actor"])
    results=_run_pair(race_app, grant, lambda:_transition(race_app))
    assert {r[0] for r in results} <= {"ok", "TRANSITION_READINESS_BLOCKED"}


def test_override_revoke_vs_transition_and_single_consumption(race_app):
    with race_app.app_context():
        c=_ctx(race_app); req=_req(race_app,"MDPM-APPROVAL")
        override=docs.create_override(c["shipment"],req.public_id,{"milestone_public_id":c["milestone"],"target_status":"READY","authority":"race","reason":"race"},c["actor"])
    results=_run_pair(race_app, lambda:docs.revoke_override(_ctx(race_app)["shipment"],override["public_id"],_ctx(race_app)["actor"]), lambda:_transition(race_app))
    with race_app.app_context():
        row=TransitionOverride.query.filter_by(public_id=override["public_id"]).one()
        assert row.state in {"REVOKED","CONSUMED"}
        assert [r[0] for r in results].count("ok") == 1


def test_two_simultaneous_transition_attempts(race_app):
    with race_app.app_context(): _make_ready(race_app)
    results=_run_pair(race_app, lambda:_transition(race_app,key="transition-a"), lambda:_transition(race_app,key="transition-b"))
    assert [r[0] for r in results].count("ok") == 1
    assert "STALE_AGGREGATE_VERSION" in {r[0] for r in results}


def test_two_simultaneous_assessments(race_app):
    with race_app.app_context(): _associate(race_app,"MDPM-APPROVAL",1,1)
    results=_run_pair(race_app, lambda:_assess(race_app,"MDPM-APPROVAL","APPROVED",2), lambda:_assess(race_app,"MDPM-APPROVAL","REJECTED",2,"race"))
    assert [r[0] for r in results].count("ok") == 1
    assert "STALE_REQUIREMENT_VERSION" in {r[0] for r in results}


def test_stale_requirement_version(race_app):
    with race_app.app_context():
        _associate(race_app,"MDPM-APPROVAL",1,1)
        with pytest.raises(OperationalError, match="Requirement was changed") as exc: _associate(race_app,"MDPM-APPROVAL",2,1)
        assert exc.value.code == "STALE_REQUIREMENT_VERSION"


def test_stale_milestone_version_and_organization_isolation(race_app):
    with race_app.app_context():
        with pytest.raises(OperationalError) as exc: _transition(race_app,version=0)
        assert exc.value.code == "STALE_AGGREGATE_VERSION"
        outsider=ExpertUser.query.filter_by(username="phase1b_uat_org_b_admin").one()
        c=_ctx(race_app)
        with pytest.raises(OperationalError) as isolated: docs.list_requirements(c["shipment"],{"id":outsider.id,"role":"admin"})
        assert isolated.value.code == "RESOURCE_NOT_FOUND"


def test_same_idempotency_key_same_payload(race_app):
    with race_app.app_context(): _make_ready(race_app)
    results=_run_pair(race_app, lambda:_transition(race_app,key="same-command"), lambda:_transition(race_app,key="same-command"))
    assert [r[0] for r in results].count("ok") == 2
    with race_app.app_context():
        assert OperationalIdempotency.query.filter_by(operation="execution_milestone_transition",idempotency_key="same-command").count() == 1
        assert MilestoneEvent.query.filter_by(milestone_id=Milestone.query.filter_by(public_id=_ctx(race_app)["milestone"]).one().id,event_type="READY").count() == _ctx(race_app)["ready_event_baseline"] + 1


def test_same_idempotency_key_different_payload(race_app):
    with race_app.app_context(): _make_ready(race_app)
    results=_run_pair(race_app, lambda:_transition(race_app,key="conflict-command"), lambda:_transition(race_app,key="conflict-command",reason="different payload"))
    assert [r[0] for r in results].count("ok") == 1
    assert "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD" in {r[0] for r in results}
