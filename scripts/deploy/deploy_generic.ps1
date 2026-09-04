#requires -Version 5.1
[CmdletBinding()]param([switch]$Execute,[switch]$ConfirmDeployment,[Parameter(Mandatory=$true)][string]$DescriptorPath)
$ErrorActionPreference='Stop';if(-not($Execute -and $ConfirmDeployment)){throw 'DEPLOYMENT_STOP: explicit authorization required'}
$d=Get-Content -Raw $DescriptorPath|ConvertFrom-Json;Write-Output ('CANDIDATE='+$d.release_id);throw 'DEPLOYMENT_STOP: live deployment is separately authorized'
