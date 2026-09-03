"""REQ-12 consecutive full deployment and rollback rehearsal gates."""
from pathlib import Path

import pytest

from scripts.tests.test_req1_release_engineering_qualification import protected
from scripts.tests.test_s7_r2_deployment_orchestration import fixture, run


@pytest.mark.parametrize("rehearsal", range(1, 11))
def test_full_deployment_rehearsal(rehearsal: int, tmp_path: Path) -> None:
    fixture(tmp_path)
    result = run(tmp_path, "-Execute", "-ConfirmDeployment")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DEPLOYED_AND_VERIFIED" in result.stdout
    task = (tmp_path / "task.txt").read_text(encoding="utf-8")
    assert "runtime\\python.exe" in task and ".venv\\Scripts\\python.exe" not in task


@pytest.mark.parametrize("rehearsal", range(1, 11))
def test_rollback_rehearsal(rehearsal: int, tmp_path: Path) -> None:
    fixture(tmp_path)
    before = protected(tmp_path)
    result = run(tmp_path, "-Execute", "-ConfirmDeployment", "-SimulateVerificationFailure")
    assert result.returncode != 0
    assert "FAILED_AND_RECOVERED" in result.stdout
    assert protected(tmp_path) == before
    assert not (tmp_path / "production/release-f11f2ab-s7").exists()
