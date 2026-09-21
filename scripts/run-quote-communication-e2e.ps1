[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$CertificateAdminUrl
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$admin = [Uri]$CertificateAdminUrl
if ($admin.Host -notin @('localhost', '127.0.0.1', '[::1]', '::1')) {
  throw 'Quote communication qualification requires a loopback PostgreSQL administrator URL.'
}

$databaseName = 'forwarder_integrated_cert_quote_communication_e2e'
$databasePort = if ($admin.Port -gt 0) { $admin.Port } else { 5432 }
$databaseUrl = "postgresql://$($admin.UserInfo)@127.0.0.1:$databasePort/$databaseName"
$runId = [guid]::NewGuid().ToString('N')
$runtimeParent = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$runtime = Join-Path $runtimeParent "forwarder-quote-communication-e2e-$runId"
$fixture = Join-Path $runtime 'fixtures.json'
$evidence = Join-Path $root 'test-results\quote-communication-e2e'
$backend = $null
$frontend = $null
$databaseCreated = $false
$old = @{}

function Assert-LastExit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "Qualification step failed: $Step" }
}

function Wait-Http([string]$Url, [int]$Seconds = 90) {
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
  if ((Split-Path -Parent $resolved) -ne $expectedParent -or $leaf -notmatch '^forwarder-quote-communication-e2e-[0-9a-f]{32}$') {
    throw "Refusing to remove an unowned runtime path: $resolved"
  }
  Remove-Item -LiteralPath $resolved -Recurse -Force
}

try {
  foreach ($name in @(
    'APP_ENV', 'DATABASE_URL', 'E2E_DATABASE_URL', 'FORWARDER_E2E_PASSWORD',
    'FORWARDER_E2E_FIXTURE_PATH', 'SECRET_KEY', 'JWT_SECRET_KEY', 'CORS_ORIGINS',
    'VITE_BACKEND_URL', 'PORT', 'PLAYWRIGHT_BASE_URL', 'PLAYWRIGHT_EXTERNAL_SERVER',
    'CERT_ADMIN_URL', 'CERT_DB_NAME', 'CERT_DB_ACTION'
  )) {
    $old[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  }

  New-Item -ItemType Directory -Force -Path $runtime, $evidence | Out-Null
  $password = [guid]::NewGuid().ToString('N') + 'Qa9!'
  $secret = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

  $env:CERT_ADMIN_URL = $CertificateAdminUrl
  $env:CERT_DB_NAME = $databaseName
  $env:CERT_DB_ACTION = 'create'
  python (Join-Path $root 'scripts\create_disposable_certification_database.py') | Out-Null
  Assert-LastExit 'create owned disposable database'
  $databaseCreated = $true

  $env:APP_ENV = 'uat'
  $env:DATABASE_URL = $databaseUrl
  $env:E2E_DATABASE_URL = $databaseUrl
  $env:FORWARDER_E2E_PASSWORD = $password
  $env:FORWARDER_E2E_FIXTURE_PATH = $fixture
  $env:SECRET_KEY = $secret
  $env:JWT_SECRET_KEY = $secret
  $env:CORS_ORIGINS = 'http://127.0.0.1:4175'
  $env:VITE_BACKEND_URL = 'http://127.0.0.1:5012'

  $repositoryHead = (python -m scripts.browser_migration_contract repository-head).Trim()
  Assert-LastExit 'resolve repository migration head'
  python -m backend.migration_cli upgrade $repositoryHead --confirm
  Assert-LastExit 'upgrade owned browser database'
  python -m scripts.browser_migration_contract verify-database-head --expected $repositoryHead
  Assert-LastExit 'verify browser database head'
  python (Join-Path $root 'scripts\uat\seed_quote_communication_e2e.py')
  Assert-LastExit 'seed Quote communication browser fixtures'

  $env:PORT = '5012'
  $backend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'backend' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  $frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '4175' -WorkingDirectory $root -PassThru -WindowStyle Hidden
  Wait-Http 'http://127.0.0.1:5012/api/health'
  Wait-Http 'http://127.0.0.1:4175'

  $env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:4175'
  $env:PLAYWRIGHT_EXTERNAL_SERVER = 'true'
  npx playwright test e2e/quote-communication.spec.ts --output $evidence
  Assert-LastExit 'real browser Quote communication journeys'
  python (Join-Path $root 'scripts\uat\audit_quote_communication_e2e.py')
  Assert-LastExit 'persisted Quote communication browser audit'
  Write-Output 'QUOTE_COMMUNICATION_BROWSER_QUALIFICATION = PASS'
}
finally {
  foreach ($process in @($frontend, $backend)) {
    try { Stop-OwnedProcess $process } catch {}
  }
  if ($databaseCreated) {
    $env:CERT_ADMIN_URL = $CertificateAdminUrl
    $env:CERT_DB_NAME = $databaseName
    $env:CERT_DB_ACTION = 'drop'
    python (Join-Path $root 'scripts\create_disposable_certification_database.py') | Out-Null
  }
  Remove-OwnedRuntime $runtime
  foreach ($name in $old.Keys) {
    if ($null -eq $old[$name]) {
      Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    } else {
      [Environment]::SetEnvironmentVariable($name, $old[$name], 'Process')
    }
  }
  Write-Output 'QUOTE_COMMUNICATION_E2E_CLEANUP = PASS'
}
