param([string]$EvidenceDirectory = (Join-Path $env:TEMP ('forwarder-fwd06-browser-' + [guid]::NewGuid().ToString('N'))))

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ((git -C $repo branch --show-current) -ne 'feature/fwd-06-tracking-timeline') { throw 'Wrong FWD-06 branch' }
$apiPort = 5056
$uiPort = 8086
$passwordText = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$variables = @{
    APP_ENV = 'test'
    FWD04_UAT_PASSWORD = $passwordText
    FWD04_UAT_API_PORT = "$apiPort"
    FWD06_UAT_BASE_URL = "http://127.0.0.1:$uiPort"
    FWD06_UAT_API_URL = "http://127.0.0.1:$apiPort"
    FWD06_UAT_EVIDENCE_DIR = $EvidenceDirectory
    FWD06_UAT_CANDIDATE = (git -C $repo rev-parse HEAD)
    VITE_BACKEND_URL = "http://127.0.0.1:$apiPort"
}
$old = @{}
foreach ($key in $variables.Keys) {
    $old[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
    [Environment]::SetEnvironmentVariable($key, $variables[$key], 'Process')
}
$backend = $null
$frontend = $null
try {
    New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
    $backend = Start-Process -FilePath 'python' -ArgumentList '-m', 'scripts.uat.fwd04_browser_fixture' -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $EvidenceDirectory 'backend.stdout.log') -RedirectStandardError (Join-Path $EvidenceDirectory 'backend.stderr.log')
    for ($i = 0; $i -lt 60; $i++) {
        try { if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$apiPort/api/health" -TimeoutSec 1).StatusCode -eq 200) { break } } catch {}
        Start-Sleep -Milliseconds 250
    }
    if ($backend.HasExited) { throw 'Synthetic backend exited' }
    $frontend = Start-Process -FilePath 'node' -ArgumentList 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', "$uiPort", '--strictPort' -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $EvidenceDirectory 'frontend.stdout.log') -RedirectStandardError (Join-Path $EvidenceDirectory 'frontend.stderr.log')
    for ($i = 0; $i -lt 60; $i++) {
        try { if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$uiPort" -TimeoutSec 1).StatusCode -eq 200) { break } } catch {}
        Start-Sleep -Milliseconds 250
    }
    if ($frontend.HasExited) { throw 'Synthetic UI exited' }
    node (Join-Path $PSScriptRoot 'fwd06_browser_runner.mjs')
    if ($LASTEXITCODE -ne 0) { throw "FWD-06 browser UAT failed: $LASTEXITCODE" }
    Write-Output "FWD06_BROWSER_EVIDENCE=$EvidenceDirectory"
} finally {
    if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force }
    if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
    foreach ($key in $old.Keys) { [Environment]::SetEnvironmentVariable($key, $old[$key], 'Process') }
    $passwordText = $null
}
