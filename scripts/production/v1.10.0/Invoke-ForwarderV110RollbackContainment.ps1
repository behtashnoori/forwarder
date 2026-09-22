#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('A','B','C')][string]$Checkpoint,
    [Parameter(Mandatory=$true)][string]$BaselineStatePath,
    [Parameter(Mandatory=$true)][string]$TargetReleasePath,
    [string]$TaskName = 'Forwarder Backend Production',
    [string]$IisSiteName = 'forwarder',
    [int]$BackendPort = 5101,
    [switch]$PlanOnly,
    [switch]$ExecuteContainment,
    [switch]$RestorePriorApplication,
    [switch]$ConfirmContainment,
    [string]$FixtureStatePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$WriterContainmentTimeoutMilliseconds=15000
$WriterContainmentPollMilliseconds=250
$WriterContainmentQuietMilliseconds=2000
function Stop-Containment([string]$Message){throw "CONTAINMENT_BLOCKED: $Message"}
function NPath([string]$Value){if([string]::IsNullOrWhiteSpace($Value)){Stop-Containment 'empty path'};return [IO.Path]::GetFullPath($Value.Trim().Trim('"').Trim("'")).TrimEnd('\')}
function SamePath([string]$A,[string]$B){return [string]::Equals((NPath $A),(NPath $B),[StringComparison]::OrdinalIgnoreCase)}
function ReleaseFrom([string]$Text){$m=[regex]::Match($Text,'(?i)[A-Z]:\\(?:[^\\\s"''&|]+\\)*release-[^\\\s"''&|]+');if($m.Success){return NPath $m.Value.TrimEnd(';','&','|')};return $null}
function AssertCandidateProcess($Process,[string]$ExpectedPython){if(-not(SamePath ([string]$Process.ExecutablePath) $ExpectedPython)){Stop-Containment 'listener executable is not candidate runtime'};$line=[string]$Process.CommandLine;$listenPattern='(?i)--listen=127\.0\.0\.1:'+[regex]::Escape([string]$BackendPort)+'(?:\s|$)';if($line-notmatch'(?i)-m\s+waitress'-or$line-notmatch$listenPattern-or$line-notmatch'(?i)backend\.wsgi:app'){Stop-Containment 'listener command is not governed Waitress invocation'}}
function GetGovernedOwners{try{$rows=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object{$_.LocalAddress-eq'127.0.0.1'-and[int]$_.LocalPort-eq$BackendPort})}catch{Stop-Containment ('governed port inspection failed: '+$_.Exception.Message)};return @($rows|Select-Object -ExpandProperty OwningProcess -Unique|ForEach-Object{[int]$_})}
function TaskIsDisabled{$tasks=@(Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop);if($tasks.Count-ne1){Stop-Containment 'governed task missing or ambiguous during teardown'};return(-not[bool]$tasks[0].Settings.Enabled)}

if($PlanOnly -and $ExecuteContainment){Stop-Containment 'choose one mode'}
if(-not$PlanOnly -and -not$ExecuteContainment){$PlanOnly=$true}
if(-not(Test-Path -LiteralPath $BaselineStatePath -PathType Leaf)){Stop-Containment 'baseline state missing'}
$baseline=Get-Content -Raw -LiteralPath $BaselineStatePath|ConvertFrom-Json
$target=NPath $TargetReleasePath
if($target-notmatch'(?i)\\release-\d{14}-20260926_fixed_shipment_responsible_expert$'){Stop-Containment 'target release path contract mismatch'}
if((NPath ([string]$baseline.target_release_path))-ne$target){Stop-Containment 'baseline target identity mismatch'}
if($RestorePriorApplication -and $Checkpoint-ne'A'){Stop-Containment 'prior application restore is prohibited after migration without a separate compatibility/recovery decision'}

Write-Output ('ROLLBACK_CHECKPOINT='+$Checkpoint)
switch($Checkpoint){
 'A'{Write-Output 'RECOVERY_DECISION=ABANDON_CANDIDATE_AND_RESTORE_VERIFIED_PRIOR_APPLICATION_IF_NEEDED'}
 'B'{Write-Output 'RECOVERY_DECISION=KEEP_WRITERS_CONTAINED_DBA_RELEASE_OWNER_FORWARD_REPAIR_OR_SEPARATE_DATABASE_RESTORE_DECISION'}
 'C'{Write-Output 'RECOVERY_DECISION=STOP_NEW_WRITES_PREFER_ROLL_FORWARD_AND_REQUIRE_EXPLICIT_DATA_LOSS_ACCEPTANCE_FOR_RESTORE'}
}
Write-Output 'AUTOMATIC_DATABASE_DOWNGRADE=NO'
Write-Output 'AUTOMATIC_DATABASE_RESTORE=NO'
if($PlanOnly){Write-Output 'CONTAINMENT_PLAN_ONLY=PASS';Write-Output 'PRODUCTION_MUTATION_PERFORMED=NO';exit 0}
if(-not$ConfirmContainment){Stop-Containment 'explicit containment confirmation required'}

if($FixtureStatePath){
    $state=Get-Content -Raw -LiteralPath $FixtureStatePath|ConvertFrom-Json
    if (-not (SamePath ([string]$state.task_release) $target) -or -not (SamePath ([string]$state.listener_release) $target)) { Stop-Containment 'fixture candidate ownership mismatch' }
    $state.task_enabled=$false;$state.listener_up=$false;$state.traffic_contained=$true
    if($RestorePriorApplication){$state.task_release=[string]$baseline.prior_release_path;$state.listener_release=[string]$baseline.prior_release_path;$state.iis_path=[string]$baseline.prior_iis_path;$state.task_enabled=$true;$state.listener_up=$true}
    $state|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $FixtureStatePath -Encoding UTF8
    Write-Output 'ROLLBACK_CONTAINMENT=PASS';exit 0
}

$tasks=@(Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop);if($tasks.Count-ne1){Stop-Containment 'task missing or ambiguous'}
$task=$tasks[0];$actions=@($task.Actions);if($actions.Count-ne1){Stop-Containment 'task action missing or ambiguous'}
$taskRelease=ReleaseFrom (([string]$actions[0].Execute)+' '+([string]$actions[0].Arguments)+' '+([string]$actions[0].WorkingDirectory))
if(-not$taskRelease-or-not(SamePath $taskRelease $target)){Stop-Containment 'task does not belong to candidate release'}
$owners=@(GetGovernedOwners);if($owners.Count-gt1){Stop-Containment 'listener ownership ambiguous'}
$candidatePython=Join-Path $target 'runtime\python.exe'
if($owners.Count-eq1){$process=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction Stop;AssertCandidateProcess $process $candidatePython}
Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
if(-not(TaskIsDisabled)){Stop-Containment 'governed task did not disable'}
Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
$listenerPid=if($owners.Count-eq1){[int]$owners[0]}else{0}
if($listenerPid-gt0){$again=Get-CimInstance Win32_Process -Filter ('ProcessId='+$listenerPid) -ErrorAction Stop;if($again){AssertCandidateProcess $again $candidatePython;Stop-Process -Id $listenerPid -Force -ErrorAction Stop}}
$deadline=[DateTime]::UtcNow.AddMilliseconds($WriterContainmentTimeoutMilliseconds);$quietSince=$null;$originalProcessGone=($listenerPid-eq0);$originalOwnsPort=($listenerPid-gt0)
do{
    if(-not(TaskIsDisabled)){Stop-Containment 'governed task became enabled during teardown'}
    $currentOwners=@(GetGovernedOwners);$replacementOwners=@($currentOwners|Where-Object{$listenerPid-eq0-or$_-ne$listenerPid})
    if($replacementOwners.Count-gt0){Stop-Containment ('replacement listener detected on 127.0.0.1:'+$BackendPort+'; original_pid='+$listenerPid+'; replacement_pid(s)='+($replacementOwners-join',')+'; replacement_not_terminated=YES')}
    $originalOwnsPort=$listenerPid-gt0-and@($currentOwners|Where-Object{$_-eq$listenerPid}).Count-gt0
    if($listenerPid-gt0){$originalProcessGone=$null-eq(Get-CimInstance Win32_Process -Filter ('ProcessId='+$listenerPid) -ErrorAction Stop)}
    $portFree=$currentOwners.Count-eq0
    if(($originalProcessGone-or-not$originalOwnsPort)-and$portFree){if($null-eq$quietSince){$quietSince=[DateTime]::UtcNow};if(([DateTime]::UtcNow-$quietSince).TotalMilliseconds-ge$WriterContainmentQuietMilliseconds){break}}else{$quietSince=$null}
    if([DateTime]::UtcNow-ge$deadline){Stop-Containment ('listener teardown timeout after '+$WriterContainmentTimeoutMilliseconds+'ms; original_process_gone='+$originalProcessGone+'; original_owns_port='+$originalOwnsPort+'; owner_pid(s)='+$(if($currentOwners.Count){$currentOwners-join','}else{'none'}))}
    Start-Sleep -Milliseconds $WriterContainmentPollMilliseconds
}while($true)
Write-Output 'TASK_DISABLED=PASS';Write-Output 'ORIGINAL_LISTENER_TERMINATED=PASS';Write-Output 'GOVERNED_PORT_FREE=PASS';Write-Output 'NO_REPLACEMENT_LISTENER=PASS'

if($RestorePriorApplication){
    if(-not(Test-Path -LiteralPath ([string]$baseline.prior_task_xml_path) -PathType Leaf)){Stop-Containment 'prior task XML missing'}
    if(-not(Test-Path -LiteralPath ([string]$baseline.prior_release_path) -PathType Container)){Stop-Containment 'prior release missing'}
    Import-Module WebAdministration -ErrorAction Stop
    Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.applicationHost/sites/site[@name='$IisSiteName']/application[@path='/']/virtualDirectory[@path='/']" -Name physicalPath -Value ([string]$baseline.prior_iis_path) -ErrorAction Stop
    Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -Raw -LiteralPath ([string]$baseline.prior_task_xml_path)) -Force -ErrorAction Stop|Out-Null
    Enable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
    Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
}
Write-Output 'ROLLBACK_CONTAINMENT=PASS'
Write-Output 'WRITERS_CONTAINED=YES'
