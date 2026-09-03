"""REQ-4A controlled IIS prerequisite qualification under fresh PowerShell 5.1."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.tests.test_req1_release_engineering_qualification import fixture, protected
from scripts.tests.test_req3_database_identity_forensics import ALEMBIC, DB, fake_psql

ROOT = Path(__file__).resolve().parents[2]
PS51 = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
BUILDER = ROOT / "scripts/deploy/build_d2_validation_package.py"
PACKAGE_ID = "D2-VALIDATION-S7-RC-f11f2ab-r10-final"


def build(path: Path) -> Path:
    subprocess.run([sys.executable, str(BUILDER), str(path), "req4a-source"], check=True, capture_output=True)
    return path


def run_contract(package: Path, root: Path, changes: dict[str, object] | None = None,
                 env_changes: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    fixture(root)
    contract_path = root / "iis-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract.update(changes or {})
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    stdout = root / "psql-stdout.txt"
    stdout.write_text(f"DATABASE={DB}\r\nALEMBIC={ALEMBIC}\r\n", encoding="utf-8")
    stderr = root / "psql-stderr.txt"
    stderr.write_text("", encoding="utf-8")
    psql = fake_psql(root / "psql.cmd")
    env = os.environ.copy()
    env.update(FORWARDER_REQ4A_HARNESS="REQ-4A-CONTROLLED-HARNESS",
               FORWARDER_PSQL_STDOUT=str(stdout), FORWARDER_PSQL_STDERR=str(stderr),
               FORWARDER_PSQL_EXIT="0")
    env.update(env_changes or {})
    return subprocess.run(
        [str(PS51), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(package / "deploy_s7_rc_f11f2ab.ps1"), "-ValidateOnly",
         "-QualificationRoot", str(root), "-PsqlPath", str(psql),
         "-BaselinePath", str(package / "expected-production-baseline.json")],
        capture_output=True, text=True, timeout=90, env=env,
    )


@pytest.fixture()
def package(tmp_path: Path) -> Path:
    return build(tmp_path / PACKAGE_ID)


IIS_FAILURES = [
    ({"module_available": "NO"}, "required IIS PowerShell module unavailable"),
    ({"import_result": "FAIL"}, "IIS PowerShell module import failed"),
    ({"provider_available": "NO"}, "IIS PowerShell provider unavailable"),
    ({"drive_available": "NO"}, "IIS PowerShell drive unavailable"),
    ({"site_available": "NO"}, "governed IIS site unavailable"),
    ({"physical_path_read": "FAIL"}, "IIS physical path unreadable"),
    ({"binding_read": "FAIL"}, "IIS bindings unreadable"),
    ({"result_shape": "MALFORMED"}, "malformed IIS inspection result"),
]


@pytest.mark.parametrize("changes,reason", IIS_FAILURES)
def test_iis_failure_state_machine_is_governed(package: Path, tmp_path: Path,
                                                changes: dict[str, str], reason: str) -> None:
    root = tmp_path / reason.replace(" ", "-")
    before_root = root
    result = run_contract(package, root, changes)
    output = result.stdout + result.stderr
    assert result.returncode != 0 and reason in output
    assert "STATE=ABORTED_BEFORE_MUTATION" in output and "MUTATION_BOUNDARY_REACHED" not in output
    assert "Cannot find drive" not in output and protected(before_root)["target"] == "False"


def test_ten_fresh_process_contract_runs(package: Path, tmp_path: Path) -> None:
    for index in range(10):
        root = tmp_path / f"fresh-{index:02d}"
        before = None
        result = run_contract(package, root)
        before = protected(root)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "HARNESS_IIS_CONTRACT_PATH=PASS" in output
        assert "RAW_IIS_PROVIDER_RECORD_COUNT=1" in output
        assert "RAW_IIS_PROVIDER_RECORD_TYPE=System.String" in output
        assert "ACTUAL_IIS_DIST_TYPE=System.String" in output
        assert "IIS_DIST_EQUALS_RESULT=True" in output
        assert "DATABASE_IDENTITY=PASS" in output and "ALEMBIC_IDENTITY=PASS" in output
        assert "PRECHECK_MANIFEST=PASS" in output and "STATE=ABORTED_BEFORE_MUTATION" in output
        assert protected(root) == before


def test_harness_is_not_exposed_by_operator_wrapper() -> None:
    wrapper = (ROOT / "scripts/deploy/validate_forwarder_s7_rc_f11f2ab.ps1").read_text(encoding="utf-8")
    deploy = (ROOT / "scripts/deploy/deploy_s7_rc_f11f2ab.ps1").read_text(encoding="utf-8")
    assert "QualificationRoot" not in wrapper
    assert "FORWARDER_REQ4A_HARNESS" in deploy and "controlled harness authorization is absent" in deploy


def test_normal_package_on_narges_is_governed_no_go(package: Path) -> None:
    result = subprocess.run([str(PS51), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(package / "validate_forwarder_s7_rc_f11f2ab.ps1")],
                            capture_output=True, text=True, timeout=90)
    output = result.stdout + result.stderr
    assert result.returncode != 0 and "GATE=wrong host" in output
    assert "STATE=ABORTED_BEFORE_MUTATION" in output and "Cannot find drive" not in output


def test_no_validateonly_iis_mutators_before_boundary() -> None:
    source = (ROOT / "scripts/deploy/deploy_s7_rc_f11f2ab.ps1").read_text(encoding="utf-8")
    validate_only = source.index("if($ValidateOnly)")
    boundary = source.index("Write-Output 'MUTATION_BOUNDARY_REACHED'")
    assert validate_only < boundary
    assert "Initialize-IisInspection" in source and source.index("Initialize-IisInspection", 1000) < boundary
    for forbidden in ("restart-webapppool", "new-webbinding", "remove-webbinding", "stop-website", "start-website"):
        assert forbidden not in source.lower()


@pytest.mark.parametrize("variant", ["exact", "case", "trailing", "slash", "environment"])
def test_iis_reference_normalization_contract(package: Path, tmp_path: Path, variant: str) -> None:
    root = tmp_path / variant
    expected = str(root / "production/release-adcc5da-adr043/dist")
    values = {
        "exact": expected,
        "case": expected.swapcase(),
        "trailing": expected + "\\",
        "slash": expected.replace("\\", "/"),
        "environment": "%REQ5_IIS_ROOT%\\dist",
    }
    env = {"REQ5_IIS_ROOT": str(root / "production/release-adcc5da-adr043")}
    result = run_contract(package, root, {"physical_path_records": [values[variant]]}, env)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "IIS_DIST_EQUALS_RESULT=True" in output
    assert "ACTUAL_IIS_DIST_TYPE=System.String" in output


@pytest.mark.parametrize("changes", [
    {"physical_path_records": None},
    {"physical_path_shape": "ZERO_RECORDS", "physical_path_records": []},
    {"physical_path_records": [""]},
    {"physical_path_records": ["C:\\one", "C:\\two"]},
    {"physical_path_shape": "STRING_ARRAY", "physical_path_records": ["C:\\one", "C:\\two"]},
    {"physical_path_shape": "PROVIDER_OBJECT"},
    {"physical_path_shape": "INTEGER", "physical_path_records": [42]},
    {"physical_path_shape": "BOOLEAN", "physical_path_records": [True]},
    {"physical_path_records": [" C:\\wrong\\dist "]},
    {"physical_path_records": ["C:\\wrong\\dist "]},
    {"physical_path_records": ["relative\\dist"]},
    {"physical_path_records": ["C:\\bad\u0000path"]},
    {"physical_path_records": ["C:\\wrong-release\\dist"]},
    {"physical_path_records": ["C:\\wrong-release"]},
    {"physical_path_shape": "PROVIDER_THROWS"},
])
def test_invalid_iis_reference_shapes_are_governed(package: Path, tmp_path: Path,
                                                    changes: dict[str, object]) -> None:
    result = run_contract(package, tmp_path / str(abs(hash(repr(changes)))), changes)
    output = result.stdout + result.stderr
    assert result.returncode != 0 and "STATE=ABORTED_BEFORE_MUTATION" in output
    assert "MUTATION_BOUNDARY_REACHED" not in output and "Cannot find drive" not in output


def test_real_production_scalar_shape_and_old_r9_failure_are_explicit(package: Path, tmp_path: Path) -> None:
    production_value = r"C:\1-webapp\forwarder-production\release-adcc5da-adr043\dist"
    command = (
        f"$raw='{production_value}';"
        "$has=$null -ne $raw.PSObject.Properties['physicalPath'];"
        "$old=$raw.physicalPath;"
        "Write-Output ('RAW_PROVIDER_RESULT_TYPE='+$raw.GetType().FullName);"
        "Write-Output ('RAW_PROVIDER_RESULT_HAS_PHYSICALPATH_PROPERTY='+$(if($has){'YES'}else{'NO'}));"
        "Write-Output ('OLD_R9_DOT_PROPERTY_RESULT='+$(if($null -eq $old){'NULL'}else{$old}));"
        "if($raw.GetType().FullName -ne 'System.String' -or $has -or $null -ne $old){exit 1}"
    )
    proof = subprocess.run([str(PS51), "-NoProfile", "-Command", command], capture_output=True, text=True)
    assert proof.returncode == 0, proof.stdout + proof.stderr
    assert "RAW_PROVIDER_RESULT_TYPE=System.String" in proof.stdout
    assert "RAW_PROVIDER_RESULT_HAS_PHYSICALPATH_PROPERTY=NO" in proof.stdout
    assert "OLD_R9_DOT_PROPERTY_RESULT=NULL" in proof.stdout

    root = tmp_path / "real-production-provider-shape"
    root.mkdir()
    (root / "iis-contract.json").write_text(json.dumps({
        "physical_path_shape": "SCALAR", "physical_path_records": [production_value],
    }), encoding="utf-8")
    deploy = str(package / "deploy_s7_rc_f11f2ab.ps1").replace("'", "''")
    qualification = str(root).replace("'", "''")
    extraction = rf"""
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{deploy}',[ref]$tokens,[ref]$errors)
foreach($name in @('Fail','ConvertTo-GovernedWindowsPath','Get-GovernedIisPhysicalPath')){{
  $function=$ast.FindAll({{param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name}},$true)|Select-Object -First 1
  Invoke-Expression $function.Extent.Text
}}
$QualificationRoot='{qualification}';$SimulationRoot=$null
$result=@(Get-GovernedIisPhysicalPath)
Write-Output ('IIS_HELPER_PIPELINE_OUTPUT_COUNT='+$result.Count)
Write-Output ('NEW_R10_EXTRACTION_RESULT='+$result[0])
if($result.Count -ne 1 -or $result[0].GetType().FullName -ne 'System.String' -or $result[0] -ne '{production_value}'){{exit 1}}
"""
    fixed = subprocess.run([str(PS51), "-NoProfile", "-Command", extraction], capture_output=True, text=True)
    output = fixed.stdout + fixed.stderr
    assert fixed.returncode == 0, output
    assert "RAW_IIS_PROVIDER_RECORD_COUNT=1" in output
    assert "RAW_IIS_PROVIDER_RECORD_TYPE=System.String" in output
    assert "IIS_HELPER_PIPELINE_OUTPUT_COUNT=1" in output
    assert f"NEW_R10_EXTRACTION_RESULT={production_value}" in output
