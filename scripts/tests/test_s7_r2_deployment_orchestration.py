"""Local filesystem orchestration tests for the governed S7-R2 PowerShell entrypoint."""

import shutil
import subprocess
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "deploy" / "deploy_s7_rc_f11f2ab.ps1"
ARTIFACT_ROOT = ROOT.parent / "release-candidates" / "S7-RC-f11f2ab"
ARTIFACT = ARTIFACT_ROOT / "Forwarder-S7-RC-f11f2ab.zip"
SIDECAR = ARTIFACT_ROOT / "Forwarder-S7-RC-f11f2ab.zip.manifest.json"


def pwsh():
    return shutil.which("powershell")


def fixture(root: Path, database_url="postgresql+psycopg2://user:secret@127.0.0.1:5432/forwarder_prod_20260728_161711", *, quoted=False, crlf=False):
    production = root / "production"
    previous = production / "release-adcc5da-adr043"
    (previous / "dist").mkdir(parents=True)
    (previous / "dist" / "index.html").write_text("previous", encoding="utf-8")
    runtime = root / "runtime"
    runtime.mkdir()
    original = (
        f"DATABASE_URL={database_url}\n"
        "JWT_SECRET_KEY=redacted\n"
        "CORS_ALLOW_ALL_ORIGINS=false\n"
        "CORS_ORIGINS=https://server.logisticmarket.ir\n"
        "CORS_ORIGIN=https://server.logisticmarket.ir\n"
    )
    if quoted:
        original=original.replace(f"DATABASE_URL={database_url}",f'DATABASE_URL="  {database_url}  "')
    (runtime / "production.env").write_text(original, encoding="utf-8", newline="\r\n" if crlf else None)
    (runtime / "phase1b_production_cutover_runtime.py").write_text("# fixture", encoding="utf-8")
    (runtime / "backend-production.log").write_text("HISTORICAL_FAILURE_MUST_NOT_BE_CAPTURED\n", encoding="utf-8")
    (root / "task.txt").write_text(str(previous), encoding="utf-8")
    (root / "iis.txt").write_text(str(previous / "dist"), encoding="utf-8")
    (root / "health.txt").write_text("200", encoding="utf-8")
    (root / "cors.txt").write_text("https://samand.forwarderet.ir", encoding="utf-8")
    (root / "preflight.txt").write_text("https://samand.forwarderet.ir", encoding="utf-8")
    (root / "host.txt").write_text("SRV8756807400", encoding="utf-8")
    (root / "admin.txt").write_text("yes", encoding="utf-8")
    (root / "task-metadata.txt").write_text("Forwarder Backend Production", encoding="utf-8")
    (root / "iis-state.txt").write_text("Started", encoding="utf-8")
    (root / "iis-bindings.txt").write_text("http,https", encoding="utf-8")
    (root / "listener.txt").write_text("127.0.0.1:5101", encoding="utf-8")
    (root / "current-health.txt").write_text("200", encoding="utf-8")
    (root / "disk-gb.txt").write_text("10", encoding="utf-8")
    (root / "current-cors.txt").write_text("LEGACY_TRANSITION_EXPECTED", encoding="utf-8")
    (root / "target-cors.txt").write_text("https://samand.forwarderet.ir", encoding="utf-8")
    (root / "unknown-origin.txt").write_text("REJECTED", encoding="utf-8")
    (root / "database.txt").write_text(
        "forwarder_prod_20260728_161711|20260907_direct_shipment_responsibility",
        encoding="utf-8",
    )
    (root / "expected-production-baseline.json").write_text(json.dumps({
        "database": "forwarder_prod_20260728_161711",
        "alembic_head": "20260907_direct_shipment_responsibility",
    }), encoding="utf-8")
    staging = root / "staging"
    staging.mkdir()
    shutil.copy2(ARTIFACT, staging / ARTIFACT.name)
    shutil.copy2(SIDECAR, staging / SIDECAR.name)
    return original


def run(root: Path, *args: str):
    return subprocess.run(
        [pwsh(), "-NoProfile", "-File", str(SCRIPT), "-SimulationRoot", str(root),
         "-BaselinePath", str(root / "expected-production-baseline.json"), *args],
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_validate_only_performs_zero_mutation(tmp_path):
    original = fixture(tmp_path)
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ABORTED_BEFORE_MUTATION" in result.stdout
    assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original
    assert not (tmp_path / "production" / "release-f11f2ab-s7").exists()
    assert (tmp_path / "task.txt").read_text(encoding="utf-8").endswith("release-adcc5da-adr043")
    assert "redacted" not in result.stdout + result.stderr


def test_entrypoint_has_no_database_mutation_or_binding_mutation_path():
    source = SCRIPT.read_text(encoding="utf-8").lower()
    forbidden = ("alembic upgrade", "alembic downgrade", "remove-webbinding", "set-webbinding")
    assert not any(token in source for token in forbidden)
    assert "begin transaction read only" in source


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_bad_artifact_aborts_before_mutation(tmp_path):
    original = fixture(tmp_path)
    with (tmp_path / "staging" / ARTIFACT.name).open("ab") as handle:
        handle.write(b"tamper")
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode != 0
    assert "ABORTED_BEFORE_MUTATION" in result.stdout
    assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original
    assert not (tmp_path / "production" / "release-f11f2ab-s7").exists()


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_bad_manifest_and_wrong_host_abort_before_mutation(tmp_path):
    original = fixture(tmp_path)
    (tmp_path / "staging" / SIDECAR.name).write_text("{}", encoding="utf-8")
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode != 0 and "ABORTED_BEFORE_MUTATION" in result.stdout
    assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original
    fixture(tmp_path / "host-case")
    (tmp_path / "host-case" / "host.txt").write_text("not-production", encoding="utf-8")
    result = run(tmp_path / "host-case", "-ValidateOnly")
    assert result.returncode != 0 and "ABORTED_BEFORE_MUTATION" in result.stdout


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_migration_identity_mismatch_aborts_before_mutation(tmp_path):
    original = fixture(tmp_path)
    (tmp_path / "database.txt").write_text("wrong|wrong", encoding="utf-8")
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode != 0
    assert "ABORTED_BEFORE_MUTATION" in result.stdout
    assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
@pytest.mark.parametrize("database_url", [
    "postgresql://user:secret@127.0.0.1:5432/forwarder_prod_20260728_161711",
    "postgresql+psycopg2://user:p%40ss%3Aword@127.0.0.1:5432/forwarder_prod_20260728_161711",
])
def test_supported_sqlalchemy_postgresql_urls_are_safe_and_accepted(tmp_path, database_url):
    fixture(tmp_path, database_url, quoted=True, crlf=True)
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DATABASE_ENGINE=POSTGRESQL" in result.stdout
    assert "secret" not in result.stdout + result.stderr and "p%40ss%3Aword" not in result.stdout + result.stderr


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
@pytest.mark.parametrize("database_url", ["mysql://u:secret@host/db", "sqlite:///tmp.db", "mssql://u:secret@host/db", "postgresql+unknown://u:secret@host/db", "not-a-url", ""])
def test_unsupported_or_malformed_database_urls_fail_closed_without_secret(tmp_path, database_url):
    fixture(tmp_path, database_url)
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode != 0 and "ABORTED_BEFORE_MUTATION" in result.stdout
    if database_url:
        assert database_url not in result.stdout + result.stderr


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
@pytest.mark.parametrize("identity", [
    "wrong_database|20260907_direct_shipment_responsibility",
    "forwarder_prod_20260728_161711|wrong_head",
])
def test_database_and_alembic_identity_gates_abort_before_mutation(tmp_path, identity):
    original = fixture(tmp_path)
    (tmp_path / "database.txt").write_text(identity, encoding="utf-8")
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode != 0 and "ABORTED_BEFORE_MUTATION" in result.stdout
    assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
@pytest.mark.parametrize("problem", ["missing-release", "missing-task", "missing-iis", "invalid-config"])
def test_prerequisite_and_target_config_gates_abort_before_mutation(tmp_path, problem):
    original = fixture(tmp_path)
    if problem == "missing-release":
        shutil.rmtree(tmp_path / "production" / "release-adcc5da-adr043")
    elif problem == "missing-task":
        (tmp_path / "task.txt").write_text("wrong", encoding="utf-8")
    elif problem == "missing-iis":
        (tmp_path / "iis.txt").write_text("wrong", encoding="utf-8")
    else:
        (tmp_path / "runtime" / "production.env").write_text("DATABASE_URL=x\n", encoding="utf-8")
    result = run(tmp_path, "-ValidateOnly")
    assert result.returncode != 0 and "ABORTED_BEFORE_MUTATION" in result.stdout
    if problem != "invalid-config":
        assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_simulated_transaction_stages_switches_and_verifies(tmp_path):
    fixture(tmp_path)
    result = run(tmp_path, "-Execute", "-ConfirmDeployment")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DEPLOYED_AND_VERIFIED" in result.stdout
    target = tmp_path / "production" / "release-f11f2ab-s7"
    assert (target / "dist" / "index.html").exists()
    updated = (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8")
    assert "CORS_ORIGINS=https://samand.forwarderet.ir" in updated
    assert "CORS_ALLOW_ALL_ORIGINS=0" in updated
    assert (tmp_path / "task.txt").read_text(encoding="utf-8") == str(target)
    assert (tmp_path / "iis.txt").read_text(encoding="utf-8") == str(target / "dist")


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_verification_failure_rolls_back_exact_previous_state(tmp_path):
    original = fixture(tmp_path)
    result = run(tmp_path, "-Execute", "-ConfirmDeployment", "-SimulateVerificationFailure")
    assert result.returncode != 0
    assert "FAILED_AND_RECOVERED" in result.stdout
    assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original
    assert (tmp_path / "task.txt").read_text(encoding="utf-8").endswith("release-adcc5da-adr043")
    assert (tmp_path / "iis.txt").read_text(encoding="utf-8").endswith("release-adcc5da-adr043\\dist")


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_staging_failure_rolls_back_without_changing_active_identities(tmp_path):
    original = fixture(tmp_path)
    result = run(tmp_path, "-Execute", "-ConfirmDeployment", "-SimulateStagingFailure")
    assert result.returncode != 0 and "FAILED_AND_RECOVERED" in result.stdout
    assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original
    assert (tmp_path / "task.txt").read_text(encoding="utf-8").endswith("release-adcc5da-adr043")


@pytest.mark.skipif(not pwsh() or not ARTIFACT.exists(), reason="PowerShell or governed local artifact unavailable")
def test_start_failure_captures_attempt_scoped_evidence_before_rollback(tmp_path):
    original = fixture(tmp_path)
    result = run(tmp_path, "-Execute", "-ConfirmDeployment", "-SimulateStartupFailure")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "STARTUP_FAILURE_EVIDENCE=" in result.stdout
    reports = list(tmp_path.glob("startup-attempt-*.json"))
    assert len(reports) == 1
    try:
        evidence = json.loads(reports[0].read_text(encoding="utf-8-sig"))
        assert evidence["candidate_id"] == "S7-RC-f11f2ab"
        assert evidence["target_release"].endswith("release-f11f2ab-s7")
        assert evidence["task_start_result"] == "PASS"
        assert evidence["listener_observations"]
        assert evidence["candidate_process_observations"] == ["SIMULATION_NO_CANDIDATE_PROCESS"]
        assert "CURRENT_ATTEMPT_IMPORT_ERROR" in evidence["candidate_new_log"]
        assert "HISTORICAL_FAILURE" not in evidence["candidate_new_log"]
        assert evidence["failure_reason"].endswith("new backend listener did not start")
        assert "FAILED_AND_RECOVERED" in result.stdout
        assert (tmp_path / "runtime" / "production.env").read_text(encoding="utf-8") == original
    finally:
        for report in reports:
            report.unlink()
