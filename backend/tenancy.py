"""Mechanically validated tenant-ownership architecture contract.

MT-0 deliberately does not resolve tenant context for requests or scope ORM
queries.  This module only loads the checked-in ownership registry and offers
small fail-closed primitives that later slices can reuse.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping


INVENTORY_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "architecture"
    / "tenant-ownership-inventory.yaml"
)


class OwnershipScope(str, Enum):
    TENANT_OWNED_DIRECT = "TENANT_OWNED_DIRECT"
    TENANT_OWNED_INDIRECT = "TENANT_OWNED_INDIRECT"
    PLATFORM_SCOPED = "PLATFORM_SCOPED"
    PUBLIC_CAPABILITY_SCOPED = "PUBLIC_CAPABILITY_SCOPED"
    LEGACY_AMBIGUOUS = "LEGACY_AMBIGUOUS"


class TenantContractError(ValueError):
    """Raised when tenant ownership is absent, ambiguous, or inconsistent."""


@dataclass(frozen=True, slots=True)
class TenantContext:
    """An immutable, already-authorized organization identity.

    Constructing this value does not authorize a caller.  MT-2 will establish
    it from server-validated membership; accepting a client-supplied ID is
    forbidden by the architecture contract.
    """

    organization_id: int

    def __post_init__(self) -> None:
        if isinstance(self.organization_id, bool) or self.organization_id <= 0:
            raise TenantContractError("tenant context requires a positive organization_id")


def require_tenant_context(context: TenantContext | None) -> TenantContext:
    if context is None:
        raise TenantContractError("tenant-owned operation requires tenant context")
    return context


def assert_same_tenant(
    context: TenantContext | None,
    resource_organization_id: int | None,
    *,
    resource: str = "resource",
) -> None:
    """Fail closed when resource ownership is absent or differs from context."""

    tenant = require_tenant_context(context)
    if resource_organization_id is None:
        raise TenantContractError(f"{resource} has ambiguous tenant ownership")
    if tenant.organization_id != resource_organization_id:
        raise TenantContractError(f"{resource} belongs to a different tenant")


def load_ownership_inventory(path: Path = INVENTORY_PATH) -> dict[str, Any]:
    """Load the inventory (JSON syntax, which is valid YAML 1.2)."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise TenantContractError(f"duplicate ownership inventory key: {key}")
            result[key] = value
        return result

    with path.open(encoding="utf-8") as handle:
        value = json.load(handle, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise TenantContractError("ownership inventory root must be an object")
    return value


def validate_inventory(inventory: Mapping[str, Any]) -> list[str]:
    """Return deterministic contract-schema errors without importing the app."""

    errors: list[str] = []
    entities = inventory.get("entities")
    if not isinstance(entities, dict):
        return ["entities must be an object"]
    known = {scope.value for scope in OwnershipScope}
    for name, entry in sorted(entities.items()):
        if not isinstance(entry, dict):
            errors.append(f"{name}: entry must be an object")
            continue
        scope = entry.get("scope")
        if scope not in known:
            errors.append(f"{name}: unknown ownership scope {scope!r}")
            continue
        if not entry.get("kind"):
            errors.append(f"{name}: kind is required")
        if scope == OwnershipScope.TENANT_OWNED_DIRECT.value and not entry.get("tenant_key"):
            errors.append(f"{name}: direct ownership requires tenant_key")
        if scope == OwnershipScope.TENANT_OWNED_INDIRECT.value and not entry.get("owner_path"):
            errors.append(f"{name}: indirect ownership requires owner_path")
        if scope == OwnershipScope.PLATFORM_SCOPED.value and not entry.get("rationale"):
            errors.append(f"{name}: platform scope requires allowlist rationale")
        if scope == OwnershipScope.PUBLIC_CAPABILITY_SCOPED.value:
            if not entry.get("constraint") or not entry.get("underlying_resource_scope"):
                errors.append(f"{name}: public capability requires constraint and underlying scope")
        if scope == OwnershipScope.LEGACY_AMBIGUOUS.value:
            required = ("owner_evidence", "risk", "ambiguity_reason", "future_slice", "mt0_policy")
            missing = [field for field in required if not entry.get(field)]
            if missing:
                errors.append(f"{name}: ambiguous entry missing {', '.join(missing)}")
    return errors
