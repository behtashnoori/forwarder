"""Safety and contract tests for the vendor-neutral AI provider boundary."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict
import hashlib
import json
import os
import socket

import pytest

from backend.extensions import db
from backend.services.ai_provider_service import (
    AIProvider,
    AIProviderDisabledError,
    AIProviderInvalidRequestError,
    AIProviderOutput,
    AIProviderRequest,
    AIProviderResponse,
    AIProviderUnsupportedModeError,
    DETERMINISTIC_MOCK_MODE,
    FINGERPRINT_DOMAIN,
    MAX_CANONICAL_REQUEST_BYTES,
    MAX_CONTEXT_DEPTH,
    MAX_CONTEXT_ITEMS,
    PROVIDER_INTERFACE_VERSION,
    DeterministicMockAIProvider,
    DisabledAIProvider,
    build_ai_provider,
    canonicalize_request,
    request_fingerprint,
)


def _request(context: dict | None = None) -> AIProviderRequest:
    return AIProviderRequest(
        operation="shipment_summary",
        context=context if context is not None else {"shipment": {"id": 42}},
        output_schema_version="1.0",
    )


def test_protocol_request_and_response_contract() -> None:
    provider = build_ai_provider(DETERMINISTIC_MOCK_MODE)
    request = _request()
    response = provider.generate(request)

    assert isinstance(provider, AIProvider)
    assert isinstance(provider, DeterministicMockAIProvider)
    assert isinstance(request, AIProviderRequest)
    assert isinstance(response, AIProviderResponse)
    assert isinstance(response.output, AIProviderOutput)
    assert response.provider == "deterministic_mock"
    assert response.mode == "deterministic_mock"
    assert response.output_schema_version == "1.0"
    assert request.interface_version == PROVIDER_INTERFACE_VERSION
    assert response.interface_version == PROVIDER_INTERFACE_VERSION


def test_default_disabled_rejects_without_inspecting_context() -> None:
    provider = build_ai_provider()
    request = _request()
    sentinel = object()
    object.__setattr__(request, "_canonical_context", sentinel)

    assert isinstance(provider, DisabledAIProvider)
    assert isinstance(provider, AIProvider)
    with pytest.raises(AIProviderDisabledError, match="execution is disabled"):
        provider.generate(request)


@pytest.mark.parametrize(
    "mode",
    [None, "", "DISABLED", " deterministic_mock", "Deterministic_Mock", "openai", "https://vendor.invalid/key"],
)
def test_only_exact_allowlisted_modes_are_accepted_without_echo(mode) -> None:
    with pytest.raises(AIProviderUnsupportedModeError) as exc_info:
        build_ai_provider(mode)  # type: ignore[arg-type]

    assert str(exc_info.value) == "Unsupported AI provider mode"
    if mode:
        assert str(mode) not in str(exc_info.value)


def test_explicit_exact_deterministic_mock_is_required() -> None:
    assert isinstance(build_ai_provider("disabled"), DisabledAIProvider)
    assert isinstance(build_ai_provider("deterministic_mock"), DeterministicMockAIProvider)


@pytest.mark.parametrize(
    "context",
    [
        {"bad": float("nan")},
        {"bad": float("inf")},
        {"bad": (1, 2)},
        {"bad": object()},
        {1: "non-string-key"},
    ],
)
def test_strict_json_rejects_non_json_values(context: dict) -> None:
    with pytest.raises(AIProviderInvalidRequestError):
        _request(context)


def test_nested_strict_json_is_accepted() -> None:
    context = {"a": [None, True, 7, 2.5, "text", {"nested": ["x"]}]}
    canonical = canonicalize_request(_request(context))
    assert json.loads(canonical)["context"] == context


def test_cycle_depth_item_and_encoded_size_limits_fail_closed() -> None:
    cyclic: dict = {}
    cyclic["self"] = cyclic
    with pytest.raises(AIProviderInvalidRequestError, match="cycle"):
        _request(cyclic)

    nested: dict = {}
    cursor = nested
    for _ in range(MAX_CONTEXT_DEPTH + 2):
        child: dict = {}
        cursor["child"] = child
        cursor = child
    with pytest.raises(AIProviderInvalidRequestError, match="nesting limit"):
        _request(nested)

    with pytest.raises(AIProviderInvalidRequestError, match="item limit"):
        _request({"items": list(range(MAX_CONTEXT_ITEMS))})

    oversized = "é" * (MAX_CANONICAL_REQUEST_BYTES // 2 + 1)
    with pytest.raises(AIProviderInvalidRequestError, match="size limit"):
        _request({"payload": oversized})


def test_operation_and_version_are_bounded_identifiers() -> None:
    invalid = [
        ("", {}, "1.0"),
        ("summarize shipment", {}, "1.0"),
        ("shipment_summary", {}, ""),
        ("shipment_summary", {}, "version with spaces"),
    ]
    for operation, context, version in invalid:
        with pytest.raises(AIProviderInvalidRequestError):
            AIProviderRequest(operation, context, version)


def test_fingerprint_is_domain_separated_order_stable_and_list_order_sensitive() -> None:
    first = _request({"b": 2, "a": {"y": 4, "x": 3}, "list": [1, 2]})
    reordered = _request({"list": [1, 2], "a": {"x": 3, "y": 4}, "b": 2})
    reversed_list = _request({"b": 2, "a": {"y": 4, "x": 3}, "list": [2, 1]})

    assert request_fingerprint(first) == request_fingerprint(reordered)
    assert request_fingerprint(first) != request_fingerprint(reversed_list)
    expected = hashlib.sha256(
        FINGERPRINT_DOMAIN + canonicalize_request(first).encode("utf-8")
    ).hexdigest()
    plain_hash = hashlib.sha256(canonicalize_request(first).encode("utf-8")).hexdigest()
    assert request_fingerprint(first) == expected
    assert request_fingerprint(first) != plain_hash


def test_request_snapshots_context_and_returned_context_copies_do_not_alias() -> None:
    context = {"shipment": {"id": 42}, "list": [1, 2]}
    request = _request(context)
    initial_fingerprint = request_fingerprint(request)

    context["shipment"]["id"] = 99
    context["list"].append(3)
    first_copy = request.context
    second_copy = request.context
    first_copy["shipment"]["id"] = 100
    first_copy["list"].append(4)

    assert request.context == {"list": [1, 2], "shipment": {"id": 42}}
    assert second_copy == {"list": [1, 2], "shipment": {"id": 42}}
    assert first_copy is not second_copy
    assert first_copy["shipment"] is not second_copy["shipment"]
    assert request_fingerprint(request) == initial_fingerprint


def test_mock_is_deterministic_does_not_mutate_alias_or_echo_context_secrets() -> None:
    context = {"shipment": {"id": 42}, "private_canary": "DO-NOT-ECHO-SECRET"}
    before = deepcopy(context)
    request = _request(context)
    provider = build_ai_provider("deterministic_mock")

    first = provider.generate(request)
    second = provider.generate(request)

    assert first == second
    assert context == before
    assert first.output is not context
    serialized = json.dumps(asdict(first), allow_nan=False, sort_keys=True)
    assert "DO-NOT-ECHO-SECRET" not in serialized
    context["shipment"]["id"] = 99
    assert first.output.operation == "shipment_summary"
    assert first.request_fingerprint == request_fingerprint(request)


def test_output_is_strict_json_advisory_and_cannot_write_or_send() -> None:
    response = build_ai_provider("deterministic_mock").generate(_request())

    assert asdict(response.output) == {
        "kind": "synthetic_mock_proposal",
        "operation": "shipment_summary",
        "findings": (),
        "proposals": (),
        "authority": "advisory_only",
        "write_allowed": False,
        "send_allowed": False,
        "requires_human_review": True,
        "business_effects_applied": False,
        "deterministic": True,
    }
    with pytest.raises(FrozenInstanceError):
        response.output.write_allowed = True  # type: ignore[misc]
    with pytest.raises(AttributeError):
        response.output.findings.append("mutation")  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        response.output.proposals[0] = "mutation"  # type: ignore[index]
    json.dumps(asdict(response), allow_nan=False)


def test_generation_does_not_access_db_network_environment_or_config(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("external state was accessed")

    monkeypatch.setattr(db.session, "add", forbidden)
    monkeypatch.setattr(db.session, "commit", forbidden)
    monkeypatch.setattr(db.session, "execute", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(os.environ, "get", forbidden)

    response = build_ai_provider("deterministic_mock").generate(_request())
    assert response.output.business_effects_applied is False
