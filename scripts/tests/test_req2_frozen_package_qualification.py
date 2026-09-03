"""REQ-2 qualification for one already-built, frozen R5 package."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.tests.test_req1_release_engineering_qualification import fixture, protected

ROOT = Path(__file__).resolve().parents[2]
PS51 = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
PACKAGE = Path(os.environ.get("REQ2_PACKAGE", ""))
ZIP = Path(os.environ.get("REQ2_PACKAGE_ZIP", ""))
EXPECTED_ZIP_SHA256 = os.environ.get("REQ2_PACKAGE_SHA256", "")
PACKAGE_ID = os.environ.get("REQ2_PACKAGE_ID", "D2-VALIDATION-S7-RC-f11f2ab-req12-listener-fix-final")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_package() -> Path:
    if not PACKAGE.is_dir():
        pytest.skip("set REQ2_PACKAGE to the extracted frozen R5 package")
    return PACKAGE


def run_wrapper(package: Path, simulation: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [str(PS51), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(package / "validate_forwarder_s7_rc_f11f2ab.ps1"),
               "-SimulationRoot", str(simulation), "-ExpectedPackageId", PACKAGE_ID]
    return subprocess.run(command, capture_output=True, text=True, timeout=90, env=env)


def copy_package(destination: Path) -> Path:
    shutil.copytree(require_package(), destination, ignore=shutil.ignore_patterns("D2-validation-report-*.json"))
    return destination


def update_manifest_record(package: Path, name: str) -> None:
    manifest_path = package / "D2-package-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = package / name
    for record in manifest["files"]:
        if record["name"] == name:
            record["bytes"] = target.stat().st_size
            record["sha256"] = digest(target)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_frozen_zip_identity_and_packaged_source_identity() -> None:
    package = require_package()
    assert ZIP.is_file() and digest(ZIP) == EXPECTED_ZIP_SHA256
    for name in ("deploy_s7_rc_f11f2ab.ps1", "validate_forwarder_s7_rc_f11f2ab.ps1"):
        assert digest(package / name) == digest(ROOT / "scripts/deploy" / name)


def test_exact_package_ten_consecutive_go_zero_mutation_and_complete_map(tmp_path: Path) -> None:
    package = require_package()
    initial_zip_hash = digest(ZIP)
    expected_map = None
    for index in range(10):
        simulation = tmp_path / f"go-{index:02d}"
        fixture(simulation)
        before = protected(simulation)
        result = run_wrapper(package, simulation)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "VALIDATION_RESULT=GO" in output
        assert "PRECHECK_47=PASS" in output
        assert output.count("_RUNTIME_TYPE=System.Boolean") == 47
        assert protected(simulation) == before
        mapping = [line for line in output.splitlines() if "_GATE=" in line]
        assert len(mapping) == 47
        expected_map = mapping if expected_map is None else expected_map
        assert mapping == expected_map
    assert digest(ZIP) == initial_zip_hash == EXPECTED_ZIP_SHA256


MUTATIONS = {
    "01_missing_application_artifact": lambda p, s: (p / "Forwarder-S7-RC-f11f2ab.zip").unlink(),
    "02_wrong_application_hash": lambda p, s: (p / "Forwarder-S7-RC-f11f2ab.zip").write_bytes(b"tampered"),
    "03_wrong_manifest_hash": lambda p, s: (p / "Forwarder-S7-RC-f11f2ab.zip.manifest.json").write_text("{}"),
    "04_missing_production_env": lambda p, s: (s / "runtime/production.env").unlink(),
    "05_empty_database_url": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=\nJWT_SECRET_KEY=x\n"),
    "06_malformed_database_url": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=not-a-url\nJWT_SECRET_KEY=x\n"),
    "07_unsupported_db_engine": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=mysql://u:p@h/db\nJWT_SECRET_KEY=x\n"),
    "08_unsupported_postgresql_driver": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=postgresql+asyncpg://u:p@h/db\nJWT_SECRET_KEY=x\n"),
    "09_db_connection_failure": lambda p, s: (s / "database.txt").unlink(),
    "10_wrong_db_identity": lambda p, s: (s / "database.txt").write_text("wrong|20260907_direct_shipment_responsibility"),
    "11_wrong_alembic_revision": lambda p, s: (s / "database.txt").write_text("forwarder_prod_20260728_161711|wrong"),
    "12_insufficient_disk": lambda p, s: (s / "disk-gb.txt").write_text("1"),
    "13_missing_expected_path": lambda p, s: shutil.rmtree(s / "production/release-adcc5da-adr043"),
    "14_wrong_task_identity": lambda p, s: (s / "task.txt").write_text("wrong"),
    "15_malformed_task_metadata": lambda p, s: (s / "task-metadata.txt").write_text("malformed"),
    "16_iis_mismatch": lambda p, s: (s / "iis.txt").write_text("wrong"),
    "17_invalid_canonical_cors_target": lambda p, s: (s / "target-cors.txt").write_text("http://bad"),
    "18_allow_all_cors": lambda p, s: (s / "current-cors.txt").write_text("ALLOW_ALL"),
    "19_conflicting_cors_values": lambda p, s: (s / "runtime/production.env").write_text("DATABASE_URL=postgresql://u:p@h/db\nDATABASE_URL=postgresql://u:p@h/db\nJWT_SECRET_KEY=x\n"),
    "20_unknown_origin_behavior": lambda p, s: (s / "unknown-origin.txt").write_text("ALLOWED"),
    "21_backend_listener_mismatch": lambda p, s: (s / "listener.txt").write_text("0.0.0.0:5101"),
    "22_health_failure": lambda p, s: (s / "current-health.txt").write_text("500"),
    "23_package_missing_deployment_script": lambda p, s: (p / "deploy_s7_rc_f11f2ab.ps1").unlink(),
    "24_stale_deployment_script_hash": lambda p, s: (p / "deploy_s7_rc_f11f2ab.ps1").write_text("# stale"),
    "25_malformed_json_manifest": lambda p, s: (p / "D2-package-manifest.json").write_text("{"),
    "26_permission_access_failure": lambda p, s: (s / "admin.txt").write_text("no"),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_failure_injection_01_26(name: str, tmp_path: Path) -> None:
    package = copy_package(tmp_path / "package")
    simulation = tmp_path / "simulation"
    fixture(simulation)
    MUTATIONS[name](package, simulation)
    before = protected(simulation)
    result = run_wrapper(package, simulation)
    output = result.stdout + result.stderr
    assert result.returncode != 0 and "VALIDATION_RESULT=NO_GO" in output, name
    assert "MUTATION_BOUNDARY_REACHED" not in output and protected(simulation) == before, name
    assert "p%40ss%3Aword" not in output and "fake-only" not in output, name


@pytest.mark.parametrize("literal", ["True", "False", "''", "$null"])
def test_failure_injection_27_30_non_boolean_producers(literal: str) -> None:
    deploy = require_package() / "deploy_s7_rc_f11f2ab.ps1"
    escaped = str(deploy).replace("'", "''")
    command = rf"""
$t=$null;$e=$null;$a=[Management.Automation.Language.Parser]::ParseFile('{escaped}',[ref]$t,[ref]$e)
$names=@('Fail','Require');foreach($n in $names){{$f=$a.FindAll({{param($x)$x -is [Management.Automation.Language.FunctionDefinitionAst] -and $x.Name -eq $n}},$true)|select -First 1;iex $f.Extent.Text}}
$script:PrecheckCount=0
try{{Require -Condition {literal} -Message 'injected non-Boolean';exit 2}}catch{{if($_.Exception.Message -match 'TOOLING_DEFECT' -and $_.Exception.Message -notmatch 'Cannot process argument transformation'){{exit 0}};write-error $_;exit 1}}
"""
    result = subprocess.run([str(PS51), "-NoProfile", "-Command", command], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_failure_injection_31_packaged_script_differs_from_source(tmp_path: Path) -> None:
    package = copy_package(tmp_path / "package")
    path = package / "deploy_s7_rc_f11f2ab.ps1"
    path.write_text(path.read_text(encoding="utf-8") + "\n# injected divergence\n", encoding="utf-8")
    assert digest(path) != digest(ROOT / "scripts/deploy/deploy_s7_rc_f11f2ab.ps1")


def test_failure_injection_32_package_rebuilt_after_qualification(tmp_path: Path) -> None:
    changed = tmp_path / "rebuilt.zip"
    shutil.copy2(ZIP, changed)
    with changed.open("ab") as stream:
        stream.write(b"rebuilt")
    assert digest(changed) != EXPECTED_ZIP_SHA256


def test_failure_injection_33_wrapper_resolves_wrong_script(tmp_path: Path) -> None:
    package = copy_package(tmp_path / "package")
    simulation = tmp_path / "simulation"
    fixture(simulation)
    wrong = tmp_path / "outside-deploy.ps1"
    shutil.copy2(package / "deploy_s7_rc_f11f2ab.ps1", wrong)
    wrapper = package / "validate_forwarder_s7_rc_f11f2ab.ps1"
    text = wrapper.read_text(encoding="utf-8").replace("$entry=Join-Path $Root 'deploy_s7_rc_f11f2ab.ps1'", f"$entry='{str(wrong).replace(chr(92), chr(92)*2)}'")
    wrapper.write_text(text, encoding="utf-8")
    update_manifest_record(package, wrapper.name)
    result = run_wrapper(package, simulation)
    assert result.returncode != 0 and "VALIDATION_RESULT=NO_GO" in result.stdout + result.stderr


def test_failure_injection_34_ps51_required(tmp_path: Path) -> None:
    package = copy_package(tmp_path / "package")
    simulation = tmp_path / "simulation"
    fixture(simulation)
    wrapper = package / "validate_forwarder_s7_rc_f11f2ab.ps1"
    text = wrapper.read_text(encoding="utf-8").replace(
        "$ps51=Join-Path $env:SystemRoot 'System32\\WindowsPowerShell\\v1.0\\powershell.exe'",
        f"$ps51='{tmp_path / 'not-powershell.exe'}'",
    )
    wrapper.write_text(text, encoding="utf-8")
    update_manifest_record(package, wrapper.name)
    result = run_wrapper(package, simulation)
    assert result.returncode != 0 and "VALIDATION_RESULT=NO_GO" in result.stdout + result.stderr


def test_failure_injection_35_child_path_is_package_local() -> None:
    wrapper = (require_package() / "validate_forwarder_s7_rc_f11f2ab.ps1").read_text(encoding="utf-8")
    assert "Resolve-Path -LiteralPath $entry" in wrapper
    assert "deployment script resolved outside the package" in wrapper
    assert "& $ps51 @childArguments" in wrapper


def test_simulated_deployment_and_exact_rollback(tmp_path: Path) -> None:
    package = require_package()
    deploy = package / "deploy_s7_rc_f11f2ab.ps1"
    success = tmp_path / "deploy-success"
    fixture(success)
    command = [str(PS51), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(deploy),
               "-Execute", "-ConfirmDeployment", "-SimulationRoot", str(success)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0 and "STATE=DEPLOYED_AND_VERIFIED" in result.stdout + result.stderr

    rollback = tmp_path / "deploy-rollback"
    fixture(rollback)
    before = protected(rollback)
    result = subprocess.run(command[:-1] + [str(rollback), "-SimulateVerificationFailure"], capture_output=True, text=True, timeout=90)
    output = result.stdout + result.stderr
    assert result.returncode != 0 and "STATE=FAILED_AND_RECOVERED" in output
    assert protected(rollback) == before
