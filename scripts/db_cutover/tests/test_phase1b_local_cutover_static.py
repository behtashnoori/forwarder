from pathlib import Path
import re
import subprocess


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


def test_active_head_normalization_regression(tmp_path):
    harness = tmp_path / "head-normalization-regression.ps1"
    tool_path = Path(__file__).parents[1] / "phase1b_local_cutover.ps1"
    harness.write_text(
        f"""
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    '{tool_path.as_posix()}',
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {{ exit 10 }}
$names = @('Assert-True', 'Resolve-ActiveMigrationHead')
$functions = $ast.FindAll({{
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $names -contains $node.Name
}}, $true)
foreach ($function in $functions) {{ Invoke-Expression $function.Extent.Text }}
$ActiveHead = '20260801_route_exception'
$cases = @(
    @{{ Name='valid'; Values=@('20260801_route_exception (head)'); Pass=$true }},
    @{{ Name='whitespace'; Values=@('  20260801_route_exception (head)  '); Pass=$true }},
    @{{ Name='informational'; Values=@("informational line`n20260801_route_exception (head)"); Pass=$true }},
    @{{ Name='empty'; Values=@(); Pass=$false }},
    @{{ Name='two'; Values=@('20260801_route_exception (head)', 'other (head)'); Pass=$false }},
    @{{ Name='different'; Values=@('other (head)'); Pass=$false }}
)
foreach ($case in $cases) {{
    $passed = $false
    $objectArrayError = $false
    try {{
        $value = Resolve-ActiveMigrationHead -RawHeadOutput @($case.Values)
        $passed = [string]::Equals(
            [string]$value,
            $ActiveHead,
            [System.StringComparison]::Ordinal
        )
    }} catch {{
        $objectArrayError = $_.Exception.Message -match 'System.Object\\[\\].*System.Boolean'
    }}
    if ($objectArrayError -or $passed -ne $case.Pass) {{
        Write-Error "case failed: $($case.Name)"
        exit 11
    }}
}}
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_alembic_head_exit_code_is_checked_separately():
    assert '"-m", "alembic", "-c", "backend/migrations/alembic.ini", "heads"' in SCRIPT
    assert "-Condition ([bool]($headResult.ExitCode -eq 0))" in SCRIPT
    assert "Resolve-ActiveMigrationHead -RawHeadOutput @($headResult.StdOut)" in SCRIPT
