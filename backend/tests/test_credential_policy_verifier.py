"""Tests for the tracked credential-policy verifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PATH = Path(__file__).resolve().parents[2] / "scripts" / "verify_credential_policy.py"
SPEC = importlib.util.spec_from_file_location("credential_policy_verifier", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_current_tracked_tree_has_no_executable_default_credentials():
    assert MODULE.findings() == []
