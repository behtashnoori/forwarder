#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProductionRoot,[Parameter(Mandatory=$true)][string]$RuntimeRoot,[string]$SiteName='forwarder',[string]$TaskName='Forwarder Backend Production',[int]$Port=5101,[string]$PsqlPath='')
$ErrorActionPreference='Stop'
# DP-R02/DP-R10: this file is deliberately read-only.  It contains no write,
# copy, archive, task, IIS, service, process, or database mutation command.
function Fail([string]$m){throw "PREFLIGHT_FAILED: $m"}
function Redact-Url([string]$v){try{$u=[Uri]$v; "$($u.Scheme)://$($u.Host):$($u.Port)/$($u.AbsolutePath.Trim('/'))"}catch{'UNPARSEABLE'}}
function Get-EnvShape([string]$p){$map=@{}; foreach($line in Get-Content -LiteralPath $p){if($line -match '^\s*([^#=\s]+)=(.*)$'){$map[$matches[1]]=$matches[2]}}; [ordered]@{DATABASE_URL=if($map.ContainsKey('DATABASE_URL')){Redact-Url $map.DATABASE_URL}else{'MISSING'};CORS_ORIGIN=if($map.ContainsKey('CORS_ORIGIN') -or $map.ContainsKey('CORS_ORIGINS')){'PRESENT'}else{'MISSING'};SECRET_KEY=if($map.ContainsKey('SECRET_KEY')){'PRESENT_UNVERIFIED_SECRET'}else{'MISSING'};JWT_SECRET_KEY=if($map.ContainsKey('JWT_SECRET_KEY')){'PRESENT_UNVERIFIED_SECRET'}else{'MISSING'}}}
function Read-InternationalCityReadiness([string]$Psql,[string]$Db,[string]$Host,[int]$DbPort,[string]$User){
 if(-not (Test-Path -LiteralPath $Psql -PathType Leaf)){return @{result='BLOCKED_WITH_EXACT_REASON';reason='psql unavailable'}}
 $sql="BEGIN TRANSACTION READ ONLY; SELECT 'DUPLICATE=' || count(*) FROM (SELECT country_id, un_locode FROM international_city WHERE un_locode IS NOT NULL GROUP BY country_id,un_locode HAVING count(*)>1) x; SELECT 'MALFORMED=' || count(*) FROM international_city WHERE un_locode IS NOT NULL AND (length(un_locode)<>5 OR un_locode<>upper(un_locode)); ROLLBACK;"
 $out=& $Psql -X -q -v ON_ERROR_STOP=1 -h $Host -p $DbPort -U $User -d $Db -Atc $sql; if($LASTEXITCODE -ne 0){return @{result='BLOCKED_WITH_EXACT_REASON';reason='read-only readiness query failed'}}; $d=($out|Where-Object{$_ -like 'DUPLICATE=*'}).Split('=')[1];$m=($out|Where-Object{$_ -like 'MALFORMED=*'}).Split('=')[1]; return @{result=if($d -eq '0' -and $m -eq '0'){'READY'}else{'BLOCKED_WITH_EXACT_REASON'};duplicates=$d;malformed=$m}
}
function Read-DatabaseIdentity([string]$Psql,[string]$Db,[string]$Host,[int]$DbPort,[string]$User){
 if([string]::IsNullOrWhiteSpace($Psql)){return @{result='NOT_REQUESTED'}}
 if(-not (Test-Path -LiteralPath $Psql -PathType Leaf)){return @{result='BLOCKED_WITH_EXACT_REASON';reason='psql unavailable'}}
 $sql="BEGIN TRANSACTION READ ONLY; SELECT 'DATABASE=' || current_database(); SELECT 'ALEMBIC=' || version_num FROM alembic_version; ROLLBACK;"
 $out=& $Psql -X -q -v ON_ERROR_STOP=1 -h $Host -p $DbPort -U $User -d $Db -Atc $sql
 if($LASTEXITCODE -ne 0){return @{result='BLOCKED_WITH_EXACT_REASON';reason='database identity query failed'}}
 $rev=($out|Where-Object{$_ -like 'ALEMBIC=*'}).Split('=')[1]
 $city=Read-InternationalCityReadiness $Psql $Db $Host $DbPort $User
 return @{result='READ_ONLY_COMPLETE';database=($out|Where-Object{$_ -like 'DATABASE=*'}).Split('=')[1];alembic_revision=$rev;international_city=$city}
}
$envPath=Join-Path $RuntimeRoot 'production.env'; if(-not(Test-Path -LiteralPath $envPath)){Fail 'production.env absent'}
$task=Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop; $taskInfo=Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
Import-Module WebAdministration -ErrorAction Stop; $site=Get-Website -Name $SiteName -ErrorAction Stop; $bindings=Get-WebBinding -Name $SiteName -ErrorAction Stop
$listeners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue|ForEach-Object{Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)"|Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine})
$current=Get-ItemProperty -Path "IIS:\Sites\$SiteName" -Name physicalPath -ErrorAction Stop
$shape=Get-EnvShape $envPath
$report=[ordered]@{mode='READ_ONLY_PREFLIGHT';host=$env:COMPUTERNAME;current_iis_path=[string]$current.physicalPath;iis_state=$site.State;bindings=@($bindings|ForEach-Object{$_.bindingInformation});task=@{state=$task.State;last_result=$taskInfo.LastTaskResult;actions=@($task.Actions|ForEach-Object{"$($_.Execute) $($_.Arguments)"})};listeners=$listeners;config=$shape;database=@{result='DATABASE_CONNECTIVITY_NOT_REQUESTED';note='Supply -PsqlPath only after deployment-time credential handling is approved; the script never prints credentials.'};rollback_release=if(Test-Path -LiteralPath $current.physicalPath){$current.physicalPath}else{'UNKNOWN'};target_path_collision='DEPLOYMENT_TIME_DISCOVERY'}
$report|ConvertTo-Json -Depth 6
