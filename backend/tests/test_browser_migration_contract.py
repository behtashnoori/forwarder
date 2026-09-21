from __future__ import annotations

from pathlib import Path

import pytest

from backend.migration_runtime import RevisionStatus
from scripts import browser_migration_contract as contract


EXPECTED_HEAD = "20260925_quote_communication"
STALE_HEAD = "20260918_customer_carrier_role"
ROOT = Path(__file__).resolve().parents[2]


def test_repository_head_is_the_browser_runner_target() -> None:
    assert contract.repository_head() == EXPECTED_HEAD
    runner = (ROOT / "scripts/run-shared-transport-e2e.ps1").read_text(encoding="utf-8")
    assert "browser_migration_contract repository-head" in runner
    assert "backend.migration_cli upgrade $repositoryHead --confirm" in runner
    assert "browser_migration_contract verify-database-head --expected $repositoryHead" in runner
    assert runner.index("verify-database-head") < runner.index("seed_shared_transport_e2e.py")
    assert "if ($MigrationBootstrapOnly)" in runner


def test_focused_f_selector_selects_only_carrier_lifecycle() -> None:
    runner = (ROOT / "scripts/run-shared-transport-e2e.ps1").read_text(encoding="utf-8")
    spec = (ROOT / "e2e/shared-transport.spec.ts").read_text(encoding="utf-8")

    assert "if ($Acceptance -eq 'F') { 'F-CARRIER -' }" in runner
    assert spec.count('test("F-CARRIER - carrier lifecycle"') == 1
    assert 'test("F - shipment list route contract"' in spec
    assert "F-CARRIER -" not in 'F - shipment list route contract'


def test_personal_analytics_mode_uses_canonical_disposable_contract() -> None:
    runner = (ROOT / "scripts/run-shared-transport-e2e.ps1").read_text(encoding="utf-8")

    assert "[switch]$PersonalAnalytics" in runner
    assert "Qualification modes are mutually exclusive" in runner
    assert "forwarder_integrated_cert_$($databaseMode)_$runId" in runner
    assert "browser_migration_contract repository-head" in runner
    assert runner.index("verify-database-head") < runner.index("seed_personal_analytics_e2e.py")
    assert "e2e/qualification.spec.ts" in runner
    assert "finally {" in runner
    assert "drop disposable database" in runner


def test_stale_target_is_rejected_before_database_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(contract, "repository_head", lambda: EXPECTED_HEAD)

    with pytest.raises(contract.BrowserMigrationContractError, match="not the repository"):
        contract.verify_database_head(STALE_HEAD)


def test_multiple_repository_heads_fail_closed() -> None:
    with pytest.raises(contract.BrowserMigrationContractError, match="exactly one"):
        contract.require_single_head((EXPECTED_HEAD, "parallel_head"))


def test_database_revision_mismatch_blocks_qualification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.migration_runtime as runtime

    monkeypatch.setattr(contract, "repository_head", lambda: EXPECTED_HEAD)
    monkeypatch.setattr(
        runtime,
        "database_url",
        lambda: "sqlite://",
    )
    monkeypatch.setattr(
        runtime,
        "revision_status",
        lambda _url: RevisionStatus(current=(STALE_HEAD,), heads=(EXPECTED_HEAD,)),
    )

    with pytest.raises(contract.BrowserMigrationContractError, match="does not exactly match"):
        contract.verify_database_head(EXPECTED_HEAD)
