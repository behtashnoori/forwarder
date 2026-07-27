"""Focused tests for safe backend server binding."""
from __future__ import annotations

import pytest

from backend.config import resolve_server_host


@pytest.mark.parametrize(
    ("configured_host", "expected"),
    [
        ("localhost", "127.0.0.1"),
        ("LOCALHOST", "127.0.0.1"),
        ("127.0.0.1", "127.0.0.1"),
        ("0.0.0.0", "0.0.0.0"),
    ],
)
def test_explicit_bind_addresses_are_resolved_without_widening(
    configured_host: str,
    expected: str,
) -> None:
    assert resolve_server_host(configured_host, environment="uat") == expected


def test_uat_profile_defaults_to_loopback() -> None:
    assert resolve_server_host(None, environment="uat") == "127.0.0.1"


@pytest.mark.parametrize("environment", ["development", "production", "prod"])
def test_non_uat_profiles_retain_historical_wildcard_default(environment: str) -> None:
    assert resolve_server_host(None, environment=environment) == "0.0.0.0"


@pytest.mark.parametrize(
    "configured_host",
    ["", "   ", "http://localhost", "127.0.0.1:5001", "-invalid", "bad host"],
)
def test_malformed_host_fails_closed(configured_host: str) -> None:
    with pytest.raises(RuntimeError, match="HOST/FLASK_RUN_HOST"):
        resolve_server_host(configured_host, environment="uat")
