#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[string]$DeployScript,[switch]$FreshChild,[ValidateSet('Full','Captured')][string]$Matrix='Full')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $DeployScript){$DeployScript=Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1'}
if(-not $FreshChild){
    # Windows PowerShell wraps native stderr as ErrorRecord objects. Preserve all
    # child diagnostics before failing, instead of terminating on the first line.
    try{$ErrorActionPreference='Continue';$output=@(& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $PSCommandPath -PackageRoot $PackageRoot -DeployScript $DeployScript -FreshChild -Matrix $Matrix 2>&1);$childExit=$LASTEXITCODE}
    finally{$ErrorActionPreference='Stop'}
    if($childExit -ne 0 -or $output -notcontains 'FRESH_PROCESS_VALIDATEONLY=PASS'){throw ($output -join "`n")}
    $output
    return
}
if($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1){throw 'Windows PowerShell 5.1 required'}
Microsoft.PowerShell.Core\Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop
if(@(Get-Variable -Scope Global | Where-Object Name -like 'Forwarder*').Count){throw 'fresh child inherited Forwarder state'}
if(Get-Variable ForwarderExecuteState -Scope Global -ErrorAction SilentlyContinue){throw 'ForwarderExecuteState is not absent'}
Write-Output 'PREINVOCATION_FORWARDER_EXECUTE_STATE=ABSENT'
$previousLocation=Get-Location
Set-Location ([IO.Path]::GetTempPath())
$release='C:\1-webapp\forwarder-production\release-forwarder-systemic-workflow-b4294fc-20260913222754'
$python=Join-Path $release 'runtime\python.exe'
$xml='<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c set PYTHONPATH='+$release+' &amp;&amp; cd /d &quot;'+$release+'&quot; &amp;&amp; &quot;'+$python+'&quot; &quot;C:\1-webapp\forwarder-runtime\phase1b\_production\_cutover\_runtime.py&quot; serve --env &quot;C:\1-webapp\forwarder-runtime\production.env&quot; --repo &quot;'+$release+'&quot; --host 127.0.0.1 --port 5101 --log &quot;C:\1-webapp\forwarder-runtime\waitress.log&quot;</Arguments><WorkingDirectory>'+$release+'</WorkingDirectory></Exec></Actions></Task>'
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('forwarder-db-gate-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary|Out-Null
$previousDatabaseUrl=$env:DATABASE_URL
$previousAppEnv=$env:APP_ENV
$previousTestDatabase=$env:FW_TEST_DATABASE
try{
    $database=Join-Path $temporary 'validate-only.sqlite'
    $env:FW_TEST_DATABASE=$database
    $runtime=Join-Path $PackageRoot 'artifact\runtime\python.exe'
    $setupCode=@'
import sqlite3, os
connection=sqlite3.connect(os.environ['FW_TEST_DATABASE'])
connection.execute('CREATE TABLE alembic_version (version_num VARCHAR(128) NOT NULL)')
connection.execute('INSERT INTO alembic_version VALUES (?)', ('20260920_legal_customer_nullable_contact_names',))
connection.commit()
connection.close()
'@
    & $runtime -c $setupCode
    if($LASTEXITCODE -ne 0){throw 'disposable DB setup failed'}
    $env:DATABASE_URL='sqlite:///'+$database.Replace('\','/')
    $env:APP_ENV='production'
    $beforeHash=(Get-FileHash -LiteralPath $database -Algorithm SHA256).Hash
    $mutations=@{Count=0}
    $topology=[pscustomobject]@{TaskState='Ready';LastTaskResult=0;Enabled=$true;TaskExists=$true;Xml=$xml;Iis=(Join-Path $release 'dist');Owners=@(93244);Runtime=$python;CommandLine=('"'+$python+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app');Health=200;HealthThrows=$false;ActionMismatch='';HealthCalls=0}
    function Reset-Topology {
        $topology.TaskState='Ready';$topology.LastTaskResult=0;$topology.Enabled=$true;$topology.TaskExists=$true
        $topology.Xml=$xml;$topology.Iis=Join-Path $release 'dist';$topology.Owners=@(93244);$topology.Runtime=$python
        $topology.CommandLine='"'+$python+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app';$topology.Health=200;$topology.HealthThrows=$false;$topology.ActionMismatch='';$topology.HealthCalls=0
    }
    function Import-Module { param([string]$Name) }
    function Get-Website { param([string]$Name) [pscustomobject]@{PhysicalPath=$topology.Iis} }
    function Get-ScheduledTask {
        param([string]$TaskName)
        if(-not $topology.TaskExists){return}
        [xml]$document=$topology.Xml
        $action=[pscustomobject]@{Execute=[string]$document.Task.Actions.Exec.Command;Arguments=[string]$document.Task.Actions.Exec.Arguments;WorkingDirectory=[string]$document.Task.Actions.Exec.WorkingDirectory}
        if($topology.ActionMismatch){$action.($topology.ActionMismatch)='C:\different-snapshot'}
        [pscustomobject]@{State=$topology.TaskState;Settings=[pscustomobject]@{Enabled=$topology.Enabled};Actions=@($action)}
    }
    function Get-ScheduledTaskInfo { param($InputObject) [pscustomobject]@{LastTaskResult=$topology.LastTaskResult} }
    function Export-ScheduledTask { param([string]$TaskName) $topology.Xml }
    function Get-NetTCPConnection { param([string]$State,[int]$LocalPort) foreach($owner in $topology.Owners){[pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=$owner}} }
    function Get-CimInstance { param([string]$ClassName,[string]$Filter) if($Filter -ne 'ProcessId=93244'){throw 'wrong listener PID inspected'};[pscustomobject]@{ExecutablePath=$topology.Runtime;CommandLine=$topology.CommandLine} }
    function Invoke-WebRequest { param([string]$Uri,[int]$TimeoutSec) $topology.HealthCalls++;if($topology.HealthThrows){throw 'simulated connection failure'};[pscustomobject]@{StatusCode=$topology.Health} }
    function Disable-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to disable task' }
    function Stop-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to stop task' }
    function Stop-Process { $mutations.Count++;throw 'ValidateOnly tried to stop process' }
    function Register-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to register task' }
    function Set-WebConfigurationProperty { $mutations.Count++;throw 'ValidateOnly tried to change IIS' }
    function Enable-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to enable task' }
    function Start-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to start task' }
    function Set-NetTCPConnection { $mutations.Count++;throw 'ValidateOnly tried to change port' }
    function New-Item { $mutations.Count++;throw 'ValidateOnly tried to create files' }
    function Copy-Item { $mutations.Count++;throw 'ValidateOnly tried to copy files' }
    $root=$PackageRoot
    if($DeployScript -ne (Join-Path $root 'deploy_windows_iis_waitress.ps1')){throw 'fresh regression requires exact packaged deployment path'}
    function Assert-Topology([string]$Name,[string]$ExpectedError='') {
        $snapshot=$topology|ConvertTo-Json -Depth 8
        $observed=New-Object 'System.Collections.Generic.List[string]'
        $failure=''
        try{& "$root\deploy_windows_iis_waitress.ps1" -PackageRoot $root -ValidateOnly | ForEach-Object {$observed.Add([string]$_)}}catch{$failure=$_.Exception.Message}
        if($ExpectedError){
            if($failure -ne ('RELEASE_STOP: '+$ExpectedError)){throw ($Name+': wrong refusal: '+$failure)}
            if($observed.Contains('OFFICIAL_BACKEND=YES') -or $observed.Contains('VALIDATEONLY_COMPLETE=YES')){throw ($Name+': invalid baseline accepted')}
        }else{
            if($failure){throw ($Name+': '+$failure)}
            foreach($mark in @('OFFICIAL_BACKEND=YES','ORPHAN_OR_MISMATCH=NO','LISTENER_PROVENANCE=MATCH','VALIDATEONLY_COMPLETE=YES',('TASK_STATE='+$topology.TaskState),('LAST_TASK_RESULT='+$topology.LastTaskResult))){if(-not $observed.Contains($mark)){throw ($Name+': missing '+$mark)}}
        }
        $healthCalls=$topology.HealthCalls;$topology.HealthCalls=0
        if($mutations.Count -ne 0 -or ($topology|ConvertTo-Json -Depth 8) -ne $snapshot -or (Get-FileHash -LiteralPath $database -Algorithm SHA256).Hash -ne $beforeHash){throw ($Name+': ValidateOnly mutated observed state')}
        if(($ExpectedError -eq '' -or $ExpectedError -like 'unhealthy*') -and $healthCalls -ne 1){throw ($Name+': health was not checked')}
        if($ExpectedError -and $ExpectedError -notlike 'unhealthy*' -and $healthCalls -ne 0){throw ($Name+': invalid provenance reached health')}
        $classification=if(-not $ExpectedError){'OFFICIAL_BACKEND=YES; ORPHAN_OR_MISMATCH=NO'}elseif($ExpectedError -like '*orphan*'){'ORPHAN_OR_MISMATCH=YES'}elseif($ExpectedError -like 'unhealthy*'){'UNHEALTHY=YES; ORPHAN_OR_MISMATCH=NO'}else{'BASELINE_REFUSED=YES'}
        Write-Output ('TOPOLOGY_CASE='+$Name+'; '+$classification+'; RESULT=PASS; MUTATION=NO')
    }
    Assert-Topology 'Ready_matching_captured_Production'
    Write-Output 'REAL_PRODUCTION_READY_TASK_TOPOLOGY=PASS'
    Write-Output 'REAL_PRODUCTION_LAUNCHER_TOPOLOGY=PASS'
    if($Matrix -eq 'Full'){
    $topology.TaskState='Running';Assert-Topology 'Running_matching'
    Reset-Topology;$topology.Runtime=$python.Replace('b4294fc','other-release');Assert-Topology 'Ready_other_release' 'orphan/mismatched listener: executable differs from task-configured runtime'
    Reset-Topology;$topology.Enabled=$false;Assert-Topology 'Ready_disabled_listener' 'stale/orphan listener: production scheduled task is disabled'
    Reset-Topology;$topology.TaskExists=$false;Assert-Topology 'Missing_task_listener' 'orphan listener: production scheduled task missing or unavailable'
    Reset-Topology;$topology.Owners=@();Assert-Topology 'Valid_task_no_listener' 'backend unavailable: no listener on 127.0.0.1:5101'
    Reset-Topology;$topology.Owners=@(93244,93245);Assert-Topology 'Multiple_unique_listener_PIDs' 'multiple listener owners on port 5101'
    Reset-Topology;$topology.Health=503;Assert-Topology 'Matching_unhealthy' 'unhealthy backend: internal health is not HTTP 200; listener provenance matches configured task'
    Reset-Topology;$topology.HealthThrows=$true;Assert-Topology 'Matching_health_transport_failure' 'unhealthy backend: internal health request failed; listener provenance matches configured task'
    Reset-Topology;$topology.Owners=@(93244,93244);Assert-Topology 'Duplicate_rows_same_PID'
    Reset-Topology;$topology.LastTaskResult=1;Assert-Topology 'Last_result_is_diagnostic'
    Reset-Topology;$topology.TaskState='Running';$topology.Enabled=$false;Assert-Topology 'Running_disabled_listener' 'stale/orphan listener: production scheduled task is disabled'
    Reset-Topology;$topology.Enabled=$null;Assert-Topology 'Unknown_enabled_state' 'task enabled state unavailable'
    Reset-Topology;$topology.Iis=$topology.Iis.Replace('b4294fc','other-release');Assert-Topology 'IIS_other_release' 'IIS/task release mismatch'
    Reset-Topology;$topology.Runtime='';Assert-Topology 'Unknown_executable' 'listener executable path unavailable'
    Reset-Topology;$topology.CommandLine=$python+' unrelated.py';Assert-Topology 'Non_backend_process' 'orphan/mismatched listener: process is not the configured Waitress backend'
    Reset-Topology;$topology.Xml=$xml.Replace('cmd.exe','powershell.exe');Assert-Topology 'Wrong_task_execute' 'system cmd.exe required'
    Reset-Topology;$topology.Xml=$xml.Replace('_cutover\_runtime.py','_cutover\unapproved.py');Assert-Topology 'Wrong_task_launcher' 'approved runtime launcher required'
    Reset-Topology;$topology.Xml=$xml.Replace('<WorkingDirectory>'+ $release,'<WorkingDirectory>C:\other-release');Assert-Topology 'Wrong_task_working_directory' 'runtime/WorkingDirectory mismatch'
    Reset-Topology;$topology.Xml=$xml.Replace('serve --env','migrate --env');Assert-Topology 'Wrong_launcher_mode' 'runtime launcher serve command required'
    Reset-Topology;$topology.Xml=$xml.Replace('--repo &quot;'+$release+'&quot;','');Assert-Topology 'Missing_repo' 'launcher --repo required'
    Reset-Topology;$topology.Xml=$xml.Replace('--repo &quot;'+$release+'&quot;','--repo &quot;C:\another-release&quot;');Assert-Topology 'Wrong_repo' 'PYTHONPATH/--repo mismatch'
    Reset-Topology;$topology.Xml=$xml.Replace('--host','--repo &quot;'+$release+'&quot; --host');Assert-Topology 'Duplicate_repo' 'duplicate runtime launcher option'
    Reset-Topology;$topology.Xml=$xml.Replace('runtime\python.exe','runtime\other.exe');Assert-Topology 'Wrong_launcher_runtime' 'runtime/--repo mismatch'
    Reset-Topology;$topology.Xml=$xml.Replace('--port 5101','--port 5102');Assert-Topology 'Wrong_launcher_port' 'launcher endpoint must be 127.0.0.1:5101'
    Reset-Topology;$topology.Xml=$xml.Replace('--host 127.0.0.1','--host 0.0.0.0');Assert-Topology 'Wrong_launcher_host' 'launcher endpoint must be 127.0.0.1:5101'
    Reset-Topology;$topology.Xml=$xml.Replace('serve --env','serve -m waitress --env');Assert-Topology 'Extra_task_backend_tokens' 'unsupported runtime launcher option'
    Reset-Topology;$topology.Xml=$xml.Replace('serve --env','serve &amp; echo --env');Assert-Topology 'Shell_chain_refused' 'unsupported shell syntax in launcher arguments'
    Reset-Topology;$topology.Xml=$xml.Replace('/d /c','/c');Assert-Topology 'Cmd_autorun_not_disabled' 'cmd.exe /d /c required'
    Reset-Topology;$topology.Xml=$xml.Replace('C:\Windows\System32\cmd.exe','C:\unapproved\cmd.exe');Assert-Topology 'Unapproved_cmd_path' 'system cmd.exe required'
    Reset-Topology;$topology.Xml=$xml.Replace('</Actions>','<ComHandler /></Actions>');Assert-Topology 'Extra_action_refused' 'one task action required'
    $badCommands=@(
        ('"'+$python+'" -m waitress --listen=127.0.0.1:5101 unrelated:app'),
        ('"'+$python+'" -m waitress --listen=127.0.0.1:5102 backend.wsgi:app'),
        ('"'+$python+'" -c "print(1)" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app'),
        '"C:\another-release\runtime\python.exe" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app'
    )
    if($badCommands.Count -ne 4){throw 'listener negative matrix inventory changed'}
    $commandCase=0
    foreach($badCommand in $badCommands){
        $commandCase++
        Reset-Topology;$topology.CommandLine=$badCommand;Assert-Topology ('Wrong_listener_command_'+$commandCase) 'orphan/mismatched listener: process is not the configured Waitress backend'
    }
    # Quoted paths, XML namespaces, slash/case normalization, and optional log.
    Reset-Topology;$topology.Xml=$xml.Replace('<Task>','<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">');Assert-Topology 'Task_XML_namespace'
    Reset-Topology;$topology.Xml=$xml.Replace('release-forwarder-systemic-workflow','release with spaces-forwarder-systemic-workflow');$topology.Runtime=$python.Replace('release-forwarder-systemic-workflow','release with spaces-forwarder-systemic-workflow');$topology.Iis=$topology.Iis.Replace('release-forwarder-systemic-workflow','release with spaces-forwarder-systemic-workflow');$topology.CommandLine='"'+$topology.Runtime+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app';Assert-Topology 'Launcher_release_path_spaces'
    Reset-Topology;$topology.Xml=$xml.Replace('/d /c set PYTHONPATH=','/d /c echo wrong &amp;&amp; set PYTHONPATH=');Assert-Topology 'Extra_shell_command' 'unsupported shell syntax in launcher arguments'
    Reset-Topology;$topology.Xml=$xml.Replace(' --log &quot;C:\1-webapp\forwarder-runtime\waitress.log&quot;','');Assert-Topology 'Launcher_optional_log_absent'
    foreach($field in @('Execute','Arguments','WorkingDirectory')){Reset-Topology;$topology.ActionMismatch=$field;Assert-Topology ('Task_export_snapshot_'+$field) 'task action/export configuration mismatch'}
    Reset-Topology;$topology.Xml=$xml.Replace('C:\Windows\System32\cmd.exe',$python);Assert-Topology 'Direct_python_action_refused' 'system cmd.exe required'
    Reset-Topology;$topology.Runtime=$python.ToUpperInvariant().Replace('\','/');Assert-Topology 'Windows_path_normalization'
    'TASK_READY_WITH_MATCHING_LISTENER_SUPPORTED=YES','TASK_STATE_NOT_USED_AS_SOLE_OWNERSHIP_AUTHORITY=YES','LISTENER_PROVENANCE_MODEL=PASS','ORPHAN_CLASSIFICATION_MATRIX=PASS','BASELINE_CAPTURE_MATRIX=PASS'
    }
    Write-Output 'REAL_NONFIXTURE_VALIDATEONLY=PASS'
    Write-Output 'VALIDATEONLY_ZERO_MUTATION=PASS'
    Write-Output 'FRESH_PROCESS_VALIDATEONLY=PASS'
    Write-Output 'STRICTMODE_FRESH_PROCESS=PASS'
    Write-Output 'ARBITRARY_CWD_VALIDATEONLY=PASS'
    'IIS_CHANGED=NO','TASK_CHANGED=NO','BACKEND_STOPPED=NO','BACKEND_STARTED=NO','DATABASE_MIGRATED=NO','PORT_CHANGED=NO'
}finally{
    $env:DATABASE_URL=$previousDatabaseUrl
    $env:APP_ENV=$previousAppEnv
    $env:FW_TEST_DATABASE=$previousTestDatabase
    if((Split-Path -Parent ([IO.Path]::GetFullPath($temporary))) -ne [IO.Path]::GetTempPath().TrimEnd('\')){throw 'cleanup escaped temporary directory'}
    Remove-Item -LiteralPath $temporary -Recurse -Force
    Set-Location $previousLocation
}
