[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PreviousBackendReleasePath,
    [Parameter(Mandatory=$true)][string]$PreviousFrontendReleasePath,
    [switch]$ConfirmDeployment,
    [string]$SimulationRoot,
    [string]$BaselinePath,
    [switch]$SimulateStagingFailure,
    [switch]$SimulateStartupFailure,
    [switch]$SimulateVerificationFailure
)
$ErrorActionPreference='Stop'
if(-not $ConfirmDeployment){throw 'DEPLOYMENT_GATE: -ConfirmDeployment is required'}
$invokeParams=@{Execute=$true;ConfirmDeployment=$true;PreviousBackendReleasePath=$PreviousBackendReleasePath;PreviousFrontendReleasePath=$PreviousFrontendReleasePath;SimulateStagingFailure=$SimulateStagingFailure;SimulateStartupFailure=$SimulateStartupFailure;SimulateVerificationFailure=$SimulateVerificationFailure}
if($SimulationRoot){$invokeParams.SimulationRoot=$SimulationRoot};if($BaselinePath){$invokeParams.BaselinePath=$BaselinePath}
& (Join-Path $PSScriptRoot 'deploy_uat_shipment_summary_rc1_4c96ea4.ps1') @invokeParams
exit $LASTEXITCODE
