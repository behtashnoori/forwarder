"""Canonical, typed identities shared by ownership analysis and enforcement."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping
from uuid import UUID


IDENTITY_VERSION = 1
MAX_RESOURCE_TYPE_LENGTH = 80
MAX_COMPONENT_NAME_LENGTH = 80
MAX_STRING_VALUE_LENGTH = 1024
KEY_KINDS = frozenset({"INTEGER", "STRING", "UUID"})


class InvalidResourceIdentity(ValueError):
    """Raised when an identity is ambiguous, lossy, or non-canonical."""


@dataclass(frozen=True)
class IdentityComponent:
    name: str
    kind: str
    value: str

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > MAX_COMPONENT_NAME_LENGTH:
            raise InvalidResourceIdentity("invalid identity component name")
        if self.kind not in KEY_KINDS:
            raise InvalidResourceIdentity(f"unsupported identity kind: {self.kind!r}")
        canonical = _canonical_value(self.kind, self.value)
        if canonical != self.value:
            raise InvalidResourceIdentity("identity component value is not canonical")

    def as_json(self) -> dict[str, str]:
        return {"kind": self.kind, "name": self.name, "value": self.value}


@dataclass(frozen=True)
class ResourceIdentity:
    resource_type: str
    components: tuple[IdentityComponent, ...]

    def __post_init__(self) -> None:
        if (
            not self.resource_type
            or len(self.resource_type) > MAX_RESOURCE_TYPE_LENGTH
            or self.resource_type.strip() != self.resource_type
        ):
            raise InvalidResourceIdentity("invalid resource type")
        if not self.components:
            raise InvalidResourceIdentity("an identity requires at least one component")
        names = [component.name for component in self.components]
        if len(names) != len(set(names)):
            raise InvalidResourceIdentity("duplicate identity component name")

    @property
    def key_payload(self) -> str:
        value = {
            "components": [component.as_json() for component in self.components],
            "version": IDENTITY_VERSION,
        }
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @property
    def key_hash(self) -> str:
        envelope = json.dumps(
            {"key": json.loads(self.key_payload), "resource_type": self.resource_type},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(envelope.encode("utf-8")).hexdigest()

    @property
    def scalar_integer(self) -> int | None:
        if len(self.components) == 1 and self.components[0].kind == "INTEGER":
            return int(self.components[0].value)
        return None

    def as_json(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_key": json.loads(self.key_payload),
            "resource_key_hash": self.key_hash,
        }

    @classmethod
    def from_payload(cls, resource_type: str, payload: str) -> "ResourceIdentity":
        try:
            parsed = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise InvalidResourceIdentity("resource key is not valid JSON") from exc
        if not isinstance(parsed, dict) or set(parsed) != {"components", "version"}:
            raise InvalidResourceIdentity("resource key has an unknown shape")
        if parsed["version"] != IDENTITY_VERSION or not isinstance(
            parsed["components"], list
        ):
            raise InvalidResourceIdentity("unsupported resource key version")
        components = []
        for item in parsed["components"]:
            if not isinstance(item, dict) or set(item) != {"kind", "name", "value"}:
                raise InvalidResourceIdentity("invalid identity component shape")
            if not all(isinstance(item[field], str) for field in item):
                raise InvalidResourceIdentity("identity components must contain strings")
            components.append(IdentityComponent(item["name"], item["kind"], item["value"]))
        identity = cls(resource_type, tuple(components))
        if identity.key_payload != payload:
            raise InvalidResourceIdentity("resource key JSON is not canonical")
        return identity


def _canonical_value(kind: str, value: Any) -> str:
    if kind == "INTEGER":
        if isinstance(value, bool):
            raise InvalidResourceIdentity("booleans are not integer identities")
        if isinstance(value, int):
            return str(value)
        if not isinstance(value, str) or not value:
            raise InvalidResourceIdentity("integer identity must be an integer or decimal string")
        if value == "0":
            return value
        if value.startswith("-"):
            digits = value[1:]
            if not digits or digits.startswith("0") or not digits.isascii() or not digits.isdigit():
                raise InvalidResourceIdentity("integer identity is not canonical")
            return value
        if value.startswith("0") or not value.isascii() or not value.isdigit():
            raise InvalidResourceIdentity("integer identity is not canonical")
        return value
    if kind == "STRING":
        if not isinstance(value, str) or len(value) > MAX_STRING_VALUE_LENGTH:
            raise InvalidResourceIdentity("string identity is invalid or too long")
        return value
    if kind == "UUID":
        if not isinstance(value, (str, UUID)):
            raise InvalidResourceIdentity("UUID identity must be text or UUID")
        try:
            return str(UUID(str(value)))
        except ValueError as exc:
            raise InvalidResourceIdentity("invalid UUID identity") from exc
    raise InvalidResourceIdentity(f"unsupported identity kind: {kind!r}")


def component(name: str, kind: str, value: Any) -> IdentityComponent:
    """Build a component while applying its lossless canonical conversion."""

    return IdentityComponent(name=name, kind=kind, value=_canonical_value(kind, value))


def scalar_identity(
    resource_type: str, value: Any, *, kind: str = "INTEGER", name: str = "id"
) -> ResourceIdentity:
    return ResourceIdentity(resource_type, (component(name, kind, value),))


def composite_identity(
    resource_type: str,
    values: Iterable[tuple[str, str, Any]] | Mapping[str, tuple[str, Any]],
) -> ResourceIdentity:
    """Build an ordered typed composite; mappings use stable name ordering."""

    items = (
        ((name, kind, value) for name, (kind, value) in sorted(values.items()))
        if isinstance(values, Mapping)
        else values
    )
    return ResourceIdentity(
        resource_type,
        tuple(component(name, kind, value) for name, kind, value in items),
    )


def project_party_identity(project_id: int, customer_id: int, party_role: str) -> ResourceIdentity:
    """The canonical identity for the sole ambiguous composite-key resource."""

    return composite_identity(
        "project_party_relationship",
        (
            ("project_id", "INTEGER", project_id),
            ("customer_id", "INTEGER", customer_id),
            ("party_role", "STRING", party_role),
        ),
    )


__all__ = [
    "IDENTITY_VERSION",
    "IdentityComponent",
    "InvalidResourceIdentity",
    "ResourceIdentity",
    "component",
    "composite_identity",
    "project_party_identity",
    "scalar_identity",
]
