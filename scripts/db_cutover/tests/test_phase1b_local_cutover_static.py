from pathlib import Path
import re


SCRIPT = (Path(__file__).parents[1] / "phase1b_local_cutover.ps1").read_text(encoding="utf-8")


def test_credential_fixture_uses_secure_prompt_and_child_only_password():
    assert 'Read-Host "PostgreSQL password for $PostgresUser" -AsSecureString' in SCRIPT
    assert 'EnvironmentVariables["PGPASSWORD"]' in SCRIPT
    assert "ZeroFreeBSTR" in SCRIPT
    assert "Write-Host $script:PlainPassword" not in SCRIPT
    assert "-Password" not in SCRIPT


def test_native_process_transport_is_shell_free_and_separates_streams():
    assert "System.Diagnostics.ProcessStartInfo" in SCRIPT
    assert "$psi.UseShellExecute = $false" in SCRIPT
    assert "$psi.RedirectStandardOutput = $true" in SCRIPT
    assert "$psi.RedirectStandardError = $true" in SCRIPT
    assert "$process.StandardInput.Write($InputText)" in SCRIPT
    assert "$psi.ArgumentList" not in SCRIPT


def test_legacy_main_is_never_migrated_or_dropped():
    assert 'Assert-True ($Database -ne $Source) "legacy Main migration is forbidden"' in SCRIPT
    assert not re.search(r'DROP DATABASE (?:IF EXISTS )?`?"?\$Source', SCRIPT, re.I)
    assert "backend.migration_cli" in SCRIPT
    assert "alembic stamp" not in SCRIPT.lower()


def test_final_mode_requires_confirmation_and_all_gates():
    assert 'Assert-True $ConfirmCutover "Final mode requires -ConfirmCutover"' in SCRIPT
    for gate in (
        "mapping incomplete", "rejected rows detected", "orphan FK detected",
        "constraint violation detected", "unexplained variance detected",
        "backend_tests", "frontend_tests", "health", "login", "crm",
        "shipment", "quote", "operational_shipment", "multileg",
    ):
        assert gate in SCRIPT


def test_preflight_preserves_baseline_lineage_after_tool_commit():
    assert "git merge-base --is-ancestor $ExpectedHead HEAD" in SCRIPT
    assert '((git rev-parse HEAD) -eq $ExpectedHead)' not in SCRIPT


def test_full_tests_are_not_pointed_at_transferred_database():
    pytest_call = 'Invoke-Native -File $Python -Arguments @("-m", "pytest", "-q")'
    assert pytest_call in SCRIPT
    assert '"TEST_DATABASE_URL"=$dsn' not in SCRIPT


def test_all_script_blocks_start_at_repository_location():
    assert SCRIPT.startswith('Set-Location "D:\\1-webapp\\15-forwarder"')
