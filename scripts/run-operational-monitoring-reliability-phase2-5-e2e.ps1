[CmdletBinding()]
param(
  [switch]$FocusedFreshnessOnly,
  [switch]$FocusedReliabilityOnly
)

$ErrorActionPreference = 'Stop'
if ($FocusedFreshnessOnly -and $FocusedReliabilityOnly) {
  throw 'Choose only one focused qualification mode.'
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-monitoring-phase2-5-e2e-$runId"
$pgData = Join-Path $runtime 'pgdata'
$pgLog = Join-Path $runtime 'postgres.log'
$fixture = Join-Path $runtime 'fixtures.json'
$playwrightOutput = Join-Path $runtime 'playwright'
$databaseName = "forwarder_workspace_phase2_oip2_gate_$($runId.Substring(0, 10))"
$evidence = Join-Path $root 'docs\operational\evidence\operational-monitoring-reliability-phase-2-5-20260924'
$backend = $null
$frontend = $null
$postgresStarted = $false
$old = @{}
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

function Wait-Http([string]$Url, [int]$Seconds = 120) {
  $until = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      if ((Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3).StatusCode -lt 500) { return }
    } catch {}
    Start-Sleep -Milliseconds 350
  } while ((Get-Date) -lt $until)
  throw "Local readiness check timed out: $Url"
}

function Stop-OwnedProcess($Process) {
  if ($null -eq $Process) { return }
  $Process.Refresh()
  if (-not $Process.HasExited) {
    & taskkill.exe /PID $Process.Id /T /F *> $null
    [void]$Process.WaitForExit(10000)
  }
  $Process.Refresh()
  if (-not $Process.HasExited) { throw "runner-owned process $($Process.Id) is still running" }
}

function Remove-OwnedRuntime([string]$RuntimePath) {
  if (-not (Test-Path -LiteralPath $RuntimePath)) { return }
  $resolved = (Resolve-Path -LiteralPath $RuntimePath).Path
  $expectedParent = (Resolve-Path -LiteralPath $runtimeParent).Path
  $leaf = Split-Path -Leaf $resolved
  if ((Split-Path -Parent $resolved) -ne $expectedParent -or $leaf -notmatch '^forwarder-monitoring-phase2-5-e2e-[0-9a-f]{32}$') {
    throw "Refusing to remove an unowned runtime path: $resolved"
  }
  Remove-Item -LiteralPath $resolved -Recurse -Force
}

try {
  foreach ($tool in @('initdb.exe', 'pg_ctl.exe', 'createdb.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $pgBin $tool))) {
      throw "PostgreSQL 18 tool is unavailable: $tool"
    }
  }
  foreach ($name in @(
    'APP_ENV', 'DATABASE_URL', 'E2E_DATABASE_URL', 'OIP_POSTGRES_URL',
    'FORWARDER_E2E_PASSWORD', 'FORWARDER_E2E_CUSTOMER_PASSWORD',
    'FORWARDER_E2E_FIXTURE_PATH', 'OPERATIONAL_WORKSPACE_EVIDENCE_PATH',
    'OPERATIONAL_MONITORING_RELIABILITY_EVIDENCE_PATH', 'SECRET_KEY',
    'JWT_SECRET_KEY', 'E2E_SECRET_KEY', 'E2E_JWT_SECRET_KEY', 'CORS_ORIGINS',
    'VITE_BACKEND_URL', 'PORT', 'PLAYWRIGHT_BASE_URL',
    'PLAYWRIGHT_EXTERNAL_SERVER', 'PLAYWRIGHT_CHANNEL'
  )) { $old[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }

  New-Item -ItemType Directory -Force -Path $runtime, $playwrightOutput, $evidence | Out-Null
  $postgresPort = Get-FreeTcpPort
  $backendPort = Get-FreeTcpPort
  $frontendPort = Get-FreeTcpPort
  $databaseUrl = "postgresql://postgres@127.0.0.1:$postgresPort/$databaseName"
  $expertPassword = [guid]::NewGuid().ToString('N') + 'Qa9!'
  $customerPassword = [guid]::NewGuid().ToString('N') + 'Cu9!'
  $secret = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

  & (Join-Path $pgBin 'initdb.exe') -D $pgData -U postgres --auth-host=trust --auth-local=trust --encoding=UTF8 | Out-Null
  Assert-LastExit 'initialize owned PostgreSQL 18 cluster'
  $postgresOptions = "`"-h 127.0.0.1 -p $postgresPort`""
  $pgStart = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'start', '-D', $pgData, '-l', $pgLog, '-o', $postgresOptions, '-w' -PassThru -WindowStyle Hidden
  [void]$pgStart.WaitForExit(30000)
  $pgStart.Refresh()
  if ($pgStart.ExitCode -ne 0) { throw 'Qualification step failed: start owned PostgreSQL 18 cluster' }
  $postgresStarted = $true
  & (Join-Path $pgBin 'createdb.exe') -h 127.0.0.1 -p $postgresPort -U postgres $databaseName
  Assert-LastExit 'create owned Phase 2.5 database'

  $env:APP_ENV = 'uat'
  $env:DATABASE_URL = $databaseUrl
  $env:E2E_DATABASE_URL = $databaseUrl
  $env:OIP_POSTGRES_URL = $databaseUrl
  $env:FORWARDER_E2E_PASSWORD = $expertPassword
  $env:FORWARDER_E2E_CUSTOMER_PASSWORD = $customerPassword
  $env:FORWARDER_E2E_FIXTURE_PATH = $fixture
  $env:OPERATIONAL_WORKSPACE_EVIDENCE_PATH = $evidence
  $env:OPERATIONAL_MONITORING_RELIABILITY_EVIDENCE_PATH = $evidence
  $env:SECRET_KEY = $secret
  $env:JWT_SECRET_KEY = $secret
  $env:E2E_SECRET_KEY = $secret
  $env:E2E_JWT_SECRET_KEY = $secret
  $env:CORS_ORIGINS = "http://127.0.0.1:$frontendPort"
  $env:VITE_BACKEND_URL = "http://127.0.0.1:$backendPort"

  $repositoryHead = (python -m scripts.browser_migration_contract repository-head).Trim()
  Assert-LastExit 'resolve repository migration head'
  if ($repositoryHead -ne '20260929_operational_monitoring_reliability') {
    throw "Unexpected repository migration head: $repositoryHead"
  }
  python -m backend.migration_cli upgrade $repositoryHead --confirm
  Assert-LastExit 'clean PostgreSQL upgrade'
  python -m scripts.browser_migration_contract verify-database-head --expected $repositoryHead
  Assert-LastExit 'verify exact Phase 2.5 database head'
  if (-not $FocusedFreshnessOnly) {
    python -m alembic -c backend/migrations/alembic.ini downgrade 20260928_operational_workspace_phase2
    Assert-LastExit 'clean PostgreSQL downgrade'
    $downgradedStatus = python -m backend.migration_cli current
    Assert-LastExit 'verify downgraded database head'
    if (($downgradedStatus -join "`n") -notmatch 'current=20260928_operational_workspace_phase2') {
      throw 'Downgraded database is not at the expected Phase 2 parent.'
    }
    python -m backend.migration_cli upgrade $repositoryHead --confirm
    Assert-LastExit 'clean PostgreSQL re-upgrade'
    python -m scripts.browser_migration_contract verify-database-head --expected $repositoryHead
    Assert-LastExit 'verify re-upgraded database head'

    python -m pytest -q backend/tests/test_oip_races_postgresql.py
    Assert-LastExit 'PostgreSQL evaluation concurrency and idempotency races'
  }

  if ($FocusedReliabilityOnly) {
    Write-Output 'OPERATIONAL_MONITORING_POSTGRESQL_VERSION=18'
    Write-Output "OPERATIONAL_MONITORING_ALEMBIC_HEAD=$repositoryHead"
    Write-Output 'FOCUSED_POSTGRESQL_MIGRATION_ROUNDTRIP=PASS'
    Write-Output 'FOCUSED_POSTGRESQL_CONCURRENCY_FENCING=PASS'
  } else {
  python (Join-Path $root 'scripts\uat\seed_operational_workspace_phase2_e2e.py')
  Assert-LastExit 'seed synthetic Phase 2.5 fixtures'
  $manifest = Get-Content -LiteralPath $fixture -Raw | ConvertFrom-Json
  $before = python -m backend.operational_cli evaluation-status --organization-id $manifest.organization_id
  Assert-LastExit 'inspect stale evaluation status before browser-independent run'
  $before | Set-Content -LiteralPath (Join-Path $evidence 'status-before-background-evaluation.log') -Encoding UTF8
  $evaluation = python -m backend.operational_cli evaluate-sla --organization-id $manifest.organization_id --confirm
  Assert-LastExit 'run browser-independent evaluation'
  $evaluation | Set-Content -LiteralPath (Join-Path $evidence 'background-evaluation.log') -Encoding UTF8
  $after = python -m backend.operational_cli evaluation-status --organization-id $manifest.organization_id
  Assert-LastExit 'inspect recovered evaluation status'
  $after | Set-Content -LiteralPath (Join-Path $evidence 'status-after-background-evaluation.log') -Encoding UTF8

  $env:PORT = "$backendPort"
  $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'backend' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev', '--', '--host', '127.0.0.1', '--port', "$frontendPort", '--strictPort' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  Wait-Http "http://127.0.0.1:$backendPort/api/health"
  Wait-Http "http://127.0.0.1:$frontendPort"

  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
  $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
  $env:PLAYWRIGHT_CHANNEL = 'chrome'
  if (-not $FocusedFreshnessOnly) {
    npx playwright test e2e/operational-workspace-phase1.spec.ts e2e/operational-workspace-phase2.spec.ts --reporter=line --output $playwrightOutput
    Assert-LastExit 'real-browser Phase 1 and Phase 2 regression journeys'
  }
  npx playwright test e2e/operational-monitoring-reliability-phase2-5.spec.ts --reporter=line --output $playwrightOutput
  Assert-LastExit 'real-browser reliability product journey'

  $resultFile = if ($FocusedFreshnessOnly) { 'focused-control-tower-freshness-result.json' } else { 'result.json' }
  $journeys = @(
    'background evaluation before browser startup creates current Attention',
    'Workspace displays current background-evaluated Action Attention',
    'Workspace displays an honest stale evaluation warning',
    'Control Tower consumes the same stale evaluation health'
  )
  if (-not $FocusedFreshnessOnly) {
    $journeys += 'Workspace Phase 1 and Phase 2 browser regressions'
  }
  [pscustomobject]@{
    result = 'PASS'
    qualification_scope = if ($FocusedFreshnessOnly) { 'focused Control Tower freshness scenario' } else { 'complete Phase 2.5 browser qualification' }
    executed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    environment = 'owned disposable local/UAT PostgreSQL'
    postgresql_major = 18
    alembic_head = $repositoryHead
    migration_roundtrip = if ($FocusedFreshnessOnly) { 'NOT_RUN_FOCUSED_SCENARIO' } else { 'PASS' }
    browser_independent_cli_evaluation = 'PASS'
    postgresql_concurrency = if ($FocusedFreshnessOnly) { 'NOT_RUN_FOCUSED_SCENARIO' } else { 'PASS' }
    browser = 'Google Chrome via Playwright'
    synthetic_data_only = $true
    production_accessed = $false
    product_journeys = $journeys
  } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidence $resultFile) -Encoding UTF8

  Write-Output 'OPERATIONAL_MONITORING_POSTGRESQL_VERSION=18'
  Write-Output "OPERATIONAL_MONITORING_ALEMBIC_HEAD=$repositoryHead"
  Write-Output 'OPERATIONAL_MONITORING_PHASE2_5_BROWSER_QUALIFICATION=PASS'
  if ($FocusedFreshnessOnly) { Write-Output 'CONTROL_TOWER_FRESHNESS_SCENARIO=PASS' }
  Write-Output "OPERATIONAL_MONITORING_EVIDENCE_DIRECTORY=$evidence"
  }
}
finally {
  foreach ($process in @($frontend, $backend)) {
    try { Stop-OwnedProcess $process } catch { $cleanupFailures.Add($_.Exception.Message) }
  }
  if ($postgresStarted) {
    try {
      $pgStop = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'stop', '-D', $pgData, '-m', 'fast', '-w' -PassThru -WindowStyle Hidden
      [void]$pgStop.WaitForExit(30000)
      $pgStop.Refresh()
      if ($pgStop.ExitCode -ne 0) { throw 'owned PostgreSQL did not stop cleanly' }
    } catch { $cleanupFailures.Add($_.Exception.Message) }
  }
  try { Remove-OwnedRuntime $runtime } catch { $cleanupFailures.Add($_.Exception.Message) }
  foreach ($name in $old.Keys) {
    if ($null -eq $old[$name]) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
    else { [Environment]::SetEnvironmentVariable($name, $old[$name], 'Process') }
  }
  if ($cleanupFailures.Count -gt 0) {
    throw ('OPERATIONAL_MONITORING_PHASE2_5_E2E_CLEANUP=FAIL: ' + ($cleanupFailures -join '; '))
  }
  Write-Output 'OPERATIONAL_MONITORING_PHASE2_5_E2E_CLEANUP=PASS'
}
