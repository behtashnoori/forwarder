"""Vendor-neutral, side-effect-free provider boundary for safe prototypes.

This module does not connect to an AI vendor.  The default provider is disabled;
the only executable implementation is an explicitly selected deterministic mock.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Any, Protocol, runtime_checkable


DEFAULT_PROVIDER_MODE = "disabled"
DETERMINISTIC_MOCK_MODE = "deterministic_mock"
PROVIDER_INTERFACE_VERSION = "1.0"
FINGERPRINT_DOMAIN = b"forwarder:ai-provider-request:v1\x00"
MAX_CONTEXT_DEPTH = 32
MAX_CONTEXT_ITEMS = 10_000
MAX_CANONICAL_REQUEST_BYTES = 1_000_000
_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$")


class AIProviderError(Exception):
    """Base error for the vendor-neutral provider boundary."""


class AIProviderDisabledError(AIProviderError):
    """Raised when generation is attempted while the provider is disabled."""


class AIProviderUnsupportedModeError(AIProviderError):
    """Raised when a caller requests a provider mode that is not implemented."""


class AIProviderInvalidRequestError(AIProviderError):
    """Raised when a request cannot be represented as canonical JSON."""


@dataclass(frozen=True, init=False)
class AIProviderRequest:
    """Immutable provider-neutral request with a canonical context snapshot."""

    operation: str
    output_schema_version: str
    interface_version: str
    _canonical_context: str = field(repr=False)

    def __init__(
        self,
        operation: str,
        context: dict[str, Any],
        output_schema_version: str = "1.0",
    ) -> None:
        _validate_request_parts(operation, context, output_schema_version)
        canonical_context = _canonicalize_context(context)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "output_schema_version", output_schema_version)
        object.__setattr__(self, "interface_version", PROVIDER_INTERFACE_VERSION)
        object.__setattr__(self, "_canonical_context", canonical_context)

    @property
    def context(self) -> dict[str, Any]:
        """Return a fresh JSON copy; caller mutation cannot alter the request."""
        return json.loads(self._canonical_context)


@dataclass(frozen=True)
class AIProviderOutput:
    """Immutable deterministic mock output with no business authority."""

    kind: str
    operation: str
    findings: tuple[Any, ...]
    proposals: tuple[Any, ...]
    authority: str
    write_allowed: bool
    send_allowed: bool
    requires_human_review: bool
    business_effects_applied: bool
    deterministic: bool


@dataclass(frozen=True)
class AIProviderResponse:
    """A deterministic provider-neutral response envelope."""

    provider: str
    mode: str
    interface_version: str
    request_fingerprint: str
    output_schema_version: str
    output: AIProviderOutput


@runtime_checkable
class AIProvider(Protocol):
    """Interface that future reviewed provider adapters must implement."""

    mode: str

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        """Generate a proposal response without applying business effects."""


@dataclass(frozen=True)
class DisabledAIProvider:
    """Fail-safe default that rejects every generation attempt."""

    mode: str = DEFAULT_PROVIDER_MODE

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        # Disabled mode must not inspect, fingerprint, copy, or otherwise process
        # context data.  It rejects every request at the boundary.
        raise AIProviderDisabledError("AI provider execution is disabled")


@dataclass(frozen=True)
class DeterministicMockAIProvider:
    """Offline mock for synthetic tests; performs no inference or I/O."""

    mode: str = DETERMINISTIC_MOCK_MODE

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        canonical_request = canonicalize_request(request)
        fingerprint = _fingerprint_canonical_request(canonical_request)
        return AIProviderResponse(
            provider="deterministic_mock",
            mode=self.mode,
            interface_version=PROVIDER_INTERFACE_VERSION,
            request_fingerprint=fingerprint,
            output_schema_version=request.output_schema_version,
            output=AIProviderOutput(
                kind="synthetic_mock_proposal",
                operation=request.operation,
                findings=(),
                proposals=(),
                authority="advisory_only",
                write_allowed=False,
                send_allowed=False,
                requires_human_review=True,
                business_effects_applied=False,
                deterministic=True,
            ),
        )


def build_ai_provider(mode: str = DEFAULT_PROVIDER_MODE) -> AIProvider:
    """Build an allow-listed provider; omitted mode always fails closed."""
    if not isinstance(mode, str):
        raise AIProviderUnsupportedModeError("Unsupported AI provider mode")
    if mode == DEFAULT_PROVIDER_MODE:
        return DisabledAIProvider()
    if mode == DETERMINISTIC_MOCK_MODE:
        return DeterministicMockAIProvider()
    raise AIProviderUnsupportedModeError("Unsupported AI provider mode")


def canonicalize_request(request: AIProviderRequest) -> str:
    """Validate and serialize a request into stable canonical JSON."""
    validate_request(request)
    payload = {
        "context": json.loads(request._canonical_context),
        "interface_version": request.interface_version,
        "operation": request.operation,
        "output_schema_version": request.output_schema_version,
    }
    try:
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise AIProviderInvalidRequestError(
            "AI provider request must contain only strict JSON values"
        ) from exc
    if len(canonical.encode("utf-8")) > MAX_CANONICAL_REQUEST_BYTES:
        raise AIProviderInvalidRequestError("AI provider request exceeds the size limit")
    return canonical


def request_fingerprint(request: AIProviderRequest) -> str:
    """Return the stable SHA-256 fingerprint used by provider responses."""
    return _fingerprint_canonical_request(canonicalize_request(request))


def validate_request(request: AIProviderRequest) -> None:
    """Reject objects that do not satisfy the immutable request contract."""
    if not isinstance(request, AIProviderRequest):
        raise AIProviderInvalidRequestError("request must be an AIProviderRequest")
    if request.interface_version != PROVIDER_INTERFACE_VERSION:
        raise AIProviderInvalidRequestError("provider interface version is invalid")
    _validate_identifier_fields(request.operation, request.output_schema_version)
    if not isinstance(request._canonical_context, str):
        raise AIProviderInvalidRequestError("canonical context is invalid")
    try:
        context = json.loads(request._canonical_context)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AIProviderInvalidRequestError("canonical context is invalid") from exc
    if not isinstance(context, dict):
        raise AIProviderInvalidRequestError("canonical context is invalid")


def _validate_request_parts(
    operation: Any,
    context: Any,
    output_schema_version: Any,
) -> None:
    _validate_identifier_fields(operation, output_schema_version)
    if not isinstance(context, dict):
        raise AIProviderInvalidRequestError("context must be a JSON object")
    state = {"items": 0}
    _validate_json_value(
        context,
        path="context",
        depth=0,
        ancestors=set(),
        state=state,
    )


def _validate_identifier_fields(operation: Any, output_schema_version: Any) -> None:
    if not isinstance(operation, str) or not _IDENTIFIER_PATTERN.fullmatch(operation):
        raise AIProviderInvalidRequestError("operation must be a valid identifier")
    if not isinstance(
        output_schema_version, str
    ) or not _VERSION_PATTERN.fullmatch(output_schema_version):
        raise AIProviderInvalidRequestError("output_schema_version must be valid")


def _canonicalize_context(context: dict[str, Any]) -> str:
    try:
        canonical = json.dumps(
            context,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise AIProviderInvalidRequestError(
            "context must contain only strict JSON values"
        ) from exc
    if len(canonical.encode("utf-8")) > MAX_CANONICAL_REQUEST_BYTES:
        raise AIProviderInvalidRequestError("AI provider request exceeds the size limit")
    return canonical


def _validate_json_value(
    value: Any,
    *,
    path: str,
    depth: int,
    ancestors: set[int],
    state: dict[str, int],
) -> None:
    if depth > MAX_CONTEXT_DEPTH:
        raise AIProviderInvalidRequestError("context exceeds the nesting limit")
    state["items"] += 1
    if state["items"] > MAX_CONTEXT_ITEMS:
        raise AIProviderInvalidRequestError("context exceeds the item limit")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise AIProviderInvalidRequestError("context contains a non-finite number")
    if isinstance(value, (dict, list)):
        identity = id(value)
        if identity in ancestors:
            raise AIProviderInvalidRequestError("context contains a cycle")
        ancestors.add(identity)
        try:
            if isinstance(value, dict):
                for key, item in value.items():
                    if not isinstance(key, str):
                        raise AIProviderInvalidRequestError(
                            "context contains a non-string key"
                        )
                    _validate_json_value(
                        item,
                        path=f"{path}.{key}",
                        depth=depth + 1,
                        ancestors=ancestors,
                        state=state,
                    )
            else:
                for index, item in enumerate(value):
                    _validate_json_value(
                        item,
                        path=f"{path}[{index}]",
                        depth=depth + 1,
                        ancestors=ancestors,
                        state=state,
                    )
        finally:
            ancestors.remove(identity)
        return
    raise AIProviderInvalidRequestError("context contains a non-JSON value")


def _fingerprint_canonical_request(canonical_request: str) -> str:
    payload = FINGERPRINT_DOMAIN + canonical_request.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
