#requires -Version 5.1
[CmdletBinding()]param([Parameter(Mandatory=$true)][string]$DescriptorPath)
$ErrorActionPreference='Stop';$d=Get-Content -Raw $DescriptorPath|ConvertFrom-Json;if([string]::IsNullOrWhiteSpace($d.release_id)){throw 'invalid descriptor'};Write-Output 'OFFLINE_DESCRIPTOR_VALID=PASS'
