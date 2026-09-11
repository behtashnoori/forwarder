[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PreviousBackendReleasePath,
    [Parameter(Mandatory=$true)][string]$PreviousFrontendReleasePath,
    [string]$SimulationRoot,
    [string]$BaselinePath
)
$ErrorActionPreference='Stop'
$invokeParams=@{ValidateOnly=$true;PreviousBackendReleasePath=$PreviousBackendReleasePath;PreviousFrontendReleasePath=$PreviousFrontendReleasePath}
if($SimulationRoot){$invokeParams.SimulationRoot=$SimulationRoot};if($BaselinePath){$invokeParams.BaselinePath=$BaselinePath}
& (Join-Path $PSScriptRoot 'deploy_uat_shipment_summary_rc1_4c96ea4.ps1') @invokeParams
exit $LASTEXITCODE
