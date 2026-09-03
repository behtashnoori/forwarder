"""Qualification of the one frozen REQ-4A package; this test never builds it."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.tests.test_req1_release_engineering_qualification import fixture, protected
from scripts.tests.test_req3_database_identity_forensics import ALEMBIC, DB, fake_psql

PS51 = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
PACKAGE = Path(os.environ.get("REQ4A_PACKAGE", ""))


def require_package() -> Path:
    if not PACKAGE.is_dir():
        pytest.skip("REQ4A_PACKAGE must name the extracted frozen R7 package")
    return PACKAGE


def prepare(root: Path) -> tuple[Path, dict[str, str]]:
    fixture(root)
    out = root / "psql-out.txt"
    out.write_text(f"DATABASE={DB}\r\nALEMBIC={ALEMBIC}\r\n", encoding="utf-8")
    err = root / "psql-err.txt"
    err.write_text("", encoding="utf-8")
    psql = fake_psql(root / "psql.cmd")
    env = os.environ.copy()
    env.update(FORWARDER_REQ4A_HARNESS="REQ-4A-CONTROLLED-HARNESS",
               FORWARDER_PSQL_STDOUT=str(out), FORWARDER_PSQL_STDERR=str(err), FORWARDER_PSQL_EXIT="0")
    return psql, env


def run(root: Path, mutate=None) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    package = require_package()
    psql, env = prepare(root)
    if mutate:
        mutate(root, env)
    before = protected(root)
    result = subprocess.run([str(PS51), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(package / "deploy_s7_rc_f11f2ab.ps1"), "-ValidateOnly",
                             "-QualificationRoot", str(root), "-PsqlPath", str(psql),
                             "-BaselinePath", str(package / "expected-production-baseline.json")],
                            capture_output=True, text=True, timeout=90, env=env)
    return result, before


def contract(root: Path, **changes: str) -> None:
    path = root / "iis-contract.json"
    value = json.loads(path.read_text(encoding="utf-8")); value.update(changes)
    path.write_text(json.dumps(value), encoding="utf-8")


def env_text(root: Path, value: str) -> None:
    (root / "runtime/production.env").write_text(value, encoding="utf-8")


CASES = {
    "iis_module_missing": lambda r,e: contract(r,module_available="NO"),
    "iis_import_failure": lambda r,e: contract(r,import_result="FAIL"),
    "iis_provider_missing": lambda r,e: contract(r,provider_available="NO"),
    "iis_drive_missing": lambda r,e: contract(r,drive_available="NO"),
    "iis_site_missing": lambda r,e: contract(r,site_available="NO"),
    "iis_path_unreadable": lambda r,e: contract(r,physical_path_read="FAIL"),
    "iis_bindings_unreadable": lambda r,e: contract(r,binding_read="FAIL"),
    "iis_result_malformed": lambda r,e: contract(r,result_shape="BAD"),
    "scheduled_module_missing": lambda r,e: contract(r,scheduled_tasks_available="NO"),
    "scheduled_task_missing": lambda r,e: contract(r,scheduled_task_available="NO"),
    "current_release_missing": lambda r,e: shutil.rmtree(r/"production/release-adcc5da-adr043"),
    "env_missing": lambda r,e: (r/"runtime/production.env").unlink(),
    "runtime_wrapper_missing": lambda r,e: (r/"runtime/phase1b_production_cutover_runtime.py").unlink(),
    "task_reference_wrong": lambda r,e: (r/"task.txt").write_text("wrong"),
    "iis_reference_wrong": lambda r,e: contract(r,physical_path_records=["C:\\wrong\\dist"]),
    "target_already_exists": lambda r,e: (r/"production/release-f11f2ab-s7").mkdir(),
    "task_metadata_wrong": lambda r,e: (r/"task-metadata.txt").write_text("wrong"),
    "iis_state_wrong": lambda r,e: (r/"iis-state.txt").write_text("Stopped"),
    "iis_binding_wrong": lambda r,e: (r/"iis-bindings.txt").write_text("http"),
    "listener_wrong": lambda r,e: (r/"listener.txt").write_text("0.0.0.0:5101"),
    "health_wrong": lambda r,e: (r/"current-health.txt").write_text("500"),
    "disk_low": lambda r,e: (r/"disk-gb.txt").write_text("1"),
    "current_cors_wrong": lambda r,e: (r/"current-cors.txt").write_text("ALLOW_ALL"),
    "target_cors_wrong": lambda r,e: (r/"target-cors.txt").write_text("http://bad"),
    "unknown_origin_allowed": lambda r,e: (r/"unknown-origin.txt").write_text("ALLOWED"),
    "db_scalar_missing": lambda r,e: Path(e["FORWARDER_PSQL_STDOUT"]).write_text(f"ALEMBIC={ALEMBIC}\n"),
    "db_scalar_multiple": lambda r,e: Path(e["FORWARDER_PSQL_STDOUT"]).write_text(f"DATABASE={DB}\nDATABASE={DB}\nALEMBIC={ALEMBIC}\n"),
    "db_mismatch": lambda r,e: Path(e["FORWARDER_PSQL_STDOUT"]).write_text(f"DATABASE=wrong\nALEMBIC={ALEMBIC}\n"),
    "alembic_scalar_missing": lambda r,e: Path(e["FORWARDER_PSQL_STDOUT"]).write_text(f"DATABASE={DB}\n"),
    "alembic_scalar_multiple": lambda r,e: Path(e["FORWARDER_PSQL_STDOUT"]).write_text(f"DATABASE={DB}\nALEMBIC={ALEMBIC}\nALEMBIC={ALEMBIC}\n"),
    "alembic_mismatch": lambda r,e: Path(e["FORWARDER_PSQL_STDOUT"]).write_text(f"DATABASE={DB}\nALEMBIC=wrong\n"),
    "psql_nonzero": lambda r,e: e.update(FORWARDER_PSQL_EXIT="2"),
    "url_malformed": lambda r,e: env_text(r,"DATABASE_URL=bad\nJWT_SECRET_KEY=x\n"),
    "url_wrong_engine": lambda r,e: env_text(r,"DATABASE_URL=mysql://u:p@h/db\nJWT_SECRET_KEY=x\n"),
    "url_user_missing": lambda r,e: env_text(r,"DATABASE_URL=postgresql://h/db\nJWT_SECRET_KEY=x\n"),
    "env_duplicate": lambda r,e: env_text(r,"DATABASE_URL=postgresql://u:p@h/db\nDATABASE_URL=postgresql://u:p@h/db\nJWT_SECRET_KEY=x\n"),
    "harness_auth_missing": lambda r,e: e.pop("FORWARDER_REQ4A_HARNESS"),
    "harness_contract_missing": lambda r,e: (r/"iis-contract.json").unlink(),
    "harness_schema_wrong": lambda r,e: contract(r,schema="wrong"),
    "artifact_missing": lambda r,e: (r/"staging/Forwarder-S7-RC-f11f2ab.zip").unlink(),
    "artifact_wrong": lambda r,e: (r/"staging/Forwarder-S7-RC-f11f2ab.zip").write_bytes(b"wrong"),
    "artifact_manifest_wrong": lambda r,e: (r/"staging/Forwarder-S7-RC-f11f2ab.zip.manifest.json").write_text("{}"),
    "iis_actual_null": lambda r,e: contract(r,physical_path_records=None),
    "iis_actual_empty": lambda r,e: contract(r,physical_path_records=[""]),
    "iis_actual_multiple": lambda r,e: contract(r,physical_path_records=["C:\\one", "C:\\two"]),
    "iis_actual_provider_object": lambda r,e: contract(r,physical_path_shape="PROVIDER_OBJECT"),
    "iis_actual_whitespace": lambda r,e: contract(r,physical_path_records=[" C:\\wrong\\dist "]),
    "iis_actual_relative": lambda r,e: contract(r,physical_path_records=["relative\\dist"]),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_42_governed_failures(name: str, tmp_path: Path) -> None:
    root = tmp_path/name
    result, before = run(root, CASES[name])
    output = result.stdout + result.stderr
    assert result.returncode != 0 and "STATE=ABORTED_BEFORE_MUTATION" in output, (name, output)
    assert "MUTATION_BOUNDARY_REACHED" not in output and "Cannot find drive" not in output
    assert protected(root) == before


def test_ten_fresh_process_exact_package_runs(tmp_path: Path) -> None:
    counts = set()
    for index in range(10):
        root = tmp_path/f"run-{index:02d}"
        def representation(r: Path, env: dict[str, str]) -> None:
            expected=str(r/"production/release-adcc5da-adr043/dist")
            variant=index % 5
            if variant == 1: value=expected.swapcase()
            elif variant == 2: value=expected+"\\"
            elif variant == 3: value=expected.replace("\\", "/")
            elif variant == 4:
                env["REQ5_IIS_ROOT"]=str(r/"production/release-adcc5da-adr043")
                value="%REQ5_IIS_ROOT%\\dist"
            else: value=expected
            contract(r,physical_path_records=[value])
        result, before = run(root, representation)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "HARNESS_IIS_CONTRACT_PATH=PASS" in output and "PRECHECK_MANIFEST=PASS" in output
        assert "DATABASE_IDENTITY=PASS" in output and "ALEMBIC_IDENTITY=PASS" in output
        values = [line for line in output.splitlines() if line.startswith(("EXPECTED_PRECHECK_COUNT=", "EXECUTED_PRECHECK_COUNT=", "PASSED_PRECHECK_COUNT="))]
        assert len(values) == 3 and len({v.split("=",1)[1] for v in values}) == 1
        counts.add(values[0]); assert protected(root) == before
    assert len(counts) == 1


def test_normal_mode_narges_is_governed() -> None:
    package = require_package()
    result = subprocess.run([str(PS51), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(package/"validate_forwarder_s7_rc_f11f2ab.ps1")], capture_output=True, text=True)
    output=result.stdout+result.stderr
    assert result.returncode != 0 and "GATE=wrong host" in output and "STATE=ABORTED_BEFORE_MUTATION" in output


def test_simulated_deploy_verify_and_rollback(tmp_path: Path) -> None:
    package=require_package(); deploy=package/"deploy_s7_rc_f11f2ab.ps1"
    success=tmp_path/"success"; fixture(success)
    baseline=package/"expected-production-baseline.json"
    command=[str(PS51),"-NoProfile","-File",str(deploy),"-Execute","-ConfirmDeployment","-SimulationRoot",str(success),"-BaselinePath",str(baseline)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=90)
    assert result.returncode == 0 and "STATE=DEPLOYED_AND_VERIFIED" in result.stdout+result.stderr
    rollback=tmp_path/"rollback"; fixture(rollback); before=protected(rollback)
    command[command.index(str(success))]=str(rollback); command.append("-SimulateVerificationFailure")
    result=subprocess.run(command,capture_output=True,text=True,timeout=90)
    assert result.returncode != 0 and "STATE=FAILED_AND_RECOVERED" in result.stdout+result.stderr
    assert protected(rollback)==before
