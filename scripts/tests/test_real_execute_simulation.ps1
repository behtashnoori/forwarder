#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[string]$DeployScript)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $DeployScript){$DeployScript=Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1'}
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('forwarder-execute-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary|Out-Null
$previousUrl=$env:DATABASE_URL
$previousAppEnv=$env:APP_ENV
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
    $xml='<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c &quot;'+$oldPython+'&quot; -m waitress --listen=127.0.0.1:5101 backend.wsgi:app</Arguments><WorkingDirectory>'+$old+'</WorkingDirectory></Exec></Actions></Task>'
    $global:ForwarderExecuteState=[pscustomobject]@{Iis=(Join-Path $old 'dist');Xml=$xml;Enabled=$true;Running=$true;Listener=$oldPython;Mutations=0;Events=@()}
    function global:Import-Module { param([string]$Name) }
    function global:Get-Website { param([string]$Name) [pscustomobject]@{PhysicalPath=$global:ForwarderExecuteState.Iis} }
    function global:Get-ScheduledTask { param([string]$TaskName) [pscustomobject]@{State=if($global:ForwarderExecuteState.Running){'Running'}else{'Ready'}} }
    function global:Export-ScheduledTask { param([string]$TaskName) $global:ForwarderExecuteState.Xml }
    function global:Get-NetTCPConnection { param([string]$State,[int]$LocalPort) if($global:ForwarderExecuteState.Listener){[pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=4242}} }
    function global:Get-CimInstance { param([string]$ClassName,[string]$Filter) [pscustomobject]@{ExecutablePath=$global:ForwarderExecuteState.Listener;CommandLine=($global:ForwarderExecuteState.Listener+' -m waitress backend.wsgi:app')} }
    function global:Invoke-WebRequest { param([string]$Uri,[int]$TimeoutSec) [pscustomobject]@{StatusCode=200} }
    function global:Disable-ScheduledTask { param([string]$TaskName) $global:ForwarderExecuteState.Enabled=$false;$global:ForwarderExecuteState.Mutations++;$global:ForwarderExecuteState.Events+=,'disable' }
    function global:Stop-ScheduledTask { param([string]$TaskName) $global:ForwarderExecuteState.Running=$false;$global:ForwarderExecuteState.Listener=$null;$global:ForwarderExecuteState.Mutations++;$global:ForwarderExecuteState.Events+=,'stop' }
    function global:Get-Process { param([int]$Id) $null }
    function global:Stop-Process { param([int]$Id) $global:ForwarderExecuteState.Listener=$null;$global:ForwarderExecuteState.Mutations++ }
    function global:Register-ScheduledTask { param([string]$TaskName,[string]$Xml) $global:ForwarderExecuteState.Xml=$Xml;$global:ForwarderExecuteState.Mutations++;$global:ForwarderExecuteState.Events+=,'register' }
    function global:Enable-ScheduledTask { param([string]$TaskName) $global:ForwarderExecuteState.Enabled=$true;$global:ForwarderExecuteState.Mutations++ }
    function global:Start-ScheduledTask { param([string]$TaskName) [xml]$task=$global:ForwarderExecuteState.Xml;$global:ForwarderExecuteState.Listener=Join-Path ([string]$task.Task.Actions.Exec.WorkingDirectory) 'runtime\python.exe';$global:ForwarderExecuteState.Running=$true;$global:ForwarderExecuteState.Mutations++ }
    function global:Set-WebConfigurationProperty { param([string]$PSPath,[string]$Filter,[string]$Name,[string]$Value) $global:ForwarderExecuteState.Iis=$Value;$global:ForwarderExecuteState.Mutations++ }
    & $DeployScript -PackageRoot $PackageRoot -Execute -ConfirmDeployment -ReleaseRoot $temporary |Out-Null
    if($global:ForwarderExecuteState.Mutations -lt 6 -or $global:ForwarderExecuteState.Listener -eq $oldPython -or $global:ForwarderExecuteState.Iis -eq (Join-Path $old 'dist')){throw 'real execute operations did not complete'}
    $events=$global:ForwarderExecuteState.Events
    if([array]::IndexOf($events,'disable') -ge [array]::IndexOf($events,'stop') -or [array]::IndexOf($events,'stop') -ge [array]::IndexOf($events,'register')){throw 'Scheduled Task stop/restart ordering is unsafe'}
    if(-not (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $global:ForwarderExecuteState.Listener) 'python.exe'))){throw 'target runtime missing'}
    foreach($failure in @('TASK_DISABLE','PUBLIC_HEALTH')){
        $global:ForwarderExecuteState.Iis=Join-Path $old 'dist'
        $global:ForwarderExecuteState.Xml=$xml
        $global:ForwarderExecuteState.Enabled=$true
        $global:ForwarderExecuteState.Running=$true
        $global:ForwarderExecuteState.Listener=$oldPython
        $failureRoot=Join-Path $temporary ('failure-'+$failure)
        New-Item -ItemType Directory -Path $failureRoot|Out-Null
        $rejected=$false
        try{& $DeployScript -PackageRoot $PackageRoot -Execute -ConfirmDeployment -ReleaseRoot $failureRoot -FailAt $failure|Out-Null}catch{$rejected=$true}
        if(-not $rejected -or $global:ForwarderExecuteState.Iis -ne (Join-Path $old 'dist') -or $global:ForwarderExecuteState.Listener -ne $oldPython -or $global:ForwarderExecuteState.Xml -ne $xml -or -not $global:ForwarderExecuteState.Enabled){throw "real rollback invariant failed: $failure"}
    }
    Write-Output 'REAL_EXECUTE_CODEPATH=PASS'
    Write-Output 'FULL_EXECUTE_SIMULATION=PASS'
    Write-Output 'REAL_ROLLBACK_MATRIX=PASS'
}finally{
    $env:DATABASE_URL=$previousUrl
    $env:APP_ENV=$previousAppEnv
    Remove-Item Env:FW_TEST_DATABASE -ErrorAction SilentlyContinue
    Remove-Variable ForwarderExecuteState -Scope Global -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
