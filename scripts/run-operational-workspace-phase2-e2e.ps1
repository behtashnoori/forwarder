[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-workspace-phase2-e2e-$runId"
$pgData = Join-Path $runtime 'pgdata'
$pgLog = Join-Path $runtime 'postgres.log'
$fixture = Join-Path $runtime 'fixtures.json'
$playwrightOutput = Join-Path $runtime 'playwright'
$databaseName = "forwarder_workspace_phase2_$($runId.Substring(0, 12))"
$evidence = Join-Path $root 'docs\operational\evidence\operational-workspace-phase-2-20260924\browser'
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
  if ((Split-Path -Parent $resolved) -ne $expectedParent -or $leaf -notmatch '^forwarder-workspace-phase2-e2e-[0-9a-f]{32}$') {
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
    'APP_ENV', 'DATABASE_URL', 'E2E_DATABASE_URL', 'FORWARDER_E2E_PASSWORD',
    'FORWARDER_E2E_CUSTOMER_PASSWORD', 'FORWARDER_E2E_FIXTURE_PATH',
    'OPERATIONAL_WORKSPACE_EVIDENCE_PATH', 'SECRET_KEY', 'JWT_SECRET_KEY',
    'E2E_SECRET_KEY', 'E2E_JWT_SECRET_KEY', 'CORS_ORIGINS', 'VITE_BACKEND_URL',
    'PORT', 'PLAYWRIGHT_BASE_URL', 'PLAYWRIGHT_EXTERNAL_SERVER', 'PLAYWRIGHT_CHANNEL'
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
  Assert-LastExit 'create owned Workspace Phase 2 database'

  $env:APP_ENV = 'uat'
  $env:DATABASE_URL = $databaseUrl
  $env:E2E_DATABASE_URL = $databaseUrl
  $env:FORWARDER_E2E_PASSWORD = $expertPassword
  $env:FORWARDER_E2E_CUSTOMER_PASSWORD = $customerPassword
  $env:FORWARDER_E2E_FIXTURE_PATH = $fixture
  $env:OPERATIONAL_WORKSPACE_EVIDENCE_PATH = $evidence
  $env:SECRET_KEY = $secret
  $env:JWT_SECRET_KEY = $secret
  $env:E2E_SECRET_KEY = $secret
  $env:E2E_JWT_SECRET_KEY = $secret
  $env:CORS_ORIGINS = "http://127.0.0.1:$frontendPort"
  $env:VITE_BACKEND_URL = "http://127.0.0.1:$backendPort"

  $repositoryHead = (python -m scripts.browser_migration_contract repository-head).Trim()
  Assert-LastExit 'resolve repository migration head'
  if ($repositoryHead -ne '20260928_operational_workspace_phase2') {
    throw "Unexpected repository migration head: $repositoryHead"
  }
  python -m backend.migration_cli upgrade $repositoryHead --confirm
  Assert-LastExit 'migrate owned Workspace Phase 2 database'
  python -m scripts.browser_migration_contract verify-database-head --expected $repositoryHead
  Assert-LastExit 'verify exact Workspace Phase 2 database head'
  python (Join-Path $root 'scripts\uat\seed_operational_workspace_phase2_e2e.py')
  Assert-LastExit 'seed synthetic Workspace Phase 2 fixtures'

  $env:PORT = "$backendPort"
  $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'backend' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev', '--', '--host', '127.0.0.1', '--port', "$frontendPort", '--strictPort' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  Wait-Http "http://127.0.0.1:$backendPort/api/health"
  Wait-Http "http://127.0.0.1:$frontendPort"

  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
  $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
  $env:PLAYWRIGHT_CHANNEL = 'chrome'
  npx playwright test e2e/operational-workspace-phase1.spec.ts e2e/operational-workspace-phase2.spec.ts --reporter=line --output $playwrightOutput
  Assert-LastExit 'real-browser Workspace Phase 1 and Phase 2 product journeys'

  [pscustomobject]@{
    result = 'PASS'
    executed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    environment = 'owned disposable local/UAT PostgreSQL'
    postgresql_major = 18
    alembic_head = $repositoryHead
    browser = 'Google Chrome via Playwright'
    synthetic_data_only = $true
    production_accessed = $false
    product_journeys = @(
      'organization-admin SLA create, prospective version update, and history',
      'tenant isolation and fixed shipment-owner authorization',
      'healthy, warning, and breached SLA evaluation without false SLA risk',
      'exception impact and evidence capture',
      'Action creation, follow-up, independent resolution, and preserved history',
      'Workspace explainable Attention and Control Tower integration',
      'Customer Account and Public Tracking regressions'
    )
  } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidence 'result.json') -Encoding UTF8

  Write-Output "OPERATIONAL_WORKSPACE_POSTGRESQL_VERSION=18"
  Write-Output "OPERATIONAL_WORKSPACE_ALEMBIC_HEAD=$repositoryHead"
  Write-Output 'OPERATIONAL_WORKSPACE_PHASE2_BROWSER_QUALIFICATION=PASS'
  Write-Output "OPERATIONAL_WORKSPACE_EVIDENCE_DIRECTORY=$evidence"
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
    throw ('OPERATIONAL_WORKSPACE_PHASE2_E2E_CLEANUP=FAIL: ' + ($cleanupFailures -join '; '))
  }
  Write-Output 'OPERATIONAL_WORKSPACE_PHASE2_E2E_CLEANUP=PASS'
}
