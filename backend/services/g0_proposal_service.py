"""In-memory G0 proposal prototype for synthetic/de-identified review.

The prototype consumes the deterministic ShipmentRequest context contract and
emits advisory missing-information and ambiguity findings.  It has no database,
network, persistence, approval, application, or external-communication path.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Literal

from backend.services.ai_provider_service import (
    DETERMINISTIC_MOCK_MODE,
    AIProviderRequest,
    build_ai_provider,
)
from backend.services.shipment_context_service import (
    CONTRACT_NAME,
    CONTRACT_PROFILE,
    CONTRACT_VERSION,
)


G0_CAPABILITY = "missing_information_ambiguity_review"
G0_PROPOSAL_SCHEMA_VERSION = "1.0"
G0_POLICY_VERSION = "ai-ready-3g-g0-v1"
G0_FINGERPRINT_DOMAIN = b"forwarder:g0-proposal:v1\x00"
MAX_FINDINGS = 256

InputClassification = Literal["synthetic", "approved_deidentified"]

_FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_SOURCE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_APPROVAL_REFERENCE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{2,63}$")
_ALLOWED_INPUT_CLASSIFICATIONS = frozenset({"synthetic", "approved_deidentified"})
_EXPECTED_CONTEXT_KEYS = frozenset(
    {
        "contract",
        "aggregate",
        "confirmed",
        "missing",
        "ambiguous",
        "excluded",
        "unavailable",
        "limitations",
    }
)
_ALLOWED_AMBIGUITY_REASONS = frozenset(
    {
        "unsupported_shipping_type",
        "values_conflict_with_domestic_shipping_type",
        "values_conflict_with_international_shipping_type",
    }
)
_ALLOWED_MISSING_EVIDENCE = frozenset(
    {
        ("shipment.status", "ShipmentRequest.status"),
        ("shipment.shipping_type", "ShipmentRequest.shipping_type"),
        ("route.origin.province_id", "ShipmentRequest.origin_province_id"),
        ("route.origin.county_id", "ShipmentRequest.origin_county_id"),
        ("route.origin.city_id", "ShipmentRequest.origin_city_id"),
        ("route.destination.province_id", "ShipmentRequest.dest_province_id"),
        ("route.destination.county_id", "ShipmentRequest.dest_county_id"),
        ("route.destination.city_id", "ShipmentRequest.dest_city_id"),
        ("route.origin.country", "ShipmentRequest.origin_country"),
        ("route.origin.city", "ShipmentRequest.origin_city_international"),
        ("route.destination.country", "ShipmentRequest.dest_country"),
        ("route.destination.city", "ShipmentRequest.dest_city_international"),
        ("route.iran_entry_port", "ShipmentRequest.iran_entry_port"),
        ("route.iran_entry_port_id", "ShipmentRequest.iran_entry_port_id"),
        ("route.iran_entry_province", "ShipmentRequest.iran_entry_province"),
        (
            "route.iran_entry_province_id",
            "ShipmentRequest.iran_entry_province_id",
        ),
        (
            "transport.domestic_method",
            "ShipmentRequest.domestic_transport_method",
        ),
        (
            "transport.international_method",
            "ShipmentRequest.international_transport_method",
        ),
        ("transport.preference", "ShipmentRequest.transport_method_preference"),
        ("cargo.description", "ShipmentRequest.cargo_description"),
        ("cargo.weight", "ShipmentRequest.cargo_weight"),
        ("cargo.volume", "ShipmentRequest.cargo_volume"),
        ("dates.created_at", "ShipmentRequest.created_at"),
        ("dates.ready_at", "ShipmentRequest.ready_at"),
        ("dates.pickup", "ShipmentRequest.pickup_date"),
        ("dates.delivery", "ShipmentRequest.delivery_date"),
        ("operations.priority", "ShipmentRequest.priority"),
        ("operations.sla_due_at", "ShipmentRequest.sla_due_at"),
        (
            "operations.last_customer_touch_at",
            "ShipmentRequest.last_customer_touch_at",
        ),
        (
            "operations.has_unread_for_assignee",
            "ShipmentRequest.has_unread_for_assignee",
        ),
    }
)
_ALLOWED_AMBIGUITY_EVIDENCE = {
    ("shipment.shipping_type", "unsupported_shipping_type"): frozenset(
        {"ShipmentRequest.shipping_type"}
    ),
    (
        "route.international",
        "values_conflict_with_domestic_shipping_type",
    ): frozenset(
        {
            "ShipmentRequest.origin_country",
            "ShipmentRequest.origin_city_international",
            "ShipmentRequest.dest_country",
            "ShipmentRequest.dest_city_international",
            "ShipmentRequest.international_transport_method",
        }
    ),
    (
        "route.domestic",
        "values_conflict_with_international_shipping_type",
    ): frozenset(
        {
            "ShipmentRequest.origin_province_id",
            "ShipmentRequest.origin_county_id",
            "ShipmentRequest.origin_city_id",
            "ShipmentRequest.dest_province_id",
            "ShipmentRequest.dest_county_id",
            "ShipmentRequest.dest_city_id",
            "ShipmentRequest.domestic_transport_method",
        }
    ),
}


class G0ProposalError(Exception):
    """Base error for the in-memory G0 prototype."""


class G0ProposalInputError(G0ProposalError):
    """Raised when governance or context preconditions are not satisfied."""


class G0ProposalUnsupportedProviderError(G0ProposalError):
    """Raised when execution does not explicitly select deterministic_mock."""


@dataclass(frozen=True)
class G0EvidenceReference:
    """A bounded reference that never includes a source value."""

    kind: str
    field: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class G0Finding:
    """Immutable advisory finding for one missing or ambiguous field."""

    finding_id: str
    category: str
    field: str
    reason: str
    clarification_question: str
    evidence: G0EvidenceReference


@dataclass(frozen=True)
class G0Proposal:
    """Immutable proposal envelope with no approval or effect authority."""

    proposal_id: str
    capability: str
    proposal_schema_version: str
    policy_version: str
    input_classification: InputClassification
    deidentification_approval_reference: str | None
    context_fingerprint: str
    provider: str
    provider_mode: str
    findings: tuple[G0Finding, ...]
    authority: str
    advisory_only: bool
    requires_human_inspection: bool
    acceptance_supported: bool
    bulk_acceptance_supported: bool
    application_supported: bool
    persistence_allowed: bool
    write_allowed: bool
    send_allowed: bool
    business_effects_applied: bool
    deterministic: bool


def build_g0_proposal(
    context: dict[str, Any],
    *,
    input_classification: InputClassification,
    deidentification_approval_reference: str | None = None,
    provider_mode: str = DETERMINISTIC_MOCK_MODE,
) -> G0Proposal:
    """Build an advisory proposal entirely in memory from an approved context."""
    _validate_governance_input(
        input_classification,
        deidentification_approval_reference,
        provider_mode,
    )
    _validate_context_contract(context)

    request = AIProviderRequest(
        operation=G0_CAPABILITY,
        context=context,
        output_schema_version=G0_PROPOSAL_SCHEMA_VERSION,
    )
    provider_response = build_ai_provider(provider_mode).generate(request)
    findings = _build_findings(request.context)
    proposal_id = _proposal_id(
        provider_response.request_fingerprint,
        input_classification,
        deidentification_approval_reference,
        findings,
    )

    return G0Proposal(
        proposal_id=proposal_id,
        capability=G0_CAPABILITY,
        proposal_schema_version=G0_PROPOSAL_SCHEMA_VERSION,
        policy_version=G0_POLICY_VERSION,
        input_classification=input_classification,
        deidentification_approval_reference=deidentification_approval_reference,
        context_fingerprint=provider_response.request_fingerprint,
        provider=provider_response.provider,
        provider_mode=provider_response.mode,
        findings=findings,
        authority="advisory_only",
        advisory_only=True,
        requires_human_inspection=True,
        acceptance_supported=False,
        bulk_acceptance_supported=False,
        application_supported=False,
        persistence_allowed=False,
        write_allowed=False,
        send_allowed=False,
        business_effects_applied=False,
        deterministic=True,
    )


def _validate_governance_input(
    input_classification: Any,
    deidentification_approval_reference: Any,
    provider_mode: Any,
) -> None:
    if input_classification not in _ALLOWED_INPUT_CLASSIFICATIONS:
        raise G0ProposalInputError("G0 input classification is not allowed")
    if provider_mode != DETERMINISTIC_MOCK_MODE:
        raise G0ProposalUnsupportedProviderError(
            "G0 execution requires deterministic_mock"
        )
    if input_classification == "synthetic":
        if deidentification_approval_reference is not None:
            raise G0ProposalInputError(
                "Synthetic input must not carry a de-identification approval reference"
            )
        return
    if not isinstance(
        deidentification_approval_reference, str
    ) or not _APPROVAL_REFERENCE_PATTERN.fullmatch(
        deidentification_approval_reference
    ):
        raise G0ProposalInputError(
            "Approved de-identified input requires a valid approval reference"
        )


def _validate_context_contract(context: Any) -> None:
    if not isinstance(context, dict):
        raise G0ProposalInputError("G0 context must be an object")
    if frozenset(context) != _EXPECTED_CONTEXT_KEYS:
        raise G0ProposalInputError("G0 context envelope is invalid")
    contract = context.get("contract")
    if not isinstance(contract, dict) or contract != {
        "name": CONTRACT_NAME,
        "version": CONTRACT_VERSION,
        "profile": CONTRACT_PROFILE,
        "mode": "read_only",
        "deterministic": True,
        "classification": "confidential",
    }:
        raise G0ProposalInputError("G0 context contract is not supported")
    aggregate = context.get("aggregate")
    if not isinstance(aggregate, dict) or frozenset(aggregate) != {"type", "id"}:
        raise G0ProposalInputError("G0 aggregate reference is invalid")
    if aggregate.get("type") != "ShipmentRequest":
        raise G0ProposalInputError("G0 aggregate type is not supported")
    for collection in ("confirmed", "missing", "ambiguous", "excluded", "unavailable"):
        if not isinstance(context.get(collection), list):
            raise G0ProposalInputError("G0 context collections are invalid")
    if not isinstance(context.get("limitations"), list):
        raise G0ProposalInputError("G0 context limitations are invalid")


def _build_findings(context: dict[str, Any]) -> tuple[G0Finding, ...]:
    findings: list[G0Finding] = []
    for item in context["missing"]:
        if len(findings) >= MAX_FINDINGS:
            raise G0ProposalInputError("G0 context exceeds the finding limit")
        field = _required_field(item)
        if item.get("reason") != "not_provided":
            raise G0ProposalInputError("G0 missing-information reason is unsupported")
        if not _FIELD_PATTERN.fullmatch(str(item.get("classification", ""))):
            raise G0ProposalInputError("G0 missing-information classification is invalid")
        if not _FIELD_PATTERN.fullmatch(str(item.get("content_trust", ""))):
            raise G0ProposalInputError("G0 missing-information trust metadata is invalid")
        source = _required_source(item.get("source"))
        if (field, source) not in _ALLOWED_MISSING_EVIDENCE:
            raise G0ProposalInputError("G0 missing-information evidence is unsupported")
        findings.append(
            _finding(
                category="missing_information",
                field=field,
                reason="not_provided",
                question=f"Please verify whether {field} is available.",
                evidence_kind="schema_absence",
                sources=(source,),
            )
        )

    for item in context["ambiguous"]:
        if len(findings) >= MAX_FINDINGS:
            raise G0ProposalInputError("G0 context exceeds the finding limit")
        field = _required_field(item)
        reason = item.get("reason")
        if reason not in _ALLOWED_AMBIGUITY_REASONS:
            raise G0ProposalInputError("G0 ambiguity reason is unsupported")
        candidates = item.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise G0ProposalInputError("G0 ambiguity evidence is invalid")
        if any(
            not isinstance(candidate, dict) or "value" not in candidate
            for candidate in candidates
        ):
            raise G0ProposalInputError("G0 ambiguity evidence is invalid")
        sources = tuple(
            sorted({_required_source(candidate.get("source")) for candidate in candidates})
        )
        if not sources or len(sources) != len(candidates):
            raise G0ProposalInputError("G0 ambiguity evidence is invalid")
        allowed_sources = _ALLOWED_AMBIGUITY_EVIDENCE.get((field, reason))
        if allowed_sources is None or not set(sources).issubset(allowed_sources):
            raise G0ProposalInputError("G0 ambiguity evidence is unsupported")
        findings.append(
            _finding(
                category="ambiguity",
                field=field,
                reason=reason,
                question=f"Please clarify the conflicting information for {field}.",
                evidence_kind="context_conflict",
                sources=sources,
            )
        )

    return tuple(sorted(findings, key=lambda item: (item.category, item.field, item.finding_id)))


def _required_field(item: Any) -> str:
    if not isinstance(item, dict):
        raise G0ProposalInputError("G0 finding input is invalid")
    field = item.get("field")
    if not isinstance(field, str) or not _FIELD_PATTERN.fullmatch(field):
        raise G0ProposalInputError("G0 field reference is invalid")
    return field


def _required_source(source: Any) -> str:
    if not isinstance(source, str) or not _SOURCE_PATTERN.fullmatch(source):
        raise G0ProposalInputError("G0 evidence source is invalid")
    return source


def _finding(
    *,
    category: str,
    field: str,
    reason: str,
    question: str,
    evidence_kind: str,
    sources: tuple[str, ...],
) -> G0Finding:
    payload = json.dumps(
        {
            "category": category,
            "field": field,
            "reason": reason,
            "sources": sources,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    finding_id = hashlib.sha256(G0_FINGERPRINT_DOMAIN + payload).hexdigest()
    return G0Finding(
        finding_id=finding_id,
        category=category,
        field=field,
        reason=reason,
        clarification_question=question,
        evidence=G0EvidenceReference(
            kind=evidence_kind,
            field=field,
            sources=sources,
        ),
    )


def _proposal_id(
    context_fingerprint: str,
    input_classification: str,
    approval_reference: str | None,
    findings: tuple[G0Finding, ...],
) -> str:
    payload = json.dumps(
        {
            "approval_reference": approval_reference,
            "capability": G0_CAPABILITY,
            "context_fingerprint": context_fingerprint,
            "finding_ids": [finding.finding_id for finding in findings],
            "input_classification": input_classification,
            "policy_version": G0_POLICY_VERSION,
            "schema_version": G0_PROPOSAL_SCHEMA_VERSION,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(G0_FINGERPRINT_DOMAIN + payload).hexdigest()
