[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-mt3-public-tracking-$runId"
$pgData = Join-Path $runtime 'pgdata'
$pgLog = Join-Path $runtime 'postgres.log'
$fixture = Join-Path $runtime 'fixtures.json'
$evidence = Join-Path $root "test-results\mt3-public-tracking-security-$runId"
$databaseName = "forwarder_mt3_$($runId.Substring(0, 12))"
$backend = $null
$frontend = $null
$postgresStarted = $false
$old = @{}

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
}

function Remove-OwnedRuntime([string]$RuntimePath) {
  if (-not (Test-Path -LiteralPath $RuntimePath)) { return }
  $resolved = (Resolve-Path -LiteralPath $RuntimePath).Path
  $expectedParent = (Resolve-Path -LiteralPath $runtimeParent).Path
  $leaf = Split-Path -Leaf $resolved
  if ((Split-Path -Parent $resolved) -ne $expectedParent -or $leaf -notmatch '^forwarder-mt3-public-tracking-[0-9a-f]{32}$') {
    throw "Refusing to remove an unowned runtime path: $resolved"
  }
  Remove-Item -LiteralPath $resolved -Recurse -Force
}

try {
  foreach ($tool in @('initdb.exe', 'pg_ctl.exe', 'createdb.exe', 'psql.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $pgBin $tool))) {
      throw "PostgreSQL 18 tool is unavailable: $tool"
    }
  }
  foreach ($name in @(
    'APP_ENV', 'DATABASE_URL', 'E2E_DATABASE_URL', 'MT3_TEST_DATABASE_URL',
    'MT3_E2E_FIXTURE_PATH', 'SECRET_KEY', 'JWT_SECRET_KEY', 'E2E_SECRET_KEY',
    'E2E_JWT_SECRET_KEY', 'CORS_ORIGINS', 'VITE_BACKEND_URL', 'PORT',
    'PLAYWRIGHT_BASE_URL', 'PLAYWRIGHT_EXTERNAL_SERVER', 'PLAYWRIGHT_CHANNEL'
  )) {
    $old[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  }

  New-Item -ItemType Directory -Force -Path $runtime, $evidence | Out-Null
  $postgresPort = Get-FreeTcpPort
  $backendPort = Get-FreeTcpPort
  $frontendPort = Get-FreeTcpPort
  $databaseUrl = "postgresql://postgres@127.0.0.1:$postgresPort/$databaseName"
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
  Assert-LastExit 'create owned MT-3 database'

  $env:APP_ENV = 'uat'
  $env:DATABASE_URL = $databaseUrl
  $env:E2E_DATABASE_URL = $databaseUrl
  $env:MT3_TEST_DATABASE_URL = $databaseUrl
  $env:MT3_E2E_FIXTURE_PATH = $fixture
  $env:SECRET_KEY = $secret
  $env:JWT_SECRET_KEY = $secret
  $env:E2E_SECRET_KEY = $secret
  $env:E2E_JWT_SECRET_KEY = $secret
  $env:CORS_ORIGINS = "http://127.0.0.1:$frontendPort"
  $env:VITE_BACKEND_URL = "http://127.0.0.1:$backendPort"

  $repositoryHead = (python -m scripts.browser_migration_contract repository-head).Trim()
  Assert-LastExit 'resolve repository migration head'
  if ($repositoryHead -ne '20260925_quote_communication') {
    throw "Unexpected migration head: $repositoryHead"
  }
  python -m backend.migration_cli upgrade $repositoryHead --confirm
  Assert-LastExit 'migrate owned MT-3 database'
  python -m scripts.browser_migration_contract verify-database-head --expected $repositoryHead
  Assert-LastExit 'verify owned MT-3 database head'

  python -m pytest backend/tests/test_public_tracking_security_postgresql.py -q --tb=short
  Assert-LastExit 'PostgreSQL 18 MT-3 security proof'
  python (Join-Path $root 'scripts\uat\seed_mt3_public_tracking_e2e.py')
  Assert-LastExit 'seed MT-3 browser fixtures'

  $env:PORT = "$backendPort"
  $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'backend' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev', '--', '--host', '127.0.0.1', '--port', "$frontendPort", '--strictPort' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  Wait-Http "http://127.0.0.1:$backendPort/api/health"
  Wait-Http "http://127.0.0.1:$frontendPort"

  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
  $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
  $env:PLAYWRIGHT_CHANNEL = 'chrome'
  npx playwright test e2e/mt3-public-tracking-security.spec.ts --reporter=line --output $evidence
  Assert-LastExit 'real browser MT-3 journeys'

  & (Join-Path $pgBin 'psql.exe') -h 127.0.0.1 -p $postgresPort -U postgres -d $databaseName -v ON_ERROR_STOP=1 -Atc "SELECT CASE WHEN count(*) >= 5 AND bool_and(tracking_code ~ '^SR2-[A-Za-z0-9_-]{22}$') THEN 'PASS' ELSE 'FAIL' END FROM shipment_request;"
  Assert-LastExit 'audit generated capability persistence'
  Write-Output "MT3_POSTGRESQL_VERSION=18"
  Write-Output "MT3_ALEMBIC_HEAD=$repositoryHead"
  Write-Output "MT3_BROWSER_QUALIFICATION=PASS"
  Write-Output "MT3_EVIDENCE_DIRECTORY=$evidence"
}
finally {
  foreach ($process in @($frontend, $backend)) {
    try { Stop-OwnedProcess $process } catch {}
  }
  if ($postgresStarted) {
    try {
      $pgStop = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'stop', '-D', $pgData, '-m', 'fast', '-w' -PassThru -WindowStyle Hidden
      [void]$pgStop.WaitForExit(30000)
    } catch {}
  }
  try { Remove-OwnedRuntime $runtime } catch { Write-Warning $_ }
  foreach ($name in $old.Keys) {
    if ($null -eq $old[$name]) {
      Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    } else {
      [Environment]::SetEnvironmentVariable($name, $old[$name], 'Process')
    }
  }
  Write-Output 'MT3_E2E_CLEANUP=PASS'
}
