import importlib.util
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _builder():
    path = ROOT / "scripts" / "build_release_package.py"
    spec = importlib.util.spec_from_file_location("build_release_package", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_integrated_190_builder_identity_and_migration_boundary():
    builder = _builder()

    assert builder.VERSION == "1.9.0"
    assert builder.PREVIOUS_VERSION == "1.8.0"
    assert builder.TAG == "v1.9.0"
    assert builder.PRODUCTION_BASELINE_REVISION == "20260809_cargo_catalog_items"
    assert builder.DATABASE_REVISION == "20260818_immutable_fx_provenance"
    assert builder.UPGRADE_REVISIONS == [
        "20260810_logistics_network",
        "20260811_project_configuration",
        "security_credential_remediation",
        "20260812_operational_execution",
        "20260813_mdpm_readiness",
        "20260814_oip_situations",
        "20260815_oip_threshold_policy",
        "20260816_oip_projection_health",
        "20260817_shipment_economics_core",
        "20260818_immutable_fx_provenance",
    ]
    assert all(builder.migration_path(revision).is_file() for revision in builder.UPGRADE_REVISIONS)


def test_windows_npm_executable_is_used_for_build_and_fingerprint(monkeypatch):
    builder = _builder()
    expected = "npm.cmd" if os.name == "nt" else "npm"
    assert builder.NPM_EXECUTABLE == expected

    version_calls = []
    build_calls = []
    monkeypatch.setattr(builder, "run", lambda *args: version_calls.append(args) or "10.0.0")
    monkeypatch.setattr(
        builder.subprocess,
        "check_call",
        lambda args, cwd: build_calls.append((tuple(args), cwd)),
    )

    assert builder.npm_version() == "10.0.0"
    builder.build_frontend()

    assert version_calls == [(expected, "--version")]
    assert build_calls == [((expected, "run", "build"), builder.ROOT)]


def test_publication_runbooks_and_dependency_contract_are_190_coherent():
    for name in (
        "DEPLOYMENT.md",
        "ROLLBACK.md",
        "MIGRATION-PREFLIGHT.md",
        "SMOKE-TEST.md",
        "VERIFY-PACKAGE.ps1",
        "VERIFY-SERVER.ps1",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "1.9.0" in text or name == "VERIFY-PACKAGE.ps1"
        assert "20260818_immutable_fx_provenance" in text

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert "psycopg2-binary==2.9.11" in requirements
