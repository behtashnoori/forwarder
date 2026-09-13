[CmdletBinding(DefaultParameterSetName = 'Validate')]
param(
    [string]$UserIdentifier,
    [string]$EnvironmentFile = 'C:\1-webapp\forwarder-runtime\production.env',
    [Parameter(ParameterSetName = 'Validate', Mandatory = $true)]
    [switch]$ValidateOnly,
    [Parameter(ParameterSetName = 'Execute', Mandatory = $true)]
    [switch]$Execute,
    [Parameter(ParameterSetName = 'Execute', Mandatory = $true)]
    [switch]$ConfirmRepair
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot 'runtime\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $repoRoot '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$tool = Join-Path $PSScriptRoot 'repair_forwarder_production_workflow.py'
if (-not (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf)) { throw "Production environment file was not found: $EnvironmentFile" }
$arguments = @('-m', 'scripts.repair_forwarder_production_workflow', '--environment-file', $EnvironmentFile)
if ($UserIdentifier) { $arguments += @('--user-identifier', $UserIdentifier) }
if ($ValidateOnly) { $arguments += '--validate-only' }
if ($Execute) {
    $answer = Read-Host 'Type REPAIR to apply the exact validated changes'
    if ($answer -cne 'REPAIR') { throw 'Repair cancelled; exact REPAIR confirmation required.' }
    $arguments += @('--execute', '--confirm-repair', $answer)
}
Push-Location $repoRoot
try {
    & $python @arguments
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
