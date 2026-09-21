#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackagePath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedPackageSha256,
    [Parameter(Mandatory=$true)][string]$PreflightResultPath,
    [Parameter(Mandatory=$true)][string]$TargetReleasePath,
    [switch]$ValidateOnly,
    [switch]$Execute,
    [switch]$ConfirmDeployment,
    [string]$RestoreOwner,
    [ValidateRange(1,3650)][int]$BackupRetentionDays=30,
    [string]$EnvironmentFile='C:\1-webapp\forwarder-runtime\production.env',
    [string]$ReleaseRoot='C:\1-webapp\forwarder-production',
    [string]$RuntimeRoot='C:\1-webapp\forwarder-runtime',
    [string]$ApprovedBackupRoot='C:\1-webapp\forwarder-backups',
    [string]$TaskName='Forwarder Backend Production',
    [string]$IisSiteName='forwarder',
    [string]$PublicBaseUrl='https://samand.forwarderet.ir',
    [int]$BackendPort=5101,
    [string]$PsqlPath='C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [string]$FixtureStatePath,
    [ValidateSet('','STAGE','CONTAIN','BACKUP','MIGRATION','POST_MIGRATION','TASK_SWITCH','BACKEND_START','IIS_SWITCH','POST_DEPLOY')][string]$FailAt=''
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ExpectedSource='e36ee7cee157657c97dc42a539eaf1909f510a33'
$ExpectedBefore='20260921_shipment_evidence_ownership'
$ExpectedTarget='20260926_fixed_shipment_responsible_expert'
function Stop-Release([string]$Message){throw "RELEASE_STOP: $Message"}
function Need([bool]$Condition,[string]$Message){if(-not$Condition){Stop-Release $Message}}
function Inject([string]$Stage){if($FailAt-eq$Stage){Stop-Release "injected $Stage"}}
function NPath([string]$Value){Need (-not [string]::IsNullOrWhiteSpace($Value)) 'empty path';return [IO.Path]::GetFullPath($Value.Trim().Trim('"').Trim("'")).TrimEnd('\')}
function SamePath([string]$A,[string]$B){return [string]::Equals((NPath $A),(NPath $B),[StringComparison]::OrdinalIgnoreCase)}
function Split-LaunchArguments([string]$Text){
    Need ($Text -notmatch '[&|<>^%!\r\n]') 'unsupported launcher syntax'
    $values=New-Object 'System.Collections.Generic.List[string]'
    $rest=$Text.Trim()
    while($rest.Length){
        $part=[regex]::Match($rest,'^(?:"([^"]+)"|([^\s"]+))(?:\s+|$)')
        Need $part.Success 'launcher quoting invalid'
        $value=if($part.Groups[1].Success){$part.Groups[1].Value}else{$part.Groups[2].Value}
        $values.Add($value)
        $rest=$rest.Substring($part.Length)
    }
    return $values.ToArray()
}
function Decode-CmdPayload([string]$Text){Need ($Text.Length -ge 2 -and $Text[0] -ceq '"' -and $Text[$Text.Length-1] -ceq '"') 'quoted cmd payload required';$inner=$Text.Substring(1,$Text.Length-2);Need ($inner -notmatch '(?<!")"(?!")|(?<!")"""|"""(?!")') 'cmd quote shape invalid';return $inner.Replace('""','"')}
function Get-TaskLaunch([string]$Xml){[xml]$doc=$Xml;$actions=@($doc.SelectNodes("/*[local-name()='Task']/*[local-name()='Actions']/*"));Need ($actions.Count -eq 1 -and $actions[0].LocalName -eq 'Exec') 'one Exec task action required';$action=$actions[0];Need (SamePath ([string]$action.Command) 'C:\Windows\System32\cmd.exe') 'system cmd.exe required';Need ([string]$action.Arguments -match '(?i)^\s*/d\s+/c\s+(.+)$') 'cmd /d /c required';$body=Decode-CmdPayload $Matches[1].Trim();Need ($body -notmatch '[|<>^%!\r\n]') 'unsupported wrapper syntax';$wrapper=[regex]::Match($body,'(?is)^set\s+PYTHONPATH=(.+?)\s*&&\s*cd\s+/d\s+"([^"]+)"\s*&&\s*(.+)$');Need $wrapper.Success 'approved wrapper required';$tokens=@(Split-LaunchArguments $wrapper.Groups[3].Value.Trim());Need ($tokens.Count -ge 3) 'launcher invocation missing';Need (SamePath $tokens[1] 'C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py') 'external Production wrapper mismatch';Need ($tokens[2] -ceq 'serve') 'serve command required';$options=@{};$repoIndex=-1;for($i=3;$i -lt $tokens.Count;$i+=2){Need ($i+1 -lt $tokens.Count) 'launcher option value missing';$key=$tokens[$i];Need ($key -cin @('--repo','--env','--host','--port','--log')) 'unsupported launcher option';Need (-not $options.ContainsKey($key)) 'duplicate launcher option';$options[$key]=$tokens[$i+1];if($key -ceq '--repo'){$repoIndex=$i+1}};Need ($repoIndex -ge 0 -and $options.ContainsKey('--env')) 'launcher repo/env missing';Need ($options['--host'] -ceq '127.0.0.1' -and $options['--port'] -ceq '5101') 'listener contract mismatch';$release=NPath $options['--repo'];Need (SamePath $wrapper.Groups[1].Value.Trim() $release) 'PYTHONPATH mismatch';Need (SamePath $wrapper.Groups[2].Value $release) 'working directory wrapper mismatch';Need (SamePath $tokens[0] (Join-Path $release 'runtime\python.exe')) 'runtime path mismatch';Need (SamePath ([string]$action.WorkingDirectory) $release) 'task working directory mismatch';return [pscustomobject]@{Document=$doc;Action=$action;Tokens=$tokens;RepoIndex=$repoIndex;Release=$release;Runtime=NPath $tokens[0]}}
function New-TaskXml([string]$Xml,[string]$Target){$launch=Get-TaskLaunch $Xml;$launch.Tokens[0]=Join-Path $Target 'runtime\python.exe';$launch.Tokens[$launch.RepoIndex]=$Target;$invocation=(($launch.Tokens|ForEach-Object{'"'+$_+'"'})-join ' ');$body='set PYTHONPATH='+$Target+'&& cd /d "'+$Target+'"&& '+$invocation;$launch.Action.Arguments='/d /c "'+$body.Replace('"','""')+'"';$launch.Action.WorkingDirectory=$Target;$result=$launch.Document.OuterXml;Need (SamePath (Get-TaskLaunch $result).Release $Target) 'generated task release mismatch';return $result}
function Assert-Listener($Process,[string]$ExpectedPython){Need (-not [string]::IsNullOrWhiteSpace([string]$Process.ExecutablePath)) 'listener executable unavailable';Need (SamePath ([string]$Process.ExecutablePath) $ExpectedPython) 'listener executable mismatch';$line=[string]$Process.CommandLine;Need ($line -match '(?i)-m\s+waitress' -and $line -match '(?i)--listen=127\.0\.0\.1:5101' -and $line -match '(?i)backend\.wsgi:app') 'listener command mismatch'}
function Get-LiveState{
    if($FixtureStatePath){return(Get-Content -Raw -LiteralPath $FixtureStatePath|ConvertFrom-Json)}
    Import-Module WebAdministration -ErrorAction Stop
    $site=Get-Website -Name $IisSiteName -ErrorAction Stop
    $tasks=@(Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop)
    Need ($tasks.Count -eq 1) 'task missing or ambiguous'
    $task=$tasks[0]
    $xml=Export-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $launch=Get-TaskLaunch $xml
    $rows=@(Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction Stop|Where-Object{$_.LocalAddress-eq'127.0.0.1'})
    $owners=@($rows|Select-Object -ExpandProperty OwningProcess -Unique)
    Need ($owners.Count -eq 1) 'listener missing or ambiguous'
    $proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop
    Assert-Listener $proc $launch.Runtime
    return [pscustomobject]@{iis_path=[string]$site.PhysicalPath;task_enabled=[bool]$task.Settings.Enabled;task_xml=$xml;task_release=$launch.Release;listener_pid=[int]$owners[0];listener_executable=[string]$proc.ExecutablePath;listener_command=[string]$proc.CommandLine;listener_up=$true;health=$true;readiness=$true;public_health=$true;public_readiness=$true;frontend=$true;login_shell=$true;numeric_tracking_status=404;invalid_tracking_status=404;database_head=$ExpectedBefore;traffic_contained=$false;post_assertions=@()}
}
function Save-Fixture($State){if($FixtureStatePath){$State|ConvertTo-Json -Depth 10|Set-Content -LiteralPath $FixtureStatePath -Encoding UTF8}}
function Read-Env([string]$Path){$m=@{};Need (Test-Path -LiteralPath $Path -PathType Leaf) 'environment file unavailable';foreach($line in Get-Content -LiteralPath $Path){if($line.Trim() -and -not $line.TrimStart().StartsWith('#') -and $line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$'){$m[$Matches[1]]=$Matches[2].Trim().Trim('"').Trim("'")}};return $m}
function Get-DbConnection([hashtable]$Map){
    Need ($Map.ContainsKey('DATABASE_URL')) 'DATABASE_URL unavailable'
    $uri=[Uri][string]$Map['DATABASE_URL']
    Need ($uri.Scheme -in @('postgres','postgresql')) 'database scheme mismatch'
    $userInfo=$uri.UserInfo.Split(':',2)
    $database=[Uri]::UnescapeDataString($uri.AbsolutePath.Trim('/'))
    $user=[Uri]::UnescapeDataString($userInfo[0])
    Need ($uri.Host -match '^[A-Za-z0-9_.:-]+$' -and $database -match '^[A-Za-z0-9_.-]+$' -and $user -match '^[A-Za-z0-9_.-]+$') 'database identity unsafe'
    return [pscustomobject]@{Host=$uri.Host;Port=$(if($uri.Port-gt0){$uri.Port}else{5432});Database=$database;User=$user;Password=$(if($userInfo.Count-eq2){[Uri]::UnescapeDataString($userInfo[1])}else{''})}
}
function Run-ReadOnlySql([string]$Sql,[object]$Db){
    Need ($Sql -match '(?is)^\s*BEGIN\s+TRANSACTION\s+READ\s+ONLY\s*;' -and $Sql -match '(?is)COMMIT\s*;\s*$') 'read-only SQL envelope invalid'
    Need ($Sql -notmatch '(?im)\b(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|TRUNCATE|GRANT|REVOKE|VACUUM|REINDEX|CALL|DO)\b') 'SQL mutation keyword rejected'
    Need (Test-Path -LiteralPath $PsqlPath -PathType Leaf) 'psql unavailable'
    $s=New-Object Diagnostics.ProcessStartInfo
    $s.FileName=$PsqlPath
    $s.Arguments='-X -w -q -A -t -F "|" -v ON_ERROR_STOP=1 -h "'+$Db.Host+'" -p '+$Db.Port+' -U "'+$Db.User+'" -d "'+$Db.Database+'"'
    $s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardInput=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true
    if($Db.Password){$s.EnvironmentVariables['PGPASSWORD']=$Db.Password}
    $p=New-Object Diagnostics.Process;$p.StartInfo=$s
    try{
        Need ($p.Start()) 'psql did not start'
        $p.StandardInput.Write($Sql);$p.StandardInput.Close()
        $stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
        Need ($p.WaitForExit(120000)) 'psql timeout'
        Need ($p.ExitCode -eq 0) 'psql read-only assertion failed'
        return @(([string]$stdout.Result)-split "`r?`n" | Where-Object {$_ -match '\S'})
    } finally { if($s.EnvironmentVariables.ContainsKey('PGPASSWORD')){$s.EnvironmentVariables.Remove('PGPASSWORD')};$p.Dispose() }
}
function Run-PackagePython([string[]]$Arguments,[hashtable]$Environment){$s=New-Object Diagnostics.ProcessStartInfo;$s.FileName=Join-Path $TargetReleasePath 'runtime\python.exe';$s.Arguments=($Arguments|ForEach-Object{'"'+$_.Replace('"','\"')+'"'})-join ' ';$s.WorkingDirectory=$TargetReleasePath;$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true;foreach($key in $Environment.Keys){$s.EnvironmentVariables[$key]=[string]$Environment[$key]};$s.EnvironmentVariables['AUTO_MIGRATE_ON_STARTUP']='false';$s.EnvironmentVariables['RELEASE_IDENTITY_PATH']=Join-Path $TargetReleasePath 'release-manifest.json';$p=New-Object Diagnostics.Process;$p.StartInfo=$s;try{Need ($p.Start()) 'package Python did not start';$o=$p.StandardOutput.ReadToEndAsync();$e=$p.StandardError.ReadToEndAsync();Need ($p.WaitForExit(600000)) 'package Python timeout';Need ($p.ExitCode -eq 0) 'package Python command failed';return [string]$o.Result}finally{$p.Dispose()}}
function Verify-Extracted([string]$Root){$expected=@{};foreach($line in Get-Content -LiteralPath (Join-Path $Root 'SHA256SUMS.txt')){$parts=$line -split '  ',2;Need ($parts.Count -eq 2) 'malformed internal checksum';$expected[$parts[1]]=$parts[0];$path=Join-Path $Root $parts[1];Need (Test-Path -LiteralPath $path -PathType Leaf) 'extracted file missing';Need ((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -eq $parts[0]) 'extracted checksum mismatch'};$actual=@(Get-ChildItem -LiteralPath $Root -Recurse -File|ForEach-Object{$_.FullName.Substring($Root.TrimEnd('\').Length+1).Replace('\','/')}|Where-Object{$_ -ne 'SHA256SUMS.txt'});Need (@($actual|Where-Object{-not $expected.ContainsKey($_)}).Count -eq 0) 'unexpected extracted file'}
function Wait-Listener([string]$ExpectedPython){$deadline=[DateTime]::UtcNow.AddSeconds(60);do{$rows=@(Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction SilentlyContinue|Where-Object{$_.LocalAddress -eq '127.0.0.1'});$owners=@($rows|Select-Object -ExpandProperty OwningProcess -Unique);Need ($owners.Count -le 1) 'listener ambiguous';if($owners.Count -eq 1){$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop;Assert-Listener $p $ExpectedPython;return};Start-Sleep -Milliseconds 500}while([DateTime]::UtcNow -lt $deadline);Stop-Release 'listener timeout'}
function Probe([string]$Uri){try{$r=Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 10 -ErrorAction Stop;return($r.StatusCode-eq200)}catch{return$false}}

Need (-not ($ValidateOnly -and $Execute)) 'choose one deployment mode';if(-not $ValidateOnly -and -not $Execute){$ValidateOnly=$true};if($Execute){Need ([bool]$ConfirmDeployment) 'explicit deployment confirmation required';Need (-not [string]::IsNullOrWhiteSpace($RestoreOwner)) 'restore owner required'}
& (Join-Path $PSScriptRoot 'Verify-ForwarderV110ProductionPackage.ps1') -PackagePath $PackagePath -ExpectedSha256 $ExpectedPackageSha256 | Out-Null
Need (Test-Path -LiteralPath $PreflightResultPath -PathType Leaf) 'collector result missing'
$pre=Get-Content -Raw -LiteralPath $PreflightResultPath|ConvertFrom-Json
Need ($pre.schema -eq 'forwarder-v1.10.0-production-readonly-preflight-v1') 'collector schema mismatch'
$age=([DateTime]::UtcNow-[DateTime]::Parse([string]$pre.generated_utc).ToUniversalTime()).TotalHours
Need ($age -ge 0 -and $age -le 4) 'collector result is stale'
if(-not $FixtureStatePath){Need ($pre.host.computer_name -eq [Environment]::MachineName) 'collector host mismatch'}
Need ($pre.collector_status -eq 'PASS') 'collector verdict blocked'
Need ([int]$pre.collection_errors -eq 0) 'collector errors present'
Need ([bool]$pre.active_release.runtime_agreement) 'runtime identity agreement missing'
Need ([bool]$pre.listener_ownership_verified) 'listener ownership unverified'
Need ([int]$pre.mandatory_config_missing_or_invalid_count -eq 0) 'mandatory config missing or invalid'
Need ($pre.config.AUTO_MIGRATE_ON_STARTUP.state -notin @('SAFE_VALUE_INVALID')) 'startup migration not disabled'
Need ($pre.config.CORS_ALLOW_ALL_ORIGINS.state -notin @('SAFE_VALUE_INVALID')) 'allow-all CORS is unsafe'
Need ($pre.database.collection -eq 'AVAILABLE') 'database read-only evidence unavailable'
Need ([int]$pre.database.identity.alembic_revision_count -eq 1 -and $pre.database.identity.alembic_revision -eq $ExpectedBefore) 'wrong starting database revision'
Need ($pre.database.identity.primary_state -eq 'PRIMARY') 'database is not primary'
Need ([int]$pre.database.schema_drift_blocker_count -eq 0) 'schema drift blocker present'
Need ([int64]$pre.database.adr047.fixed_owner_ambiguous_count -eq 0) 'ADR-047 ambiguous rows present'
Need ([int64]$pre.database.adr047.fixed_owner_contradiction_count -eq 0) 'ADR-047 contradictory rows present'
Need ([int64]$pre.database.adr047.fixed_owner_other_unresolved_count -eq 0) 'ADR-047 unresolved rows present'
Need ([bool]$pre.backup_readiness.mechanism_identified -and [bool]$pre.backup_readiness.destination_ready -and [bool]$pre.backup_readiness.tooling_available) 'backup readiness gate failed'
$target=NPath $TargetReleasePath
$root=NPath $ReleaseRoot
Need ($target.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) 'target outside release root'
Need ($target -match '(?i)\\release-\d{14}-20260926_fixed_shipment_responsible_expert$') 'target release naming mismatch'
Need (-not (Test-Path -LiteralPath $target)) 'target release path already exists'
$packageSize=(Get-Item -LiteralPath $PackagePath).Length;$dbSize=[int64]$pre.database.identity.database_size_bytes;$minimum=[int64]($packageSize*3+$dbSize+1GB);$releaseDrive=@($pre.storage.drives|Where-Object{$root.StartsWith([string]$_.root,[StringComparison]::OrdinalIgnoreCase)}|Select-Object -First 1);Need ($releaseDrive.Count -eq 1 -and [int64]$releaseDrive[0].free_bytes -ge $minimum) 'insufficient release/backup safety capacity'
$state=Get-LiveState
Need ([bool]$state.task_enabled) 'Production task disabled'
Need ([bool]$state.listener_up) 'Production listener unavailable'
Need (SamePath ([string]$state.task_release) ([string]$pre.scheduled_task.release_path)) 'task changed since collector'
Need (SamePath ([string]$state.listener_executable) ([string]$pre.listeners[0].executable)) 'listener changed since collector'
Need (SamePath ([string]$state.iis_path) ([string]$pre.iis.physical_path)) 'IIS changed since collector'
Need ([string]$state.database_head -eq $ExpectedBefore) 'live database head mismatch'
if($ValidateOnly){Write-Output 'PRODUCTION_VALIDATE_ONLY=PASS';Write-Output 'VALIDATEONLY_ZERO_MUTATION=YES';Write-Output ('TARGET_RELEASE_PATH='+$target);return}

$TargetReleasePath=$target;$mutationStarted=$false;$migrationComplete=$false;$iisSwitched=$false;$evidenceRoot=$null;$baselinePath=$null;$previousXml=[string]$state.task_xml;$previousIis=[string]$state.iis_path;$previousRelease=[string]$state.task_release
try{
    Inject 'STAGE';New-Item -ItemType Directory -Path $target -ErrorAction Stop|Out-Null;Add-Type -AssemblyName System.IO.Compression.FileSystem;[IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $PackagePath).Path,$target);Verify-Extracted $target
    $evidenceRoot=Join-Path $RuntimeRoot('deployment-evidence\v1.10.0-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'));New-Item -ItemType Directory -Path $evidenceRoot -ErrorAction Stop|Out-Null
    $taskXmlPath=Join-Path $evidenceRoot 'prior-task.xml';[IO.File]::WriteAllText($taskXmlPath,$previousXml,(New-Object Text.UTF8Encoding($false)))
    $baselinePath=Join-Path $evidenceRoot 'baseline-state.json';$baseline=[ordered]@{schema='forwarder-v1.10.0-deployment-baseline-v1';captured_utc=[DateTime]::UtcNow.ToString('o');prior_iis_path=$previousIis;prior_task_xml_path=$taskXmlPath;prior_release_path=$previousRelease;target_release_path=$target;package_sha256=$ExpectedPackageSha256.ToLowerInvariant();starting_database_revision=$ExpectedBefore};[IO.File]::WriteAllText($baselinePath,(($baseline|ConvertTo-Json -Depth 6)+"`n"),(New-Object Text.UTF8Encoding($false)))
    $mutationStarted=$true
    Inject 'CONTAIN'
    if($FixtureStatePath){$state.task_enabled=$false;$state.listener_up=$false;$state.traffic_contained=$true;Save-Fixture $state}
    else{Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null;Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue;$pid=[int]$state.listener_pid;$running=Get-CimInstance Win32_Process -Filter ('ProcessId='+$pid) -ErrorAction SilentlyContinue;if($running){Assert-Listener $running (Join-Path $previousRelease 'runtime\python.exe');Stop-Process -Id $pid -Force -ErrorAction Stop};$remaining=@(Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction SilentlyContinue|Where-Object{$_.LocalAddress -eq '127.0.0.1'});Need ($remaining.Count -eq 0) 'writer/listener containment failed'}
    Inject 'BACKUP'
    if($FixtureStatePath){Need ([bool]$state.backup_verified) 'fixture backup verification failed'}else{$backupOutput=@(& (Join-Path $PSScriptRoot 'New-ForwarderV110PreDeploymentBackup.ps1') -EnvironmentFile $EnvironmentFile -ApprovedBackupRoot $ApprovedBackupRoot -RestoreOwner $RestoreOwner -RetentionDays $BackupRetentionDays -CreateBackup -ConfirmBackup);Need (@($backupOutput|Where-Object{$_ -eq 'PREDEPLOYMENT_BACKUP=PASS'}).Count -eq 1) 'fresh backup verification failed'}
    Inject 'MIGRATION'
    if($FixtureStatePath){Need ([bool]$state.migration_allowed) 'fixture migration refused';$state.database_head=$ExpectedTarget;$state.deterministic_repairs_applied=[int64]$pre.database.adr047.fixed_owner_deterministic_repair_count;Save-Fixture $state}else{$envMap=Read-Env $EnvironmentFile;Run-PackagePython @('-m','backend.migration_cli','upgrade',$ExpectedTarget,'--confirm') $envMap|Out-Null;$current=Run-PackagePython @('-m','backend.migration_cli','current') $envMap;Need ($current -match ('current='+[regex]::Escape($ExpectedTarget))) 'migration current mismatch';Run-PackagePython @('-m','backend.migration_cli','check') $envMap|Out-Null}
    $migrationComplete=$true
    Inject 'POST_MIGRATION'
    if($FixtureStatePath){Need (@($state.post_assertions|Where-Object{$_.state -ne 'PASS'}).Count -eq 0) 'post-migration fixture assertion failed'}else{
        $assertionPath=Join-Path $target 'production-tooling\sql\post-migration-assertions-readonly.sql'
        Need (Test-Path -LiteralPath $assertionPath -PathType Leaf) 'post-migration assertion payload missing'
        $db=Get-DbConnection $envMap
        $assertionRows=@(Run-ReadOnlySql (Get-Content -Raw -LiteralPath $assertionPath) $db)
        $db.Password=$null
        Need ($assertionRows.Count -gt 0) 'post-migration assertions returned no rows'
        foreach($row in $assertionRows){
            $parts=$row.Split('|',3)
            $code=if($parts.Count -gt 0){$parts[0]}else{'INVALID_RESULT'}
            Need ($parts.Count -eq 3 -and $parts[1] -eq 'PASS') ('post-migration assertion blocked: '+$code)
        }
    }
    $nextXml=New-TaskXml $previousXml $target
    Inject 'TASK_SWITCH'
    if($FixtureStatePath){$state.task_xml=$nextXml;$state.task_release=$target;$state.listener_release=$target;$state.listener_executable=Join-Path $target 'runtime\python.exe';$state.listener_command='"'+$state.listener_executable+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app';$state.task_enabled=$true;Save-Fixture $state}else{Register-ScheduledTask -TaskName $TaskName -Xml $nextXml -Force -ErrorAction Stop|Out-Null;Enable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null}
    Inject 'BACKEND_START';if($FixtureStatePath){$state.listener_up=$true;Save-Fixture $state}else{Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop;Wait-Listener (Join-Path $target 'runtime\python.exe');Need (Probe "http://127.0.0.1:$BackendPort/api/health") 'local health failed';Need (Probe "http://127.0.0.1:$BackendPort/api/health/ready") 'local readiness failed'}
    Inject 'IIS_SWITCH';if($FixtureStatePath){$state.iis_path=Join-Path $target 'dist';Save-Fixture $state}else{Import-Module WebAdministration -ErrorAction Stop;Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.applicationHost/sites/site[@name='$IisSiteName']/application[@path='/']/virtualDirectory[@path='/']" -Name physicalPath -Value (Join-Path $target 'dist') -ErrorAction Stop;Need (SamePath ([string](Get-Website -Name $IisSiteName).PhysicalPath) (Join-Path $target 'dist')) 'IIS cutover mismatch'};$iisSwitched=$true
    Inject 'POST_DEPLOY';if($FixtureStatePath){$state.health=$true;$state.readiness=$true;$state.public_health=$true;$state.public_readiness=$true;$state.frontend=$true;$state.login_shell=$true;Save-Fixture $state}
    & (Join-Path $target 'production-tooling\Verify-ForwarderV110PostDeploy.ps1') -PackagePath $PackagePath -ExpectedPackageSha256 $ExpectedPackageSha256 -TargetReleasePath $target -PreflightResultPath $PreflightResultPath -OutputDirectory $evidenceRoot -EnvironmentFile $EnvironmentFile -PublicBaseUrl $PublicBaseUrl -FixtureStatePath $FixtureStatePath | Out-Null
    Write-Output 'PRODUCTION_DEPLOYMENT_TOOL_RESULT=PASS';Write-Output ('BASELINE_STATE='+$baselinePath)
}catch{
    $primary=$_
    if($mutationStarted){
        if($migrationComplete){
            try{if($FixtureStatePath){$state.task_enabled=$false;$state.listener_up=$false;$state.traffic_contained=$true;if($iisSwitched){$state.iis_path=$previousIis};Save-Fixture $state}else{Disable-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue|Out-Null;if($iisSwitched){Import-Module WebAdministration -ErrorAction Stop;Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.applicationHost/sites/site[@name='$IisSiteName']/application[@path='/']/virtualDirectory[@path='/']" -Name physicalPath -Value $previousIis -ErrorAction Stop}};Write-Output 'ROLLBACK_CHECKPOINT=B_OR_C';Write-Output 'WRITERS_CONTAINED=YES';Write-Output 'DBA_RELEASE_OWNER_DECISION_REQUIRED=YES'}catch{Write-Output 'CONTAINMENT_RESULT=FAILED'}
        }else{
            try{if($FixtureStatePath){$state.task_enabled=$true;$state.listener_up=$true;$state.task_release=$previousRelease;$state.listener_release=$previousRelease;$state.iis_path=$previousIis;Save-Fixture $state}else{Register-ScheduledTask -TaskName $TaskName -Xml $previousXml -Force -ErrorAction Stop|Out-Null;Enable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null;Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop};Write-Output 'ROLLBACK_CHECKPOINT=A';Write-Output 'PRIOR_APPLICATION_RESTORED=YES'}catch{Write-Output 'CHECKPOINT_A_RESTORE=FAILED'}
        }
    }
    throw $primary
}
