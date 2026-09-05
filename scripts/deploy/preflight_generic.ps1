#requires -Version 5.1
[CmdletBinding()]param([Parameter(Mandatory=$true)][string]$DescriptorPath,[Parameter(Mandatory=$true)][string]$ReadOnlyEvidencePath)
$ErrorActionPreference='Stop';$d=Get-Content -Raw $DescriptorPath|ConvertFrom-Json;$live=Get-Content -Raw $ReadOnlyEvidencePath|ConvertFrom-Json
if($live.application_source_sha -ne $d.previous_application_source_sha){throw 'PRECHECK_FAIL: predecessor source mismatch'}
if($live.alembic_head -ne $d.alembic_head){throw 'PRECHECK_FAIL: migration head mismatch'}
Write-Output 'PRECHECK_COMPLETE'
