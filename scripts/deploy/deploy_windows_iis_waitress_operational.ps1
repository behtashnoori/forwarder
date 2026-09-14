#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[switch]$ValidateOnly,[switch]$Execute,[switch]$ConfirmDeployment,[string]$FixtureStatePath,[string]$EnvironmentFile='C:\1-webapp\forwarder-runtime\production.env',[string]$ReleaseRoot='C:\1-webapp\forwarder-production',[ValidateSet('','PACKAGE_VERIFY','BASELINE_CAPTURE','DB_GATE','MIGRATION','TARGET_MATERIALIZE','TASK_DISABLE','BACKEND_STOP','PORT_RELEASE','TASK_SWITCH','BACKEND_START','LISTENER_VERIFY','INTERNAL_HEALTH','IIS_SWITCH','IIS_VERIFY','PUBLIC_HEALTH','POST_DEPLOY_VERIFY')][string]$FailAt='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$RequiredBefore='20260920_legal_customer_nullable_contact_names';$RequiredTarget='20260921_shipment_evidence_ownership'
$Timeouts=@{DB_GATE=30;MIGRATION=180;BACKEND_STOP=30;PORT_RELEASE=30;TASK_UPDATE=30;BACKEND_START=45;LISTENER_VERIFY=45;IIS_SWITCH=30;IIS_VERIFY=30;INTERNAL_HEALTH=30;PUBLIC_HEALTH=45;ROLLBACK_RECOVERY=60}
function Need([bool]$Ok,[string]$Message){if(-not $Ok){throw "RELEASE_STOP: $Message"}}
function Import-ReleaseEnvironment {if(-not $env:DATABASE_URL){Need (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf) 'production environment file unavailable';foreach($line in Get-Content -LiteralPath $EnvironmentFile){if($line -match '^DATABASE_URL=(.+)$'){$env:DATABASE_URL=$Matches[1].Trim().Trim('"').Trim("'");break}}};Need (-not [string]::IsNullOrWhiteSpace($env:DATABASE_URL)) 'DATABASE_URL unavailable'}
function NPath([string]$Value){Need (-not [string]::IsNullOrWhiteSpace($Value)) 'empty path';$normalized=($Value.Trim().Trim('"').Trim("'") -replace '/','\');return [IO.Path]::GetFullPath($normalized).TrimEnd('\')}
function SamePath([string]$A,[string]$B){return [string]::Equals((NPath $A),(NPath $B),[StringComparison]::OrdinalIgnoreCase)}
function Split-LaunchArguments([string]$Text){
    # A single Windows command with quoted path tokens, never a shell program.
    Need ($Text -notmatch '[&|<>^%!\r\n]') 'unsupported shell syntax in launcher arguments'
    $values=New-Object 'System.Collections.Generic.List[string]'
    $rest=$Text.Trim()
    while($rest.Length){
        $part=[regex]::Match($rest,'^(?:"([^"]+)"|([^\s"]+))(?:\s+|$)')
        Need $part.Success 'invalid launcher argument quoting'
        $value=if($part.Groups[1].Success){$part.Groups[1].Value}else{$part.Groups[2].Value}
        $values.Add($value);$rest=$rest.Substring($part.Length)
    }
    return $values.ToArray()
}
function Decode-CmdPayload([string]$Text){
    Need ($Text.Length -ge 2 -and $Text[0] -ceq '"' -and $Text[$Text.Length-1] -ceq '"') 'quoted cmd.exe /c payload required'
    $inner=$Text.Substring(1,$Text.Length-2)
    Need ($inner -notmatch '(?<!")"(?!")|(?<!")"""|"""(?!")') 'malformed doubled cmd.exe quotes'
    Need ($inner -notmatch '"{3,}') 'malformed doubled cmd.exe quotes'
    return $inner.Replace('""','"')
}
function Get-TaskLaunch([string]$Xml){
    [xml]$doc=$Xml
    $actions=@($doc.SelectNodes("/*[local-name()='Task']/*[local-name()='Actions']/*"))
    Need ($actions.Count -eq 1 -and $actions[0].LocalName -eq 'Exec') 'one task action required'
    $action=$actions[0]
    Need (SamePath ([string]$action.Command) 'C:\Windows\System32\cmd.exe') 'system cmd.exe required'
    $arguments=[string]$action.Arguments
    Need ($arguments -match '(?i)^\s*/d\s+/c\s+(.+)$') 'cmd.exe /d /c required'
    $body=Decode-CmdPayload $Matches[1].Trim()
    # Parse the only approved shell program before tokenizing its final command.
    # In particular, Split-LaunchArguments must never receive a cmd.exe body.
    Need ($body -notmatch '[|<>^%!\r\n]' -and $body -notmatch '&&.*&&.*&&') 'unsupported shell syntax in launcher arguments'
    $wrapper=[regex]::Match($body,'(?is)^set\s+PYTHONPATH=(.+?)\s*&&\s*cd\s+/d\s+"([^"]+)"\s*&&\s*(.+)$')
    Need $wrapper.Success 'approved task launcher wrapper required'
    $pythonPath=$wrapper.Groups[1].Value.Trim()
    $cdPath=$wrapper.Groups[2].Value
    $invocation=$wrapper.Groups[3].Value.Trim()
    Need ($pythonPath -notmatch '[&|<>^%!"\r\n]' -and $cdPath -notmatch '[&|<>^%!\r\n]') 'unsupported shell syntax in launcher arguments'
    $tokens=@(Split-LaunchArguments $invocation)
    Need ($tokens.Count -ge 3) 'runtime launcher invocation required'
    Need (SamePath $tokens[1] 'C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py') 'approved runtime launcher required'
    Need ($tokens[2] -ceq 'serve') 'runtime launcher serve command required'
    $options=@{};$repoIndex=-1
    for($index=3;$index -lt $tokens.Count;$index+=2){
        $key=$tokens[$index]
        Need ($key -cin @('--repo','--env','--host','--port','--log') -and $index+1 -lt $tokens.Count) 'unsupported runtime launcher option'
        Need (-not $options.ContainsKey($key)) 'duplicate runtime launcher option'
        $options[$key]=$tokens[$index+1]
        if($key -ceq '--repo'){$repoIndex=$index+1}
    }
    Need ($options.ContainsKey('--repo')) 'launcher --repo required'
    $release=NPath $options['--repo'];$runtime=NPath $tokens[0]
    Need (SamePath $pythonPath $release) 'PYTHONPATH/--repo mismatch'
    Need (SamePath $cdPath $release) 'cd/--repo mismatch'
    Need (SamePath $runtime (Join-Path $release 'runtime\python.exe')) 'runtime/--repo mismatch'
    Need (SamePath ([string]$action.WorkingDirectory) $release) 'runtime/WorkingDirectory mismatch'
    Need ($options.ContainsKey('--env')) 'launcher --env required'
    Need ($options.ContainsKey('--host') -and $options['--host'] -ceq '127.0.0.1' -and $options.ContainsKey('--port') -and $options['--port'] -ceq '5101') 'launcher endpoint must be 127.0.0.1:5101'
    return [pscustomobject]@{Document=$doc;Action=$action;Tokens=$tokens;RepoIndex=$repoIndex;Runtime=$runtime;Release=$release;PythonPath=$pythonPath;CdPath=$cdPath}
}
function TaskRuntime([string]$Xml){return (Get-TaskLaunch $Xml).Runtime}
function New-TaskLaunchXml([string]$Xml,[string]$Release){
    $launch=Get-TaskLaunch $Xml
    $launch.Tokens[0]=Join-Path $Release 'runtime\python.exe'
    $launch.Tokens[$launch.RepoIndex]=$Release
    $invocation=(($launch.Tokens|ForEach-Object {'"'+$_+'"'}) -join ' ')
    $body='set PYTHONPATH='+$Release+'&& cd /d "'+$Release+'"&& '+$invocation
    $launch.Action.Arguments='/d /c "'+$body.Replace('"','""')+'"'
    $launch.Action.WorkingDirectory=$Release
    $result=$launch.Document.OuterXml
    Need (SamePath (TaskRuntime $result) (Join-Path $Release 'runtime\python.exe')) 'target task/runtime mismatch'
    return $result
}
function Assert-ListenerProcess($Process,[string]$Expected){
    Need (-not [string]::IsNullOrWhiteSpace([string]$Process.ExecutablePath)) 'listener executable path unavailable'
    Need (SamePath ([string]$Process.ExecutablePath) $Expected) 'orphan/mismatched listener: executable differs from task-configured runtime'
    $valid=$false
    try{
        $tokens=@(Split-LaunchArguments ([string]$Process.CommandLine))
        $valid=$tokens.Count -eq 5 -and (SamePath $tokens[0] $Expected) -and $tokens[1] -ceq '-m' -and $tokens[2] -ceq 'waitress' -and $tokens[3] -ceq '--listen=127.0.0.1:5101' -and $tokens[4] -ceq 'backend.wsgi:app'
    }catch{$valid=$false}
    Need $valid 'orphan/mismatched listener: process is not the configured Waitress backend'
}
function Get-ConfiguredTask {
    $tasks=@(Get-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction SilentlyContinue)
    Need ($tasks.Count -eq 1) 'production scheduled task missing or ambiguous'
    $task=$tasks[0]
    Need ($task.Settings.Enabled -is [bool] -and $task.Settings.Enabled) 'production scheduled task must be enabled'
    $xml=Export-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop
    $launch=Get-TaskLaunch $xml
    $actions=@($task.Actions)
    Need ($actions.Count -eq 1) 'one task action required'
    Need ((SamePath ([string]$actions[0].Execute) ([string]$launch.Action.Command)) -and
          [string]::Equals([string]$actions[0].Arguments,[string]$launch.Action.Arguments,[StringComparison]::Ordinal) -and
          (SamePath ([string]$actions[0].WorkingDirectory) ([string]$launch.Action.WorkingDirectory))) 'task action/export configuration mismatch'
    return [pscustomobject]@{Task=$task;Xml=$xml;Runtime=$launch.Runtime;Release=$launch.Release}
}
function Fail([string]$Stage){if($FailAt -eq $Stage){throw "RELEASE_STOP: injected $Stage"}}
function Save($state){if($FixtureStatePath){$state|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $FixtureStatePath -Encoding UTF8}}
function Get-RealServerDiscoveryState{
    # This function is deliberately read-only.  It is the non-fixture path used
    # by ValidateOnly; Execute remains explicitly gated below.
    Import-Module WebAdministration -ErrorAction Stop
    $site=Get-Website -Name 'forwarder' -ErrorAction Stop
    $rows=@(Get-NetTCPConnection -State Listen -LocalPort 5101 -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq '127.0.0.1'})
    $owners=@($rows | Select-Object -ExpandProperty OwningProcess -Unique)
    Need ($owners.Count -le 1) 'multiple listener owners on port 5101'
    $tasks=@(Get-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction SilentlyContinue)
    if($tasks.Count -eq 0){
        if($owners.Count){throw 'RELEASE_STOP: orphan listener: production scheduled task missing or unavailable'}
        throw 'RELEASE_STOP: backend unavailable: production scheduled task missing or unavailable'
    }
    Need ($tasks.Count -eq 1) 'ambiguous production scheduled task'
    $task=$tasks[0]
    # A launcher may finish successfully and return to Ready while its child
    # continues serving. State and LastTaskResult are diagnostics, not ownership.
    Need ($task.Settings.Enabled -is [bool]) 'task enabled state unavailable'
    $enabled=[bool]$task.Settings.Enabled
    if(-not $enabled){
        if($owners.Count){throw 'RELEASE_STOP: stale/orphan listener: production scheduled task is disabled'}
        throw 'RELEASE_STOP: backend unavailable: production scheduled task is disabled'
    }
    $configured=Get-ConfiguredTask
    $task=$configured.Task;$xml=$configured.Xml
    $expectedRuntime=$configured.Runtime;$expectedRoot=$configured.Release
    Need (SamePath ([string]$site.PhysicalPath) (Join-Path $expectedRoot 'dist')) 'IIS/task release mismatch'
    Need ($owners.Count -eq 1) 'backend unavailable: no listener on 127.0.0.1:5101'
    $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop
    Assert-ListenerProcess $process $expectedRuntime
    $runtime=[string]$process.ExecutablePath
    try{$healthResponse=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5101/api/health' -TimeoutSec 10 -ErrorAction Stop}
    catch{throw 'RELEASE_STOP: unhealthy backend: internal health request failed; listener provenance matches configured task'}
    Need ($healthResponse.StatusCode -eq 200) 'unhealthy backend: internal health is not HTTP 200; listener provenance matches configured task'
    $taskInfo=Get-ScheduledTaskInfo -InputObject $task -ErrorAction Stop
    Import-ReleaseEnvironment
    $migration=Invoke-MigrationCli @('current')
    $revisionLine=@($migration | ForEach-Object {[string]$_} | Where-Object {$_ -match '^current='} | Select-Object -Last 1)
    Need ($revisionLine.Count -eq 1) 'database revision output is ambiguous'
    $revision=$revisionLine[0].Substring(8)
    Need (-not [string]::IsNullOrWhiteSpace($revision)) 'database revision unavailable'
    return [pscustomobject]@{iis_path=[string]$site.PhysicalPath;task_xml=[string]$xml;enabled=$enabled;task_state=[string]$task.State;last_task_result=$taskInfo.LastTaskResult;listener_runtime=$runtime;listener_pid=[int]$owners[0];listener_up=$true;health=$true;db_revision=$revision}
}
function Invoke-MigrationCli([string[]]$Arguments){
    $info=New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName=Join-Path $PackageRoot 'artifact\runtime\python.exe'
    $info.Arguments='-m backend.migration_cli '+($Arguments -join ' ')
    $info.WorkingDirectory=Join-Path $PackageRoot 'artifact'
    $info.UseShellExecute=$false
    $info.CreateNoWindow=$true
    $info.RedirectStandardOutput=$true
    $info.RedirectStandardError=$true
    $info.EnvironmentVariables['PYTHONDONTWRITEBYTECODE']='1'
    $process=New-Object System.Diagnostics.Process
    $process.StartInfo=$info
    try{
        Need ($process.Start()) 'migration process could not start'
        $stdout=$process.StandardOutput.ReadToEndAsync()
        $stderr=$process.StandardError.ReadToEndAsync()
        $limit=if($Arguments[0] -eq 'upgrade'){$Timeouts.MIGRATION}else{$Timeouts.DB_GATE}
        if(-not $process.WaitForExit($limit*1000)){$process.Kill();throw 'RELEASE_STOP: migration command timeout'}
        $result=[string]$stdout.Result
        $null=$stderr.Result
        if($process.ExitCode -ne 0){throw 'RELEASE_STOP: migration command failed'}
        return ($result -split "`r?`n")
    }finally{$process.Dispose()}
}
function Wait-Listener([string]$Expected,[int]$Seconds){
    $deadline=[datetime]::UtcNow.AddSeconds($Seconds)
    do{
        $rows=@(Get-NetTCPConnection -State Listen -LocalPort 5101 -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq '127.0.0.1'})
        $owners=@($rows | Select-Object -ExpandProperty OwningProcess -Unique)
        Need ($owners.Count -le 1) 'multiple listener owners'
        if($owners.Count -eq 1){
            $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop
            Assert-ListenerProcess $process $Expected
            Need (SamePath (Get-ConfiguredTask).Runtime $Expected) 'listener/task runtime mismatch'
            return
        }
        Start-Sleep -Milliseconds 250
    }while([datetime]::UtcNow -lt $deadline)
    throw 'RELEASE_STOP: listener identity timeout'
}
function Wait-PortFree([int]$Seconds){
    $deadline=[datetime]::UtcNow.AddSeconds($Seconds)
    do{
        $rows=@(Get-NetTCPConnection -State Listen -LocalPort 5101 -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq '127.0.0.1'})
        if($rows.Count -eq 0){return}
        Start-Sleep -Milliseconds 250
    }while([datetime]::UtcNow -lt $deadline)
    throw 'RELEASE_STOP: port release timeout'
}
function Assert-Health([string]$Uri,[int]$Seconds){
    $deadline=[datetime]::UtcNow.AddSeconds($Seconds)
    do{
        try{$response=Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 5 -ErrorAction Stop;if($response.StatusCode -eq 200){return}}catch{}
        Start-Sleep -Milliseconds 500
    }while([datetime]::UtcNow -lt $deadline)
    throw ('RELEASE_STOP: health timeout '+$Uri)
}
function Set-IisPhysicalPath([string]$Path){
    Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.applicationHost/sites/site[@name='forwarder']/application[@path='/']/virtualDirectory[@path='/']" -Name physicalPath -Value $Path -ErrorAction Stop
    Need (SamePath ([string](Get-Website -Name 'forwarder' -ErrorAction Stop).PhysicalPath) $Path) 'IIS physical path mismatch'
}
function Rollback($state,$before,[string]$targetPython){
    try{
        Need (SamePath (TaskRuntime $before.task_xml) $before.listener_runtime) 'rollback baseline task/runtime mismatch'
        if($FixtureStatePath){$state.iis_path=$before.iis_path;$state.task_xml=$before.task_xml;$state.enabled=$before.enabled;$state.listener_runtime=$before.listener_runtime;$state.listener_up=$true;$state.health=$true;Save $state}
        else{
            Disable-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop|Out-Null
            $rows=@(Get-NetTCPConnection -State Listen -LocalPort 5101 -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq '127.0.0.1'})
            $owners=@($rows | Select-Object -ExpandProperty OwningProcess -Unique)
            Need ($owners.Count -le 1) 'ambiguous rollback listener'
            if($owners.Count -eq 1){
                $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop
                Need ((SamePath ([string]$process.ExecutablePath) $targetPython) -or (SamePath ([string]$process.ExecutablePath) $before.listener_runtime)) 'unrecognized rollback listener'
                Assert-ListenerProcess $process ([string]$process.ExecutablePath)
                Stop-Process -Id ([int]$owners[0]) -Force -ErrorAction Stop
            }
            Wait-PortFree $Timeouts.PORT_RELEASE
            Set-IisPhysicalPath $before.iis_path
            Register-ScheduledTask -TaskName 'Forwarder Backend Production' -Xml $before.task_xml -Force -ErrorAction Stop|Out-Null
            if($before.enabled){Enable-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop|Out-Null;Start-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop;Wait-Listener $before.listener_runtime $Timeouts.ROLLBACK_RECOVERY;Assert-Health 'http://127.0.0.1:5101/api/health' $Timeouts.ROLLBACK_RECOVERY}
        }
        Write-Output 'ROLLBACK_RESULT=PASS'
    }catch{Write-Output 'ROLLBACK_RESULT=FAIL';throw}
}
Need (-not($ValidateOnly -and $Execute)) 'one deployment mode';if(-not $ValidateOnly -and -not $Execute){$ValidateOnly=$true};if($Execute){Need $ConfirmDeployment 'confirmation required'}
Need (Test-Path -LiteralPath $PackageRoot -PathType Container) 'absolute package root required';$PackageRoot=(Resolve-Path -LiteralPath $PackageRoot).Path
# Verify bytes before discovery can launch the packaged migration runtime.
Fail 'PACKAGE_VERIFY';& (Join-Path $PackageRoot 'VERIFY-PACKAGE.ps1') -PackageRoot $PackageRoot
if($FixtureStatePath){$state=Get-Content -Raw -LiteralPath $FixtureStatePath|ConvertFrom-Json}else{$state=Get-RealServerDiscoveryState}
Fail 'BASELINE_CAPTURE';$before=[pscustomobject]@{iis_path=$state.iis_path;task_xml=$state.task_xml;enabled=$state.enabled;listener_runtime=$state.listener_runtime};$oldPython=TaskRuntime $before.task_xml
$oldRoot=Split-Path -Parent (Split-Path -Parent $oldPython)
Need $before.enabled 'stale/orphan listener: production scheduled task is disabled'
Need $state.listener_up 'backend unavailable: no listener on 127.0.0.1:5101'
Need (SamePath $oldPython $before.listener_runtime) 'pre-cutover runtime mismatch'
Need (SamePath $before.iis_path (Join-Path $oldRoot 'dist')) 'IIS/task release mismatch'
Need $state.health 'unhealthy backend: listener provenance matches configured task'
Write-Output 'LISTENER_PROVENANCE=MATCH'
Write-Output 'OFFICIAL_BACKEND=YES'
Write-Output 'ORPHAN_OR_MISMATCH=NO'
if(-not $FixtureStatePath){Write-Output ('TASK_STATE='+$state.task_state);Write-Output ('LAST_TASK_RESULT='+$state.last_task_result)}
Fail 'DB_GATE';Need ($state.db_revision -in @($RequiredBefore,$RequiredTarget)) 'unknown database lineage';if($state.db_revision -eq $RequiredBefore){$migrationNeeded=$true}else{$migrationNeeded=$false};if($ValidateOnly){Write-Output 'DB_GATE_MATRIX=PASS';Write-Output 'VALIDATEONLY_COMPLETE=YES';return}
$target=Join-Path (NPath $ReleaseRoot) ('release-'+(Get-Date).ToUniversalTime().ToString('yyyyMMddHHmmss')+'-'+$RequiredTarget)
$targetPython=Join-Path $target 'runtime\python.exe'
$nextXml=New-TaskLaunchXml $before.task_xml $target
Need (-not (Test-Path -LiteralPath $target)) 'target already exists'
$mutationStarted=$false
try{
    Fail 'TARGET_MATERIALIZE'
    if(-not $FixtureStatePath){New-Item -ItemType Directory -Path $target -ErrorAction Stop|Out-Null;Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'artifact') -Force|Copy-Item -Destination $target -Recurse -Force -ErrorAction Stop;Need (Test-Path -LiteralPath $targetPython -PathType Leaf) 'target runtime missing'}
    if($migrationNeeded){Fail 'MIGRATION';if($FixtureStatePath){$state.db_revision=$RequiredTarget;Save $state}else{Invoke-MigrationCli @('upgrade',$RequiredTarget,'--confirm')|Out-Null;$afterMigration=@(Invoke-MigrationCli @('current')|Where-Object {$_ -match '^current='});Need ($afterMigration.Count -eq 1 -and $afterMigration[0] -eq ('current='+$RequiredTarget)) 'migration postcondition mismatch';$state.db_revision=$RequiredTarget}}
    $mutationStarted=$true
    Fail 'TASK_DISABLE';if($FixtureStatePath){$state.enabled=$false;Save $state}else{Disable-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop|Out-Null}
    Fail 'BACKEND_STOP';if($FixtureStatePath){$state.listener_up=$false;Save $state}else{Stop-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop;$remaining=Get-Process -Id ([int]$state.listener_pid) -ErrorAction SilentlyContinue;if($null -ne $remaining){$identity=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$state.listener_pid) -ErrorAction Stop;Assert-ListenerProcess $identity $oldPython;Stop-Process -Id ([int]$state.listener_pid) -Force -ErrorAction Stop}}
    Fail 'PORT_RELEASE';if($FixtureStatePath){Need (-not $state.listener_up) 'port not released'}else{Wait-PortFree $Timeouts.PORT_RELEASE}
    Fail 'TASK_SWITCH';Need (SamePath (TaskRuntime $nextXml) $targetPython) 'target task/runtime mismatch';if($FixtureStatePath){$state.task_xml=$nextXml;Save $state}else{Register-ScheduledTask -TaskName 'Forwarder Backend Production' -Xml $nextXml -Force -ErrorAction Stop|Out-Null}
    Fail 'BACKEND_START';if($FixtureStatePath){$state.enabled=$true;$state.listener_up=$true;$state.listener_runtime=$targetPython;Save $state}else{Enable-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop|Out-Null;Start-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop}
    Fail 'LISTENER_VERIFY';if($FixtureStatePath){Need (SamePath $state.listener_runtime $targetPython) 'target runtime mismatch'}else{Wait-Listener $targetPython $Timeouts.LISTENER_VERIFY}
    Fail 'INTERNAL_HEALTH';if($FixtureStatePath){Need $state.health 'internal health failure'}else{Assert-Health 'http://127.0.0.1:5101/api/health' $Timeouts.INTERNAL_HEALTH}
    Fail 'IIS_SWITCH';if($FixtureStatePath){$state.iis_path=Join-Path $target 'dist';Save $state}else{Set-IisPhysicalPath (Join-Path $target 'dist')}
    Fail 'IIS_VERIFY';if($FixtureStatePath){Need (SamePath $state.iis_path (Join-Path $target 'dist')) 'IIS target mismatch'}else{Need (SamePath ([string](Get-Website -Name 'forwarder').PhysicalPath) (Join-Path $target 'dist')) 'IIS target mismatch'}
    Fail 'PUBLIC_HEALTH';if($FixtureStatePath){Need $state.health 'public health failure'}else{Assert-Health 'https://samand.forwarderet.ir/api/health' $Timeouts.PUBLIC_HEALTH}
    Fail 'POST_DEPLOY_VERIFY';Write-Output 'FULL_EXECUTE_SIMULATION=PASS'
}catch{$primary=$_;if($mutationStarted){try{Rollback $state $before $targetPython}catch{throw ('RELEASE_STOP: cutover and rollback failed; primary='+$primary.Exception.Message+'; rollback='+$_.Exception.Message)}};throw $primary}
