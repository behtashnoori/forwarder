import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

MODULE_PATH = Path(__file__).parents[1] / "mt1a_legacy_ownership_analyzer.py"
SPEC = importlib.util.spec_from_file_location("mt1b_analyzer", MODULE_PATH)
ANALYZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYZER
SPEC.loader.exec_module(ANALYZER)

DDL = """
CREATE TABLE operational_organization (id INTEGER PRIMARY KEY);
CREATE TABLE customer (id INTEGER PRIMARY KEY);
CREATE TABLE customer_gamification (id INTEGER PRIMARY KEY);
CREATE TABLE shipment_request (id INTEGER PRIMARY KEY, project_id INTEGER, customer_id INTEGER, gamification_customer_id INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, primary_customer_id INTEGER);
CREATE TABLE expert_quote (id INTEGER PRIMARY KEY, shipment_request_id INTEGER NOT NULL, operational_organization_id INTEGER);
CREATE TABLE operational_shipment (id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, project_id INTEGER, source_type TEXT NOT NULL, customer_id INTEGER, shipment_request_id INTEGER, accepted_quote_id INTEGER);
CREATE TABLE shipment_tracking (id INTEGER PRIMARY KEY, shipment_request_id INTEGER NOT NULL);
CREATE TABLE shipment_transport_unit (id INTEGER PRIMARY KEY, tracking_id INTEGER NOT NULL);
CREATE TABLE shipment_transport_unit_update (id INTEGER PRIMARY KEY, unit_id INTEGER NOT NULL);
CREATE TABLE referral_rule (id INTEGER PRIMARY KEY);
CREATE TABLE referral_rule_state (id INTEGER PRIMARY KEY, rule_id INTEGER NOT NULL);
CREATE TABLE referral_auto_assign_state (id INTEGER PRIMARY KEY);
CREATE TABLE referral_assignment_log (id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL, rule_id INTEGER);
CREATE TABLE case_document_requirement (id INTEGER PRIMARY KEY, shipment_request_id INTEGER NOT NULL);
CREATE TABLE case_document_file (id INTEGER PRIMARY KEY, shipment_request_id INTEGER NOT NULL, case_requirement_id INTEGER);
CREATE TABLE document_audit_event (id INTEGER PRIMARY KEY, shipment_request_id INTEGER, document_file_id INTEGER);
CREATE TABLE project_party_relationship (project_id INTEGER NOT NULL, customer_id INTEGER NOT NULL, party_role TEXT NOT NULL, PRIMARY KEY(project_id, customer_id, party_role));
"""


def database():
    engine = create_engine("sqlite://").execution_options(
        include_quarantined_for_certification=True
    )
    with engine.begin() as connection:
        connection = connection.execution_options(
            include_quarantined_for_certification=True
        )
        for statement in DDL.split(";"):
            if statement.strip():
                connection.execute(text(statement))
        connection.execute(
            text("INSERT INTO operational_organization VALUES (1),(2),(3)")
        )
        connection.execute(text("INSERT INTO customer VALUES (1),(2),(3),(4),(5)"))
        connection.execute(text("INSERT INTO customer_gamification VALUES (1)"))
        connection.execute(text("INSERT INTO project VALUES (1,1,1),(2,1,3),(3,2,3)"))
        connection.execute(
            text(
                "INSERT INTO shipment_request VALUES (1,1,1,NULL),(2,999,NULL,NULL),(3,2,NULL,NULL),(4,NULL,5,NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO expert_quote VALUES (1,1,1),(2,3,2),(3,4,NULL)")
        )
        connection.execute(
            text(
                "INSERT INTO operational_shipment VALUES (1,1,1,'accepted_quote',1,1,1)"
            )
        )
        connection.execute(text("INSERT INTO shipment_tracking VALUES (1,1)"))
        connection.execute(text("INSERT INTO shipment_transport_unit VALUES (1,1)"))
        connection.execute(
            text("INSERT INTO shipment_transport_unit_update VALUES (1,1)")
        )
        connection.execute(text("INSERT INTO referral_rule VALUES (1)"))
        connection.execute(text("INSERT INTO referral_rule_state VALUES (1,1)"))
        connection.execute(text("INSERT INTO referral_auto_assign_state VALUES (1)"))
        connection.execute(text("INSERT INTO referral_assignment_log VALUES (1,1,1)"))
        connection.execute(
            text("INSERT INTO case_document_requirement VALUES (1,1),(2,3)")
        )
        connection.execute(
            text("INSERT INTO case_document_file VALUES (1,1,1),(2,1,2)")
        )
        connection.execute(
            text("INSERT INTO document_audit_event VALUES (1,NULL,1),(2,3,1)")
        )
        connection.execute(
            text("INSERT INTO project_party_relationship VALUES (1,1,'payer')")
        )
    return engine


def row_map(connection, mappings=None):
    return {
        (r["entity_type"], r["entity_id"]): r
        for r in ANALYZER.analyze(connection, mappings, require_full_coverage=False)
    }


def decision(entity="Customer", entity_id=2, organization_id=2, **overrides):
    value = {
        "entity_type": entity,
        "entity_id": entity_id,
        "target_organization_id": organization_id,
        "reason": "reviewed source record",
        "operator_identity": "operator-a",
        "reviewer_identity": "reviewer-b",
        "created_at": "2026-08-11T10:00:00Z",
        "decision_version": 1,
        "decision_id": f"decision-{entity}-{entity_id}-0001",
        "review_status": "ACTIVE",
    }
    value.update(overrides)
    return value


def test_fixpoint_conflict_invalid_cycle_and_full_present_coverage():
    with database().connect() as connection:
        rows = row_map(connection)
    assert rows[("ShipmentRequest", 1)]["classification"] == "DETERMINISTIC"
    assert rows[("ShipmentRequest", 2)]["classification"] == "INVALID_LINEAGE"
    assert rows[("ShipmentRequest", 3)]["classification"] == "CONFLICT"
    assert rows[("Customer", 3)]["classification"] == "CONFLICT"
    assert rows[("ShipmentTransportUnitUpdate", 1)]["candidate_organization_ids"] == [1]
    assert rows[("ExpertQuote", 3)]["classification"] == "UNRESOLVED"
    assert rows[("ReferralAssignmentLog", 1)]["candidate_organization_ids"] == [1]
    assert rows[("CaseDocumentFile", 1)]["candidate_organization_ids"] == [1]
    assert rows[("DocumentAuditEvent", 1)]["candidate_organization_ids"] == [1]
    assert rows[("CaseDocumentFile", 2)]["classification"] == "INVALID_LINEAGE"
    assert rows[("DocumentAuditEvent", 2)]["classification"] == "INVALID_LINEAGE"
    assert (
        rows[
            (
                "project_party_relationship",
                "project_id=1;customer_id=1;party_role=payer",
            )
        ]["classification"]
        == "DETERMINISTIC"
    )
    party_identity = rows[
        (
            "project_party_relationship",
            "project_id=1;customer_id=1;party_role=payer",
        )
    ]["resource_identity"]
    assert [item["name"] for item in party_identity["resource_key"]["components"]] == [
        "project_id", "customer_id", "party_role"
    ]
    assert party_identity["resource_key"]["components"][-1]["value"] == "payer"
    assert rows[("ReferralRule", 1)]["classification"] == "UNRESOLVED"
    assert rows[("ReferralRuleState", 1)]["classification"] == "UNRESOLVED"
    assert rows[("ReferralAutoAssignState", 1)]["quarantine_status"] == "QUARANTINED"


def test_mapping_schema_valid_and_references_are_enforced():
    engine = database()
    document = {"format_version": 2, "mappings": [decision()]}
    with engine.connect() as connection:
        mappings = ANALYZER.load_mappings(document, connection)
        assert (
            row_map(connection, mappings)[("Customer", 2)]["mapping_status"] == "ACTIVE"
        )
    missing = {"format_version": 2, "mappings": [decision(entity_id=999)]}
    with engine.connect() as connection, pytest.raises(ValueError, match="missing row"):
        ANALYZER.load_mappings(missing, connection)
    bad_org = {"format_version": 2, "mappings": [decision(organization_id=999)]}
    with (
        engine.connect() as connection,
        pytest.raises(ValueError, match="missing organization"),
    ):
        ANALYZER.load_mappings(bad_org, connection)


def test_mapping_history_and_reviewer_controls():
    first = decision(review_status="ACTIVE")
    second = decision(
        organization_id=1,
        created_at="2026-08-11T11:00:00Z",
        decision_version=2,
        decision_id="decision-Customer-2-0002",
        supersedes_decision_id=first["decision_id"],
    )
    assert (
        ANALYZER.load_mappings({"format_version": 2, "mappings": [first, second]})[
            ("Customer", 2)
        ]["decision_version"]
        == 2
    )
    with pytest.raises(ValueError, match="operator and reviewer"):
        ANALYZER.load_mappings(
            {
                "format_version": 2,
                "mappings": [decision(reviewer_identity="operator-a")],
            }
        )
    with pytest.raises(ValueError, match="duplicate or contradictory"):
        ANALYZER.load_mappings(
            {
                "format_version": 2,
                "mappings": [
                    decision(),
                    decision(organization_id=1, decision_id="decision-Customer-2-0002"),
                ],
            }
        )


def test_mapping_cannot_manufacture_conflict_adjudication_candidates():
    mapped = decision(
        entity_id=1,
        organization_id=2,
        conflict_adjudication={
            "candidate_organization_ids": [1, 2],
            "evidence_reference": "evidence:review-1",
            "policy_version": "mt1b-v1",
        },
    )
    with database().connect() as connection:
        mappings = ANALYZER.load_mappings(
            {"format_version": 2, "mappings": [mapped]}, connection
        )
        row = row_map(connection, mappings)[("Customer", 1)]
    assert row["classification"] == "DETERMINISTIC"
    assert row["candidate_organization_ids"] == [1]
    assert row["mapping_status"] == "REJECTED_STALE_ADJUDICATION"


def test_full_coverage_fails_closed_on_partial_schema():
    with (
        database().connect() as connection,
        pytest.raises(ValueError, match="coverage error: missing declared tables"),
    ):
        ANALYZER.analyze(connection)


def test_mapping_cannot_silently_override_conflict():
    with database().connect() as connection:
        mappings = ANALYZER.load_mappings(
            {
                "format_version": 2,
                "mappings": [decision(entity_id=3, organization_id=1)],
            },
            connection,
        )
        row = row_map(connection, mappings)[("Customer", 3)]
    assert row["classification"] == "CONFLICT"
    assert row["mapping_status"] == "REJECTED_CONFLICT_OVERRIDE"


def test_readiness_is_evidence_only_and_fail_closed():
    rows = [{"classification": "DETERMINISTIC", "mapping_status": "NONE"}]
    matrix = {
        "surfaces": [
            {"surface": name, "pass": True}
            for name in sorted(ANALYZER.REQUIRED_QUARANTINE_SURFACES)
        ]
    }
    postgres = {
        "database_backend": "postgresql",
        "loopback_only": True,
        "transaction_read_only": True,
        "mutation_sqlstate": "25006",
        "scenarios": {name: "PASS" for name in ANALYZER.REQUIRED_POSTGRESQL_SCENARIOS},
    }
    review = {"independent": True, "classification": "MT-1B SECURITY REVIEW — PASS"}
    assert (
        ANALYZER.evaluate_readiness(
            rows,
            quarantine_matrix=matrix,
            postgresql_evidence=postgres,
            security_review_evidence=review,
        )["MT1_OWNERSHIP_RESOLUTION_READY"]
        is True
    )
    rows.append({"classification": "UNRESOLVED", "mapping_status": "NONE"})
    assert (
        ANALYZER.evaluate_readiness(
            rows,
            quarantine_matrix=matrix,
            postgresql_evidence=postgres,
            security_review_evidence=review,
        )["MT1_OWNERSHIP_RESOLUTION_READY"]
        is False
    )
    assert (
        ANALYZER.evaluate_readiness(rows[:1])["MT1_OWNERSHIP_RESOLUTION_READY"] is False
    )


def test_schema_rejects_changed_stable_id_and_unauthorized_status():
    bad = decision()
    bad["entity_id"] = "2"
    with pytest.raises(ValueError, match="invalid mapping document"):
        ANALYZER.load_mappings({"format_version": 2, "mappings": [bad]})


def test_json_schema_is_executed_not_just_duplicated_in_python():
    bad = decision(operator_identity="x" * 201)
    with pytest.raises(
        ValueError, match="invalid mapping document at mappings.0.operator_identity"
    ):
        ANALYZER.load_mappings({"format_version": 2, "mappings": [bad]})
    bad = decision(decision_id="contains spaces")
    with pytest.raises(
        ValueError, match="invalid mapping document at mappings.0.decision_id"
    ):
        ANALYZER.load_mappings({"format_version": 2, "mappings": [bad]})


def test_mapping_rejects_extra_property_and_stale_conflict_adjudication():
    bad = decision(unexpected=True)
    with pytest.raises(ValueError, match="invalid mapping document"):
        ANALYZER.load_mappings({"format_version": 2, "mappings": [bad]})
    mapped = decision(
        entity_id=3,
        organization_id=1,
        conflict_adjudication={
            "candidate_organization_ids": [1, 3],
            "evidence_reference": "evidence:review-1",
            "policy_version": "mt1b-v1",
        },
    )
    with database().connect() as connection:
        mappings = ANALYZER.load_mappings(
            {"format_version": 2, "mappings": [mapped]}, connection
        )
        row = row_map(connection, mappings)[("Customer", 3)]
    assert row["classification"] == "CONFLICT"
    assert row["mapping_status"] == "REJECTED_STALE_ADJUDICATION"
    bad = decision(review_status="APPROVED")
    with pytest.raises(ValueError, match="invalid mapping document"):
        ANALYZER.load_mappings({"format_version": 2, "mappings": [bad]})


def synthetic_provenance(**overrides):
    hashes = {"csv_sha256": "a" * 64, "summary_sha256": "b" * 64}
    value = {
        "dataset_classification": "SYNTHETIC_ONLY",
        "legacy_real_customer_data_present": False,
        "human_ownership_adjudication_required_for_this_dataset": False,
        "auto_tenant_assignment_allowed": False,
        "synthetic_data_may_be_disposed_only_by_explicit_policy": True,
        "real_data_census_required_if_real_legacy_data_is_ever_introduced": True,
        "recommended_disposition": "KEEP_QUARANTINED_SYNTHETIC",
        "source_census_hashes": hashes,
        "total_rows": 1,
    }
    value.update(overrides)
    return value


def test_synthetic_only_skips_mapping_but_does_not_clear_ownership():
    rows = [{
        "classification": "UNRESOLVED",
        "candidate_organization_ids": [],
        "mapping_status": "NONE",
        "quarantine_status": "QUARANTINED",
    }]
    gate = ANALYZER.evaluate_dataset_provenance(
        rows,
        synthetic_provenance(),
        observed_census_hashes=synthetic_provenance()["source_census_hashes"],
    )
    assert gate["provenance_gate_pass"] is True
    assert gate["REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED"] is False
    assert gate["SYNTHETIC_LEGACY_DISPOSITION_READY"] is True
    assert rows[0]["classification"] == "UNRESOLVED"
    assert rows[0]["quarantine_status"] == "QUARANTINED"


def test_synthetic_classification_rejects_candidates_and_active_mappings():
    candidate = [{"candidate_organization_ids": [1], "mapping_status": "NONE"}]
    mapped = [{"candidate_organization_ids": [], "mapping_status": "ACTIVE"}]
    assert not ANALYZER.evaluate_dataset_provenance(
        candidate,
        synthetic_provenance(),
        observed_census_hashes=synthetic_provenance()["source_census_hashes"],
    )["provenance_gate_pass"]
    assert not ANALYZER.evaluate_dataset_provenance(
        mapped,
        synthetic_provenance(),
        observed_census_hashes=synthetic_provenance()["source_census_hashes"],
    )["provenance_gate_pass"]


def test_real_and_unknown_provenance_fail_closed_for_ownership():
    rows = [{"candidate_organization_ids": [], "mapping_status": "NONE"}]
    unknown = ANALYZER.evaluate_dataset_provenance(rows)
    assert unknown["REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED"] is True
    assert unknown["provenance_gate_pass"] is False
    real = ANALYZER.evaluate_dataset_provenance(
        rows, {"dataset_classification": "REAL_NON_PRODUCTION_CLONE"}
    )
    assert real["REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED"] is True
    assert real["MT1_REAL_DATA_GATE_APPLICABLE"] is True


def test_future_real_dataset_cannot_reuse_synthetic_exemption():
    rows = [{"candidate_organization_ids": [], "mapping_status": "NONE"}]
    malformed = synthetic_provenance(legacy_real_customer_data_present=True)
    gate = ANALYZER.evaluate_dataset_provenance(
        rows,
        malformed,
        observed_census_hashes=malformed["source_census_hashes"],
    )
    assert gate["provenance_gate_pass"] is False
    assert gate["REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED"] is True


def test_future_dataset_cannot_reuse_synthetic_manifest_hashes():
    rows = [{"candidate_organization_ids": [], "mapping_status": "NONE"}]
    provenance = synthetic_provenance()
    gate = ANALYZER.evaluate_dataset_provenance(
        rows,
        provenance,
        observed_census_hashes={"csv_sha256": "c" * 64, "summary_sha256": "d" * 64},
    )
    assert gate["provenance_gate_pass"] is False
    assert gate["REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED"] is True
