"""Regression for the Production ValidateOnly current-listener ownership defect."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "scripts/deploy/deploy_s7_rc_f11f2ab.ps1").read_text(encoding="utf-8")


def test_validateonly_accepts_governed_previous_venv_listener_not_future_runtime() -> None:
    previous = r"C:\1-webapp\forwarder-production\release-adcc5da-adr043"
    target = r"C:\1-webapp\forwarder-production\release-f11f2ab-s7"
    previous_python = previous + r"\.venv\Scripts\python.exe"
    target_python = target + r"\runtime\python.exe"
    # Exact Production baseline: previous listener active, candidate absent.
    command = previous_python + " -m waitress --listen=127.0.0.1:5101 backend.wsgi:app"
    assert previous_python in command and target_python not in command
    assert "if($PackagedRuntime){Join-Path $ExpectedRelease 'runtime\\python.exe'}else{Join-Path $ExpectedRelease '.venv\\Scripts\\python.exe'}" in SOURCE
    pre_mutation = SOURCE.index("Get-GovernedBackendListener $script:PreviousRelease")
    switching = SOURCE.index("Set-State 'SWITCHING'")
    assert pre_mutation < switching
    assert "Get-GovernedBackendListener $ExpectedRelease -PackagedRuntime:" in SOURCE


def test_previous_unknown_candidate_and_listener_topology_fail_closed_contracts_remain_present() -> None:
    for gate in (
        "backend listener identity is ambiguous",
        "governed backend listener is absent",
        "backend listener does not belong to expected release Python",
        "backend listener is not Waitress",
        "backend listener is not Forwarder WSGI",
        "previous backend listener did not stop",
        "new backend listener did not start",
        "rollback task reference mismatch",
    ):
        assert gate in SOURCE
