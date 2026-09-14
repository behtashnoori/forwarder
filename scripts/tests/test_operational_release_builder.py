"""Canonical active-release lineage gate regression tests."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("operational_builder", ROOT / "scripts/build_operational_workspace_release.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def package(tmp_path):
    metadata = {
        "candidate": builder.NAME,
        "application_source_commit": builder.APP,
        "tooling_commit": "b" * 40,
        "production_before_revision": builder.BEFORE,
        "required_db_revision": builder.TARGET,
        "migration_required": True,
        "runtime_sha256": builder.RHASH,
    }
    (tmp_path / "artifact").mkdir()
    for name in ("RELEASE-METADATA.json", "artifact/release-manifest.json"):
        (tmp_path / name).write_text(json.dumps(metadata), encoding="utf-8")
    for name in ("VERIFY-PACKAGE.ps1", "CERTIFY-RELEASE.ps1", "QUALIFY-REAL-VALIDATEONLY.ps1", "QUALIFY-REAL-EXECUTE.ps1", "deploy_windows_iis_waitress.ps1", "SERVER-DEPLOY-STEPS.md", "ROLLBACK.md"):
        (tmp_path / name).write_text(builder.APP, encoding="utf-8")
    return metadata


def test_active_lineage_passes_canonical_contract(tmp_path):
    metadata = package(tmp_path)
    assert builder.active_lineage_gate(tmp_path, "b" * 40) == metadata


@pytest.mark.parametrize("lineage", builder.STALE)
@pytest.mark.parametrize("name", ("VERIFY-PACKAGE.ps1", "CERTIFY-RELEASE.ps1", "deploy_windows_iis_waitress.ps1", "SERVER-DEPLOY-STEPS.md", "ROLLBACK.md"))
def test_active_lineage_rejects_stale_claims(tmp_path, lineage, name):
    package(tmp_path)
    (tmp_path / name).write_text(builder.APP + "\n" + lineage, encoding="utf-8")
    with pytest.raises(RuntimeError, match="stale active release lineage"):
        builder.active_lineage_gate(tmp_path, "b" * 40)


@pytest.mark.parametrize("key,value", [
    ("application_source_commit", "a" * 40),
    ("production_before_revision", "wrong"),
    ("required_db_revision", "wrong"),
    ("migration_required", False),
    ("tooling_commit", "c" * 40),
])
def test_manifest_disagreement_fails_closed(tmp_path, key, value):
    metadata = package(tmp_path)
    metadata[key] = value
    (tmp_path / "artifact/release-manifest.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(RuntimeError, match="release metadata mismatch"):
        builder.active_lineage_gate(tmp_path, "b" * 40)


@pytest.mark.parametrize('defect', [
    '$global:ForwarderExecuteState.Iis',
    'if($false){$script:state.iis_path}',
    'try {throw "failure"} finally {$script:cleanup}',
    'function global:Get-Website {$global:ForwarderExecuteState.Iis}',
    'function Save {$script:state | ConvertTo-Json}',
])
def test_unset_state_cannot_escape_qualification(tmp_path, defect):
    (tmp_path / 'deploy_windows_iis_waitress.ps1').write_text(
        'Set-StrictMode -Version Latest\n' + defect, encoding='utf-8')
    result = subprocess.run([
        'powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(ROOT / 'scripts/tests/audit_release_state_lifecycle.ps1'),
        '-PackageRoot', str(tmp_path),
    ], capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert 'ambient mutable variable reference' in result.stderr


@pytest.mark.parametrize('wrong_failure', [
    '$null=$global:ForwarderExecuteState',
    'throw "unexpected state lifecycle failure"',
])
def test_failure_matrix_rejects_unrelated_state_error(tmp_path, wrong_failure):
    for name in ('VERIFY-PACKAGE.ps1', 'AUDIT-STATE-LIFECYCLE.ps1'):
        (tmp_path / name).write_text('return\n')
    original = (ROOT / 'scripts/deploy/deploy_windows_iis_waitress_operational.ps1').read_text()
    expected = 'throw "RELEASE_STOP: injected $Stage"'
    assert original.count(expected) == 1
    mutant = tmp_path / 'deploy-mutant.ps1'
    mutant.write_text(original.replace(expected, wrong_failure))
    result = subprocess.run([
        'powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(ROOT / 'scripts/tests/test_operational_release_pipeline.ps1'),
        '-PackageRoot', str(tmp_path), '-DeployScript', str(mutant),
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert 'FAILURE_INJECTION_MATRIX=PASS' not in result.stdout
    assert ('ForwarderExecuteState' in result.stderr or
            'unexpected state lifecycle failure' in result.stderr)


def test_package_refusal_precedes_discovery_and_packaged_runtime(tmp_path):
    # This package deliberately has no runtime and must never reach Windows
    # server discovery or execute database commands before its verifier refuses.
    (tmp_path / 'VERIFY-PACKAGE.ps1').write_text("throw 'VERIFY_FAIL test checksum refusal'\n")
    result = subprocess.run([
        'powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(ROOT / 'scripts/deploy/deploy_windows_iis_waitress_operational.ps1'),
        '-PackageRoot', str(tmp_path), '-ValidateOnly',
    ], capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert 'VERIFY_FAIL test checksum refusal' in result.stderr
    assert 'WebAdministration' not in result.stderr
