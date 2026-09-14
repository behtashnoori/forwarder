#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[string]$DeployScript)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $DeployScript){$DeployScript=Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1'}
$release='C:\1-webapp\forwarder-production\release-mocked'
$python=Join-Path $release 'runtime\python.exe'
$xml='<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c &quot;'+$python+'&quot; -m waitress --listen=127.0.0.1:5101 backend.wsgi:app</Arguments><WorkingDirectory>'+$release+'</WorkingDirectory></Exec></Actions></Task>'
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('forwarder-db-gate-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary|Out-Null
$previousDatabaseUrl=$env:DATABASE_URL
$previousAppEnv=$env:APP_ENV
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
    $script:mutations=0
    function global:Import-Module { param([string]$Name) }
    function global:Get-Website { param([string]$Name) [pscustomobject]@{PhysicalPath=(Join-Path $release 'dist')} }
    function global:Get-ScheduledTask { param([string]$TaskName) [pscustomobject]@{State='Running'} }
    function global:Export-ScheduledTask { param([string]$TaskName) $xml }
    function global:Get-NetTCPConnection { param([string]$State,[int]$LocalPort) [pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=4242} }
    function global:Get-CimInstance { param([string]$ClassName,[string]$Filter) [pscustomobject]@{ExecutablePath=$python;CommandLine=($python+' -m waitress backend.wsgi:app')} }
    function global:Invoke-WebRequest { param([string]$Uri,[int]$TimeoutSec) [pscustomobject]@{StatusCode=200} }
    function global:Disable-ScheduledTask { $script:mutations++;throw 'ValidateOnly tried to disable task' }
    function global:Stop-ScheduledTask { $script:mutations++;throw 'ValidateOnly tried to stop task' }
    function global:Stop-Process { $script:mutations++;throw 'ValidateOnly tried to stop process' }
    function global:Register-ScheduledTask { $script:mutations++;throw 'ValidateOnly tried to register task' }
    function global:Set-WebConfigurationProperty { $script:mutations++;throw 'ValidateOnly tried to change IIS' }
    & $DeployScript -PackageRoot $PackageRoot -ValidateOnly
    if($script:mutations -ne 0 -or (Get-FileHash -LiteralPath $database -Algorithm SHA256).Hash -ne $beforeHash){throw 'ValidateOnly mutated observed state'}
    Write-Output 'REAL_NONFIXTURE_VALIDATEONLY=PASS'
    Write-Output 'VALIDATEONLY_ZERO_MUTATION=PASS'
}finally{
    $env:DATABASE_URL=$previousDatabaseUrl
    $env:APP_ENV=$previousAppEnv
    Remove-Item Env:FW_TEST_DATABASE -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
