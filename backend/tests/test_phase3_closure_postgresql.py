"""Owned PostgreSQL 18 migration, raw integrity and source/close serialization."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from time import monotonic, sleep
from uuid import uuid4
import os
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from alembic import command
from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import ExpertUser, DocumentDefinition, CaseDocumentFile
from backend.mdpm_models import OperationalDocumentRequirement, ArtifactAssociation, DocumentAssessment
from backend.operational_models import OperationalShipment, OperationalMembership, OperationalWorkItem, utcnow
from backend.closure_models import ClosureDecision
from backend.services import closure_service as svc
from backend.services.operational_service import OperationalError
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime

URL = os.environ.get("P3_CLOSURE_POSTGRES_URL", "")
HEAD = "20261010_phase3_closure"
PREVIOUS = "20261009_phase3_route_time"
pytestmark = pytest.mark.skipif(not URL, reason="requires explicit owned P3_CLOSURE_POSTGRES_URL")


def values(shipment, kind="NORMAL"):
    assessment = svc.assess(shipment)
    return {"kind":kind, "reason":"Synthetic exception" if kind=="EXCEPTIONAL" else None,
        "expected_shipment_version":shipment.version, "policy_version_public_id":assessment["policy"]["public_id"],
        "assessment_fingerprint":assessment["fingerprint"]}


def blocked(engine, pid, ready):
    assert ready.wait(5)
    until = monotonic()+8
    while monotonic()<until:
        with engine.connect() as connection:
            if connection.execute(sa.text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid":pid[0]}).scalar():
                return
        sleep(.03)
    raise AssertionError("Expected a real PostgreSQL row-lock waiter")


def test_postgresql18_closure_upgrade_preservation_history_and_both_race_orders():
    parsed = make_url(URL)
    assert parsed.get_backend_name()=="postgresql" and parsed.host in {"localhost","127.0.0.1"}
    assert parsed.database.startswith("forwarder_integrated_cert_p3_12_closure_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar()) < 190000
    config = alembic_config(URL)
    command.upgrade(config, PREVIOUS)
    app = create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":URL,"SECRET_KEY":"p312-owned-pg"}, skip_startup=True)
    with app.app_context():
        ids = _seed_runtime(app)
        shipment = OperationalShipment.query.filter_by(public_id=ids["shipment"]).one()
        shipment.lifecycle_status = "completed"
        admin = ExpertUser(username="p312-admin",password_hash="unused",full_name="Synthetic closure admin",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
        db.session.add(admin);db.session.flush()
        db.session.add(OperationalMembership(user_id=admin.id,organization_id=shipment.organization_id,permissions=["operational_shipment.read"]))
        db.session.commit()
        ids.update(shipment_id=shipment.id,org=shipment.organization_id,admin=admin.id)
    def legacy():
        with engine.connect() as connection:
            return connection.execute(sa.text("SELECT id, lifecycle_status, version, primary_responsible_expert_id FROM operational_shipment ORDER BY id")).all()
    before = legacy()
    command.upgrade(config, HEAD)
    assert legacy()==before
    command.downgrade(config, PREVIOUS)
    assert legacy()==before
    command.upgrade(config, HEAD)
    owner = {"id":ids["owner"],"role":"expert"}
    admin_user = {"id":ids["admin"],"role":"admin"}
    with app.app_context():
        version,_ = svc.save_policy(admin_user, {"expected_version":0,"effective_from":(utcnow()-timedelta(days=1)).isoformat(),
            "criteria":[{"scope":"GENERAL","code":"NO_OPEN_FOLLOW_UPS","mandatory":True}]}, str(uuid4()))
        db.session.commit(); version_id=version.id
        shipment = db.session.get(OperationalShipment,ids["shipment_id"])
        stale = values(shipment)
    # A new source row (absent during the earlier read) must fence closing.
    with engine.connect() as writer:
        transaction = writer.begin()
        item = writer.execute(OperationalWorkItem.__table__.insert().values(organization_id=ids["org"],
            operational_shipment_id=ids["shipment_id"],work_type="FOLLOW_UP",action_context_type="SHIPMENT",
            due_at=utcnow(),reason="Synthetic concurrent work",assignee_user_id=ids["owner"])).inserted_primary_key[0]
        ready=Event();pid=[]
        def attempt():
            with app.app_context():
                pid.append(db.session.execute(sa.text("SELECT pg_backend_pid()")).scalar());ready.set()
                try:
                    svc.close(ids["shipment"],owner,stale,str(uuid4()));db.session.commit()
                    return "unexpected close"
                except OperationalError as exc:
                    db.session.rollback();return exc.code
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(attempt)
            try: blocked(engine,pid,ready)
            finally: transaction.commit()
            assert future.result(timeout=10)=="STALE_CLOSURE_ASSESSMENT"
    # Exact artifact status is also a closure source and must use the same fence.
    with app.app_context():
        definition=DocumentDefinition(code="P312_SYNTHETIC",title="Synthetic requirement",allowed_formats=["pdf"],max_file_size_bytes=1024)
        db.session.add(definition);db.session.flush()
        requirement=OperationalDocumentRequirement(organization_id=ids["org"],operational_shipment_id=ids["shipment_id"],
            document_definition_id=definition.id,requirement_level="REQUIRED",applicability_state="APPLICABLE",
            created_by_user_id=ids["owner"])
        artifact=CaseDocumentFile(operational_organization_id=ids["org"],owner_type="SHIPMENT",operational_shipment_id=ids["shipment_id"],
            is_miscellaneous=True,custom_title="Synthetic exact evidence",original_filename="synthetic.pdf",safe_download_filename="synthetic.pdf",
            storage_key="synthetic-p312-never-downloaded",canonical_extension="pdf",detected_mime_type="application/pdf",
            file_size_bytes=20,sha256_hash="0"*64,version_number=1,uploaded_by=ids["owner"])
        db.session.add_all([requirement,artifact]);db.session.flush()
        association=ArtifactAssociation(organization_id=ids["org"],requirement_id=requirement.id,document_file_id=artifact.id,
            artifact_version=1,associated_by_user_id=ids["owner"])
        db.session.add(association);db.session.flush()
        db.session.add(DocumentAssessment(organization_id=ids["org"],association_id=association.id,decision="APPROVED",actor_user_id=ids["admin"]))
        db.session.commit();artifact_id=artifact.id
        stale=values(db.session.get(OperationalShipment,ids["shipment_id"]))
    with engine.connect() as writer:
        transaction=writer.begin()
        writer.execute(sa.text("UPDATE case_document_file SET status='deleted', deleted_at=CURRENT_TIMESTAMP, deleted_by=:actor, deletion_reason='Synthetic correction' WHERE id=:id"),{"actor":ids["owner"],"id":artifact_id})
        ready=Event();pid=[]
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(attempt)
            try:blocked(engine,pid,ready)
            finally:transaction.commit()
            assert future.result(timeout=10)=="STALE_CLOSURE_ASSESSMENT"
    with app.app_context():
        shipment=db.session.get(OperationalShipment,ids["shipment_id"])
        assert shipment.lifecycle_status=="completed" and ClosureDecision.query.count()==0
        current=values(shipment,"EXCEPTIONAL")
        decision,_=svc.close(ids["shipment"],admin_user,current,"close-p312-once")
        frozen=decision.assessment
        # Closing holds the same fence while a writer tries to resolve its item.
        ready=Event();pid=[]
        def repair():
            with engine.begin() as connection:
                pid.append(connection.execute(sa.text("SELECT pg_backend_pid()")).scalar());ready.set()
                connection.execute(sa.text("UPDATE operational_work_item SET status='resolved', version=version+1 WHERE id=:id"),{"id":item})
            return "repaired"
        duplicate_ready=Event();duplicate_pid=[]
        def duplicate_close():
            with app.app_context():
                duplicate_pid.append(db.session.execute(sa.text("SELECT pg_backend_pid()")).scalar());duplicate_ready.set()
                replay, created = svc.close(ids["shipment"],admin_user,current,"close-p312-once")
                db.session.commit()
                return replay.public_id, created
        with ThreadPoolExecutor(max_workers=2) as pool:
            future=pool.submit(repair)
            duplicate=pool.submit(duplicate_close)
            try:
                blocked(engine,pid,ready)
                blocked(engine,duplicate_pid,duplicate_ready)
            finally: db.session.commit()
            assert future.result(timeout=10)=="repaired"
            assert duplicate.result(timeout=10)==(decision.public_id, False)
        db.session.expire_all()
        decision=ClosureDecision.query.one()
        assert decision.assessment==frozen and decision.missing_items[0]["code"]=="NO_OPEN_FOLLOW_UPS"
        assert decision.assessment["source_facts"]["documents"][0]["readiness_status"]=="MISSING"
        assert "source_facts" not in svc.project_decision(decision)["assessment"]
        assert db.session.get(OperationalShipment,ids["shipment_id"]).lifecycle_status=="closed"
        replay,created=svc.close(ids["shipment"],admin_user,current,"close-p312-once")
        assert not created and replay.id==decision.id
        db.session.commit()
        with pytest.raises(OperationalError) as denied:
            svc.close(ids["shipment"],admin_user,current,"second-independent-close")
        assert denied.value.code=="CLOSURE_PREDECESSOR"
        db.session.rollback()
    for sql in (
        "UPDATE operational_shipment SET lifecycle_status='completed'",
        "UPDATE shipment_closure_decision SET reason='rewritten'",
        "DELETE FROM shipment_closure_decision",
        "UPDATE closure_policy_version SET effective_from=clock_timestamp()",
        "DELETE FROM closure_policy_criterion",
        f"INSERT INTO closure_policy_criterion(public_id,organization_id,policy_version_id,scope,code,mandatory) VALUES ('{uuid4()}',{ids['org']},{version_id},'road','NO_OPEN_EXCEPTIONS',true)",
    ):
        with pytest.raises(sa.exc.DBAPIError),engine.begin() as connection: connection.execute(sa.text(sql))
    with pytest.raises(RuntimeError,match="evidence exists"): command.downgrade(config,PREVIOUS)
    assert legacy()[0][1]=="closed"
    engine.dispose()
