param(
    [string]$EvidenceDirectory = (Join-Path $env:TEMP "forwarder-fwd04-uat-evidence"),
    [switch]$Fwd05QuoteCapability
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if ($Fwd05QuoteCapability) {
    if ((git -C $repo branch --show-current) -ne 'feature/fwd-05-quote-response') {
        throw 'FWD-05 qualification requires its authorized feature branch'
    }
    Push-Location $repo
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'FWD-05 production bundle build failed' }
        # The existing launcher delegates to actual native PG + Chromium tests.
        # Synthetic credentials and links stay in private in-memory pipes; no
        # operational env file, shared port/service or human password is used.
        python -B scripts/uat/run_fwd05_disposable_postgres.py backend/tests/test_fwd05_browser.py -k postgresql --show-capture=no --disable-warnings
        if ($LASTEXITCODE -ne 0) { throw 'FWD-05 browser qualification failed' }
    } finally { Pop-Location }
    return
}
$password = Read-Host "Synthetic FWD-04 UAT password" -AsSecureString
$passwordText = [System.Net.NetworkCredential]::new("", $password).Password
$apiPort = 5054
$uiPort = 8084
$environment = @{
    FWD04_UAT_PASSWORD = $passwordText
    FWD04_UAT_API_PORT = "$apiPort"
    FWD04_UAT_BASE_URL = "http://127.0.0.1:$uiPort"
    FWD04_UAT_API_URL = "http://127.0.0.1:$apiPort"
    FWD04_UAT_EVIDENCE_DIR = $EvidenceDirectory
    FWD04_UAT_CANDIDATE = (git -C $repo rev-parse HEAD)
    VITE_BACKEND_URL = "http://127.0.0.1:$apiPort"
}
$old = @{}
foreach ($key in $environment.Keys) { $old[$key] = [Environment]::GetEnvironmentVariable($key, "Process"); [Environment]::SetEnvironmentVariable($key, $environment[$key], "Process") }
$backend = $null
$frontend = $null
try {
    New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
    $backend = Start-Process -FilePath "python" -ArgumentList "-m", "scripts.uat.fwd04_browser_fixture" -WorkingDirectory $repo -WindowStyle Hidden -PassThru
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try { if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$apiPort/api/health" -TimeoutSec 1).StatusCode -eq 200) { break } } catch {}
        Start-Sleep -Milliseconds 250
    }
    if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port $apiPort -InformationLevel Quiet)) { throw "FWD-04 fixture backend did not start on loopback" }
    $frontend = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev -- --port $uiPort" -WorkingDirectory $repo -WindowStyle Hidden -PassThru
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try { if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$uiPort" -TimeoutSec 1).StatusCode -eq 200) { break } } catch {}
        Start-Sleep -Milliseconds 250
    }
    if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port $uiPort -InformationLevel Quiet)) { throw "FWD-04 local UI did not start on loopback" }
    node (Join-Path $PSScriptRoot "fwd04_browser_runner.mjs")
    if ($LASTEXITCODE -ne 0) { throw "FWD-04 browser runner failed with exit code $LASTEXITCODE" }
} finally {
    if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force }
    if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
    foreach ($key in $old.Keys) { [Environment]::SetEnvironmentVariable($key, $old[$key], "Process") }
    $passwordText = $null
}
