#requires -Version 5.1
[CmdletBinding()]
param([switch]$Execute,[switch]$ConfirmDeployment,[Parameter(Mandatory=$true)][string]$ApplicationZip,[Parameter(Mandatory=$true)][string]$ApplicationManifest,[Parameter(Mandatory=$true)][string]$TargetReleasePath,[Parameter(Mandatory=$true)][string]$PreflightEvidencePath)
$ErrorActionPreference='Stop'
$ReleaseId='S7-RC-a257669-rg1-frozen';$SourceSha='a2576690364fcaf58ca7ddc6c57143c3084bbb00';$ZipSha='aca7a147cad97edf0e3f03d763c63471c283f62021a23a4e6a47b5e59aa88534';$TargetHead='20260908_governed_international_geography'
$RollbackStrategy='KEEP_UPGRADED_DB_AND_ROLLBACK_APP'
function Hash([string]$p){(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}
function Require([bool]$v,[string]$m){if(-not $v){throw "DEPLOYMENT_STOP: $m"}}
Require ($Execute -and $ConfirmDeployment) 'explicit -Execute -ConfirmDeployment is required'; Require ((Hash $ApplicationZip) -eq $ZipSha) 'application ZIP hash mismatch'; Require (Test-Path $ApplicationManifest) 'application manifest absent'; Require (Test-Path $PreflightEvidencePath) 'approved read-only preflight evidence absent'; Require (-not(Test-Path $TargetReleasePath)) 'target release path collision'
Write-Output 'PRECHECK_COMPLETE';Write-Output 'READY_FOR_FIRST_MUTATION'
# Phase 1 begins only after the two lines above: capture backup identities, stage,
# hash, extract, validate manifest/source/head, migrate via packaged runtime, switch
# exact task/IIS targets, prove singular candidate PID/listener, health/CORS, then
# finalize. Any failure restores the captured task/IIS/current application; DB stays
# upgraded and requires a separate recovery decision (no automated downgrade).
throw 'DEPLOYMENT_EXECUTION_NOT_IMPLEMENTED: use only the qualified operator package after a separately authorized deployment mission.'
