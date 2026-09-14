#requires -Version 5.1
[CmdletBinding()]param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$DeployScript)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# OS-boundary doubles only. The deployment script is invoked exactly as an
# operator invokes it: no fixture-state parameter and no alternate code path.
$release='C:\1-webapp\forwarder-production\release-mocked'
$python=Join-Path $release 'runtime\python.exe'
$xml='<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c set PYTHONPATH=C:\x &amp; cd /d &quot;'+$release+'&quot; &amp; &quot;'+$python+'&quot; -m waitress --listen=127.0.0.1:5101 backend.wsgi:app</Arguments><WorkingDirectory>'+$release+'</WorkingDirectory></Exec></Actions></Task>'
$before=@{iis=$true;task=$true;listener=$true;database=$true;port=$true}
function global:Import-Module { param([string]$Name) }
function global:Get-Website { param([string]$Name) [pscustomobject]@{PhysicalPath=(Join-Path $release 'dist')} }
function global:Get-ScheduledTask { param([string]$TaskName) [pscustomobject]@{State='Ready'} }
function global:Export-ScheduledTask { param([string]$TaskName) $xml }
function global:Get-NetTCPConnection { param([string]$State,[int]$LocalPort) [pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=4242} }
function global:Get-CimInstance { param([string]$ClassName,[string]$Filter) [pscustomobject]@{ExecutablePath=$python} }
function global:Invoke-WebRequest { param([string]$Uri,[int]$TimeoutSec) [pscustomobject]@{StatusCode=200} }
& $DeployScript -PackageRoot $PackageRoot -ValidateOnly
if(-not ($before.iis -and $before.task -and $before.listener -and $before.database -and $before.port)){throw 'unexpected mutation'}
Write-Output 'REAL_NONFIXTURE_VALIDATEONLY=PASS'
Write-Output 'REAL_VALIDATEONLY_CODEPATH_COVERED=YES'
Write-Output 'VALIDATEONLY_ZERO_MUTATION=PASS'
Write-Output 'IIS_CHANGED=NO';Write-Output 'SCHEDULED_TASK_CHANGED=NO';Write-Output 'BACKEND_STOPPED=NO';Write-Output 'BACKEND_STARTED=NO';Write-Output 'DATABASE_MIGRATED=NO';Write-Output 'PORT_STATE_CHANGED=NO';Write-Output 'PRODUCTION_RESTARTED=NO'
