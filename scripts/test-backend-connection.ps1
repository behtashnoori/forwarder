[CmdletBinding()]
param(
    [string]$ServerIP = "127.0.0.1",
    [int]$ApiPort = 5001,
    [switch]$AllowRemote
)

$ErrorActionPreference = "Stop"
$localTargets = @("127.0.0.1", "localhost", "::1")
if (-not $AllowRemote -and $localTargets -notcontains $ServerIP) {
    throw "Remote target refused. Pass -AllowRemote only after explicit target approval."
}

$healthUrl = "http://{0}:{1}/api/health" -f $ServerIP, $ApiPort
$pingUrl = "http://{0}:{1}/api/health/ping" -f $ServerIP, $ApiPort
$readyUrl = "http://{0}:{1}/api/health/ready" -f $ServerIP, $ApiPort

Write-Host ("Testing approved backend target {0}:{1}" -f $ServerIP, $ApiPort) -ForegroundColor Cyan
foreach ($probe in @(
    @{ Name = "Liveness"; Uri = $pingUrl },
    @{ Name = "Database health"; Uri = $healthUrl },
    @{ Name = "Readiness"; Uri = $readyUrl }
)) {
    try {
        $response = Invoke-WebRequest -Uri $probe.Uri -UseBasicParsing -TimeoutSec 5
        Write-Host ("{0}: HTTP {1}" -f $probe.Name, $response.StatusCode) -ForegroundColor Green
    }
    catch {
        Write-Host ("{0}: failed" -f $probe.Name) -ForegroundColor Red
        throw
    }
}

Write-Host "Development command: python -m backend.run" -ForegroundColor White
Write-Host ("Windows status: powershell -File scripts/backend-service.ps1 -Action Status -Port {0}" -f $ApiPort) -ForegroundColor White
