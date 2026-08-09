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


def package_fixture(tmp_path: Path) -> Path:
    for relative in (MODULE.LEGACY_PATH, MODULE.REMEDIATION_PATH):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    manifest = {
        "production_baseline_revision": MODULE.BASELINE,
        "upgrade_revisions": [
            "20260810_logistics_network",
            "20260811_project_configuration",
            MODULE.REMEDIATION,
            "20260812_operational_execution",
        ],
        "migration_files": [
            {"revision": MODULE.REMEDIATION, "sha256": MODULE.REMEDIATION_SHA256}
        ],
    }
    (tmp_path / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_exact_historical_migration_is_allowed_only_with_mandatory_remediation(tmp_path):
    root = package_fixture(tmp_path)
    assert MODULE.findings(root) == []

    manifest_path = root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["upgrade_revisions"].remove(MODULE.REMEDIATION)
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


def test_exact_credential_and_migration_fingerprints_are_pinned():
    assert MODULE.sha256(ROOT / MODULE.LEGACY_PATH) == MODULE.LEGACY_FILE_SHA256
    assert MODULE.sha256(ROOT / MODULE.REMEDIATION_PATH) == MODULE.REMEDIATION_SHA256
