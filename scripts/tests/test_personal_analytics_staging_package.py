from pathlib import Path
import json

import scripts.build_personal_analytics_staging_package as builder


ROOT=Path(__file__).resolve().parents[2]; PACKAGE=ROOT/"release-engineering"/builder.RC_ID

def test_operator_scripts_fail_closed_and_template_has_no_secret():
    preflight=(PACKAGE/"PRECHECK-STAGING.ps1").read_text(encoding="utf-8")
    migration=(PACKAGE/"MIGRATE-STAGING.ps1").read_text(encoding="utf-8")
    assert "Forwarder Backend Production" in preflight and "5101" in preflight
    assert "PREFLIGHT_READ_ONLY=PASS" in preflight and "ConfirmStagingMigration" in migration
    assert "<GENERATE_UNIQUE_STAGING_SECRET>" in (PACKAGE/"staging.env.template").read_text(encoding="utf-8")

def test_builder_pins_identity_and_writes_verifiable_manifest(tmp_path, monkeypatch):
    dist=ROOT/"dist"; dist.mkdir(exist_ok=True); index=dist/"index.html"
    existed=index.exists(); original=index.read_bytes() if existed else None
    index.write_text("fixture",encoding="utf-8")
    try:
        original_run = builder.run
        def controlled_run(*args):
            if args == ("git", "status", "--porcelain", "--untracked-files=no"):
                return ""
            return original_run(*args)
        monkeypatch.setattr(builder, "run", controlled_run)
        artifact, manifest=builder.build(tmp_path)
        data=json.loads(manifest.read_text(encoding="utf-8"))
        assert artifact.is_file() and data["rc_id"]==builder.RC_ID and data["source_commit"]==builder.COMMIT and data["alembic_head"]==builder.HEAD
    finally:
        if existed: index.write_bytes(original)
        else: index.unlink(); dist.rmdir()
