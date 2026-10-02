[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$EvidenceDirectory)
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-org-stages-owned-$runId"
$pgData = Join-Path $runtime 'pgdata'
$postgresStarted = $false
$backend = $null
$frontend = $null
New-Item -ItemType Directory -Path $runtime, $EvidenceDirectory -Force | Out-Null

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
  if (-not $Process.HasExited) { & taskkill.exe /PID $Process.Id /T /F *> $null; [void]$Process.WaitForExit(10000) }
  $Process.Refresh()
  if (-not $Process.HasExited) { throw 'Owned child process did not stop' }
}
function Check-Exit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "$Step failed (see owned qualification logs)" }
}

Push-Location $workspace
try {
  $productHead = (git rev-parse HEAD).Trim()
  $dirty = [bool](git status --porcelain)
  $head = (python -m scripts.browser_migration_contract repository-head).Trim()
  if ($head -ne '20261017_document_type_ownership') { throw "Unexpected migration head: $head" }
  $pgPort = Free-Port
  & (Join-Path $pgBin 'initdb.exe') -D $pgData -U postgres --auth-host=trust --auth-local=trust --encoding=UTF8 --locale=C *> (Join-Path $EvidenceDirectory 'initdb.log')
  Check-Exit 'initialize owned PostgreSQL 18'
  $pgStart = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'start','-D',$pgData,'-l',(Join-Path $runtime 'postgres.log'),'-o',"`"-h 127.0.0.1 -p $pgPort`"",'-w' -PassThru -WindowStyle Hidden
  [void]$pgStart.WaitForExit(30000)
  if ($pgStart.ExitCode -ne 0) { throw 'Owned PostgreSQL 18 failed to start' }
  $postgresStarted = $true
  $database = "forwarder_org_stages_$($runId.Substring(0,8))"
  & (Join-Path $pgBin 'createdb.exe') -h 127.0.0.1 -p $pgPort -U postgres $database
  Check-Exit 'create owned browser database'
  $env:APP_ENV = 'uat'
  $env:DATABASE_URL = "postgresql://postgres@127.0.0.1:$pgPort/$database"
  $env:E2E_DATABASE_URL = $env:DATABASE_URL
  $env:SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
  $env:JWT_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
  $env:FORWARDER_E2E_PASSWORD = [guid]::NewGuid().ToString('N') + 'Qa9!'
  $env:FORWARDER_E2E_FIXTURE_PATH = Join-Path $runtime 'fixture.json'
  $env:DOCUMENT_STORAGE_ROOT = Join-Path $runtime 'private-documents'
  python -m backend.migration_cli upgrade $head --confirm *> (Join-Path $EvidenceDirectory 'migration.log')
  Check-Exit 'upgrade owned database'
  python -m scripts.browser_migration_contract verify-database-head --expected $head *> (Join-Path $EvidenceDirectory 'database-head.log')
  Check-Exit 'verify owned database identity'
  python scripts/uat/seed_organization_shipment_stages_e2e.py *> (Join-Path $EvidenceDirectory 'seed.log')
  Check-Exit 'seed owned journey'

  $backendPort = Free-Port
  $frontendPort = Free-Port
  $env:CORS_ORIGINS = "http://127.0.0.1:$frontendPort"
  $env:VITE_BACKEND_URL = "http://127.0.0.1:$backendPort"
  $env:PORT = [string]$backendPort
  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
  $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
  $env:PLAYWRIGHT_CHANNEL = 'chrome'
  $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','backend' -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $EvidenceDirectory 'backend.log') -RedirectStandardError (Join-Path $EvidenceDirectory 'backend-error.log')
  $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--host','127.0.0.1','--port',([string]$frontendPort),'--strictPort') -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $EvidenceDirectory 'frontend.log') -RedirectStandardError (Join-Path $EvidenceDirectory 'frontend-error.log')
  Wait-Http "http://127.0.0.1:$backendPort/api/health"
  Wait-Http "http://127.0.0.1:$frontendPort"
  npx playwright test e2e/organization-shipment-stages.spec.ts --reporter=line --output (Join-Path $EvidenceDirectory 'browser') *> (Join-Path $EvidenceDirectory 'browser.log')
  Check-Exit 'Organization Shipment stages Chrome journey'
  @{ product_sha=$productHead; dirty_source=$dirty; schema=$head; postgresql_major=18;
     journey='PASS'; production_accessed=$false; stopped=$false;
     executed_at_utc=(Get-Date).ToUniversalTime().ToString('o') } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'result.json') -Encoding UTF8
} finally {
  Stop-OwnedProcess $frontend
  Stop-OwnedProcess $backend
  if ($postgresStarted) {
    & (Join-Path $pgBin 'pg_ctl.exe') stop -D $pgData -m fast -w *> (Join-Path $EvidenceDirectory 'postgres-stop.log')
    Check-Exit 'stop owned PostgreSQL 18'
  }
  $resolvedRuntime = (Resolve-Path -LiteralPath $runtime).Path
  $resolvedParent = (Resolve-Path -LiteralPath $runtimeParent).Path
  if ((Split-Path -Parent $resolvedRuntime) -ne $resolvedParent -or
      (Split-Path -Leaf $resolvedRuntime) -ne "forwarder-org-stages-owned-$runId") {
    throw 'Refusing to remove runtime outside the exact owned temporary directory'
  }
  Remove-Item -LiteralPath $resolvedRuntime -Recurse -Force
  Pop-Location
}
