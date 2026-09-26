[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$EvidenceDirectory, [switch]$IncludeRegressions, [switch]$PostgresOnly, [switch]$BrowserOnly)
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-p311-owned-$runId"
$pgData = Join-Path $runtime 'pgdata'
$postgresStarted = $false
$backend = $null
$frontend = $null
$results = [System.Collections.Generic.List[object]]::new()
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
function New-Database([string]$Prefix) {
  $name = "${Prefix}_$($runId.Substring(0,8))"
  & (Join-Path $pgBin 'createdb.exe') -h 127.0.0.1 -p $pgPort -U postgres $name
  Check-Exit 'create synthetic database'
  return "postgresql://postgres@127.0.0.1:$pgPort/$name"
}
Push-Location $workspace
try {
  $productHead = (git rev-parse HEAD).Trim()
  $dirty = [bool](git status --porcelain)
  $head = (python -m scripts.browser_migration_contract repository-head).Trim()
  if ($head -ne '20261010_phase3_cargo_eta') { throw "Unexpected migration head: $head" }
  $pgPort = Free-Port
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
  $env:P3_ETA_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_11_eta'
  $env:P3_ROUTE_TIME_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_10_route_time'
  $env:P3_CUSTOMER_SHIPMENT_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_09_customer'
  $env:P3_CARGO_DELIVERY_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_08_delivery'
  $env:P3_REPORTED_FACTS_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_07_reports'
  $env:DN10_POSTGRES_URL = New-Database 'forwarder_integrated_cert_dn10'
  $env:P3_DOCUMENT_CONTEXT_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_06_documents'
  python -m pytest backend/tests/test_phase3_eta_postgresql.py backend/tests/test_phase3_route_time_postgresql.py backend/tests/test_phase3_customer_shipment_postgresql.py backend/tests/test_phase3_cargo_delivery_postgresql.py backend/tests/test_phase3_reported_facts_postgresql.py backend/tests/test_customer_entitlement_postgresql.py backend/tests/test_phase3_document_context_postgresql.py -q --disable-warnings *> (Join-Path $EvidenceDirectory 'postgresql.log')
  Check-Exit 'PostgreSQL 18 migration/concurrency'
  $results.Add(@{ name='PostgreSQL 18'; status='PASS' })
  Write-Output 'PostgreSQL 18 migration/concurrency PASS'
  if ($IncludeRegressions) {
    $env:P3_REFERENCE_CATALOG_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_reference_catalog'
    $env:P3_CARGO_LINEAGE_POSTGRES_URL = New-Database 'forwarder_p3_02_cargo_lineage'
    $env:P3_BRANCHED_ROUTE_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_03_branched_route'
    $env:P3_TRANSPORT_EXECUTION_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_04_transport_execution'
    $env:P3_CARGO_ALLOCATION_POSTGRES_URL = New-Database 'forwarder_integrated_cert_p3_05_cargo_allocation'
    python -m pytest backend/tests/test_phase3_reference_catalog_postgresql.py backend/tests/test_phase3_cargo_lineage_postgresql.py backend/tests/test_phase3_branched_route_postgresql.py backend/tests/test_phase3_transport_execution_postgresql.py backend/tests/test_phase3_cargo_allocation_postgresql.py -q --disable-warnings *> (Join-Path $EvidenceDirectory 'postgresql-regressions.log')
    Check-Exit 'P3-01 through P3-05 PostgreSQL regressions'
    $results.Add(@{ name='P3-01 through P3-05 PostgreSQL'; status='PASS' })
    $env:MT3_TEST_DATABASE_URL = New-Database 'forwarder_mt3_regression'
    $env:DATABASE_URL = $env:MT3_TEST_DATABASE_URL
    python -m backend.migration_cli upgrade $head --confirm *> (Join-Path $EvidenceDirectory 'public-migration.log')
    Check-Exit 'Public regression schema'
    python -m pytest backend/tests/test_public_tracking_security_postgresql.py -q --disable-warnings *> (Join-Path $EvidenceDirectory 'postgresql-public.log')
    Check-Exit 'Public Tracking PostgreSQL regression'
    $results.Add(@{ name='Public Tracking PostgreSQL'; status='PASS' })
    Write-Output 'Public Tracking PostgreSQL PASS'
  }
  }
  $journeys = @(@{ name='P311'; seed='eta'; spec='eta' })
  if ($IncludeRegressions) {
    $journeys += @(
      @{ name='P310'; seed='route_time'; spec='route-time' },
      @{ name='P309'; seed='customer_shipment'; spec='customer-shipment' },
      @{ name='P303'; seed='branched_route'; spec='branched-route' },
      @{ name='P301'; seed='reference_catalog'; spec='reference-catalog' },
      @{ name='P308'; seed='cargo_delivery'; spec='cargo-delivery' },
      @{ name='P307'; seed='reported_facts'; spec='reported-facts' },
      @{ name='P306'; seed='document_context'; spec='document-context' },
      @{ name='MT3'; seed='mt3_public_tracking'; spec='mt3-public-tracking-security' }
    )
  }
  if ($PostgresOnly) { $journeys = @() }
  foreach ($journey in $journeys) {
    $name = $journey.name
    $prefix = if ($name -eq 'MT3') { 'forwarder_mt3_browser' } else { "forwarder_integrated_cert_p3_06_documents_$($name.ToLower())" }
    $env:DATABASE_URL = New-Database $prefix
    $env:E2E_DATABASE_URL = $env:DATABASE_URL
    $env:FORWARDER_E2E_PASSWORD = [guid]::NewGuid().ToString('N') + 'Qa9!'
    $env:FORWARDER_E2E_FIXTURE_PATH = Join-Path $runtime "$name-fixture.json"
    $env:MT3_E2E_FIXTURE_PATH = $env:FORWARDER_E2E_FIXTURE_PATH
    $env:DOCUMENT_STORAGE_ROOT = Join-Path $runtime "$name-private-documents"
    $backendPort = Free-Port
    $frontendPort = Free-Port
    $env:CORS_ORIGINS = "http://127.0.0.1:$frontendPort"
    $env:VITE_BACKEND_URL = "http://127.0.0.1:$backendPort"
    $env:PORT = [string]$backendPort
    $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
    $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
    $env:PLAYWRIGHT_CHANNEL = 'chrome'
    python -m backend.migration_cli upgrade $head --confirm *> (Join-Path $EvidenceDirectory "$name-migration.log")
    Check-Exit "$name upgrade"
    python -m scripts.browser_migration_contract verify-database-head --expected $head
    Check-Exit "$name database identity"
    $seedPath = if ($name -eq 'MT3') { 'scripts/uat/seed_mt3_public_tracking_e2e.py' } else { "scripts/uat/seed_phase3_$($journey.seed)_e2e.py" }
    python $seedPath *> (Join-Path $EvidenceDirectory "$name-seed.log")
    Check-Exit "$name synthetic seed"
    $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','backend' -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $EvidenceDirectory "$name-backend.log") -RedirectStandardError (Join-Path $EvidenceDirectory "$name-backend-error.log")
    $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--host','127.0.0.1','--port',([string]$frontendPort),'--strictPort') -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $EvidenceDirectory "$name-frontend.log") -RedirectStandardError (Join-Path $EvidenceDirectory "$name-frontend-error.log")
    Wait-Http "http://127.0.0.1:$backendPort/api/health"
    Wait-Http "http://127.0.0.1:$frontendPort"
    $specPath = if ($name -eq 'MT3') { 'e2e/mt3-public-tracking-security.spec.ts' } else { "e2e/phase3-$($journey.spec).spec.ts" }
    npx playwright test $specPath --reporter=line --output (Join-Path $EvidenceDirectory "$name-browser") *> (Join-Path $EvidenceDirectory "$name-browser.log")
    Check-Exit "$name Chrome"
    Stop-OwnedProcess $frontend; $frontend = $null
    Stop-OwnedProcess $backend; $backend = $null
    $results.Add(@{ name="$name Chrome"; status='PASS' })
    Write-Output "$name Chrome PASS"
  }
} finally {
  Stop-OwnedProcess $frontend
  Stop-OwnedProcess $backend
  if ($postgresStarted) {
    & (Join-Path $pgBin 'pg_ctl.exe') stop -D $pgData -m fast -w *> (Join-Path $EvidenceDirectory 'postgres-stop.log')
    Check-Exit 'stop owned PostgreSQL'
  }
  @{ product_sha=$productHead; dirty_source=$dirty; schema=$head; results=$results.ToArray(); browser_only=[bool]$BrowserOnly; postgres_only=[bool]$PostgresOnly;
     executed_at_utc=(Get-Date).ToUniversalTime().ToString('o'); runtime=$runtime;
     production_accessed=$false; stopped=$true } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'result.json') -Encoding UTF8
  $resolvedRuntime = (Resolve-Path -LiteralPath $runtime).Path
  $resolvedParent = (Resolve-Path -LiteralPath $runtimeParent).Path
  if ((Split-Path -Parent $resolvedRuntime) -ne $resolvedParent -or
      (Split-Path -Leaf $resolvedRuntime) -ne "forwarder-p311-owned-$runId") {
    throw 'Refusing to remove runtime outside the exact owned temporary directory'
  }
  Remove-Item -LiteralPath $resolvedRuntime -Recurse -Force
  Pop-Location
}
