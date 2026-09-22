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
    [switch]$ToolingSelfTest,
    [string]$SelfTestPythonPath,
    [ValidateSet('','STAGE','CONTAIN','BACKUP','MIGRATION','POST_MIGRATION','TASK_SWITCH','BACKEND_START','IIS_SWITCH','POST_DEPLOY')][string]$FailAt=''
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ExpectedSource='e36ee7cee157657c97dc42a539eaf1909f510a33'
$ExpectedBefore='20260921_shipment_evidence_ownership'
$ExpectedTarget='20260926_fixed_shipment_responsible_expert'
$WriterContainmentTimeoutMilliseconds=15000
$WriterContainmentPollMilliseconds=250
$WriterContainmentQuietMilliseconds=2000
$script:ContainmentSelfTestTaskMode=$false
$script:ContainmentSelfTestTaskEnabled=$false
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
function Assert-Listener($Process,[string]$ExpectedPython){Need (-not [string]::IsNullOrWhiteSpace([string]$Process.ExecutablePath)) 'listener executable unavailable';Need (SamePath ([string]$Process.ExecutablePath) $ExpectedPython) 'listener executable mismatch';$line=[string]$Process.CommandLine;$listenPattern='(?i)--listen=127\.0\.0\.1:'+[regex]::Escape([string]$BackendPort)+'(?:\s|$)';Need ($line -match '(?i)-m\s+waitress' -and $line -match $listenPattern -and $line -match '(?i)backend\.wsgi:app') 'listener command mismatch'}
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
function Get-OptionalProperty([object]$Value,[string]$Name,[object]$Default){$property=$Value.PSObject.Properties[$Name];if($null-ne$property){return $property.Value};return $Default}
function Set-FixtureProperty([object]$State,[string]$Name,[object]$Value){$property=$State.PSObject.Properties[$Name];if($null-ne$property){$property.Value=$Value}else{$State|Add-Member -MemberType NoteProperty -Name $Name -Value $Value}}
function Disable-GovernedWriterTask([object]$State){
    if($FixtureStatePath){$State.task_enabled=$false;Save-Fixture $State;return}
    if($script:ContainmentSelfTestTaskMode){$script:ContainmentSelfTestTaskEnabled=$false;return}
    Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
}
function Stop-GovernedWriterTask([object]$State){
    if($FixtureStatePath){Set-FixtureProperty $State 'containment_task_stop_requested' $true;Save-Fixture $State;return}
    if($script:ContainmentSelfTestTaskMode){return}
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
}
function Get-GovernedWriterTaskEnabled([object]$State){
    if($FixtureStatePath){$checks=[int](Get-OptionalProperty $State 'containment_task_state_checks' 0);Set-FixtureProperty $State 'containment_task_state_checks' ($checks+1);Save-Fixture $State;return [bool]$State.task_enabled}
    if($script:ContainmentSelfTestTaskMode){return [bool]$script:ContainmentSelfTestTaskEnabled}
    $tasks=@(Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop)
    Need ($tasks.Count -eq 1) 'writer/listener containment failed: governed Scheduled Task missing or ambiguous'
    return [bool]$tasks[0].Settings.Enabled
}
function Get-GovernedListenerOwners([object]$State){
    if($FixtureStatePath){
        $poll=[int](Get-OptionalProperty $State 'containment_poll_count' 0)+1;Set-FixtureProperty $State 'containment_poll_count' $poll
        $behavior=[string](Get-OptionalProperty $State 'containment_behavior' 'immediate')
        $stopRequested=[bool](Get-OptionalProperty $State 'containment_process_stop_requested' $false)
        if(-not$stopRequested){Save-Fixture $State;return @([int]$State.listener_pid)}
        if($behavior -eq 'delayed_teardown'){
            $after=[int](Get-OptionalProperty $State 'containment_teardown_after_polls' 3)
            if($poll -lt $after){Save-Fixture $State;return @([int]$State.listener_pid)}
            $State.listener_up=$false;Save-Fixture $State;return @()
        }
        if($behavior -eq 'teardown_timeout'){Save-Fixture $State;return @([int]$State.listener_pid)}
        if($behavior -eq 'replacement_listener'){
            $replacement=[int](Get-OptionalProperty $State 'containment_replacement_pid' ([int]$State.listener_pid+1))
            Set-FixtureProperty $State 'containment_replacement_observed' $true;Save-Fixture $State;return @($replacement)
        }
        $State.listener_up=$false;Save-Fixture $State;return @()
    }
    try{$rows=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object{$_.LocalAddress -eq '127.0.0.1' -and [int]$_.LocalPort -eq $BackendPort})}catch{Stop-Release ('writer/listener containment failed: governed port inspection failed: '+$_.Exception.Message)}
    return @($rows|Select-Object -ExpandProperty OwningProcess -Unique|ForEach-Object{[int]$_})
}
function Get-GovernedWriterProcess([object]$State,[int]$ProcessId){
    if($FixtureStatePath){
        $behavior=[string](Get-OptionalProperty $State 'containment_behavior' 'immediate')
        $stopRequested=[bool](Get-OptionalProperty $State 'containment_process_stop_requested' $false)
        if($ProcessId -ne [int]$State.listener_pid -or -not[bool]$State.listener_up -or ($stopRequested -and $behavior -in @('immediate','replacement_listener'))){return $null}
        return [pscustomobject]@{ProcessId=$ProcessId;ExecutablePath=[string]$State.listener_executable;CommandLine=[string]$State.listener_command}
    }
    try{return Get-CimInstance Win32_Process -Filter ('ProcessId='+$ProcessId) -ErrorAction Stop}catch{Stop-Release ('writer/listener containment failed: listener process inspection failed: '+$_.Exception.Message)}
}
function Stop-GovernedWriterProcess([object]$State,[int]$ProcessId){
    if($FixtureStatePath){
        $stopped=@(Get-OptionalProperty $State 'containment_stopped_process_ids' @());Set-FixtureProperty $State 'containment_stopped_process_ids' @($stopped+$ProcessId);Set-FixtureProperty $State 'containment_process_stop_requested' $true
        if(([string](Get-OptionalProperty $State 'containment_behavior' 'immediate')) -eq 'immediate'){$State.listener_up=$false}
        Save-Fixture $State;return
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction Stop
}
function Wait-WriterContainmentPoll([object]$State,[int]$Milliseconds){if($FixtureStatePath){Start-Sleep -Milliseconds $Milliseconds}else{Start-Sleep -Milliseconds $Milliseconds}}
function Invoke-WriterContainment([object]$State,[string]$ExpectedPython){
    $listenerPid=[int]$State.listener_pid
    $timeoutMilliseconds=if($FixtureStatePath){[int](Get-OptionalProperty $State 'containment_timeout_milliseconds' 500)}else{$WriterContainmentTimeoutMilliseconds}
    $pollMilliseconds=if($FixtureStatePath){[int](Get-OptionalProperty $State 'containment_poll_milliseconds' 20)}else{$WriterContainmentPollMilliseconds}
    $quietMilliseconds=if($FixtureStatePath){[int](Get-OptionalProperty $State 'containment_quiet_milliseconds' 60)}else{$WriterContainmentQuietMilliseconds}
    Need ($timeoutMilliseconds -gt $quietMilliseconds -and $quietMilliseconds -ge $pollMilliseconds -and $pollMilliseconds -gt 0) 'writer/listener containment timing contract invalid'
    Disable-GovernedWriterTask $State
    Need (-not(Get-GovernedWriterTaskEnabled $State)) 'writer/listener containment failed: governed Scheduled Task did not disable'
    Stop-GovernedWriterTask $State
    $running=Get-GovernedWriterProcess $State $listenerPid
    if($running){Assert-Listener $running $ExpectedPython;Stop-GovernedWriterProcess $State $listenerPid}
    $deadline=[DateTime]::UtcNow.AddMilliseconds($timeoutMilliseconds)
    $quietSince=$null;$pollCount=0;$originalProcessGone=$false;$originalOwnsPort=$true;$taskDisabled=$false
    do{
        $pollCount++
        $taskDisabled=-not(Get-GovernedWriterTaskEnabled $State)
        Need $taskDisabled 'writer/listener containment failed: governed Scheduled Task became enabled during teardown'
        $owners=@(Get-GovernedListenerOwners $State)
        $replacementOwners=@($owners|Where-Object{$_ -ne $listenerPid})
        if($replacementOwners.Count -gt 0){Stop-Release ('writer/listener containment failed: replacement listener detected on 127.0.0.1:'+$BackendPort+'; original_pid='+$listenerPid+'; replacement_pid(s)='+($replacementOwners -join ',')+'; replacement_not_terminated=YES')}
        $originalOwnsPort=@($owners|Where-Object{$_ -eq $listenerPid}).Count -gt 0
        $originalProcessGone=$null -eq (Get-GovernedWriterProcess $State $listenerPid)
        $portFree=$owners.Count -eq 0
        if(($originalProcessGone -or -not$originalOwnsPort) -and $portFree){
            if($null-eq$quietSince){$quietSince=[DateTime]::UtcNow}
            if(([DateTime]::UtcNow-$quietSince).TotalMilliseconds -ge $quietMilliseconds){
                if($FixtureStatePath){$State.traffic_contained=$true;Set-FixtureProperty $State 'containment_task_disabled_proven' $true;Set-FixtureProperty $State 'containment_original_listener_terminated_proven' $true;Set-FixtureProperty $State 'containment_governed_port_free_proven' $true;Set-FixtureProperty $State 'containment_no_replacement_listener_proven' $true;Save-Fixture $State}
                return [pscustomobject]@{ConfirmedUtc=[DateTime]::UtcNow;TaskDisabled=$true;OriginalListenerTerminated=$true;OriginalProcessGone=$originalProcessGone;OriginalPortReleased=(-not$originalOwnsPort);GovernedPortFree=$true;NoReplacementListener=$true;PollCount=$pollCount;TimeoutMilliseconds=$timeoutMilliseconds;PollMilliseconds=$pollMilliseconds;QuietMilliseconds=$quietMilliseconds}
            }
        }else{$quietSince=$null}
        if([DateTime]::UtcNow -ge $deadline){break}
        Wait-WriterContainmentPoll $State $pollMilliseconds
    }while($true)
    $lastOwners=@(Get-GovernedListenerOwners $State)
    Stop-Release ('writer/listener containment failed: teardown timeout after '+$timeoutMilliseconds+'ms; task_disabled='+$taskDisabled+'; original_process_gone='+$originalProcessGone+'; original_owns_port='+$originalOwnsPort+'; owner_pid(s)='+$(if($lastOwners.Count){$lastOwners -join ','}else{'none'}))
}
function Invoke-NativeWriterContainmentSelfTest([string]$PythonPath){
    if([string]::IsNullOrWhiteSpace($PythonPath)){$command=Get-Command python -ErrorAction Stop;$PythonPath=[string]$command.Source}
    $PythonPath=NPath $PythonPath;Need (Test-Path -LiteralPath $PythonPath -PathType Leaf) 'self-test Python unavailable'
    $reservation=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0);$reservation.Start();$testPort=[int]$reservation.LocalEndpoint.Port;$reservation.Stop()
    $oldPort=$BackendPort;$launcher=$null;$listenerPid=0
    try{
        $BackendPort=$testPort
        $code="import socket,time;s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',$testPort));s.listen(1);time.sleep(60)"
        $arguments='/d /c start "" /b "'+$PythonPath+'" -c "'+$code+'" -m waitress --listen=127.0.0.1:'+$testPort+' backend.wsgi:app'
        $start=New-Object Diagnostics.ProcessStartInfo;$start.FileName=(Join-Path $env:SystemRoot 'System32\cmd.exe');$start.Arguments=$arguments;$start.UseShellExecute=$false;$start.CreateNoWindow=$true
        $launcher=New-Object Diagnostics.Process;$launcher.StartInfo=$start;Need ($launcher.Start()) 'native containment self-test launcher did not start';Need ($launcher.WaitForExit(5000)) 'native containment self-test launcher timeout';Need ($launcher.ExitCode -eq 0) 'native containment self-test launcher failed'
        $deadline=[DateTime]::UtcNow.AddSeconds(10)
        do{$owners=@(Get-GovernedListenerOwners ([pscustomobject]@{}));if($owners.Count -eq 1){$listenerPid=[int]$owners[0];break};Start-Sleep -Milliseconds 50}while([DateTime]::UtcNow -lt $deadline)
        Need ($listenerPid -gt 0) 'native containment self-test listener did not start'
        $listener=Get-GovernedWriterProcess ([pscustomobject]@{}) $listenerPid;Assert-Listener $listener $PythonPath
        $parent=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$listener.ParentProcessId) -ErrorAction SilentlyContinue
        Need ($null-eq$parent) 'native containment self-test listener parent still exists'
        $script:ContainmentSelfTestTaskMode=$true;$script:ContainmentSelfTestTaskEnabled=$true
        $result=Invoke-WriterContainment ([pscustomobject]@{listener_pid=$listenerPid}) $PythonPath
        Need ($result.TaskDisabled -and $result.OriginalListenerTerminated -and $result.GovernedPortFree -and $result.NoReplacementListener) 'native containment self-test contract failed'
        Write-Output 'NATIVE_ORPHAN_LISTENER_PARENT_ABSENT=PASS'
        Write-Output 'NATIVE_EXACT_PID_SOCKET_TEARDOWN=PASS'
    }finally{
        $script:ContainmentSelfTestTaskMode=$false;$script:ContainmentSelfTestTaskEnabled=$false;$BackendPort=$oldPort
        if($listenerPid -gt 0){$remaining=Get-CimInstance Win32_Process -Filter ('ProcessId='+$listenerPid) -ErrorAction SilentlyContinue;if($remaining -and (SamePath ([string]$remaining.ExecutablePath) $PythonPath)){Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue}}
        if($launcher){$launcher.Dispose()}
    }
}
function Is-TrueBoolean([object]$Value){return($Value -is [bool] -and $Value -eq $true)}
function Is-FalseBoolean([object]$Value){return($Value -is [bool] -and $Value -eq $false)}
function Write-JsonEvidence([string]$Path,[object]$Value){[IO.File]::WriteAllText($Path,(($Value|ConvertTo-Json -Depth 10)+"`n"),(New-Object Text.UTF8Encoding($false)))}
function Get-DeploymentWindowBackupEvidence([string[]]$Output,[DateTime]$ContainedUtc){
    $evidenceLines=@($Output|Where-Object{$_ -like 'BACKUP_EVIDENCE=*'})
    $hashLines=@($Output|Where-Object{$_ -like 'BACKUP_SHA256=*'})
    Need ($evidenceLines.Count -eq 1 -and $hashLines.Count -eq 1) 'deployment-window backup output identity missing or ambiguous'
    $evidencePath=NPath $evidenceLines[0].Substring('BACKUP_EVIDENCE='.Length)
    $reportedHash=$hashLines[0].Substring('BACKUP_SHA256='.Length).ToLowerInvariant()
    $backupRoot=NPath $ApprovedBackupRoot
    Need ($evidencePath.StartsWith($backupRoot+'\',[StringComparison]::OrdinalIgnoreCase)) 'deployment-window backup evidence outside approved root'
    Need (Test-Path -LiteralPath $evidencePath -PathType Leaf) 'deployment-window backup evidence missing'
    $record=Get-Content -Raw -LiteralPath $evidencePath|ConvertFrom-Json
    $created=[DateTime]::Parse([string]$record.created_utc).ToUniversalTime()
    $dump=NPath ([string]$record.backup_path)
    $catalog=NPath ([string]$record.catalog_path)
    $hashSidecar=NPath ([string]$record.sha256_sidecar_path)
    Need ($record.schema -eq 'forwarder-v1.10.0-predeployment-backup-evidence-v2' -and $record.status -eq 'PASS' -and (Is-TrueBoolean $record.verified)) 'deployment-window backup evidence invalid'
    Need ($record.purpose -eq 'fresh_predeployment_backup_and_isolated_restore_input' -and $record.product_version -eq '1.10.0') 'deployment-window backup purpose mismatch'
    Need ($record.current_application_commit -eq 'e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4' -and $record.target_application_commit -eq $ExpectedSource) 'deployment-window backup application identity mismatch'
    Need ($record.database_revision -eq $ExpectedBefore -and [int]$record.alembic_revision_count -eq 1 -and $record.database_state -eq 'PRIMARY' -and [string]$record.postgresql_version -match '^18(?:\.|$)' -and [int64]$record.database_size_bytes -gt 0) 'deployment-window backup database identity mismatch'
    Need ($created -ge $ContainedUtc -and $created -le [DateTime]::UtcNow) 'deployment-window backup was not created after writer containment'
    Need ($dump.StartsWith($backupRoot+'\',[StringComparison]::OrdinalIgnoreCase) -and $catalog.StartsWith($backupRoot+'\',[StringComparison]::OrdinalIgnoreCase) -and $hashSidecar.StartsWith($backupRoot+'\',[StringComparison]::OrdinalIgnoreCase)) 'deployment-window backup artifacts outside approved root'
    Need (Test-Path -LiteralPath $dump -PathType Leaf) 'deployment-window dump missing'
    Need (Test-Path -LiteralPath $catalog -PathType Leaf) 'deployment-window catalog missing'
    Need (Test-Path -LiteralPath $hashSidecar -PathType Leaf) 'deployment-window hash sidecar missing'
    $actualDump=Get-Item -LiteralPath $dump
    $actualHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $dump).Hash.ToLowerInvariant()
    Need ($actualDump.Length -gt 0 -and $actualDump.Length -eq [int64]$record.dump_size_bytes) 'deployment-window dump size mismatch'
    Need ($actualHash -eq ([string]$record.dump_sha256).ToLowerInvariant() -and $actualHash -eq $reportedHash) 'deployment-window dump hash mismatch'
    Need ((Get-Item -LiteralPath $catalog).Length -gt 0 -and $record.catalog_verification -eq 'PASS' -and [int]$record.pg_dump_exit_code -eq 0 -and [int]$record.pg_restore_list_exit_code -eq 0) 'deployment-window backup catalog verification failed'
    Need ((Get-Content -Raw -LiteralPath $hashSidecar).Trim() -ceq ($actualHash+'  '+[IO.Path]::GetFileName($dump))) 'deployment-window hash sidecar mismatch'
    Need ($record.restore_owner -eq $RestoreOwner -and [int]$record.retention_days -eq $BackupRetentionDays) 'deployment-window backup ownership or retention mismatch'
    Need ((Is-FalseBoolean $record.production_database_mutated) -and (Is-FalseBoolean $record.production_deployment_performed) -and (Is-FalseBoolean $record.secret_values_emitted) -and $record.reference_impact -eq 'NONE') 'deployment-window backup mutation declaration invalid'
    return [pscustomobject]@{EvidencePath=$evidencePath;DumpPath=$dump;DumpSha256=$actualHash;DumpSizeBytes=[int64]$actualDump.Length;CreatedUtc=$created}
}
function Read-Env([string]$Path){$m=@{};Need (Test-Path -LiteralPath $Path -PathType Leaf) 'environment file unavailable';foreach($line in Get-Content -LiteralPath $Path){if($line.Trim() -and -not $line.TrimStart().StartsWith('#') -and $line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$'){$m[$Matches[1]]=$Matches[2].Trim().Trim('"').Trim("'")}};return $m}
function Get-DbConnection([hashtable]$Map){
    Need ($Map.ContainsKey('DATABASE_URL')) 'DATABASE_URL unavailable'
    $raw=[string]$Map['DATABASE_URL']
    $scheme=[regex]::Match($raw,'(?i)^(postgres|postgresql|postgresql\+psycopg2)://')
    Need $scheme.Success 'database scheme mismatch'
    $uri=[Uri]('postgresql://'+$raw.Substring($scheme.Length))
    $userInfo=$uri.UserInfo.Split(':',2)
    $database=[Uri]::UnescapeDataString($uri.AbsolutePath.Trim('/'))
    $user=[Uri]::UnescapeDataString($userInfo[0])
    Need ($uri.Host -match '^[A-Za-z0-9_.:-]+$' -and $database -match '^[A-Za-z0-9_.-]+$' -and $user -match '^[A-Za-z0-9_.-]+$') 'database identity unsafe'
    $sslMatch=[regex]::Match($uri.Query,'(?i)(?:^|[?&])sslmode=([^&]*)')
    $sslMode=if($sslMatch.Success){[Uri]::UnescapeDataString($sslMatch.Groups[1].Value)}else{''}
    Need (-not $sslMode -or $sslMode -match '^[A-Za-z0-9_-]+$') 'database sslmode invalid'
    return [pscustomobject]@{Host=$uri.Host;Port=$(if($uri.Port-gt0){$uri.Port}else{5432});Database=$database;User=$user;Password=$(if($userInfo.Count-eq2){[Uri]::UnescapeDataString($userInfo[1])}else{''});SslMode=$sslMode}
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
    if($Db.SslMode){$s.EnvironmentVariables['PGSSLMODE']=$Db.SslMode}
    $p=New-Object Diagnostics.Process;$p.StartInfo=$s
    try{
        Need ($p.Start()) 'psql did not start'
        $p.StandardInput.Write($Sql);$p.StandardInput.Close()
        $stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
        Need ($p.WaitForExit(120000)) 'psql timeout'
        Need ($p.ExitCode -eq 0) 'psql read-only assertion failed'
        return @(([string]$stdout.Result)-split "`r?`n" | Where-Object {$_ -match '\S'})
    } finally { if($s.EnvironmentVariables.ContainsKey('PGPASSWORD')){$s.EnvironmentVariables.Remove('PGPASSWORD')};if($s.EnvironmentVariables.ContainsKey('PGSSLMODE')){$s.EnvironmentVariables.Remove('PGSSLMODE')};$p.Dispose() }
}
function Run-PackagePython([string[]]$Arguments,[hashtable]$Environment){$s=New-Object Diagnostics.ProcessStartInfo;$s.FileName=Join-Path $TargetReleasePath 'runtime\python.exe';$s.Arguments=($Arguments|ForEach-Object{'"'+$_.Replace('"','\"')+'"'})-join ' ';$s.WorkingDirectory=$TargetReleasePath;$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true;foreach($key in $Environment.Keys){$s.EnvironmentVariables[$key]=[string]$Environment[$key]};$s.EnvironmentVariables['AUTO_MIGRATE_ON_STARTUP']='false';$s.EnvironmentVariables['RELEASE_IDENTITY_PATH']=Join-Path $TargetReleasePath 'release-manifest.json';$p=New-Object Diagnostics.Process;$p.StartInfo=$s;try{Need ($p.Start()) 'package Python did not start';$o=$p.StandardOutput.ReadToEndAsync();$e=$p.StandardError.ReadToEndAsync();Need ($p.WaitForExit(600000)) 'package Python timeout';Need ($p.ExitCode -eq 0) 'package Python command failed';return [string]$o.Result}finally{$p.Dispose()}}
function Verify-Extracted([string]$Root){$expected=@{};foreach($line in Get-Content -LiteralPath (Join-Path $Root 'SHA256SUMS.txt')){$parts=$line -split '  ',2;Need ($parts.Count -eq 2) 'malformed internal checksum';$expected[$parts[1]]=$parts[0];$path=Join-Path $Root $parts[1];Need (Test-Path -LiteralPath $path -PathType Leaf) 'extracted file missing';Need ((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -eq $parts[0]) 'extracted checksum mismatch'};$actual=@(Get-ChildItem -LiteralPath $Root -Recurse -File|ForEach-Object{$_.FullName.Substring($Root.TrimEnd('\').Length+1).Replace('\','/')}|Where-Object{$_ -ne 'SHA256SUMS.txt'});Need (@($actual|Where-Object{-not $expected.ContainsKey($_)}).Count -eq 0) 'unexpected extracted file'}
function Wait-Listener([string]$ExpectedPython){$deadline=[DateTime]::UtcNow.AddSeconds(60);do{$rows=@(Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction SilentlyContinue|Where-Object{$_.LocalAddress -eq '127.0.0.1'});$owners=@($rows|Select-Object -ExpandProperty OwningProcess -Unique);Need ($owners.Count -le 1) 'listener ambiguous';if($owners.Count -eq 1){$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop;Assert-Listener $p $ExpectedPython;return};Start-Sleep -Milliseconds 500}while([DateTime]::UtcNow -lt $deadline);Stop-Release 'listener timeout'}
function Probe([string]$Uri){try{$r=Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 10 -ErrorAction Stop;return($r.StatusCode-eq200)}catch{return$false}}

if($ToolingSelfTest){$test=Get-DbConnection @{DATABASE_URL='postgresql+psycopg2://forwarder_user:test-only-p%40ss%3Aword@127.0.0.1:5432/forwarder?sslmode=require'};Need ($test.Host -eq '127.0.0.1' -and $test.Port -eq 5432 -and $test.Database -eq 'forwarder' -and $test.User -eq 'forwarder_user' -and $test.Password -eq 'test-only-p@ss:word' -and $test.SslMode -eq 'require') 'deployer database URL self-test failed';$test.Password=$null;Invoke-NativeWriterContainmentSelfTest $SelfTestPythonPath;Write-Output 'DEPLOYER_SQLALCHEMY_DATABASE_URL=SUPPORTED';Write-Output 'PRODUCTION_MUTATION_PERFORMED=NO';exit 0}

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
Need ($pre.deployment_prerequisite_status -eq 'READY_FOR_SEPARATE_GO_REVIEW') 'pre-Execute release gate is not ready for separate GO review'
Need ($pre.backup_readiness.deployment_prerequisite_status -eq 'READY_FOR_SEPARATE_GO_REVIEW') 'backup release gate projection mismatch'
Need ((Is-TrueBoolean $pre.backup_readiness.pre_execute_backup_restore_proof_required) -and (Is-TrueBoolean $pre.backup_readiness.pre_execute_backup_restore_proof_ready) -and $pre.backup_readiness.pre_execute_backup_restore_proof_status -eq 'PASS') 'exact pre-Execute backup and restore proof missing'
Need ((Is-TrueBoolean $pre.backup_readiness.backup_evidence_available) -and $pre.backup_readiness.backup_evidence.state -eq 'VERIFIED_EXACT_DUMP') 'pre-Execute backup evidence identity is not exact-dump verified'
Need ((Is-TrueBoolean $pre.backup_readiness.restore_evidence_available) -and $pre.backup_readiness.restore_evidence.state -eq 'VERIFIED_EXACT_DUMP') 'restore proof identity is not exact-dump verified'
Need ($pre.backup_readiness.latest_dump.dump_sha256 -match '^[0-9a-f]{64}$' -and $pre.backup_readiness.backup_evidence.dump_sha256 -eq $pre.backup_readiness.latest_dump.dump_sha256 -and $pre.backup_readiness.restore_evidence.source_dump_sha256 -eq $pre.backup_readiness.latest_dump.dump_sha256) 'restore proof dump identity mismatch'
$preExecuteBackupCreatedUtc=[DateTime]::Parse([string]$pre.backup_readiness.backup_evidence.created_utc).ToUniversalTime();$preExecuteRestoreTestedUtc=[DateTime]::Parse([string]$pre.backup_readiness.restore_evidence.tested_utc).ToUniversalTime();Need ($preExecuteRestoreTestedUtc -ge $preExecuteBackupCreatedUtc -and $preExecuteRestoreTestedUtc -le [DateTime]::Parse([string]$pre.generated_utc).ToUniversalTime()) 'pre-Execute backup/restore proof chronology invalid'
Need ((Is-FalseBoolean $pre.backup_readiness.fresh_deployment_window_backup_present) -and (Is-TrueBoolean $pre.backup_readiness.fresh_deployment_window_backup_required)) 'deployment-window backup projection invalid'
Need ($pre.backup_readiness.deployment_window_backup_timing -eq 'AFTER_WRITER_CONTAINMENT_BEFORE_MIGRATION' -and $pre.backup_readiness.deployment_window_backup_verification -eq 'HASH_SIZE_CATALOG_AND_BASELINE_IDENTITY') 'deployment-window backup contract mismatch'
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
if($ValidateOnly){Write-Output 'PRE_EXECUTE_BACKUP_RESTORE_PROOF=PASS';Write-Output 'DEPLOYMENT_WINDOW_BACKUP=REQUIRED_DURING_EXECUTE_AFTER_WRITER_CONTAINMENT';Write-Output 'PRODUCTION_VALIDATE_ONLY=PASS';Write-Output 'VALIDATEONLY_ZERO_MUTATION=YES';Write-Output ('TARGET_RELEASE_PATH='+$target);return}

$TargetReleasePath=$target;$mutationStarted=$false;$migrationComplete=$false;$iisSwitched=$false;$evidenceRoot=$null;$baselinePath=$null;$writerContainmentUtc=$null;$deploymentWindowBackup=$null;$previousXml=[string]$state.task_xml;$previousIis=[string]$state.iis_path;$previousRelease=[string]$state.task_release
try{
    Inject 'STAGE';New-Item -ItemType Directory -Path $target -ErrorAction Stop|Out-Null;Add-Type -AssemblyName System.IO.Compression.FileSystem;[IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $PackagePath).Path,$target);Verify-Extracted $target
    $evidenceRoot=Join-Path $RuntimeRoot('deployment-evidence\v1.10.0-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'));New-Item -ItemType Directory -Path $evidenceRoot -ErrorAction Stop|Out-Null
    $taskXmlPath=Join-Path $evidenceRoot 'prior-task.xml';[IO.File]::WriteAllText($taskXmlPath,$previousXml,(New-Object Text.UTF8Encoding($false)))
    $baselinePath=Join-Path $evidenceRoot 'baseline-state.json';$baseline=[ordered]@{schema='forwarder-v1.10.0-deployment-baseline-v2';captured_utc=[DateTime]::UtcNow.ToString('o');prior_iis_path=$previousIis;prior_task_xml_path=$taskXmlPath;prior_release_path=$previousRelease;target_release_path=$target;package_sha256=$ExpectedPackageSha256.ToLowerInvariant();starting_database_revision=$ExpectedBefore;pre_execute_backup_restore_proof_status='PASS';pre_execute_restore_proven_dump_sha256=[string]$pre.backup_readiness.latest_dump.dump_sha256;pre_execute_restore_tested_utc=[string]$pre.backup_readiness.restore_evidence.tested_utc;writer_containment_confirmed_utc=$null;writer_containment_task_disabled=$null;writer_containment_original_listener_terminated=$null;writer_containment_original_process_gone=$null;writer_containment_original_port_released=$null;writer_containment_governed_port_free=$null;writer_containment_no_replacement_listener=$null;writer_containment_poll_count=$null;writer_containment_timeout_milliseconds=$WriterContainmentTimeoutMilliseconds;writer_containment_poll_milliseconds=$WriterContainmentPollMilliseconds;writer_containment_quiet_milliseconds=$WriterContainmentQuietMilliseconds;deployment_window_backup_status='PENDING';deployment_window_backup_evidence_path=$null;deployment_window_backup_dump_path=$null;deployment_window_backup_dump_sha256=$null;deployment_window_backup_dump_size_bytes=$null;deployment_window_backup_created_utc=$null};Write-JsonEvidence $baselinePath $baseline
    $mutationStarted=$true
    Inject 'CONTAIN'
    $writerContainment=Invoke-WriterContainment $state (Join-Path $previousRelease 'runtime\python.exe')
    $writerContainmentUtc=$writerContainment.ConfirmedUtc
    $baseline.writer_containment_confirmed_utc=$writerContainmentUtc.ToString('o');$baseline.writer_containment_task_disabled=$writerContainment.TaskDisabled;$baseline.writer_containment_original_listener_terminated=$writerContainment.OriginalListenerTerminated;$baseline.writer_containment_original_process_gone=$writerContainment.OriginalProcessGone;$baseline.writer_containment_original_port_released=$writerContainment.OriginalPortReleased;$baseline.writer_containment_governed_port_free=$writerContainment.GovernedPortFree;$baseline.writer_containment_no_replacement_listener=$writerContainment.NoReplacementListener;$baseline.writer_containment_poll_count=$writerContainment.PollCount;$baseline.writer_containment_timeout_milliseconds=$writerContainment.TimeoutMilliseconds;$baseline.writer_containment_poll_milliseconds=$writerContainment.PollMilliseconds;$baseline.writer_containment_quiet_milliseconds=$writerContainment.QuietMilliseconds;Write-JsonEvidence $baselinePath $baseline
    Write-Output 'TASK_DISABLED=PASS';Write-Output 'ORIGINAL_LISTENER_TERMINATED=PASS';Write-Output 'GOVERNED_PORT_FREE=PASS';Write-Output 'NO_REPLACEMENT_LISTENER=PASS';Write-Output 'WRITER_CONTAINMENT=PASS'
    Inject 'BACKUP'
    if($FixtureStatePath){
        Need (Is-TrueBoolean $state.backup_verified) 'fixture backup verification failed'
        $fixtureCreated=[DateTime]::UtcNow
        $deploymentWindowBackup=[pscustomobject]@{EvidencePath=(Join-Path $ApprovedBackupRoot ('Forwarder-v1.10.0-PreDeploymentBackup-'+$fixtureCreated.ToString('yyyyMMddTHHmmssZ')+'.json'));DumpPath=(Join-Path $ApprovedBackupRoot ('forwarder-v1.10.0-predeploy-'+$fixtureCreated.ToString('yyyyMMddTHHmmssZ')+'.dump'));DumpSha256=('b'*64);DumpSizeBytes=2048L;CreatedUtc=$fixtureCreated}
    }else{
        $backupOutput=@(& (Join-Path $PSScriptRoot 'New-ForwarderV110PreDeploymentBackup.ps1') -EnvironmentFile $EnvironmentFile -ApprovedBackupRoot $ApprovedBackupRoot -RestoreOwner $RestoreOwner -RetentionDays $BackupRetentionDays -CreateBackup -ConfirmBackup)
        Need (@($backupOutput|Where-Object{$_ -eq 'PREDEPLOYMENT_BACKUP=PASS'}).Count -eq 1) 'fresh backup verification failed'
        $deploymentWindowBackup=Get-DeploymentWindowBackupEvidence $backupOutput $writerContainmentUtc
    }
    Need ($deploymentWindowBackup.CreatedUtc -ge $writerContainmentUtc -and $deploymentWindowBackup.CreatedUtc -gt $preExecuteBackupCreatedUtc) 'deployment-window backup timing invalid'
    $baseline.deployment_window_backup_status='PASS';$baseline.deployment_window_backup_evidence_path=$deploymentWindowBackup.EvidencePath;$baseline.deployment_window_backup_dump_path=$deploymentWindowBackup.DumpPath;$baseline.deployment_window_backup_dump_sha256=$deploymentWindowBackup.DumpSha256;$baseline.deployment_window_backup_dump_size_bytes=$deploymentWindowBackup.DumpSizeBytes;$baseline.deployment_window_backup_created_utc=$deploymentWindowBackup.CreatedUtc.ToString('o');Write-JsonEvidence $baselinePath $baseline
    Write-Output 'DEPLOYMENT_WINDOW_BACKUP=PASS';Write-Output ('DEPLOYMENT_WINDOW_BACKUP_SHA256='+$deploymentWindowBackup.DumpSha256)
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
