#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackagePath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedPackageSha256,
    [Parameter(Mandatory=$true)][string]$TargetReleasePath,
    [Parameter(Mandatory=$true)][string]$PreflightResultPath,
    [string]$OutputDirectory = 'C:\1-webapp\forwarder-runtime\deployment-evidence',
    [string]$EnvironmentFile = 'C:\1-webapp\forwarder-runtime\production.env',
    [string]$TaskName = 'Forwarder Backend Production',
    [string]$IisSiteName = 'forwarder',
    [string]$PublicBaseUrl = 'https://samand.forwarderet.ir',
    [int]$BackendPort = 5101,
    [string]$PsqlPath = 'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [string]$FixtureStatePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ExpectedSource='e36ee7cee157657c97dc42a539eaf1909f510a33'
$ExpectedTarget='20260926_fixed_shipment_responsible_expert'
$errors=New-Object 'System.Collections.Generic.List[string]'
function Add-ErrorCode([string]$Code){if(-not$errors.Contains($Code)){$errors.Add($Code)}}
function NPath([string]$Value){if([string]::IsNullOrWhiteSpace($Value)){return $null};try{return [IO.Path]::GetFullPath($Value.Trim().Trim('"').Trim("'")).TrimEnd('\')}catch{return $null}}
function SamePath([string]$A,[string]$B){$a=NPath $A;$b=NPath $B;return($a-and$b-and[string]::Equals($a,$b,[StringComparison]::OrdinalIgnoreCase))}
function Probe([string]$Uri){try{$r=Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 15 -MaximumRedirection 0 -ErrorAction Stop;return [pscustomobject]@{uri=$Uri;status=[int]$r.StatusCode;ok=([int]$r.StatusCode-eq200);content=[string]$r.Content}}catch{$status=$null;if($_.Exception.PSObject.Properties['Response'] -and $_.Exception.Response){try{$status=[int]$_.Exception.Response.StatusCode}catch{}};return [pscustomobject]@{uri=$Uri;status=$status;ok=$false;content=$null}}}
function Read-Map([string]$Path){$m=@{};if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw 'environment missing'};foreach($line in Get-Content -LiteralPath $Path){if($line.Trim()-and-not$line.TrimStart().StartsWith('#')-and$line-match'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$'){$m[$Matches[1]]=$Matches[2].Trim().Trim('"').Trim("'")}};return $m}
function Connection([hashtable]$Map){if(-not$Map.ContainsKey('DATABASE_URL')){throw 'DATABASE_URL absent'};$u=[Uri][string]$Map['DATABASE_URL'];$ui=$u.UserInfo.Split(':',2);return [pscustomobject]@{Host=$u.Host;Port=$(if($u.Port-gt0){$u.Port}else{5432});Database=[Uri]::UnescapeDataString($u.AbsolutePath.Trim('/'));User=[Uri]::UnescapeDataString($ui[0]);Password=$(if($ui.Count-eq2){[Uri]::UnescapeDataString($ui[1])}else{''})}}
function Run-Sql([string]$Sql,[object]$Db){if($Sql-notmatch'(?is)^\s*BEGIN\s+TRANSACTION\s+READ\s+ONLY\s*;'-or$Sql-notmatch'(?is)COMMIT\s*;\s*$'-or$Sql-match'(?im)\b(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|TRUNCATE|GRANT|REVOKE|VACUUM|REINDEX|CALL|DO)\b'){throw 'read-only SQL gate failed'};$s=New-Object Diagnostics.ProcessStartInfo;$s.FileName=$PsqlPath;$s.Arguments='-X -w -q -A -t -F "|" -v ON_ERROR_STOP=1 -h "'+$Db.Host+'" -p '+$Db.Port+' -U "'+$Db.User+'" -d "'+$Db.Database+'"';$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardInput=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true;if($Db.Password){$s.EnvironmentVariables['PGPASSWORD']=$Db.Password};$p=New-Object Diagnostics.Process;$p.StartInfo=$s;try{if(-not$p.Start()){throw 'psql start failed'};$p.StandardInput.Write($Sql);$p.StandardInput.Close();$o=$p.StandardOutput.ReadToEndAsync();$e=$p.StandardError.ReadToEndAsync();if(-not$p.WaitForExit(120000)){$p.Kill();throw 'psql timeout'};if($p.ExitCode-ne0){throw 'psql failed'};return @(([string]$o.Result)-split"`r?`n"|Where-Object{$_-match'\S'})}finally{if($s.EnvironmentVariables.ContainsKey('PGPASSWORD')){$s.EnvironmentVariables.Remove('PGPASSWORD')};$p.Dispose()}}

& (Join-Path $PSScriptRoot 'Verify-ForwarderV110ProductionPackage.ps1') -PackagePath $PackagePath -ExpectedSha256 $ExpectedPackageSha256 | Out-Null
if(-not(Test-Path -LiteralPath $PreflightResultPath -PathType Leaf)){throw 'preflight result missing'}
$preflight=Get-Content -Raw -LiteralPath $PreflightResultPath|ConvertFrom-Json
$target=NPath $TargetReleasePath
if(-not(Test-Path -LiteralPath $target -PathType Container)){throw 'target release missing'}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $target 'release-manifest.json')|ConvertFrom-Json
if($manifest.application_version-ne'1.10.0'-or$manifest.application_commit-ne$ExpectedSource-or$manifest.database_revision-ne$ExpectedTarget){Add-ErrorCode 'RELEASE_MANIFEST_IDENTITY_MISMATCH'}

$state=$null
if($FixtureStatePath){$state=Get-Content -Raw -LiteralPath $FixtureStatePath|ConvertFrom-Json}
else{
    try{
        Import-Module WebAdministration -ErrorAction Stop
        $site=Get-Website -Name $IisSiteName -ErrorAction Stop
        $tasks=@(Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop);if($tasks.Count-ne1){throw 'task ambiguous'};$task=$tasks[0];$actions=@($task.Actions);if($actions.Count-ne1){throw 'action ambiguous'}
        $rows=@(Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction Stop|Where-Object{$_.LocalAddress-eq'127.0.0.1'});$owners=@($rows|Select-Object -ExpandProperty OwningProcess -Unique);if($owners.Count-ne1){throw 'listener ambiguous'};$proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop
        $state=[pscustomobject]@{iis_path=[string]$site.PhysicalPath;task_enabled=[bool]$task.Settings.Enabled;task_action=([string]$actions[0].Arguments);listener_pid=[int]$owners[0];listener_executable=[string]$proc.ExecutablePath;listener_command=[string]$proc.CommandLine;listener_up=$true;database_head=$null;post_assertions=@()}
    }catch{Add-ErrorCode 'LIVE_TOPOLOGY_VERIFICATION_FAILED'}
}
if($state){
    if(-not(SamePath ([string]$state.iis_path) (Join-Path $target 'dist'))){Add-ErrorCode 'IIS_TARGET_MISMATCH'}
    if(-not[bool]$state.task_enabled){Add-ErrorCode 'TASK_NOT_ENABLED'}
    if(-not(SamePath ([string]$state.listener_executable) (Join-Path $target 'runtime\python.exe'))){Add-ErrorCode 'LISTENER_RUNTIME_MISMATCH'}
    if(([string]$state.listener_command-notmatch'(?i)-m\s+waitress')-or([string]$state.listener_command-notmatch'(?i)backend\.wsgi:app')){Add-ErrorCode 'LISTENER_COMMAND_MISMATCH'}
}

$localHealth=if($FixtureStatePath){[pscustomobject]@{status=$(if($state.health){200}else{503});ok=[bool]$state.health}}else{Probe "http://127.0.0.1:$BackendPort/api/health"}
$localReady=if($FixtureStatePath){[pscustomobject]@{status=$(if($state.readiness){200}else{503});ok=[bool]$state.readiness}}else{Probe "http://127.0.0.1:$BackendPort/api/health/ready"}
$publicHealth=if($FixtureStatePath){[pscustomobject]@{status=$(if($state.public_health){200}else{503});ok=[bool]$state.public_health}}else{Probe ($PublicBaseUrl.TrimEnd('/')+'/api/health')}
$publicReady=if($FixtureStatePath){[pscustomobject]@{status=$(if($state.public_readiness){200}else{503});ok=[bool]$state.public_readiness}}else{Probe ($PublicBaseUrl.TrimEnd('/')+'/api/health/ready')}
$frontend=if($FixtureStatePath){[pscustomobject]@{status=200;ok=[bool]$state.frontend}}else{Probe ($PublicBaseUrl.TrimEnd('/')+'/')}
$login=if($FixtureStatePath){[pscustomobject]@{status=200;ok=[bool]$state.login_shell}}else{Probe ($PublicBaseUrl.TrimEnd('/')+'/login')}
$numeric=if($FixtureStatePath){[pscustomobject]@{status=404;ok=([int]$state.numeric_tracking_status-in@(400,404))}}else{$p=Probe ($PublicBaseUrl.TrimEnd('/')+'/api/public/track/1');[pscustomobject]@{status=$p.status;ok=($p.status-in@(400,404))}}
$invalid=if($FixtureStatePath){[pscustomobject]@{status=404;ok=([int]$state.invalid_tracking_status-eq404)}}else{$p=Probe ($PublicBaseUrl.TrimEnd('/')+'/api/public/track/invalid-opaque-production-verification');[pscustomobject]@{status=$p.status;ok=($p.status-eq404)}}
foreach($pair in @(@('LOCAL_HEALTH',$localHealth),@('LOCAL_READINESS',$localReady),@('PUBLIC_HEALTH',$publicHealth),@('PUBLIC_READINESS',$publicReady),@('FRONTEND',$frontend),@('LOGIN_SHELL',$login),@('NUMERIC_TRACKING_DENIAL',$numeric),@('INVALID_TRACKING_DENIAL',$invalid))){if(-not$pair[1].ok){Add-ErrorCode ($pair[0]+'_FAILED')}}

$assertions=@()
if($FixtureStatePath){$assertions=@($state.post_assertions);if([string]$state.database_head-ne$ExpectedTarget){Add-ErrorCode 'DATABASE_HEAD_MISMATCH'}}
else{
    try{$db=Connection (Read-Map $EnvironmentFile);$sql=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'sql\post-migration-assertions-readonly.sql');$assertions=@(Run-Sql $sql $db|ForEach-Object{$parts=$_.Split('|',3);[pscustomobject]@{code=$parts[0];state=$parts[1];detail=$parts[2]}});$db.Password=$null;if(@($assertions|Where-Object{$_.state-ne'PASS'}).Count-gt0){Add-ErrorCode 'POST_MIGRATION_ASSERTIONS_BLOCKED'}}catch{Add-ErrorCode 'POST_MIGRATION_ASSERTIONS_UNAVAILABLE'}
}

$documentPath=[string]$preflight.config.DOCUMENT_STORAGE_ROOT.path
if(-not$documentPath-or-not(Test-Path -LiteralPath $documentPath -PathType Container)){Add-ErrorCode 'DOCUMENT_STORAGE_CONTINUITY_FAILED'}
$status=if($errors.Count-eq0){'PASS'}else{'BLOCKED'}
$result=[ordered]@{schema='forwarder-v1.10.0-post-deploy-verification-v1';generated_utc=[DateTime]::UtcNow.ToString('o');status=$status;product_version='1.10.0';application_commit=$ExpectedSource;database_head=$ExpectedTarget;package_sha256=$ExpectedPackageSha256.ToLowerInvariant();target_release_path=$target;local_health=$localHealth;local_readiness=$localReady;public_health=$publicHealth;public_readiness=$publicReady;frontend=$frontend;login_shell=$login;numeric_tracking_denial=$numeric;invalid_tracking_denial=$invalid;post_migration_assertions=$assertions;document_storage_path=$documentPath;business_writes_performed=$false;errors=@($errors)}
if(-not(Test-Path -LiteralPath $OutputDirectory -PathType Container)){throw 'output directory must already exist'}
$path=Join-Path (NPath $OutputDirectory) ('Forwarder-v1.10.0-PostDeploy-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'.json');[IO.File]::WriteAllText($path,(($result|ConvertTo-Json -Depth 10)+"`n"),(New-Object Text.UTF8Encoding($false)))
Write-Output ('PRODUCTION_POST_DEPLOY_VERIFICATION='+$status)
Write-Output ('SANITIZED_RESULT='+$path)
if($status-ne'PASS'){exit 2}
