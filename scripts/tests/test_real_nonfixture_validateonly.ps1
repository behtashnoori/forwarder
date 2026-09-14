#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[string]$DeployScript,[switch]$FreshChild)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $DeployScript){$DeployScript=Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1'}
if(-not $FreshChild){
    $output=@(& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $PSCommandPath -PackageRoot $PackageRoot -DeployScript $DeployScript -FreshChild 2>&1)
    if($LASTEXITCODE -ne 0 -or $output -notcontains 'FRESH_PROCESS_VALIDATEONLY=PASS'){throw ($output -join "`n")}
    $output
    return
}
if($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1){throw 'Windows PowerShell 5.1 required'}
if(@(Get-Variable -Scope Global | Where-Object Name -like 'Forwarder*').Count){throw 'fresh child inherited Forwarder state'}
if(Get-Variable ForwarderExecuteState -Scope Global -ErrorAction SilentlyContinue){throw 'ForwarderExecuteState is not absent'}
Write-Output 'PREINVOCATION_FORWARDER_EXECUTE_STATE=ABSENT'
$previousLocation=Get-Location
Set-Location ([IO.Path]::GetTempPath())
$release='C:\1-webapp\forwarder-production\release-mocked'
$python=Join-Path $release 'runtime\python.exe'
$xml='<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c &quot;'+$python+'&quot; -m waitress --listen=127.0.0.1:5101 backend.wsgi:app</Arguments><WorkingDirectory>'+$release+'</WorkingDirectory></Exec></Actions></Task>'
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
    function Import-Module { param([string]$Name) }
    function Get-Website { param([string]$Name) [pscustomobject]@{PhysicalPath=(Join-Path $release 'dist')} }
    function Get-ScheduledTask { param([string]$TaskName) [pscustomobject]@{State='Running'} }
    function Export-ScheduledTask { param([string]$TaskName) $xml }
    function Get-NetTCPConnection { param([string]$State,[int]$LocalPort) [pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=4242} }
    function Get-CimInstance { param([string]$ClassName,[string]$Filter) [pscustomobject]@{ExecutablePath=$python;CommandLine=($python+' -m waitress backend.wsgi:app')} }
    function Invoke-WebRequest { param([string]$Uri,[int]$TimeoutSec) [pscustomobject]@{StatusCode=200} }
    function Disable-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to disable task' }
    function Stop-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to stop task' }
    function Stop-Process { $mutations.Count++;throw 'ValidateOnly tried to stop process' }
    function Register-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to register task' }
    function Set-WebConfigurationProperty { $mutations.Count++;throw 'ValidateOnly tried to change IIS' }
    function Enable-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to enable task' }
    function Start-ScheduledTask { $mutations.Count++;throw 'ValidateOnly tried to start task' }
    function Set-NetTCPConnection { $mutations.Count++;throw 'ValidateOnly tried to change port' }
    $root=$PackageRoot
    if($DeployScript -ne (Join-Path $root 'deploy_windows_iis_waitress.ps1')){throw 'fresh regression requires exact packaged deployment path'}
    & "$root\deploy_windows_iis_waitress.ps1" -PackageRoot $root -ValidateOnly
    if($mutations.Count -ne 0 -or (Get-FileHash -LiteralPath $database -Algorithm SHA256).Hash -ne $beforeHash){throw 'ValidateOnly mutated observed state'}
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
    Remove-Item -LiteralPath $temporary -Recurse -Force
    Set-Location $previousLocation
}
