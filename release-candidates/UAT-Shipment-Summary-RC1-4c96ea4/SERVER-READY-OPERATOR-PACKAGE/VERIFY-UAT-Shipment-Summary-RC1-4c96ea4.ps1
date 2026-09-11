[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$target='C:\1-webapp\forwarder-production\release-UAT-Shipment-Summary-RC1-4c96ea4'
$task='Forwarder Backend Production'
Import-Module WebAdministration -ErrorAction Stop
Import-Module ScheduledTasks -ErrorAction Stop
$site=Get-Website -Name forwarder -ErrorAction Stop
if($site.physicalPath -ne (Join-Path $target 'dist')){throw 'VERIFY_FAIL: IIS target identity mismatch'}
$xml=(Export-ScheduledTask -TaskName $task) -replace '\r|\n',' '
if($xml -notmatch [regex]::Escape((Join-Path $target 'runtime\python.exe'))){throw 'VERIFY_FAIL: Scheduled Task target runtime mismatch'}
$connection=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5101 -State Listen -ErrorAction Stop
if(@($connection).Count -ne 1){throw 'VERIFY_FAIL: backend listener is not singular'}
$process=Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)" -ErrorAction Stop
if(([string]$process.CommandLine).IndexOf((Join-Path $target 'runtime\python.exe'),[StringComparison]::OrdinalIgnoreCase) -lt 0){throw 'VERIFY_FAIL: listener runtime provenance mismatch'}
if((Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5101/api/health').StatusCode -ne 200){throw 'VERIFY_FAIL: health endpoint failed'}
if((Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5101/api/health/ping').StatusCode -ne 200){throw 'VERIFY_FAIL: ping endpoint failed'}
$origin='https://samand.forwarderet.ir'
$cors=Invoke-WebRequest -UseBasicParsing "$origin/api/health" -Headers @{Origin=$origin}
if($cors.StatusCode -ne 200 -or $cors.Headers['Access-Control-Allow-Origin'] -ne $origin){throw 'VERIFY_FAIL: canonical same-origin/CORS check failed'}
Write-Output 'IIS_TARGET=PASS';Write-Output 'TASK_TARGET=PASS';Write-Output 'LISTENER_TARGET=PASS';Write-Output 'HEALTH=PASS';Write-Output 'PING=PASS';Write-Output 'CORS=PASS';Write-Output 'RELEASE_IDENTITY_MATCH=YES'
