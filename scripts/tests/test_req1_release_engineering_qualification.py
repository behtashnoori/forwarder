"""REQ-1 qualification of the actual packaged operator path under Windows PowerShell 5.1."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/deploy/build_d2_validation_package.py"
DEPLOY = ROOT / "scripts/deploy/deploy_s7_rc_f11f2ab.ps1"
WRAPPER = ROOT / "scripts/deploy/validate_forwarder_s7_rc_f11f2ab.ps1"
PACKAGE_ID = "D2-VALIDATION-S7-RC-f11f2ab-r3-final"
PS51 = shutil.which("powershell")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root: Path, database_url: str = "postgresql+psycopg2://user:p%40ss%3Aword@127.0.0.1:5432/forwarder_prod_20260728_161711") -> None:
    previous = root / "production/release-adcc5da-adr043"
    (previous / "dist").mkdir(parents=True)
    (previous / "dist/index.html").write_text("previous", encoding="utf-8")
    runtime = root / "runtime"
    runtime.mkdir()
    env = (f'\ufeff  DATABASE_URL = "  {database_url}  "\r\nJWT_SECRET_KEY=fake-only\r\n'
           "CORS_ALLOW_ALL_ORIGINS=false\r\nCORS_ORIGINS=https://server.logisticmarket.ir\r\n"
           "CORS_ORIGIN=https://server.logisticmarket.ir\r\nEMPTY_VALUE=\r\n")
    (runtime / "production.env").write_text(env, encoding="utf-8", newline="")
    (runtime / "phase1b_production_cutover_runtime.py").write_text("# fixture", encoding="utf-8")
    values = {
        "task.txt": f'{previous}\\.venv\\Scripts\\python.exe wrapper.py serve --repo {previous}', "iis.txt": str(previous / "dist"), "host.txt": "SRV8756807400",
        "admin.txt": "yes", "database.txt": "forwarder_prod_20260728_161711|20260907_direct_shipment_responsibility",
        "task-metadata.txt": "Forwarder Backend Production", "iis-state.txt": "Started", "iis-bindings.txt": "http,https",
        "listener.txt": "127.0.0.1:5101", "current-health.txt": "200", "disk-gb.txt": "10",
        "current-cors.txt": "LEGACY_TRANSITION_EXPECTED", "target-cors.txt": "https://samand.forwarderet.ir",
        "unknown-origin.txt": "REJECTED", "health.txt": "200", "cors.txt": "https://samand.forwarderet.ir",
        "preflight.txt": "https://samand.forwarderet.ir",
    }
    for name, value in values.items():
        (root / name).write_text(value, encoding="utf-8")
    (root / "iis-contract.json").write_text(json.dumps({
        "schema": "forwarder-req4a-iis-contract-v1", "module_available": "YES",
        "import_result": "PASS", "provider_available": "YES", "drive_available": "YES",
        "site_available": "YES", "physical_path_read": "PASS", "binding_read": "PASS",
        "result_shape": "VALID", "scheduled_tasks_available": "YES",
        "scheduled_task_available": "YES", "physical_path_shape": "SCALAR",
        "physical_path_records": [str(previous / "dist")],
    }), encoding="utf-8")
    staging = root / "staging"
    staging.mkdir()
    rc = ROOT.parent / "release-candidates/S7-RC-f11f2ab"
    for name in ("Forwarder-S7-RC-f11f2ab.zip", "Forwarder-S7-RC-f11f2ab.zip.manifest.json"):
        shutil.copy2(rc / name, staging / name)
    runtime_rc = ROOT.parent / "release-candidates"
    for name in ("Forwarder-Windows-Runtime-REQ12.zip", "Forwarder-Windows-Runtime-REQ12.zip.manifest.json"):
        shutil.copy2(runtime_rc / name, staging / name)


def build(path: Path) -> Path:
    subprocess.run([sys.executable, str(BUILDER), str(path), "qualification-commit"], check=True, capture_output=True, text=True)
    return path


def run_wrapper(package: Path, sim: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PS51, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                           str(package / "validate_forwarder_s7_rc_f11f2ab.ps1"), "-SimulationRoot", str(sim)],
                          capture_output=True, text=True, timeout=60)


def protected(root: Path) -> dict[str, str]:
    answer = {}
    for relative in ("runtime/production.env", "task.txt", "iis.txt", "database.txt"):
        path = root / relative
        answer[relative] = digest(path) if path.exists() else "ABSENT"
    answer["target"] = str((root / "production/release-f11f2ab-s7").exists())
    return answer


@pytest.mark.skipif(not PS51, reason="Windows PowerShell 5.1 unavailable")
def test_ps51_parser_and_automatic_variable_audit():
    for path in (DEPLOY, WRAPPER):
        escaped = str(path).replace("'", "''")
        command = f"$e=$null;$t=$null;[Management.Automation.Language.Parser]::ParseFile('{escaped}',[ref]$t,[ref]$e)|Out-Null;if($e.Count){{$e|% Message;exit 1}}"
        result = subprocess.run([PS51, "-NoProfile", "-Command", command], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    wrapper = WRAPPER.read_text(encoding="utf-8")
    deploy = DEPLOY.read_text(encoding="utf-8")
    assert "$args=" not in wrapper.lower()
    assert "Require ($map.Contains('DATABASE_URL'))" in deploy
    for unsafe in ("$Host=", "$Input=", "$Error=", "$PID=", "$HOME=", "$PWD=", "$Matches="):
        assert unsafe.lower() not in (wrapper + deploy).lower()


@pytest.mark.skipif(not PS51, reason="Windows PowerShell 5.1 unavailable")
def test_exact_packaged_operator_five_consecutive_go_and_zero_mutation(tmp_path):
    package = build(tmp_path / PACKAGE_ID)
    transitions = []
    for index in range(5):
        sim = tmp_path / f"success-{index}"
        fixture(sim)
        before = protected(sim)
        result = run_wrapper(package, sim)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "VALIDATION_RESULT=GO" in result.stdout
        assert "CURRENT_STATE_CAN_TRANSITION=YES" in result.stdout
        assert "TARGET_CONFIGURATION_VALID=YES" in result.stdout
        assert "MUTATION_BOUNDARY_REACHED" not in result.stdout
        assert protected(sim) == before
        transitions.append([line for line in result.stdout.splitlines() if line.startswith("STATE=")])
    assert all(item == transitions[0] for item in transitions)


@pytest.mark.skipif(not PS51, reason="Windows PowerShell 5.1 unavailable")
def test_failure_injection_matrix_is_fail_closed_and_zero_mutation(tmp_path):
    mutations = {
        "missing_application_artifact": lambda p, s: (p / "Forwarder-S7-RC-f11f2ab.zip").unlink(),
        "wrong_application_hash": lambda p, s: (p / "Forwarder-S7-RC-f11f2ab.zip").write_bytes(b"tampered"),
        "wrong_manifest_hash": lambda p, s: (p / "Forwarder-S7-RC-f11f2ab.zip.manifest.json").write_text("{}"),
        "missing_production_env": lambda p, s: (s / "runtime/production.env").unlink(),
        "empty_database_url": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=\nJWT_SECRET_KEY=x\n"),
        "malformed_database_url": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=not-a-url\nJWT_SECRET_KEY=x\n"),
        "unsupported_db_engine": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=mysql://u:p@h/db\nJWT_SECRET_KEY=x\n"),
        "unsupported_postgresql_driver": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=postgresql+asyncpg://u:p@h/db\nJWT_SECRET_KEY=x\n"),
        "db_connection_failure": lambda p, s: (s / "database.txt").unlink(),
        "wrong_db_identity": lambda p, s: (s / "database.txt").write_text("wrong|20260907_direct_shipment_responsibility"),
        "wrong_alembic_revision": lambda p, s: (s / "database.txt").write_text("forwarder_prod_20260728_161711|wrong"),
        "insufficient_disk": lambda p, s: (s / "disk-gb.txt").write_text("1"),
        "missing_expected_path": lambda p, s: shutil.rmtree(s / "production/release-adcc5da-adr043"),
        "wrong_task_identity": lambda p, s: (s / "task.txt").write_text("wrong"),
        "malformed_task_metadata": lambda p, s: (s / "task-metadata.txt").write_text("malformed"),
        "iis_mismatch": lambda p, s: (s / "iis.txt").write_text("wrong"),
        "invalid_canonical_cors_target": lambda p, s: (s / "target-cors.txt").write_text("http://bad"),
        "allow_all_cors": lambda p, s: (s / "current-cors.txt").write_text("ALLOW_ALL"),
        "conflicting_cors_values": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=postgresql://u:p@h/db\nDATABASE_URL=postgresql://u:p@h/db\nJWT_SECRET_KEY=x\n"),
        "unknown_origin_behavior": lambda p, s: (s / "unknown-origin.txt").write_text("ALLOWED"),
        "backend_listener_mismatch": lambda p, s: (s / "listener.txt").write_text("0.0.0.0:5101"),
        "health_failure": lambda p, s: (s / "current-health.txt").write_text("500"),
        "package_missing_deployment_script": lambda p, s: (p / "deploy_s7_rc_f11f2ab.ps1").unlink(),
        "stale_deployment_script_hash": lambda p, s: (p / "deploy_s7_rc_f11f2ab.ps1").write_text("# stale"),
        "malformed_json_manifest": lambda p, s: (p / "D2-package-manifest.json").write_text("{"),
        "permission_access_failure": lambda p, s: (s / "admin.txt").write_text("no"),
    }
    for name, mutate in mutations.items():
        case = tmp_path / name
        package = build(case / PACKAGE_ID)
        sim = case / "simulation"
        fixture(sim)
        mutate(package, sim)
        before = protected(sim)
        result = run_wrapper(package, sim)
        combined = result.stdout + result.stderr
        assert result.returncode != 0, name
        assert "VALIDATION_RESULT=NO_GO" in combined, name
        assert "MUTATION_BOUNDARY_REACHED" not in combined, name
        assert protected(sim) == before, name
        assert "p%40ss%3Aword" not in combined and "fake-only" not in combined, name


def test_package_freshness_contract_and_database_read_only():
    builder = BUILDER.read_text(encoding="utf-8")
    deploy = DEPLOY.read_text(encoding="utf-8").lower()
    assert "shutil.copy2" in builder and "sha256" in builder
    assert "begin transaction read only" in deploy
    for forbidden in ("alembic upgrade", "alembic downgrade", "insert into", "update ", "delete from", "create table", "alter table"):
        assert forbidden not in deploy
