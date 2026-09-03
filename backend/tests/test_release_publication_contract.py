import importlib.util
import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]


def builder():
    path = ROOT / "scripts/build_release_package.py"
    spec = importlib.util.spec_from_file_location("build_release_package", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builder_is_generalized_and_pins_current_release_inputs():
    module = builder()
    assert not hasattr(module, "VERSION") and not hasattr(module, "TAG")
    assert module.EXPECTED_HEAD == "20260908_governed_international_geography"
    assert (
        module.BASELINE_VERSION
        == "china-iran-global-logistics-points-1.0.0-approved-baseline"
    )
    assert module.BASELINE_CHECKSUM.endswith("e09c7564690c7c")
    parser_source = (ROOT / "scripts/build_release_package.py").read_text(
        encoding="utf-8"
    )
    for option in (
        "--repository",
        "--authorized-commit",
        "--output-directory",
        "--release-label",
    ):
        assert option in parser_source


def test_builder_uses_platform_native_npm_and_fresh_build_contract():
    source = (ROOT / "scripts/build_release_package.py").read_text(encoding="utf-8")
    expected = 'npm = "npm.cmd" if os.name == "nt" else "npm"'
    assert expected in source
    assert '[npm, "ci"]' in source
    assert '[npm, "run", "test:frontend"]' in source
    assert '[npm, "run", "build"]' in source
    assert 'env["VITE_API_URL"] = "__FORWARDER_SAME_ORIGIN__"' in source
    assert "fresh dist/index.html is missing" in source
    assert "npm.cmd" if os.name == "nt" else "npm"


def test_builder_backend_qualification_has_progress_and_bounded_stall_diagnostics():
    source = (ROOT / "scripts/build_release_package.py").read_text(encoding="utf-8")
    assert '"-vv"' in source
    assert '"--durations=25"' in source
    assert '"faulthandler_timeout=120"' in source


def test_builder_packages_importer_migrations_baseline_dist_and_secret_verifier():
    source = (ROOT / "scripts/build_release_package.py").read_text(encoding="utf-8")
    for required in (
        "backend/migrations",
        "backend/reference_data",
        "dist/index.html",
        "backend/global_logistics_point_catalog.py",
        "backend/global_logistics_point_catalog_cli.py",
        "verify_package_secrets.py",
    ):
        assert required in source
    assert '".test." in relative.name' in source
    assert '"historical_security_remediation"' in source


def test_repository_has_one_expected_alembic_head():
    script = ScriptDirectory.from_config(
        Config(str(ROOT / "backend/migrations/alembic.ini"))
    )
    assert script.get_heads() == ["20260908_governed_international_geography"]


def test_packaged_frontend_is_pinned_to_same_origin():
    env_source = (ROOT / "src/lib/env.ts").read_text(encoding="utf-8")
    api_source = (ROOT / "src/lib/api.ts").read_text(encoding="utf-8")
    assert "import.meta.env.VITE_API_URL === '__FORWARDER_SAME_ORIGIN__'" in env_source
    assert "return import.meta.env.VITE_API_URL || '';" in env_source
    assert "env.API_URL.replace" in api_source
