#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[switch]$ValidateOnly,[switch]$Execute,[switch]$ConfirmDeployment,[string]$FixtureStatePath,[ValidateSet('','PACKAGE_VERIFY','BASELINE_CAPTURE','DB_GATE','MIGRATION','TARGET_MATERIALIZE','TASK_DISABLE','BACKEND_STOP','PORT_RELEASE','TASK_SWITCH','BACKEND_START','LISTENER_VERIFY','INTERNAL_HEALTH','IIS_SWITCH','IIS_VERIFY','PUBLIC_HEALTH','POST_DEPLOY_VERIFY')][string]$FailAt='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$RequiredBefore='20260920_legal_customer_nullable_contact_names';$RequiredTarget='20260921_shipment_evidence_ownership'
$Timeouts=@{DB_GATE=30;MIGRATION=180;BACKEND_STOP=30;PORT_RELEASE=30;TASK_UPDATE=30;BACKEND_START=45;LISTENER_VERIFY=45;IIS_SWITCH=30;IIS_VERIFY=30;INTERNAL_HEALTH=30;PUBLIC_HEALTH=45;ROLLBACK_RECOVERY=60}
function Need([bool]$Ok,[string]$Message){if(-not $Ok){throw "RELEASE_STOP: $Message"}}
function NPath([string]$Value){Need (-not [string]::IsNullOrWhiteSpace($Value)) 'empty path';$normalized=($Value.Trim().Trim('"').Trim("'") -replace '/','\');return [IO.Path]::GetFullPath($normalized).TrimEnd('\')}
function SamePath([string]$A,[string]$B){return [string]::Equals((NPath $A),(NPath $B),[StringComparison]::OrdinalIgnoreCase)}
function TaskRuntime([string]$Xml){[xml]$doc=$Xml;$exec=@($doc.SelectNodes("//*[local-name()='Exec']"));Need ($exec.Count -eq 1) 'one task action required';$command=NPath ([string]$exec[0].Command);$work=NPath ([string]$exec[0].WorkingDirectory);if([IO.Path]::GetFileName($command) -ieq 'python.exe'){$path=$command}else{Need ([IO.Path]::GetFileName($command) -ieq 'cmd.exe') 'cmd.exe or python.exe required';$found=@([regex]::Matches([string]$exec[0].Arguments,'(?i)[a-z]:[\\/][^"&\r\n]*?[\\/]runtime[\\/]python\.exe'));Need ($found.Count -eq 1) 'one release-local runtime required';$path=NPath $found[0].Value};Need ($path.StartsWith($work+'\',[StringComparison]::OrdinalIgnoreCase)) 'runtime outside task working directory';return $path}
function Fail([string]$Stage){if($FailAt -eq $Stage){throw "RELEASE_STOP: injected $Stage"}}
function Save(){if($FixtureStatePath){$script:state|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $FixtureStatePath -Encoding UTF8}}
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
    if($owners.Count -eq 1){$process=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop;Need (-not [string]::IsNullOrWhiteSpace([string]$process.ExecutablePath)) 'listener executable path unavailable';$runtime=[string]$process.ExecutablePath}
    $migration=& (Join-Path $PackageRoot 'artifact\runtime\python.exe') -m backend.migration_cli current 2>&1
    if($LASTEXITCODE -ne 0){throw 'RELEASE_STOP: database revision discovery failed'}
    $revisionLine=@($migration | ForEach-Object {[string]$_} | Where-Object {$_ -match '^current='} | Select-Object -Last 1)
    Need ($revisionLine.Count -eq 1) 'database revision output is ambiguous'
    $revision=$revisionLine[0].Substring(8)
    Need (-not [string]::IsNullOrWhiteSpace($revision)) 'database revision unavailable'
    $healthResponse=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5101/api/health' -TimeoutSec 10 -ErrorAction Stop
    Need ($healthResponse.StatusCode -eq 200) 'internal health is not HTTP 200'
    return [pscustomobject]@{iis_path=[string]$site.PhysicalPath;task_xml=[string]$xml;enabled=([string]$task.State -ne 'Disabled');listener_runtime=$runtime;listener_up=($owners.Count -eq 1);health=$true;db_revision=$revision}
}
function Rollback(){try{$script:state.iis_path=$script:before.iis_path;$script:state.task_xml=$script:before.task_xml;$script:state.enabled=$script:before.enabled;$script:state.listener_runtime=$script:before.listener_runtime;$script:state.listener_up=$true;$script:state.health=$true;Save;Write-Output 'ROLLBACK_RESULT=PASS'}catch{Write-Output 'ROLLBACK_RESULT=FAIL';throw}}
Need (-not($ValidateOnly -and $Execute)) 'one deployment mode';if(-not $ValidateOnly -and -not $Execute){$ValidateOnly=$true};if($Execute){Need $ConfirmDeployment 'confirmation required'}
Need (Test-Path -LiteralPath $PackageRoot -PathType Container) 'absolute package root required';$PackageRoot=(Resolve-Path -LiteralPath $PackageRoot).Path
if($FixtureStatePath){$script:state=Get-Content -Raw -LiteralPath $FixtureStatePath|ConvertFrom-Json}else{$script:state=Get-RealServerDiscoveryState}
Fail 'PACKAGE_VERIFY';& (Join-Path $PackageRoot 'VERIFY-PACKAGE.ps1') -PackageRoot $PackageRoot
Fail 'BASELINE_CAPTURE';$script:before=[pscustomobject]@{iis_path=$script:state.iis_path;task_xml=$script:state.task_xml;enabled=$script:state.enabled;listener_runtime=$script:state.listener_runtime};$oldPython=TaskRuntime $before.task_xml;Need (SamePath $oldPython $before.listener_runtime) 'pre-cutover runtime mismatch'
Fail 'DB_GATE';Need ($state.db_revision -in @($RequiredBefore,$RequiredTarget)) 'unknown database lineage';if($state.db_revision -eq $RequiredBefore){$migrationNeeded=$true}else{$migrationNeeded=$false};if($ValidateOnly){Write-Output 'FULL_VALIDATEONLY_SIMULATION=PASS';exit 0}
try{if($migrationNeeded){Fail 'MIGRATION';$state.db_revision=$RequiredTarget;Save};Fail 'TARGET_MATERIALIZE';$target='C:\1-webapp\forwarder-production\release-'+(Get-Date).ToUniversalTime().ToString('yyyyMMddHHmmss')+'-'+$RequiredTarget;$targetPython=Join-Path $target 'runtime\python.exe';Fail 'TASK_DISABLE';$state.enabled=$false;Save;Fail 'BACKEND_STOP';$state.listener_up=$false;Save;Fail 'PORT_RELEASE';Need (-not $state.listener_up) 'port not released';Fail 'TASK_SWITCH';$state.task_xml=$before.task_xml.Replace((Split-Path -Parent (Split-Path -Parent $oldPython)),$target);Save;Fail 'BACKEND_START';$state.enabled=$true;$state.listener_up=$true;$state.listener_runtime=$targetPython;Save;Fail 'LISTENER_VERIFY';Need (SamePath $state.listener_runtime $targetPython) 'target runtime mismatch';Fail 'INTERNAL_HEALTH';Need $state.health 'internal health failure';Fail 'IIS_SWITCH';$state.iis_path=Join-Path $target 'dist';Save;Fail 'IIS_VERIFY';Need (SamePath $state.iis_path (Join-Path $target 'dist')) 'IIS target mismatch';Fail 'PUBLIC_HEALTH';Need $state.health 'public health failure';Fail 'POST_DEPLOY_VERIFY';Write-Output 'FULL_EXECUTE_SIMULATION=PASS'}catch{$primary=$_;Rollback;throw $primary}
