[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$EvidenceDirectory,
  [switch]$BrowserOnly
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-p314-owned-$runId"
$pgData = Join-Path $runtime 'pgdata'
$pgPort = 55432
$backend = $null
$frontend = $null
$postgresStarted = $false
$productHead = $null
$dirty = $null
$results = [System.Collections.Generic.List[object]]::new()

function Free-Port {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  try { return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port } finally { $listener.Stop() }
}
function Wait-Http([string]$Url) {
  $until = (Get-Date).AddSeconds(120)
  do {
    try { if ((Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3).StatusCode -lt 500) { return } } catch {}
    Start-Sleep -Milliseconds 300
  } while ((Get-Date) -lt $until)
  throw "Owned runtime readiness timeout: $Url"
}
function Stop-OwnedProcess($Process) {
  if ($null -eq $Process) { return }
  $Process.Refresh()
  if (-not $Process.HasExited) {
    & taskkill.exe /PID $Process.Id /T /F *> $null
    [void]$Process.WaitForExit(10000)
  }
  $Process.Refresh()
  if (-not $Process.HasExited) { throw 'Owned child process did not stop' }
}
function Check-Exit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "$Step failed; inspect the owned evidence log" }
}

Push-Location $workspace
try {
  $productHead = (git rev-parse HEAD).Trim()
  $dirty = [bool](git status --porcelain)
  New-Item -ItemType Directory -Path $runtime, $EvidenceDirectory -Force | Out-Null
  $head = (python -m scripts.browser_migration_contract repository-head).Trim()
  if ($head -ne '20261012_phase3_cargo_eta') { throw "Unexpected migration head: $head" }
  if (Get-NetTCPConnection -LocalPort $pgPort -State Listen -ErrorAction SilentlyContinue) {
    throw "Owned PostgreSQL port $pgPort is already in use"
  }
  & (Join-Path $pgBin 'initdb.exe') -D $pgData -U postgres --auth-host=trust --auth-local=trust --encoding=UTF8 --locale=C *> (Join-Path $EvidenceDirectory 'initdb.log')
  Check-Exit 'initialize owned PostgreSQL'
  $pgStart = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'start','-D',$pgData,'-l',(Join-Path $runtime 'postgres.log'),'-o',"`"-h 127.0.0.1 -p $pgPort`"",'-w' -PassThru -WindowStyle Hidden
  [void]$pgStart.WaitForExit(30000)
  if ($pgStart.ExitCode -ne 0) { throw 'Owned PostgreSQL failed to start' }
  $postgresStarted = $true

  $env:APP_ENV = 'uat'
  $env:SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
  $env:JWT_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
  if (-not $BrowserOnly) {
    & (Join-Path $pgBin 'createdb.exe') -h 127.0.0.1 -p $pgPort -U postgres forwarder_control_tower_build
    Check-Exit 'create Control Tower qualification database'
    $env:CONTROL_TOWER_DISPOSABLE_POSTGRES_URL = "postgresql://postgres@127.0.0.1:$pgPort/forwarder_control_tower_build"
    python -m pytest backend/tests/test_control_tower_scalability_postgresql.py -q --disable-warnings *> (Join-Path $EvidenceDirectory 'postgresql-control-tower.log')
    Check-Exit 'Control Tower PostgreSQL relational/count/query-bound proof'
    $results.Add(@{ name='Control Tower PostgreSQL parity'; status='PASS' })
  }

  $browserDb = "forwarder_p314_browser_$($runId.Substring(0,8))"
  & (Join-Path $pgBin 'createdb.exe') -h 127.0.0.1 -p $pgPort -U postgres $browserDb
  Check-Exit 'create browser qualification database'
  $env:DATABASE_URL = "postgresql://postgres@127.0.0.1:$pgPort/$browserDb"
  $env:E2E_DATABASE_URL = $env:DATABASE_URL
  $env:TEST_DATABASE_URL = 'sqlite:///:memory:'
  $env:FORWARDER_E2E_PASSWORD = [guid]::NewGuid().ToString('N') + 'Qa9!'
  $env:FORWARDER_E2E_FIXTURE_PATH = Join-Path $runtime 'P314-fixture.json'
  $env:DOCUMENT_STORAGE_ROOT = Join-Path $runtime 'private-documents'
  $backendPort = Free-Port
  $frontendPort = Free-Port
  $env:CORS_ORIGINS = "http://127.0.0.1:$frontendPort"
  $env:VITE_BACKEND_URL = "http://127.0.0.1:$backendPort"
  $env:PORT = [string]$backendPort
  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
  $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
  $env:PLAYWRIGHT_CHANNEL = 'chrome'
  # Alembic emits ordinary INFO diagnostics on stderr. Capture them without
  # letting Windows PowerShell promote successful native stderr to a terminating
  # PowerShell error; the native exit code remains the gate.
  $strictPreference = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  python -m backend.migration_cli upgrade $head --confirm *> (Join-Path $EvidenceDirectory 'browser-migration.log')
  $migrationExit = $LASTEXITCODE
  $ErrorActionPreference = $strictPreference
  if ($migrationExit -ne 0) { throw 'P3-14 browser schema upgrade failed' }
  python -m scripts.browser_migration_contract verify-database-head --expected $head *> (Join-Path $EvidenceDirectory 'browser-database-identity.log')
  Check-Exit 'P3-14 browser database identity'
  $ErrorActionPreference = 'Continue'
  python scripts/uat/seed_phase3_final_runtime_ux_e2e.py *> (Join-Path $EvidenceDirectory 'browser-seed.log')
  $seedExit = $LASTEXITCODE
  $ErrorActionPreference = $strictPreference
  if ($seedExit -ne 0) { throw 'P3-14 synthetic seed failed' }

  $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','backend' -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $EvidenceDirectory 'backend.log') -RedirectStandardError (Join-Path $EvidenceDirectory 'backend-error.log')
  $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--host','127.0.0.1','--port',([string]$frontendPort),'--strictPort') -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $EvidenceDirectory 'frontend.log') -RedirectStandardError (Join-Path $EvidenceDirectory 'frontend-error.log')
  Wait-Http "http://127.0.0.1:$backendPort/api/health"
  Wait-Http "http://127.0.0.1:$frontendPort"
  $ErrorActionPreference = 'Continue'
  npx playwright test e2e/phase3-final-runtime-ux.spec.ts --reporter=line --output (Join-Path $EvidenceDirectory 'browser') *> (Join-Path $EvidenceDirectory 'browser.log')
  $browserExit = $LASTEXITCODE
  $ErrorActionPreference = $strictPreference
  if ($browserExit -ne 0) { throw 'P3-14 Chrome role/navigation/parity journey failed' }
  $results.Add(@{ name='P3-14 Chrome'; status='PASS' })
} finally {
  Stop-OwnedProcess $frontend
  Stop-OwnedProcess $backend
  if ($postgresStarted) {
    & (Join-Path $pgBin 'pg_ctl.exe') stop -D $pgData -m fast -w *> (Join-Path $EvidenceDirectory 'postgres-stop.log')
    Check-Exit 'stop owned PostgreSQL'
  }
  @{
    product_sha=$productHead
    dirty_source=$dirty
    schema=$head
    browser_only=[bool]$BrowserOnly
    results=$results.ToArray()
    executed_at_utc=(Get-Date).ToUniversalTime().ToString('o')
    production_accessed=$false
    production_mutated=$false
    stopped=$true
  } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'result.json') -Encoding UTF8
  if (Test-Path -LiteralPath $runtime) {
    $resolvedRuntime = (Resolve-Path -LiteralPath $runtime).Path
    $resolvedParent = (Resolve-Path -LiteralPath $runtimeParent).Path
    if ((Split-Path -Parent $resolvedRuntime) -ne $resolvedParent -or (Split-Path -Leaf $resolvedRuntime) -ne "forwarder-p314-owned-$runId") {
      throw 'Refusing to remove runtime outside the exact owned temporary directory'
    }
    Remove-Item -LiteralPath $resolvedRuntime -Recurse -Force
  }
  Pop-Location
}
