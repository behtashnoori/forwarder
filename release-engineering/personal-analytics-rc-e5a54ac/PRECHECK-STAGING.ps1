[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$StagingHostname,[Parameter(Mandatory=$true)][string]$StagingIisSite,[Parameter(Mandatory=$true)][string]$StagingTaskName,[Parameter(Mandatory=$true)][string]$DatabaseName,[int]$BackendPort=5201,[int]$IisPort=8443)
$ErrorActionPreference='Stop'
function Deny([string]$message){ throw "STAGING_PRECHECK_DENIED: $message" }
if($env:APP_ENV -notin @('staging','uat')){Deny 'APP_ENV must be staging or uat'}
if([string]::IsNullOrWhiteSpace($StagingHostname) -or [string]::IsNullOrWhiteSpace($StagingIisSite) -or [string]::IsNullOrWhiteSpace($StagingTaskName)){Deny 'staging identity is incomplete'}
if($BackendPort -eq 5101 -or $StagingTaskName -eq 'Forwarder Backend Production' -or $StagingIisSite -eq 'forwarder'){Deny 'production listener, task, or IIS site is forbidden'}
if($DatabaseName -match '(?i)(production|prod|live)' -or $DatabaseName -notmatch '^(forwarder_personal_analytics_uat|forwarder_staging_)'){Deny 'database name is not allow-listed'}
if($StagingHostname -match '(?i)production'){Deny 'production-like hostname is forbidden'}
Write-Output 'PREFLIGHT_READ_ONLY=PASS'; Write-Output 'STAGING_IDENTITY=PASS'
