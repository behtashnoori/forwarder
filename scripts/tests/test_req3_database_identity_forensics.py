"""REQ-3 database/Alembic false-negative repair and non-simulation qualification."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.tests.test_req1_release_engineering_qualification import fixture, protected

ROOT = Path(__file__).resolve().parents[2]
PS51 = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
BUILDER = ROOT / "scripts/deploy/build_d2_validation_package.py"
PACKAGE_ID = "D2-VALIDATION-S7-RC-f11f2ab-r6-final"
DB = "forwarder_prod_20260728_161711"
ALEMBIC = "20260907_direct_shipment_responsibility"


def fake_psql(path: Path) -> Path:
    path.write_text(
        "@echo off\r\n"
        "if exist \"%FORWARDER_PSQL_STDERR%\" type \"%FORWARDER_PSQL_STDERR%\" 1>&2\r\n"
        "if exist \"%FORWARDER_PSQL_STDOUT%\" type \"%FORWARDER_PSQL_STDOUT%\"\r\n"
        "exit /b %FORWARDER_PSQL_EXIT%\r\n",
        encoding="ascii",
        newline="",
    )
    return path


def build(path: Path) -> Path:
    subprocess.run([sys.executable, str(BUILDER), str(path), "req3-tooling"], check=True)
    return path


def run(package: Path, root: Path, lines: list[str], *, exit_code: int = 0,
        stderr: str = "", baseline: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
    fixture(root)
    stdout = root / "psql-stdout.txt"
    stdout.write_text("\r\n".join(lines) + ("\r\n" if lines else ""), encoding="utf-8", newline="")
    stderr_path = root / "psql-stderr.txt"
    stderr_path.write_text(stderr, encoding="utf-8")
    psql = fake_psql(root / "psql.cmd")
    if baseline is not None:
        (package / "expected-production-baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
        # Tests that mutate package content invoke the deploy entrypoint directly.
    env = dict(**__import__("os").environ)
    env.update(FORWARDER_PSQL_STDOUT=str(stdout), FORWARDER_PSQL_STDERR=str(stderr_path),
               FORWARDER_PSQL_EXIT=str(exit_code))
    command = [str(PS51), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(package / "deploy_s7_rc_f11f2ab.ps1"), "-ValidateOnly",
               "-QualificationRoot", str(root), "-PsqlPath", str(psql),
               "-BaselinePath", str(package / "expected-production-baseline.json")]
    return subprocess.run(command, capture_output=True, text=True, timeout=90, env=env)


@pytest.fixture()
def package(tmp_path: Path) -> Path:
    return build(tmp_path / PACKAGE_ID)


def test_r5_false_negative_is_reproduced_under_ps51() -> None:
    command = f"$result=@('BEGIN','{DB}|{ALEMBIC}','COMMIT');if((($result|select -First 1).Trim() -eq '{DB}|{ALEMBIC}')){{exit 1}};Write-Output 'R5_DATABASE_FALSE_NEGATIVE_REPRODUCED=YES'"
    result = subprocess.run([str(PS51), "-NoProfile", "-Command", command], capture_output=True, text=True)
    assert result.returncode == 0 and "R5_DATABASE_FALSE_NEGATIVE_REPRODUCED=YES" in result.stdout


@pytest.mark.parametrize(
    "name,lines,exit_code,expected",
    [
        ("correct", [f"DATABASE={DB}", f"ALEMBIC={ALEMBIC}"], 0, True),
        ("wrong_db", ["DATABASE=wrong", f"ALEMBIC={ALEMBIC}"], 0, False),
        ("wrong_alembic", [f"DATABASE={DB}", "ALEMBIC=wrong"], 0, False),
        ("both_wrong", ["DATABASE=wrong", "ALEMBIC=wrong"], 0, False),
        ("empty_db", ["DATABASE=", f"ALEMBIC={ALEMBIC}"], 0, False),
        ("empty_alembic", [f"DATABASE={DB}", "ALEMBIC="], 0, False),
        ("multiple_db", [f"DATABASE={DB}", f"DATABASE={DB}", f"ALEMBIC={ALEMBIC}"], 0, False),
        ("multiple_alembic", [f"DATABASE={DB}", f"ALEMBIC={ALEMBIC}", f"ALEMBIC={ALEMBIC}"], 0, False),
        ("whitespace", [f"DATABASE=  {DB}  ", f"ALEMBIC=  {ALEMBIC}  "], 0, True),
        ("object_array", ["BEGIN", f"DATABASE={DB}", f"ALEMBIC={ALEMBIC}", "COMMIT"], 0, True),
        ("command_failure", [], 2, False),
    ],
)
def test_identity_matrix(package: Path, tmp_path: Path, name: str, lines: list[str], exit_code: int, expected: bool) -> None:
    result = run(package, tmp_path / name, lines, exit_code=exit_code,
                 stderr="NOTICE: harmless diagnostic\n")
    output = result.stdout + result.stderr
    assert (result.returncode == 0) is expected, output
    assert ("DATABASE_IDENTITY=PASS" in output and "ALEMBIC_IDENTITY=PASS" in output) is expected
    assert "MUTATION_BOUNDARY_REACHED" not in output


def test_exact_package_ten_non_simulation_database_runs(package: Path, tmp_path: Path) -> None:
    for index in range(10):
        root = tmp_path / f"go-{index:02d}"
        result = run(package, root, [f"DATABASE={DB}", f"ALEMBIC={ALEMBIC}"])
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "DATABASE_IDENTITY=PASS" in output and "ALEMBIC_IDENTITY=PASS" in output
        assert "STATE=ABORTED_BEFORE_MUTATION" in output
        assert "MUTATION_BOUNDARY_REACHED" not in output


def test_quoted_and_bom_baseline_are_deterministic(package: Path, tmp_path: Path) -> None:
    baseline = json.loads((package / "expected-production-baseline.json").read_text(encoding="utf-8-sig"))
    baseline["database"] = f'"{DB}"'
    result = run(package, tmp_path / "quoted", [f"DATABASE={DB}", f"ALEMBIC={ALEMBIC}"], baseline=baseline)
    assert result.returncode != 0 and "database identity mismatch" in result.stdout + result.stderr
    baseline["database"] = DB
    path = package / "expected-production-baseline.json"
    path.write_text("\ufeff" + json.dumps(baseline), encoding="utf-8")
    result = run(package, tmp_path / "bom", [f"DATABASE={DB}", f"ALEMBIC={ALEMBIC}"])
    assert result.returncode == 0, result.stdout + result.stderr
