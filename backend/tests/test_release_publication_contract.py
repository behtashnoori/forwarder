import importlib.util
import os
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[2]


def _builder():
    path = ROOT / "scripts" / "build_release_package.py"
    spec = importlib.util.spec_from_file_location("build_release_package", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_integrated_1951_builder_identity_with_migration():
    builder = _builder()

    assert builder.VERSION == "1.9.5.1"
    assert builder.PREVIOUS_VERSION == "1.9.5"
    assert builder.TAG == "v1.9.5.1"
    assert builder.PRODUCTION_BASELINE_REVISION == "20260827_org_hostname"
    assert builder.DATABASE_REVISION == "20260828_referral_state_compat"
    assert builder.UPGRADE_REVISIONS == ["20260828_referral_state_compat"]
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
        lambda args, cwd, env: build_calls.append((tuple(args), cwd, env)),
    )

    assert builder.npm_version() == "10.0.0"
    builder.build_frontend()

    assert version_calls == [(expected, "--version")]
    assert len(build_calls) == 1
    args, cwd, build_env = build_calls[0]
    assert args == (expected, "run", "build")
    assert cwd == builder.ROOT
    assert build_env["VITE_API_URL"] == "__FORWARDER_SAME_ORIGIN__"


def test_packaged_frontend_is_pinned_to_same_origin():
    env_source = (ROOT / "src" / "lib" / "env.ts").read_text(encoding="utf-8")
    api_source = (ROOT / "src" / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_URL === '__FORWARDER_SAME_ORIGIN__'" in env_source
    assert "return import.meta.env.VITE_API_URL || '';" in env_source
    assert "env.API_URL.replace" in api_source
    assert "API URL is not configured" not in api_source


def test_complete_release_directory_is_promoted_without_copying(tmp_path):
    builder = _builder()
    staging = tmp_path / ".release-staging"
    final = tmp_path / "release-final"
    (staging / "assets").mkdir(parents=True)
    (staging / "release-manifest.json").write_text("complete\n", encoding="utf-8")
    (staging / "assets" / "application.js").write_bytes(b"immutable-content")

    assert not final.exists()
    builder.promote_release_directory(staging, final)

    assert not staging.exists()
    assert (final / "release-manifest.json").read_text(encoding="utf-8") == "complete\n"
    assert (final / "assets" / "application.js").read_bytes() == b"immutable-content"


def test_release_promotion_refuses_existing_final_and_keeps_staging(tmp_path):
    builder = _builder()
    staging = tmp_path / ".release-staging"
    final = tmp_path / "release-final"
    staging.mkdir()
    final.mkdir()
    (staging / "new.txt").write_text("new", encoding="utf-8")
    (final / "existing.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        builder.promote_release_directory(staging, final)

    assert (staging / "new.txt").read_text(encoding="utf-8") == "new"
    assert (final / "existing.txt").read_text(encoding="utf-8") == "existing"


def test_release_promotion_requires_sibling_directories(tmp_path):
    builder = _builder()
    staging = tmp_path / "staging-parent" / ".release-staging"
    final = tmp_path / "final-parent" / "release-final"
    staging.mkdir(parents=True)

    with pytest.raises(ValueError, match="must be siblings"):
        builder.promote_release_directory(staging, final)

    assert staging.is_dir()
    assert not final.exists()


def test_release_promotion_requires_existing_staging_directory(tmp_path):
    builder = _builder()
    staging = tmp_path / ".release-staging"
    final = tmp_path / "release-final"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        builder.promote_release_directory(staging, final)

    assert not final.exists()


def test_failed_release_promotion_is_cleaned_by_staging_context(tmp_path, monkeypatch):
    builder = _builder()
    final = tmp_path / "release-final"

    with pytest.raises(PermissionError, match="simulated rename failure"):
        with builder.tempfile.TemporaryDirectory(
            prefix=".release-final-staging-", dir=tmp_path
        ) as temporary:
            staging = Path(temporary)
            (staging / "release-manifest.json").write_text("complete\n", encoding="utf-8")
            monkeypatch.setattr(
                builder.os,
                "rename",
                lambda source, destination: (_ for _ in ()).throw(
                    PermissionError("simulated rename failure")
                ),
            )
            builder.promote_release_directory(staging, final)

    assert not final.exists()
    assert not list(tmp_path.glob(".release-final-staging-*"))


def test_vite_does_not_watch_immutable_release_staging_directories():
    config = (ROOT / "vite.config.ts").read_text(encoding="utf-8")

    assert 'ignored: ["**/.release-v*-staging-*"]' in config


def test_publication_runbooks_and_dependency_contract_are_1951_coherent():
    for name in (
        "DEPLOYMENT.md",
        "ROLLBACK.md",
        "MIGRATION-PREFLIGHT.md",
        "SMOKE-TEST.md",
        "VERIFY-PACKAGE.ps1",
        "VERIFY-SERVER.ps1",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "1.9.5.1" in text
        assert "20260828_referral_state_compat" in text

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert "psycopg2-binary==2.9.11" in requirements


def test_package_builder_includes_fail_closed_secret_verifier():
    builder = (ROOT / "scripts" / "build_release_package.py").read_text(encoding="utf-8")
    verifier = (ROOT / "VERIFY-PACKAGE.ps1").read_text(encoding="utf-8")
    assert '"verify_package_secrets.py"' in builder
    assert '"verify_package_secrets.py"' in verifier
    assert "Package secret policy failed" in verifier
    assert '$_.Extension -in @(\'.ps1\',\'.bat\',\'.cmd\',\'.yml\',\'.yaml\')' in verifier
    assert '$seedControlFiles = @("VERIFY-PACKAGE.ps1", "VERIFY-SERVER.ps1")' in verifier


def test_release_upgrade_chain_is_contiguous_and_remediation_is_mandatory():
    builder = _builder()
    config = Config(str(ROOT / "backend" / "migrations" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    revisions = list(
        reversed(
            [
                item.revision
                for item in script.iterate_revisions(
                    builder.DATABASE_REVISION, builder.PRODUCTION_BASELINE_REVISION
                )
            ]
        )
    )
    assert revisions == builder.UPGRADE_REVISIONS
    assert script.get_revision(builder.DATABASE_REVISION) is not None
    assert script.get_heads() == ["20260906_global_logistics_point_materialization"]
