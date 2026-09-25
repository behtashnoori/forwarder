[CmdletBinding()]
param(
  [string]$CertificateAdminUrl = $env:CERT_ADMIN_URL,
  [ValidatePattern('^[A-I]$')]
  [string]$Acceptance = 'A',
  [switch]$CatalogJourney,
  [switch]$ProductReality,
  [switch]$PersonalAnalytics,
  [switch]$PartyRoleQualification,
  [switch]$Phase3ReferenceCatalog,
  [switch]$Phase3CargoLineage,
  [switch]$Phase3BranchedRoute,
  [string]$PartyRoleGrep,
  [switch]$MigrationBootstrapOnly,
  [switch]$KeepEvidence
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runId = [guid]::NewGuid().ToString('N')
$runtimeRoot = [System.IO.Path]::GetTempPath()
$runtimePrefix = 'forwarder-shared-e2e-'
$modeCount = @($CatalogJourney, $ProductReality, $PersonalAnalytics, $PartyRoleQualification, $Phase3ReferenceCatalog, $Phase3CargoLineage, $Phase3BranchedRoute).Where({ $_ }).Count
if ($modeCount -gt 1) { throw 'Qualification modes are mutually exclusive.' }
$purpose = if ($PersonalAnalytics) { 'personal-analytics-e2e' } elseif ($Phase3ReferenceCatalog) { 'phase3-reference-catalog-e2e' } elseif ($Phase3CargoLineage) { 'phase3-cargo-lineage-e2e' } elseif ($Phase3BranchedRoute) { 'phase3-branched-route-e2e' } else { 'shared-transport-e2e' }
$databaseMode = if ($PersonalAnalytics) { 'personal_analytics' } elseif ($Phase3ReferenceCatalog) { 'p3_reference_catalog' } elseif ($Phase3CargoLineage) { 'p3_cargo_lineage' } elseif ($Phase3BranchedRoute) { 'p3_branched_route' } else { 'shared' }
$dbName = "forwarder_integrated_cert_$($databaseMode)_$runId"
$runtime = Join-Path $runtimeRoot "$runtimePrefix$runId"
$fixture = Join-Path $runtime 'fixtures.json'
$evidence = Join-Path $root "test-results\shared-transport-$runId"
$backend = $null
$frontend = $null
$old = @{}
$cleanupFailures = [System.Collections.Generic.List[string]]::new()

function Stop-QualificationProcess($process) {
  if ($null -eq $process) { return }
  try {
    $process.Refresh()
    if (-not $process.HasExited) {
      # Only process trees started by this runner are eligible for termination.
      & taskkill.exe /PID $process.Id /T /F *> $null
      $process.WaitForExit(10000)
    }
    $process.Refresh()
    if (-not $process.HasExited) { throw "process $($process.Id) is still running" }
  } catch { throw "runner-owned process cleanup failed: $($_.Exception.Message)" }
}

function Wait-Http([string]$Url, [int]$Seconds = 90) {
  $until = (Get-Date).AddSeconds($Seconds)
  do { try { if ((Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3).StatusCode -lt 500) { return } } catch {}; Start-Sleep -Milliseconds 350 } while ((Get-Date) -lt $until)
  throw 'Local readiness check timed out.'
}

function Assert-LastExit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "Qualification step failed: $Step" }
}

function Test-QualificationRuntimeOwnership([System.IO.DirectoryInfo]$Directory, [switch]$AllowLegacy) {
  if ($Directory.Name -notmatch '^forwarder-shared-e2e-([0-9a-f]{32})$') { return $false }
  $manifest = Join-Path $Directory.FullName 'qualification-owner.json'
  if (Test-Path -LiteralPath $manifest -PathType Leaf) {
    try {
      $owner = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
      return $owner.purpose -in @('shared-transport-e2e','personal-analytics-e2e','phase3-reference-catalog-e2e','phase3-cargo-lineage-e2e','phase3-branched-route-e2e') -and $owner.run_id -eq $Matches[1] -and $owner.repository -eq $root
    } catch { return $false }
  }
  # Backward-compatible recovery for runtimes produced by the pre-manifest runner.
  return $AllowLegacy -and (Test-Path -LiteralPath (Join-Path $Directory.FullName 'fixtures.json') -PathType Leaf)
}

function Get-RuntimeReferencingProcesses([string]$RuntimePath) {
  @(Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -and $_.CommandLine -like "*$RuntimePath*") -or
    ($_.ExecutablePath -and $_.ExecutablePath -like "*$RuntimePath*")
  })
}

function Remove-QualificationRuntime([string]$RuntimePath) {
  for ($attempt = 1; $attempt -le 5; $attempt++) {
    if (-not (Test-Path -LiteralPath $RuntimePath)) { return }
    try { Remove-Item -LiteralPath $RuntimePath -Recurse -Force -ErrorAction Stop } catch {
      if ($attempt -eq 5) { throw "runtime cleanup failed for runner-owned path: $RuntimePath ($($_.Exception.Message))" }
      Start-Sleep -Milliseconds (200 * $attempt)
    }
  }
  if (Test-Path -LiteralPath $RuntimePath) { throw "runtime cleanup failed for runner-owned path: $RuntimePath" }
}

function Invoke-StaleRuntimeRecovery {
  $candidates = @(Get-ChildItem -LiteralPath $runtimeRoot -Directory -Filter "$runtimePrefix*" -ErrorAction Stop)
  foreach ($candidate in $candidates) {
    if (-not (Test-QualificationRuntimeOwnership $candidate -AllowLegacy)) { continue }
    $live = @(Get-RuntimeReferencingProcesses $candidate.FullName)
    if ($live.Count -gt 0) { throw "stale runner-owned runtime has a live referencing process: $($candidate.FullName)" }
    Remove-QualificationRuntime $candidate.FullName
  }
}

try {
  if (-not (Test-Path (Join-Path $root '.git'))) { throw 'This runner must be launched from the repository scripts directory.' }
  if (-not $CertificateAdminUrl) { throw 'CERT_ADMIN_URL must provide a loopback-only local PostgreSQL administrator connection.' }
  $admin = [Uri]$CertificateAdminUrl
  if ($admin.Host -notin @('localhost','127.0.0.1','[::1]','::1')) { throw 'Refusing a non-loopback PostgreSQL host.' }

  $repositoryHead = (& python -m scripts.browser_migration_contract repository-head)
  Assert-LastExit 'resolve single repository Alembic head'
  if ($repositoryHead -is [array] -or [string]::IsNullOrWhiteSpace($repositoryHead)) { throw 'Repository Alembic head resolution returned an invalid target.' }
  $repositoryHead = $repositoryHead.Trim()

  Invoke-StaleRuntimeRecovery
  foreach ($name in 'DATABASE_URL','FORWARDER_E2E_PASSWORD','FORWARDER_E2E_FIXTURE_PATH','PORT','E2E_DATABASE_URL','CERT_DB_NAME','CERT_DB_ACTION','FORWARDER_E2E_ACCEPTANCE','APP_ENV','CORS_ORIGINS','VITE_BACKEND_URL','PLAYWRIGHT_BASE_URL','PLAYWRIGHT_EXTERNAL_SERVER','SECRET_KEY','JWT_SECRET_KEY') { $old[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
  New-Item -ItemType Directory -Force -Path $runtime, $evidence | Out-Null
  # Windows PowerShell 5.1 does not recognize utf8NoBOM; UTF8 remains valid
  # JSON input for the runner's own reader on both supported PowerShell hosts.
  [pscustomobject]@{ purpose = $purpose; run_id = $runId; created_at = (Get-Date).ToUniversalTime().ToString('o'); repository = $root } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'qualification-owner.json') -Encoding UTF8

  $passwordBytes = New-Object byte[] 48
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($passwordBytes); $rng.Dispose()
  $password = [Convert]::ToBase64String($passwordBytes).Replace('+','A').Replace('/','B').Replace('=','')
  $secretBytes = New-Object byte[] 64
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($secretBytes); $rng.Dispose()
  $runtimeSecret = [Convert]::ToBase64String($secretBytes)
  $databaseUrl = "$($admin.GetLeftPart([System.UriPartial]::Authority))/$dbName"
  $env:CERT_ADMIN_URL = $CertificateAdminUrl; $env:CERT_DB_NAME = $dbName; $env:CERT_DB_ACTION = 'create'
  python (Join-Path $root 'scripts\create_disposable_certification_database.py') | Out-Null
  Assert-LastExit 'create disposable database'
  $env:DATABASE_URL = $databaseUrl; $env:E2E_DATABASE_URL = $databaseUrl; $env:FORWARDER_E2E_PASSWORD = $password; $env:FORWARDER_E2E_FIXTURE_PATH = $fixture; $env:APP_ENV = 'uat'; $env:CORS_ORIGINS = 'http://127.0.0.1:4174'; $env:VITE_BACKEND_URL = 'http://127.0.0.1:5011'; $env:SECRET_KEY = $runtimeSecret; $env:JWT_SECRET_KEY = $runtimeSecret
  python -m backend.migration_cli upgrade $repositoryHead --confirm
  Assert-LastExit 'Alembic upgrade'
  python -m scripts.browser_migration_contract verify-database-head --expected $repositoryHead
  Assert-LastExit 'verify browser database Alembic head before seed'
  if ($MigrationBootstrapOnly) {
    Write-Output "BROWSER_MIGRATION_BOOTSTRAP = PASS; head=$repositoryHead"
    return
  }
  $seed = if ($PersonalAnalytics) { 'scripts\uat\seed_personal_analytics_e2e.py' } elseif ($Phase3ReferenceCatalog) { 'scripts\uat\seed_phase3_reference_catalog_e2e.py' } elseif ($Phase3CargoLineage) { 'scripts\uat\seed_phase3_cargo_lineage_e2e.py' } elseif ($Phase3BranchedRoute) { 'scripts\uat\seed_phase3_branched_route_e2e.py' } elseif ($CatalogJourney) { 'scripts\uat\seed_catalog_journey_e2e.py' } else { 'scripts\uat\seed_shared_transport_e2e.py' }
  python (Join-Path $root $seed)
  Assert-LastExit 'deterministic fixture seed'
  $env:PORT = '5011'
  $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','backend' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev','--','--host','127.0.0.1','--port','4174' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  Wait-Http 'http://127.0.0.1:5011/api/health'; Wait-Http 'http://127.0.0.1:4174'
  $env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:4174'; $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'; $env:FORWARDER_E2E_ACCEPTANCE = $Acceptance
  if ($PersonalAnalytics) {
    npx playwright test e2e/qualification.spec.ts --output $evidence
    Assert-LastExit 'Personal Analytics Saved View and Dashboard browser qualification'
  } elseif ($Phase3ReferenceCatalog) {
    npx playwright test e2e/phase3-reference-catalog.spec.ts --output $evidence
    Assert-LastExit 'Phase 3 P3-01 reference catalog browser qualification'
  } elseif ($Phase3CargoLineage) {
    npx playwright test e2e/phase3-cargo-lineage.spec.ts --output $evidence
    Assert-LastExit 'Phase 3 P3-02 cargo lineage browser qualification'
  } elseif ($Phase3BranchedRoute) {
    npx playwright test e2e/phase3-branched-route.spec.ts --output $evidence
    Assert-LastExit 'Phase 3 P3-03 branched route browser qualification'
  } elseif ($PartyRoleQualification) {
    if ($PartyRoleGrep) {
      npx playwright test e2e/party-role-provider-eligibility.spec.ts --grep $PartyRoleGrep --output $evidence
    } else {
      npx playwright test e2e/party-role-provider-eligibility.spec.ts --output $evidence
    }
    Assert-LastExit 'Party Role / Provider Eligibility browser qualification'
  } elseif ($CatalogJourney) {
    npx playwright test e2e/catalog-operational-cargo-journey.spec.ts --output $evidence
    Assert-LastExit 'Catalog operational cargo journey'
  } elseif ($ProductReality) {
    npx playwright test e2e/product-reality-corrective.spec.ts --output $evidence
    Assert-LastExit 'Product Reality corrective browser retest'
  } else {
    $acceptancePattern = if ($Acceptance -eq 'F') { 'F-CARRIER -' } else { "$Acceptance -" }
    npx playwright test e2e/shared-transport.spec.ts --grep $acceptancePattern --output $evidence
    Assert-LastExit "Shared Transport Acceptance $Acceptance"
  }
  if (-not $CatalogJourney -and -not $ProductReality -and -not $PersonalAnalytics -and -not $PartyRoleQualification -and $Acceptance -in @('C','D','E','F','I')) {
    python (Join-Path $root 'scripts\uat\audit_shared_transport_e2e.py')
    Assert-LastExit "Shared Transport Acceptance $Acceptance supplemental audit"
  }
  Write-Output 'RUNNER_EXECUTION = PASS'
}
finally {
  foreach ($process in @($frontend, $backend)) { try { Stop-QualificationProcess $process } catch { $cleanupFailures.Add($_.Exception.Message) } }
  if ($dbName -and $CertificateAdminUrl) {
    try { $env:CERT_ADMIN_URL = $CertificateAdminUrl; $env:CERT_DB_NAME = $dbName; $env:CERT_DB_ACTION = 'drop'; python (Join-Path $root 'scripts\create_disposable_certification_database.py') | Out-Null; Assert-LastExit 'drop disposable database' } catch { $cleanupFailures.Add("database cleanup failed: $($_.Exception.Message)") }
  }
  try { Remove-QualificationRuntime $runtime } catch { $cleanupFailures.Add($_.Exception.Message) }
  foreach ($name in $old.Keys) { if ($null -eq $old[$name]) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue } else { [Environment]::SetEnvironmentVariable($name, $old[$name], 'Process') } }
  foreach ($name in 'FORWARDER_E2E_PASSWORD','SECRET_KEY','JWT_SECRET_KEY') {
    if ([Environment]::GetEnvironmentVariable($name,'Process') -ne $old[$name]) { $cleanupFailures.Add("ephemeral qualification credential remains in the process environment: $name") }
  }
  if ($cleanupFailures.Count -gt 0) { throw ('E2E_CLEANUP = FAIL: ' + ($cleanupFailures -join '; ')) }
  Write-Output 'E2E_CLEANUP = PASS'
}
