[CmdletBinding()]
param(
  [string]$EvidenceDirectory = ''
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-expert-baseline-$runId"
$pgData = Join-Path $runtime 'pgdata'
$pgLog = Join-Path $runtime 'postgres.log'
$databaseName = "forwarder_expert_baseline_test_$($runId.Substring(0, 12))"
$evidence = if ([string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
  Join-Path $root 'docs\operational\evidence\expert-operational-baseline-reconciliation-20261001\qualification'
} else {
  [System.IO.Path]::GetFullPath($EvidenceDirectory)
}
$postgresStarted = $false
$oldDatabaseUrl = [Environment]::GetEnvironmentVariable('FORWARDER_EXPERT_BASELINE_POSTGRES_URL', 'Process')
$cleanupFailures = [System.Collections.Generic.List[string]]::new()

function Assert-LastExit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "Qualification step failed: $Step" }
}

function Get-FreeTcpPort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  try { return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port }
  finally { $listener.Stop() }
}

function Remove-OwnedRuntime([string]$RuntimePath) {
  if (-not (Test-Path -LiteralPath $RuntimePath)) { return }
  $resolved = (Resolve-Path -LiteralPath $RuntimePath).Path
  $expectedParent = (Resolve-Path -LiteralPath $runtimeParent).Path
  $leaf = Split-Path -Leaf $resolved
  if ((Split-Path -Parent $resolved) -ne $expectedParent -or $leaf -notmatch '^forwarder-expert-baseline-[0-9a-f]{32}$') {
    throw "Refusing to remove an unowned runtime path: $resolved"
  }
  Remove-Item -LiteralPath $resolved -Recurse -Force
}

$focusedCases = @(
  'backend/tests/test_operational_vertical_slice.py::test_expert_operational_baseline_allows_direct_creation',
  'backend/tests/test_execution_authority_3a.py::test_legacy_route_occurrence_endpoint_accepts_public_milestone_identity',
  'backend/tests/test_phase3_reported_facts.py::test_http_owner_only_reopen_and_cross_tenant_fail_closed',
  'backend/tests/test_organization_shipment_stages.py::test_exact_closure_refusal_warning_only_success_and_unified_history',
  'backend/tests/test_phase3_cargo_delivery.py::test_http_permissions_replay_correction_conflict_and_reload',
  'backend/tests/test_phase3_closure.py::test_normal_close_idempotency_terminal_and_pinned_policy',
  'backend/tests/test_phase3_closure.py::test_policy_and_close_authority_no_store_and_pure_read',
  'backend/tests/test_expert_membership_permissions.py::test_organization_expert_provisioning_receives_operational_baseline',
  'backend/tests/test_admin_capability_composition.py::test_system_admin_has_no_implicit_tenant_capability',
  'backend/tests/test_phase3_closure.py::test_live_authority_denies_close_without_partial_evidence[cross_tenant]',
  'backend/tests/test_execution_authority_3a.py::test_leg_guard_and_explicit_shipment_cancel[cancelled]',
  'backend/tests/test_organization_shipment_stages.py::test_projectless_configuration_order_authority_pinning_and_immutability',
  'backend/tests/test_admin_capability_composition.py::test_bootstrap_composes_both_capabilities_idempotently_with_audit'
)

try {
  foreach ($tool in @('initdb.exe', 'pg_ctl.exe', 'createdb.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $pgBin $tool))) {
      throw "PostgreSQL 18 tool is unavailable: $tool"
    }
  }
  New-Item -ItemType Directory -Force -Path $runtime, $evidence | Out-Null
  $postgresPort = Get-FreeTcpPort
  $databaseUrl = "postgresql://postgres@127.0.0.1:$postgresPort/$databaseName"

  & (Join-Path $pgBin 'initdb.exe') -D $pgData -U postgres --auth-host=trust --auth-local=trust --encoding=UTF8 | Out-Null
  Assert-LastExit 'initialize owned PostgreSQL 18 cluster'
  $postgresOptions = "`"-h 127.0.0.1 -p $postgresPort`""
  $pgStart = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'start', '-D', $pgData, '-l', $pgLog, '-o', $postgresOptions, '-w' -PassThru -WindowStyle Hidden
  [void]$pgStart.WaitForExit(30000)
  $pgStart.Refresh()
  if ($pgStart.ExitCode -ne 0) { throw 'Qualification step failed: start owned PostgreSQL 18 cluster' }
  $postgresStarted = $true
  & (Join-Path $pgBin 'createdb.exe') -h 127.0.0.1 -p $postgresPort -U postgres $databaseName
  Assert-LastExit 'create owned Expert baseline database'

  $env:FORWARDER_EXPERT_BASELINE_POSTGRES_URL = $databaseUrl
  python -m pytest -q backend/tests/test_expert_operational_baseline_postgresql.py 2>&1 |
    Tee-Object -LiteralPath (Join-Path $evidence 'postgresql-focused.log')
  Assert-LastExit 'PostgreSQL Expert baseline proof'

  python -m pytest -q @focusedCases 2>&1 |
    Tee-Object -LiteralPath (Join-Path $evidence 'authorization-cases.log')
  Assert-LastExit '13 focused authorization cases'

  $repositoryHead = (python -m scripts.browser_migration_contract repository-head).Trim()
  Assert-LastExit 'resolve repository migration head'
  $serverVersion = (& (Join-Path $pgBin 'psql.exe') -h 127.0.0.1 -p $postgresPort -U postgres -d $databaseName -Atc 'SHOW server_version;').Trim()
  Assert-LastExit 'read PostgreSQL version'

  [pscustomobject]@{
    result = 'PASS'
    executed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    product_sha = (git -C $root rev-parse HEAD).Trim()
    environment = 'owned disposable local PostgreSQL'
    postgresql_version = $serverVersion
    alembic_head = $repositoryHead
    postgresql_baseline_test_count = 1
    focused_authorization_case_count = $focusedCases.Count
    focused_authorization_cases = $focusedCases
    production_accessed = $false
    preserved_walkthrough_accessed = $false
    business_actions_on_preserved_walkthrough = 0
  } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $evidence 'result.json') -Encoding UTF8

  Write-Output 'EXPERT_BASELINE_FOCUSED_AUTHORIZATION=PASS'
  Write-Output "EXPERT_BASELINE_POSTGRESQL_VERSION=$serverVersion"
  Write-Output "EXPERT_BASELINE_ALEMBIC_HEAD=$repositoryHead"
  Write-Output "EXPERT_BASELINE_EVIDENCE_DIRECTORY=$evidence"
}
finally {
  if ($postgresStarted) {
    try {
      $pgStop = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'stop', '-D', $pgData, '-m', 'fast', '-w' -PassThru -WindowStyle Hidden
      [void]$pgStop.WaitForExit(30000)
      $pgStop.Refresh()
      if ($pgStop.ExitCode -ne 0) { throw 'owned PostgreSQL did not stop cleanly' }
    } catch { $cleanupFailures.Add($_.Exception.Message) }
  }
  try { Remove-OwnedRuntime $runtime } catch { $cleanupFailures.Add($_.Exception.Message) }
  if ($null -eq $oldDatabaseUrl) {
    Remove-Item 'Env:FORWARDER_EXPERT_BASELINE_POSTGRES_URL' -ErrorAction SilentlyContinue
  } else {
    [Environment]::SetEnvironmentVariable('FORWARDER_EXPERT_BASELINE_POSTGRES_URL', $oldDatabaseUrl, 'Process')
  }
  if ($cleanupFailures.Count -gt 0) {
    throw ('EXPERT_BASELINE_QUALIFICATION_CLEANUP=FAIL: ' + ($cleanupFailures -join '; '))
  }
  Write-Output 'EXPERT_BASELINE_QUALIFICATION_CLEANUP=PASS'
}
