#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ReleasePath,[Parameter(Mandatory=$true)][string]$ExpectedRuntime,[Parameter(Mandatory=$true)][int]$Port,[Parameter(Mandatory=$true)][string]$CanonicalOrigin)
$ErrorActionPreference='Stop'
function Require([bool]$v,[string]$m){if(-not $v){throw "VALIDATION_FAILED: $m"}}
$m=Get-Content -Raw -LiteralPath (Join-Path $ReleasePath 'release-manifest.json')|ConvertFrom-Json
Require ($m.source_commit -eq 'a2576690364fcaf58ca7ddc6c57143c3084bbb00') 'source identity mismatch';Require ($m.alembic_head -eq '20260908_governed_international_geography') 'Alembic identity mismatch'
$p=@(Get-NetTCPConnection -State Listen -LocalPort $Port|ForEach-Object{Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)"});Require ($p.Count -eq 1) 'listener is not singular';Require ($p[0].ExecutablePath -eq $ExpectedRuntime) 'listener runtime mismatch'
foreach($path in @('/','/api/health','/api/health/ping')){Require ((Invoke-WebRequest -UseBasicParsing "$CanonicalOrigin$path").StatusCode -eq 200) "health failed: $path"};foreach($origin in @($CanonicalOrigin,'https://server.logisticmarket.ir','https://unknown.invalid')){$r=Invoke-WebRequest -UseBasicParsing "$CanonicalOrigin/api/health" -Headers @{Origin=$origin};if($origin -eq $CanonicalOrigin){Require($r.Headers['Access-Control-Allow-Origin'] -eq $origin)'canonical CORS failed'}else{Require($r.Headers['Access-Control-Allow-Origin'] -ne $origin)'unexpected CORS allow'}};Write-Output 'DEPLOYED_AND_VERIFIED'
