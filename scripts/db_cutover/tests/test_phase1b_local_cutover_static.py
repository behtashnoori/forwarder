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
    assert "$process.StandardOutput.ReadToEndAsync()" in SCRIPT
    assert "$process.StandardError.ReadToEndAsync()" in SCRIPT
    assert "$process.WaitForExit($TimeoutSeconds * 1000)" in SCRIPT
    assert "Stop-ProcessTree $process" in SCRIPT
    assert 'Write-StageEvent "PROCESS_TIMEOUT" $operationName' in SCRIPT


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


def test_failed_transfer_prints_only_sanitized_mapping_decisions():
    assert "function Write-SanitizedMappingBlockers" in SCRIPT
    assert '"mapping-contract.json"' in SCRIPT
    assert '"blocked.json"' in SCRIPT
    assert "MAPPING_BLOCKED table={0} reason={1}" in SCRIPT
    assert "Write-SanitizedMappingBlockers $path" in SCRIPT


def _run_powershell_harness(tmp_path, body):
    harness = tmp_path / "cutover-harness.ps1"
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
function Get-ToolFunctionText([string[]]$Names) {{
    $functions = $ast.FindAll({{
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $Names -contains $node.Name
    }}, $true)
    foreach ($function in $functions) {{ $function.Extent.Text }}
}}
{body}
""",
        encoding="utf-8",
    )
    return subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(harness),
        ],
        text=True, capture_output=True, check=False,
    )


def test_mock_dryrun_success_stages_and_cleanup(tmp_path):
    completed = _run_powershell_harness(
        tmp_path,
        r"""
Invoke-Expression ((Get-ToolFunctionText @('Invoke-DryRunWorkflow')) -join "`n")
$events = New-Object System.Collections.Generic.List[string]
$Rehearsal = 'forwarder_phase1b_rehearsal_mock'
function Invoke-Stage([string]$Stage, [scriptblock]$Action) {
    $events.Add("START:$Stage")
    & $Action
    $events.Add("COMPLETE:$Stage")
}
function New-Database([string]$Name) { $events.Add('CREATE') }
function Invoke-Migration([string]$Name) { $events.Add('MIGRATION_COMPLETE') }
function Invoke-Transfer([string]$Mode, [string]$Name, [string]$Evidence) {
    $events.Add('ANALYSIS_EXIT_0')
    $events.Add('MAPPING_COMPLETE')
}
function Remove-DisposableDatabase([string]$Name) { $events.Add('CLEANUP_COMPLETE') }
function Invoke-RenameCutover { $events.Add('MAIN_CHANGED') }
Invoke-DryRunWorkflow
$required = @(
    'MIGRATION_COMPLETE', 'ANALYSIS_EXIT_0', 'MAPPING_COMPLETE',
    'CLEANUP_COMPLETE'
)
if (@($required | Where-Object { -not $events.Contains($_) }).Count -ne 0) { exit 20 }
if ($events.Contains('MAIN_CHANGED')) { exit 21 }
""",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_native_timeout_stops_process_and_dryrun_cleanup_runs(tmp_path):
    evidence = (tmp_path / "evidence").as_posix()
    completed = _run_powershell_harness(
        tmp_path,
        rf"""
Invoke-Expression ((Get-ToolFunctionText @(
    'Write-StageEvent', 'Stop-ProcessTree', 'Invoke-Native',
    'Invoke-DryRunWorkflow'
)) -join "`n")
$EvidenceRoot = '{evidence}'
New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
$script:PlainPassword = $null
$Rehearsal = 'forwarder_phase1b_rehearsal_mock'
$cleanup = $false
$mainChanged = $false
function Invoke-Stage([string]$Stage, [scriptblock]$Action) {{ & $Action }}
function New-Database([string]$Name) {{ }}
function Invoke-Migration([string]$Name) {{
    Invoke-Native -File 'powershell.exe' -Arguments @(
        '-NoProfile', '-Command', 'Start-Sleep -Seconds 30'
    ) -Operation 'mock-analysis' -TimeoutSeconds 1 | Out-Null
}}
function Invoke-Transfer([string]$Mode, [string]$Name, [string]$Evidence) {{ }}
function Remove-DisposableDatabase([string]$Name) {{ $script:cleanup = $true }}
function Invoke-RenameCutover {{ $script:mainChanged = $true }}
$timedOut = $false
try {{
    Invoke-DryRunWorkflow
}} catch {{
    $timedOut = $_.Exception.Message -match 'PROCESS_TIMEOUT:mock-analysis'
}}
if (-not $timedOut) {{ exit 30 }}
if (-not $script:cleanup) {{ exit 31 }}
if ($script:mainChanged) {{ exit 32 }}
$log = Get-Content -Raw -LiteralPath (Join-Path $EvidenceRoot 'stage-events.log')
if ($log -notmatch 'PROCESS_TIMEOUT=mock-analysis') {{ exit 33 }}
""",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
