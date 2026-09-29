[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$EvidenceDirectory,
  [Parameter(Mandatory = $true)][string]$ExpectedProductSha,
  [switch]$PostgresOnly,
  [switch]$BrowserOnly,
  [ValidateSet('P301','P302','P303','P304','P305','P306','P307','P308','P309','P310','P311','P312','P313','P314','MT3','IPJ01','IPJ02-IPJ03','P315-CORE','HW-COMMERCIAL','IPJ04')]
  [string]$StartBrowserAt
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-p315-owned-$runId"
$pgData = Join-Path $runtime 'pgdata'
$postgresStarted = $false
$backend = $null
$frontend = $null
$productHead = $null
$dirty = $null
$schemaHead = $null
$results = [System.Collections.Generic.List[object]]::new()
$browserSelectionStarted = -not [bool]$StartBrowserAt

function Get-FreePort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  try { return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port }
  finally { $listener.Stop() }
}

function Wait-Http([string]$Url) {
  $until = (Get-Date).AddSeconds(120)
  do {
    try {
      if ((Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3).StatusCode -lt 500) { return }
    } catch {}
    Start-Sleep -Milliseconds 350
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
  if (-not $Process.HasExited) { throw "Owned child process $($Process.Id) did not stop" }
}

function Invoke-Logged([string]$Step, [scriptblock]$Command, [string]$LogPath) {
  $strictPreference = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    & $Command *> $LogPath
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $strictPreference
  }
  if ($exitCode -ne 0) { throw "$Step failed; inspect $LogPath" }
}

function New-OwnedDatabase([string]$Name) {
  & (Join-Path $pgBin 'createdb.exe') -h 127.0.0.1 -p $pgPort -U postgres $Name
  if ($LASTEXITCODE -ne 0) { throw "Failed to create owned database $Name" }
  return "postgresql://postgres@127.0.0.1:$pgPort/$Name"
}

function Invoke-BrowserJourney {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$DatabaseName,
    [Parameter(Mandatory = $true)][string]$Seed,
    [Parameter(Mandatory = $true)][string[]]$Specs,
    [string]$PostAudit,
    [string]$MidJourneySeed,
    [string[]]$FollowUpSpecs,
    [switch]$RestrictedOwnerRuntime,
    [switch]$CustomerPassword
  )
  if (-not $script:browserSelectionStarted) {
    if ($Name -ne $StartBrowserAt) {
      Write-Output "$Name Chrome SKIPPED_FOR_DIAGNOSTIC_RESUME"
      return
    }
    $script:browserSelectionStarted = $true
  }
  $journeyEvidence = Join-Path $EvidenceDirectory $Name
  New-Item -ItemType Directory -Path $journeyEvidence -Force | Out-Null
  $databaseUrl = New-OwnedDatabase $DatabaseName
  $env:DATABASE_URL = $databaseUrl
  $env:E2E_DATABASE_URL = $databaseUrl
  $env:FORWARDER_E2E_PASSWORD = [guid]::NewGuid().ToString('N') + 'Qa9!'
  $env:FORWARDER_E2E_REPLACEMENT_PASSWORD = [guid]::NewGuid().ToString('N') + 'Rp9!'
  if ($CustomerPassword) {
    $env:FORWARDER_E2E_CUSTOMER_PASSWORD = [guid]::NewGuid().ToString('N') + 'Cu9!'
  } else {
    $env:FORWARDER_E2E_CUSTOMER_PASSWORD = $env:FORWARDER_E2E_PASSWORD
  }
  $env:FORWARDER_E2E_FIXTURE_PATH = Join-Path $runtime "$Name-fixture.json"
  $env:MT3_E2E_FIXTURE_PATH = $env:FORWARDER_E2E_FIXTURE_PATH
  $env:DOCUMENT_STORAGE_ROOT = Join-Path $runtime "$Name-private-documents"
  $env:OPERATIONAL_WORKSPACE_EVIDENCE_PATH = $journeyEvidence
  $env:OPERATIONAL_MONITORING_RELIABILITY_EVIDENCE_PATH = $journeyEvidence
  $env:PHASE3_FINAL_CANDIDATE_EVIDENCE_PATH = $journeyEvidence
  $backendPort = Get-FreePort
  $frontendPort = Get-FreePort
  $env:CORS_ORIGINS = "http://127.0.0.1:$frontendPort"
  $env:VITE_BACKEND_URL = "http://127.0.0.1:$backendPort"
  $env:PORT = [string]$backendPort
  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
  $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
  $env:PLAYWRIGHT_CHANNEL = 'chrome'
  $ownerDatabaseUrl = $databaseUrl

  Invoke-Logged "$Name migration" {
    python -m backend.migration_cli upgrade $schemaHead --confirm
  } (Join-Path $journeyEvidence 'migration.log')
  Invoke-Logged "$Name database identity" {
    python -m scripts.browser_migration_contract verify-database-head --expected $schemaHead
  } (Join-Path $journeyEvidence 'database-identity.log')
  Invoke-Logged "$Name synthetic seed" {
    python $Seed
  } (Join-Path $journeyEvidence 'seed.log')

  if ($RestrictedOwnerRuntime) {
    Invoke-Logged "$Name restricted runtime" {
      python scripts/uat/configure_owner_transfer_test_runtime.py
    } (Join-Path $journeyEvidence 'restricted-runtime.log')
    $runtimeDatabaseUrl = (Get-Content -LiteralPath (Join-Path $journeyEvidence 'restricted-runtime.log') | Select-Object -Last 1).Trim()
    if (-not $runtimeDatabaseUrl.StartsWith('postgresql://p313_browser_')) {
      throw "$Name restricted runtime identity was not established"
    }
    $env:DATABASE_URL = $runtimeDatabaseUrl
    $env:E2E_DATABASE_URL = $runtimeDatabaseUrl
    @{
      actual_login = $true
      owner_membership = $false
      elevated_runtime = $false
      ddl_grants = $false
      production_accessed = $false
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $journeyEvidence 'runtime-identity.json') -Encoding UTF8
  }

  try {
    $script:backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'backend' -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $journeyEvidence 'backend.log') -RedirectStandardError (Join-Path $journeyEvidence 'backend-error.log')
    $script:frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run', 'dev', '--', '--host', '127.0.0.1', '--port', ([string]$frontendPort), '--strictPort') -WorkingDirectory $workspace -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $journeyEvidence 'frontend.log') -RedirectStandardError (Join-Path $journeyEvidence 'frontend-error.log')
    Wait-Http "http://127.0.0.1:$backendPort/api/health"
    Wait-Http "http://127.0.0.1:$frontendPort"
    Invoke-Logged "$Name Chrome journey" {
      npx.cmd playwright test @Specs --reporter=line --output (Join-Path $journeyEvidence 'browser')
    } (Join-Path $journeyEvidence 'browser.log')
    if ($MidJourneySeed) {
      $restrictedDatabaseUrl = $env:DATABASE_URL
      try {
        # The already-running backend retains its restricted connection.  Only
        # this owned setup process receives the database-owner URL so it can
        # advance the synthetic starting state between browser chapters.
        $env:DATABASE_URL = $ownerDatabaseUrl
        $env:E2E_DATABASE_URL = $ownerDatabaseUrl
        Invoke-Logged "$Name mid-journey synthetic setup" {
          python $MidJourneySeed
        } (Join-Path $journeyEvidence 'mid-journey-seed.log')
      } finally {
        $env:DATABASE_URL = $restrictedDatabaseUrl
        $env:E2E_DATABASE_URL = $restrictedDatabaseUrl
      }
      Invoke-Logged "$Name follow-up Chrome journey" {
        npx.cmd playwright test @FollowUpSpecs --reporter=line --output (Join-Path $journeyEvidence 'browser-follow-up')
      } (Join-Path $journeyEvidence 'browser-follow-up.log')
    }
    if ($PostAudit) {
      Invoke-Logged "$Name persisted audit" {
        python $PostAudit
      } (Join-Path $journeyEvidence 'persisted-audit.log')
    }
    $results.Add(@{ name = "$Name Chrome"; status = 'PASS'; specs = $Specs })
    Write-Output "$Name Chrome PASS"
  } finally {
    Stop-OwnedProcess $script:frontend
    $script:frontend = $null
    Stop-OwnedProcess $script:backend
    $script:backend = $null
  }
}

Push-Location $workspace
try {
  $productHead = (git rev-parse HEAD).Trim()
  $dirty = [bool](git status --porcelain)
  if ($dirty -or $productHead -ne $ExpectedProductSha) {
    throw 'Final qualification requires the exact clean Product SHA'
  }
  $schemaHead = (python -m scripts.browser_migration_contract repository-head).Trim()
  if ($LASTEXITCODE -ne 0 -or $schemaHead -ne '20261013_structured_route_progress_eta') {
    throw "Unexpected migration head: $schemaHead"
  }
  foreach ($tool in @('initdb.exe', 'pg_ctl.exe', 'createdb.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $pgBin $tool))) {
      throw "PostgreSQL 18 tool is unavailable: $tool"
    }
  }

  New-Item -ItemType Directory -Path $runtime, $EvidenceDirectory -Force | Out-Null
  $pgPort = 55432
  if (Get-NetTCPConnection -LocalPort $pgPort -State Listen -ErrorAction SilentlyContinue) {
    throw "Owned PostgreSQL port $pgPort is already in use"
  }
  Invoke-Logged 'initialize owned PostgreSQL 18' {
    & (Join-Path $pgBin 'initdb.exe') -D $pgData -U postgres --auth-host=trust --auth-local=trust --encoding=UTF8 --locale=C
  } (Join-Path $EvidenceDirectory 'initdb.log')
  $pgStart = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList 'start', '-D', $pgData, '-l', (Join-Path $runtime 'postgres.log'), '-o', "`"-h 127.0.0.1 -p $pgPort`"", '-w' -PassThru -WindowStyle Hidden
  [void]$pgStart.WaitForExit(30000)
  $pgStart.Refresh()
  if ($pgStart.ExitCode -ne 0) { throw 'Owned PostgreSQL 18 failed to start' }
  $postgresStarted = $true

  $env:APP_ENV = 'uat'
  $env:PYTHONIOENCODING = 'utf-8'
  $env:SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
  $env:JWT_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
  $env:E2E_SECRET_KEY = $env:SECRET_KEY
  $env:E2E_JWT_SECRET_KEY = $env:JWT_SECRET_KEY
  $env:TEST_DATABASE_URL = 'sqlite:///:memory:'
  $env:DATABASE_URL = 'sqlite:///:memory:'

  if (-not $BrowserOnly) {
    $migrationDb = New-OwnedDatabase "forwarder_p315_migration_chain_$($runId.Substring(0, 8))"
    $env:DATABASE_URL = $migrationDb
    Invoke-Logged 'fresh PostgreSQL 18 base-to-head migration chain' {
      python -m backend.migration_cli upgrade $schemaHead --confirm
      if ($LASTEXITCODE -eq 0) { python -m backend.migration_cli check }
    } (Join-Path $EvidenceDirectory 'postgresql-migration-chain.log')
    $results.Add(@{ name = 'PostgreSQL 18 base-to-head migration chain'; status = 'PASS' })

    $env:P3_REFERENCE_CATALOG_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_reference_catalog_$($runId.Substring(0, 8))"
    $env:P3_CARGO_LINEAGE_POSTGRES_URL = New-OwnedDatabase "forwarder_p3_02_cargo_lineage_$($runId.Substring(0, 8))"
    $env:P3_BRANCHED_ROUTE_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_03_branched_route_$($runId.Substring(0, 8))"
    $env:P3_TRANSPORT_EXECUTION_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_04_transport_execution_$($runId.Substring(0, 8))"
    $env:P3_CARGO_ALLOCATION_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_05_cargo_allocation_$($runId.Substring(0, 8))"
    $env:P3_DOCUMENT_CONTEXT_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_06_documents_$($runId.Substring(0, 8))"
    $env:P3_REPORTED_FACTS_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_07_reports_$($runId.Substring(0, 8))"
    $env:P3_CARGO_DELIVERY_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_08_delivery_$($runId.Substring(0, 8))"
    $env:P3_CUSTOMER_SHIPMENT_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_09_customer_$($runId.Substring(0, 8))"
    $env:P3_ROUTE_TIME_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_10_route_time_$($runId.Substring(0, 8))"
    $env:P3_ETA_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_11_eta_$($runId.Substring(0, 8))"
    $env:P3_CLOSURE_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_12_closure_$($runId.Substring(0, 8))"
    $env:P3_OWNER_TRANSFER_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_p3_13_owner_$($runId.Substring(0, 8))"
    $env:SHIPMENT_CARGO_CREATION_POSTGRES_URL = New-OwnedDatabase "forwarder_cargo_create_$($runId.Substring(0, 8))"
    $env:CARGO_CONTINUITY_REPAIR_POSTGRES_URL = New-OwnedDatabase "forwarder_cargo_continuity_repair_$($runId.Substring(0, 8))"
    $env:DN10_POSTGRES_URL = New-OwnedDatabase "forwarder_integrated_cert_dn10_$($runId.Substring(0, 8))"
    $env:CONTROL_TOWER_DISPOSABLE_POSTGRES_URL = New-OwnedDatabase 'forwarder_control_tower_build'
    $postgresSpecs = @(
      'backend/tests/test_phase3_reference_catalog_postgresql.py',
      'backend/tests/test_phase3_cargo_lineage_postgresql.py',
      'backend/tests/test_phase3_branched_route_postgresql.py',
      'backend/tests/test_phase3_transport_execution_postgresql.py',
      'backend/tests/test_phase3_cargo_allocation_postgresql.py',
      'backend/tests/test_phase3_document_context_postgresql.py',
      'backend/tests/test_phase3_reported_facts_postgresql.py',
      'backend/tests/test_phase3_cargo_delivery_postgresql.py',
      'backend/tests/test_phase3_customer_shipment_postgresql.py',
      'backend/tests/test_phase3_route_time_postgresql.py',
      'backend/tests/test_phase3_eta_postgresql.py',
      'backend/tests/test_phase3_closure_postgresql.py',
      'backend/tests/test_phase3_owner_transfer_postgresql.py',
      'backend/tests/test_shipment_cargo_creation_postgresql.py',
      'backend/tests/test_cargo_continuity_repair_postgresql.py',
      'backend/tests/test_customer_entitlement_postgresql.py',
      'backend/tests/test_control_tower_scalability_postgresql.py'
    )
    Invoke-Logged 'Phase 3 PostgreSQL 18 migration/concurrency/scale qualification' {
      python -m pytest @postgresSpecs -q --disable-warnings
    } (Join-Path $EvidenceDirectory 'postgresql-phase3.log')
    $results.Add(@{ name = 'Phase 3 PostgreSQL 18'; status = 'PASS' })

    $env:MT3_TEST_DATABASE_URL = New-OwnedDatabase "forwarder_mt3_final_$($runId.Substring(0, 8))"
    $env:DATABASE_URL = $env:MT3_TEST_DATABASE_URL
    Invoke-Logged 'Public Tracking PostgreSQL migration' {
      python -m backend.migration_cli upgrade $schemaHead --confirm
    } (Join-Path $EvidenceDirectory 'public-tracking-migration.log')
    Invoke-Logged 'Public Tracking PostgreSQL regression' {
      python -m pytest backend/tests/test_public_tracking_security_postgresql.py -q --disable-warnings
    } (Join-Path $EvidenceDirectory 'public-tracking-postgresql.log')
    $results.Add(@{ name = 'Public Tracking regression'; status = 'PASS' })
  }

  if (-not $PostgresOnly) {
    $phase3Journeys = @(
      @{ Name = 'P301'; Seed = 'scripts/uat/seed_phase3_reference_catalog_e2e.py'; Spec = @('e2e/phase3-reference-catalog.spec.ts', 'e2e/admin-system-foundations.spec.ts') },
      @{ Name = 'P302'; Seed = 'scripts/uat/seed_phase3_cargo_lineage_e2e.py'; Spec = 'e2e/phase3-cargo-lineage.spec.ts' },
      @{ Name = 'P303'; Seed = 'scripts/uat/seed_phase3_branched_route_e2e.py'; Spec = 'e2e/phase3-branched-route.spec.ts' },
      @{ Name = 'P304'; Seed = 'scripts/uat/seed_human_walkthrough_cargo_chain_e2e.py'; Spec = @('e2e/phase3-transport-execution.spec.ts', 'e2e/human-walkthrough-cargo-chain.spec.ts') },
      @{ Name = 'P305'; Seed = 'scripts/uat/seed_phase3_cargo_allocation_e2e.py'; Spec = 'e2e/phase3-cargo-allocation.spec.ts' },
      @{ Name = 'P306'; Seed = 'scripts/uat/seed_phase3_document_context_e2e.py'; Spec = 'e2e/phase3-document-context.spec.ts' },
      @{ Name = 'P307'; Seed = 'scripts/uat/seed_phase3_reported_facts_e2e.py'; Spec = 'e2e/phase3-reported-facts.spec.ts' },
      @{ Name = 'P308'; Seed = 'scripts/uat/seed_phase3_cargo_delivery_e2e.py'; Spec = 'e2e/phase3-cargo-delivery.spec.ts' },
      @{ Name = 'P309'; Seed = 'scripts/uat/seed_phase3_customer_shipment_e2e.py'; Spec = 'e2e/phase3-customer-shipment.spec.ts' },
      @{ Name = 'P310'; Seed = 'scripts/uat/seed_phase3_route_time_e2e.py'; Spec = 'e2e/phase3-route-time.spec.ts' },
      @{ Name = 'P311'; Seed = 'scripts/uat/seed_phase3_eta_e2e.py'; Spec = 'e2e/phase3-eta.spec.ts' },
      @{ Name = 'P312'; Seed = 'scripts/uat/seed_phase3_closure_e2e.py'; Spec = 'e2e/phase3-closure.spec.ts' },
      @{ Name = 'P313'; Seed = 'scripts/uat/seed_phase3_owner_transfer_e2e.py'; Spec = 'e2e/phase3-owner-transfer.spec.ts'; Restricted = $true },
      @{ Name = 'P314'; Seed = 'scripts/uat/seed_phase3_final_runtime_ux_e2e.py'; Spec = 'e2e/phase3-final-runtime-ux.spec.ts' }
    )
    foreach ($journey in $phase3Journeys) {
      $databaseName = "forwarder_integrated_cert_p3_06_documents_$($journey.Name.ToLower())_$($runId.Substring(0, 8))"
      Invoke-BrowserJourney -Name $journey.Name -DatabaseName $databaseName -Seed $journey.Seed -Specs @($journey.Spec) -RestrictedOwnerRuntime:([bool]$journey.Restricted)
    }

    Invoke-BrowserJourney -Name 'MT3' -DatabaseName "forwarder_mt3_browser_$($runId.Substring(0, 8))" -Seed 'scripts/uat/seed_mt3_public_tracking_e2e.py' -Specs @('e2e/mt3-public-tracking-security.spec.ts')
    Invoke-BrowserJourney -Name 'IPJ01' -DatabaseName 'forwarder_integrated_cert_fixed_shipment_owner_e2e' -Seed 'scripts/uat/seed_fixed_shipment_owner_e2e.py' -Specs @('e2e/fixed-shipment-owner.spec.ts')
    # These suites deliberately mutate Actions and SLA rule versions. Keep each
    # proof on a fresh owned database so one journey cannot precondition another.
    Invoke-BrowserJourney -Name 'IPJ02-IPJ03' -DatabaseName "forwarder_workspace_phase2_phase1_$($runId.Substring(0, 8))" -Seed 'scripts/uat/seed_operational_workspace_phase2_e2e.py' -Specs @(
      'e2e/operational-workspace-phase1.spec.ts'
    ) -CustomerPassword
    Invoke-BrowserJourney -Name 'IPJ02-IPJ03-PHASE2' -DatabaseName "forwarder_workspace_phase2_phase2_$($runId.Substring(0, 8))" -Seed 'scripts/uat/seed_operational_workspace_phase2_e2e.py' -Specs @(
      'e2e/operational-workspace-phase2.spec.ts'
    ) -CustomerPassword
    Invoke-BrowserJourney -Name 'IPJ02-IPJ03-MONITORING' -DatabaseName "forwarder_workspace_phase2_monitoring_$($runId.Substring(0, 8))" -Seed 'scripts/uat/seed_operational_workspace_phase2_e2e.py' -Specs @(
      'e2e/operational-monitoring-reliability-phase2-5.spec.ts'
    ) -CustomerPassword
    Invoke-BrowserJourney -Name 'P315-CORE' -DatabaseName "forwarder_workspace_phase1_$($runId.Substring(0, 8))" -Seed 'scripts/uat/seed_phase3_final_candidate_e2e.py' -Specs @('e2e/phase3-final-candidate.spec.ts') -PostAudit 'scripts/uat/audit_phase3_final_candidate_e2e.py' -CustomerPassword
    Invoke-BrowserJourney -Name 'HW-COMMERCIAL' -DatabaseName 'forwarder_integrated_cert_quote_communication_e2e' -Seed 'scripts/uat/seed_quote_communication_e2e.py' -Specs @('e2e/quote-communication.spec.ts') -PostAudit 'scripts/uat/audit_quote_communication_e2e.py'
    Invoke-BrowserJourney -Name 'IPJ04' -DatabaseName "forwarder_integrated_cert_p3_06_documents_p313_ipj04_$($runId.Substring(8, 8))" -Seed 'scripts/uat/seed_phase3_owner_transfer_e2e.py' -Specs @('e2e/phase3-owner-transfer.spec.ts') -RestrictedOwnerRuntime -MidJourneySeed 'scripts/uat/advance_phase3_ipj04_e2e.py' -FollowUpSpecs @('e2e/phase3-ipj04-history-closure.spec.ts')
    if (-not $script:browserSelectionStarted) {
      throw "Diagnostic browser resume target was not found: $StartBrowserAt"
    }
  }

  if ((git rev-parse HEAD).Trim() -ne $ExpectedProductSha -or (git status --porcelain)) {
    throw 'Source changed during final qualification'
  }
} finally {
  Stop-OwnedProcess $frontend
  Stop-OwnedProcess $backend
  if ($postgresStarted) {
    Invoke-Logged 'stop owned PostgreSQL 18' {
      & (Join-Path $pgBin 'pg_ctl.exe') stop -D $pgData -m fast -w
    } (Join-Path $EvidenceDirectory 'postgres-stop.log')
  }
  if (Test-Path -LiteralPath $EvidenceDirectory) {
    @{
      product_sha = $productHead
      dirty_source = $dirty
      schema = $schemaHead
      results = $results.ToArray()
      browser_only = [bool]$BrowserOnly
      postgres_only = [bool]$PostgresOnly
      executed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
      environment = 'owned disposable local/UAT PostgreSQL 18 and Chrome'
      production_accessed = $false
      production_mutated = $false
      production_migration_performed = $false
      deployment_performed = $false
      release_created = $false
      stopped = $true
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'result.json') -Encoding UTF8
  }
  if (Test-Path -LiteralPath $runtime) {
    $resolvedRuntime = (Resolve-Path -LiteralPath $runtime).Path
    $resolvedParent = (Resolve-Path -LiteralPath $runtimeParent).Path
    if ((Split-Path -Parent $resolvedRuntime) -ne $resolvedParent -or
        (Split-Path -Leaf $resolvedRuntime) -ne "forwarder-p315-owned-$runId") {
      throw 'Refusing to remove runtime outside the exact owned temporary directory'
    }
    Remove-Item -LiteralPath $resolvedRuntime -Recurse -Force
  }
  Pop-Location
}
