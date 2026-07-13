"""Synthetic governance and safety tests for the in-memory G0 prototype."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
from copy import deepcopy
import builtins
import json
import os
import socket

import pytest

from backend.extensions import db
from backend.services.g0_proposal_service import (
    G0ProposalInputError,
    G0ProposalUnsupportedProviderError,
    build_g0_proposal,
)


def _context() -> dict:
    return {
        "contract": {
            "name": "shipment_request_context",
            "version": "1.0",
            "profile": "operational_minimum_v1",
            "mode": "read_only",
            "deterministic": True,
            "classification": "confidential",
        },
        "aggregate": {"type": "ShipmentRequest", "id": "SYNTHETIC-001"},
        "confirmed": [
            {
                "field": "cargo.description",
                "source": "ShipmentRequest.cargo_description",
                "classification": "operational_confidential",
                "content_trust": "untrusted_user_text",
                "value": "SYNTHETIC-CANARY-NOT-FOR-OUTPUT",
            }
        ],
        "missing": [
            {
                "field": "cargo.weight",
                "source": "ShipmentRequest.cargo_weight",
                "classification": "operational_confidential",
                "content_trust": "trusted_structured",
                "reason": "not_provided",
            }
        ],
        "ambiguous": [
            {
                "field": "route.international",
                "reason": "values_conflict_with_domestic_shipping_type",
                "candidates": [
                    {
                        "value": "SYNTHETIC-COUNTRY-CANARY",
                        "source": "ShipmentRequest.origin_country",
                    }
                ],
            }
        ],
        "excluded": [],
        "unavailable": [],
        "limitations": ["read_only_snapshot", "not_authoritative_for_writes"],
    }


def test_synthetic_proposal_is_deterministic_advisory_and_in_memory() -> None:
    context = _context()
    before = deepcopy(context)

    first = build_g0_proposal(context, input_classification="synthetic")
    second = build_g0_proposal(context, input_classification="synthetic")

    assert first == second
    assert context == before
    assert first.provider == "deterministic_mock"
    assert first.provider_mode == "deterministic_mock"
    assert first.authority == "advisory_only"
    assert first.advisory_only is True
    assert first.requires_human_inspection is True
    assert first.acceptance_supported is False
    assert first.bulk_acceptance_supported is False
    assert first.application_supported is False
    assert first.persistence_allowed is False
    assert first.write_allowed is False
    assert first.send_allowed is False
    assert first.business_effects_applied is False
    assert first.deterministic is True


def test_only_missing_information_and_ambiguity_findings_are_emitted() -> None:
    proposal = build_g0_proposal(_context(), input_classification="synthetic")

    assert [(item.category, item.field, item.reason) for item in proposal.findings] == [
        (
            "ambiguity",
            "route.international",
            "values_conflict_with_domestic_shipping_type",
        ),
        ("missing_information", "cargo.weight", "not_provided"),
    ]
    assert proposal.findings[0].evidence.sources == (
        "ShipmentRequest.origin_country",
    )
    assert proposal.findings[1].evidence.kind == "schema_absence"


def test_output_does_not_echo_confirmed_or_ambiguous_values() -> None:
    proposal = build_g0_proposal(_context(), input_classification="synthetic")
    serialized = json.dumps(asdict(proposal), sort_keys=True)

    assert "SYNTHETIC-CANARY-NOT-FOR-OUTPUT" not in serialized
    assert "SYNTHETIC-COUNTRY-CANARY" not in serialized
    assert "SYNTHETIC-001" not in serialized


def test_approved_deidentified_input_requires_bounded_approval_reference() -> None:
    context = _context()
    proposal = build_g0_proposal(
        context,
        input_classification="approved_deidentified",
        deidentification_approval_reference="DEID:TEST:001",
    )
    assert proposal.input_classification == "approved_deidentified"
    assert proposal.deidentification_approval_reference == "DEID:TEST:001"

    with pytest.raises(G0ProposalInputError, match="approval reference"):
        build_g0_proposal(context, input_classification="approved_deidentified")
    with pytest.raises(G0ProposalInputError, match="must not carry"):
        build_g0_proposal(
            context,
            input_classification="synthetic",
            deidentification_approval_reference="DEID:TEST:001",
        )


@pytest.mark.parametrize("classification", ["real", "operational", "production", ""])
def test_real_or_unapproved_input_classifications_fail_closed(classification: str) -> None:
    with pytest.raises(G0ProposalInputError, match="classification is not allowed"):
        build_g0_proposal(  # type: ignore[arg-type]
            _context(),
            input_classification=classification,
        )


@pytest.mark.parametrize("mode", [None, "", "disabled", "openai", "Deterministic_Mock"])
def test_only_exact_deterministic_mock_mode_is_allowed(mode) -> None:
    with pytest.raises(
        G0ProposalUnsupportedProviderError,
        match="requires deterministic_mock",
    ):
        build_g0_proposal(
            _context(),
            input_classification="synthetic",
            provider_mode=mode,
        )


def test_unknown_contract_reason_and_unbounded_evidence_fail_closed() -> None:
    invalid_contract = _context()
    invalid_contract["contract"]["version"] = "2.0"
    with pytest.raises(G0ProposalInputError, match="contract is not supported"):
        build_g0_proposal(invalid_contract, input_classification="synthetic")

    invalid_reason = _context()
    invalid_reason["missing"][0]["reason"] = "infer_a_value"
    with pytest.raises(G0ProposalInputError, match="reason is unsupported"):
        build_g0_proposal(invalid_reason, input_classification="synthetic")

    invalid_source = _context()
    invalid_source["ambiguous"][0]["candidates"][0]["source"] = "secret value"
    with pytest.raises(G0ProposalInputError, match="source is invalid"):
        build_g0_proposal(invalid_source, input_classification="synthetic")


def test_forged_context_envelope_aggregate_metadata_and_candidate_fail_closed() -> None:
    extra_key = _context()
    extra_key["raw_email"] = "must never be accepted"
    with pytest.raises(G0ProposalInputError, match="envelope is invalid"):
        build_g0_proposal(extra_key, input_classification="synthetic")

    wrong_aggregate = _context()
    wrong_aggregate["aggregate"]["type"] = "Customer"
    with pytest.raises(G0ProposalInputError, match="type is not supported"):
        build_g0_proposal(wrong_aggregate, input_classification="synthetic")

    missing_metadata = _context()
    del missing_metadata["missing"][0]["classification"]
    with pytest.raises(G0ProposalInputError, match="classification is invalid"):
        build_g0_proposal(missing_metadata, input_classification="synthetic")

    missing_candidate_value = _context()
    del missing_candidate_value["ambiguous"][0]["candidates"][0]["value"]
    with pytest.raises(G0ProposalInputError, match="evidence is invalid"):
        build_g0_proposal(missing_candidate_value, input_classification="synthetic")


def test_invented_excluded_or_mismatched_evidence_fails_closed() -> None:
    invented_missing = _context()
    invented_missing["missing"][0]["field"] = "shipment.invented"
    invented_missing["missing"][0]["source"] = "ShipmentRequest.invented"
    with pytest.raises(G0ProposalInputError, match="evidence is unsupported"):
        build_g0_proposal(invented_missing, input_classification="synthetic")

    excluded_missing = _context()
    excluded_missing["missing"][0]["field"] = "contact_phone"
    excluded_missing["missing"][0]["source"] = "ShipmentRequest.contact_phone"
    with pytest.raises(G0ProposalInputError, match="evidence is unsupported"):
        build_g0_proposal(excluded_missing, input_classification="synthetic")

    mismatched_missing = _context()
    mismatched_missing["missing"][0]["source"] = "ShipmentRequest.cargo_volume"
    with pytest.raises(G0ProposalInputError, match="evidence is unsupported"):
        build_g0_proposal(mismatched_missing, input_classification="synthetic")

    arbitrary_ambiguity = _context()
    arbitrary_ambiguity["ambiguous"][0]["field"] = "cargo.weight"
    with pytest.raises(G0ProposalInputError, match="evidence is unsupported"):
        build_g0_proposal(arbitrary_ambiguity, input_classification="synthetic")

    forbidden_candidate_source = _context()
    forbidden_candidate_source["ambiguous"][0]["candidates"][0][
        "source"
    ] = "ShipmentRequest.contact_phone"
    with pytest.raises(G0ProposalInputError, match="evidence is unsupported"):
        build_g0_proposal(forbidden_candidate_source, input_classification="synthetic")


def test_finding_and_proposal_objects_are_immutable() -> None:
    proposal = build_g0_proposal(_context(), input_classification="synthetic")
    with pytest.raises(FrozenInstanceError):
        proposal.write_allowed = True  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        proposal.findings[0].reason = "changed"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        proposal.findings.append("changed")  # type: ignore[attr-defined]


def test_execution_does_not_access_db_network_environment_config_or_files(
    monkeypatch,
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("external state was accessed")

    monkeypatch.setattr(db.session, "add", forbidden)
    monkeypatch.setattr(db.session, "commit", forbidden)
    monkeypatch.setattr(db.session, "execute", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(os.environ, "get", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)

    proposal = build_g0_proposal(_context(), input_classification="synthetic")
    assert proposal.business_effects_applied is False
