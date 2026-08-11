"""Regression tests for the deployment-package historical credential boundary."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "verify_package_secrets.py"
SPEC = importlib.util.spec_from_file_location("package_secret_policy", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def package_fixture(tmp_path: Path, *, legacy_contract: bool = False) -> Path:
    for relative in (MODULE.LEGACY_PATH, MODULE.REMEDIATION_PATH):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    if legacy_contract:
        manifest = {
            "production_baseline_revision": MODULE.BASELINE,
            "upgrade_revisions": [
                MODULE.REMEDIATION,
                "20260812_operational_execution",
            ],
            "migration_files": [
                {"revision": MODULE.REMEDIATION, "sha256": MODULE.REMEDIATION_SHA256}
            ],
        }
    else:
        head = tmp_path / "backend/migrations/versions/20260819_v191_acceptance_corrections.py"
        head.write_text(
            'revision = "20260819_v191_acceptance_corrections"\n'
            f'down_revision = "{MODULE.REMEDIATION}"\n',
            encoding="utf-8",
        )
        manifest = {
            "application_version": "1.9.1",
            "database_revision": "20260819_v191_acceptance_corrections",
            "production_baseline_revision": "20260818_immutable_fx_provenance",
            "upgrade_revisions": ["20260819_v191_acceptance_corrections"],
            "migration_files": [],
            "historical_security_remediation": {
                "policy": MODULE.HISTORICAL_POLICY,
                "legacy_revision": MODULE.LEGACY_PATH.stem,
                "legacy_file_sha256": MODULE.LEGACY_FILE_SHA256,
                "remediation_revision": MODULE.REMEDIATION,
                "remediation_sha256": MODULE.REMEDIATION_SHA256,
            },
        }
    (tmp_path / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_later_release_baseline_uses_independent_historical_ancestry(tmp_path):
    root = package_fixture(tmp_path)
    assert MODULE.findings(root) == []


def test_lf_and_crlf_remediation_have_same_canonical_fingerprint(tmp_path):
    root = package_fixture(tmp_path)
    remediation = root / MODULE.REMEDIATION_PATH
    lf_bytes = remediation.read_bytes().replace(b"\r\n", b"\n")
    remediation.write_bytes(lf_bytes)
    lf_hash = MODULE.canonical_line_ending_sha256(remediation)
    assert MODULE.findings(root) == []

    remediation.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))
    assert MODULE.canonical_line_ending_sha256(remediation) == lf_hash
    assert lf_hash == MODULE.REMEDIATION_SHA256
    assert MODULE.findings(root) == []


def test_non_newline_remediation_byte_change_fails_closed(tmp_path):
    root = package_fixture(tmp_path)
    remediation = root / MODULE.REMEDIATION_PATH
    data = remediation.read_bytes()
    remediation.write_bytes(data.replace(b"Revision ID", b"Revision Id", 1))
    assert MODULE.findings(root) == [MODULE.LEGACY_PATH.as_posix()]


def test_non_newline_whitespace_change_fails_closed(tmp_path):
    root = package_fixture(tmp_path)
    remediation = root / MODULE.REMEDIATION_PATH
    data = remediation.read_bytes()
    remediation.write_bytes(data.replace(b"Revision ID", b"Revision  ID", 1))
    assert MODULE.findings(root) == [MODULE.LEGACY_PATH.as_posix()]


def test_lone_carriage_return_is_not_normalized(tmp_path):
    root = package_fixture(tmp_path)
    remediation = root / MODULE.REMEDIATION_PATH
    data = remediation.read_bytes().replace(b"\r\n", b"\n")
    remediation.write_bytes(data.replace(b"\n", b"\r", 1))
    assert MODULE.findings(root) == [MODULE.LEGACY_PATH.as_posix()]


def test_missing_historical_remediation_declaration_fails_closed(tmp_path):
    root = package_fixture(tmp_path)
    manifest_path = root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["historical_security_remediation"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert MODULE.findings(root) == [MODULE.LEGACY_PATH.as_posix()]


def test_unknown_secret_still_fails_when_exception_is_valid(tmp_path):
    root = package_fixture(tmp_path)
    unknown = root / "backend" / "new_config.py"
    unknown.write_text('api_key = "new-unrecognized-value"\n', encoding="utf-8")
    assert MODULE.findings(root) == ["backend/new_config.py"]


def test_historical_file_mutation_cannot_broaden_exception(tmp_path):
    root = package_fixture(tmp_path)
    legacy = root / MODULE.LEGACY_PATH
    legacy.write_text(legacy.read_text(encoding="utf-8") + '\nsecret = "extra"\n', encoding="utf-8")
    assert MODULE.findings(root) == [MODULE.LEGACY_PATH.as_posix()]


def test_tampered_historical_remediation_declaration_fails_closed(tmp_path):
    root = package_fixture(tmp_path)
    manifest_path = root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["historical_security_remediation"]["remediation_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert MODULE.findings(root) == [MODULE.LEGACY_PATH.as_posix()]


def test_v190_legacy_package_contract_remains_valid(tmp_path):
    assert MODULE.findings(package_fixture(tmp_path, legacy_contract=True)) == []


def test_unrelated_future_baseline_does_not_inherit_exception(tmp_path):
    root = package_fixture(tmp_path)
    unrelated = root / "backend/migrations/versions/future_unrelated.py"
    unrelated.write_text(
        'revision = "future_unrelated"\ndown_revision = None\n', encoding="utf-8"
    )
    manifest_path = root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["application_version"] = "99.0.0"
    manifest["database_revision"] = "future_unrelated"
    manifest["production_baseline_revision"] = "future_baseline"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert MODULE.findings(root) == [MODULE.LEGACY_PATH.as_posix()]


def test_exact_credential_and_migration_fingerprints_are_pinned():
    assert MODULE.sha256(ROOT / MODULE.LEGACY_PATH) == MODULE.LEGACY_FILE_SHA256
    assert (
        MODULE.canonical_line_ending_sha256(ROOT / MODULE.REMEDIATION_PATH)
        == MODULE.REMEDIATION_SHA256
    )


def test_builder_and_scanner_share_the_exact_historical_contract():
    builder_path = ROOT / "scripts/build_release_package.py"
    spec = importlib.util.spec_from_file_location("release_builder", builder_path)
    builder = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(builder)
    assert builder.HISTORICAL_SECURITY_REMEDIATION == {
        "policy": MODULE.HISTORICAL_POLICY,
        "legacy_revision": MODULE.LEGACY_PATH.stem,
        "legacy_file_sha256": MODULE.LEGACY_FILE_SHA256,
        "remediation_revision": MODULE.REMEDIATION,
        "remediation_sha256": MODULE.REMEDIATION_SHA256,
    }
