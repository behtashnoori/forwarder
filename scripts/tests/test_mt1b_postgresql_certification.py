"""MT-1B synthetic certification. Requires an isolated PostgreSQL URL."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

URL = os.environ.get("MT1B_CERT_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="MT1B_CERT_DATABASE_URL is required")

MODULE_PATH = Path(__file__).parents[1] / "mt1a_legacy_ownership_analyzer.py"
SPEC = importlib.util.spec_from_file_location("mt1b_pg_analyzer", MODULE_PATH)
ANALYZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYZER
SPEC.loader.exec_module(ANALYZER)


def _engine():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost", "::1"}
    assert parsed.database.startswith("forwarder_mt1b_cert_")
    return create_engine(URL)


def _decision(entity_id, organization_id, **overrides):
    value = {
        "entity_type": "Customer",
        "entity_id": entity_id,
        "target_organization_id": organization_id,
        "reason": "reviewed synthetic source evidence",
        "operator_identity": "operator-a",
        "reviewer_identity": "reviewer-b",
        "created_at": "2026-08-11T10:00:00Z",
        "decision_version": 1,
        "decision_id": f"decision-Customer-{entity_id}-0001",
        "review_status": "ACTIVE",
    }
    value.update(overrides)
    return value


def test_postgresql_analyzer_scenarios_and_read_only_mutation_rejection():
    engine = _engine()
    ddl = """
    CREATE TABLE operational_organization(id bigint primary key);
    CREATE TABLE customer(id bigint primary key);
    CREATE TABLE shipment_request(id bigint primary key, project_id bigint, customer_id bigint, gamification_customer_id bigint);
    CREATE TABLE project(id bigint primary key, organization_id bigint not null, primary_customer_id bigint);
    CREATE TABLE expert_quote(id bigint primary key, shipment_request_id bigint not null, operational_organization_id bigint);
    CREATE TABLE operational_shipment(id bigint primary key, organization_id bigint not null, project_id bigint, source_type text not null, customer_id bigint, shipment_request_id bigint, accepted_quote_id bigint);
    CREATE TABLE shipment_tracking(id bigint primary key, shipment_request_id bigint not null);
    CREATE TABLE customer_gamification(id bigint primary key);
    CREATE TABLE customer_contact(id bigint primary key, customer_id bigint not null);
    CREATE TABLE opportunity(id bigint primary key, customer_id bigint not null);
    CREATE TABLE activity(id bigint primary key, customer_id bigint, opportunity_id bigint, shipment_request_id bigint);
    CREATE TABLE task(id bigint primary key, customer_id bigint, opportunity_id bigint, shipment_request_id bigint);
    CREATE TABLE customer_workflow_step(id bigint primary key, customer_id bigint not null, shipment_request_id bigint not null);
    CREATE TABLE shipment_transport_unit(id bigint primary key, tracking_id bigint not null);
    CREATE TABLE shipment_transport_unit_update(id bigint primary key, unit_id bigint not null);
    CREATE TABLE shipment_request_log(id bigint primary key, shipment_request_id bigint not null);
    CREATE TABLE expert_console_log(id bigint primary key, shipment_request_id bigint not null);
    CREATE TABLE expert_console_message(id bigint primary key, shipment_request_id bigint not null);
    CREATE TABLE expert_console_notification(id bigint primary key, shipment_request_id bigint not null);
    CREATE TABLE crm_customer_link_audit(id bigint primary key, shipment_request_id bigint not null, old_customer_id bigint, new_customer_id bigint);
    CREATE TABLE assignment_rule(id bigint primary key);
    CREATE TABLE assignment_log(id bigint primary key, shipment_request_id bigint not null, assignment_rule_id bigint);
    CREATE TABLE referral_rule(id bigint primary key);
    CREATE TABLE referral_rule_state(id bigint primary key, rule_id bigint not null);
    CREATE TABLE referral_auto_assign_state(id bigint primary key);
    CREATE TABLE referral_assignment_log(id bigint primary key, request_id bigint not null, rule_id bigint);
    CREATE TABLE case_document_requirement(id bigint primary key, shipment_request_id bigint not null);
    CREATE TABLE case_document_file(id bigint primary key, shipment_request_id bigint not null, case_requirement_id bigint);
    CREATE TABLE document_audit_event(id bigint primary key, shipment_request_id bigint, document_file_id bigint);
    CREATE TABLE report(id bigint primary key);
    CREATE TABLE project_party_relationship(project_id bigint not null, customer_id bigint not null, party_role text not null, primary key(project_id, customer_id, party_role));
    CREATE TABLE operational_artifact_association(id bigint primary key, organization_id bigint not null, document_file_id bigint not null);
    CREATE TABLE economic_evidence_association(id bigint primary key, organization_id bigint not null, document_file_id bigint not null);
    """
    with engine.begin() as connection:
        for table in reversed(
            sorted(set(ANALYZER.ENTITY_TABLE.values()) | {"operational_organization"})
        ):
            connection.execute(text(f"DROP TABLE IF EXISTS {table}"))
        for statement in ddl.split(";"):
            if statement.strip():
                connection.execute(text(statement))
        connection.execute(text("INSERT INTO operational_organization VALUES (1),(2)"))
        connection.execute(text("INSERT INTO customer VALUES (1),(2),(3),(4)"))
        connection.execute(text("INSERT INTO project VALUES (1,1,1),(2,1,3),(3,2,3)"))
        connection.execute(
            text(
                "INSERT INTO shipment_request VALUES (1,1,1,NULL),(2,NULL,NULL,NULL),(3,999,NULL,NULL),(4,2,NULL,NULL),(5,NULL,4,NULL)"
            )
        )
        connection.execute(text("INSERT INTO expert_quote VALUES (1,1,1),(2,4,2)"))
        connection.execute(
            text(
                "INSERT INTO operational_shipment VALUES (1,1,1,'accepted_quote',1,1,1)"
            )
        )
        connection.execute(text("INSERT INTO shipment_tracking VALUES (1,1)"))
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text("SET TRANSACTION READ ONLY"))
        assert (
            connection.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        )
        rows = {
            (r["entity_type"], r["entity_id"]): r for r in ANALYZER.analyze(connection)
        }
        assert rows[("ShipmentRequest", 1)]["classification"] == "DETERMINISTIC"  # A/F
        assert rows[("Customer", 4)]["classification"] == "UNRESOLVED"  # B
        assert (
            rows[("ShipmentRequest", 3)]["classification"] == "INVALID_LINEAGE"
        )  # C/K
        assert rows[("ShipmentRequest", 4)]["classification"] == "CONFLICT"  # D
        assert rows[("Customer", 3)]["classification"] == "CONFLICT"  # E
        assert rows[("ShipmentTracking", 1)]["candidate_organization_ids"] == [1]  # F/J
        assert (
            rows[("ShipmentRequest", 5)]["classification"] == "UNRESOLVED"
        )  # L: seedless cycle
        assert rows[("Customer", 4)]["classification"] == "UNRESOLVED"  # L

        valid_mapping = ANALYZER.load_mappings(
            {"format_version": 2, "mappings": [_decision(2, 2)]}, connection
        )
        mapped = {
            (r["entity_type"], r["entity_id"]): r
            for r in ANALYZER.analyze(connection, valid_mapping)
        }
        assert mapped[("Customer", 2)]["classification"] == "DETERMINISTIC"  # G

        old = _decision(2, 1, review_status="SUPERSEDED")
        new = _decision(
            2,
            2,
            decision_version=2,
            decision_id="decision-Customer-2-0002",
            created_at="2026-08-11T11:00:00Z",
            supersedes_decision_id=old["decision_id"],
        )
        history = ANALYZER.load_mappings(
            {"format_version": 2, "mappings": [old, new]}, connection
        )
        assert history[("Customer", 2)]["target_organization_id"] == 2  # H

        improper = ANALYZER.load_mappings(
            {"format_version": 2, "mappings": [_decision(3, 1)]}, connection
        )
        rejected = {
            (r["entity_type"], r["entity_id"]): r
            for r in ANALYZER.analyze(connection, improper)
        }
        assert (
            rejected[("Customer", 3)]["mapping_status"] == "REJECTED_CONFLICT_OVERRIDE"
        )  # I

        readiness = ANALYZER.evaluate_readiness(
            rows.values(),
            quarantine_matrix={"surfaces": []},
            postgresql_evidence={
                "database_backend": "postgresql",
                "loopback_only": True,
                "transaction_read_only": True,
                "mutation_sqlstate": "25006",
                "scenarios": {name: "PASS" for name in "ABCDEFGHIKLM"}
                | {"J": "BLOCKED"},
            },
            security_review_evidence={
                "independent": True,
                "classification": "MT-1B SECURITY REVIEW — BLOCK",
            },
        )
        assert readiness["MT1_OWNERSHIP_RESOLUTION_READY"] is False  # J remains blocked
        with pytest.raises(Exception) as error:
            connection.execute(text("INSERT INTO customer VALUES (999)"))  # M
        assert (
            getattr(error.value.orig, "sqlstate", None)
            or getattr(error.value.orig, "pgcode", None)
        ) == "25006"
        transaction.rollback()
