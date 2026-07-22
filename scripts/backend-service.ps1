[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Start", "Stop", "Restart", "Status")]
    [string]$Action,
    [int]$Port = 5001,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $repositoryRoot "instance\logs"
$stdoutPath = Join-Path $logDirectory "backend.stdout.log"
$stderrPath = Join-Path $logDirectory "backend.stderr.log"
$entrypointMarker = "backend.wsgi:app"

function Get-BackendOwner {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) {
        return $null
    }
    $ownerIds = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($ownerIds.Count -ne 1) {
        throw "Port $Port has ambiguous ownership; refusing process control."
    }
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($ownerIds[0])"
    if ($null -eq $processInfo) {
        throw "Unable to inspect the process listening on port $Port."
    }
    $resolvedExecutable = [System.IO.Path]::GetFullPath([string]$processInfo.ExecutablePath)
    $expectedExecutable = [System.IO.Path]::GetFullPath($pythonPath)
    $commandLine = [string]$processInfo.CommandLine
    if (-not $resolvedExecutable.Equals($expectedExecutable, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Port $Port belongs to an unexpected executable; refusing process control."
    }
    if ($commandLine.IndexOf($entrypointMarker, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Port $Port is not owned by the versioned backend entrypoint."
    }
    return $processInfo
}

function Show-FailureLogs {
    foreach ($path in @($stdoutPath, $stderrPath)) {
        if (Test-Path -LiteralPath $path) {
            Write-Host "--- $path"
            Get-Content -LiteralPath $path -Tail 40
        }
    }
}

function Wait-Endpoint {
    param([string]$Url)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Start-Backend {
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python entrypoint missing: $pythonPath. Create .venv and install requirements.txt."
    }
    $existing = Get-BackendOwner
    if ($null -ne $existing) {
        throw "The backend is already listening on port $Port (process $($existing.ProcessId))."
    }
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    $arguments = @("-m", "waitress", "--listen=0.0.0.0:$Port", $entrypointMarker)
    $started = Start-Process -FilePath $pythonPath -ArgumentList $arguments `
        -WorkingDirectory $repositoryRoot -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath -WindowStyle Hidden -PassThru
    try {
        if (-not (Wait-Endpoint "http://127.0.0.1:$Port/api/health/ping")) {
            throw "Liveness did not become healthy within $TimeoutSeconds seconds."
        }
        if (-not (Wait-Endpoint "http://127.0.0.1:$Port/api/health/ready")) {
            throw "Readiness did not become healthy within $TimeoutSeconds seconds."
        }
        $owner = Get-BackendOwner
        if ($null -eq $owner -or $owner.ProcessId -ne $started.Id) {
            throw "Listener ownership changed during startup verification."
        }
        Write-Host "Backend ready on port $Port (process $($started.Id))."
    }
    catch {
        $fresh = Get-CimInstance Win32_Process -Filter "ProcessId = $($started.Id)" -ErrorAction SilentlyContinue
        if ($null -ne $fresh) {
            Stop-Process -Id $started.Id -Force
        }
        Show-FailureLogs
        throw
    }
}

function Stop-Backend {
    $owner = Get-BackendOwner
    if ($null -eq $owner) {
        Write-Host "No backend listener exists on port $Port."
        return
    }
    Stop-Process -Id $owner.ProcessId -Force
    Write-Host "Stopped verified backend process $($owner.ProcessId)."
}

switch ($Action) {
    "Start" { Start-Backend }
    "Stop" { Stop-Backend }
    "Restart" { Stop-Backend; Start-Backend }
    "Status" {
        $owner = Get-BackendOwner
        if ($null -eq $owner) { Write-Host "Backend is stopped." }
        else { Write-Host "Backend owns port $Port (process $($owner.ProcessId))." }
    }
}
