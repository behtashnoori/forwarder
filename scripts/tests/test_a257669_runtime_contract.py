"""Permanent regression gate for governed Windows runtime provisioning."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = (ROOT / "scripts/deploy/deploy_a257669_r4.ps1").read_text(encoding="utf-8")
BUILD = (ROOT / "scripts/deploy/build_a257669_runtime_deployment_package.py").read_text(encoding="utf-8")


def test_r4_requires_an_immutable_separate_runtime_and_manifest():
    for token in ("RuntimeZip", "RuntimeManifest", "runtime_id", "artifact_sha256", "runtime\\python.exe"):
        assert token in DEPLOY + BUILD


def test_r4_fails_closed_and_preserves_the_no_downgrade_policy():
    assert "-Execute -ConfirmDeployment" in DEPLOY
    assert "PRECHECK_COMPLETE" in DEPLOY and "READY_FOR_FIRST_MUTATION" in DEPLOY
    assert "ROLLBACK=PREVIOUS_APPLICATION_RUNTIME;DB=UPGRADED_NO_DOWNGRADE" in DEPLOY
    assert "DB predecessor Alembic mismatch" in DEPLOY
    assert "taskkill /IM python.exe" not in DEPLOY
    assert "Stop-Process -Id" in DEPLOY


def test_r4_contract_uses_the_candidate_runtime_for_migration_and_task():
    assert "& $python -m alembic upgrade $TargetHead" in DEPLOY
    assert "$newXml -match [regex]::Escape($python)" in DEPLOY
    assert "Listener $target" in DEPLOY
