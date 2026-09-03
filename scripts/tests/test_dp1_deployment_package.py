from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "deploy"


def text(name):
    return (DEPLOY / name).read_text(encoding="utf-8")


def test_dp1_scripts_pin_the_frozen_application_identity():
    joined = text("deploy_a257669.ps1") + text("validate_a257669.ps1")
    assert "S7-RC-a257669-rg1-frozen" in joined
    assert "a2576690364fcaf58ca7ddc6c57143c3084bbb00" in joined
    assert "aca7a147cad97edf0e3f03d763c63471c283f62021a23a4e6a47b5e59aa88534" in joined
    assert "20260908_governed_international_geography" in joined


def test_preflight_is_read_only_and_has_city_readiness_contract():
    source = text("preflight_a257669.ps1")
    prohibited = ("Set-Website", "Set-WebBinding", "Start-Process", "Stop-Process", "Restart-",
                  "Copy-Item", "Move-Item", "Remove-Item", "Expand-Archive", "New-Item")
    assert not any(token in source for token in prohibited)
    assert "BEGIN TRANSACTION READ ONLY" in source
    assert "country_id,un_locode" in source
    assert "BLOCKED_WITH_EXACT_REASON" in source


def test_mutation_boundary_and_db_rollback_rule_are_explicit():
    source = text("deploy_a257669.ps1")
    assert "-Execute" in source and "-ConfirmDeployment" in source
    assert "PRECHECK_COMPLETE" in source and "READY_FOR_FIRST_MUTATION" in source
    assert "KEEP_UPGRADED_DB_AND_ROLLBACK_APP" in source
