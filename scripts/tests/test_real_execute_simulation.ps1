#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[string]$DeployScript,[switch]$DirtyChild)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $DeployScript){$DeployScript=Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1'}
if(-not $DirtyChild){
    try{$ErrorActionPreference='Continue';$output=@(& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $PSCommandPath -PackageRoot $PackageRoot -DeployScript $DeployScript -DirtyChild 2>&1);$childExit=$LASTEXITCODE}
    finally{$ErrorActionPreference='Stop'}
    if($childExit -ne 0 -or $output -notcontains 'REPEATED_INVOCATION_MATRIX=PASS'){throw ($output -join "`n")}
    $output
    return
}
if($PSVersionTable.PSVersion.ToString() -notlike '5.1.*'){throw 'Windows PowerShell 5.1 required'}
Microsoft.PowerShell.Core\Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('fx-'+[guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $temporary|Out-Null
$previousUrl=$env:DATABASE_URL
$previousAppEnv=$env:APP_ENV
$previousTestDatabase=$env:FW_TEST_DATABASE
try{
    $old=Join-Path $temporary 'previous-release'
    $oldPython=Join-Path $old 'runtime\python.exe'
    $database=Join-Path $temporary 'execute.sqlite'
    $env:FW_TEST_DATABASE=$database
    $setup=@'
import sqlite3, os
connection=sqlite3.connect(os.environ['FW_TEST_DATABASE'])
connection.execute('CREATE TABLE alembic_version (version_num VARCHAR(128) NOT NULL)')
connection.execute('INSERT INTO alembic_version VALUES (?)', ('20260921_shipment_evidence_ownership',))
connection.commit()
connection.close()
'@
    & (Join-Path $PackageRoot 'artifact\runtime\python.exe') -c $setup
    if($LASTEXITCODE -ne 0){throw 'disposable DB setup failed'}
    $env:DATABASE_URL='sqlite:///'+$database.Replace('\','/')
    $env:APP_ENV='production'
    $xml='<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c set PYTHONPATH='+$old+' &amp;&amp; cd /d &quot;'+$old+'&quot; &amp;&amp; &quot;'+$oldPython+'&quot; &quot;C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py&quot; serve --env &quot;C:\1-webapp\forwarder-runtime\production.env&quot; --repo &quot;'+$old+'&quot; --host 127.0.0.1 --port 5101 --log &quot;C:\1-webapp\forwarder-runtime\waitress.log&quot;</Arguments><WorkingDirectory>'+$old+'</WorkingDirectory></Exec></Actions></Task>'
    [xml]$taskDoc=$xml; $taskArgs=[string]$taskDoc.Task.Actions.Exec.Arguments; $taskDoc.Task.Actions.Exec.Arguments='/d /c "'+$taskArgs.Substring(6).Replace('"','""')+'"'; $xml=$taskDoc.OuterXml
    $simulation=[pscustomobject]@{Iis=(Join-Path $old 'dist');Xml=$xml;Enabled=$true;Running=$false;Listener=$oldPython;Mutations=0;Events=@()}
    function Import-Module { param([string]$Name) }
    function Get-Website { param([string]$Name) [pscustomobject]@{PhysicalPath=$simulation.Iis} }
    function Get-ScheduledTask { param([string]$TaskName) [xml]$document=$simulation.Xml;[pscustomobject]@{State=if($simulation.Running){'Running'}else{'Ready'};Settings=[pscustomobject]@{Enabled=$simulation.Enabled};Actions=@([pscustomobject]@{Execute=[string]$document.Task.Actions.Exec.Command;Arguments=[string]$document.Task.Actions.Exec.Arguments;WorkingDirectory=[string]$document.Task.Actions.Exec.WorkingDirectory})} }
    function Get-ScheduledTaskInfo { param($InputObject) [pscustomobject]@{LastTaskResult=0} }
    function Export-ScheduledTask { param([string]$TaskName) $simulation.Xml }
    function Get-NetTCPConnection { param([string]$State,[int]$LocalPort) if($simulation.Listener){[pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=4242}} }
    function Get-CimInstance { param([string]$ClassName,[string]$Filter) [pscustomobject]@{ExecutablePath=$simulation.Listener;CommandLine=('"'+$simulation.Listener+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app')} }
    function Invoke-WebRequest { param([string]$Uri,[int]$TimeoutSec) [pscustomobject]@{StatusCode=200} }
    function Disable-ScheduledTask { param([string]$TaskName) $simulation.Enabled=$false;$simulation.Mutations++;$simulation.Events+=,'disable' }
    function Stop-ScheduledTask { param([string]$TaskName) $simulation.Running=$false;$simulation.Mutations++;$simulation.Events+=,'stop' }
    function Get-Process { param([int]$Id) if($simulation.Listener){[pscustomobject]@{Id=$Id}} }
    function Stop-Process { param([int]$Id) if($Id -ne 4242){throw 'wrong listener PID stopped'};$simulation.Listener=$null;$simulation.Mutations++;$simulation.Events+=,'stop-listener' }
    function Register-ScheduledTask { param([string]$TaskName,[string]$Xml) if($simulation.FailRollback){throw 'simulated rollback task restore failure'};$simulation.Xml=$Xml;$simulation.Mutations++;$simulation.Events+=,'register' }
    function Enable-ScheduledTask { param([string]$TaskName) $simulation.Enabled=$true;$simulation.Mutations++ }
    function Start-ScheduledTask { param([string]$TaskName) [xml]$task=$simulation.Xml;$simulation.Listener=Join-Path ([string]$task.Task.Actions.Exec.WorkingDirectory) 'runtime\python.exe';$simulation.Running=$false;$simulation.Mutations++ }
    function Set-WebConfigurationProperty { param([string]$PSPath,[string]$Filter,[string]$Name,[string]$Value) $simulation.Iis=$Value;$simulation.Mutations++ }
    $simulation | Add-Member NoteProperty FailRollback $false
    # A, B, C: unset global, deliberately stale global, repeated validation.
    & $DeployScript -PackageRoot $PackageRoot -ValidateOnly | Out-Null
    Set-Variable ForwarderExecuteState -Scope Global -Value 'stale-state-must-not-be-read'
    & $DeployScript -PackageRoot $PackageRoot -ValidateOnly | Out-Null
    & $DeployScript -PackageRoot $PackageRoot -ValidateOnly | Out-Null
    if($simulation.Mutations -ne 0){throw 'repeated ValidateOnly mutated server boundary'}
    & $DeployScript -PackageRoot $PackageRoot -Execute -ConfirmDeployment -ReleaseRoot $temporary |Out-Null
    $mutationCount=$simulation.Mutations
    & $DeployScript -PackageRoot $PackageRoot -ValidateOnly | Out-Null
    if($simulation.Mutations -ne $mutationCount){throw 'post-Execute ValidateOnly mutated state'}
    if($simulation.Mutations -lt 6 -or $simulation.Listener -eq $oldPython -or $simulation.Iis -eq (Join-Path $old 'dist')){throw 'real execute operations did not complete'}
    $events=$simulation.Events
    if([array]::IndexOf($events,'disable') -ge [array]::IndexOf($events,'stop') -or [array]::IndexOf($events,'stop') -ge [array]::IndexOf($events,'register')){throw 'Scheduled Task stop/restart ordering is unsafe'}
    if([array]::IndexOf($events,'stop-listener') -le [array]::IndexOf($events,'stop') -or [array]::IndexOf($events,'stop-listener') -ge [array]::IndexOf($events,'register')){throw 'launcher child was not stopped before task replacement'}
    if(-not (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $simulation.Listener) 'python.exe'))){throw 'target runtime missing'}
    $failureIndex=0
    foreach($failure in @('PACKAGE_VERIFY','BASELINE_CAPTURE','DB_GATE','TARGET_MATERIALIZE','TASK_DISABLE','BACKEND_STOP','PORT_RELEASE','TASK_SWITCH','BACKEND_START','LISTENER_VERIFY','INTERNAL_HEALTH','IIS_SWITCH','IIS_VERIFY','PUBLIC_HEALTH','POST_DEPLOY_VERIFY')){
        $simulation.Iis=Join-Path $old 'dist'
        $simulation.Xml=$xml
        $simulation.Enabled=$true
        $simulation.Running=$false
        $simulation.Listener=$oldPython
        $failureIndex++
        $failureRoot=Join-Path $temporary ('f'+$failureIndex)
        New-Item -ItemType Directory -Path $failureRoot|Out-Null
        $rejected=$false
        try{& $DeployScript -PackageRoot $PackageRoot -Execute -ConfirmDeployment -ReleaseRoot $failureRoot -FailAt $failure|Out-Null}catch{if($_.Exception.Message -ne ('RELEASE_STOP: injected '+$failure)){throw};$rejected=$true}
        if(-not $rejected -or $simulation.Iis -ne (Join-Path $old 'dist') -or $simulation.Listener -ne $oldPython -or $simulation.Xml -ne $xml -or -not $simulation.Enabled){throw "real rollback invariant failed: $failure"}
        $mutationCount=$simulation.Mutations
        & $DeployScript -PackageRoot $PackageRoot -ValidateOnly | Out-Null
        if($simulation.Mutations -ne $mutationCount){throw 'post-rollback ValidateOnly mutated state'}
        $resolvedFailure=[IO.Path]::GetFullPath($failureRoot)
        if(-not $resolvedFailure.StartsWith([IO.Path]::GetFullPath($temporary)+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'cleanup escaped disposable root'}
        Remove-Item -LiteralPath $resolvedFailure -Recurse -Force
        Write-Output ('REAL_FAILURE_STAGE='+$failure+'; POST_FAILURE_VALIDATEONLY=PASS')
    }
    $simulation.FailRollback=$true
    $rollbackFailed=$false
    $rollbackMessage='no exception'
    try{& $DeployScript -PackageRoot $PackageRoot -Execute -ConfirmDeployment -ReleaseRoot (Join-Path $temporary 'rb') -FailAt TASK_DISABLE | Out-Null}
    catch{$rollbackMessage=$_.Exception.Message;$rollbackFailed=$rollbackMessage -match 'cutover and rollback failed; primary=.*TASK_DISABLE; rollback=.*simulated rollback'}
    if(-not $rollbackFailed){throw ('rollback failure was not reported with primary failure: '+$rollbackMessage)}
    $simulation.FailRollback=$false
    if((Get-Variable ForwarderExecuteState -Scope Global -ValueOnly) -ne 'stale-state-must-not-be-read'){throw 'ambient state modified'}
    Remove-Variable ForwarderExecuteState -Scope Global
    Write-Output 'ROLLBACK_FAILURE_REPORTING=PASS'
    Write-Output 'AMBIENT_GLOBAL_STATE_INDEPENDENCE=PASS'
    Write-Output 'REPEATED_INVOCATION_MATRIX=PASS'
    Write-Output 'REAL_EXECUTE_CODEPATH=PASS'
    Write-Output 'FULL_EXECUTE_SIMULATION=PASS'
    Write-Output 'REAL_ROLLBACK_MATRIX=PASS'
}finally{
    $env:DATABASE_URL=$previousUrl
    $env:APP_ENV=$previousAppEnv
    $env:FW_TEST_DATABASE=$previousTestDatabase
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
