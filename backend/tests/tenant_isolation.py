"""Reusable two-tenant behavior contract for future MT resource adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TenantPair:
    actor_a: Any
    actor_b: Any
    resource_a: Any
    resource_b: Any


class TenantResourceAdapter(Protocol):
    """Small adapter surface; unsupported operations must be explicit in tests."""

    def read(self, actor: Any, resource: Any) -> Any: ...
    def discover(self, actor: Any, resource: Any) -> bool: ...
    def update(self, actor: Any, resource: Any) -> Any: ...
    def delete(self, actor: Any, resource: Any) -> Any: ...
    def reference(self, actor: Any, resource: Any) -> Any: ...


def assert_two_tenant_contract(adapter: TenantResourceAdapter, pair: TenantPair) -> None:
    """Baseline required by future resource-specific isolation tests.

    Adapters express denial by returning ``False`` from discovery and raising
    their stable domain/HTTP exception for forbidden cross-tenant operations.
    Resource tests remain responsible for asserting the exact non-disclosing
    status/error and that denied writes have no side effects.
    """

    assert adapter.read(pair.actor_a, pair.resource_a) is not None
    assert adapter.discover(pair.actor_a, pair.resource_a) is True
    assert adapter.discover(pair.actor_a, pair.resource_b) is False
    for operation in (adapter.read, adapter.update, adapter.delete, adapter.reference):
        try:
            operation(pair.actor_a, pair.resource_b)
        except Exception:  # the resource test asserts the concrete exception
            continue
        raise AssertionError(f"{operation.__name__} accepted a cross-tenant resource")
