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
function TaskRuntime([string]$Xml){[xml]$doc=$Xml;$exec=@($doc.SelectNodes("//*[local-name()='Exec']"));Need ($exec.Count -eq 1) 'one task action required';$command=NPath ([string]$exec[0].Command);$work=NPath ([string]$exec[0].WorkingDirectory);$arguments=[string]$exec[0].Arguments;Need ($arguments -match '(?i)-m\s+waitress\b' -and $arguments -match '(?i)backend\.wsgi:app') 'task must launch the Waitress backend';if([IO.Path]::GetFileName($command) -ieq 'python.exe'){$path=$command}else{Need ([IO.Path]::GetFileName($command) -ieq 'cmd.exe') 'cmd.exe or python.exe required';Need ($arguments -match '(?i)^\s*/d\s+/c\s+') 'cmd.exe /d /c required';$found=@([regex]::Matches($arguments,'(?i)[a-z]:[\\/][^"&\r\n]*?[\\/]runtime[\\/]python\.exe'));Need ($found.Count -eq 1) 'one release-local runtime required';$path=NPath $found[0].Value};Need (SamePath $work (Split-Path -Parent (Split-Path -Parent $path))) 'runtime/WorkingDirectory mismatch';return $path}
function Fail([string]$Stage){if($FailAt -eq $Stage){throw "RELEASE_STOP: injected $Stage"}}
function Save($state){if($FixtureStatePath){$state|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $FixtureStatePath -Encoding UTF8}}
function Get-RealServerDiscoveryState{
    # This function is deliberately read-only.  It is the non-fixture path used
    # by ValidateOnly; Execute remains explicitly gated below.
    Import-Module WebAdministration -ErrorAction Stop
    $site=Get-Website -Name 'forwarder' -ErrorAction Stop
    $task=Get-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop
    $xml=Export-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop
    $rows=@(Get-NetTCPConnection -State Listen -LocalPort 5101 -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq '127.0.0.1'})
    $owners=@($rows | Select-Object -ExpandProperty OwningProcess -Unique)
    Need ($owners.Count -le 1) 'multiple listener owners on port 5101'
    $runtime=$null
    if($owners.Count -eq 1){$process=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop;Need (-not [string]::IsNullOrWhiteSpace([string]$process.ExecutablePath)) 'listener executable path unavailable';Need ([string]$process.CommandLine -match '(?i)-m\s+waitress\b' -and [string]$process.CommandLine -match '(?i)backend\.wsgi:app') 'listener is not the Waitress backend';$runtime=[string]$process.ExecutablePath;Need ([string]$task.State -eq 'Running') 'orphan Waitress listener: scheduled task is not running'}
    Import-ReleaseEnvironment
    $migration=Invoke-MigrationCli @('current')
    $revisionLine=@($migration | ForEach-Object {[string]$_} | Where-Object {$_ -match '^current='} | Select-Object -Last 1)
    Need ($revisionLine.Count -eq 1) 'database revision output is ambiguous'
    $revision=$revisionLine[0].Substring(8)
    Need (-not [string]::IsNullOrWhiteSpace($revision)) 'database revision unavailable'
    $healthResponse=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5101/api/health' -TimeoutSec 10 -ErrorAction Stop
    Need ($healthResponse.StatusCode -eq 200) 'internal health is not HTTP 200'
    return [pscustomobject]@{iis_path=[string]$site.PhysicalPath;task_xml=[string]$xml;enabled=([string]$task.State -ne 'Disabled');listener_runtime=$runtime;listener_pid=if($owners.Count -eq 1){[int]$owners[0]}else{0};listener_up=($owners.Count -eq 1);health=$true;db_revision=$revision}
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
            if(SamePath ([string]$process.ExecutablePath) $Expected){return}
            Need $false 'unrecognized Waitress listener'
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
        if($FixtureStatePath){$state.iis_path=$before.iis_path;$state.task_xml=$before.task_xml;$state.enabled=$before.enabled;$state.listener_runtime=$before.listener_runtime;$state.listener_up=$true;$state.health=$true;Save $state}
        else{
            Disable-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop|Out-Null
            $rows=@(Get-NetTCPConnection -State Listen -LocalPort 5101 -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq '127.0.0.1'})
            $owners=@($rows | Select-Object -ExpandProperty OwningProcess -Unique)
            Need ($owners.Count -le 1) 'ambiguous rollback listener'
            if($owners.Count -eq 1){$process=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop;Need ((SamePath ([string]$process.ExecutablePath) $targetPython) -or (SamePath ([string]$process.ExecutablePath) $before.listener_runtime)) 'unrecognized rollback listener';Stop-Process -Id ([int]$owners[0]) -Force -ErrorAction Stop}
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
if($FixtureStatePath){$state=Get-Content -Raw -LiteralPath $FixtureStatePath|ConvertFrom-Json}else{$state=Get-RealServerDiscoveryState}
Fail 'PACKAGE_VERIFY';& (Join-Path $PackageRoot 'VERIFY-PACKAGE.ps1') -PackageRoot $PackageRoot
Fail 'BASELINE_CAPTURE';$before=[pscustomobject]@{iis_path=$state.iis_path;task_xml=$state.task_xml;enabled=$state.enabled;listener_runtime=$state.listener_runtime};$oldPython=TaskRuntime $before.task_xml;Need (SamePath $oldPython $before.listener_runtime) 'pre-cutover runtime mismatch'
Fail 'DB_GATE';Need ($state.db_revision -in @($RequiredBefore,$RequiredTarget)) 'unknown database lineage';if($state.db_revision -eq $RequiredBefore){$migrationNeeded=$true}else{$migrationNeeded=$false};if($ValidateOnly){Write-Output 'DB_GATE_MATRIX=PASS';Write-Output 'VALIDATEONLY_COMPLETE=YES';return}
$target=Join-Path (NPath $ReleaseRoot) ('release-'+(Get-Date).ToUniversalTime().ToString('yyyyMMddHHmmss')+'-'+$RequiredTarget)
$targetPython=Join-Path $target 'runtime\python.exe'
$oldRoot=Split-Path -Parent (Split-Path -Parent $oldPython)
Need ((SamePath $before.iis_path (Join-Path $oldRoot 'dist')) -and $before.enabled -and $state.listener_up) 'incoherent production baseline'
Need ($before.task_xml.Contains($oldRoot)) 'task XML does not identify current release'
Need (-not (Test-Path -LiteralPath $target)) 'target already exists'
$mutationStarted=$false
try{
    Fail 'TARGET_MATERIALIZE'
    if(-not $FixtureStatePath){New-Item -ItemType Directory -Path $target -ErrorAction Stop|Out-Null;Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'artifact') -Force|Copy-Item -Destination $target -Recurse -Force -ErrorAction Stop;Need (Test-Path -LiteralPath $targetPython -PathType Leaf) 'target runtime missing'}
    if($migrationNeeded){Fail 'MIGRATION';if($FixtureStatePath){$state.db_revision=$RequiredTarget;Save $state}else{Invoke-MigrationCli @('upgrade',$RequiredTarget,'--confirm')|Out-Null;$afterMigration=@(Invoke-MigrationCli @('current')|Where-Object {$_ -match '^current='});Need ($afterMigration.Count -eq 1 -and $afterMigration[0] -eq ('current='+$RequiredTarget)) 'migration postcondition mismatch';$state.db_revision=$RequiredTarget}}
    $mutationStarted=$true
    Fail 'TASK_DISABLE';if($FixtureStatePath){$state.enabled=$false;Save $state}else{Disable-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop|Out-Null}
    Fail 'BACKEND_STOP';if($FixtureStatePath){$state.listener_up=$false;Save $state}else{Stop-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop;$remaining=Get-Process -Id ([int]$state.listener_pid) -ErrorAction SilentlyContinue;if($null -ne $remaining){$identity=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$state.listener_pid) -ErrorAction Stop;Need (SamePath ([string]$identity.ExecutablePath) $oldPython) 'listener PID was reused by an unrelated process';Stop-Process -Id ([int]$state.listener_pid) -Force -ErrorAction Stop}}
    Fail 'PORT_RELEASE';if($FixtureStatePath){Need (-not $state.listener_up) 'port not released'}else{Wait-PortFree $Timeouts.PORT_RELEASE}
    Fail 'TASK_SWITCH';$nextXml=$before.task_xml.Replace($oldRoot,$target);Need ($nextXml -ne $before.task_xml) 'task target not replaced';Need (SamePath (TaskRuntime $nextXml) $targetPython) 'target task/runtime mismatch';if($FixtureStatePath){$state.task_xml=$nextXml;Save $state}else{Register-ScheduledTask -TaskName 'Forwarder Backend Production' -Xml $nextXml -Force -ErrorAction Stop|Out-Null}
    Fail 'BACKEND_START';if($FixtureStatePath){$state.enabled=$true;$state.listener_up=$true;$state.listener_runtime=$targetPython;Save $state}else{Enable-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop|Out-Null;Start-ScheduledTask -TaskName 'Forwarder Backend Production' -ErrorAction Stop}
    Fail 'LISTENER_VERIFY';if($FixtureStatePath){Need (SamePath $state.listener_runtime $targetPython) 'target runtime mismatch'}else{Wait-Listener $targetPython $Timeouts.LISTENER_VERIFY}
    Fail 'INTERNAL_HEALTH';if($FixtureStatePath){Need $state.health 'internal health failure'}else{Assert-Health 'http://127.0.0.1:5101/api/health' $Timeouts.INTERNAL_HEALTH}
    Fail 'IIS_SWITCH';if($FixtureStatePath){$state.iis_path=Join-Path $target 'dist';Save $state}else{Set-IisPhysicalPath (Join-Path $target 'dist')}
    Fail 'IIS_VERIFY';if($FixtureStatePath){Need (SamePath $state.iis_path (Join-Path $target 'dist')) 'IIS target mismatch'}else{Need (SamePath ([string](Get-Website -Name 'forwarder').PhysicalPath) (Join-Path $target 'dist')) 'IIS target mismatch'}
    Fail 'PUBLIC_HEALTH';if($FixtureStatePath){Need $state.health 'public health failure'}else{Assert-Health 'https://samand.forwarderet.ir/api/health' $Timeouts.PUBLIC_HEALTH}
    Fail 'POST_DEPLOY_VERIFY';Write-Output 'FULL_EXECUTE_SIMULATION=PASS'
}catch{$primary=$_;if($mutationStarted){try{Rollback $state $before $targetPython}catch{throw ('RELEASE_STOP: cutover and rollback failed; primary='+$primary.Exception.Message+'; rollback='+$_.Exception.Message)}};throw $primary}
